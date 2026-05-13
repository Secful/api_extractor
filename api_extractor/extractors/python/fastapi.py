"""FastAPI framework extractor."""

import os
import re
from typing import List, Optional, Dict, Any
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
    Schema,
    Endpoint,
    Response,
    ParameterLocation,
    ValidationLibrary,
)


class FastAPIExtractor(BaseExtractor):
    """Extract API routes from FastAPI applications."""

    # HTTP method decorators
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize FastAPI extractor."""
        super().__init__(FrameworkType.FASTAPI)
        # Map of file paths to router variable names and their prefixes from APIRouter(prefix=...)
        # e.g., {"/path/to/endpoints.py": {"router": "/organizations"}}
        self.router_definitions: Dict[str, Dict[str, str]] = {}
        # Map of router variable names to their URL prefixes after include
        # e.g., {"/v1": {"/organizations": "organization_router"}}
        self.router_includes: Dict[str, Dict[str, str]] = {}
        # Map of router variable names to prefix from include_router(prefix=...) calls
        # e.g., {"v1_router": "/api", "integrations_router": "/api/integrations"}
        self.router_include_prefixes: Dict[str, str] = {}
        # Map of router import aliases to (source_file, original_variable_name)
        # e.g., {"analytics_router": ("/path/analytics.py", "router")}
        self.router_imports: Dict[str, tuple[str, str]] = {}
        # FastAPI app variable names (e.g., ["app"])
        self.app_variables: set = set()
        # Base path for the project (set during extract())
        self.base_path: str = ""
        # Global prefix from main router file (api.py, main.py, app.py)
        self.global_prefix: Optional[str] = None

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

    def get_validation_libraries(self) -> List[ValidationLibrary]:
        """FastAPI uses Pydantic for validation by default."""
        from api_extractor.core.models import ValidationLibrary
        return [ValidationLibrary.PYDANTIC]

    def extract(self, path: str):
        """
        Override extract to do multi-pass extraction:
        1. First pass: scan files to find APIRouter(prefix="...") definitions
        2. Second pass: scan files to find router.include_router() calls
        3. Third pass: extract routes with correct prefix chains

        Args:
            path: Path to codebase directory

        Returns:
            ExtractionResult with endpoints and any errors
        """
        self.endpoints = []
        self.errors = []
        self.warnings = []
        self.router_definitions = {}
        self.router_includes = {}
        self.router_include_prefixes = {}
        self.router_imports = {}
        self.app_variables = set()
        self.base_path = path
        self.global_prefix = None

        # Find all relevant files
        files = self._find_source_files(path)

        # Pass 1: Extract router definitions and imports to find prefixes
        # Also detect global prefix from main router files
        for file_path in files:
            try:
                self._extract_router_definitions(file_path)
                self._extract_router_imports(file_path)
                # Check if this is a main aggregator file
                filename = file_path.split('/')[-1]
                if filename in ('api.py', 'main.py', 'app.py') and self.global_prefix is None:
                    # Try to extract prefix from this file's router
                    if file_path in self.router_definitions:
                        routers = self.router_definitions[file_path]
                        # Use the first router's prefix as global prefix
                        if routers:
                            self.global_prefix = next(iter(routers.values()))
            except Exception as e:
                self.errors.append(f"Error extracting router definitions from {file_path}: {str(e)}")

        # Pass 2: Extract router includes to build hierarchy
        for file_path in files:
            try:
                self._extract_router_includes(file_path)
            except Exception as e:
                self.errors.append(f"Error extracting router includes from {file_path}: {str(e)}")

        # Pass 3: Extract routes from all files (now with prefix info)
        all_routes = []
        for file_path in files:
            try:
                routes = self.extract_routes_from_file(file_path)
                all_routes.extend(routes)
            except Exception as e:
                self.errors.append(f"Error extracting from {file_path}: {str(e)}")

        # Convert routes to endpoints
        for route in all_routes:
            try:
                endpoints = self._route_to_endpoints(route)
                self.endpoints.extend(endpoints)
            except Exception as e:
                self.errors.append(f"Error converting route to endpoint: {str(e)}")

        # Determine success
        success = len(self.endpoints) > 0 and len(self.errors) == 0

        from api_extractor.core.models import ExtractionResult
        return ExtractionResult(
            success=success,
            endpoints=self.endpoints,
            errors=self.errors,
            warnings=self.warnings,
            frameworks_detected=[self.framework],
        )

    def _extract_router_definitions(self, file_path: str) -> None:
        """
        Extract APIRouter and FastAPI app definitions from a file.

        Parses patterns like:
        router = APIRouter(prefix="/organizations")
        app = FastAPI(...)

        Builds mapping of file paths to router variable names and prefixes.

        Args:
            file_path: Path to Python file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for assignments: router = APIRouter(...) or app = FastAPI(...)
        assignment_query = """
        (assignment
          left: (identifier) @var_name
          right: (call
            function: (identifier) @func_name
            arguments: (argument_list) @args))
        """

        # Also query for attribute calls: app = fastapi.FastAPI(...)
        attribute_assignment_query = """
        (assignment
          left: (identifier) @var_name
          right: (call
            function: (attribute
              object: (identifier) @module_name
              attribute: (identifier) @func_name)
            arguments: (argument_list) @args))
        """

        matches = self.parser.query(tree, assignment_query, "python")
        matches.extend(self.parser.query(tree, attribute_assignment_query, "python"))

        file_routers = {}
        for match in matches:
            var_name_node = match.get("var_name")
            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not all([var_name_node, func_name_node, args_node]):
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Track FastAPI app instantiations
            if func_name == "FastAPI":
                self.app_variables.add(var_name)
                continue

            # Track APIRouter definitions
            if func_name != "APIRouter":
                continue

            # Extract prefix from arguments (can be None/empty)
            prefix = self._extract_prefix_from_arguments(args_node, source_code)
            # Store router even if no prefix (prefix can be empty string)
            file_routers[var_name] = prefix or ""

        if file_routers:
            self.router_definitions[file_path] = file_routers

    def _extract_router_imports(self, file_path: str) -> None:
        """
        Extract router imports and resolve them to source files.

        Parses patterns like:
        from .features.analytics import router as analytics_router
        from backend.api.features.store.routes import router

        Builds mapping of aliases to (source_file, original_variable_name).

        Args:
            file_path: Path to Python file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for aliased imports: from X import Y as Z
        aliased_import_query = """
        (import_from_statement
          module_name: (relative_import) @rel_module_name
          name: (aliased_import
            name: (dotted_name) @import_name
            alias: (identifier) @alias_name))
        """

        # Query for simple imports: from X import Y (no alias)
        simple_import_query = """
        (import_from_statement
          module_name: (relative_import) @rel_module_name
          name: (dotted_name) @import_name)
        """

        # Query for absolute aliased imports: from X import Y as Z
        absolute_aliased_query = """
        (import_from_statement
          module_name: (dotted_name) @abs_module_name
          name: (aliased_import
            name: (dotted_name) @import_name
            alias: (identifier) @alias_name))
        """

        # Query for absolute simple imports: from X import Y
        absolute_simple_query = """
        (import_from_statement
          module_name: (dotted_name) @abs_module_name
          name: (dotted_name) @import_name)
        """

        matches = self.parser.query(tree, aliased_import_query, "python")
        matches.extend(self.parser.query(tree, simple_import_query, "python"))
        matches.extend(self.parser.query(tree, absolute_aliased_query, "python"))
        matches.extend(self.parser.query(tree, absolute_simple_query, "python"))

        for match in matches:
            # Get module name (can be relative or absolute)
            module_name_node = match.get("rel_module_name") or match.get("abs_module_name")
            import_name_node = match.get("import_name")
            alias_name_node = match.get("alias_name")

            if not module_name_node or not import_name_node:
                continue

            module_name = self.parser.get_node_text(module_name_node, source_code)
            import_name = self.parser.get_node_text(import_name_node, source_code)

            # Use alias if present, otherwise use import name
            alias_name = self.parser.get_node_text(alias_name_node, source_code) if alias_name_node else import_name

            # Skip non-router imports
            if "router" not in import_name.lower():
                continue

            # Resolve module path to actual file
            source_file = self._resolve_import_to_file(module_name, file_path)
            if source_file:
                self.router_imports[alias_name] = (source_file, import_name)

    def _resolve_import_to_file(self, module_name: str, current_file: str) -> Optional[str]:
        """
        Resolve Python import path to actual file path.

        Handles:
        - Relative imports: .features.analytics -> features/analytics.py
        - Absolute imports: backend.api.features.analytics -> backend/api/features/analytics.py

        Args:
            module_name: Import module name (can be relative with dots)
            current_file: Path to current file (for resolving relative imports)

        Returns:
            Absolute path to the imported file, or None if not found
        """
        current_dir = os.path.dirname(current_file)

        # Handle relative imports
        if module_name.startswith("."):
            # Count leading dots
            # 1 dot = current package (no directory change)
            # 2 dots = parent package (go up 1 dir)
            # 3 dots = grandparent package (go up 2 dirs)
            dots = len(module_name) - len(module_name.lstrip("."))
            level = dots - 1  # Adjust: 1 dot = level 0, 2 dots = level 1, etc.
            module_parts = module_name.lstrip(".").split(".")

            # Go up 'level' directories
            target_dir = current_dir
            for _ in range(level):
                target_dir = os.path.dirname(target_dir)

            # Append module parts
            if module_parts and module_parts[0]:
                target_path = os.path.join(target_dir, *module_parts)
            else:
                target_path = target_dir

            # Try .py file
            if os.path.isfile(target_path + ".py"):
                return os.path.abspath(target_path + ".py")
            # Try __init__.py in directory
            if os.path.isdir(target_path):
                init_file = os.path.join(target_path, "__init__.py")
                if os.path.isfile(init_file):
                    return os.path.abspath(init_file)

        # Handle absolute imports (search from base_path)
        else:
            module_parts = module_name.split(".")
            # Try from base_path
            target_path = os.path.join(self.base_path, *module_parts)

            # Try .py file
            if os.path.isfile(target_path + ".py"):
                return os.path.abspath(target_path + ".py")
            # Try __init__.py in directory
            if os.path.isdir(target_path):
                init_file = os.path.join(target_path, "__init__.py")
                if os.path.isfile(init_file):
                    return os.path.abspath(init_file)

        return None

    def _extract_prefix_from_arguments(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract prefix parameter from APIRouter arguments.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            Prefix string or None
        """
        for child in args_node.children:
            if child.type == "keyword_argument":
                key_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    key_text = self.parser.get_node_text(key_node, source_code)
                    if key_text == "prefix":
                        if value_node.type == "string":
                            return self.parser.extract_string_value(value_node, source_code)

        return None

    def _extract_router_includes(self, file_path: str) -> None:
        """
        Extract router.include_router() and app.include_router() calls.

        Parses patterns like:
        router.include_router(organization_router, prefix="/orgs")
        app.include_router(router, prefix="/api")
        app.include_router(backend.api.features.v1.v1_router, tags=["v1"], prefix="/api")

        Extracts the prefix keyword argument and stores router->prefix mapping.

        Args:
            file_path: Path to Python file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for include_router calls: router.include_router(other_router, prefix="/api")
        include_query = """
        (expression_statement
          (call
            function: (attribute
              object: (identifier) @parent_router
              attribute: (identifier) @method_name)
            arguments: (argument_list) @args))
        """

        matches = self.parser.query(tree, include_query, "python")

        for match in matches:
            parent_router_node = match.get("parent_router")
            method_name_node = match.get("method_name")
            args_node = match.get("args")

            if not all([parent_router_node, method_name_node, args_node]):
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)
            if method_name != "include_router":
                continue

            parent_router_name = self.parser.get_node_text(parent_router_node, source_code)

            # Extract child router name from first positional argument
            child_router_name = None
            for child in args_node.children:
                # Handle: router_name, module.router_name, or backend.api.features.store.routes.router
                if child.type == "identifier":
                    child_router_name = self.parser.get_node_text(child, source_code)
                    break
                elif child.type == "attribute":
                    # For dotted names like backend.api.features.v1.v1_router
                    full_name = self.parser.get_node_text(child, source_code)
                    # Extract last component as router name
                    child_router_name = full_name.split(".")[-1]
                    break

            if not child_router_name:
                continue

            # Extract prefix from keyword arguments
            include_prefix = self._extract_prefix_from_arguments(args_node, source_code)

            # Store router->prefix mapping from include_router call
            if include_prefix:
                self.router_include_prefixes[child_router_name] = include_prefix

            # Legacy: Look up parent router prefix in current file
            parent_prefix = None
            if file_path in self.router_definitions:
                parent_prefix = self.router_definitions[file_path].get(parent_router_name)

            # Store the relationship (legacy)
            if parent_prefix is not None:
                if parent_prefix not in self.router_includes:
                    self.router_includes[parent_prefix] = {}
                self.router_includes[parent_prefix][child_router_name] = child_router_name

    def _get_router_prefix_for_file(self, file_path: str) -> Optional[str]:
        """
        Get the complete URL prefix chain for routes in a given file.

        Priority order:
        1. Prefix from include_router(alias, prefix="/api") via import resolution
        2. Prefix from include_router(router_name, prefix="/api") via direct name
        3. Prefix from APIRouter(prefix="/local") + global prefix
        4. Global prefix only

        Args:
            file_path: Absolute path to the file

        Returns:
            Full URL prefix (e.g., '/api/store') or None
        """
        # Normalize file path for comparison
        abs_file_path = os.path.abspath(file_path)

        # Check if this is the main router file (api.py, main.py, app.py)
        filename = file_path.split('/')[-1]
        if filename in ('api.py', 'main.py', 'app.py'):
            # Main router file only gets its own prefix (the global one)
            if file_path in self.router_definitions:
                file_routers = self.router_definitions[file_path]
                if file_routers:
                    return next(iter(file_routers.values()))
            return None

        # Check if this file has router definitions
        if file_path not in self.router_definitions:
            # No local router, apply only global prefix if available
            return self.global_prefix

        # Get the first router definition in the file
        file_routers = self.router_definitions[file_path]
        if not file_routers:
            return self.global_prefix

        router_name = next(iter(file_routers.keys()))
        local_prefix = file_routers[router_name]

        # Priority 1: Check if this router was imported with an alias and included with prefix
        # Look through router_imports to find aliases that point to this file
        for alias_name, (source_file, original_name) in self.router_imports.items():
            # Match by file path and original variable name
            if os.path.abspath(source_file) == abs_file_path and original_name == router_name:
                # Found an import alias for this router
                # Check if this alias has a prefix from include_router
                if alias_name in self.router_include_prefixes:
                    return self.router_include_prefixes[alias_name]

        # Priority 2: Check if this router was included with an explicit prefix using direct name
        if router_name in self.router_include_prefixes:
            return self.router_include_prefixes[router_name]

        # Priority 3: Compose global prefix + local prefix from APIRouter(prefix=...)
        if self.global_prefix:
            # Ensure prefixes are properly formatted
            global_part = self.global_prefix.rstrip("/")
            local_part = local_prefix.rstrip("/")
            if not global_part.startswith("/"):
                global_part = "/" + global_part
            if not local_part.startswith("/"):
                local_part = "/" + local_part
            return global_part + local_part

        # Priority 4: No global prefix, just return local
        return local_prefix

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a FastAPI file.

        Args:
            file_path: Path to Python file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return routes

        # Query for FastAPI route decorators: @app.get(), @router.post(), etc.
        route_query = """
        (decorated_definition
          (decorator
            (call
              function: (attribute
                object: (identifier) @obj_name
                attribute: (identifier) @method_name)
              arguments: (argument_list) @args))
          definition: (function_definition
            name: (identifier) @func_name))
        """

        route_matches = self.parser.query(tree, route_query, "python")

        # First, extract imports to resolve model references
        imports = self._extract_imports(tree, source_code, file_path)

        # Build a registry of Pydantic models (local + imported)
        # Collect local type aliases first (so we can pass to model parsing)
        local_type_aliases = self._find_local_type_aliases(tree, source_code)

        # Find enum classes and add to type aliases (StrEnum → string, IntEnum → integer)
        enum_classes = self._find_enum_classes(tree, source_code)

        # Resolve imported type aliases (only those that look like aliases - uppercase)
        imported_type_aliases = self._resolve_imported_type_aliases(imports, file_path)

        # Merge: local + enums + imported
        combined_type_aliases = {**local_type_aliases, **enum_classes, **imported_type_aliases}

        pydantic_models = self._find_pydantic_models_with_aliases(tree, source_code, combined_type_aliases)

        # Resolve imported models
        imported_models = self._resolve_imported_models(imports, file_path)
        pydantic_models.update(imported_models)

        # Second expansion pass with lazy import resolution
        # Pass imports dict so expansion can resolve on-demand
        pydantic_models = self._expand_nested_models_lazy(
            pydantic_models, combined_type_aliases, imports, file_path
        )

        for match in route_matches:
            obj_name_node = match.get("obj_name")
            method_name_node = match.get("method_name")
            args_node = match.get("args")
            func_name_node = match.get("func_name")

            if not method_name_node or not func_name_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's a valid HTTP method
            if method_name not in self.HTTP_METHODS:
                continue

            # Extract path from arguments
            path = None
            response_model_name = None
            decorator_metadata = {}
            if args_node:
                path = self._extract_path_from_arguments(args_node, source_code)
                response_model_name = self._extract_response_model(args_node, source_code)
                decorator_metadata = self._extract_decorator_metadata(args_node, source_code)

            if not path:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            location = self.parser.get_node_location(func_name_node)

            # Get the function definition node to analyze parameters
            # The function_definition is the sibling after the decorator
            func_def_node = None
            if func_name_node.parent and func_name_node.parent.type == "function_definition":
                func_def_node = func_name_node.parent

            # Extract function parameters for request body and query/header params
            metadata = {}
            if func_def_node:
                params_metadata = self._extract_function_parameters(
                    func_def_node, source_code, pydantic_models, imports, file_path
                )
                metadata.update(params_metadata)

            # Store pydantic models for later resolution of return types
            metadata["pydantic_models"] = pydantic_models
            metadata["type_aliases"] = combined_type_aliases
            metadata["imports"] = imports  # Store imports for lazy resolution

            # Add response model if present
            if response_model_name:
                # Track that response_model was specified (even if we couldn't resolve it)
                metadata["response_model_specified"] = True
                # Parse response_model (could be "list[Model]" or "Model")
                response_schema = self._parse_return_type_to_schema(
                    response_model_name, pydantic_models, imports, file_path
                )
                if response_schema:
                    metadata["response_model"] = response_schema

            # Add decorator metadata (summary, responses, etc)
            metadata.update(decorator_metadata)

            # Store responses dict for later processing
            if "responses" in decorator_metadata:
                metadata["response_codes"] = decorator_metadata["responses"]

            # Convert method name to HTTPMethod enum
            http_method = HTTPMethod[method_name.upper()]

            # Apply router prefix if available
            router_prefix = self._get_router_prefix_for_file(file_path)
            full_path = path
            if router_prefix:
                # Ensure prefix starts with / and doesn't end with /
                prefix = router_prefix.rstrip("/")
                if not prefix.startswith("/"):
                    prefix = "/" + prefix
                # Ensure path starts with /
                if not path.startswith("/"):
                    path = "/" + path
                full_path = prefix + path
            else:
                # Ensure path starts with /
                if not path.startswith("/"):
                    full_path = "/" + path

            route = Route(
                path=full_path,
                methods=[http_method],
                handler_name=func_name,
                framework=self.framework,
                raw_path=full_path,
                source_file=file_path,
                source_line=location["start_line"],
                metadata=metadata,
            )
            routes.append(route)

        return routes

    def _extract_path_from_arguments(self, args_node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract path string from arguments node.

        Args:
            args_node: argument_list node
            source_code: Source code bytes

        Returns:
            Path string or None
        """
        # First argument should be the path
        for child in args_node.children:
            if child.type == "string":
                return self.parser.extract_string_value(child, source_code)
            elif child.type == "identifier":
                # Could be a variable reference - for now skip
                continue

        return None

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from FastAPI path.

        FastAPI uses {param_name} or {param_name:type} syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all {param} patterns
        pattern = r"\{([^}:]+)(?::([^}]+))?\}"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)
            param_type = match.group(2) if match.group(2) else "string"

            # Map FastAPI types to OpenAPI types
            type_map = {
                "int": "integer",
                "float": "number",
                "str": "string",
                "bool": "boolean",
                "path": "string",
            }

            openapi_type = type_map.get(param_type, "string")

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type=openapi_type,
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize FastAPI path to OpenAPI format.

        FastAPI uses {param} which is already OpenAPI format.

        Args:
            path: FastAPI path

        Returns:
            Normalized path
        """
        # FastAPI already uses OpenAPI format
        return path

    def _find_pydantic_models_with_aliases(self, tree, source_code: bytes, type_aliases: Dict[str, str]) -> Dict[str, Schema]:
        """
        Find all Pydantic BaseModel classes in the file.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes
            type_aliases: Combined local + imported type aliases

        Returns:
            Dictionary mapping model names to Schema objects
        """
        models = {}

        # Query for classes inheriting from BaseModel
        model_query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses
          body: (block) @class_body)
        """

        matches = self.parser.query(tree, model_query, "python")

        for match in matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")
            class_body_node = match.get("class_body")

            if not all([class_name_node, superclasses_node, class_body_node]):
                continue

            # Check if it looks like a Pydantic model
            # Accept all classes that have superclasses - we'll filter later
            # This allows us to catch classes that inherit from other Pydantic models
            superclasses_text = self.parser.get_node_text(superclasses_node, source_code)

            # Skip common non-Pydantic base classes
            skip_patterns = ["Enum", "Exception", "Error", "TestCase", "ABC"]
            if any(pattern in superclasses_text for pattern in skip_patterns):
                continue

            # Accept if it has common Pydantic indicators OR other capital-case classes (likely models)
            pydantic_indicators = ["BaseModel", "Schema", "TimestampedSchema", "IDSchema", "Mixin"]
            has_pydantic_base = any(indicator in superclasses_text for indicator in pydantic_indicators)
            has_model_parent = bool(re.search(r'[A-Z][a-zA-Z0-9]*', superclasses_text))

            if not (has_pydantic_base or has_model_parent):
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Parse fields from class body
            schema = self._parse_pydantic_class_body(class_body_node, source_code, type_aliases)

            # Store parent class names for later inheritance resolution
            parent_names = []
            for child in superclasses_node.children:
                if child.type in ("identifier", "attribute"):
                    parent_name = self.parser.get_node_text(child, source_code)
                    # Extract just the class name (e.g., "module.Class" -> "Class")
                    if "." in parent_name:
                        parent_name = parent_name.split(".")[-1]
                    parent_names.append(parent_name)

            models[class_name] = {"schema": schema, "parents": parent_names}

        # Resolve inheritance - merge parent fields into child schemas
        resolved_models = self._resolve_model_inheritance(models)

        # Expand nested model references in properties
        expanded_models = self._expand_nested_models(resolved_models, type_aliases)

        return expanded_models

    def _extract_imports(
        self, tree, source_code: bytes, file_path: str
    ) -> Dict[str, str]:
        """
        Extract import statements to resolve model references.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes
            file_path: Path to current file

        Returns:
            Dictionary mapping imported names to module paths
            Example: {"CustomerSchema": "polar.customer.schemas.customer"}
        """
        imports = {}

        # Query for import_from_statement nodes
        import_query = "(import_from_statement) @import_stmt"

        matches = self.parser.query(tree, import_query, "python")

        for match in matches:
            import_node = match.get("import_stmt")
            if not import_node:
                continue

            # Get module name
            module_name_node = import_node.child_by_field_name("module_name")
            if not module_name_node:
                continue

            module_path = self.parser.get_node_text(module_name_node, source_code)

            # Handle relative imports: from .schemas import X or from ..module import Y
            if module_path.startswith("."):
                # Convert relative to absolute module path
                # e.g., from .schemas in polar/metrics/endpoints.py -> polar.metrics.schemas
                try:
                    current_dir = os.path.dirname(file_path)

                    # Count leading dots (1 = same package, 2 = parent package, etc.)
                    level = len(module_path) - len(module_path.lstrip("."))
                    remaining = module_path.lstrip(".")

                    # Start from current directory, go up (level-1) times
                    # (level=1 means same dir, so go up 0 times)
                    target_dir = current_dir
                    for _ in range(level - 1):
                        target_dir = os.path.dirname(target_dir)

                    # Find package root by walking up until no __init__.py in parent
                    package_root = target_dir
                    while True:
                        parent = os.path.dirname(package_root)
                        if not os.path.exists(os.path.join(parent, "__init__.py")):
                            break
                        package_root = parent

                    # Build module path from package_root to target_dir
                    rel_path = os.path.relpath(target_dir, os.path.dirname(package_root))
                    module_parts = rel_path.replace(os.sep, ".").split(".")

                    # Append remaining part of relative import
                    if remaining:
                        module_parts.append(remaining)

                    module_path = ".".join(module_parts)
                except Exception:
                    # Fallback: keep as-is if resolution fails
                    pass

            # For multi-line imports with parentheses, tree-sitter puts import names
            # as direct children of import_from_statement, not under a single "name" field
            # Example: from x import (a, b, c) -> children are: from, module, import, (, a, ,, b, ,, c, )

            # Collect all imported names from import_node children
            # Skip children before "import" keyword to avoid capturing module name
            imported_names = []
            seen_import_keyword = False
            for child in import_node.children:
                if child.type == "import":
                    seen_import_keyword = True
                    continue

                if not seen_import_keyword:
                    continue

                if child.type in ("dotted_name", "identifier"):
                    import_name = self.parser.get_node_text(child, source_code)
                    imported_names.append((import_name, import_name))  # (name, alias)
                elif child.type == "aliased_import":
                    actual_name_node = child.child_by_field_name("name")
                    alias_name_node = child.child_by_field_name("alias")
                    if actual_name_node and alias_name_node:
                        import_name = self.parser.get_node_text(actual_name_node, source_code)
                        alias_name = self.parser.get_node_text(alias_name_node, source_code)
                        imported_names.append((import_name, alias_name))

            # Add to imports dict
            for import_name, alias_name in imported_names:
                imports[alias_name] = f"{module_path}.{import_name}"

        return imports

    def _find_local_type_aliases(self, tree, source_code: bytes) -> Dict[str, str]:
        """
        Find type aliases defined in current file.

        Args:
            tree: Tree-sitter tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping alias names to resolved type strings
        """
        type_aliases = {}

        # Query for module-level assignments only (not inside functions/classes)
        # This avoids processing thousands of local variables
        query = """
        (module
          (expression_statement
            (assignment
              left: (identifier) @var_name
              right: (_) @value)))
        """
        matches = self.parser.query(tree, query, "python")

        count = 0
        max_aliases = 100  # Safety limit
        for match in matches:
            if count >= max_aliases:
                break
            count += 1
            var_name_node = match.get("var_name")
            value_node = match.get("value")

            if not var_name_node or not value_node:
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Only consider capitalized names (type aliases convention)
            if not var_name[0].isupper():
                continue

            value_text = self.parser.get_node_text(value_node, source_code)

            # Unwrap Annotated[T, ...] → T
            if value_text.startswith("Annotated["):
                start = value_text.find("[") + 1
                bracket_depth = 1
                i = start
                while i < len(value_text) and bracket_depth > 0:
                    if value_text[i] == "[":
                        bracket_depth += 1
                    elif value_text[i] == "]":
                        bracket_depth -= 1
                    elif value_text[i] == "," and bracket_depth == 1:
                        value_text = value_text[start:i].strip()
                        break
                    i += 1

            # Unwrap SkipJsonSchema[T] → T
            if value_text.startswith("SkipJsonSchema["):
                start = value_text.find("[") + 1
                end = value_text.rfind("]")
                value_text = value_text[start:end].strip()

            # For list[T] type aliases, store as-is
            # The _parse_type_annotation will handle list[T] resolution
            type_aliases[var_name] = value_text

        return type_aliases

    def _find_enum_classes(self, tree, source_code: bytes) -> Dict[str, str]:
        """
        Find enum classes and map to their base types.

        Args:
            tree: Tree-sitter tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping enum class names to base type (string/integer)
        """
        enums = {}

        # Query for class definitions
        query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses)
        """
        matches = self.parser.query(tree, query, "python")

        for match in matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")

            if not class_name_node or not superclasses_node:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)
            superclasses_text = self.parser.get_node_text(superclasses_node, source_code)

            # Check for enum base classes
            if "StrEnum" in superclasses_text:
                enums[class_name] = "string"
            elif "IntEnum" in superclasses_text:
                enums[class_name] = "integer"
            elif "Enum" in superclasses_text:
                # Generic Enum - default to string (most common)
                enums[class_name] = "string"

        return enums

    def _resolve_imported_type_aliases(
        self, imports: Dict[str, str], current_file_path: str
    ) -> Dict[str, str]:
        """
        Resolve imported type aliases to their underlying types.

        Args:
            imports: Dictionary mapping names to module paths
            current_file_path: Path to current file

        Returns:
            Dictionary mapping alias names to resolved type strings
        """
        type_aliases = {}

        # Limit processing to avoid performance issues
        count = 0
        max_imports = 50
        for alias_name, module_path in imports.items():
            if count >= max_imports:
                break
            count += 1

            # Module path format: "module.Class" for imports
            # For type aliases, strip last component to get module path
            # e.g., "polar.organization.schemas.OrganizationID" → "polar.organization.schemas"
            if "." in module_path:
                # Strip last component (the imported name)
                module_only = ".".join(module_path.split(".")[:-1])
            else:
                module_only = module_path

            # Try to resolve module to file
            file_path = self._resolve_module_to_file(module_only, current_file_path)
            if not file_path:
                continue

            try:
                source_code = self._read_file(file_path)
                if not source_code:
                    continue

                # Parse source to check if it's an enum or type alias
                tree = self.parser.parse_source(source_code, "python")
                if tree:
                    # Check if it's an enum class
                    enums = self._find_enum_classes(tree, source_code)
                    if alias_name in enums:
                        type_aliases[alias_name] = enums[alias_name]
                        continue

                    # Try to resolve as type alias
                    resolved_type = self._try_resolve_type_alias_inline(alias_name, source_code)
                    if resolved_type:
                        type_aliases[alias_name] = resolved_type

            except Exception:
                continue

        return type_aliases

    def _resolve_imported_models(
        self, imports: Dict[str, str], current_file_path: str, depth: int = 0, visited: set = None
    ) -> Dict[str, Schema]:
        """
        Resolve imported Pydantic models by parsing their source files.

        Follows re-export chains (barrel files).

        Args:
            imports: Dictionary mapping names to module paths
            current_file_path: Path to current file for relative resolution
            depth: Recursion depth (max 5 to prevent infinite loops)
            visited: Set of visited file paths to prevent cycles

        Returns:
            Dictionary mapping model names to Schema objects
        """
        if visited is None:
            visited = set()

        if depth > 5:  # Max chain depth
            return {}

        models = {}

        for model_name, module_path in imports.items():
            # Strip class name from module path to get file path
            # e.g., "polar.metrics.schemas.MetricDashboardSchema" -> "polar.metrics.schemas"
            if "." in module_path:
                module_only = ".".join(module_path.split(".")[:-1])
            else:
                module_only = module_path

            # Try to resolve the module path to a file path
            file_path = self._resolve_module_to_file(module_only, current_file_path)

            if not file_path:
                continue

            # Skip if already visited (cycle detection)
            if file_path in visited:
                continue

            visited.add(file_path)

            # Parse the file to extract Pydantic models
            try:
                source_code = self._read_file(file_path)
                if not source_code:
                    continue

                tree = self.parser.parse_source(source_code, "python")
                if not tree:
                    continue

                # Find all Pydantic models in the imported file
                # Get its local type aliases, enums, AND imported type aliases
                imported_file_imports = self._extract_imports(tree, source_code, file_path)
                imported_file_aliases = self._find_local_type_aliases(tree, source_code)
                imported_file_enums = self._find_enum_classes(tree, source_code)
                imported_file_imported_aliases = self._resolve_imported_type_aliases(imported_file_imports, file_path)
                imported_file_type_aliases = {**imported_file_aliases, **imported_file_enums, **imported_file_imported_aliases}
                imported_models = self._find_pydantic_models_with_aliases(tree, source_code, imported_file_type_aliases)

                # Add the specific imported model if it exists
                if model_name in imported_models:
                    models[model_name] = imported_models[model_name]
                else:
                    # Check if it's aliased - look for the actual class name
                    # Extract the class name from the module path
                    class_name = module_path.split(".")[-1]
                    if class_name in imported_models:
                        models[model_name] = imported_models[class_name]
                    else:
                        # Try to resolve type aliases (Annotated, Union, etc.)
                        type_alias_models = self._resolve_type_alias(
                            class_name, file_path, imported_models
                        )
                        if type_alias_models:
                            models[model_name] = type_alias_models
                        else:
                            # Check if re-exported - follow the chain
                            re_exports = self._extract_imports(tree, source_code, file_path)
                            if model_name in re_exports:
                                # Recursively follow re-export
                                re_export_path = re_exports[model_name]
                                chained_models = self._resolve_imported_models(
                                    {model_name: re_export_path},
                                    file_path,
                                    depth + 1,
                                    visited.copy()
                                )
                                if model_name in chained_models:
                                    models[model_name] = chained_models[model_name]

            except Exception:
                # Skip files that can't be parsed
                continue

        return models

    def _resolve_module_to_file(
        self, module_path: str, current_file_path: str
    ) -> Optional[str]:
        """
        Resolve a Python module path to a file path.

        Args:
            module_path: Module path like "polar.customer.schemas.customer" or ".schemas.customer"
            current_file_path: Current file path for relative resolution

        Returns:
            Resolved file path or None
        """
        import os
        from pathlib import Path

        # Handle relative imports (starting with .)
        if module_path.startswith("."):
            current_dir = Path(current_file_path).parent
            parts = module_path.lstrip(".").split(".") if module_path != "." else []

            # Count leading dots for parent directory traversal
            dot_count = len(module_path) - len(module_path.lstrip("."))

            # Go up the directory tree
            target_dir = current_dir
            for _ in range(dot_count - 1):
                target_dir = target_dir.parent

            # Build file path from remaining parts
            if parts:
                file_path = target_dir
                for part in parts[:-1]:
                    file_path = file_path / part

                # Last part could be a module or a class
                last_part = parts[-1]
                final_file = file_path / last_part

                # Try .py file
                if final_file.with_suffix(".py").exists():
                    return str(final_file.with_suffix(".py"))

                # Try as a package with __init__.py
                if (final_file / "__init__.py").exists():
                    return str(final_file / "__init__.py")

                # Try the parent directory as a .py file (last part might be a class name)
                if file_path.with_suffix(".py").exists():
                    return str(file_path.with_suffix(".py"))
            else:
                # Just "." - current directory's __init__.py
                if (target_dir / "__init__.py").exists():
                    return str(target_dir / "__init__.py")

            return None

        # Handle absolute imports
        else:
            # Try to find the module in the project
            # Start from current file and work backwards to find project root
            current_dir = Path(current_file_path).parent

            # Look for common project root indicators
            max_levels = 10
            for _ in range(max_levels):
                # Convert module path to file path
                parts = module_path.split(".")
                potential_file = current_dir / "/".join(parts)

                # Try .py file
                if potential_file.with_suffix(".py").exists():
                    return str(potential_file.with_suffix(".py"))

                # Try package with __init__.py
                if (potential_file / "__init__.py").exists():
                    return str(potential_file / "__init__.py")

                # Try one level up
                if current_dir.parent == current_dir:
                    break
                current_dir = current_dir.parent

        return None

    def _resolve_type_alias(
        self, alias_name: str, file_path: str, available_models: Dict[str, Schema]
    ) -> Optional[Schema]:
        """
        Resolve a type alias to its underlying Pydantic model.

        Handles patterns like:
        - CustomerResponse = Annotated[CustomerIndividual | CustomerTeam, ...]
        - UserSchema = Union[UserBase, UserExtended]

        Args:
            alias_name: Name of the type alias
            file_path: File where the alias is defined
            available_models: Already extracted models from the same file

        Returns:
            Schema object or None
        """
        try:
            source_code = self._read_file(file_path)
            if not source_code:
                return None

            tree = self.parser.parse_source(source_code, "python")
            if not tree:
                return None

            # Query for assignment statements: alias_name = ...
            query = """
            (assignment
              left: (identifier) @var_name
              right: (_) @value)
            """

            matches = self.parser.query(tree, query, "python")

            for match in matches:
                var_name_node = match.get("var_name")
                value_node = match.get("value")

                if not var_name_node or not value_node:
                    continue

                var_name = self.parser.get_node_text(var_name_node, source_code)

                if var_name == alias_name:
                    # Found the alias assignment - extract model names from the value
                    value_text = self.parser.get_node_text(value_node, source_code)

                    # Extract model names from union types and Annotated
                    model_names = self._extract_model_names_from_type(value_text)

                    # Return the first available model
                    for model_name in model_names:
                        if model_name in available_models:
                            return available_models[model_name]

        except Exception:
            pass

        return None

    def _resolve_model_inheritance(
        self, models_with_parents: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Schema]:
        """
        Resolve model inheritance by merging parent fields into child schemas.

        Args:
            models_with_parents: Dict mapping model names to {schema, parents} dicts

        Returns:
            Dict mapping model names to fully resolved Schema objects
        """
        resolved = {}

        def resolve_model(name: str, visited: set = None) -> Schema:
            """Recursively resolve a model's fields including inherited ones."""
            if visited is None:
                visited = set()

            if name in visited:
                # Circular dependency - return empty schema
                return Schema(type="object", properties={})

            if name in resolved:
                return resolved[name]

            if name not in models_with_parents:
                # Unknown model - return empty schema
                return Schema(type="object", properties={})

            visited.add(name)
            model_data = models_with_parents[name]
            schema = model_data["schema"]
            parents = model_data["parents"]

            # Start with current model's properties
            merged_properties = dict(schema.properties)
            merged_required = list(schema.required)

            # Merge parent properties (parents first, so child overrides)
            for parent_name in parents:
                parent_schema = resolve_model(parent_name, visited.copy())
                # Add parent properties that aren't overridden
                for prop_name, prop_value in parent_schema.properties.items():
                    if prop_name not in merged_properties:
                        merged_properties[prop_name] = prop_value

                # Merge required fields
                for req_field in parent_schema.required:
                    if req_field not in merged_required:
                        merged_required.append(req_field)

            # Create resolved schema
            resolved_schema = Schema(
                type=schema.type,
                properties=merged_properties,
                required=merged_required,
                description=schema.description,
            )

            resolved[name] = resolved_schema
            return resolved_schema

        # Resolve all models
        for name in models_with_parents:
            resolve_model(name)

        return resolved

    def _expand_schema_references(
        self,
        schema: Schema,
        models: Dict[str, Schema],
        type_aliases: Dict[str, str],
        imports: Dict[str, str] = None,
        file_path: str = None
    ) -> Schema:
        """
        Expand references in single schema (for request/response bodies).

        Args:
            schema: Schema to expand
            models: Available models
            type_aliases: Type aliases mapping
            imports: Import statements for lazy model resolution
            file_path: Current file path for import resolution

        Returns:
            Expanded schema
        """
        if not isinstance(schema, Schema):
            return schema

        # Handle array-type schemas (e.g., list[Model])
        if schema.type == "array" and schema.items:
            items = schema.items
            if isinstance(items, dict) and items.get("type") == "object":
                if "description" in items and items["description"].startswith("Reference: "):
                    model_name = items["description"].replace("Reference: ", "").strip()

                    # Try type alias first
                    if model_name in type_aliases:
                        resolved_type = type_aliases[model_name]
                        field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type, type_aliases)
                        resolved_items = {"type": field_type}
                        if format_spec:
                            resolved_items["format"] = format_spec
                        if items_schema:
                            resolved_items.update(items_schema)
                        return Schema(
                            type="array",
                            items=resolved_items,
                            required=schema.required if hasattr(schema, 'required') else None
                        )

                    # Try model
                    if model_name in models:
                        model_schema = models[model_name]
                        # Keep model_schema as Schema object (not dict) so properties are accessible
                        return Schema(
                            type="array",
                            items=model_schema if isinstance(model_schema, Schema) else model_schema,
                            required=schema.required if hasattr(schema, 'required') else None
                        )

                    # Lazy resolution: try to resolve from imports
                    if imports and file_path and model_name in imports:
                        resolved_models = self._resolve_imported_models({model_name: imports[model_name]}, file_path)
                        if model_name in resolved_models:
                            model_schema = resolved_models[model_name]
                            return Schema(
                                type="array",
                                items=model_schema if isinstance(model_schema, Schema) else model_schema,
                                required=schema.required if hasattr(schema, 'required') else None
                            )

        # Handle object-type schemas with properties
        if not schema.properties:
            return schema

        expanded_props = {}
        for prop_name, prop_schema in schema.properties.items():
            if isinstance(prop_schema, dict):
                prop_type = prop_schema.get("type")

                # Handle direct object reference
                if prop_type == "object" and "description" in prop_schema:
                    desc = prop_schema["description"]
                    if desc.startswith("Reference: "):
                        model_name = desc.replace("Reference: ", "").strip()

                        # Try type alias first
                        if model_name in type_aliases:
                            resolved_type = type_aliases[model_name]
                            field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type)
                            resolved_schema = {"type": field_type}
                            if format_spec:
                                resolved_schema["format"] = format_spec
                            if items_schema:
                                resolved_schema["items"] = items_schema
                            expanded_props[prop_name] = resolved_schema
                            continue

                        # Try model
                        if model_name in models:
                            model_schema = models[model_name]
                            schema_dict = model_schema.model_dump(exclude_none=True) if isinstance(model_schema, Schema) else model_schema
                            expanded_props[prop_name] = schema_dict
                            continue

                # Handle array items
                elif prop_type == "array" and "items" in prop_schema:
                    items = prop_schema["items"]
                    if isinstance(items, dict) and items.get("type") == "object":
                        if "description" in items and items["description"].startswith("Reference: "):
                            model_name = items["description"].replace("Reference: ", "").strip()

                            # Try type alias first
                            if model_name in type_aliases:
                                resolved_type = type_aliases[model_name]
                                field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type)
                                resolved_items = {"type": field_type}
                                if format_spec:
                                    resolved_items["format"] = format_spec
                                if items_schema:
                                    resolved_items.update(items_schema)
                                expanded_props[prop_name] = {
                                    "type": "array",
                                    "items": resolved_items
                                }
                                continue

                            # Try model
                            if model_name in models:
                                model_schema = models[model_name]
                                items_dict = model_schema.model_dump(exclude_none=True) if isinstance(model_schema, Schema) else model_schema
                                expanded_props[prop_name] = {
                                    "type": "array",
                                    "items": items_dict
                                }
                                continue

            expanded_props[prop_name] = prop_schema

        return Schema(
            type=schema.type,
            properties=expanded_props,
            required=schema.required if hasattr(schema, 'required') else None
        )

    def _expand_nested_models_lazy(
        self,
        models: Dict[str, Schema],
        local_type_aliases: Dict[str, str],
        imports: Dict[str, str],
        current_file_path: str
    ) -> Dict[str, Schema]:
        """
        Expand nested models with on-demand import resolution.

        Only resolves imported type aliases when actually referenced.

        Args:
            models: Dictionary of resolved models
            local_type_aliases: Local type aliases in same file
            imports: Import mapping for on-demand resolution
            current_file_path: Current file path

        Returns:
            Models with expanded nested references
        """
        # Cache for resolved imports (lazy population)
        resolved_imports_cache = {}

        def resolve_type_alias_on_demand(alias_name: str) -> Optional[str]:
            """Resolve type alias on-demand from local or imports."""
            # Check local first
            if alias_name in local_type_aliases:
                return local_type_aliases[alias_name]

            # Check cache
            if alias_name in resolved_imports_cache:
                return resolved_imports_cache[alias_name]

            # Check if imported
            if alias_name in imports:
                module_path = imports[alias_name]
                file_path = self._resolve_module_to_file(module_path, current_file_path)
                if file_path:
                    try:
                        source_code = self._read_file(file_path)
                        if source_code:
                            # Check if it's an enum class
                            tree = self.parser.parse_source(source_code, "python")
                            if tree:
                                enums = self._find_enum_classes(tree, source_code)
                                if alias_name in enums:
                                    resolved_imports_cache[alias_name] = enums[alias_name]
                                    return enums[alias_name]

                            # Try type alias
                            resolved = self._try_resolve_type_alias_inline(alias_name, source_code)
                            if resolved:
                                resolved_imports_cache[alias_name] = resolved
                                return resolved
                    except Exception:
                        pass

            return None

        def expand_schema(schema: Schema, visited: set = None) -> Schema:
            """Recursively expand nested model refs."""
            if visited is None:
                visited = set()

            if not isinstance(schema, Schema) or not schema.properties:
                return schema

            expanded_props = {}
            for prop_name, prop_schema in schema.properties.items():
                if isinstance(prop_schema, dict):
                    prop_type = prop_schema.get("type")

                    # Handle direct object reference
                    if prop_type == "object" and "description" in prop_schema:
                        desc = prop_schema["description"]
                        if desc.startswith("Reference: "):
                            model_name = desc.replace("Reference: ", "").strip()

                            # Try to resolve as type alias (on-demand)
                            resolved_type = resolve_type_alias_on_demand(model_name)
                            if resolved_type:
                                # Parse resolved type to get proper schema
                                field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type)
                                resolved_schema = {"type": field_type}
                                if format_spec:
                                    resolved_schema["format"] = format_spec
                                if items_schema:
                                    resolved_schema["items"] = items_schema
                                expanded_props[prop_name] = resolved_schema
                                continue

                            # Try as model
                            if model_name in models and model_name not in visited:
                                visited.add(model_name)
                                expanded_schema = expand_schema(models[model_name], visited.copy())
                                schema_dict = expanded_schema.model_dump(exclude_none=True) if isinstance(expanded_schema, Schema) else expanded_schema
                                expanded_props[prop_name] = schema_dict
                                continue

                            # Try to import model on-demand
                            if model_name in imports and model_name not in visited:
                                module_path = imports[model_name]
                                file_path = self._resolve_module_to_file(module_path, current_file_path)
                                if file_path:
                                    try:
                                        source_code = self._read_file(file_path)
                                        if source_code:
                                            tree = self.parser.parse_source(source_code, "python")
                                            if tree:
                                                # Get type aliases + enums for imported file (including its imports)
                                                imported_file_imports = self._extract_imports(tree, source_code, file_path)
                                                imported_aliases = self._find_local_type_aliases(tree, source_code)
                                                imported_enums = self._find_enum_classes(tree, source_code)
                                                imported_from_imports = self._resolve_imported_type_aliases(imported_file_imports, file_path)
                                                imported_type_aliases = {**imported_aliases, **imported_enums, **imported_from_imports}
                                                imported_models = self._find_pydantic_models_with_aliases(tree, source_code, imported_type_aliases)

                                                if model_name in imported_models:
                                                    visited.add(model_name)
                                                    expanded_schema = expand_schema(imported_models[model_name], visited.copy())
                                                    schema_dict = expanded_schema.model_dump(exclude_none=True) if isinstance(expanded_schema, Schema) else expanded_schema
                                                    expanded_props[prop_name] = schema_dict
                                                    continue
                                    except Exception:
                                        pass

                    # Handle array with object items
                    elif prop_type == "array" and "items" in prop_schema:
                        items = prop_schema["items"]
                        if isinstance(items, dict) and items.get("type") == "object":
                            if "description" in items and items["description"].startswith("Reference: "):
                                model_name = items["description"].replace("Reference: ", "").strip()

                                # Try to resolve as type alias (on-demand)
                                resolved_type = resolve_type_alias_on_demand(model_name)
                                if resolved_type:
                                    field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type)
                                    resolved_items = {"type": field_type}
                                    if format_spec:
                                        resolved_items["format"] = format_spec
                                    if items_schema:
                                        resolved_items.update(items_schema)
                                    expanded_props[prop_name] = {
                                        "type": "array",
                                        "items": resolved_items
                                    }
                                    continue

                                # Try as model
                                if model_name in models and model_name not in visited:
                                    visited.add(model_name)
                                    expanded_items = expand_schema(models[model_name], visited.copy())
                                    items_dict = expanded_items.model_dump(exclude_none=True) if isinstance(expanded_items, Schema) else expanded_items
                                    expanded_props[prop_name] = {
                                        "type": "array",
                                        "items": items_dict
                                    }
                                    continue

                                # Try to import model on-demand
                                if model_name in imports and model_name not in visited:
                                    module_path = imports[model_name]
                                    file_path = self._resolve_module_to_file(module_path, current_file_path)
                                    if file_path:
                                        try:
                                            source_code = self._read_file(file_path)
                                            if source_code:
                                                tree = self.parser.parse_source(source_code, "python")
                                                if tree:
                                                    imported_file_imports = self._extract_imports(tree, source_code, file_path)
                                                    imported_aliases = self._find_local_type_aliases(tree, source_code)
                                                    imported_enums = self._find_enum_classes(tree, source_code)
                                                    imported_from_imports = self._resolve_imported_type_aliases(imported_file_imports, file_path)
                                                    imported_type_aliases = {**imported_aliases, **imported_enums, **imported_from_imports}
                                                    imported_models = self._find_pydantic_models_with_aliases(tree, source_code, imported_type_aliases)

                                                    if model_name in imported_models:
                                                        visited.add(model_name)
                                                        expanded_items = expand_schema(imported_models[model_name], visited.copy())
                                                        items_dict = expanded_items.model_dump(exclude_none=True) if isinstance(expanded_items, Schema) else expanded_items
                                                        expanded_props[prop_name] = {
                                                            "type": "array",
                                                            "items": items_dict
                                                        }
                                                        continue
                                        except Exception:
                                            pass

                expanded_props[prop_name] = prop_schema

            return Schema(
                type=schema.type,
                properties=expanded_props,
                required=schema.required if hasattr(schema, 'required') else None
            )

        # Expand all models
        expanded = {}
        for name, schema in models.items():
            expanded[name] = expand_schema(schema, set())

        return expanded

    def _expand_nested_models(self, models: Dict[str, Schema], type_aliases: Dict[str, str] = None) -> Dict[str, Schema]:
        """
        Expand nested model references in property schemas.

        Replaces object placeholders with actual nested model schemas.
        Handles: periods: list[MetricsPeriod], totals: MetricsTotals

        Args:
            models: Dictionary of resolved models
            type_aliases: Dictionary mapping alias names to resolved types

        Returns:
            Models with expanded nested references
        """
        if type_aliases is None:
            type_aliases = {}
        def expand_schema(schema: Schema, visited: set = None) -> Schema:
            """Recursively expand nested model refs."""
            if visited is None:
                visited = set()

            if not isinstance(schema, Schema) or not schema.properties:
                return schema

            expanded_props = {}
            for prop_name, prop_schema in schema.properties.items():
                if isinstance(prop_schema, dict):
                    prop_type = prop_schema.get("type")

                    # Handle direct object reference
                    if prop_type == "object" and "description" in prop_schema:
                        desc = prop_schema["description"]
                        # Check for "Reference: ModelName" pattern
                        if desc.startswith("Reference: "):
                            model_name = desc.replace("Reference: ", "").strip()

                            # Try to resolve as type alias first
                            if model_name in type_aliases:
                                # Resolve alias and re-parse
                                resolved_type = type_aliases[model_name]
                                # Parse resolved type to get proper schema
                                field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type)
                                resolved_schema = {"type": field_type}
                                if format_spec:
                                    resolved_schema["format"] = format_spec
                                if items_schema:
                                    resolved_schema["items"] = items_schema
                                expanded_props[prop_name] = resolved_schema
                                continue

                            if model_name in models and model_name not in visited:
                                # Expand nested model
                                visited.add(model_name)
                                expanded_schema = expand_schema(models[model_name], visited.copy())
                                # Convert Schema to dict
                                schema_dict = expanded_schema.model_dump(exclude_none=True) if isinstance(expanded_schema, Schema) else expanded_schema
                                expanded_props[prop_name] = schema_dict
                                continue

                    # Handle array with object items
                    elif prop_type == "array" and "items" in prop_schema:
                        items = prop_schema["items"]
                        if isinstance(items, dict) and items.get("type") == "object":
                            # Check items description for model reference
                            if "description" in items and items["description"].startswith("Reference: "):
                                model_name = items["description"].replace("Reference: ", "").strip()

                                # Try to resolve as type alias first
                                if model_name in type_aliases:
                                    resolved_type = type_aliases[model_name]
                                    field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(resolved_type)
                                    resolved_items = {"type": field_type}
                                    if format_spec:
                                        resolved_items["format"] = format_spec
                                    if items_schema:
                                        resolved_items.update(items_schema)
                                    expanded_props[prop_name] = {
                                        "type": "array",
                                        "items": resolved_items
                                    }
                                    continue

                                if model_name in models and model_name not in visited:
                                    visited.add(model_name)
                                    expanded_items = expand_schema(models[model_name], visited.copy())
                                    # Convert Schema to dict for OpenAPI builder
                                    items_dict = expanded_items.model_dump(exclude_none=True) if isinstance(expanded_items, Schema) else expanded_items
                                    expanded_props[prop_name] = {
                                        "type": "array",
                                        "items": items_dict
                                    }
                                    continue

                expanded_props[prop_name] = prop_schema

            return Schema(
                type=schema.type,
                properties=expanded_props,
                required=schema.required if hasattr(schema, 'required') else None
            )

        # Expand all models
        expanded = {}
        for name, schema in models.items():
            expanded[name] = expand_schema(schema, set())

        return expanded

    def _extract_model_names_from_type(self, type_expr: str) -> List[str]:
        """
        Extract model class names from a type expression.

        Examples:
        - "Annotated[CustomerIndividual | CustomerTeam, ...]" -> ["CustomerIndividual", "CustomerTeam"]
        - "Union[UserBase, UserExtended]" -> ["UserBase", "UserExtended"]
        - "CustomerBase" -> ["CustomerBase"]

        Args:
            type_expr: Type expression string

        Returns:
            List of model class names
        """
        import re

        # Remove Annotated wrapper
        type_expr = re.sub(r'Annotated\s*\[', '', type_expr)

        # Remove Optional/Union wrappers
        type_expr = re.sub(r'(Optional|Union)\s*\[', '', type_expr)

        # Extract identifiers (class names) - match capitalized words
        # This pattern matches Python class names (PascalCase identifiers)
        pattern = r'\b([A-Z][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, type_expr)

        # Filter out common type annotation keywords
        keywords = {'Union', 'Optional', 'Annotated', 'List', 'Dict', 'Set', 'Tuple',
                   'Any', 'Literal', 'Final', 'ClassVar', 'Discriminator', 'Field', 'Tag'}

        model_names = [m for m in matches if m not in keywords]

        return model_names

    def _parse_pydantic_class_body(self, class_body_node: Node, source_code: bytes, type_aliases: Dict[str, str] = None) -> Schema:
        """
        Parse Pydantic model fields from class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes
            type_aliases: Optional dict of type aliases for resolution

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for typed assignments: name: str, age: Optional[int] = None
        for child in class_body_node.children:
            if child.type == "expression_statement":
                # Check if it's a typed assignment
                for expr_child in child.children:
                    if expr_child.type == "assignment":
                        field_info = self._parse_pydantic_field(expr_child, source_code, type_aliases)
                        if field_info:
                            name, field_schema, is_required = field_info
                            properties[name] = field_schema
                            if is_required:
                                required.append(name)
                    elif expr_child.type == "type_alias_statement":
                        # Handle: name: str (no default value)
                        field_info = self._parse_type_alias(expr_child, source_code, type_aliases)
                        if field_info:
                            name, field_schema, is_required = field_info
                            properties[name] = field_schema
                            if is_required:
                                required.append(name)

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _parse_pydantic_field(
        self, assignment_node: Node, source_code: bytes, type_aliases: Dict[str, str] = None
    ) -> Optional[tuple]:
        """
        Parse a Pydantic field definition.

        Args:
            assignment_node: Assignment node
            source_code: Source code bytes
            type_aliases: Optional dict of type aliases for resolution

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        # Get left side (annotated_assignment with name and type)
        left = assignment_node.child_by_field_name("left")
        if not left or left.type != "identifier":
            return None

        field_name = self.parser.get_node_text(left, source_code)

        # Get type annotation
        type_node = assignment_node.child_by_field_name("type")
        if not type_node:
            return None

        type_text = self.parser.get_node_text(type_node, source_code)

        # Try to resolve type alias in same file (e.g., OrganizationID = Annotated[UUID4, ...])
        # Do this before parsing so _parse_type_annotation sees the resolved type
        resolved_type = self._try_resolve_type_alias_inline(type_text, source_code)
        if resolved_type:
            type_text = resolved_type
            # Recursively resolve if still a type alias
            max_depth = 5
            for _ in range(max_depth):
                next_resolved = self._try_resolve_type_alias_inline(type_text, source_code)
                if not next_resolved or next_resolved == type_text:
                    break
                type_text = next_resolved

        field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(type_text, type_aliases)

        # Check if there's a default value
        right = assignment_node.child_by_field_name("right")
        has_default = right is not None

        # Field is required if it's not Optional and has no default
        is_required = not is_optional and not has_default

        field_schema = {"type": field_type}
        if format_spec:
            field_schema["format"] = format_spec
        if items_schema:
            field_schema["items"] = items_schema

        # Store model reference for object types
        if field_type == "object" and type_text and type_text[0].isupper():
            # Extract base type without Optional/Union wrappers
            base_type = type_text
            if "Optional[" in base_type:
                base_type = base_type[base_type.find("[")+1:base_type.rfind("]")]
            elif "|" in base_type:
                parts = [p.strip() for p in base_type.split("|") if p.strip() != "None"]
                base_type = parts[0] if parts else base_type
            field_schema["description"] = f"Reference: {base_type.strip()}"

        return (field_name, field_schema, is_required)

    def _try_resolve_type_alias_inline(self, type_text: str, source_code: bytes) -> Optional[str]:
        """
        Try to resolve type alias by finding its definition in same file.

        Example:
          OrganizationID = Annotated[UUID4, ...]
          If type_text == "OrganizationID", returns "UUID4"

        Args:
            type_text: Type annotation text (e.g., "OrganizationID")
            source_code: Source code of current file

        Returns:
            Resolved innermost type or None
        """
        # Skip if already a known builtin or contains brackets (already resolved)
        if "[" in type_text or type_text in ("str", "int", "float", "bool", "dict", "list"):
            return None

        # Extract base type name
        type_name = type_text.strip()
        if "|" in type_name:
            parts = [p.strip() for p in type_name.split("|") if p.strip() != "None"]
            type_name = parts[0] if parts else type_name

        # Parse source to find assignment
        try:
            tree = self.parser.parse_source(source_code, "python")
            if not tree:
                return None

            # Query for assignment: TypeName = ...
            query = """
            (assignment
              left: (identifier) @var_name
              right: (_) @value)
            """
            matches = self.parser.query(tree, query, "python")

            for match in matches:
                var_name_node = match.get("var_name")
                value_node = match.get("value")

                if not var_name_node or not value_node:
                    continue

                var_name = self.parser.get_node_text(var_name_node, source_code)

                if var_name == type_name:
                    # Found type alias assignment - extract value
                    value_text = self.parser.get_node_text(value_node, source_code)

                    # Unwrap Annotated[T, ...] → T
                    if value_text.startswith("Annotated["):
                        # Extract first type argument
                        start = value_text.find("[") + 1
                        bracket_depth = 1
                        i = start
                        while i < len(value_text) and bracket_depth > 0:
                            if value_text[i] == "[":
                                bracket_depth += 1
                            elif value_text[i] == "]":
                                bracket_depth -= 1
                            elif value_text[i] == "," and bracket_depth == 1:
                                value_text = value_text[start:i].strip()
                                break
                            i += 1

                    # Unwrap SkipJsonSchema[T] → T
                    if value_text.startswith("SkipJsonSchema["):
                        start = value_text.find("[") + 1
                        end = value_text.rfind("]")
                        value_text = value_text[start:end].strip()

                    return value_text

        except Exception:
            pass

        return None

    def _parse_type_alias(self, type_alias_node: Node, source_code: bytes, type_aliases: Dict[str, str] = None) -> Optional[tuple]:
        """
        Parse a type alias statement (field without default value).

        Args:
            type_alias_node: Type alias node
            source_code: Source code bytes
            type_aliases: Optional dict of type aliases for resolution

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        field_name_node = type_alias_node.child_by_field_name("name")
        type_node = type_alias_node.child_by_field_name("value")

        if not field_name_node or not type_node:
            return None

        field_name = self.parser.get_node_text(field_name_node, source_code)
        type_text = self.parser.get_node_text(type_node, source_code)

        # Try to resolve type alias
        resolved_type = self._try_resolve_type_alias_inline(type_text, source_code)
        if resolved_type:
            type_text = resolved_type
            # Recursively resolve if still a type alias
            max_depth = 5
            for _ in range(max_depth):
                next_resolved = self._try_resolve_type_alias_inline(type_text, source_code)
                if not next_resolved or next_resolved == type_text:
                    break
                type_text = next_resolved

        field_type, is_optional, items_schema, format_spec = self._parse_type_annotation(type_text, type_aliases)

        # No default value, so required unless Optional
        is_required = not is_optional

        field_schema = {"type": field_type}
        if format_spec:
            field_schema["format"] = format_spec
        if items_schema:
            field_schema["items"] = items_schema

        # Store model reference for object types
        if field_type == "object" and type_text and type_text[0].isupper():
            base_type = type_text
            if "Optional[" in base_type:
                base_type = base_type[base_type.find("[")+1:base_type.rfind("]")]
            elif "|" in base_type:
                parts = [p.strip() for p in base_type.split("|") if p.strip() != "None"]
                base_type = parts[0] if parts else base_type
            field_schema["description"] = f"Reference: {base_type.strip()}"

        return (field_name, field_schema, is_required)

    def _parse_type_annotation(self, type_text: str, type_aliases: Dict[str, str] = None) -> tuple:
        """
        Parse Python type annotation to OpenAPI type.

        Args:
            type_text: Type annotation text
            type_aliases: Optional dict of type aliases to resolve before falling back to object

        Returns:
            Tuple of (openapi_type, is_optional, items_schema, format_spec)
            items_schema is dict for array items or None
            format_spec is format string or None
        """
        import re

        is_optional = "Optional" in type_text or "None" in type_text

        # Extract base type
        if "Optional[" in type_text:
            # Extract type from Optional[Type]
            start = type_text.find("[") + 1
            end = type_text.rfind("]")
            base_type = type_text[start:end].strip()
        elif "|" in type_text and "None" in type_text:
            # Handle Union syntax: str | None
            parts = [p.strip() for p in type_text.split("|")]
            base_type = next((p for p in parts if p != "None"), "str")
        else:
            base_type = type_text.strip()

        # Unwrap Annotated[T, ...] and SkipJsonSchema[T] patterns
        # Annotated[UUID4, ...] → UUID4
        # SkipJsonSchema[str] → str
        if base_type.startswith("Annotated["):
            # Extract first type argument
            start = base_type.find("[") + 1
            # Find matching bracket, accounting for nested brackets
            bracket_depth = 1
            i = start
            while i < len(base_type) and bracket_depth > 0:
                if base_type[i] == "[":
                    bracket_depth += 1
                elif base_type[i] == "]":
                    bracket_depth -= 1
                elif base_type[i] == "," and bracket_depth == 1:
                    # Found first comma at top level
                    base_type = base_type[start:i].strip()
                    break
                i += 1
        elif base_type.startswith("SkipJsonSchema["):
            # Extract inner type
            start = base_type.find("[") + 1
            end = base_type.rfind("]")
            base_type = base_type[start:end].strip()

        # Handle Union types after unwrapping: A | B
        # Parse first variant only (simplification - full oneOf support needs more work)
        if "|" in base_type:
            # Split on | and take first non-None variant
            parts = [p.strip() for p in base_type.split("|")]
            # Filter out None, take first variant
            variants = [p for p in parts if p != "None"]
            if variants:
                # Recursively parse first variant
                return self._parse_type_annotation(variants[0], type_aliases)

        # Map Python types to OpenAPI types
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "List": "array",
            "dict": "object",
            "Dict": "object",
            # Pydantic types with format
            "UUID4": ("string", "uuid"),
            "UUID": ("string", "uuid"),
            "EmailStr": ("string", "email"),
            "EmailStrDNS": ("string", "email"),
            "HttpUrl": ("string", "uri"),
            "AnyHttpUrl": ("string", "uri"),
            "AnyUrl": ("string", "uri"),
            "datetime": ("string", "date-time"),
            "date": ("string", "date"),
            "time": ("string", "time"),
            "Decimal": ("number", None),
            "IPvAnyAddress": ("string", "ipvanyaddress"),
            # Common type aliases
            "StrEnum": ("string", None),
            "IntEnum": ("integer", None),
        }

        # Check for List[T] pattern and extract inner type
        list_match = re.match(r'(?:list|List)\[(.+)\]', base_type)
        if list_match:
            inner_type = list_match.group(1).strip()

            # Unwrap SkipJsonSchema[T] in array items
            if inner_type.startswith("SkipJsonSchema["):
                start = inner_type.find("[") + 1
                end = inner_type.rfind("]")
                inner_type = inner_type[start:end].strip()

            # Check type_aliases first (for enums, type aliases)
            if type_aliases and inner_type in type_aliases:
                resolved_inner = type_aliases[inner_type]
                # Recursively parse resolved inner type
                inner_openapi_type, _, _, inner_format = self._parse_type_annotation(resolved_inner, type_aliases)
                items_schema = {"type": inner_openapi_type}
                if inner_format:
                    items_schema["format"] = inner_format
                return ("array", is_optional, items_schema, None)

            # Map inner type to OpenAPI type
            inner_mapping = type_map.get(inner_type)
            if inner_mapping:
                if isinstance(inner_mapping, tuple):
                    inner_openapi, inner_format = inner_mapping
                    items_schema = {"type": inner_openapi}
                    if inner_format:
                        items_schema["format"] = inner_format
                else:
                    items_schema = {"type": inner_mapping}
            else:
                # Likely a model reference (e.g., list[MetricsPeriod])
                items_schema = {"type": "object", "description": f"Reference: {inner_type}"}
            return ("array", is_optional, items_schema, None)

        # Check for Literal types: Literal["a", "b"] -> string with enum
        if base_type.startswith("Literal["):
            # Map to string type (simplification - could infer type from values)
            return ("string", is_optional, None, None)

        # Check if base type is a known type or model reference
        type_mapping = type_map.get(base_type)
        if type_mapping:
            if isinstance(type_mapping, tuple):
                # Type with format specification (e.g., UUID4 -> ("string", "uuid"))
                openapi_type, format_spec = type_mapping
                return (openapi_type, is_optional, None, format_spec)
            else:
                # Simple type mapping (e.g., str -> "string")
                return (type_mapping, is_optional, None, None)

        # Unknown type - check if it looks like a model name (starts with uppercase)
        if base_type and base_type[0].isupper():
            # Check type_aliases first
            if type_aliases and base_type in type_aliases:
                resolved = type_aliases[base_type]
                # Recursively parse resolved type
                return self._parse_type_annotation(resolved, type_aliases)

            # Store as object reference for later expansion
            return ("object", is_optional, None, None)

        return ("string", is_optional, None, None)

    def _extract_response_model(
        self, args_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Extract response_model from decorator arguments.

        Args:
            args_node: Arguments node
            source_code: Source code bytes

        Returns:
            Response model class name or None
        """
        for child in args_node.children:
            if child.type == "keyword_argument":
                key_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    key_text = self.parser.get_node_text(key_node, source_code)
                    if key_text == "response_model":
                        return self.parser.get_node_text(value_node, source_code)

        return None

    def _extract_decorator_metadata(
        self, args_node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Extract metadata from decorator arguments (summary, responses, etc).

        Args:
            args_node: Arguments node
            source_code: Source code bytes

        Returns:
            Dictionary with decorator metadata
        """
        metadata = {}

        for child in args_node.children:
            if child.type == "keyword_argument":
                key_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if not key_node or not value_node:
                    continue

                key_text = self.parser.get_node_text(key_node, source_code)

                # Extract summary
                if key_text == "summary":
                    if value_node.type == "string":
                        metadata["summary"] = self.parser.extract_string_value(value_node, source_code)

                # Extract responses dict
                elif key_text == "responses":
                    if value_node.type == "dictionary":
                        responses = self._extract_responses_dict(value_node, source_code)
                        if responses:
                            metadata["responses"] = responses

        return metadata

    def _extract_responses_dict(
        self, dict_node: Node, source_code: bytes
    ) -> Dict[str, str]:
        """
        Extract responses dictionary from decorator.
        Example: responses={404: NotFoundError, 400: BadRequestError}

        Args:
            dict_node: Dictionary node
            source_code: Source code bytes

        Returns:
            Dictionary mapping status codes to model names
        """
        responses = {}

        for child in dict_node.children:
            if child.type == "pair":
                key_node = child.child_by_field_name("key")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    # Status code (usually an integer)
                    status_code = self.parser.get_node_text(key_node, source_code)
                    # Model name (identifier)
                    model_name = self.parser.get_node_text(value_node, source_code)
                    responses[status_code] = model_name

        return responses

    def _extract_function_parameters(
        self, func_def_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema],
        imports: Dict[str, str] = None, file_path: str = None
    ) -> Dict[str, Any]:
        """
        Extract function parameters to identify request body and query/header params.
        Also extracts return type annotation.

        Args:
            func_def_node: Function definition node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models
            imports: Import statements for lazy model resolution
            file_path: Current file path for import resolution

        Returns:
            Dictionary with request_body, query_params, header_params, return_type
        """
        metadata = {}
        query_params = []
        header_params = []

        # Get parameters node
        params_node = func_def_node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type in ("typed_parameter", "typed_default_parameter"):
                    param_info = self._analyze_parameter(
                        param, source_code, pydantic_models, imports, file_path
                    )
                    if param_info:
                        param_type, param_data = param_info
                        if param_type == "body":
                            metadata["request_body"] = param_data
                        elif param_type == "query":
                            query_params.append(param_data)
                        elif param_type == "header":
                            header_params.append(param_data)

        if query_params:
            metadata["query_params"] = query_params
        if header_params:
            metadata["header_params"] = header_params

        # Extract return type annotation
        return_type_node = func_def_node.child_by_field_name("return_type")
        if return_type_node:
            return_type = self.parser.get_node_text(return_type_node, source_code)
            # Store the return type name for later use
            metadata["return_type"] = return_type

        return metadata

    def _analyze_parameter(
        self, param_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema],
        imports: Dict[str, str] = None, file_path: str = None
    ) -> Optional[tuple]:
        """
        Analyze a function parameter to determine its type.

        Args:
            param_node: Parameter node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models
            imports: Import statements for lazy model resolution
            file_path: Current file path for import resolution

        Returns:
            Tuple of (param_type, param_data) or None
        """
        # Get parameter name and type from children
        # Structure: identifier : type or identifier : type = default
        name_node = None
        type_node = None

        for child in param_node.children:
            if child.type == "identifier" and not name_node:
                name_node = child
            elif child.type == "type":
                type_node = child

        if not name_node or not type_node:
            return None

        param_name = self.parser.get_node_text(name_node, source_code)
        type_text = self.parser.get_node_text(type_node, source_code)

        # Check if type is a Pydantic model (request body)
        if type_text in pydantic_models:
            return ("body", pydantic_models[type_text])

        # Lazy resolution: try to resolve from imports
        if imports and file_path and type_text in imports:
            resolved_models = self._resolve_imported_models({type_text: imports[type_text]}, file_path)
            if type_text in resolved_models:
                return ("body", resolved_models[type_text])

        # Check for Query/Header default values
        if param_node.type == "typed_default_parameter":
            # Find the default value (after =)
            default_node = None
            for child in param_node.children:
                if child.type == "call":
                    default_node = child
                    break

            if default_node:
                default_text = self.parser.get_node_text(default_node, source_code)

                # Check for Query(...)
                if default_text.startswith("Query("):
                    param_data = self._parse_query_parameter(
                        param_name, type_text, default_text
                    )
                    return ("query", param_data)

                # Check for Header(...)
                if default_text.startswith("Header("):
                    param_data = self._parse_header_parameter(
                        param_name, type_text, default_text
                    )
                    return ("header", param_data)

        return None

    def _parse_query_parameter(
        self, param_name: str, type_text: str, default_text: str
    ) -> Parameter:
        """
        Parse a Query parameter.

        Args:
            param_name: Parameter name
            type_text: Type annotation
            default_text: Default value text (Query(...))

        Returns:
            Parameter object
        """
        param_type, _, _, _ = self._parse_type_annotation(type_text)

        # Extract description from Query(..., description="...")
        description = None
        if 'description="' in default_text:
            start = default_text.find('description="') + len('description="')
            end = default_text.find('"', start)
            description = default_text[start:end]
        elif "description='" in default_text:
            start = default_text.find("description='") + len("description='")
            end = default_text.find("'", start)
            description = default_text[start:end]

        # Check if required (Query(...) vs Query with default)
        required = "..." in default_text.split(",")[0]

        return Parameter(
            name=param_name,
            location=ParameterLocation.QUERY,
            type=param_type,
            required=required,
            description=description,
        )

    def _parse_header_parameter(
        self, param_name: str, type_text: str, default_text: str
    ) -> Parameter:
        """
        Parse a Header parameter.

        Args:
            param_name: Parameter name
            type_text: Type annotation
            default_text: Default value text (Header(...))

        Returns:
            Parameter object
        """
        param_type, _, _, _ = self._parse_type_annotation(type_text)

        # Extract description from Header(..., description="...")
        description = None
        if 'description="' in default_text:
            start = default_text.find('description="') + len('description="')
            end = default_text.find('"', start)
            description = default_text[start:end]
        elif "description='" in default_text:
            start = default_text.find("description='") + len("description='")
            end = default_text.find("'", start)
            description = default_text[start:end]

        # Check if required
        required = "..." in default_text.split(",")[0]

        return Parameter(
            name=param_name,
            location=ParameterLocation.HEADER,
            type=param_type,
            required=required,
            description=description,
        )

    def _parse_return_type_to_schema(
        self, return_type: str, pydantic_models: Dict[str, Schema],
        imports: Dict[str, str] = None, file_path: str = None
    ) -> Optional[Schema]:
        """
        Parse return type annotation to Schema.

        Handles:
        - list[ModelName] -> array schema with items
        - List[ModelName] -> array schema with items
        - ModelName -> object schema
        - dict, str, int, etc -> basic types

        Args:
            return_type: Return type annotation string
            pydantic_models: Available Pydantic models
            imports: Import statements for lazy model resolution
            file_path: Current file path for import resolution

        Returns:
            Schema object or None
        """
        import re

        # Remove whitespace
        return_type = return_type.strip()

        # Handle list[X] or List[X]
        list_match = re.match(r'(?:list|List)\[(.+)\]', return_type)
        if list_match:
            inner_type = list_match.group(1).strip()

            # Check if inner type is a Pydantic model
            if inner_type in pydantic_models:
                return Schema(
                    type="array",
                    items=pydantic_models[inner_type],
                )
            # Lazy resolution: try to resolve from imports
            elif imports and file_path and inner_type in imports:
                resolved_models = self._resolve_imported_models({inner_type: imports[inner_type]}, file_path)
                if inner_type in resolved_models:
                    return Schema(
                        type="array",
                        items=resolved_models[inner_type],
                    )

            # Fallback
            if inner_type not in pydantic_models:
                # Try basic type mapping
                type_map = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "dict": "object",
                    "Dict": "object",
                }
                items_type = type_map.get(inner_type, "object")

                # Generic array with fallback items
                return Schema(
                    type="array",
                    items=Schema(type=items_type),
                    description=f"Array of {inner_type}",
                )

        # Handle direct model reference
        if return_type in pydantic_models:
            return pydantic_models[return_type]

        # Handle basic types
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "dict": "object",
            "Dict": "object",
        }

        if return_type in type_map:
            return Schema(type=type_map[return_type])

        # Unknown type - return generic schema with description
        return Schema(
            type="object",
            description=f"Returns {return_type}",
        )

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle Pydantic model schemas.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            parameters = self._extract_path_parameters(route.raw_path)

            # Add query and header parameters from metadata
            if "query_params" in route.metadata:
                parameters.extend(route.metadata["query_params"])
            if "header_params" in route.metadata:
                parameters.extend(route.metadata["header_params"])

            # Get pydantic models and type aliases from metadata for expansion
            pydantic_models = route.metadata.get("pydantic_models", {})
            type_aliases = route.metadata.get("type_aliases", {})
            imports = route.metadata.get("imports", {})

            # Get request body from metadata and expand references
            request_body = route.metadata.get("request_body")
            if request_body:
                request_body = self._expand_schema_references(
                    request_body, pydantic_models, type_aliases, imports, route.source_file
                )

            # Build responses list
            responses = []

            # Determine response schema
            response_schema = None

            # First try response_model from decorator (if successfully resolved)
            if "response_model" in route.metadata:
                response_schema = route.metadata["response_model"]
            # Only use return type annotation if NO response_model was specified in decorator
            elif "return_type" in route.metadata and not route.metadata.get("response_model_specified"):
                return_type = route.metadata["return_type"]
                # Parse return type to proper schema
                response_schema = self._parse_return_type_to_schema(
                    return_type, pydantic_models, imports, route.source_file
                )

            # Expand response schema references
            if response_schema:
                response_schema = self._expand_schema_references(
                    response_schema, pydantic_models, type_aliases, imports, route.source_file
                )

            # Add 200 response
            if response_schema:
                responses.append(
                    Response(
                        status_code="200",
                        description="Success",
                        response_schema=response_schema,
                        content_type="application/json",
                    )
                )
            else:
                # Default 200 response without schema
                responses.append(
                    Response(
                        status_code="200",
                        description="Success",
                        content_type="application/json",
                    )
                )

            # Add additional response codes from responses dict
            if "response_codes" in route.metadata:
                for status_code, model_name in route.metadata["response_codes"].items():
                    # Skip if it's the 200 response (already handled)
                    if status_code == "200":
                        continue

                    # Get description based on status code
                    status_descriptions = {
                        "400": "Bad Request",
                        "401": "Unauthorized",
                        "403": "Forbidden",
                        "404": "Not Found",
                        "422": "Validation Error",
                        "500": "Internal Server Error",
                    }
                    description = status_descriptions.get(status_code, f"Response {status_code}")

                    responses.append(
                        Response(
                            status_code=status_code,
                            description=description,
                            content_type="application/json",
                        )
                    )

            # Get summary from metadata
            summary = route.metadata.get("summary")

            endpoint = Endpoint(
                path=self._normalize_path(route.raw_path),
                method=method,
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                summary=summary,
                operation_id=route.handler_name,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints
