"""Map validation schemas to OpenAPI format."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api_extractor.core.models import Schema


class SchemaMapper:
    """Utility to convert validation library schemas to OpenAPI schemas."""

    @staticmethod
    def joi_to_openapi(
        method_chain: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Convert Joi method chain to OpenAPI schema properties.

        Args:
            method_chain: List of method calls from Joi schema

        Returns:
            OpenAPI schema dictionary
        """
        schema_dict: Dict[str, Any] = {}
        is_required = False

        for method in method_chain:
            method_name = method["method"]
            args = method.get("args", [])

            # Type methods
            if method_name == "string":
                schema_dict["type"] = "string"
            elif method_name == "number":
                schema_dict["type"] = "number"
            elif method_name == "integer":
                schema_dict["type"] = "integer"
            elif method_name == "boolean":
                schema_dict["type"] = "boolean"
            elif method_name == "array":
                schema_dict["type"] = "array"
            elif method_name == "object":
                schema_dict["type"] = "object"
            elif method_name == "date":
                schema_dict["type"] = "string"
                schema_dict["format"] = "date-time"

            # Validation methods
            elif method_name == "required":
                is_required = True
            elif method_name == "optional":
                is_required = False
            elif method_name == "email":
                schema_dict["format"] = "email"
            elif method_name == "uri" or method_name == "url":
                schema_dict["format"] = "uri"
            elif method_name == "uuid":
                schema_dict["format"] = "uuid"
            elif method_name == "min" and args:
                if schema_dict.get("type") == "string":
                    schema_dict["minLength"] = args[0]
                elif schema_dict.get("type") in ("number", "integer"):
                    schema_dict["minimum"] = args[0]
                elif schema_dict.get("type") == "array":
                    schema_dict["minItems"] = args[0]
            elif method_name == "max" and args:
                if schema_dict.get("type") == "string":
                    schema_dict["maxLength"] = args[0]
                elif schema_dict.get("type") in ("number", "integer"):
                    schema_dict["maximum"] = args[0]
                elif schema_dict.get("type") == "array":
                    schema_dict["maxItems"] = args[0]
            elif method_name == "length" and args:
                if schema_dict.get("type") == "string":
                    schema_dict["minLength"] = args[0]
                    schema_dict["maxLength"] = args[0]
                elif schema_dict.get("type") == "array":
                    schema_dict["minItems"] = args[0]
                    schema_dict["maxItems"] = args[0]
            elif method_name == "pattern" and args:
                schema_dict["pattern"] = args[0]
            elif method_name == "valid" and args:
                # Joi.valid('a', 'b', 'c') or Joi.valid(['a', 'b', 'c'])
                if args and isinstance(args[0], list):
                    schema_dict["enum"] = args[0]
                else:
                    schema_dict["enum"] = args
            elif method_name == "allow" and args:
                # Similar to valid but for allowed values
                if args and isinstance(args[0], list):
                    schema_dict["enum"] = args[0]
                else:
                    schema_dict["enum"] = args
            elif method_name == "default" and args:
                schema_dict["default"] = args[0]
            elif method_name == "description" and args:
                schema_dict["description"] = args[0]
            elif method_name == "example" and args:
                schema_dict["example"] = args[0]

        # Default to string if no type specified
        if "type" not in schema_dict:
            schema_dict["type"] = "string"

        return schema_dict, is_required

    @staticmethod
    def zod_to_openapi(
        method_chain: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Convert Zod method chain to OpenAPI schema properties.

        Args:
            method_chain: List of method calls from Zod schema

        Returns:
            OpenAPI schema dictionary and required flag
        """
        schema_dict: Dict[str, Any] = {}
        is_required = True  # Zod fields are required by default

        for method in method_chain:
            method_name = method["method"]
            args = method.get("args", [])

            # Type methods
            if method_name == "string":
                schema_dict["type"] = "string"
            elif method_name == "number":
                schema_dict["type"] = "number"
            elif method_name == "int" or method_name == "integer":
                schema_dict["type"] = "integer"
            elif method_name == "boolean":
                schema_dict["type"] = "boolean"
            elif method_name == "array":
                schema_dict["type"] = "array"
            elif method_name == "object":
                schema_dict["type"] = "object"
            elif method_name == "date":
                schema_dict["type"] = "string"
                schema_dict["format"] = "date-time"

            # Validation methods
            elif method_name == "optional":
                is_required = False
            elif method_name == "nullable":
                # In OpenAPI 3.1, use type: [string, null]
                current_type = schema_dict.get("type", "string")
                schema_dict["type"] = [current_type, "null"]
            elif method_name == "email":
                schema_dict["format"] = "email"
            elif method_name == "url":
                schema_dict["format"] = "uri"
            elif method_name == "uuid":
                schema_dict["format"] = "uuid"
            elif method_name == "min" and args:
                if schema_dict.get("type") == "string":
                    schema_dict["minLength"] = args[0]
                elif schema_dict.get("type") in ("number", "integer"):
                    schema_dict["minimum"] = args[0]
                elif schema_dict.get("type") == "array":
                    schema_dict["minItems"] = args[0]
            elif method_name == "max" and args:
                if schema_dict.get("type") == "string":
                    schema_dict["maxLength"] = args[0]
                elif schema_dict.get("type") in ("number", "integer"):
                    schema_dict["maximum"] = args[0]
                elif schema_dict.get("type") == "array":
                    schema_dict["maxItems"] = args[0]
            elif method_name == "length" and args:
                if schema_dict.get("type") == "string":
                    schema_dict["minLength"] = args[0]
                    schema_dict["maxLength"] = args[0]
            elif method_name == "regex" and args:
                # Convert regex to string pattern
                schema_dict["pattern"] = str(args[0])
            elif method_name == "enum" and args:
                # z.enum(['a', 'b', 'c'])
                if args and isinstance(args[0], list):
                    schema_dict["enum"] = args[0]
                else:
                    schema_dict["enum"] = args
            elif method_name == "literal" and args:
                # z.literal('value') - single allowed value
                schema_dict["enum"] = [args[0]]
            elif method_name == "default" and args:
                schema_dict["default"] = args[0]
            elif method_name == "describe" and args:
                schema_dict["description"] = args[0]

        # Default to string if no type specified
        if "type" not in schema_dict:
            schema_dict["type"] = "string"

        return schema_dict, is_required

    @staticmethod
    def create_object_schema(
        properties: Dict[str, Schema],
        required: List[str]
    ) -> Schema:
        """
        Create OpenAPI object schema from properties.

        Args:
            properties: Dictionary of property schemas
            required: List of required property names

        Returns:
            OpenAPI Schema object
        """
        return Schema(
            type="object",
            properties={
                name: {
                    "type": schema.type,
                    **(schema.properties or {}),
                    **({"format": schema.format} if schema.format else {}),
                    **({"minimum": schema.minimum} if schema.minimum is not None else {}),
                    **({"maximum": schema.maximum} if schema.maximum is not None else {}),
                    **({"minLength": schema.min_length} if schema.min_length is not None else {}),
                    **({"maxLength": schema.max_length} if schema.max_length is not None else {}),
                    **({"pattern": schema.pattern} if schema.pattern else {}),
                    **({"enum": schema.enum} if schema.enum else {}),
                    **({"default": schema.default} if schema.default is not None else {}),
                    **({"description": schema.description} if schema.description else {}),
                }
                for name, schema in properties.items()
            },
            required=required,
        )

    @staticmethod
    def dict_to_schema(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert schema dictionary to a format compatible with Schema model.

        For primitive types, returns a dict with validation rules.
        For object types, returns a Schema object.

        Args:
            schema_dict: Dictionary with schema properties

        Returns:
            Schema dict or Schema object
        """
        # Return the schema_dict as-is for now
        # It will be used in the properties dict of the parent object schema
        return schema_dict
