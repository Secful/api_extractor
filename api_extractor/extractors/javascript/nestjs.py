"""NestJS framework extractor."""

import re
from typing import List, Optional, Dict, Tuple
from tree_sitter import Node

from api_extractor.core.base_extractor import BaseExtractor
from api_extractor.core.parser import find_child_by_type
from api_extractor.core.models import (
    Route,
    Parameter,
    HTTPMethod,
    FrameworkType,
)


class NestJSExtractor(BaseExtractor):
    """Extract API routes from NestJS applications."""

    # HTTP method decorators
    HTTP_METHOD_DECORATORS = ["Get", "Post", "Put", "Delete", "Patch", "Head", "Options"]

    def __init__(self) -> None:
        """Initialize NestJS extractor."""
        super().__init__(FrameworkType.NESTJS)

    def get_file_extensions(self) -> List[str]:
        """Get TypeScript file extensions."""
        return [".ts"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from a NestJS file.

        Args:
            file_path: Path to TypeScript file

        Returns:
            List of Route objects
        """
        routes = []

        # Read file content
        source_code = self._read_file(file_path)
        if not source_code:
            return routes

        # Parse with Tree-sitter
        tree = self.parser.parse_source(source_code, "typescript")
        if not tree:
            return routes

        # Query for all class declarations (works for both exported and non-exported)
        class_query = """
        (class_declaration
          name: (type_identifier) @class_name
          body: (class_body) @class_body)
        """

        all_classes = self.parser.query(tree, class_query, "typescript")

        for match in all_classes:
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")

            if not class_name_node or not class_body_node:
                continue

            # Check if this class has @Controller decorator
            # We need to check the parent nodes for decorators
            controller_info = self._find_controller_decorator(class_name_node, source_code)
            if not controller_info:
                continue

            # Extract routes from this controller
            class_routes = self._extract_routes_from_controller_query(
                class_body_node, source_code, file_path, controller_info, tree
            )
            routes.extend(class_routes)

        return routes

    def _find_controller_decorator(
        self, class_name_node: Node, source_code: bytes
    ) -> Optional[Dict[str, any]]:
        """
        Find @Controller decorator for a class by checking parent nodes.

        Args:
            class_name_node: Class name identifier node
            source_code: Source code bytes

        Returns:
            Controller info dict or None
        """
        # Walk up to find decorators
        current = class_name_node.parent  # class_declaration
        if not current:
            return None

        # Check parent's siblings for decorators
        parent = current.parent
        if not parent:
            return None

        # Look for decorator among siblings or parent's children
        for sibling in parent.children:
            if sibling.type == "decorator":
                decorator_text = self.parser.get_node_text(sibling, source_code)
                if "Controller" in decorator_text:
                    return self._extract_controller_info(sibling, source_code)

        return None

    def _extract_routes_from_controller_query(
        self,
        class_body_node: Node,
        source_code: bytes,
        file_path: str,
        controller_info: Dict[str, any],
        tree,
    ) -> List[Route]:
        """
        Extract routes from controller using queries.

        Args:
            class_body_node: Class body node
            source_code: Source code bytes
            file_path: Path to source file
            controller_info: Controller path and version info
            tree: Full syntax tree

        Returns:
            List of Route objects
        """
        routes = []

        # Get controller path and version
        controller_path = controller_info["path"]
        version = controller_info["version"]

        # Add version prefix if present
        if version:
            controller_path = f"/v{version}{controller_path}"

        # Iterate through class_body children and pair decorators with methods
        # In TypeScript AST, decorators immediately precede their method
        # There can be multiple decorators before a method
        children = class_body_node.children
        i = 0
        while i < len(children):
            child = children[i]

            # Look for decorator(s) followed by method_definition
            if child.type == "decorator":
                # Collect all consecutive decorators
                decorators = [child]
                j = i + 1
                while j < len(children) and children[j].type == "decorator":
                    decorators.append(children[j])
                    j += 1

                # Check if decorators are followed by a method_definition
                if j < len(children) and children[j].type == "method_definition":
                    method_node = children[j]

                    # Look through all decorators for HTTP method decorator
                    for decorator_node in decorators:
                        decorator_text = self.parser.get_node_text(decorator_node, source_code)

                        for http_decorator in self.HTTP_METHOD_DECORATORS:
                            # Match decorator that starts with @<HttpMethod>(
                            if decorator_text.strip().startswith(f"@{http_decorator}("):
                                # Extract path from decorator
                                method_path = self._extract_method_path(decorator_node, source_code)

                                # Combine controller and method paths
                                full_path = self._combine_paths(controller_path, method_path)

                                # Get method name from first child (property_identifier)
                                if method_node.children:
                                    method_name_node = method_node.children[0]
                                    method_name = self.parser.get_node_text(method_name_node, source_code)

                                    # Get location
                                    location = self.parser.get_node_location(method_name_node)

                                    # Create route
                                    try:
                                        http_method = HTTPMethod[http_decorator.upper()]
                                        route = Route(
                                            path=full_path,
                                            methods=[http_method],
                                            handler_name=method_name,
                                            framework=self.framework,
                                            raw_path=full_path,
                                            source_file=file_path,
                                            source_line=location["start_line"],
                                        )
                                        routes.append(route)
                                        break  # Only one HTTP method per method
                                    except KeyError:
                                        pass

                    # Skip past all decorators and the method
                    i = j

            i += 1

        return routes

    def _is_node_within(self, child_node: Node, parent_node: Node) -> bool:
        """
        Check if child_node is within parent_node's range.

        Args:
            child_node: Potential child node
            parent_node: Parent node

        Returns:
            True if child is within parent
        """
        return (
            child_node.start_byte >= parent_node.start_byte
            and child_node.end_byte <= parent_node.end_byte
        )

    def _extract_controller_info(
        self, decorator_node: Node, source_code: bytes
    ) -> Optional[Dict[str, any]]:
        """
        Extract controller information from @Controller decorator.

        Handles both:
        - @Controller('users')
        - @Controller({ path: 'users', version: '1' })

        Args:
            decorator_node: decorator node
            source_code: Source code bytes

        Returns:
            Dict with 'path' and optional 'version', or None
        """
        # Find call expression
        call_expr = find_child_by_type(decorator_node, "call_expression")
        if not call_expr:
            return {"path": "", "version": None}

        # Get arguments
        args = self.parser.find_child_by_field(call_expr, "arguments")
        if not args:
            return {"path": "", "version": None}

        # Check first argument
        for child in args.children:
            # Simple string path: @Controller('users')
            if child.type == "string":
                path = self.parser.extract_string_value(child, source_code)
                return {
                    "path": f"/{path}" if path and not path.startswith("/") else path or "",
                    "version": None,
                }

            # Object syntax: @Controller({ path: 'users', version: '1' })
            elif child.type == "object":
                return self._parse_controller_object(child, source_code)

        return {"path": "", "version": None}

    def _parse_controller_object(self, obj_node: Node, source_code: bytes) -> Dict[str, any]:
        """
        Parse @Controller({ path: 'users', version: '1' }) object.

        Args:
            obj_node: object node
            source_code: Source code bytes

        Returns:
            Dict with path and version
        """
        result = {"path": "", "version": None}

        for child in obj_node.children:
            if child.type == "pair":
                # Get key and value
                key_node = self.parser.find_child_by_field(child, "key")
                value_node = self.parser.find_child_by_field(child, "value")

                if not key_node or not value_node:
                    continue

                key = self.parser.get_node_text(key_node, source_code).strip("'\"")

                if key == "path":
                    if value_node.type == "string":
                        path = self.parser.extract_string_value(value_node, source_code)
                        result["path"] = (
                            f"/{path}" if path and not path.startswith("/") else path or ""
                        )

                elif key == "version":
                    if value_node.type == "string":
                        result["version"] = self.parser.extract_string_value(value_node, source_code)
                    elif value_node.type == "number":
                        result["version"] = self.parser.get_node_text(value_node, source_code)

        return result

    def _combine_paths(self, base: str, method: str) -> str:
        """
        Combine base and method paths properly.

        Args:
            base: Base path from controller
            method: Method path from decorator

        Returns:
            Combined path
        """
        # Normalize paths
        base = base.rstrip("/") if base else ""
        method = method.lstrip("/") if method else ""

        if not method:
            return base or "/"

        if not base:
            return f"/{method}"

        return f"{base}/{method}"

    def _extract_method_path(self, decorator_node: Node, source_code: bytes) -> str:
        """
        Extract path from HTTP method decorator.

        Handles:
        - @Get() → empty string
        - @Get(':id') → ':id'
        - @Get('profile') → 'profile'

        Args:
            decorator_node: decorator node
            source_code: Source code bytes

        Returns:
            Method path (may be empty for root)
        """
        # Find call expression
        call_expr = find_child_by_type(decorator_node, "call_expression")
        if not call_expr:
            return ""

        # Get arguments
        args = self.parser.find_child_by_field(call_expr, "arguments")
        if not args:
            return ""

        # Get first argument (path string)
        for child in args.children:
            if child.type == "string":
                path = self.parser.extract_string_value(child, source_code)
                return path or ""

        return ""

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from NestJS path.

        NestJS uses :paramName syntax.

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
        Normalize NestJS path to OpenAPI format.

        Convert :param to {param}.

        Args:
            path: NestJS path

        Returns:
            Normalized path
        """
        # Replace :param with {param}
        normalized = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
        return normalized
