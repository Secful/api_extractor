"""TypeScript type resolution and conversion to OpenAPI schemas.

Generic, reusable TypeScript type resolver for extracting response types
from TypeScript code and converting them to OpenAPI schemas.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from tree_sitter import Node

from api_extractor.core.models import Schema
from api_extractor.core.parser import LanguageParser
from api_extractor.extractors.javascript.module_resolver import ModuleResolver


class TypeScriptTypeResolver:
    """Resolve TypeScript types and convert to OpenAPI schemas."""

    def __init__(self, parser: LanguageParser) -> None:
        """
        Initialize TypeScript type resolver.

        Args:
            parser: Tree-sitter parser instance
        """
        self.parser = parser
        self.module_resolver = ModuleResolver(parser)
        self.current_file: Optional[str] = None
        # Cache of resolved types: type_name -> Schema
        self.type_cache: Dict[str, Schema] = {}

    def extract_response_type_from_generic(
        self, node: Node, source_code: bytes, file_path: str
    ) -> Optional[Schema]:
        """
        Extract response type from generic call expression or inline object.

        Patterns:
        - NextResponse.json<ResponseType>(...)  [generic type]
        - NextResponse.json({ foo: "bar" })     [inline object literal]

        Args:
            node: Call expression node
            source_code: Source code bytes
            file_path: Current file path

        Returns:
            Schema if type found and resolved, None otherwise
        """
        self.current_file = file_path

        # Check if this is a .json<Type> call
        if node.type != "call_expression":
            return None

        function_node = node.child_by_field_name("function")
        if not function_node or function_node.type != "member_expression":
            return None

        # Check property is "json"
        property_node = function_node.child_by_field_name("property")
        if not property_node:
            return None

        property_name = self.parser.get_node_text(property_node, source_code)
        if property_name != "json":
            return None

        # Look for type_arguments node (generic type parameters)
        type_arguments = node.child_by_field_name("type_arguments")
        if type_arguments:
            # Extract first type argument
            type_node = None
            for child in type_arguments.children:
                if child.type in ("type_identifier", "object_type", "array_type"):
                    type_node = child
                    break

            if type_node:
                # Resolve the type
                if type_node.type == "type_identifier":
                    type_name = self.parser.get_node_text(type_node, source_code)
                    return self.resolve_type_reference(type_name, file_path)
                elif type_node.type == "object_type":
                    return self.convert_object_type_to_schema(type_node, source_code)
                elif type_node.type == "array_type":
                    return self.convert_array_type_to_schema(type_node, source_code)

        # No generic type - check for inline object literal argument
        arguments_node = node.child_by_field_name("arguments")
        if not arguments_node:
            return None

        # Find first object literal in arguments
        object_literal = None
        for child in arguments_node.children:
            if child.type == "object":
                object_literal = child
                break

        if not object_literal:
            return None

        # Extract schema from object literal
        schema = self.extract_schema_from_object_literal(object_literal, source_code)
        if not schema:
            return None

        # Filter out error-only responses
        # If object ONLY has "error" field (or "error" + "message"), likely error response
        if schema.properties:
            prop_keys = set(schema.properties.keys())
            if prop_keys == {"error"} or prop_keys == {"error", "message"}:
                # Error-only response, skip
                return None

            # Also skip if status is explicitly non-2xx
            status_code = self._extract_status_code(node, source_code)
            if status_code is not None and not (200 <= status_code < 300):
                return None

        return schema

    def resolve_type_reference(
        self, type_name: str, file_path: str
    ) -> Optional[Schema]:
        """
        Resolve a type reference to its definition.

        Args:
            type_name: Name of the type to resolve
            file_path: Current file path

        Returns:
            Schema if type found, None otherwise
        """
        # Check cache
        cache_key = f"{file_path}::{type_name}"
        if cache_key in self.type_cache:
            return self.type_cache[cache_key]

        # Read and parse file
        try:
            with open(file_path, "rb") as f:
                source_code = f.read()
        except Exception:
            return None

        tree = self.parser.parse_source(source_code, "typescript")
        if not tree:
            return None

        # Extract imports
        self.module_resolver.extract_imports(tree, source_code, file_path, "typescript")

        # Look for type alias or interface in current file
        schema = self._find_type_in_file(type_name, tree, source_code, file_path)
        if schema:
            self.type_cache[cache_key] = schema
            return schema

        # Check if type is imported
        if type_name in self.module_resolver.imports:
            imported_file = self.module_resolver.get_imported_module_path(type_name, file_path)
            if imported_file and os.path.exists(imported_file):
                return self.resolve_type_reference(type_name, imported_file)

        return None

    def _find_type_in_file(
        self, type_name: str, tree, source_code: bytes, file_path: str
    ) -> Optional[Schema]:
        """
        Find type definition in file (interface, type alias, exported type).

        Args:
            type_name: Type to find
            tree: Syntax tree
            source_code: Source code bytes
            file_path: File path

        Returns:
            Schema if found, None otherwise
        """
        # Look for type alias: type Foo = { ... }
        type_alias_query = """
        (type_alias_declaration
          name: (type_identifier) @type_name
          value: (_) @type_value)
        """

        matches = self.parser.query(tree, type_alias_query, "typescript")
        for match in matches:
            name_node = match.get("type_name")
            value_node = match.get("type_value")

            if not all([name_node, value_node]):
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name == type_name:
                return self._convert_type_node_to_schema(value_node, source_code)

        # Look for interface: interface Foo { ... }
        interface_query = """
        (interface_declaration
          name: (type_identifier) @interface_name
          body: (interface_body) @interface_body)
        """

        matches = self.parser.query(tree, interface_query, "typescript")
        for match in matches:
            name_node = match.get("interface_name")
            body_node = match.get("interface_body")

            if not all([name_node, body_node]):
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name == type_name:
                return self.convert_interface_body_to_schema(body_node, source_code)

        # Look for exported type: export type Foo = { ... }
        export_type_query = """
        (export_statement
          (type_alias_declaration
            name: (type_identifier) @type_name
            value: (_) @type_value))
        """

        matches = self.parser.query(tree, export_type_query, "typescript")
        for match in matches:
            name_node = match.get("type_name")
            value_node = match.get("type_value")

            if not all([name_node, value_node]):
                continue

            name = self.parser.get_node_text(name_node, source_code)
            if name == type_name:
                return self._convert_type_node_to_schema(value_node, source_code)

        return None

    def _convert_type_node_to_schema(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Convert a TypeScript type node to OpenAPI schema.

        Args:
            node: Type node
            source_code: Source code bytes

        Returns:
            Schema if convertible, None otherwise
        """
        if node.type == "object_type":
            return self.convert_object_type_to_schema(node, source_code)
        elif node.type == "array_type":
            return self.convert_array_type_to_schema(node, source_code)
        elif node.type == "union_type":
            return self.convert_union_type_to_schema(node, source_code)
        elif node.type == "literal_type":
            return self.convert_literal_type_to_schema(node, source_code)
        elif node.type in ("predefined_type", "type_identifier"):
            return self.convert_primitive_type_to_schema(node, source_code)

        return None

    def convert_object_type_to_schema(
        self, node: Node, source_code: bytes
    ) -> Schema:
        """
        Convert TypeScript object type to OpenAPI schema.

        Pattern: { foo: string; bar: number }

        Args:
            node: Object type node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        for child in node.children:
            if child.type == "property_signature":
                prop_schema = self._parse_property_signature(child, source_code)
                if prop_schema:
                    prop_name, prop_type, is_required = prop_schema
                    properties[prop_name] = prop_type
                    if is_required:
                        required.append(prop_name)

        return Schema(
            type="object",
            properties=properties,
            required=required if required else None,
        )

    def convert_interface_body_to_schema(
        self, node: Node, source_code: bytes
    ) -> Schema:
        """
        Convert TypeScript interface body to OpenAPI schema.

        Args:
            node: Interface body node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        properties = {}
        required = []

        for child in node.children:
            if child.type == "property_signature":
                prop_schema = self._parse_property_signature(child, source_code)
                if prop_schema:
                    prop_name, prop_type, is_required = prop_schema
                    properties[prop_name] = prop_type
                    if is_required:
                        required.append(prop_name)

        return Schema(
            type="object",
            properties=properties,
            required=required if required else None,
        )

    def _parse_property_signature(
        self, node: Node, source_code: bytes
    ) -> Optional[tuple[str, Dict[str, Any], bool]]:
        """
        Parse property signature from interface/object type.

        Args:
            node: Property signature node
            source_code: Source code bytes

        Returns:
            Tuple of (property_name, property_schema_dict, is_required)
        """
        prop_name = None
        prop_type = {"type": "string"}  # default
        is_required = True

        for child in node.children:
            if child.type == "property_identifier":
                prop_name = self.parser.get_node_text(child, source_code)
            elif child.type == "?":
                is_required = False
            elif child.type == "type_annotation":
                # Extract type from type_annotation
                type_node = child.child_by_field_name("type")
                if type_node:
                    prop_type = self._type_node_to_openapi_type(type_node, source_code)

        if not prop_name:
            return None

        return (prop_name, prop_type, is_required)

    def _type_node_to_openapi_type(
        self, node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Convert TypeScript type node to OpenAPI type dict.

        Args:
            node: Type node
            source_code: Source code bytes

        Returns:
            OpenAPI type dictionary
        """
        if node.type == "predefined_type":
            type_text = self.parser.get_node_text(node, source_code)
            return self._map_typescript_primitive(type_text)
        elif node.type == "array_type":
            # Handle array: string[]
            element_type_node = node.child_by_field_name("element")
            if element_type_node:
                items = self._type_node_to_openapi_type(element_type_node, source_code)
                return {"type": "array", "items": items}
            return {"type": "array"}
        elif node.type == "union_type":
            # Handle union: string | number
            # For now, just take first type (simplified)
            for child in node.children:
                if child.type in ("predefined_type", "type_identifier", "literal_type"):
                    return self._type_node_to_openapi_type(child, source_code)
            return {"type": "string"}
        elif node.type == "literal_type":
            # Handle literal: "foo", 123, true
            literal_node = node.children[0] if node.children else None
            if literal_node:
                if literal_node.type in ("string", "template_string"):
                    return {"type": "string"}
                elif literal_node.type == "number":
                    return {"type": "number"}
                elif literal_node.type in ("true", "false"):
                    return {"type": "boolean"}
            return {"type": "string"}
        elif node.type == "type_identifier":
            # Reference to another type - could resolve but for now treat as string
            return {"type": "string"}

        return {"type": "string"}

    def _map_typescript_primitive(self, type_text: str) -> Dict[str, Any]:
        """
        Map TypeScript primitive to OpenAPI type.

        Args:
            type_text: TypeScript type string

        Returns:
            OpenAPI type dictionary
        """
        mapping = {
            "string": {"type": "string"},
            "number": {"type": "number"},
            "boolean": {"type": "boolean"},
            "any": {},
            "unknown": {},
            "void": {},
            "null": {"type": "null"},
        }
        return mapping.get(type_text, {"type": "string"})

    def convert_array_type_to_schema(
        self, node: Node, source_code: bytes
    ) -> Schema:
        """
        Convert TypeScript array type to OpenAPI schema.

        Args:
            node: Array type node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        element_node = node.child_by_field_name("element")
        if element_node:
            items_dict = self._type_node_to_openapi_type(element_node, source_code)
            return Schema(type="array", items=items_dict)

        return Schema(type="array")

    def convert_union_type_to_schema(
        self, node: Node, source_code: bytes
    ) -> Schema:
        """
        Convert TypeScript union type to OpenAPI schema.

        Args:
            node: Union type node
            source_code: Source code bytes

        Returns:
            Schema object (simplified - takes first type)
        """
        # Simplified: just take first type
        # Full implementation would use oneOf
        for child in node.children:
            if child.type in ("predefined_type", "type_identifier", "object_type"):
                result = self._convert_type_node_to_schema(child, source_code)
                if result:
                    return result

        return Schema(type="string")

    def convert_literal_type_to_schema(
        self, node: Node, source_code: bytes
    ) -> Schema:
        """
        Convert TypeScript literal type to OpenAPI schema.

        Args:
            node: Literal type node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        # Get literal value
        literal_node = node.children[0] if node.children else None
        if literal_node:
            if literal_node.type in ("string", "template_string"):
                return Schema(type="string")
            elif literal_node.type == "number":
                return Schema(type="number")
            elif literal_node.type in ("true", "false"):
                return Schema(type="boolean")

        return Schema(type="string")

    def convert_primitive_type_to_schema(
        self, node: Node, source_code: bytes
    ) -> Schema:
        """
        Convert TypeScript primitive type to OpenAPI schema.

        Args:
            node: Type node
            source_code: Source code bytes

        Returns:
            Schema object
        """
        type_text = self.parser.get_node_text(node, source_code)
        type_dict = self._map_typescript_primitive(type_text)

        return Schema(
            type=type_dict.get("type", "string"),
            properties=type_dict.get("properties"),
            items=type_dict.get("items"),
        )

    def extract_schema_from_object_literal(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract OpenAPI schema from JavaScript/TypeScript object literal.

        Pattern: { foo: "bar", count: 123, items: [...] }

        Args:
            node: Object literal node
            source_code: Source code bytes

        Returns:
            Schema object with inferred types
        """
        if node.type != "object":
            return None

        properties = {}
        required = []

        # Iterate through object properties
        for child in node.children:
            if child.type == "pair":
                prop_schema = self._parse_object_pair(child, source_code)
                if prop_schema:
                    prop_name, prop_type = prop_schema
                    properties[prop_name] = prop_type
                    # All properties in literal objects are required by default
                    required.append(prop_name)

        if not properties:
            return None

        return Schema(
            type="object",
            properties=properties,
            required=required if required else None,
        )

    def _parse_object_pair(
        self, node: Node, source_code: bytes
    ) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Parse key-value pair from object literal.

        Args:
            node: Pair node
            source_code: Source code bytes

        Returns:
            Tuple of (property_name, property_schema_dict) or None to skip
        """
        key_node = node.child_by_field_name("key")
        value_node = node.child_by_field_name("value")

        if not key_node or not value_node:
            return None

        # Skip call expressions and identifiers (variables/functions)
        # Can't reliably infer their types at runtime
        if value_node.type in ("call_expression", "identifier"):
            return None

        # Extract property name
        prop_name = self.parser.get_node_text(key_node, source_code)
        # Remove quotes if present
        prop_name = prop_name.strip('"\'')

        # Infer type from value
        prop_type = self._infer_type_from_value(value_node, source_code)

        return (prop_name, prop_type)

    def _infer_type_from_value(
        self, node: Node, source_code: bytes
    ) -> Dict[str, Any]:
        """
        Infer OpenAPI type from JavaScript value node.

        Args:
            node: Value node
            source_code: Source code bytes

        Returns:
            OpenAPI type dictionary
        """
        if node.type == "string":
            return {"type": "string"}
        elif node.type == "template_string":
            return {"type": "string"}
        elif node.type == "number":
            return {"type": "number"}
        elif node.type == "true" or node.type == "false":
            return {"type": "boolean"}
        elif node.type == "null":
            return {"type": "null"}
        elif node.type == "array":
            # Infer array item type from first element
            items_type = {"type": "string"}  # default
            for child in node.children:
                if child.type not in ("[", "]", ","):
                    items_type = self._infer_type_from_value(child, source_code)
                    break
            return {"type": "array", "items": items_type}
        elif node.type == "object":
            # Nested object
            schema = self.extract_schema_from_object_literal(node, source_code)
            if schema:
                return {
                    "type": "object",
                    "properties": schema.properties,
                    "required": schema.required,
                }
            return {"type": "object"}
        elif node.type == "identifier":
            # Variable reference - can't infer type
            return {"type": "string"}
        elif node.type == "call_expression":
            # Function call result - can't infer type
            return {"type": "string"}

        return {"type": "string"}

    def _extract_status_code(
        self, node: Node, source_code: bytes
    ) -> Optional[int]:
        """
        Extract status code from NextResponse.json(body, { status: 400 }) pattern.

        Args:
            node: Call expression node
            source_code: Source code bytes

        Returns:
            Status code integer or None
        """
        arguments_node = node.child_by_field_name("arguments")
        if not arguments_node:
            return None

        # Look for second argument (options object)
        args = [child for child in arguments_node.children if child.type == "object"]
        if len(args) < 2:
            return None

        options_obj = args[1]

        # Find "status" property
        for child in options_obj.children:
            if child.type == "pair":
                key_node = child.child_by_field_name("key")
                value_node = child.child_by_field_name("value")

                if key_node and value_node:
                    key = self.parser.get_node_text(key_node, source_code)
                    if key == "status" and value_node.type == "number":
                        try:
                            return int(self.parser.get_node_text(value_node, source_code))
                        except ValueError:
                            return None

        return None
