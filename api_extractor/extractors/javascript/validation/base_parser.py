"""Base class for validation library parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from tree_sitter import Node

from api_extractor.core.models import Schema
from api_extractor.core.parser import LanguageParser


class ValidationSchema:
    """Represents a validation schema with metadata."""

    def __init__(
        self,
        name: str | None,
        schema: Schema,
        location: str,
        source_line: int,
        parser_type: str | None = None,
    ) -> None:
        """
        Initialize validation schema.

        Args:
            name: Variable name if schema is assigned to a variable
            schema: OpenAPI schema object
            location: Type of validation (body, query, params, headers)
            source_line: Line number in source file
            parser_type: Type of parser that extracted this (joi, zod, json_schema)
        """
        self.name = name
        self.schema = schema
        self.location = location
        self.source_line = source_line
        self.parser_type = parser_type


class BaseValidationParser(ABC):
    """Abstract base class for validation library parsers."""

    def __init__(self, parser: LanguageParser) -> None:
        """
        Initialize validation parser.

        Args:
            parser: Tree-sitter code parser instance
        """
        self.parser = parser

    @abstractmethod
    def extract_schemas_from_file(
        self, tree, source_code: bytes, language: str
    ) -> Dict[str, ValidationSchema]:
        """
        Extract all validation schemas from a file.

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            language: Language (javascript or typescript)

        Returns:
            Dictionary mapping schema variable names to ValidationSchema objects
        """
        pass

    @abstractmethod
    def extract_inline_schema(
        self, node: Node, source_code: bytes
    ) -> Optional[Schema]:
        """
        Extract schema from inline validation call.

        Args:
            node: AST node containing validation definition
            source_code: Source code bytes

        Returns:
            OpenAPI Schema object or None
        """
        pass

    @abstractmethod
    def detect_middleware_pattern(
        self, node: Node, source_code: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if node is a validation middleware call.

        Args:
            node: AST node to check
            source_code: Source code bytes

        Returns:
            Dictionary with middleware info (type, schema) or None
        """
        pass

    def _parse_method_chain(
        self, node: Node, source_code: bytes
    ) -> List[Dict[str, Any]]:
        """
        Parse method call chain from AST node.

        Example: .string().email().required() → [
            {'method': 'string', 'args': []},
            {'method': 'email', 'args': []},
            {'method': 'required', 'args': []}
        ]

        Args:
            node: AST node
            source_code: Source code bytes

        Returns:
            List of method call dictionaries
        """
        chain = []
        current_node = node

        while current_node:
            if current_node.type == "call_expression":
                # Extract method name and arguments
                func_node = current_node.child_by_field_name("function")
                args_node = current_node.child_by_field_name("arguments")

                if func_node:
                    method_name = None

                    # Check if it's a member_expression (e.g., obj.method())
                    if func_node.type == "member_expression":
                        prop_node = func_node.child_by_field_name("property")
                        if prop_node:
                            method_name = self.parser.get_node_text(
                                prop_node, source_code
                            )
                        # Continue with the object for next iteration
                        current_node = func_node.child_by_field_name("object")
                    # Check if it's an identifier (e.g., method())
                    elif func_node.type == "identifier":
                        method_name = self.parser.get_node_text(func_node, source_code)
                        current_node = None
                    else:
                        current_node = None

                    if method_name:
                        # Extract arguments
                        args = []
                        if args_node:
                            args = self._extract_arguments(args_node, source_code)

                        chain.insert(0, {"method": method_name, "args": args})
                else:
                    break
            elif current_node.type == "member_expression":
                # Just a property access, not a call
                prop_node = current_node.child_by_field_name("property")
                if prop_node:
                    prop_name = self.parser.get_node_text(prop_node, source_code)
                    chain.insert(0, {"method": prop_name, "args": []})
                current_node = current_node.child_by_field_name("object")
            elif current_node.type == "identifier":
                # Base identifier
                name = self.parser.get_node_text(current_node, source_code)
                chain.insert(0, {"method": name, "args": []})
                break
            else:
                break

        return chain

    def _extract_arguments(
        self, args_node: Node, source_code: bytes
    ) -> List[Any]:
        """
        Extract arguments from arguments node.

        Args:
            args_node: Arguments AST node
            source_code: Source code bytes

        Returns:
            List of argument values
        """
        args = []

        for child in args_node.children:
            if child.type in ("(", ")", ",", "comment"):
                continue

            # Extract argument value based on type
            if child.type == "string":
                value = self.parser.extract_string_value(child, source_code)
                args.append(value)
            elif child.type == "number":
                value_text = self.parser.get_node_text(child, source_code)
                try:
                    value = int(value_text) if "." not in value_text else float(value_text)
                    args.append(value)
                except ValueError:
                    args.append(value_text)
            elif child.type in ("true", "false"):
                args.append(child.type == "true")
            elif child.type == "array":
                # Extract array elements
                array_values = self._extract_array_elements(child, source_code)
                args.append(array_values)
            elif child.type == "object":
                # For now, just capture that it's an object
                args.append({"type": "object"})
            else:
                # Fallback: capture as string
                args.append(self.parser.get_node_text(child, source_code))

        return args

    def _extract_array_elements(
        self, array_node: Node, source_code: bytes
    ) -> List[Any]:
        """
        Extract elements from array literal.

        Args:
            array_node: Array AST node
            source_code: Source code bytes

        Returns:
            List of array element values
        """
        elements = []

        for child in array_node.children:
            if child.type in ("[", "]", ",", "comment"):
                continue

            if child.type == "string":
                value = self.parser.extract_string_value(child, source_code)
                elements.append(value)
            elif child.type == "number":
                value_text = self.parser.get_node_text(child, source_code)
                try:
                    value = int(value_text) if "." not in value_text else float(value_text)
                    elements.append(value)
                except ValueError:
                    elements.append(value_text)
            elif child.type in ("true", "false"):
                elements.append(child.type == "true")
            else:
                elements.append(self.parser.get_node_text(child, source_code))

        return elements
