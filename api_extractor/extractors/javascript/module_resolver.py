"""Module resolver for tracking and resolving cross-file imports."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Set

from tree_sitter import Node

from api_extractor.core.parser import LanguageParser


class ModuleResolver:
    """Resolves module imports and tracks dependencies."""

    def __init__(self, parser: LanguageParser) -> None:
        """
        Initialize module resolver.

        Args:
            parser: Tree-sitter parser instance
        """
        self.parser = parser
        self.imports: Dict[str, str] = {}  # var_name -> module_path
        self.resolved_paths: Dict[str, str] = {}  # module_path -> absolute_path
        self.parsed_modules: Set[str] = set()  # Avoid circular imports

    def extract_imports(
        self, tree, source_code: bytes, file_path: str, language: str
    ) -> None:
        """
        Extract all require() and import statements from a file.

        Args:
            tree: Tree-sitter syntax tree
            source_code: Source code bytes
            file_path: Current file path
            language: Language (javascript or typescript)
        """
        # Query for require() statements
        require_query = """
        (variable_declarator
          name: (identifier) @var_name
          value: (call_expression
            function: (identifier) @func_name
            arguments: (arguments
              (string) @module_path)))
        """

        matches = self.parser.query(tree, require_query, language)

        for match in matches:
            func_name_node = match.get("func_name")
            var_name_node = match.get("var_name")
            module_path_node = match.get("module_path")

            if not all([func_name_node, var_name_node, module_path_node]):
                continue

            func_name = self.parser.get_node_text(func_name_node, source_code)
            if func_name != "require":
                continue

            var_name = self.parser.get_node_text(var_name_node, source_code)
            module_path = self.parser.extract_string_value(
                module_path_node, source_code
            )

            # Store the import
            self.imports[var_name] = module_path

            # Resolve to absolute path
            absolute_path = self._resolve_module_path(module_path, file_path)
            if absolute_path:
                self.resolved_paths[module_path] = absolute_path

        # Query for ES6 import statements
        import_query = """
        (import_statement
          source: (string) @module_path)
        """

        matches = self.parser.query(tree, import_query, language)

        for match in matches:
            module_path_node = match.get("module_path")
            if not module_path_node:
                continue

            module_path = self.parser.extract_string_value(
                module_path_node, source_code
            )

            # Resolve to absolute path
            absolute_path = self._resolve_module_path(module_path, file_path)
            if absolute_path:
                self.resolved_paths[module_path] = absolute_path

    def get_imported_module_path(self, var_name: str, current_file: str) -> Optional[str]:
        """
        Get the absolute path for an imported module.

        Args:
            var_name: Variable name used in import
            current_file: Current file path

        Returns:
            Absolute path to the imported module or None
        """
        if var_name not in self.imports:
            return None

        module_path = self.imports[var_name]
        return self.resolved_paths.get(module_path)

    def _resolve_module_path(
        self, module_path: str, current_file: str
    ) -> Optional[str]:
        """
        Resolve a module path to an absolute file path.

        Args:
            module_path: Module path from require/import (e.g., './validation', '../../foo')
            current_file: Current file path

        Returns:
            Absolute file path or None
        """
        # Skip node_modules
        if not module_path.startswith("."):
            return None

        # Get current directory
        current_dir = os.path.dirname(current_file)

        # Resolve relative path
        resolved = os.path.normpath(os.path.join(current_dir, module_path))

        # Try common extensions
        for ext in [".js", ".ts", ".mjs", ""]:
            candidate = resolved + ext
            if os.path.isfile(candidate):
                return candidate

        # Try index files
        for ext in [".js", ".ts"]:
            index_file = os.path.join(resolved, f"index{ext}")
            if os.path.isfile(index_file):
                return index_file

        return None

    def extract_member_access(
        self, node: Node, source_code: bytes
    ) -> Optional[tuple[str, str]]:
        """
        Extract member access like 'validation.createUser'.

        Args:
            node: AST node
            source_code: Source code bytes

        Returns:
            Tuple of (object_name, property_name) or None
        """
        if node.type == "member_expression":
            object_node = node.child_by_field_name("object")
            property_node = node.child_by_field_name("property")

            if object_node and property_node:
                object_name = self.parser.get_node_text(object_node, source_code)
                property_name = self.parser.get_node_text(property_node, source_code)
                return (object_name, property_name)

        return None

    def mark_module_parsed(self, file_path: str) -> None:
        """Mark a module as parsed to avoid circular imports."""
        self.parsed_modules.add(file_path)

    def is_module_parsed(self, file_path: str) -> bool:
        """Check if a module has been parsed."""
        return file_path in self.parsed_modules
