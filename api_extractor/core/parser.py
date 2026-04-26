"""Tree-sitter parser wrapper for AST analysis."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser, Node, Tree


def find_child_by_type(node: Node, child_type: str) -> Optional[Node]:
    """
    Find first direct child of a specific type.

    Args:
        node: Parent node
        child_type: Type of child to find

    Returns:
        First matching child or None
    """
    for child in node.children:
        if child.type == child_type:
            return child
    return None


class LanguageParser:
    """Wrapper for Tree-sitter parser with language detection."""

    # Language instances cache
    _languages: Dict[str, Language] = {}

    # Extension to language mapping
    EXTENSION_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
    }

    def __init__(self) -> None:
        """Initialize parser."""
        self._init_languages()
        self.parser = None  # Will be set per-language

    def _init_languages(self) -> None:
        """Initialize language parsers."""
        if "python" not in self._languages:
            self._languages["python"] = Language(tspython.language())

        if "javascript" not in self._languages:
            self._languages["javascript"] = Language(tsjavascript.language())

        if "typescript" not in self._languages:
            self._languages["typescript"] = Language(tstypescript.language_typescript())

        if "tsx" not in self._languages:
            self._languages["tsx"] = Language(tstypescript.language_tsx())

    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect language from file extension.

        Args:
            file_path: Path to source file

        Returns:
            Language name or None if not supported
        """
        ext = Path(file_path).suffix.lower()
        return self.EXTENSION_MAP.get(ext)

    def parse_file(self, file_path: str) -> Optional[Tree]:
        """
        Parse a source file and return AST.

        Args:
            file_path: Path to source file

        Returns:
            Tree-sitter Tree object or None if parsing failed
        """
        language = self.detect_language(file_path)
        if not language:
            return None

        try:
            with open(file_path, "rb") as f:
                source_code = f.read()
            return self.parse_source(source_code, language)
        except Exception:
            return None

    def parse_source(self, source_code: bytes, language: str) -> Optional[Tree]:
        """
        Parse source code with specified language.

        Args:
            source_code: Source code as bytes
            language: Language name (python, javascript, typescript, tsx)

        Returns:
            Tree-sitter Tree object or None if parsing failed
        """
        lang = self._languages.get(language)
        if not lang:
            return None

        try:
            parser = Parser(lang)
            return parser.parse(source_code)
        except Exception:
            return None

    def query(self, tree: Tree, query_str: str, language: str) -> List[Dict[str, Node]]:
        """
        Execute a Tree-sitter query on an AST.

        Args:
            tree: Tree-sitter Tree object
            query_str: S-expression query string
            language: Language name for the query

        Returns:
            List of dictionaries mapping capture names to single nodes
            (takes first node from each capture list)
        """
        from tree_sitter import Query, QueryCursor

        lang = self._languages.get(language)
        if not lang:
            return []

        try:
            query = Query(lang, query_str)
            cursor = QueryCursor(query)
            matches = cursor.matches(tree.root_node)

            # Convert matches to list of dicts with capture names
            # Each capture maps to a list of nodes, but we take the first
            results = []
            for pattern_idx, captures_dict in matches:
                result_dict = {}
                for capture_name, nodes in captures_dict.items():
                    # Take first node from list (queries typically capture one node per name)
                    if nodes:
                        result_dict[capture_name] = nodes[0]
                results.append(result_dict)

            return results
        except Exception as e:
            # Silently fail for malformed queries
            return []

    def find_nodes_by_type(self, node: Node, node_type: str) -> List[Node]:
        """
        Find all nodes of a specific type in the AST.

        Args:
            node: Root node to start search
            node_type: Type of nodes to find

        Returns:
            List of matching nodes
        """
        results = []

        def traverse(n: Node) -> None:
            if n.type == node_type:
                results.append(n)
            for child in n.children:
                traverse(child)

        traverse(node)
        return results

    def get_node_text(self, node: Node, source_code: bytes) -> str:
        """
        Extract text content from a node.

        Args:
            node: Tree-sitter Node
            source_code: Original source code as bytes

        Returns:
            Text content of the node
        """
        return source_code[node.start_byte : node.end_byte].decode("utf-8")

    def find_child_by_field(self, node: Node, field_name: str) -> Optional[Node]:
        """
        Find child by field name.

        Args:
            node: Parent node
            field_name: Field name to find

        Returns:
            Child node or None
        """
        return node.child_by_field_name(field_name)

    def extract_string_value(self, node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract string value from a string node.

        Args:
            node: String node
            source_code: Original source code

        Returns:
            String value without quotes or None
        """
        if node.type not in ("string", "string_literal"):
            return None

        text = self.get_node_text(node, source_code)
        # Remove quotes
        if text.startswith(('"""', "'''")) and text.endswith(('"""', "'''")):
            return text[3:-3]
        elif text.startswith(('"', "'")) and text.endswith(('"', "'")):
            return text[1:-1]
        return text

    def extract_identifier(self, node: Node, source_code: bytes) -> Optional[str]:
        """
        Extract identifier name from a node.

        Args:
            node: Identifier node
            source_code: Original source code

        Returns:
            Identifier name or None
        """
        if node.type not in ("identifier", "property_identifier"):
            return None

        return self.get_node_text(node, source_code)

    def traverse(
        self, node: Node, callback: callable, source_code: Optional[bytes] = None
    ) -> None:
        """
        Traverse AST and call callback for each node.

        Args:
            node: Root node to start traversal
            callback: Function to call for each node (receives node, source_code)
            source_code: Optional source code for text extraction
        """

        def _traverse(n: Node) -> None:
            callback(n, source_code)
            for child in n.children:
                _traverse(child)

        _traverse(node)

    def get_node_location(self, node: Node) -> Dict[str, int]:
        """
        Get location information for a node.

        Args:
            node: Tree-sitter Node

        Returns:
            Dictionary with start_line, end_line, start_col, end_col
        """
        return {
            "start_line": node.start_point[0] + 1,  # Convert to 1-indexed
            "end_line": node.end_point[0] + 1,
            "start_col": node.start_point[1],
            "end_col": node.end_point[1],
        }
