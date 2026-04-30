"""ASP.NET Core REST API extractor."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from tree_sitter import Node

from api_extractor.core.models import (
    Endpoint,
    FrameworkType,
    HTTPMethod,
    Parameter,
    ParameterLocation,
    Response,
    Route,
    Schema,
)
from api_extractor.core.parser import LanguageParser
from api_extractor.core.base_extractor import BaseExtractor


class ASPNETCoreExtractor(BaseExtractor):
    """Extract API routes from ASP.NET Core applications."""

    HTTP_METHOD_ATTRIBUTES = {
        "HttpGet": HTTPMethod.GET,
        "HttpPost": HTTPMethod.POST,
        "HttpPut": HTTPMethod.PUT,
        "HttpDelete": HTTPMethod.DELETE,
        "HttpPatch": HTTPMethod.PATCH,
    }

    # C# type to OpenAPI type mapping
    CSHARP_TYPE_MAP = {
        "string": "string",
        "String": "string",
        "int": "integer",
        "Int32": "integer",
        "long": "integer",
        "Int64": "integer",
        "short": "integer",
        "Int16": "integer",
        "byte": "integer",
        "Byte": "integer",
        "bool": "boolean",
        "Boolean": "boolean",
        "double": "number",
        "Double": "number",
        "float": "number",
        "Float": "number",
        "Single": "number",
        "decimal": "number",
        "Decimal": "number",
        "DateTime": "string",
        "DateTimeOffset": "string",
        "Guid": "string",
        "object": "object",
        "Object": "object",
    }

    # Generic type patterns
    ARRAY_TYPES = ["List", "IEnumerable", "ICollection", "IList", "Array", "HashSet", "ISet"]
    DICT_TYPES = ["Dictionary", "IDictionary", "Hashtable"]

    # Minimal API method mappings
    MINIMAL_API_METHODS = {
        "MapGet": HTTPMethod.GET,
        "MapPost": HTTPMethod.POST,
        "MapPut": HTTPMethod.PUT,
        "MapDelete": HTTPMethod.DELETE,
        "MapPatch": HTTPMethod.PATCH,
    }

    def __init__(self) -> None:
        """Initialize ASP.NET Core extractor."""
        super().__init__(FrameworkType.ASPNET_CORE)
        self.parser = LanguageParser()
        # Track MapGroup prefix mappings: {variable_name: prefix_path}
        self.map_group_prefixes: Dict[str, str] = {}

    def get_file_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".cs"]

    def extract_routes_from_file(self, file_path: str) -> List[Route]:
        """
        Extract routes from ASP.NET Core file (Controllers or Minimal APIs).

        Args:
            file_path: Path to C# source file

        Returns:
            List of Route objects
        """
        tree = self.parser.parse_file(file_path)
        if not tree:
            return []

        routes = []

        try:
            with open(file_path, "rb") as f:
                source_code = f.read()
        except Exception:
            return []

        # Find all DTO classes for schema extraction
        dto_schemas = self._find_dto_classes(tree, source_code)

        # First, extract Controller-based routes
        # Query for class declarations
        class_query = """
        (class_declaration
          name: (identifier) @class_name) @class_decl
        """

        matches = self.parser.query(tree, class_query, "csharp")

        for match in matches:
            class_name_node = match.get("class_name")
            class_decl_node = match.get("class_decl")

            if not class_name_node or not class_decl_node:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Check if this is a controller class
            controller_info = self._find_controller_attribute(class_decl_node, source_code)
            if not controller_info:
                continue

            base_path = controller_info.get("base_path", "")
            # Replace [controller] token
            base_path = self._replace_route_tokens(base_path, class_name)

            # Find all methods in the controller
            method_routes = self._extract_methods_from_class(
                class_decl_node, source_code, base_path, file_path, dto_schemas
            )
            routes.extend(method_routes)

        # Second, extract Minimal API routes
        minimal_api_routes = self._extract_minimal_api_routes(tree, source_code, file_path)
        routes.extend(minimal_api_routes)

        return routes

    def _find_controller_attribute(
        self, class_decl_node: Node, source_code: bytes
    ) -> Optional[Dict]:
        """
        Find [ApiController] or [Controller] attribute and extract base route.
        Also checks if class inherits from Controller or ControllerBase.

        Args:
            class_decl_node: Class declaration node
            source_code: Source code bytes

        Returns:
            Dictionary with controller info or None
        """
        # Look for attribute_list nodes before the class
        has_controller_attribute = False
        base_path = ""

        # Walk children to find attribute_list nodes
        for child in class_decl_node.children:
            if child.type == "attribute_list":
                # Check attributes in this list
                for attr_child in child.children:
                    if attr_child.type == "attribute":
                        attr_name_node = None
                        # Find the identifier in attribute
                        for attr_part in attr_child.children:
                            if attr_part.type == "identifier":
                                attr_name_node = attr_part
                                break

                        if not attr_name_node:
                            continue

                        attr_name = self.parser.get_node_text(attr_name_node, source_code)

                        # Check for controller attributes
                        if attr_name in ["ApiController", "Controller"]:
                            has_controller_attribute = True

                        # Check for Route attribute
                        if attr_name == "Route":
                            # Extract route path from attribute argument
                            route_path = self._extract_attribute_string_argument(
                                attr_child, source_code
                            )
                            if route_path:
                                base_path = route_path

            # Check for base_list (inheritance)
            elif child.type == "base_list":
                for base_child in child.children:
                    if base_child.type == "identifier":
                        base_name = self.parser.get_node_text(base_child, source_code)
                        # Check if inherits from Controller or ControllerBase
                        if base_name in ["Controller", "ControllerBase"]:
                            has_controller_attribute = True

        if not has_controller_attribute:
            return None

        return {"base_path": base_path}

    def _extract_attribute_string_argument(
        self, attribute_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Extract string argument from attribute like [Route("api/products")].

        Args:
            attribute_node: Attribute node
            source_code: Source code bytes

        Returns:
            String value or None
        """
        # Look for attribute_argument_list → attribute_argument → string_literal
        for child in attribute_node.children:
            if child.type == "attribute_argument_list":
                for arg in child.children:
                    if arg.type == "attribute_argument":
                        # Find string_literal
                        string_literal = None
                        for arg_child in arg.children:
                            if arg_child.type == "string_literal":
                                string_literal = arg_child
                                break

                        if string_literal:
                            # Extract string_literal_content
                            for str_child in string_literal.children:
                                if str_child.type == "string_literal_content":
                                    return self.parser.get_node_text(str_child, source_code)

        return None

    def _replace_route_tokens(self, path: str, controller_name: str) -> str:
        """
        Replace [controller] and [action] tokens in route path.

        Args:
            path: Route path with tokens
            controller_name: Controller class name

        Returns:
            Path with tokens replaced
        """
        # Remove "Controller" suffix if present
        if controller_name.endswith("Controller"):
            controller_name = controller_name[: -len("Controller")]

        # Lowercase first letter (C# convention)
        if controller_name:
            controller_name = controller_name[0].lower() + controller_name[1:]

        # Replace [controller] token
        path = path.replace("[controller]", controller_name)

        return path

    def _extract_methods_from_class(
        self,
        class_decl_node: Node,
        source_code: bytes,
        base_path: str,
        file_path: str,
        dto_schemas: Dict[str, Schema],
    ) -> List[Route]:
        """
        Extract routes from all methods in a controller class.

        Args:
            class_decl_node: Class declaration node
            source_code: Source code bytes
            base_path: Base route path from controller
            file_path: Source file path
            dto_schemas: Available DTO schemas

        Returns:
            List of routes
        """
        routes = []

        # Find declaration_list (class body)
        declaration_list = None
        for child in class_decl_node.children:
            if child.type == "declaration_list":
                declaration_list = child
                break

        if not declaration_list:
            return routes

        # Find all method_declaration nodes
        for child in declaration_list.children:
            if child.type == "method_declaration":
                route = self._extract_route_from_method(
                    child, source_code, base_path, file_path, dto_schemas
                )
                if route:
                    routes.append(route)

        return routes

    def _extract_route_from_method(
        self,
        method_node: Node,
        source_code: bytes,
        base_path: str,
        file_path: str,
        dto_schemas: Dict[str, Schema],
    ) -> Optional[Route]:
        """
        Extract route from a single method.

        Args:
            method_node: Method declaration node
            source_code: Source code bytes
            base_path: Base route path
            file_path: Source file path
            dto_schemas: Available DTO schemas

        Returns:
            Route object or None
        """
        # Extract HTTP method and path from attributes
        http_method_info = self._extract_http_method_attribute(method_node, source_code)
        if not http_method_info:
            return None

        http_method = http_method_info["method"]
        method_path = http_method_info.get("path", "")

        # Extract method name
        method_name = None
        for child in method_node.children:
            if child.type == "identifier":
                # This is the method name (not return type)
                if method_name is None:
                    method_name = self.parser.get_node_text(child, source_code)
                    break

        # Replace [action] token with method name
        if method_name and "[action]" in method_path:
            action_name = method_name[0].lower() + method_name[1:] if method_name else ""
            method_path = method_path.replace("[action]", action_name)

        # Combine paths
        full_path = self._combine_paths(base_path, method_path)

        # Normalize path (remove constraints like {id:int})
        normalized_path = self._normalize_path(full_path)

        # Link method schemas (request body and response)
        schema_metadata = self._link_method_schemas(method_node, source_code, dto_schemas)

        # Create route
        route = Route(
            path=normalized_path,
            methods=[http_method],
            handler_name=method_name,
            framework=FrameworkType.ASPNET_CORE,
            raw_path=full_path,
            source_file=file_path,
            source_line=method_node.start_point[0] + 1,
            metadata={
                "dto_schemas": dto_schemas,
                **schema_metadata,  # Merge schema metadata
            },
        )

        return route

    def _extract_http_method_attribute(
        self, method_node: Node, source_code: bytes
    ) -> Optional[Dict]:
        """
        Extract HTTP method from [HttpGet], [HttpPost], etc. attributes.

        Args:
            method_node: Method declaration node
            source_code: Source code bytes

        Returns:
            Dictionary with method and optional path
        """
        for child in method_node.children:
            if child.type == "attribute_list":
                for attr_child in child.children:
                    if attr_child.type == "attribute":
                        # Find attribute identifier
                        attr_name_node = None
                        for attr_part in attr_child.children:
                            if attr_part.type == "identifier":
                                attr_name_node = attr_part
                                break

                        if not attr_name_node:
                            continue

                        attr_name = self.parser.get_node_text(attr_name_node, source_code)

                        # Check if this is an HTTP method attribute
                        if attr_name in self.HTTP_METHOD_ATTRIBUTES:
                            http_method = self.HTTP_METHOD_ATTRIBUTES[attr_name]
                            # Try to extract path argument
                            path = self._extract_attribute_string_argument(attr_child, source_code)
                            return {"method": http_method, "path": path or ""}

        return None

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by removing type constraints and optional markers.

        Examples:
        - {id:int} → {id}
        - {slug:regex(...)} → {slug}
        - {brandId?} → {brandId}
        - {id:int?} → {id}

        Args:
            path: Path with potential constraints and optional markers

        Returns:
            Normalized path
        """
        # Remove type constraints: {param:type} → {param}
        # This also handles {param:type?} → {param?}
        pattern = r"\{([^:}]+):[^}]+\}"
        normalized = re.sub(pattern, r"{\1}", path)

        # Remove optional markers: {param?} → {param}
        normalized = re.sub(r"\{([^}]+)\?\}", r"{\1}", normalized)

        return normalized

    def _combine_paths(self, base_path: str, method_path: str) -> str:
        """
        Combine controller base path with method path.

        Args:
            base_path: Controller base path
            method_path: Method path

        Returns:
            Combined path
        """
        # Remove trailing slashes
        base = base_path.rstrip("/")
        method = method_path.lstrip("/")

        if not base:
            return f"/{method}" if method else "/"
        if not method:
            return base if base.startswith("/") else f"/{base}"

        return f"{base if base.startswith('/') else f'/{base}'}/{method}"

    def _extract_path_parameters(self, path: str) -> List[Parameter]:
        """
        Extract path parameters from route path.

        Handles ASP.NET Core optional parameter syntax:
        - {id} → required parameter named 'id'
        - {id?} → optional parameter named 'id'
        - {id:int} → required parameter named 'id' with constraint
        - {id:int?} → optional parameter named 'id' with constraint

        Args:
            path: Route path with {param} placeholders

        Returns:
            List of path parameters
        """
        # Match {param} or {param:constraint} or {param?} or {param:constraint?}
        # Capture: param name and optional marker (?)
        # Pattern explanation:
        # \{ - opening brace
        # ([^:}?]+) - capture param name (everything before :, }, or ?)
        # (?::[^}?]+)? - optionally match constraint (:anything_except_}_or_?)
        # (\?)? - optionally capture the ? marker
        # \} - closing brace
        pattern = r"\{([^:}?]+)(?::[^}?]+)?(\?)?\}"
        matches = re.findall(pattern, path)

        parameters = []
        for param_name, optional_marker in matches:
            # NOTE: In OpenAPI, path parameters MUST always be required=True.
            # The ? in ASP.NET Core routes indicates optional routing segments,
            # but OpenAPI doesn't support optional path parameters.
            # We strip the ? from the name and path, but keep required=True.
            parameters.append(
                Parameter(
                    name=param_name,
                    location=ParameterLocation.PATH,
                    type="string",
                    required=True,  # OpenAPI spec requires path params to be required
                )
            )

        return parameters

    def _extract_method_parameters(
        self, params_node: Node, source_code: bytes, dto_schemas: Dict[str, Schema]
    ) -> List[Parameter]:
        """
        Extract parameters from method signature with binding attributes.

        Args:
            params_node: Parameter list node
            source_code: Source code bytes
            dto_schemas: Available DTO schemas

        Returns:
            List of parameters
        """
        parameters = []

        for child in params_node.children:
            if child.type == "parameter":
                param = self._extract_single_parameter(child, source_code, dto_schemas)
                if param:
                    parameters.append(param)

        return parameters

    def _extract_single_parameter(
        self, param_node: Node, source_code: bytes, dto_schemas: Dict[str, Schema]
    ) -> Optional[Parameter]:
        """
        Extract a single parameter with its type and location.

        Args:
            param_node: Parameter node
            source_code: Source code bytes
            dto_schemas: Available DTO schemas

        Returns:
            Parameter or None
        """
        # Extract parameter name
        param_name = None
        param_type = None
        binding_location = None

        # Check for binding attributes (FromRoute, FromQuery, FromBody, FromHeader)
        for child in param_node.children:
            if child.type == "attribute_list":
                for attr_child in child.children:
                    if attr_child.type == "attribute":
                        for attr_part in attr_child.children:
                            if attr_part.type == "identifier":
                                attr_name = self.parser.get_node_text(attr_part, source_code)
                                if attr_name == "FromRoute":
                                    binding_location = ParameterLocation.PATH
                                elif attr_name == "FromQuery":
                                    binding_location = ParameterLocation.QUERY
                                elif attr_name == "FromBody":
                                    binding_location = ParameterLocation.BODY
                                elif attr_name == "FromHeader":
                                    binding_location = ParameterLocation.HEADER

        # Extract type and name
        for child in param_node.children:
            if child.type == "identifier":
                if param_type is None:
                    # First identifier might be type name (for non-predefined types)
                    param_type = self.parser.get_node_text(child, source_code)
                else:
                    # Second identifier is parameter name
                    param_name = self.parser.get_node_text(child, source_code)
            elif child.type in ["predefined_type", "generic_name", "nullable_type"]:
                param_type = self._extract_type_text(child, source_code)

        if not param_name:
            return None

        # Determine location if not explicitly set
        if not binding_location:
            # Default: complex types go to body, simple types to query
            if param_type and param_type in dto_schemas:
                binding_location = ParameterLocation.BODY
            else:
                binding_location = ParameterLocation.QUERY

        # Map C# type to OpenAPI type
        openapi_type = self._parse_csharp_type(param_type) if param_type else "string"

        # Check if required (not nullable)
        required = "?" not in (param_type or "")

        return Parameter(
            name=param_name,
            location=binding_location,
            type=openapi_type,
            required=required,
        )

    def _extract_type_text(self, type_node: Node, source_code: bytes) -> str:
        """
        Extract type text from various type nodes.

        Args:
            type_node: Type node (predefined_type, generic_name, nullable_type, etc.)
            source_code: Source code bytes

        Returns:
            Type string
        """
        return self.parser.get_node_text(type_node, source_code)

    def _parse_csharp_type(self, type_text: str) -> str:
        """
        Map C# type to OpenAPI type.

        Args:
            type_text: C# type string

        Returns:
            OpenAPI type
        """
        if not type_text:
            return "object"

        # Remove nullable marker
        type_text = type_text.replace("?", "").strip()

        # Check for array/list types
        for array_type in self.ARRAY_TYPES:
            if type_text.startswith(array_type):
                return "array"

        # Check for dictionary types
        for dict_type in self.DICT_TYPES:
            if type_text.startswith(dict_type):
                return "object"

        # Handle generic types: Task<User>, ActionResult<Product>, etc.
        if "<" in type_text and ">" in type_text:
            # Extract inner type
            match = re.search(r"<([^<>]+)>", type_text)
            if match:
                inner_type = match.group(1)
                # Check if inner type is an array
                if inner_type.startswith(tuple(self.ARRAY_TYPES)):
                    return "array"
                # Recursively parse inner type
                return self._parse_csharp_type(inner_type)

        # Direct mapping
        if type_text in self.CSHARP_TYPE_MAP:
            return self.CSHARP_TYPE_MAP[type_text]

        # Default to object for unknown types
        return "object"

    def _find_dto_classes(self, tree, source_code: bytes) -> Dict[str, Schema]:
        """
        Find C# class definitions for request/response schemas.

        Args:
            tree: Parsed AST tree
            source_code: Source code bytes

        Returns:
            Dictionary mapping class names to Schema objects
        """
        schemas = {}

        # Query for class declarations
        class_query = """
        (class_declaration
          name: (identifier) @class_name
          body: (declaration_list) @class_body) @class_decl
        """

        matches = self.parser.query(tree, class_query, "csharp")

        for match in matches:
            class_name_node = match.get("class_name")
            class_body_node = match.get("class_body")
            class_decl_node = match.get("class_decl")

            if not class_name_node or not class_body_node:
                continue

            class_name = self.parser.get_node_text(class_name_node, source_code)

            # Check if this is a controller - skip if so
            controller_info = self._find_controller_attribute(class_decl_node, source_code)
            if controller_info:
                continue

            # Extract properties
            properties = {}
            required = []

            for child in class_body_node.children:
                if child.type == "property_declaration":
                    prop_info = self._extract_property(child, source_code)
                    if prop_info:
                        properties[prop_info["name"]] = {
                            "type": prop_info["type"],
                        }
                        # C# properties are required by default unless nullable
                        if prop_info.get("required", True):
                            required.append(prop_info["name"])

            if properties:
                schemas[class_name] = Schema(
                    type="object",
                    properties=properties,
                    required=required,
                )

        return schemas

    def _extract_property(self, prop_node: Node, source_code: bytes) -> Optional[Dict]:
        """
        Extract property information from property_declaration node.

        Args:
            prop_node: Property declaration node
            source_code: Source code bytes

        Returns:
            Dictionary with property info or None
        """
        prop_name = None
        prop_type = None
        nullable = False

        for child in prop_node.children:
            if child.type == "identifier":
                prop_name = self.parser.get_node_text(child, source_code)
            elif child.type in ["predefined_type", "generic_name", "nullable_type", "identifier"]:
                type_text = self._extract_type_text(child, source_code)
                prop_type = self._parse_csharp_type(type_text)
                nullable = "?" in type_text

        if not prop_name:
            return None

        return {
            "name": prop_name,
            "type": prop_type or "object",
            "required": not nullable,
        }

    def _extract_return_type(
        self, method_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Extract return type from C# method declaration.

        Handles types like:
        - User
        - Task<User>
        - ActionResult<Product>
        - Task<ActionResult<Product>>
        - IEnumerable<Product>

        Args:
            method_node: Method declaration node
            source_code: Source code bytes

        Returns:
            Return type string, or None if not found
        """
        # Find return type - it's usually the first type-related node
        for child in method_node.children:
            if child.type in ("predefined_type", "identifier", "generic_name", "nullable_type"):
                return self.parser.get_node_text(child, source_code)

        return None

    def _resolve_generic_type(self, type_text: str) -> tuple[str, Optional[str]]:
        """
        Parse generic type to extract base and inner type.

        Examples:
            - Task<User> → ('Task', 'User')
            - ActionResult<Product> → ('ActionResult', 'Product')
            - IEnumerable<User> → ('IEnumerable', 'User')
            - User → ('User', None)

        Args:
            type_text: Generic type string

        Returns:
            Tuple of (base_type, inner_type)
        """
        from api_extractor.extractors.schema_utils import resolve_generic_type_recursive

        base_type, type_args = resolve_generic_type_recursive(type_text)

        if type_args:
            # Return first type argument as inner type
            return (base_type, type_args[0])

        return (base_type, None)

    def _link_method_schemas(
        self,
        method_node: Node,
        source_code: bytes,
        dto_schemas: Dict[str, Schema]
    ) -> Dict[str, any]:
        """
        Link method parameters and return type to schemas.

        Extracts:
        - Request body from [FromBody] parameter
        - Response schema from return type

        Args:
            method_node: Method declaration node
            source_code: Source code bytes
            dto_schemas: Dictionary of DTO schemas

        Returns:
            Dict with request_body, response_schema, and type names
        """
        from api_extractor.extractors.schema_utils import (
            strip_wrapper_types,
            is_collection_type,
            wrap_array_schema,
            normalize_type_name
        )

        metadata = {}

        # Extract return type
        return_type_raw = self._extract_return_type(method_node, source_code)
        if return_type_raw and return_type_raw not in ("void", "IActionResult"):
            # Strip wrapper types like Task, ActionResult
            return_type = strip_wrapper_types(return_type_raw, language='csharp')

            # Normalize type name
            return_type = normalize_type_name(return_type, language='csharp')

            # Store type name for later resolution
            metadata["response_type_name"] = return_type

            # Check if it's a collection type
            if is_collection_type(return_type, language='csharp'):
                # Extract inner type from List<User> → User
                _, inner_type = self._resolve_generic_type(return_type)
                if inner_type:
                    inner_type = normalize_type_name(inner_type, language='csharp')
                    # Try to find schema for inner type
                    if inner_type in dto_schemas:
                        # Wrap in array schema
                        metadata["response_schema"] = wrap_array_schema(dto_schemas[inner_type])
                    else:
                        metadata["response_type_name"] = inner_type
                        metadata["is_array_response"] = True
            else:
                # Try to find schema directly
                if return_type in dto_schemas:
                    metadata["response_schema"] = dto_schemas[return_type]

        # Extract [FromBody] parameter type
        # Find parameter_list node
        param_list_node = None
        for child in method_node.children:
            if child.type == "parameter_list":
                param_list_node = child
                break

        if param_list_node:
            for param_child in param_list_node.children:
                if param_child.type == "parameter":
                    # Check for [FromBody] attribute
                    has_from_body = False
                    param_type = None
                    found_first_identifier = False

                    for param_part in param_child.children:
                        if param_part.type == "attribute_list":
                            for attr in param_part.children:
                                if attr.type == "attribute":
                                    for attr_part in attr.children:
                                        if attr_part.type == "identifier":
                                            attr_name = self.parser.get_node_text(attr_part, source_code)
                                            if attr_name == "FromBody":
                                                has_from_body = True

                        # For C#, parameter structure is: type identifier_name
                        # We want the first identifier (type), not the second (variable name)
                        if param_part.type in ("predefined_type", "generic_name", "nullable_type"):
                            param_type = self.parser.get_node_text(param_part, source_code)
                        elif param_part.type == "identifier" and not found_first_identifier and param_type is None:
                            # This is the type identifier (first one)
                            param_type = self.parser.get_node_text(param_part, source_code)
                            found_first_identifier = True

                    if has_from_body and param_type:
                        # Normalize type name
                        param_type = normalize_type_name(param_type, language='csharp')

                        # Store type name for later resolution
                        metadata["request_body_type_name"] = param_type

                        # Try to find schema
                        if param_type in dto_schemas:
                            metadata["request_body"] = dto_schemas[param_type]
                        elif is_collection_type(param_type, language='csharp'):
                            # Extract inner type from List<User> → User
                            _, inner_type = self._resolve_generic_type(param_type)
                            if inner_type:
                                inner_type = normalize_type_name(inner_type, language='csharp')
                                if inner_type in dto_schemas:
                                    metadata["request_body"] = wrap_array_schema(dto_schemas[inner_type])
                                else:
                                    metadata["request_body_type_name"] = inner_type
                                    metadata["is_array_request"] = True

                        break  # Only one [FromBody] per method

        return metadata

    def _extract_minimal_api_routes(
        self, tree, source_code: bytes, file_path: str
    ) -> List[Route]:
        """
        Extract routes from Minimal API patterns (MapGet, MapPost, MapGroup, etc.).

        Args:
            tree: Parsed AST tree
            source_code: Source code bytes
            file_path: Source file path

        Returns:
            List of Route objects
        """
        routes = []

        # Reset MapGroup tracking for this file
        self.map_group_prefixes = {}

        # First pass: Extract MapGroup() calls to build prefix mappings
        # Pattern: var api = app.MapGroup("api/catalog");
        #      or: var api = vApi.MapGroup("api/catalog").HasApiVersion(1, 0);
        # We need to look for any assignment where MapGroup is somewhere in the expression
        map_group_query = """
        (local_declaration_statement
          (variable_declaration
            (variable_declarator
              (identifier) @var_name
              (_) @expression)))
        """

        group_matches = self.parser.query(tree, map_group_query, "csharp")

        for match in group_matches:
            var_name = match.get("var_name")
            expression = match.get("expression")

            if not var_name or not expression:
                continue

            var_name_text = self.parser.get_node_text(var_name, source_code)

            # Search the expression for MapGroup() calls
            path = self._find_map_group_in_expression(expression, source_code)
            if path:
                self.map_group_prefixes[var_name_text] = path

        # Second pass: Extract MapGet(), MapPost(), etc. calls
        # Pattern: api.MapGet("/items", handler);
        map_method_query = """
        (invocation_expression
          function: (member_access_expression
            expression: (identifier) @var_name
            name: (identifier) @method_name)
          arguments: (argument_list
            (argument
              (string_literal) @path_literal))) @invocation
        """

        method_matches = self.parser.query(tree, map_method_query, "csharp")

        for match in method_matches:
            method_name = match.get("method_name")
            if not method_name:
                continue

            method_name_text = self.parser.get_node_text(method_name, source_code)

            # Check if this is a Minimal API method
            if method_name_text not in self.MINIMAL_API_METHODS:
                continue

            http_method = self.MINIMAL_API_METHODS[method_name_text]

            var_name = match.get("var_name")
            path_literal = match.get("path_literal")
            invocation = match.get("invocation")

            if not path_literal:
                continue

            # Extract path
            path = self._extract_string_literal_content(path_literal, source_code)
            if not path:
                continue

            # Check if variable has a prefix from MapGroup
            if var_name:
                var_name_text = self.parser.get_node_text(var_name, source_code)
                prefix = self.map_group_prefixes.get(var_name_text, "")
                if prefix:
                    path = self._combine_paths(prefix, path)

            # Normalize path (remove constraints like {id:int})
            normalized_path = self._normalize_path(path)

            # Get source line
            source_line = invocation.start_point[0] + 1 if invocation else 1

            # Create route
            route = Route(
                path=normalized_path,
                methods=[http_method],
                handler_name=f"{method_name_text}_handler",
                framework=FrameworkType.ASPNET_CORE,
                raw_path=path,
                source_file=file_path,
                source_line=source_line,
                metadata={"minimal_api": True},
            )

            routes.append(route)

        return routes

    def _find_map_group_in_expression(
        self, expression_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Recursively search for MapGroup() call in an expression and extract its path argument.

        Args:
            expression_node: Expression node to search
            source_code: Source code bytes

        Returns:
            Path string or None
        """
        # Check if this node is an invocation_expression
        if expression_node.type == "invocation_expression":
            # Check if the function is a member_access_expression with name "MapGroup"
            for child in expression_node.children:
                if child.type == "member_access_expression":
                    # Check the name
                    for member_child in child.children:
                        if member_child.type == "identifier":
                            method_name = self.parser.get_node_text(member_child, source_code)
                            if method_name == "MapGroup":
                                # Found it! Extract the path argument
                                for inv_child in expression_node.children:
                                    if inv_child.type == "argument_list":
                                        for arg_child in inv_child.children:
                                            if arg_child.type == "argument":
                                                for arg_part in arg_child.children:
                                                    if arg_part.type == "string_literal":
                                                        return self._extract_string_literal_content(
                                                            arg_part, source_code
                                                        )

        # Recursively search children
        for child in expression_node.children:
            result = self._find_map_group_in_expression(child, source_code)
            if result:
                return result

        return None

    def _extract_string_literal_content(
        self, string_literal_node: Node, source_code: bytes
    ) -> Optional[str]:
        """
        Extract content from string_literal node.

        Args:
            string_literal_node: String literal node
            source_code: Source code bytes

        Returns:
            String content or None
        """
        # Look for string_literal_content child
        for child in string_literal_node.children:
            if child.type == "string_literal_content":
                return self.parser.get_node_text(child, source_code)

        # If no child, try to extract directly and remove quotes
        text = self.parser.get_node_text(string_literal_node, source_code)
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]

        return text

    def _route_to_endpoints(self, route: Route) -> List[Endpoint]:
        """
        Convert a Route to one or more Endpoint objects with schema support.

        Args:
            route: Route object with schema metadata

        Returns:
            List of Endpoint objects (one per HTTP method)
        """
        endpoints = []

        for method in route.methods:
            # Parse path parameters from raw_path to preserve optional markers (?)
            # Use raw_path if available, otherwise fall back to normalized path
            path_for_params = route.raw_path or route.path
            path_parameters = self._extract_path_parameters(path_for_params)

            # Create default response
            responses = [
                Response(
                    status_code="200",
                    description="Success",
                    content_type="application/json",
                )
            ]

            # Add response schema if available
            if route.metadata and "response_schema" in route.metadata:
                responses[0].response_schema = route.metadata["response_schema"]

            # Extract request body schema from metadata
            request_body = None
            if route.metadata and "request_body" in route.metadata:
                request_body = route.metadata["request_body"]

            # Generate unique operation ID
            # OpenAPI requires operation IDs to be unique across all operations
            clean_path = route.path.replace("{", "").replace("}", "").replace("/", "_")
            clean_path = clean_path.lstrip("_")
            if not route.path.endswith("/") or route.path == "/":
                clean_path = clean_path.rstrip("_")

            method_lower = method.value.lower()

            if route.handler_name == "<anonymous>":
                # Anonymous handler: method_path
                operation_id = f"{method_lower}_{clean_path}" if clean_path else method_lower
            else:
                # Named handler: handler_method_path
                operation_id = f"{route.handler_name}_{method_lower}_{clean_path}" if clean_path else f"{route.handler_name}_{method_lower}"

            endpoint = Endpoint(
                path=route.path,
                method=method,
                parameters=path_parameters,
                request_body=request_body,
                responses=responses,
                tags=[self.framework.value],
                operation_id=operation_id,
                source_file=route.source_file,
                source_line=route.source_line,
            )

            endpoints.append(endpoint)

        return endpoints

    def convert_route_to_endpoint(self, route: Route) -> Endpoint:
        """
        Convert Route to OpenAPI Endpoint.

        Args:
            route: Route object

        Returns:
            Endpoint object
        """
        # Extract path parameters from route
        path_params = self._extract_path_parameters(route.path)

        # Create default response
        responses = [
            Response(
                status_code="200",
                description="Success",
                response_schema=None,
                content_type="application/json",
            )
        ]

        return Endpoint(
            path=route.path,
            method=route.methods[0] if route.methods else HTTPMethod.GET,
            summary=f"{route.handler_name or 'Handler'} endpoint",
            parameters=path_params,
            responses=responses,
            source_file=route.source_file,
            source_line=route.source_line,
        )
