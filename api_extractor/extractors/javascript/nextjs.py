"""Next.js framework extractor."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Endpoint,
    FrameworkType,
    HTTPMethod,
    Parameter,
    ParameterLocation,
    Response,
    Route,
    Schema,
)


class NextJSExtractor(BaseExtractor):
    """Extract API routes from Next.js applications (App Router & Pages Router)."""

    # HTTP methods for App Router (exported functions)
    APP_ROUTER_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

    def __init__(self) -> None:
        """Initialize Next.js extractor."""
        super().__init__(FrameworkType.NEXTJS)
        self.router_type: str | None = None

    def get_file_extensions(self) -> List[str]:
        """Get JavaScript/TypeScript file extensions."""
        return [".js", ".ts", ".jsx", ".tsx"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Next.js file.

        Args:
            file_path: Path to JavaScript/TypeScript file

        Returns:
            List of Route objects
        """
        routes = []

        # Detect router type from file path
        router_type = self._detect_router_type(file_path)
        if router_type == "unknown":
            return routes

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Determine language (JavaScript or TypeScript)
        language = "javascript" if file_path.endswith((".js", ".jsx")) else "typescript"
        is_typescript = language == "typescript"

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return routes

        # For TypeScript files, find interface definitions
        interfaces = {}
        if is_typescript:
            interfaces = self._find_interfaces(tree, source_code)

        # Extract routes based on router type
        if router_type == "app":
            routes.extend(
                self._extract_app_router_routes(file_path, source_code, tree, language, interfaces)
            )
        elif router_type == "pages":
            routes.extend(
                self._extract_pages_router_routes(
                    file_path, source_code, tree, language, interfaces
                )
            )

        return routes

    def _detect_router_type(self, file_path: str) -> str:
        """
        Detect if file is App Router or Pages Router based on path.

        Args:
            file_path: Path to file

        Returns:
            'app', 'pages', or 'unknown'
        """
        normalized_path = file_path.replace(os.sep, "/")

        if "/app/api/" in normalized_path:
            return "app"
        elif "/pages/api/" in normalized_path:
            return "pages"
        else:
            return "unknown"

    def _extract_app_router_routes(
        self,
        file_path: str,
        source_code: bytes,
        tree,
        language: str,
        interfaces: Dict[str, Schema],
    ) -> List[Route]:
        """
        Extract routes from App Router (route.ts files).

        Args:
            file_path: Path to file
            source_code: Source code bytes
            tree: Syntax tree
            language: Language (javascript or typescript)
            interfaces: TypeScript interfaces

        Returns:
            List of Route objects
        """
        routes = []

        # Derive path from file structure
        route_path = self._derive_route_path_app(file_path)

        # Query for exported async functions (HTTP method handlers)
        export_query = """
        (export_statement
          (function_declaration
            name: (identifier) @func_name
            parameters: (formal_parameters) @params))
        """

        # Also check for arrow function exports
        export_arrow_query = """
        (export_statement
          (lexical_declaration
            (variable_declarator
              name: (identifier) @func_name
              value: (arrow_function
                parameters: (formal_parameters) @params))))
        """

        matches = self.parser.query(tree, export_query, language)
        arrow_matches = self.parser.query(tree, export_arrow_query, language)
        all_matches = matches + arrow_matches

        for match in all_matches:
            func_name_node = match.get("func_name")
            params_node = match.get("params")

            if not func_name_node:
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)

            # Check if it's an HTTP method
            if func_name not in self.APP_ROUTER_METHODS:
                continue

            method = HTTPMethod[func_name]

            # Extract parameters if this is TypeScript
            metadata = {}
            if params_node and language == "typescript":
                metadata = self._extract_app_router_metadata(params_node, source_code, interfaces)

            location = self.parser.get_node_location(func_name_node)

            route = Route(
                path=route_path,
                methods=[method],
                handler_name=func_name,
                framework=self.framework,
                raw_path=route_path,
                source_file=file_path,
                source_line=location["start_line"],
                metadata=metadata,
            )
            routes.append(route)

        return routes

    def _extract_pages_router_routes(
        self,
        file_path: str,
        source_code: bytes,
        tree,
        language: str,
        interfaces: Dict[str, Schema],
    ) -> List[Route]:
        """
        Extract routes from Pages Router (pages/api/*.ts files).

        Args:
            file_path: Path to file
            source_code: Source code bytes
            tree: Syntax tree
            language: Language (javascript or typescript)
            interfaces: TypeScript interfaces

        Returns:
            List of Route objects
        """
        routes = []

        # Derive path from file structure
        route_path = self._derive_route_path_pages(file_path)

        # Query for default export handler function
        # Pattern 1: export default function handler(req, res) { }
        export_query = """
        (export_statement
          (function_declaration
            name: (identifier)? @func_name
            parameters: (formal_parameters) @params
            body: (statement_block) @body))
        """

        # Pattern 2: export default (req, res) => { }
        export_arrow_query = """
        (export_statement
          (arrow_function
            parameters: (formal_parameters) @params
            body: (_) @body))
        """

        matches = self.parser.query(tree, export_query, language)
        arrow_matches = self.parser.query(tree, export_arrow_query, language)

        # Combine both patterns
        all_matches = []
        for match in matches:
            all_matches.append(match)
        for match in arrow_matches:
            all_matches.append(match)

        if not all_matches:
            return routes

        # Take first match (should only be one default export)
        match = all_matches[0]
        body_node = match.get("body")
        params_node = match.get("params")

        if not body_node:
            return routes

        # Analyze handler body for req.method checks
        methods = self._extract_http_methods_from_body(body_node, source_code)

        # Extract metadata if TypeScript
        metadata = {}
        if params_node and language == "typescript":
            metadata = self._extract_pages_router_metadata(params_node, source_code, interfaces)

        # Get first node location for line number
        func_name_node = match.get("func_name")
        if func_name_node:
            location = self.parser.get_node_location(func_name_node)
        elif body_node:
            location = self.parser.get_node_location(body_node)
        else:
            location = {"start_line": 1}

        # Create route for each detected method
        for method in methods:
            route = Route(
                path=route_path,
                methods=[method],
                handler_name="handler",
                framework=self.framework,
                raw_path=route_path,
                source_file=file_path,
                source_line=location["start_line"],
                metadata=metadata,
            )
            routes.append(route)

        return routes

    def _derive_route_path_app(self, file_path: str) -> str:
        """
        Derive route path from App Router file structure.

        app/api/users/[id]/route.ts → /api/users/:id

        Args:
            file_path: File path

        Returns:
            Route path
        """
        # Normalize path separators
        normalized_path = file_path.replace(os.sep, "/")

        # Find 'app/api/' segment
        match = re.search(r"app/api/(.+)/route\.(ts|js|tsx|jsx)$", normalized_path)
        if not match:
            # Check if it's just app/api/route.ts (root API route)
            if re.search(r"app/api/route\.(ts|js|tsx|jsx)$", normalized_path):
                return "/api"
            return "/"

        path_segment = match.group(1)

        # Convert [param] to :param
        path = re.sub(r"\[([^\]]+)\]", r":\1", path_segment)

        # Handle catch-all [...slug] -> :...slug (will be processed later)
        # Keep the ... prefix for now

        return f"/api/{path}"

    def _derive_route_path_pages(self, file_path: str) -> str:
        """
        Derive route path from Pages Router file structure.

        pages/api/users/[id].ts → /api/users/:id
        pages/api/users.ts → /api/users

        Args:
            file_path: File path

        Returns:
            Route path
        """
        # Normalize path separators
        normalized_path = file_path.replace(os.sep, "/")

        # Find 'pages/api/' segment
        match = re.search(r"pages/api/(.+)\.(ts|js|tsx|jsx)$", normalized_path)
        if not match:
            return "/"

        path_segment = match.group(1)

        # Handle index files
        if path_segment.endswith("/index"):
            path_segment = path_segment[:-6]  # Remove '/index'
        elif path_segment == "index":
            return "/api"

        # Convert [param] to :param
        path = re.sub(r"\[([^\]]+)\]", r":\1", path_segment)

        # Handle catch-all [...slug] already converted to :...slug

        return f"/api/{path}"

    def _extract_http_methods_from_body(
        self, body_node: Node, source_code: bytes
    ) -> List[HTTPMethod]:
        """
        Scan handler body for if (req.method === 'GET') patterns.

        Args:
            body_node: Function body node
            source_code: Source code bytes

        Returns:
            List of HTTPMethod enums
        """
        methods = []
        body_text = self.parser.get_node_text(body_node, source_code)

        # Pattern: req.method === 'GET', req.method == 'POST', etc.
        method_patterns = [
            r"req\.method\s*===?\s*['\"](\w+)['\"]",
            r"req\.method\s*===?\s*`(\w+)`",
        ]

        seen_methods = set()
        for pattern in method_patterns:
            for match in re.finditer(pattern, body_text):
                method_name = match.group(1).upper()
                if method_name in HTTPMethod.__members__ and method_name not in seen_methods:
                    methods.append(HTTPMethod[method_name])
                    seen_methods.add(method_name)

        # If no methods found, assume GET (common default)
        return methods if methods else [HTTPMethod.GET]

    def _extract_app_router_metadata(
        self, params_node: Node, source_code: bytes, interfaces: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract metadata from App Router handler parameters.

        Args:
            params_node: Parameters node
            source_code: Source code bytes
            interfaces: TypeScript interfaces

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Look for second parameter { params } with type annotation
        param_nodes = [child for child in params_node.children if child.type == "required_parameter"]

        if len(param_nodes) >= 2:
            # Second parameter might have params type
            second_param = param_nodes[1]
            metadata.update(self._extract_params_metadata(second_param, source_code, interfaces))

        return metadata

    def _extract_pages_router_metadata(
        self, params_node: Node, source_code: bytes, interfaces: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract metadata from Pages Router handler parameters.

        Args:
            params_node: Parameters node
            source_code: Source code bytes
            interfaces: TypeScript interfaces

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Look for req and res parameters with type annotations
        param_nodes = [child for child in params_node.children if child.type == "required_parameter"]

        for param_node in param_nodes:
            param_name = None
            type_annotation_node = None

            for child in param_node.children:
                if child.type == "identifier":
                    param_name = self.parser.get_node_text(child, source_code)
                elif child.type == "type_annotation":
                    type_annotation_node = child

            if param_name == "req" and type_annotation_node:
                # Extract request types
                type_text = self.parser.get_node_text(type_annotation_node, source_code)
                metadata.update(self._parse_nextapi_request_type(type_text, interfaces))
            elif param_name == "res" and type_annotation_node:
                # Extract response types
                type_text = self.parser.get_node_text(type_annotation_node, source_code)
                response_schema = self._parse_nextapi_response_type(type_text, interfaces)
                if response_schema:
                    metadata["response_schema"] = response_schema

        return metadata

    def _extract_params_metadata(
        self, param_node: Node, source_code: bytes, interfaces: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Extract params metadata from App Router second parameter.

        Args:
            param_node: Parameter node
            source_code: Source code bytes
            interfaces: TypeScript interfaces

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Check if parameter has type annotation with params
        for child in param_node.children:
            if child.type == "type_annotation":
                type_text = self.parser.get_node_text(child, source_code)
                # Look for { params: { id: string } } pattern
                if "params" in type_text:
                    metadata["has_params"] = True

        return metadata

    def _parse_nextapi_request_type(
        self, type_text: str, interfaces: Dict[str, Schema]
    ) -> Dict[str, Any]:
        """
        Parse NextApiRequest type annotation.

        Args:
            type_text: Type annotation text
            interfaces: TypeScript interfaces

        Returns:
            Metadata dictionary
        """
        # For now, just return empty - could be extended to parse custom request types
        return {}

    def _parse_nextapi_response_type(
        self, type_text: str, interfaces: Dict[str, Schema]
    ) -> Schema | None:
        """
        Parse NextApiResponse type annotation.

        Args:
            type_text: Type annotation text
            interfaces: TypeScript interfaces

        Returns:
            Response schema or None
        """
        # Extract type from NextApiResponse<Type>
        match = re.search(r"NextApiResponse<([^>]+)>", type_text)
        if not match:
            return None

        response_type = match.group(1).strip()

        # Handle array types: User[]
        if "[]" in response_type:
            base_type = response_type.replace("[]", "").strip()
            if base_type in interfaces:
                return Schema(type="array", items=interfaces[base_type])
        elif response_type in interfaces:
            return interfaces[response_type]

        return None

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Next.js path syntax.

        :userId → path parameter 'userId'
        :...slug → catch-all parameter 'slug'

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Pattern 1: Catch-all parameter :...param
        catch_all_pattern = r":\.\.\.([a-zA-Z_][\w]*)"
        for match in re.finditer(catch_all_pattern, path):
            param_name = match.group(1)
            parameters.append(
                Parameter(
                    name=param_name,
                    location=ParameterLocation.PATH,
                    type="array",
                    required=True,
                    description="Catch-all route parameter (captures multiple segments)",
                )
            )

        # Pattern 2: Regular parameter :param (but not catch-all)
        regular_pattern = r":(?!\.\.\.)([a-zA-Z_][\w]*)"
        for match in re.finditer(regular_pattern, path):
            param_name = match.group(1)
            parameters.append(
                Parameter(
                    name=param_name,
                    location=ParameterLocation.PATH,
                    type="string",
                    required=True,
                )
            )

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Next.js path to OpenAPI format.

        :userId → {userId}
        :...slug → {slug}

        Args:
            path: Next.js path

        Returns:
            Normalized OpenAPI path
        """
        # Convert :...param to {param} (catch-all)
        normalized = re.sub(r":\.\.\.([a-zA-Z_][\w]*)", r"{\1}", path)

        # Convert :param to {param}
        normalized = re.sub(r":([a-zA-Z_][\w]*)", r"{\1}", normalized)

        return normalized

    def _find_interfaces(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find all TypeScript interface definitions.

        Args:
            tree: Tree-sitter Tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping interface names to Schema objects
        """
        interfaces = {}

        # Query for interface declarations
        interface_query = """
        (interface_declaration
          name: (type_identifier) @interface_name
          body: (interface_body) @interface_body)
        """

        matches = self.parser.query(tree, interface_query, "typescript")

        for match in matches:
            interface_name_node = match.get("interface_name")
            interface_body_node = match.get("interface_body")

            if not all([interface_name_node, interface_body_node]):
                continue

            interface_name = self.parser.get_node_text(interface_name_node, source_code)

            # Parse fields from interface body
            schema = self._parse_interface_body(interface_body_node, source_code)
            interfaces[interface_name] = schema

        return interfaces

    def _parse_interface_body(self, body_node: Node, source_code: bytes) -> Schema:
        """
        Parse TypeScript interface fields.

        Args:
            body_node: Interface body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        # Look for property signatures
        for child in body_node.children:
            if child.type == "property_signature":
                field_name = None
                field_type = "string"
                is_optional = False

                for field_child in child.children:
                    if field_child.type == "property_identifier":
                        field_name = self.parser.get_node_text(field_child, source_code)
                    elif field_child.type == "?":
                        is_optional = True
                    elif field_child.type == "type_annotation":
                        # Extract type from type_annotation
                        for type_child in field_child.children:
                            if type_child.type in ("type_identifier", "predefined_type", "array_type"):
                                type_text = self.parser.get_node_text(type_child, source_code)
                                field_type = self._map_typescript_type(type_text)
                                break

                if field_name:
                    properties[field_name] = {"type": field_type}
                    if not is_optional:
                        required.append(field_name)

        return Schema(type="object", properties=properties, required=required)

    def _map_typescript_type(self, type_text: str) -> str:
        """
        Map TypeScript type to OpenAPI type.

        Args:
            type_text: TypeScript type text

        Returns:
            OpenAPI type string
        """
        # Check for array first
        if "[]" in type_text or "Array<" in type_text:
            return "array"
        elif "string" in type_text:
            return "string"
        elif "number" in type_text:
            return "number"
        elif "boolean" in type_text:
            return "boolean"
        else:
            return "string"

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

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

            # Get response schema from metadata
            response_schema = route.metadata.get("response_schema")

            # Create response
            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    content_type="application/json",
                    response_schema=response_schema,
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
