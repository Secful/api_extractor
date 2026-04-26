"""Fastify framework extractor."""

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
)


class FastifyExtractor(BaseExtractor):
    """Extract API routes from Fastify applications."""

    # HTTP methods
    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "head", "options"]

    def __init__(self) -> None:
        """Initialize Fastify extractor."""
        super().__init__(FrameworkType.FASTIFY)

    def get_file_extensions(self) -> List[str]:
        """Get JavaScript/TypeScript file extensions."""
        return [".js", ".ts"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a Fastify file.

        Args:
            file_path: Path to JavaScript/TypeScript file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Determine language
        language = "javascript" if file_path.endswith(".js") else "typescript"

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, language)
        if not tree:
            return routes

        # Query for route method calls: fastify.get(), app.post(), etc.
        route_query = """
        (expression_statement
          (call_expression
            function: (member_expression
              object: (identifier) @obj_name
              property: (property_identifier) @method_name)
            arguments: (arguments) @args))
        """

        route_matches = self.parser.query(tree, route_query, language)

        for match in route_matches:
            method_name_node = match.get("method_name")
            args_node = match.get("args")
            obj_name_node = match.get("obj_name")

            if not method_name_node or not args_node or not obj_name_node:
                continue

            method_name = self.parser.get_node_text(method_name_node, source_code)

            # Check if it's a valid HTTP method
            if method_name not in self.HTTP_METHODS:
                continue

            # Extract path from first argument
            arg_nodes = [
                child
                for child in args_node.children
                if child.type not in (",", "(", ")", "comment")
            ]

            if not arg_nodes:
                continue

            path_node = arg_nodes[0]
            if path_node.type != "string":
                continue

            path = self.parser.extract_string_value(path_node, source_code)
            if not path:
                continue

            # Get location
            location = self.parser.get_node_location(obj_name_node)

            # Extract schema from route options (if present)
            schemas = self._extract_schema_from_route_options(args_node, source_code)

            # Create route
            http_method = HTTPMethod[method_name.upper()]
            route = Route(
                path=path,
                methods=[http_method],
                handler_name=None,
                framework=self.framework,
                raw_path=path,
                source_file=file_path,
                source_line=location["start_line"],
                metadata=schemas,
            )
            routes.append(route)

        return routes

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from Fastify path.

        Fastify uses :paramName syntax.

        Args:
            path: Route path

        Returns:
            List of Parameter objects
        """
        parameters = []

        # Find all :param patterns
        pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
        matches = re.finditer(pattern, path)

        for match in matches:
            param_name = match.group(1)

            param = self._create_parameter(
                name=param_name,
                location="path",
                param_type="string",
                required=True,
            )
            parameters.append(param)

        return parameters

    def _normalize_path(self, path: str) -> str:
        """
        Normalize Fastify path to OpenAPI format.

        Convert :param to {param}.

        Args:
            path: Fastify path

        Returns:
            Normalized path
        """
        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        return normalized

    def _extract_schema_from_route_options(
        self, args_node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Extract schema from Fastify route options object.

        Fastify routes can have a second argument (between path and handler) with a schema object.

        Args:
            args_node: Arguments node from route call
            source_code: Source code bytes

        Returns:
            Dictionary with request_body and responses schemas
        """
        schemas = {}

        # Get all argument nodes (excluding punctuation)
        arg_nodes = [
            child
            for child in args_node.children
            if child.type not in (",", "(", ")", "comment")
        ]

        # Schema object is in the second argument (index 1) if it exists
        if len(arg_nodes) < 2:
            return schemas

        options_node = arg_nodes[1]

        # Options must be an object literal
        if options_node.type != "object":
            return schemas

        # Find the schema property in the options object
        for pair in options_node.children:
            if pair.type != "pair":
                continue

            key_node = pair.child_by_field_name("key")
            value_node = pair.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key_text = self.parser.get_node_text(key_node, source_code)

            # Remove quotes if present
            if key_text.startswith(('"', "'")) and key_text.endswith(('"', "'")):
                key_text = key_text[1:-1]

            if key_text == "schema" and value_node.type == "object":
                # Parse the schema object
                schema_dict = self._parse_schema_object(value_node, source_code)

                # Extract body schema
                if "body" in schema_dict:
                    schemas["request_body"] = schema_dict["body"]

                # Extract response schemas
                if "response" in schema_dict:
                    response_schemas = {}
                    for status_code, response_schema in schema_dict["response"].items():
                        response_schemas[status_code] = response_schema
                    schemas["responses"] = response_schemas

        return schemas

    def _parse_schema_object(
        self, schema_node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Parse a Fastify schema object.

        Args:
            schema_node: Object node containing schema definition
            source_code: Source code bytes

        Returns:
            Dictionary mapping schema sections (body, response, etc.) to Schema objects
        """
        result = {}

        for pair in schema_node.children:
            if pair.type != "pair":
                continue

            key_node = pair.child_by_field_name("key")
            value_node = pair.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key_text = self.parser.get_node_text(key_node, source_code)

            # Remove quotes if present
            if key_text.startswith(('"', "'")) and key_text.endswith(('"', "'")):
                key_text = key_text[1:-1]

            if key_text == "body" and value_node.type == "object":
                # Parse body schema and convert to Schema object
                schema_dict = self._parse_json_schema_object(value_node, source_code)
                result["body"] = self._dict_to_schema(schema_dict)
            elif key_text == "response" and value_node.type == "object":
                # Parse response schemas (keyed by status code)
                response_schemas = {}
                for response_pair in value_node.children:
                    if response_pair.type != "pair":
                        continue

                    status_key = response_pair.child_by_field_name("key")
                    status_value = response_pair.child_by_field_name("value")

                    if not status_key or not status_value:
                        continue

                    status_code = self.parser.get_node_text(status_key, source_code)
                    # Remove quotes
                    if status_code.startswith(('"', "'")) and status_code.endswith(
                        ('"', "'")
                    ):
                        status_code = status_code[1:-1]

                    if status_value.type == "object":
                        schema_dict = self._parse_json_schema_object(
                            status_value, source_code
                        )
                        response_schemas[status_code] = self._dict_to_schema(schema_dict)

                result["response"] = response_schemas

        return result

    def _dict_to_schema(self, schema_dict: Dict[str, Any]) -> Schema:
        """
        Convert a schema dictionary to a Schema object.

        Args:
            schema_dict: Dictionary containing schema data

        Returns:
            Schema object
        """
        return Schema(
            type=schema_dict.get("type", "object"),
            properties=schema_dict.get("properties", {}),
            required=schema_dict.get("required", []),
            description=schema_dict.get("description"),
            items=schema_dict.get("items"),
        )

    def _parse_json_schema_object(
        self, json_schema_node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Parse a JSON Schema object into a dictionary.

        Args:
            json_schema_node: Object node containing JSON Schema
            source_code: Source code bytes

        Returns:
            Dictionary representing JSON Schema
        """
        schema_dict = {
            "type": "object",
            "properties": {},
            "required": [],
            "description": None,
        }

        for pair in json_schema_node.children:
            if pair.type != "pair":
                continue

            key_node = pair.child_by_field_name("key")
            value_node = pair.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key_text = self.parser.get_node_text(key_node, source_code)

            # Remove quotes if present
            if key_text.startswith(('"', "'")) and key_text.endswith(('"', "'")):
                key_text = key_text[1:-1]

            if key_text == "type":
                # Extract type
                type_value = self.parser.extract_string_value(value_node, source_code)
                if type_value:
                    schema_dict["type"] = type_value

            elif key_text == "properties" and value_node.type == "object":
                # Parse properties object
                properties = {}
                for prop_pair in value_node.children:
                    if prop_pair.type != "pair":
                        continue

                    prop_key = prop_pair.child_by_field_name("key")
                    prop_value = prop_pair.child_by_field_name("value")

                    if not prop_key or not prop_value:
                        continue

                    prop_name = self.parser.get_node_text(prop_key, source_code)
                    # Remove quotes
                    if prop_name.startswith(('"', "'")) and prop_name.endswith(
                        ('"', "'")
                    ):
                        prop_name = prop_name[1:-1]

                    if prop_value.type == "object":
                        # Recursively parse property schema
                        prop_schema = self._parse_json_schema_object(
                            prop_value, source_code
                        )
                        properties[prop_name] = prop_schema
                    else:
                        # Simple property (might be inline)
                        properties[prop_name] = {"type": "string"}

                schema_dict["properties"] = properties

            elif key_text == "required" and value_node.type == "array":
                # Extract required fields
                required = []
                for item in value_node.children:
                    if item.type == "string":
                        field_name = self.parser.extract_string_value(item, source_code)
                        if field_name:
                            required.append(field_name)
                schema_dict["required"] = required

            elif key_text == "description":
                # Extract description
                desc = self.parser.extract_string_value(value_node, source_code)
                if desc:
                    schema_dict["description"] = desc

            elif key_text == "items" and value_node.type == "object":
                # For array types, parse items schema
                schema_dict["items"] = self._parse_json_schema_object(
                    value_node, source_code
                )

        return schema_dict

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects.

        Overridden to handle schema extraction from metadata.

        Args:
            route: Route object

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters
            parameters = self._extract_path_parameters(route.raw_path)

            # Create default response
            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    content_type="application/json",
                )
            ]

            # Check for schemas in metadata
            request_body = None
            if "request_body" in route.metadata:
                request_body = route.metadata["request_body"]

            # Check for response schemas in metadata
            if "responses" in route.metadata:
                response_schemas = route.metadata["responses"]
                responses = []
                for status_code, schema in response_schemas.items():
                    responses.append(
                        Response(
                            status_code=status_code,
                            description="Success",
                            response_schema=schema,
                            content_type="application/json",
                        )
                    )
                # If no responses were added, use default
                if not responses:
                    responses = [
                        Response(
                            status_code="200",
                            description="Success",
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
