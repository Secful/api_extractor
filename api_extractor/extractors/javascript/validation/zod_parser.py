"""Zod validation schema parser."""

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


class ZodParser(BaseValidationParser):
    """Parser for Zod validation schemas."""

    # Middleware function names that use Zod
    MIDDLEWARE_PATTERNS = [
        "validateRequest",
        "validateRequestBody",
        "validateRequestQuery",
        "validateRequestParams",
        "validate",
        "zodValidator",
    ]

    def __init__(self, parser: LanguageParser) -> None:
        """
        Initialize Zod parser.

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
        Extract all Zod validation schemas from a file.

        Finds patterns like:
        - const schema = z.object({ ... })
        - import { userSchema } from './schemas'

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

        # Query for z.object() variable assignments
        # Pattern: const schema = z.object({ ... })
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

            # Check if it's a z.object() call
            if not func_text.startswith("z.object"):
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)
            location = self.parser.get_node_location(var_name_node)

            # Parse the schema
            schema = self._parse_zod_object(value_node, source_code)
            if schema:
                validation_schema = ValidationSchema(
                    name=var_name,
                    schema=schema,
                    location="body",  # Default to body
                    source_line=location["start_line"],
                    parser_type="zod",
                )
                schemas[var_name] = validation_schema

        return schemas

    def _load_imported_schemas(self, language: str) -> None:
        """
        Load schemas from imported validation files.

        Parses files like:
        import { userSchema } from './schemas';

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
        const createUser = { body: z.object({...}), query: z.object({...}) };
        export { createUser, getUser };
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
        # const createUser = { body: z.object({...}), query: z.object({...}) }
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

        # TODO: Add ES6 export statement support
        # export { createUser, getUser };
        # export const createUser = { ... };

        return exported

    def _parse_validation_object(
        self, node: Node, source_code: bytes
    ) -> Optional[ValidationSchema]:
        """
        Parse validation object structure: { body: z.object({...}), query: z.object({...}) }.

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

            # Extract schema for body, query, or params
            if key in ["body", "query", "params"] and value_node.type == "call_expression":
                schema = self._parse_zod_object(value_node, source_code)
                if schema:
                    return ValidationSchema(
                        name=None,
                        schema=schema,
                        location=key,
                        source_line=0,
                        parser_type="zod",
                    )

        return None

    def extract_inline_schema(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract schema from inline Zod validation call.

        Args:
            node: AST node containing z.object() call
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        return self._parse_zod_object(node, source_code)

    def detect_middleware_pattern(
        self, node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if node is a Zod validation middleware call.

        Patterns:
        - validateRequest(schema)
        - validateRequest(z.object({ ... }))
        - validateRequestBody(schema)
        - validateRequestQuery(schema)

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
        if "Query" in func_name:
            location = "query"
        elif "Params" in func_name:
            location = "path"
        elif "Body" in func_name:
            location = "body"

        # Extract the first argument (schema)
        schema_node = None
        for child in args_node.children:
            if child.type in ("(", ")", ",", "comment"):
                continue

            schema_node = child
            break

        if not schema_node:
            return None

        # Handle schema reference or inline schema
        schema = None
        if schema_node.type == "identifier":
            # Reference to variable: validateRequest(createUserSchema)
            schema_ref = self.parser.get_node_text(schema_node, source_code)
            return {
                "type": "zod",
                "schema_ref": schema_ref,
                "location": location,
            }
        elif schema_node.type == "member_expression":
            # Cross-file reference: validateRequest(validation.createUser)
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
                            "type": "zod",
                            "schema": validation_schema.schema,
                            "location": validation_schema.location,
                        }

                # Fallback: return as reference
                return {
                    "type": "zod",
                    "schema_ref": f"{object_name}.{property_name}",
                    "location": location,
                }
        elif schema_node.type == "call_expression":
            # Inline schema: validateRequest(z.object({...}))
            schema = self._parse_zod_object(schema_node, source_code)
            if schema:
                return {
                    "type": "zod",
                    "schema": schema,
                    "location": location,
                }

        return None

    def _parse_zod_object(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Parse z.object() call to extract schema.

        Handles:
        - z.object({ field: z.string() })
        - z.object({ field: z.string().email() })

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        if node.type != "call_expression":
            return None

        # Check if the call chain contains z.object
        func_node = node.child_by_field_name("function")
        if not func_node:
            return None

        func_text = self.parser.get_node_text(func_node, source_code)
        if not func_text.startswith("z.object"):
            return None

        # Get arguments
        args_node = node.child_by_field_name("arguments")
        if not args_node:
            return None

        # Find object literal argument
        object_node = None
        for child in args_node.children:
            if child.type == "object":
                object_node = child
                break

        if not object_node:
            return None

        # Parse object properties
        return self._parse_zod_object_properties(object_node, source_code)

    def _parse_zod_object_properties(
        self, object_node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Parse properties from Zod object literal.

        { field1: z.string().email(), field2: z.number().optional() }

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

            # Parse Zod validation chain
            if value_node.type == "call_expression":
                method_chain = self._parse_method_chain(value_node, source_code)
                schema_dict, is_required = SchemaMapper.zod_to_openapi(method_chain)

                # Store the schema dict directly (will be used in properties)
                properties[prop_name] = schema_dict

                # Zod fields are required by default
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
        Extract nested z.object() from method chain.

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            Nested schema or None
        """
        # Look through arguments for nested z.object()
        if node.type == "call_expression":
            args_node = node.child_by_field_name("arguments")
            if args_node:
                for child in args_node.children:
                    if child.type == "call_expression":
                        nested = self._parse_zod_object(child, source_code)
                        if nested:
                            return nested

        return None

    def _extract_array_items(
        self, node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Extract array items schema from z.array() argument.

        z.array(z.string())

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            Items schema dictionary or None
        """
        # Check if this is z.array() call
        method_chain = self._parse_method_chain(node, source_code)

        for i, method in enumerate(method_chain):
            if method["method"] == "array":
                # Look at the arguments of the array call
                # We need to find the actual call_expression node for z.array()
                if node.type == "call_expression":
                    args_node = node.child_by_field_name("arguments")
                    if args_node:
                        for child in args_node.children:
                            if child.type == "call_expression":
                                # Parse the items schema
                                items_chain = self._parse_method_chain(child, source_code)
                                if items_chain:
                                    items_dict, _ = SchemaMapper.zod_to_openapi(items_chain)
                                    return items_dict

        return {"type": "string"}  # Default fallback
