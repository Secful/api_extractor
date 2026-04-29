"""OpenAPI specification builder."""

from typing import List, Dict, Optional, Any
from api_extractor.core.models import Endpoint, Parameter, Schema, Response as EndpointResponse
from api_extractor.openapi.models import (
    OpenAPISpec,
    Info,
    PathItem,
    Operation,
    ParameterObject,
    SchemaObject,
    Response,
    MediaType,
    RequestBody,
    Tag,
)


class OpenAPIBuilder:
    """Build OpenAPI specification from extracted endpoints."""

    def __init__(
        self,
        title: str = "Extracted API",
        version: str = "1.0.0",
        description: Optional[str] = None,
    ) -> None:
        """
        Initialize builder.

        Args:
            title: API title
            version: API version
            description: API description
        """
        self.title = title
        self.version = version
        self.description = description

    def build(self, endpoints: List[Endpoint]) -> OpenAPISpec:
        """
        Build OpenAPI specification from endpoints.

        Args:
            endpoints: List of Endpoint objects

        Returns:
            OpenAPISpec object
        """
        # Group endpoints by path
        paths: Dict[str, Dict[str, Operation]] = {}

        # Collect all unique tags
        all_tags = set()

        # Collect all schemas for components section
        self.collected_schemas: Dict[str, Schema] = {}

        for endpoint in endpoints:
            path = endpoint.path
            method = endpoint.method.value.lower()

            # Convert endpoint to operation
            operation = self._endpoint_to_operation(endpoint)

            # Collect tags
            if endpoint.tags:
                all_tags.update(endpoint.tags)

            # Add to paths
            if path not in paths:
                paths[path] = {}
            paths[path][method] = operation

        # Build PathItem objects
        path_items: Dict[str, PathItem] = {}
        for path, operations in paths.items():
            path_items[path] = PathItem(**operations)

        # Build tags
        tags = [Tag(name=tag) for tag in sorted(all_tags)]

        # Build components section if schemas were collected
        components = None
        if self.collected_schemas:
            components = {"schemas": self._build_schemas_dict()}

        # Build specification
        spec = OpenAPISpec(
            openapi="3.1.0",
            info=Info(
                title=self.title,
                version=self.version,
                description=self.description,
            ),
            servers=[],
            paths=path_items,
            components=components,
            tags=tags if tags else None,
        )

        return spec

    def _endpoint_to_operation(self, endpoint: Endpoint) -> Operation:
        """
        Convert Endpoint to OpenAPI Operation.

        Args:
            endpoint: Endpoint object

        Returns:
            Operation object
        """
        # Convert parameters
        parameters = [self._parameter_to_openapi(p) for p in endpoint.parameters]

        # Convert request body
        request_body = None
        if endpoint.request_body:
            request_body = RequestBody(
                description=endpoint.request_body.description,
                content={
                    "application/json": MediaType(
                        schema_=self._schema_to_openapi(endpoint.request_body)
                    )
                },
                required=True,
            )

        # Convert responses
        responses = {}
        if endpoint.responses:
            for response in endpoint.responses:
                responses[response.status_code] = self._response_to_openapi(response)
        else:
            # Default response
            responses["200"] = Response(description="Success")

        # Build operation with extension fields
        operation_data = {
            "tags": endpoint.tags if endpoint.tags else None,
            "summary": endpoint.summary,
            "description": endpoint.description,
            "operation_id": endpoint.operation_id,
            "parameters": parameters if parameters else None,
            "request_body": request_body,
            "responses": responses,
        }

        # Add api_extractor extension fields (x-api-extractor-*)
        if endpoint.source_file:
            operation_data["x-api-extractor-source-file"] = endpoint.source_file
        if endpoint.source_line:
            operation_data["x-api-extractor-source-line"] = endpoint.source_line

        operation = Operation(**operation_data)

        return operation

    def _parameter_to_openapi(self, param: Parameter) -> ParameterObject:
        """
        Convert Parameter to OpenAPI ParameterObject.

        Args:
            param: Parameter object

        Returns:
            ParameterObject
        """
        schema = SchemaObject(type=param.type)

        if param.param_schema:
            schema = self._schema_to_openapi(param.param_schema)

        return ParameterObject.model_validate(
            {
                "name": param.name,
                "in": param.location.value,
                "description": param.description,
                "required": param.required,
                "schema": schema.model_dump(by_alias=True, exclude_none=True) if schema else None,
            }
        )

    def _schema_to_openapi(self, schema: Schema) -> SchemaObject:
        """
        Convert Schema to OpenAPI SchemaObject.
        Collects schemas with refs for components section.

        Args:
            schema: Schema object

        Returns:
            SchemaObject
        """
        if schema.ref:
            # Extract schema name from ref
            if schema.ref.startswith("#/components/schemas/"):
                schema_name = schema.ref.split("/")[-1]
                # Store the schema for components section
                if schema_name not in self.collected_schemas:
                    self.collected_schemas[schema_name] = schema
            return SchemaObject(ref=schema.ref)

        # Store schema with properties for components section
        if schema.type == "object" and schema.properties:
            # Generate a name if this is a reusable schema
            # For now, we'll let the extractor name them via refs
            pass

        openapi_schema = SchemaObject(
            type=schema.type,
            description=schema.description,
            example=schema.example,
        )

        # Add enum support
        if hasattr(schema, "enum") and schema.enum:
            openapi_schema.enum = schema.enum

        if schema.properties:
            openapi_schema.properties = {}
            for name, prop in schema.properties.items():
                if isinstance(prop, Schema):
                    openapi_schema.properties[name] = self._schema_to_openapi(prop)
                elif isinstance(prop, dict):
                    # Create SchemaObject from dict, only including non-None/non-empty values
                    cleaned_prop = {k: v for k, v in prop.items() if v not in (None, [], {})}
                    openapi_schema.properties[name] = SchemaObject(**cleaned_prop)
                else:
                    openapi_schema.properties[name] = prop

        if schema.required:
            openapi_schema.required = schema.required

        if schema.items:
            # Handle array items schema
            if isinstance(schema.items, Schema):
                openapi_schema.items = self._schema_to_openapi(schema.items)
            elif isinstance(schema.items, dict):
                openapi_schema.items = SchemaObject(**schema.items)

        return openapi_schema

    def _build_schemas_dict(self) -> Dict[str, SchemaObject]:
        """
        Build schemas dictionary for components section.

        Returns:
            Dictionary of schema names to SchemaObject
        """
        schemas = {}
        for name, schema in self.collected_schemas.items():
            # Convert to OpenAPI schema without the ref
            if schema.ref:
                # Skip - this is just a reference, actual schema should be defined elsewhere
                continue
            schemas[name] = self._schema_to_openapi(schema)
        return schemas

    def _response_to_openapi(self, response: EndpointResponse) -> Response:
        """
        Convert Response to OpenAPI Response.

        Args:
            response: EndpointResponse object

        Returns:
            Response object
        """
        content = None
        if response.response_schema:
            content = {
                response.content_type: MediaType(
                    schema_=self._schema_to_openapi(response.response_schema)
                )
            }

        return Response(description=response.description, content=content)

    def to_dict(self, spec: OpenAPISpec) -> Dict[str, Any]:
        """
        Convert OpenAPI spec to dictionary.

        Args:
            spec: OpenAPISpec object

        Returns:
            Dictionary representation
        """
        return spec.model_dump(by_alias=True, exclude_none=True)

    def to_json(self, spec: OpenAPISpec) -> str:
        """
        Convert OpenAPI spec to JSON string.

        Args:
            spec: OpenAPISpec object

        Returns:
            JSON string
        """
        import json

        return json.dumps(self.to_dict(spec), indent=2)

    def to_yaml(self, spec: OpenAPISpec) -> str:
        """
        Convert OpenAPI spec to YAML string.

        Args:
            spec: OpenAPISpec object

        Returns:
            YAML string
        """
        import yaml

        return yaml.dump(self.to_dict(spec), default_flow_style=False, sort_keys=False)
