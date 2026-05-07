"""Express-zod-api extractor for declarative routing with Zod schemas."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.models import (
    Endpoint,
    ExtractionResult,
    HTTPMethod,
    Route,
    FrameworkType,
)
from api_extractor.extractors.javascript.module_resolver import ModuleResolver
from api_extractor.extractors.javascript.validation import ZodParser


@dataclass
class RouteDefinition:
    """Represents a route from the routing tree."""
    path: str
    endpoint_name: str
    file_path: Optional[str] = None
    method: Optional[str] = None


class ExpressZodAPIExtractor(BaseExtractor):
    """Extractor for express-zod-api framework."""

    def __init__(self):
        """Initialize extractor."""
        super().__init__(FrameworkType.EXPRESS_ZOD_API)
        self.module_resolver = ModuleResolver(self.parser)
        self.zod_parser = ZodParser(self.parser)
        self._processed_files: Set[str] = set()

    def get_file_extensions(self) -> List[str]:
        """Get file extensions."""
        return [".js", ".ts"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """Not used - express-zod-api uses custom extraction logic."""
        return []

    def _extract_path_parameters(self, path: str) -> List:
        """Extract path parameters from express-zod-api path."""
        from api_extractor.core.models import Parameter, ParameterLocation
        import re

        # Express-zod-api uses :param syntax
        params = []
        for match in re.finditer(r':([a-zA-Z_][a-zA-Z0-9_]*)', path):
            params.append(Parameter(
                name=match.group(1),
                location=ParameterLocation.PATH,
                type="string",
                required=True
            ))
        return params

    def _normalize_path(self, path: str) -> str:
        """Normalize path to OpenAPI format."""
        import re
        # Convert :param to {param}
        return re.sub(r':([a-zA-Z_][a-zA-Z0-9_]*)', r'{\1}', path)

    def extract(self, path: str) -> ExtractionResult:
        """
        Extract API endpoints from express-zod-api project.

        Args:
            path: Path to project directory

        Returns:
            ExtractionResult with extracted endpoints
        """
        endpoints = []
        errors = []

        try:
            # Find routing.ts or routing.js
            routing_file = self._find_routing_file(path)
            if not routing_file:
                return ExtractionResult(
                    success=False,
                    endpoints=[],
                    errors=["Could not find routing.ts or routing.js"],
                    frameworks_detected=[self.framework]
                )

            # Parse routing tree
            routes = self._extract_routes_from_routing_file(routing_file)

            # Extract endpoint details for each route
            for route in routes:
                if not route.file_path:
                    continue
                try:
                    endpoint = self._extract_endpoint_from_route(route, path)
                    if endpoint:
                        endpoints.append(endpoint)
                except Exception as e:
                    errors.append(f"Error extracting route {route.path}: {str(e)}")

        except Exception as e:
            return ExtractionResult(
                success=False,
                endpoints=[],
                errors=[f"Extraction failed: {str(e)}"],
                frameworks_detected=[self.framework]
            )

        return ExtractionResult(
            success=len(endpoints) > 0,
            endpoints=endpoints,
            errors=errors or [],
            frameworks_detected=[self.framework]
        )

    def _find_routing_file(self, source_path: str) -> Optional[str]:
        """Find routing.ts or routing.js file."""
        for root, _, files in os.walk(source_path):
            for file in files:
                if file in ("routing.ts", "routing.js"):
                    return os.path.join(root, file)
        return None

    def _extract_routes_from_routing_file(self, routing_file: str) -> List[RouteDefinition]:
        """
        Extract routes from routing file.

        Parses the routing object tree and builds path/endpoint mappings.
        """
        routes = []

        source_code = self._read_file(routing_file)
        if not source_code:
            return routes

        language = "typescript" if routing_file.endswith(".ts") else "javascript"
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return routes

        # Find routing export: export const routing = { ... }
        routing_query = """
        (export_statement
          declaration: (lexical_declaration
            (variable_declarator
              name: (identifier) @name
              value: (object) @routing_obj)))
        """

        matches = self.parser.query(tree, routing_query, language)

        for match in matches:
            name_node = match.get("name")
            routing_obj_node = match.get("routing_obj")

            if not name_node or not routing_obj_node:
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name != "routing":
                continue

            # Parse routing object tree
            routes.extend(self._parse_routing_object(
                routing_obj_node, source_code, routing_file, []
            ))

        return routes

    def _parse_routing_object(
        self,
        obj_node,
        source_code: bytes,
        file_path: str,
        path_parts: List[str]
    ) -> List[RouteDefinition]:
        """
        Recursively parse routing object tree.

        Args:
            obj_node: Object node to parse
            source_code: Source code bytes
            file_path: Current file path
            path_parts: Accumulated path segments

        Returns:
            List of RouteDefinition objects
        """
        routes = []

        for child in obj_node.children:
            if child.type != "pair":
                continue

            # Get key
            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key = self._extract_object_key(key_node, source_code)
            if not key:
                continue

            # Check if key specifies method
            method = None
            is_http_method = False
            # Format 1: "post /v1/forms/feedback"
            if " " in key:
                parts = key.split(" ", 1)
                if parts[0].upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    method = parts[0].upper()
                    key = parts[1]
            # Format 2: key is HTTP verb: patch: endpoint
            elif key.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                method = key.upper()
                is_http_method = True

            # Build current path
            # Don't include HTTP method in path
            if not is_http_method:
                current_path_parts = path_parts + [key]
            else:
                current_path_parts = path_parts

            # If value is another object, recurse
            if value_node.type == "object":
                routes.extend(self._parse_routing_object(
                    value_node, source_code, file_path, current_path_parts
                ))
            else:
                # Value is endpoint reference (identifier or call_expression)
                endpoint_name = self._extract_endpoint_reference(value_node, source_code)
                if endpoint_name:
                    # Build full path
                    path = "/" + "/".join(current_path_parts)
                    routes.append(RouteDefinition(
                        path=path,
                        endpoint_name=endpoint_name,
                        file_path=file_path,
                        method=method
                    ))

        return routes

    def _extract_object_key(self, key_node, source_code: bytes) -> Optional[str]:
        """Extract key from object pair."""
        if key_node.type == "property_identifier":
            return self.parser.get_node_text(key_node, source_code)
        elif key_node.type == "string":
            return self.parser.extract_string_value(key_node, source_code)
        elif key_node.type == "computed_property_name":
            # Handle [key]: value
            expr = key_node.child(1)  # Get expression inside []
            if expr and expr.type == "string":
                return self.parser.extract_string_value(expr, source_code)
        return None

    def _extract_endpoint_reference(self, value_node, source_code: bytes) -> Optional[str]:
        """Extract endpoint identifier from value node."""
        if value_node.type == "identifier":
            return self.parser.get_node_text(value_node, source_code)
        elif value_node.type == "call_expression":
            # Handle endpoint.deprecated()
            obj = value_node.child_by_field_name("function")
            if obj and obj.type == "member_expression":
                obj_node = obj.child_by_field_name("object")
                if obj_node and obj_node.type == "identifier":
                    return self.parser.get_node_text(obj_node, source_code)
        return None

    def _extract_endpoint_from_route(
        self,
        route: RouteDefinition,
        source_path: str
    ) -> Optional[Endpoint]:
        """
        Extract endpoint details from route definition.

        Resolves endpoint import and parses factory.build() config.
        """
        # Find endpoint file by resolving import
        endpoint_file = self._resolve_endpoint_import(
            route.file_path, route.endpoint_name, source_path
        )

        if not endpoint_file or not os.path.exists(endpoint_file):
            return None

        # Parse endpoint file
        source_code = self._read_file(endpoint_file)
        if not source_code:
            return None

        language = "typescript" if endpoint_file.endswith(".ts") else "javascript"
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return None

        # Find endpoint export
        endpoint_config = self._extract_endpoint_config(
            tree, source_code, language, route.endpoint_name
        )

        if not endpoint_config:
            return None

        # Build Endpoint object
        method = route.method or endpoint_config.get("method", "GET").upper()

        # Build responses list if output schema exists
        responses = []
        output_schema = endpoint_config.get("output_schema")
        if output_schema:
            from api_extractor.core.models import Response
            responses.append(Response(
                status_code="200",
                description="Success",
                schema=output_schema
            ))

        return Endpoint(
            path=route.path,
            method=HTTPMethod(method),
            request_body=endpoint_config.get("input_schema"),
            responses=responses,
            summary=endpoint_config.get("description"),
            tags=endpoint_config.get("tags", []),
            parameters=[]
        )

    def _resolve_endpoint_import(
        self,
        routing_file: str,
        endpoint_name: str,
        source_path: str
    ) -> Optional[str]:
        """Resolve endpoint import to file path."""
        source_code = self._read_file(routing_file)
        if not source_code:
            return None

        language = "typescript" if routing_file.endswith(".ts") else "javascript"
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return None

        # Find import for endpoint
        import_query = """
        (import_statement
          (import_clause
            (named_imports
              (import_specifier
                (identifier) @imported_name)))
          (string) @source)
        """

        matches = self.parser.query(tree, import_query, language)

        for match in matches:
            imported_name_node = match.get("imported_name")
            source_node = match.get("source")

            if not imported_name_node or not source_node:
                continue

            imported_name = self.parser.get_node_text(imported_name_node, source_code)
            if imported_name != endpoint_name:
                continue

            import_path = self.parser.extract_string_value(source_node, source_code)
            if not import_path:
                continue

            # Resolve relative path
            return self.module_resolver._resolve_module_path(
                import_path, routing_file
            )

        return None

    def _extract_endpoint_config(
        self,
        tree,
        source_code: bytes,
        language: str,
        endpoint_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract endpoint configuration from factory.build() call.

        Looks for: export const endpointName = factory.build({ ... })
        """
        # Query for export with factory.build()
        query = """
        (export_statement
          declaration: (lexical_declaration
            (variable_declarator
              name: (identifier) @name
              value: (call_expression
                function: (member_expression
                  property: (property_identifier) @method_name)
                arguments: (arguments
                  (object) @config)))))
        """

        matches = self.parser.query(tree, query, language)

        for match in matches:
            name_node = match.get("name")
            method_name_node = match.get("method_name")
            config_node = match.get("config")

            if not name_node or not method_name_node or not config_node:
                continue

            name = self.parser.get_node_text(name_node, source_code)
            method_name = self.parser.get_node_text(method_name_node, source_code)

            if name != endpoint_name or method_name != "build":
                continue

            # Parse config object
            return self._parse_endpoint_config(config_node, source_code, language)

        return None

    def _parse_endpoint_config(
        self,
        config_node,
        source_code: bytes,
        language: str
    ) -> Dict[str, Any]:
        """Parse factory.build() config object."""
        config = {}

        for child in config_node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key = self._extract_object_key(key_node, source_code)
            if not key:
                continue

            if key == "method":
                if value_node.type == "string":
                    config["method"] = self.parser.extract_string_value(value_node, source_code)
            elif key == "description":
                if value_node.type == "string":
                    config["description"] = self.parser.extract_string_value(value_node, source_code)
            elif key == "tag":
                if value_node.type == "string":
                    tag = self.parser.extract_string_value(value_node, source_code)
                    if tag:
                        config["tags"] = [tag]
            elif key == "input":
                # Parse Zod schema
                schema = self.zod_parser.extract_inline_schema(value_node, source_code)
                if schema:
                    config["input_schema"] = schema
            elif key == "output":
                # Parse Zod schema
                schema = self.zod_parser.extract_inline_schema(value_node, source_code)
                if schema:
                    config["output_schema"] = schema

        return config

    def _read_file(self, file_path: str) -> Optional[bytes]:
        """Read file and return as bytes."""
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception:
            return None
