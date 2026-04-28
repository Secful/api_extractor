"""Django REST Framework extractor."""

import re
from typing import List, Optional, Dict, Set, Any
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
)


class DjangoRESTExtractor(BaseExtractor):
    """Extract API routes from Django REST Framework applications."""

    # ViewSet method to HTTP method mapping
    VIEWSET_METHODS = {
        "list": HTTPMethod.GET,
        "retrieve": HTTPMethod.GET,
        "create": HTTPMethod.POST,
        "update": HTTPMethod.PUT,
        "partial_update": HTTPMethod.PATCH,
        "destroy": HTTPMethod.DELETE,
    }

    def __init__(self) -> None:
        """Initialize Django REST extractor."""
        super().__init__(FrameworkType.DJANGO_REST)
        # Map of ViewSet class names to their registered paths
        # e.g., {"SnippetViewSet": "snippets", "UserViewSet": "users"}
        self.viewset_registrations: Dict[str, str] = {}
        # Map of URL file paths to their URL prefixes from include()
        # e.g., {"circuits/api/urls.py": "/api/circuits/"}
        self.url_includes: Dict[str, str] = {}
        # Map of router variable names to their URL prefixes
        # e.g., {"router": "/api/v2/"} for path('api/v2/', include(router.urls))
        self.router_prefixes: Dict[str, str] = {}
        # Base path for the project (set during extract())
        self.base_path: str = ""

    def get_file_extensions(self) -> List[str]:
        """Get Python file extensions."""
        return [".py"]

    def extract(self, path: str):
        """
        Override extract to do three-pass extraction:
        1. First pass: scan urls.py files to find path(..., include(...)) calls
        2. Second pass: scan urls.py files to find router.register() calls
        3. Third pass: extract ViewSets from views.py with correct paths

        Args:
            path: Path to codebase directory

        Returns:
            ExtractionResult with endpoints and any errors
        """
        self.endpoints = []
        self.errors = []
        self.warnings = []
        self.viewset_registrations = {}
        self.url_includes = {}
        self.router_prefixes = {}
        self.base_path = path

        # Find all relevant files
        files = self._find_source_files(path)

        # Pass 1: Extract URL includes to build prefix mappings
        for file_path in files:
            if file_path.endswith('urls.py'):
                try:
                    self._extract_url_includes(file_path)
                except Exception as e:
                    self.errors.append(f"Error extracting URL includes from {file_path}: {str(e)}")

        # Pass 2: Extract router registrations from urls.py files
        for file_path in files:
            if file_path.endswith('urls.py'):
                try:
                    self._extract_router_registrations(file_path)
                except Exception as e:
                    self.errors.append(f"Error extracting router registrations from {file_path}: {str(e)}")

        # Pass 3: Extract routes from all files (now with include and registration info)
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

    def _get_url_prefix_for_file(self, file_path: str) -> str | None:
        """
        Get the URL prefix for a given file path based on include() mappings.

        Args:
            file_path: Absolute path to the file

        Returns:
            URL prefix (e.g., '/api/circuits/') or None if no mapping found
        """
        import os

        # Make file path relative to base path
        if file_path.startswith(self.base_path):
            relative_path = file_path[len(self.base_path):].lstrip('/')
        else:
            relative_path = file_path

        # Check if this file is in the same directory as an included urls.py
        # For example, if circuits/api/urls.py is included, then circuits/api/views.py
        # should get the same prefix
        for include_path, prefix in self.url_includes.items():
            # Get the directory of the included urls.py file
            include_dir = os.path.dirname(include_path)

            # Check if the current file is in that directory
            file_dir = os.path.dirname(relative_path)

            # Match if the directory paths are the same or if file_dir ends with include_dir
            if file_dir == include_dir or file_dir.endswith(include_dir):
                return prefix

        return None

    def _extract_url_includes(self, file_path: str) -> None:
        """
        Extract path(..., include(...)) calls from urls.py file.

        Parses patterns like:
        path('api/circuits/', include('circuits.api.urls'))
        path('api/', include('myapp.urls'))

        Builds mapping of included URL files to their URL prefixes.

        Args:
            file_path: Path to urls.py file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Query for path(..., include(...)) calls
        # Matches: path('prefix/', include('module.path'))
        path_include_query = """
        (call
          function: (identifier) @func_name
          arguments: (argument_list) @args)
        """

        matches = self.parser.query(tree, path_include_query, "python")
        for match in matches:
            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not func_name_node or not args_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)

            # Check if this is a path() call
            if func_name != "path":
                continue

            # Extract arguments
            url_prefix = None
            include_module = None

            for child in args_node.children:
                if child.type in ("string", "raw_string_literal") and url_prefix is None:
                    # First string argument is the URL prefix
                    text = self.parser.get_node_text(child, source_code).strip()
                    if text.startswith(("r'", 'r"')):
                        url_prefix = text[2:-1]
                    elif text.startswith(("'", '"')):
                        url_prefix = text[1:-1]
                elif child.type == "call":
                    # Check if this is an include() call
                    func_node = child.child_by_field_name("function")
                    if func_node:
                        func_text = self.parser.get_node_text(func_node, source_code)
                        if func_text == "include":
                            # Extract the module path from include() argument
                            include_args = child.child_by_field_name("arguments")
                            if include_args:
                                for arg_child in include_args.children:
                                    if arg_child.type in ("string", "raw_string_literal"):
                                        text = self.parser.get_node_text(arg_child, source_code).strip()
                                        if text.startswith(("'", '"')):
                                            include_module = text[1:-1]
                                        break
                                    elif arg_child.type == "attribute":
                                        # Handle include(router.urls) pattern
                                        attr_text = self.parser.get_node_text(arg_child, source_code)
                                        if attr_text.endswith(".urls"):
                                            # Extract router variable name
                                            router_var = attr_text.rsplit(".", 1)[0]
                                            # Store router prefix mapping
                                            if url_prefix:
                                                prefix = url_prefix if url_prefix.startswith('/') else '/' + url_prefix
                                                if not prefix.endswith('/'):
                                                    prefix = prefix + '/'
                                                self.router_prefixes[router_var] = prefix
                                        break

            # If we found both prefix and module, create mapping
            if url_prefix and include_module:
                # Convert module path to file path
                # 'circuits.api.urls' -> 'circuits/api/urls.py'
                file_relative_path = include_module.replace('.', '/') + '.py'

                # Normalize prefix to start and end with /
                if not url_prefix.startswith('/'):
                    url_prefix = '/' + url_prefix
                if not url_prefix.endswith('/'):
                    url_prefix = url_prefix + '/'

                # Store the mapping
                self.url_includes[file_relative_path] = url_prefix

    def _extract_router_registrations(self, file_path: str) -> None:
        """
        Extract router.register() calls from urls.py file.

        Parses patterns like:
        router.register(r'snippets', views.SnippetViewSet)
        router.register('users', UserViewSet)

        Also checks if this router has a URL prefix from include(router.urls).

        Args:
            file_path: Path to urls.py file
        """
        source_code = self._read_file(file_path)
        if not source_code:
            return

        tree = self.parser.parse_source(source_code, "python")
        if not tree:
            return

        # Check if any router in this file has a prefix
        router_prefix_in_file = None
        for router_var, prefix in self.router_prefixes.items():
            # Simple heuristic: if this file contains router.register() calls,
            # assume it's the file where the router is defined
            if router_var.encode() in source_code:
                router_prefix_in_file = prefix
                break

        # Query for router.register() calls
        register_query = """
        (expression_statement
          (call
            function: (attribute
              object: (identifier) @router_name
              attribute: (identifier) @method_name)
            arguments: (argument_list) @args))
        """

        matches = self.parser.query(tree, register_query, "python")
        for match in matches:
            router_name_node = match.get("router_name")
            method_name_node = match.get("method_name")
            args_node = match.get("args")

            if not all([router_name_node, method_name_node, args_node]):
                continue

            router_name = self.parser.get_node_text(router_name_node, source_code)
            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if this is router.register()
            if method_name != "register":
                continue

            # Extract arguments: path prefix and ViewSet class
            args = []
            for child in args_node.children:
                if child.type in ("string", "raw_string_literal"):
                    # Extract path prefix (first argument)
                    path_text = self.parser.get_node_text(child, source_code)
                    # Remove r' or ' or " prefix and trailing quote
                    path_value = path_text.strip()
                    # Handle r'snippets', 'snippets', or "snippets"
                    if path_value.startswith(("r'", 'r"')):
                        path_value = path_value[2:-1]
                    elif path_value.startswith(("'", '"')):
                        path_value = path_value[1:-1]
                    if path_value:
                        args.append(path_value)
                elif child.type == "attribute":
                    # Extract ViewSet class name like views.SnippetViewSet
                    viewset_name = self.parser.get_node_text(child, source_code)
                    # Get just the class name part
                    if "." in viewset_name:
                        viewset_name = viewset_name.split(".")[-1]
                    args.append(viewset_name)
                elif child.type == "identifier":
                    # Direct identifier without module prefix
                    viewset_name = self.parser.get_node_text(child, source_code)
                    args.append(viewset_name)

            # Should have at least 2 args: path and ViewSet
            if len(args) >= 2:
                path_prefix = args[0]
                viewset_class = args[1]

                # Apply router prefix if this router is included with a prefix
                if router_prefix_in_file:
                    # Combine router prefix with registration path
                    path_prefix = router_prefix_in_file.rstrip('/') + '/' + path_prefix.lstrip('/')

                # Store the mapping
                self.viewset_registrations[viewset_class] = path_prefix

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Django REST Framework file.

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

        # First, find all serializer classes
        serializers = self._find_serializers(tree, source_code)

        # Query 1: Find ViewSet/APIView classes with base classes
        class_query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses
          body: (block) @body)
        """

        class_matches = self.parser.query(tree, class_query, "python")
        for match in class_matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")
            body_node = match.get("body")

            if not class_name_node or not body_node:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Get base classes
            bases = []
            if superclasses_node:
                for child in superclasses_node.children:
                    if child.type in ("identifier", "attribute"):
                        base_name = self.parser.get_node_text(child, source_code)
                        bases.append(base_name)

            # Check if it's a ViewSet or APIView
            is_viewset = any("ViewSet" in base for base in bases)
            is_apiview = any("APIView" in base for base in bases)

            if not is_viewset and not is_apiview:
                continue

            # Get the registered path for this ViewSet, or generate one as fallback
            if class_name in self.viewset_registrations:
                registered_path = self.viewset_registrations[class_name]
                # If path already starts with /, don't add another one
                if registered_path.startswith('/'):
                    base_path = f"{registered_path}/"
                else:
                    base_path = f"/{registered_path}/"
            else:
                base_path = self._generate_path_from_class_name(class_name)

            # Apply URL prefix from include() if this file is included in main urls
            url_prefix = self._get_url_prefix_for_file(file_path)
            if url_prefix:
                # Combine prefix and base_path, avoiding double slashes
                base_path = base_path.lstrip('/')
                if not url_prefix.endswith('/'):
                    url_prefix = url_prefix + '/'
                base_path = url_prefix + base_path

            location = self.parser.get_node_location(class_name_node)

            # Find serializer_class for this ViewSet
            serializer_class_name = None
            if is_viewset:
                serializer_class_name = self._find_serializer_class_for_viewset(
                    body_node, source_code
                )

            if is_viewset:
                routes.extend(
                    self._extract_viewset_routes_query(
                        body_node, source_code, file_path, base_path, location, tree,
                        serializers, serializer_class_name, bases
                    )
                )
            elif is_apiview:
                routes.extend(
                    self._extract_apiview_routes_query(
                        body_node, source_code, file_path, base_path, location, tree
                    )
                )

        # Query 2: Find function-based views with @api_view decorator
        api_view_query = """
        (decorated_definition
          (decorator
            (call
              function: (identifier) @decorator_name
              arguments: (argument_list
                (list) @methods_list)))
          definition: (function_definition
            name: (identifier) @func_name))
        """

        api_view_matches = self.parser.query(tree, api_view_query, "python")
        for match in api_view_matches:
            decorator_name_node = match.get("decorator_name")
            if not decorator_name_node:
                continue

            decorator_name = self.parser.get_node_text(decorator_name_node, source_code)
            if decorator_name != "api_view":
                continue

            func_name_node = match.get("func_name")
            methods_list_node = match.get("methods_list")

            if not func_name_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)

            # Extract HTTP methods from list
            http_methods = []
            if methods_list_node:
                for child in methods_list_node.children:
                    if child.type == "string":
                        method_str = self.parser.extract_string_value(child, source_code)
                        if method_str:
                            try:
                                http_methods.append(HTTPMethod[method_str.upper()])
                            except KeyError:
                                pass

            # Default to GET if no methods specified
            if not http_methods:
                http_methods = [HTTPMethod.GET]

            # Generate path from function name
            path = f"/{func_name.replace('_', '-')}"
            location = self.parser.get_node_location(func_name_node)

            route = Route(
                path=path,
                methods=http_methods,
                handler_name=func_name,
                framework=self.framework,
                raw_path=path,
                source_file=file_path,
                source_line=location["start_line"],
            )
            routes.append(route)

        return routes


    def _generate_path_from_class_name(self, class_name: str) -> str:
        """
        Generate REST path from class name.

        UserViewSet -> /users
        ItemAPIView -> /items

        Args:
            class_name: Class name

        Returns:
            Generated path
        """
        # Remove ViewSet/APIView suffix
        name = re.sub(r"(ViewSet|APIView)$", "", class_name)

        # Convert CamelCase to snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        # Pluralize (simple approach)
        if not name.endswith("s"):
            name += "s"

        return f"/{name}"

    def _extract_viewset_routes_query(
        self,
        body_node: Node,
        source_code: bytes,
        file_path: str,
        base_path: str,
        location: Dict,
        tree,
        serializers: Dict[str, Schema],
        serializer_class_name: Optional[str],
        bases: List[str],
    ) -> List[Route]:
        """
        Extract routes from ViewSet class using queries.

        Args:
            body_node: class body node
            source_code: Source code bytes
            file_path: Path to source file
            base_path: Base path for this ViewSet
            location: Source location info
            tree: Full syntax tree
            serializers: Dictionary of serializer schemas
            serializer_class_name: Name of serializer_class for this ViewSet
            bases: List of base class names

        Returns:
            List of Route objects
        """
        routes = []

        # Get the serializer schema if available
        serializer_schema = None
        if serializer_class_name and serializer_class_name in serializers:
            serializer_schema = serializers[serializer_class_name]

        # Determine which standard methods this ViewSet should have
        # Check ReadOnlyModelViewSet first since it contains "ModelViewSet" in the name
        standard_methods = []
        is_readonly_viewset = any("ReadOnlyModelViewSet" in base for base in bases)
        is_model_viewset = any("ModelViewSet" in base for base in bases) and not is_readonly_viewset

        if is_readonly_viewset:
            # ReadOnlyModelViewSet provides only list and retrieve
            standard_methods = ["list", "retrieve"]
        elif is_model_viewset:
            # ModelViewSet provides all CRUD operations
            standard_methods = ["list", "create", "retrieve", "update", "partial_update", "destroy"]

        # Generate routes for standard ViewSet methods
        for method_name in standard_methods:
            http_method = self.VIEWSET_METHODS[method_name]

            # Determine path (list vs detail)
            if method_name in ["list", "create"]:
                path = base_path
            else:
                # Remove trailing slash from base_path before adding /{pk}/
                base = base_path.rstrip('/')
                path = f"{base}/{{pk}}/"

            # Build metadata with serializer schemas based on method
            metadata = {}
            if serializer_schema:
                if method_name == "create":
                    # POST uses serializer for request body
                    metadata["request_body"] = serializer_schema
                elif method_name in ["update", "partial_update"]:
                    # PUT/PATCH uses serializer for request body
                    metadata["request_body"] = serializer_schema
                elif method_name in ["retrieve", "list"]:
                    # GET returns serializer as response
                    metadata["response_schema"] = serializer_schema
                    if method_name == "list":
                        metadata["response_is_list"] = True

            route = Route(
                path=path,
                methods=[http_method],
                handler_name=method_name,
                framework=self.framework,
                raw_path=path,
                source_file=file_path,
                source_line=location["start_line"],
                metadata=metadata,
            )
            routes.append(route)

        # Note: We already generated routes for standard methods above,
        # so we don't need to query for them again

        # Query for @action decorated methods
        action_query = """
        (decorated_definition
          (decorator
            (call
              function: (identifier) @decorator_name
              arguments: (argument_list) @args))
          definition: (function_definition
            name: (identifier) @func_name))
        """

        action_matches = self.parser.query(tree, action_query, "python")
        for match in action_matches:
            decorator_name_node = match.get("decorator_name")
            if not decorator_name_node:
                continue

            # Check if within body
            if not self._is_node_within(decorator_name_node, body_node):
                continue

            decorator_name = self.parser.get_node_text(decorator_name_node, source_code)
            if decorator_name != "action":
                continue

            func_name_node = match.get("func_name")
            args_node = match.get("args")

            if not func_name_node:
                continue

            method_name = self.parser.get_node_text(func_name_node, source_code)

            # Parse @action arguments
            is_detail = False
            http_methods = [HTTPMethod.GET]  # Default

            if args_node:
                for arg in args_node.children:
                    if arg.type == "keyword_argument":
                        name_node = self.parser.find_child_by_field(arg, "name")
                        value_node = self.parser.find_child_by_field(arg, "value")

                        if name_node and value_node:
                            arg_name = self.parser.get_node_text(name_node, source_code)

                            if arg_name == "detail":
                                value_text = self.parser.get_node_text(value_node, source_code)
                                is_detail = value_text == "True"

                            elif arg_name == "methods":
                                if value_node.type == "list":
                                    http_methods = []
                                    for list_child in value_node.children:
                                        if list_child.type == "string":
                                            method_str = self.parser.extract_string_value(
                                                list_child, source_code
                                            )
                                            if method_str:
                                                try:
                                                    http_methods.append(
                                                        HTTPMethod[method_str.upper()]
                                                    )
                                                except KeyError:
                                                    pass

            # Build path (normalize base_path to avoid double slashes)
            base = base_path.rstrip('/')
            if is_detail:
                path = f"{base}/{{pk}}/{method_name}/"
            else:
                path = f"{base}/{method_name}/"

            for http_method in http_methods:
                route = Route(
                    path=path,
                    methods=[http_method],
                    handler_name=method_name,
                    framework=self.framework,
                    raw_path=path,
                    source_file=file_path,
                    source_line=location["start_line"],
                )
                routes.append(route)

        return routes

    def _extract_apiview_routes_query(
        self,
        body_node: Node,
        source_code: bytes,
        file_path: str,
        base_path: str,
        location: Dict,
        tree,
    ) -> List[Route]:
        """
        Extract routes from APIView class using queries.

        Args:
            body_node: class body node
            source_code: Source code bytes
            file_path: Path to source file
            base_path: Base path for this view
            location: Source location info
            tree: Full syntax tree

        Returns:
            List of Route objects
        """
        routes = []

        # Query for HTTP method handlers
        method_query = """
        (function_definition
          name: (identifier) @method_name)
        """

        http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
        method_matches = self.parser.query(tree, method_query, "python")

        for match in method_matches:
            method_name_node = match.get("method_name")
            if not method_name_node:
                continue

            # Check if within body
            if not self._is_node_within(method_name_node, body_node):
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            if method_name.lower() in http_method_names:
                try:
                    http_method = HTTPMethod[method_name.upper()]

                    route = Route(
                        path=base_path,
                        methods=[http_method],
                        handler_name=method_name,
                        framework=self.framework,
                        raw_path=base_path,
                        source_file=file_path,
                        source_line=location["start_line"],
                    )
                    routes.append(route)
                except KeyError:
                    pass

        return routes

    def _is_node_within(self, child_node: Node, parent_node: Node) -> bool:
        """
        Check if child_node is within parent_node's range.

        Args:
            child_node: Potential child node
            parent_node: Parent node

        Returns:
            True if child is within parent
        """
        return (
            child_node.start_byte >= parent_node.start_byte
            and child_node.end_byte <= parent_node.end_byte
        )


    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Django REST path.

        Uses {param} syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all {param} patterns
        pattern = r"\{([^}]+)\}"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)

            # pk is typically an integer
            param_type = "integer" if param_name == "pk" else "string"

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type=param_type,
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Django REST path to OpenAPI format.

        Already uses {param} format which is OpenAPI compatible.
        Removes trailing slashes to match OpenAPI conventions (except for root /).

        Args:
            path: Django REST path

        Returns:
            Normalized path without trailing slash
        """
        # Django REST Framework adds trailing slashes by default, but OpenAPI
        # convention is to omit them for consistency with other frameworks
        if path != "/" and path.endswith("/"):
            return path.rstrip("/")
        return path

    def _find_serializers(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all Serializer classes in the file.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping serializer names to Schema objects
        """
        serializers = {}

        # Query for classes inheriting from serializers.Serializer
        class_query = """
        (class_definition
          name: (identifier) @class_name
          superclasses: (argument_list) @superclasses
          body: (block) @class_body)
        """

        matches = self.parser.query(tree, class_query, "python")

        for match in matches:
            class_name_node = match.get("class_name")
            superclasses_node = match.get("superclasses")
            class_body_node = match.get("class_body")

            if not all([class_name_node, superclasses_node, class_body_node]):
                continue

            # Check if it inherits from serializers.Serializer
            superclasses_text = self.parser.get_node_text(superclasses_node, source_code)
            if "Serializer" not in superclasses_text:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Parse fields from class body
            schema = self._parse_serializer_class_body(class_body_node, source_code)
            serializers[class_name] = schema

        return serializers

    def _parse_serializer_class_body(self, class_body_node: Node, source_code: bytes) -> Schema:
        """
        Parse serializer field definitions from class body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for field assignments: field_name = serializers.FieldType(...)
        for child in class_body_node.children:
            if child.type == "expression_statement":
                for expr_child in child.children:
                    if expr_child.type == "assignment":
                        field_info = self._parse_serializer_field(expr_child, source_code)
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

    def _parse_serializer_field(self, assignment_node: Node, source_code: bytes) -> Optional[tuple]:
        """
        Parse a serializer field definition.

        Args:
            assignment_node: Assignment node
            source_code: Source code bytes

        Returns:
            Tuple of (field_name, field_schema_dict, is_required) or None
        """
        # Get left side (field name)
        left = assignment_node.child_by_field_name("left")
        if not left or left.type != "identifier":
            return None

        field_name = self.parser.get_node_text(left, source_code)

        # Get right side (field definition)
        right = assignment_node.child_by_field_name("right")
        if not right or right.type != "call":
            return None

        # Get the field type from call expression
        call_text = self.parser.get_node_text(right, source_code)

        # Parse field type
        field_type, constraints = self._parse_field_type_and_constraints(call_text)

        # Fields are required by default in DRF unless required=False
        is_required = "required=False" not in call_text

        field_schema = {"type": field_type}
        field_schema.update(constraints)

        return (field_name, field_schema, is_required)

    def _parse_field_type_and_constraints(self, call_text: str) -> tuple:
        """
        Parse field type and constraints from field definition.

        Args:
            call_text: Field definition call text

        Returns:
            Tuple of (openapi_type, constraints_dict)
        """
        constraints = {}

        # Map DRF field types to OpenAPI types
        if "IntegerField" in call_text:
            field_type = "integer"
        elif "DecimalField" in call_text or "FloatField" in call_text:
            field_type = "number"
        elif "BooleanField" in call_text:
            field_type = "boolean"
        elif "EmailField" in call_text or "CharField" in call_text or "TextField" in call_text:
            field_type = "string"
            if "EmailField" in call_text:
                constraints["format"] = "email"
        elif "DateTimeField" in call_text:
            field_type = "string"
            constraints["format"] = "date-time"
        elif "DateField" in call_text:
            field_type = "string"
            constraints["format"] = "date"
        elif "ListField" in call_text:
            field_type = "array"
        else:
            field_type = "string"

        # Extract max_length constraint
        import re
        max_length_match = re.search(r"max_length=(\d+)", call_text)
        if max_length_match:
            constraints["maxLength"] = int(max_length_match.group(1))

        # Extract max_digits and decimal_places for DecimalField
        max_digits_match = re.search(r"max_digits=(\d+)", call_text)
        if max_digits_match:
            constraints["maximum"] = 10 ** int(max_digits_match.group(1))

        return (field_type, constraints)

    def _find_serializer_class_for_viewset(
        self, class_body_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Find serializer_class attribute in ViewSet body.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes

        Returns:
            Serializer class name or None
        """
        for child in class_body_node.children:
            if child.type == "expression_statement":
                for expr_child in child.children:
                    if expr_child.type == "assignment":
                        left = expr_child.child_by_field_name("left")
                        right = expr_child.child_by_field_name("right")

                        if left and right:
                            left_text = self.parser.get_node_text(left, source_code)
                            if left_text == "serializer_class":
                                return self.parser.get_node_text(right, source_code)

        return None

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle serializer schemas.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            parameters = self._extract_path_parameters(route.raw_path)

            # Get request body from metadata
            request_body = route.metadata.get("request_body")

            # Create response
            response_schema = route.metadata.get("response_schema")
            response_is_list = route.metadata.get("response_is_list", False)

            # If response is a list, wrap schema in array
            if response_is_list and response_schema:
                response_schema = Schema(
                    type="array",
                    items=response_schema.model_dump(),
                )

            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    response_schema=response_schema,
                    content_type="application/json",
                )
            ]

            endpoint = Endpoint(
                path=self._normalize_path(route.raw_path),
                method=method,
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                operation_id=route.handler_name,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints
