"""JSON Schema validation parser."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from tree_sitter import Node

from api_extractor.core.models import Schema
from api_extractor.core.parser import LanguageParser
from api_extractor.extractors.javascript.module_resolver import ModuleResolver
from api_extractor.extractors.javascript.validation.base_parser import (
    BaseValidationParser,
    ValidationSchema,
)


class JSONSchemaParser(BaseValidationParser):
    """Parser for JSON Schema validation."""

    # Middleware function names that use JSON Schema
    MIDDLEWARE_PATTERNS = [
        "validate",
        "validator",
        "validateSchema",
        "validateQuery",
        "validateBody",
        "validateParams",
        "validateRequest",
        "validateRequestBody",
        "validateRequestQuery",
        "validateRequestParams",
    ]

    def __init__(self, parser: LanguageParser) -> None:
        """
        Initialize JSON Schema parser.

        Args:
            parser: Tree-sitter code parser instance
        """
        super().__init__(parser)
        self.module_resolver = ModuleResolver(parser)
        self.current_file: Optional[str] = None
        self.imported_schemas: Dict[str, Dict[str, ValidationSchema]] = {}  # module_var -> {export_name -> schema}

    def extract_schemas_from_file(
        self, tree, source_code: bytes, language: str, file_path: str = None
    ) -> Dict[str, ValidationSchema]:
        """
        Extract all JSON Schema definitions from a file.

        Finds patterns like:
        - const schema = { type: 'object', properties: {...} }
        - const schema = require('./schemas/user.json')

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            language: Language (javascript or typescript)
            file_path: Path to the file being parsed

        Returns:
            Dictionary mapping schema variable names to ValidationSchema objects
        """
        schemas = {}
        self.current_file = file_path

        # Extract imports/requires
        if file_path:
            self.module_resolver.extract_imports(tree, source_code, file_path, language)

            # Parse imported validation files
            self._load_imported_schemas(language)

        # Query for object literal assignments that look like JSON Schema
        schema_query = """
        (variable_declarator
          name: (identifier) @var_name
          value: (object) @value)
        """

        matches = self.parser.query(tree, schema_query, language)

        for match in matches:
            var_name_node = match.get("var_name")
            value_node = match.get("value")

            if not all([var_name_node, value_node]):
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)
            location = self.parser.get_node_location(var_name_node)

            # Check if object looks like JSON Schema
            if self._is_json_schema_object(value_node, source_code):
                schema = self._parse_json_schema_object(value_node, source_code)
                if schema:
                    validation_schema = ValidationSchema(
                        name=var_name,
                        schema=schema,
                        location="body",
                        source_line=location["start_line"],
                        parser_type="json_schema",
                    )
                    schemas[var_name] = validation_schema

        return schemas

    def _load_imported_schemas(self, language: str) -> None:
        """
        Load schemas from imported validation files.

        Parses files like:
        const schemas = require('./json_schema_schemas');

        Args:
            language: Language (javascript or typescript)
        """
        for var_name, module_path in self.module_resolver.imports.items():
            # Get absolute path
            absolute_path = self.module_resolver.get_imported_module_path(
                var_name, self.current_file
            )

            if not absolute_path or not os.path.exists(absolute_path):
                continue

            # Avoid circular imports
            if self.module_resolver.is_module_parsed(absolute_path):
                continue

            # Mark as parsed
            self.module_resolver.mark_module_parsed(absolute_path)

            # Parse the imported file
            try:
                with open(absolute_path, "rb") as f:
                    content = f.read()

                tree = self.parser.parse_source(content, language)
                if not tree:
                    continue

                # Extract exported schemas from this file
                exported_schemas = self._parse_exported_schemas(tree, content, language)

                if exported_schemas:
                    self.imported_schemas[var_name] = exported_schemas

            except Exception:
                # Skip files that can't be parsed
                continue

    def _parse_exported_schemas(
        self, tree, source_code: bytes, language: str
    ) -> Dict[str, ValidationSchema]:
        """
        Parse exported validation schemas from a file.

        Handles patterns like:
        const createUser = { body: {...}, query: {...} };
        export { createUser };
        module.exports = { createUser };

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            language: Language

        Returns:
            Dictionary of exported schemas
        """
        exported = {}

        # First pass: Extract all validation object variable declarations
        # const createUser = { body: {...}, query: {...} }
        local_schemas: Dict[str, ValidationSchema] = {}

        var_query = """
        (variable_declarator
          name: (identifier) @var_name
          value: (object) @value)
        """

        matches = self.parser.query(tree, var_query, language)

        for match in matches:
            var_name_node = match.get("var_name")
            value_node = match.get("value")

            if not var_name_node or not value_node:
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)

            # Check if this looks like a validation object (has body/query/params)
            schema = self._parse_validation_object(value_node, source_code)
            if schema:
                local_schemas[var_name] = schema

        # Second pass: Look for module.exports assignments (CommonJS)
        export_query = """
        (assignment_expression
          left: (member_expression
            object: (identifier) @module
            property: (property_identifier) @exports)
          right: (object) @exports_object)
        """

        matches = self.parser.query(tree, export_query, language)

        for match in matches:
            module_node = match.get("module")
            exports_node = match.get("exports")
            exports_object_node = match.get("exports_object")

            if not all([module_node, exports_node, exports_object_node]):
                continue

            module_name = self.parser.get_node_text(module_node, source_code)
            exports_name = self.parser.get_node_text(exports_node, source_code)

            if module_name != "module" or exports_name != "exports":
                continue

            # Parse each exported property
            for child in exports_object_node.children:
                # Handle ES6 shorthand properties: { createUser, getUser }
                if child.type == "shorthand_property_identifier":
                    prop_name = self.parser.get_node_text(child, source_code)
                    if prop_name in local_schemas:
                        exported[prop_name] = local_schemas[prop_name]
                    continue

                # Handle regular key-value pairs: { createUser: createUserSchema }
                if child.type == "pair":
                    key_node = child.child_by_field_name("key")
                    value_node = child.child_by_field_name("value")

                    if not key_node or not value_node:
                        continue

                    export_name = self.parser.get_node_text(key_node, source_code)

                    # Check if value is a reference to a local schema
                    if value_node.type == "identifier":
                        var_ref = self.parser.get_node_text(value_node, source_code)
                        if var_ref in local_schemas:
                            exported[export_name] = local_schemas[var_ref]
                    # Or if value is an inline object with body/query/params
                    elif value_node.type == "object":
                        schema = self._parse_validation_object(value_node, source_code)
                        if schema:
                            exported[export_name] = schema

        return exported

    def _parse_validation_object(
        self, node: Node, source_code: bytes
    ) -> Optional[ValidationSchema]:
        """
        Parse validation object structure: { body: {...}, query: {...} }.

        Args:
            node: Object literal node
            source_code: Source code bytes

        Returns:
            ValidationSchema or None
        """
        # Look for body, query, params properties
        for child in node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key = self.parser.get_node_text(key_node, source_code)
            # Remove quotes if present
            if key.startswith('"') or key.startswith("'"):
                key = key[1:-1]

            # Extract schema for body, query, or params
            if key in ["body", "query", "params"] and value_node.type == "object":
                if self._is_json_schema_object(value_node, source_code):
                    schema = self._parse_json_schema_object(value_node, source_code)
                    if schema:
                        return ValidationSchema(
                            name=None,
                            schema=schema,
                            location=key,
                            source_line=0,
                            parser_type="json_schema",
                        )

        return None

    def extract_inline_schema(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract schema from inline JSON Schema object.

        Args:
            node: AST node containing JSON Schema object
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        if self._is_json_schema_object(node, source_code):
            return self._parse_json_schema_object(node, source_code)
        return None

    def detect_middleware_pattern(
        self, node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if node is a JSON Schema validation middleware call.

        Patterns:
        - validate({ body: schema })
        - validator.validate({ body: schema })
        - validateSchema(schema)

        Args:
            node: AST node to check
            source_code: Source code bytes

        Returns:
            Dictionary with middleware info or None
        """
        if node.type != "call_expression":
            return None

        func_node = node.child_by_field_name("function")
        if not func_node:
            return None

        func_name = self.parser.get_node_text(func_node, source_code)

        # Check if it's a known validation middleware
        if not any(pattern in func_name for pattern in self.MIDDLEWARE_PATTERNS):
            return None

        args_node = node.child_by_field_name("arguments")
        if not args_node:
            return None

        # Determine location from function name
        location = "body"  # Default
        if "Query" in func_name or "query" in func_name.lower():
            location = "query"
        elif "Params" in func_name or "params" in func_name.lower():
            location = "path"
        elif "Body" in func_name or "body" in func_name.lower():
            location = "body"

        # Extract the first argument (schema or config object)
        schema_node = None

        for child in args_node.children:
            if child.type in ("(", ")", ",", "comment"):
                continue

            schema_node = child
            break

        if not schema_node:
            return None

        # Handle different argument types
        if schema_node.type == "identifier":
            # Reference to variable: validate(createUserSchema)
            schema_ref = self.parser.get_node_text(schema_node, source_code)
            return {
                "type": "json_schema",
                "schema_ref": schema_ref,
                "location": location,
            }
        elif schema_node.type == "member_expression":
            # Cross-file reference: validate(schemas.createUser.body)
            # Extract the full member access chain
            access_chain = self._extract_member_access_chain(schema_node, source_code)

            if access_chain and len(access_chain) >= 2:
                module_name = access_chain[0]

                # Check if this refers to an imported module
                if module_name in self.imported_schemas:
                    imported_exports = self.imported_schemas[module_name]

                    if len(access_chain) == 3:
                        # schemas.createUser.body
                        export_name = access_chain[1]
                        location_key = access_chain[2]

                        if export_name in imported_exports:
                            validation_schema = imported_exports[export_name]
                            # If the imported schema has the right location, use it
                            if validation_schema.location == location_key:
                                return {
                                    "type": "json_schema",
                                    "schema": validation_schema.schema,
                                    "location": location_key,
                                }
                    elif len(access_chain) == 2:
                        # schemas.createUser
                        export_name = access_chain[1]
                        if export_name in imported_exports:
                            validation_schema = imported_exports[export_name]
                            return {
                                "type": "json_schema",
                                "schema": validation_schema.schema,
                                "location": validation_schema.location,
                            }

            # Fallback: return as reference
            full_ref = ".".join(access_chain) if access_chain else self.parser.get_node_text(schema_node, source_code)
            return {
                "type": "json_schema",
                "schema_ref": full_ref,
                "location": location,
            }
        elif schema_node.type == "object":
            # Check if it's a config object: validate({ body: schema, query: schema })
            # Config objects have keys like "body", "query", "params"
            config_result = self._parse_validation_config(schema_node, source_code)
            if config_result:
                return config_result

            # Otherwise, it's an inline schema: validate({ type: 'object', properties: {...} })
            if self._is_json_schema_object(schema_node, source_code):
                schema = self._parse_json_schema_object(schema_node, source_code)
                if schema:
                    return {
                        "type": "json_schema",
                        "schema": schema,
                        "location": location,
                    }

        return None

    def _extract_member_access_chain(
        self, node: Node, source_code: bytes
    ) -> list[str]:
        """
        Extract full member access chain like 'schemas.createUser.body'.

        Args:
            node: Member expression AST node
            source_code: Source code bytes

        Returns:
            List of property names in access order
        """
        chain = []
        current = node

        while current:
            if current.type == "member_expression":
                property_node = current.child_by_field_name("property")
                if property_node:
                    prop_name = self.parser.get_node_text(property_node, source_code)
                    chain.insert(0, prop_name)

                # Continue with the object
                current = current.child_by_field_name("object")
            elif current.type == "identifier":
                # Base identifier
                name = self.parser.get_node_text(current, source_code)
                chain.insert(0, name)
                break
            else:
                break

        return chain

    def _parse_validation_config(
        self, config_node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Parse validation config object.

        { body: schema, query: schema, params: schema }

        Args:
            config_node: Object literal node
            source_code: Source code bytes

        Returns:
            Dictionary with schemas for each location, or None if not a config object
        """
        schemas = {}
        valid_locations = ["body", "query", "params", "headers"]

        for child in config_node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key = self.parser.get_node_text(key_node, source_code)
            # Remove quotes if present
            if key.startswith('"') or key.startswith("'"):
                key = key[1:-1]

            # Only process if key is a valid location (body/query/params)
            if key not in valid_locations:
                continue

            # Parse the schema
            if value_node.type == "identifier":
                schema_ref = self.parser.get_node_text(value_node, source_code)
                schemas[key] = {"schema_ref": schema_ref}
            elif value_node.type == "object":
                if self._is_json_schema_object(value_node, source_code):
                    schema = self._parse_json_schema_object(value_node, source_code)
                    if schema:
                        schemas[key] = {"schema": schema}

        # Only return if we found at least one valid location key
        if schemas:
            return {
                "type": "json_schema",
                "config": True,
                "schemas": schemas,
            }

        return None

    def _is_json_schema_object(self, node: Node, source_code: bytes) -> bool:
        """
        Check if an object literal looks like a JSON Schema.

        JSON Schema objects have: type, properties, required, etc.

        Args:
            node: Object literal node
            source_code: Source code bytes

        Returns:
            True if it looks like JSON Schema
        """
        if node.type != "object":
            return False

        # Look for JSON Schema keywords
        has_type = False
        has_properties = False

        for child in node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            if not key_node:
                continue

            key = self.parser.get_node_text(key_node, source_code)
            if key in ('"type"', "'type'", "type"):
                has_type = True
            elif key in ('"properties"', "'properties'", "properties"):
                has_properties = True

        # JSON Schema must have at least 'type' or 'properties'
        return has_type or has_properties

    def _parse_json_schema_object(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Parse JSON Schema object literal to OpenAPI Schema.

        JSON Schema is already in a format very similar to OpenAPI,
        so we mostly just convert the AST to a dict and wrap it.

        Args:
            node: Object literal node
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        if node.type != "object":
            return None

        # Convert object to dict
        schema_dict = self._object_to_dict(node, source_code)

        if not schema_dict:
            return None

        # JSON Schema to OpenAPI conversion (minimal changes needed)
        # Most JSON Schema properties are valid OpenAPI properties
        return Schema(
            type=schema_dict.get("type", "object"),
            properties=schema_dict.get("properties", {}),
            required=schema_dict.get("required", []),
            description=schema_dict.get("description"),
            enum=schema_dict.get("enum"),
            items=schema_dict.get("items"),
        )

    def _object_to_dict(self, node: Node, source_code: bytes) -> Dict[str, Any]:
        """
        Convert object literal AST node to Python dict.

        Args:
            node: Object literal node
            source_code: Source code bytes

        Returns:
            Dictionary representation of the object
        """
        result = {}

        for child in node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            # Get key
            key = self.parser.get_node_text(key_node, source_code)
            # Remove quotes from key
            if key.startswith('"') or key.startswith("'"):
                key = key[1:-1]

            # Get value
            value = self._parse_value(value_node, source_code)
            result[key] = value

        return result

    def _parse_value(self, node: Node, source_code: bytes) -> Any:
        """
        Parse a value node to Python value.

        Args:
            node: Value AST node
            source_code: Source code bytes

        Returns:
            Python value
        """
        if node.type == "string":
            return self.parser.extract_string_value(node, source_code)
        elif node.type == "number":
            text = self.parser.get_node_text(node, source_code)
            try:
                return int(text) if "." not in text else float(text)
            except ValueError:
                return text
        elif node.type in ("true", "false"):
            return node.type == "true"
        elif node.type == "null":
            return None
        elif node.type == "array":
            return self._array_to_list(node, source_code)
        elif node.type == "object":
            return self._object_to_dict(node, source_code)
        else:
            # Fallback
            return self.parser.get_node_text(node, source_code)

    def _array_to_list(self, node: Node, source_code: bytes) -> list:
        """
        Convert array literal to Python list.

        Args:
            node: Array literal node
            source_code: Source code bytes

        Returns:
            List of values
        """
        result = []

        for child in node.children:
            if child.type in ("[", "]", ",", "comment"):
                continue

            value = self._parse_value(child, source_code)
            result.append(value)

        return result
