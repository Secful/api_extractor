"""FastAPI framework extractor."""

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
)


class FastAPIExtractor(BaseExtractor):
    """Extract API routes from FastAPI applications."""

    # HTTP method decorators
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize FastAPI extractor."""
        super().__init__(FrameworkType.FASTAPI)
        # Map of file paths to router variable names and their prefixes
        # e.g., {"/path/to/endpoints.py": {"router": "/organizations"}}
        self.router_definitions: Dict[str, Dict[str, str]] = {}
        # Map of router variable names to their URL prefixes after include
        # e.g., {"/v1": {"/organizations": "organization_router"}}
        self.router_includes: Dict[str, Dict[str, str]] = {}
        # Base path for the project (set during extract())
        self.base_path: str = ""
        # Global prefix from main router file (api.py, main.py, app.py)
        self.global_prefix: Optional[str] = None

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

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
        self.base_path = path
        self.global_prefix = None

        # Find all relevant files
        files = self._find_source_files(path)

        # Pass 1: Extract router definitions to find prefixes
        # Also detect global prefix from main router files
        for file_path in files:
            try:
                self._extract_router_definitions(file_path)
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
        Extract APIRouter definitions and their prefixes from a file.

        Parses patterns like:
        router = APIRouter(prefix="/organizations")
        organization_router = APIRouter(prefix="/orgs", tags=["orgs"])

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

        # Query for router assignments: router = APIRouter(...)
        router_query = """
        (assignment
          left: (identifier) @var_name
          right: (call
            function: (identifier) @func_name
            arguments: (argument_list) @args))
        """

        matches = self.parser.query(tree, router_query, "python")

        file_routers = {}
        for match in matches:
            var_name_node = match.get("var_name")
            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not all([var_name_node, func_name_node, args_node]):
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            if func_name != "APIRouter":
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Extract prefix from arguments
            prefix = self._extract_prefix_from_arguments(args_node, source_code)
            if prefix:
                file_routers[var_name] = prefix

        if file_routers:
            self.router_definitions[file_path] = file_routers

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
        Extract router.include_router() calls to build inclusion hierarchy.

        Parses patterns like:
        router.include_router(organization_router)
        app.include_router(router)

        Builds mapping of parent prefixes to child routers.

        Args:
            file_path: Path to Python file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for include_router calls: router.include_router(other_router)
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

            # Extract child router name from arguments
            child_router_name = None
            for child in args_node.children:
                if child.type == "identifier":
                    child_router_name = self.parser.get_node_text(child, source_code)
                    break

            if not child_router_name:
                continue

            # Look up parent router prefix in current file
            parent_prefix = None
            if file_path in self.router_definitions:
                parent_prefix = self.router_definitions[file_path].get(parent_router_name)

            # Store the relationship
            if parent_prefix is not None:
                if parent_prefix not in self.router_includes:
                    self.router_includes[parent_prefix] = {}
                self.router_includes[parent_prefix][child_router_name] = child_router_name

    def _get_router_prefix_for_file(self, file_path: str) -> Optional[str]:
        """
        Get the complete URL prefix chain for routes in a given file.

        Looks up router definition in the file, then composes with global prefix.

        Args:
            file_path: Absolute path to the file

        Returns:
            Full URL prefix (e.g., '/v1/organizations') or None
        """
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

        local_prefix = next(iter(file_routers.values()))

        # Compose global prefix + local prefix
        if self.global_prefix:
            # Ensure prefixes are properly formatted
            global_part = self.global_prefix.rstrip("/")
            local_part = local_prefix.rstrip("/")
            if not global_part.startswith("/"):
                global_part = "/" + global_part
            if not local_part.startswith("/"):
                local_part = "/" + local_part
            return global_part + local_part

        # No global prefix, just return local
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
        pydantic_models = self._find_pydantic_models(tree, source_code)

        # Resolve imported models
        imported_models = self._resolve_imported_models(imports, file_path)
        pydantic_models.update(imported_models)

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
                    func_def_node, source_code, pydantic_models
                )
                metadata.update(params_metadata)

            # Add response model if present
            if response_model_name:
                # Track that response_model was specified (even if we couldn't resolve it)
                metadata["response_model_specified"] = True
                if response_model_name in pydantic_models:
                    metadata["response_model"] = pydantic_models[response_model_name]

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

    def _find_pydantic_models(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all Pydantic BaseModel classes in the file.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

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
            schema = self._parse_pydantic_class_body(class_body_node, source_code)

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

        return resolved_models

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

            # Get name or names list
            name_node = import_node.child_by_field_name("name")
            if not name_node:
                continue

            # Handle both single imports and import lists
            if name_node.type == "dotted_name" or name_node.type == "identifier":
                # Single import: from x import y
                import_name = self.parser.get_node_text(name_node, source_code)
                imports[import_name] = f"{module_path}.{import_name}"

            elif name_node.type == "aliased_import":
                # Aliased import: from x import y as z
                actual_name_node = name_node.child_by_field_name("name")
                alias_name_node = name_node.child_by_field_name("alias")
                if actual_name_node and alias_name_node:
                    import_name = self.parser.get_node_text(actual_name_node, source_code)
                    alias_name = self.parser.get_node_text(alias_name_node, source_code)
                    imports[alias_name] = f"{module_path}.{import_name}"

            elif hasattr(name_node, 'children'):
                # Import list: from x import (y, z as w, ...)
                for child in name_node.children:
                    if child.type == "dotted_name" or child.type == "identifier":
                        import_name = self.parser.get_node_text(child, source_code)
                        imports[import_name] = f"{module_path}.{import_name}"
                    elif child.type == "aliased_import":
                        actual_name_node = child.child_by_field_name("name")
                        alias_name_node = child.child_by_field_name("alias")
                        if actual_name_node and alias_name_node:
                            import_name = self.parser.get_node_text(actual_name_node, source_code)
                            alias_name = self.parser.get_node_text(alias_name_node, source_code)
                            imports[alias_name] = f"{module_path}.{import_name}"

        return imports

    def _resolve_imported_models(
        self, imports: Dict[str, str], current_file_path: str
    ) -> Dict[str, Schema]:
        """
        Resolve imported Pydantic models by parsing their source files.

        Args:
            imports: Dictionary mapping names to module paths
            current_file_path: Path to current file for relative resolution

        Returns:
            Dictionary mapping model names to Schema objects
        """
        models = {}

        for model_name, module_path in imports.items():
            # Try to resolve the module path to a file path
            file_path = self._resolve_module_to_file(module_path, current_file_path)

            if not file_path:
                continue

            # Parse the file to extract Pydantic models
            try:
                source_code = self._read_file(file_path)
                if not source_code:
                    continue

                tree = self.parser.parse_source(source_code, "python")
                if not tree:
                    continue

                # Find all Pydantic models in the imported file
                imported_models = self._find_pydantic_models(tree, source_code)

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

    def _parse_pydantic_class_body(self, class_body_node: Node, source_code: bytes) -> Schema:
        """
        Parse Pydantic model fields from class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

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
                        field_info = self._parse_pydantic_field(expr_child, source_code)
                        if field_info:
                            name, field_schema, is_required = field_info
                            properties[name] = field_schema
                            if is_required:
                                required.append(name)
                    elif expr_child.type == "type_alias_statement":
                        # Handle: name: str (no default value)
                        field_info = self._parse_type_alias(expr_child, source_code)
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
        self, assignment_node: Node, source_code: bytes
    ) -> Optional[tuple]:
        """
        Parse a Pydantic field definition.

        Args:
            assignment_node: Assignment node
            source_code: Source code bytes

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
        field_type, is_optional = self._parse_type_annotation(type_text)

        # Check if there's a default value
        right = assignment_node.child_by_field_name("right")
        has_default = right is not None

        # Field is required if it's not Optional and has no default
        is_required = not is_optional and not has_default

        field_schema = {"type": field_type}

        return (field_name, field_schema, is_required)

    def _parse_type_alias(self, type_alias_node: Node, source_code: bytes) -> Optional[tuple]:
        """
        Parse a type alias statement (field without default value).

        Args:
            type_alias_node: Type alias node
            source_code: Source code bytes

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        field_name_node = type_alias_node.child_by_field_name("name")
        type_node = type_alias_node.child_by_field_name("value")

        if not field_name_node or not type_node:
            return None

        field_name = self.parser.get_node_text(field_name_node, source_code)
        type_text = self.parser.get_node_text(type_node, source_code)

        field_type, is_optional = self._parse_type_annotation(type_text)

        # No default value, so required unless Optional
        is_required = not is_optional

        field_schema = {"type": field_type}

        return (field_name, field_schema, is_required)

    def _parse_type_annotation(self, type_text: str) -> tuple:
        """
        Parse Python type annotation to OpenAPI type.

        Args:
            type_text: Type annotation text

        Returns:
            Tuple of (openapi_type, is_optional)
        """
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
        }

        # Check for List[T] pattern
        if "List[" in base_type or "list[" in base_type:
            return ("array", is_optional)

        openapi_type = type_map.get(base_type, "string")

        return (openapi_type, is_optional)

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
        self, func_def_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract function parameters to identify request body and query/header params.
        Also extracts return type annotation.

        Args:
            func_def_node: Function definition node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models

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
                    param_info = self._analyze_parameter(param, source_code, pydantic_models)
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
        self, param_node: Node, source_code: bytes, pydantic_models: Dict[str, Schema]
    ) -> Optional[tuple]:
        """
        Analyze a function parameter to determine its type.

        Args:
            param_node: Parameter node
            source_code: Source code bytes
            pydantic_models: Dictionary of Pydantic models

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
        param_type, _ = self._parse_type_annotation(type_text)

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
        param_type, _ = self._parse_type_annotation(type_text)

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

            # Get request body from metadata
            request_body = route.metadata.get("request_body")

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
                # Create a simple schema indicating the return type
                # We don't have the full model definition, so just use description
                response_schema = Schema(
                    type="object",
                    description=f"Returns {return_type} object",
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
