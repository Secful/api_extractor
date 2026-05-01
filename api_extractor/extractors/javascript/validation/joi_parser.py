"""Joi validation schema parser."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from tree_sitter import Node

from api_extractor.core.models import Schema
from api_extractor.core.parser import LanguageParser
from api_extractor.extractors.javascript.module_resolver import ModuleResolver
from api_extractor.extractors.javascript.validation.base_parser import (
    BaseValidationParser,
    ValidationSchema,
)
from api_extractor.extractors.javascript.validation.schema_mapper import SchemaMapper


class JoiParser(BaseValidationParser):
    """Parser for Joi validation schemas."""

    # Middleware function names that use Joi
    MIDDLEWARE_PATTERNS = ["validate", "celebrate", "validator"]

    def __init__(self, parser: LanguageParser) -> None:
        """
        Initialize Joi parser.

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
        Extract all Joi validation schemas from a file.

        Finds patterns like:
        - const schema = Joi.object({ ... })
        - const schema = Joi.object().keys({ ... })
        - const validation = require('./validation'); // Imports

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

        # Query for Joi.object() variable assignments
        # Pattern: const schema = Joi.object({ ... })
        schema_query = """
        (variable_declarator
          name: (identifier) @var_name
          value: (call_expression
            function: (member_expression) @func) @value)
        """

        matches = self.parser.query(tree, schema_query, language)

        for match in matches:
            var_name_node = match.get("var_name")
            func_node = match.get("func")
            value_node = match.get("value")

            if not all([var_name_node, func_node, value_node]):
                continue

            func_text = self.parser.get_node_text(func_node, source_code)

            # Check if it's a Joi.object() call
            if "Joi" not in func_text or "object" not in func_text:
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)
            location = self.parser.get_node_location(var_name_node)

            # Parse the schema
            schema = self._parse_joi_object(value_node, source_code)
            if schema:
                validation_schema = ValidationSchema(
                    name=var_name,
                    schema=schema,
                    location="body",  # Default to body, can be overridden by celebrate
                    source_line=location["start_line"],
                    parser_type="joi",
                )
                schemas[var_name] = validation_schema

        return schemas

    def _load_imported_schemas(self, language: str) -> None:
        """
        Load schemas from imported validation files.

        Parses files like:
        const validation = require('./validation');

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
        const createUser = { body: Joi.object({...}) };
        module.exports = { createUser, getUser };

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            language: Language

        Returns:
            Dictionary of exported schemas
        """
        exported = {}

        # First pass: Extract all validation object variable declarations
        # const createUser = { body: Joi.object({...}), query: Joi.object({...}) }
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

        # Second pass: Look for module.exports assignments
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
                # Handle ES6 shorthand properties: { register, login }
                if child.type == "shorthand_property_identifier":
                    prop_name = self.parser.get_node_text(child, source_code)
                    if prop_name in local_schemas:
                        exported[prop_name] = local_schemas[prop_name]
                    continue

                # Handle regular key-value pairs: { register: registerSchema }
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
        Parse validation object structure: { body: Joi.object({...}), query: Joi.object({...}) }.

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

            # For now, only extract body schema (most common)
            if key == "body" and value_node.type == "call_expression":
                schema = self._parse_joi_object(value_node, source_code)
                if schema:
                    return ValidationSchema(
                        name=None,
                        schema=schema,
                        location="body",
                        source_line=0,
                        parser_type="joi",
                    )

        return None

    def extract_inline_schema(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract schema from inline Joi validation call.

        Args:
            node: AST node containing Joi.object() call
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        return self._parse_joi_object(node, source_code)

    def detect_middleware_pattern(
        self, node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if node is a Joi validation middleware call.

        Patterns:
        - validate(schema)
        - validate(Joi.object({ ... }))
        - celebrate({ body: schema })
        - celebrate({ body: Joi.object({ ... }) })

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

        # Extract the first argument (schema or config object)
        schema_node = None
        location = "body"  # Default location

        for child in args_node.children:
            if child.type in ("(", ")", ",", "comment"):
                continue

            schema_node = child
            break

        if not schema_node:
            return None

        # Handle celebrate pattern: celebrate({ body: schema, query: schema })
        if "celebrate" in func_name and schema_node.type == "object":
            return self._parse_celebrate_config(schema_node, source_code)

        # Handle direct schema: validate(schema) or validate(Joi.object({...}))
        schema = None
        if schema_node.type == "identifier":
            # Reference to variable: validate(createUserSchema)
            schema_ref = self.parser.get_node_text(schema_node, source_code)
            # Only claim this if we actually have this schema
            # (avoids false positives when other validators use similar patterns)
            # Note: We can't check self.validation_schemas here as it's shared across parsers
            # So we return it and let Express decide based on validation_schemas lookup
            return {
                "type": "joi",
                "schema_ref": schema_ref,
                "location": location,
            }
        elif schema_node.type == "member_expression":
            # Cross-file reference: validate(validation.createUser)
            member_access = self.module_resolver.extract_member_access(
                schema_node, source_code
            )
            if member_access:
                object_name, property_name = member_access

                # Check if this refers to an imported module
                if object_name in self.imported_schemas:
                    imported_exports = self.imported_schemas[object_name]
                    if property_name in imported_exports:
                        validation_schema = imported_exports[property_name]
                        return {
                            "type": "joi",
                            "schema": validation_schema.schema,
                            "location": validation_schema.location,
                        }

                # Fallback: return as reference
                return {
                    "type": "joi",
                    "schema_ref": f"{object_name}.{property_name}",
                    "location": location,
                }
        elif schema_node.type == "call_expression":
            # Inline schema: validate(Joi.object({...}))
            schema = self._parse_joi_object(schema_node, source_code)
            if schema:
                return {
                    "type": "joi",
                    "schema": schema,
                    "location": location,
                }

        return None

    def _parse_celebrate_config(
        self, config_node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Parse celebrate configuration object.

        celebrate({ body: schema, query: schema, params: schema })

        Args:
            config_node: Object literal node
            source_code: Source code bytes

        Returns:
            Dictionary with schemas for each location
        """
        schemas = {}

        # Look for property assignments
        for child in config_node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            key = self.parser.get_node_text(key_node, source_code)

            # Parse the schema
            schema = None
            if value_node.type == "identifier":
                # Reference to variable
                schema_ref = self.parser.get_node_text(value_node, source_code)
                schemas[key] = {"schema_ref": schema_ref}
            elif value_node.type == "call_expression":
                # Inline schema
                schema = self._parse_joi_object(value_node, source_code)
                if schema:
                    schemas[key] = {"schema": schema}

        if schemas:
            return {
                "type": "joi",
                "celebrate": True,
                "schemas": schemas,
            }

        return None

    def _parse_joi_object(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Parse Joi.object() call to extract schema.

        Handles:
        - Joi.object({ field: Joi.string() })
        - Joi.object().keys({ field: Joi.string() })

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        if node.type != "call_expression":
            return None

        # Check if the call chain contains Joi.object
        func_node = node.child_by_field_name("function")
        if not func_node:
            return None

        func_text = self.parser.get_node_text(func_node, source_code)
        if "Joi" not in func_text or "object" not in func_text:
            return None

        # Get arguments
        args_node = node.child_by_field_name("arguments")
        if not args_node:
            # Could be Joi.object() without arguments, followed by .keys()
            return self._check_for_keys_method(node, source_code)

        # Find object literal argument
        object_node = None
        for child in args_node.children:
            if child.type == "object":
                object_node = child
                break

        if not object_node:
            # No inline object, check for .keys() method
            return self._check_for_keys_method(node, source_code)

        # Parse object properties
        return self._parse_joi_object_properties(object_node, source_code)

    def _check_for_keys_method(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Check if the call expression is followed by .keys() method.

        Joi.object().keys({ ... })

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        # This would require looking at the parent/sibling nodes
        # For now, return None (simpler implementation)
        return None

    def _parse_joi_object_properties(
        self, object_node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Parse properties from Joi object literal.

        { field1: Joi.string().required(), field2: Joi.number() }

        Args:
            object_node: Object literal node
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        properties = {}
        required = []

        # Iterate through object properties
        for child in object_node.children:
            if child.type != "pair":
                continue

            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")

            if not key_node or not value_node:
                continue

            # Get property name
            prop_name = self.parser.get_node_text(key_node, source_code)
            if prop_name.startswith('"') or prop_name.startswith("'"):
                prop_name = prop_name[1:-1]

            # Parse Joi validation chain
            if value_node.type == "call_expression":
                method_chain = self._parse_method_chain(value_node, source_code)
                schema_dict, is_required = SchemaMapper.joi_to_openapi(method_chain)

                # Store the schema dict directly (will be used in properties)
                properties[prop_name] = schema_dict

                if is_required:
                    required.append(prop_name)

        if not properties:
            return None

        return Schema(
            type="object",
            properties=properties,
            required=required,
        )

    def _extract_nested_object(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract nested Joi.object() from method chain.

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            Nested schema or None
        """
        # Look through arguments for nested Joi.object()
        if node.type == "call_expression":
            args_node = node.child_by_field_name("arguments")
            if args_node:
                for child in args_node.children:
                    if child.type == "call_expression":
                        nested = self._parse_joi_object(child, source_code)
                        if nested:
                            return nested

        return None

    def _extract_array_items(
        self, node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Extract array items schema from .items() method.

        Joi.array().items(Joi.string())

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            Items schema dictionary or None
        """
        # Look for .items() in the method chain
        method_chain = self._parse_method_chain(node, source_code)

        for method in method_chain:
            if method["method"] == "items" and method.get("args"):
                # The args might contain a Joi schema
                # For now, return a simple string schema
                # TODO: Parse the actual items schema
                return {"type": "string"}

        return None
