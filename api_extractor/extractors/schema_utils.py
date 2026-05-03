"""Shared utilities for schema extraction across extractors."""

from __future__ import annotations

import re
from typing import Any, Tuple, List, Optional

from api_extractor.core.models import Schema


def resolve_generic_type_recursive(
    type_text: str,
    max_depth: int = 5
) -> Tuple[str, List[str]]:
    """
    Recursively parse nested generic types.

    Handles generic type syntax from multiple languages:
    - Java/C#: List<User>, Map<String, List<User>>, Task<ActionResult<Product>>
    - TypeScript: Array<User>, Promise<Response<User>>

    Args:
        type_text: Generic type string to parse
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Tuple of (base_type, type_arguments)

    Examples:
        >>> resolve_generic_type_recursive("List<User>")
        ('List', ['User'])

        >>> resolve_generic_type_recursive("Map<String, List<User>>")
        ('Map', ['String', 'List<User>'])

        >>> resolve_generic_type_recursive("Task<ActionResult<Product>>")
        ('Task', ['ActionResult<Product>'])

        >>> resolve_generic_type_recursive("User")
        ('User', [])
    """
    if max_depth <= 0:
        return (type_text, [])

    # Match pattern: BaseType<TypeArg1, TypeArg2, ...>
    match = re.match(r'^([^<>]+)<(.+)>$', type_text.strip())
    if not match:
        # Not a generic type, return as-is
        return (type_text.strip(), [])

    base_type = match.group(1).strip()
    args_text = match.group(2)

    # Parse type arguments, respecting nested brackets
    type_args = _split_generic_arguments(args_text)

    return base_type, type_args


def _split_generic_arguments(args_text: str) -> List[str]:
    """
    Split generic type arguments by comma, respecting nested brackets.

    Args:
        args_text: The content between < and >

    Returns:
        List of type argument strings

    Examples:
        >>> _split_generic_arguments("String, User")
        ['String', 'User']

        >>> _split_generic_arguments("String, List<User>")
        ['String', 'List<User>']

        >>> _split_generic_arguments("Map<String, Integer>, List<User>")
        ['Map<String, Integer>', 'List<User>']
    """
    args = []
    current = []
    depth = 0

    for char in args_text:
        if char == '<':
            depth += 1
            current.append(char)
        elif char == '>':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            # This comma separates type arguments
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(char)

    # Add the last argument
    if current:
        args.append(''.join(current).strip())

    return args


def extract_inner_generic_type(type_text: str) -> Optional[str]:
    """
    Extract the innermost type from nested generics.

    Useful for unwrapping wrapper types like:
    - ResponseEntity<User> → User
    - Task<ActionResult<Product>> → Product
    - Promise<Response<User>> → User
    - List<User> → User
    - Optional<User> → User

    Args:
        type_text: Generic type string

    Returns:
        Innermost type, or None if not a generic type

    Examples:
        >>> extract_inner_generic_type("ResponseEntity<User>")
        'User'

        >>> extract_inner_generic_type("Task<ActionResult<Product>>")
        'Product'

        >>> extract_inner_generic_type("List<User>")
        'User'
    """
    current_type = type_text
    inner_type = None

    # Keep unwrapping until we reach a non-generic type
    for _ in range(10):  # Limit iterations to prevent infinite loops
        base, args = resolve_generic_type_recursive(current_type)

        if not args:
            # No more generic arguments, we've reached the innermost type
            return current_type.strip()

        # Take the first type argument and continue unwrapping
        inner_type = args[0]
        current_type = inner_type

    return inner_type


def wrap_array_schema(item_schema: Schema | dict) -> Schema:
    """
    Wrap a schema in an array schema.

    Used when return type is List<T>, IEnumerable<T>, []T, Array<T>, etc.

    Args:
        item_schema: The schema for array items

    Returns:
        Schema object with type='array' and items set

    Examples:
        >>> user_schema = Schema(type="object", properties={"name": {"type": "string"}})
        >>> array_schema = wrap_array_schema(user_schema)
        >>> array_schema.type
        'array'
        >>> array_schema.items == user_schema
        True
    """
    if isinstance(item_schema, dict):
        # Convert dict to Schema object
        item_schema = Schema(**item_schema)

    return Schema(
        type="array",
        items=item_schema
    )


def normalize_type_name(type_text: str, language: str = 'java') -> str:
    """
    Normalize type names across languages.

    Removes:
    - Whitespace
    - Nullable markers (?, Optional, Nullable)
    - Type modifiers (const, readonly, public, private)
    - Package/namespace prefixes

    Args:
        type_text: Raw type string from AST
        language: Programming language ('java', 'csharp', 'typescript', 'go')

    Returns:
        Normalized type name

    Examples:
        >>> normalize_type_name("  String  ")
        'String'

        >>> normalize_type_name("Optional<User>")
        'User'

        >>> normalize_type_name("List<User>?", language='csharp')
        'List<User>'

        >>> normalize_type_name("com.example.model.User", language='java')
        'User'
    """
    # Remove leading/trailing whitespace
    normalized = type_text.strip()

    # Remove nullable markers
    if language == 'csharp':
        # C# nullable reference types: string? → string
        normalized = normalized.rstrip('?')
    elif language == 'typescript':
        # TypeScript: string | null → string
        normalized = re.sub(r'\s*\|\s*null\s*$', '', normalized)
        normalized = re.sub(r'\s*\|\s*undefined\s*$', '', normalized)

    # Unwrap Optional<T> to T
    if normalized.startswith('Optional<') and normalized.endswith('>'):
        normalized = normalized[9:-1].strip()

    # Unwrap Nullable<T> to T
    if normalized.startswith('Nullable<') and normalized.endswith('>'):
        normalized = normalized[9:-1].strip()

    # Remove package/namespace prefixes for Java/C#
    if language in ('java', 'csharp'):
        # com.example.User → User
        # System.Collections.Generic.List<User> → List<User>
        parts = normalized.split('.')
        if len(parts) > 1:
            # Keep only the last part, but preserve generics
            last_part = parts[-1]
            # Check if there are generics that might contain dots
            if '<' in normalized:
                # Complex case: might have dots in generic arguments
                # For now, just take everything after the last dot before '<'
                before_generic = normalized.split('<')[0]
                after_generic = '<' + '<'.join(normalized.split('<')[1:])
                simple_name = before_generic.split('.')[-1]
                normalized = simple_name + after_generic
            else:
                normalized = last_part

    return normalized


def is_collection_type(type_name: str, language: str = 'java') -> bool:
    """
    Check if a type represents a collection/array.

    Args:
        type_name: Type name to check
        language: Programming language

    Returns:
        True if the type is a collection type

    Examples:
        >>> is_collection_type("List<User>")
        True

        >>> is_collection_type("ArrayList<Product>")
        True

        >>> is_collection_type("User")
        False

        >>> is_collection_type("[]User", language='go')
        True
    """
    # Extract base type for generic types
    base_type, _ = resolve_generic_type_recursive(type_name)

    if language == 'java':
        collection_types = {
            'List', 'ArrayList', 'LinkedList',
            'Set', 'HashSet', 'TreeSet',
            'Collection', 'Iterable',
            'Vector', 'Stack'
        }
        return base_type in collection_types

    elif language == 'csharp':
        collection_types = {
            'List', 'IEnumerable', 'ICollection', 'IList',
            'HashSet', 'LinkedList', 'Queue', 'Stack',
            'Collection', 'ObservableCollection'
        }
        return base_type in collection_types

    elif language == 'typescript':
        return base_type in ('Array', 'ReadonlyArray') or type_name.endswith('[]')

    elif language == 'go':
        # Go slices: []Type
        return type_name.startswith('[]')

    return False


def strip_wrapper_types(type_text: str, language: str = 'java') -> str:
    """
    Strip common wrapper types to get the actual data type.

    Common wrappers:
    - Java: ResponseEntity<T>, Optional<T>
    - C#: ActionResult<T>, Task<T>, IActionResult
    - TypeScript: Promise<T>, Observable<T>

    Args:
        type_text: Type string with potential wrappers
        language: Programming language

    Returns:
        Type string with wrappers removed

    Examples:
        >>> strip_wrapper_types("ResponseEntity<User>", language='java')
        'User'

        >>> strip_wrapper_types("Task<ActionResult<Product>>", language='csharp')
        'Product'

        >>> strip_wrapper_types("Promise<Response<User>>", language='typescript')
        'User'
    """
    wrappers = []

    if language == 'java':
        wrappers = ['ResponseEntity', 'Optional', 'CompletableFuture', 'Mono', 'Flux']
    elif language == 'csharp':
        wrappers = ['ActionResult', 'Task', 'ValueTask', 'IActionResult']
    elif language == 'typescript':
        wrappers = ['Promise', 'Observable']

    current = type_text.strip()

    # Keep unwrapping while we find wrapper types
    for _ in range(10):  # Prevent infinite loops
        base, args = resolve_generic_type_recursive(current)

        if base in wrappers and args:
            # This is a wrapper type, unwrap it
            current = args[0]
        else:
            # Not a wrapper, we're done
            break

    return current


def extract_nested_field_from_struct(
    struct_schema: Schema,
    field_path: str
) -> Schema | None:
    """
    Extract a nested field from a struct/class schema.

    Used for validator patterns where a validator struct has a nested field
    representing the actual request/response type.

    Args:
        struct_schema: Parent schema containing the field
        field_path: Field name or dot-separated path (e.g., "User" or "User.Profile")

    Returns:
        Schema of the nested field, or None if not found

    Examples:
        Validator struct has nested "User" field:
        >>> validator_schema = Schema(
        ...     type="object",
        ...     properties={"User": {"type": "object", "properties": {"name": {"type": "string"}}}}
        ... )
        >>> nested = extract_nested_field_from_struct(validator_schema, "User")
        >>> nested.type
        'object'
    """
    if not struct_schema or not struct_schema.properties:
        return None

    # Split path by dots for nested access
    parts = field_path.split('.')

    current_schema = struct_schema
    for part in parts:
        if not current_schema.properties or part not in current_schema.properties:
            return None

        # Get the nested property
        nested_prop = current_schema.properties[part]

        # Convert dict to Schema if needed
        if isinstance(nested_prop, dict):
            # Check if this looks like a schema (has 'type' key)
            if 'type' in nested_prop:
                current_schema = Schema(**nested_prop)
            else:
                # Might be a simple type reference - return as-is wrapped in a schema
                return Schema(type="object", properties=nested_prop)
        elif isinstance(nested_prop, Schema):
            current_schema = nested_prop
        else:
            return None

    return current_schema


def trace_method_return_type(
    method_name: str,
    source_tree: Any,
    source_code: bytes,
    language: str,
    parser: Any
) -> str | None:
    """
    Find a method/function definition and extract its return type.

    Used for serializer patterns where a serializer object has a method that
    returns the actual response type.

    Args:
        method_name: Method to find (e.g., "Response", "serialize")
        source_tree: Tree-sitter tree
        source_code: Source code bytes
        language: Language ("go", "python", "java", etc.)
        parser: LanguageParser instance for querying

    Returns:
        Return type name or None if not found

    Examples:
        Go: func (s *UserSerializer) Response() UserResponse {...}
        Python: def serialize(self) -> UserResponse: ...
        Java: public UserResponse serialize() {...}
    """
    if not source_tree or not parser:
        return None

    if language == "go":
        # Query for method declaration with specific name
        # Go: func (receiver Type) MethodName() ReturnType {...}
        method_query = """
        (method_declaration
          name: (field_identifier) @method_name
          result: (_) @return_type)
        """

        matches = parser.query(source_tree, method_query, "go")

        for match in matches:
            name_node = match.get("method_name")
            return_node = match.get("return_type")

            if not name_node or not return_node:
                continue

            name_text = parser.get_node_text(name_node, source_code)
            if name_text == method_name:
                return_text = parser.get_node_text(return_node, source_code)
                # Clean up return type (remove pointers, etc.)
                return_text = return_text.strip()
                if return_text.startswith('*'):
                    return_text = return_text[1:]
                return return_text

    elif language == "python":
        # Python: def method_name(self) -> ReturnType: ...
        method_query = """
        (function_definition
          name: (identifier) @method_name
          return_type: (type) @return_type)
        """

        matches = parser.query(source_tree, method_query, "python")

        for match in matches:
            name_node = match.get("method_name")
            return_node = match.get("return_type")

            if not name_node or not return_node:
                continue

            name_text = parser.get_node_text(name_node, source_code)
            if name_text == method_name:
                return_text = parser.get_node_text(return_node, source_code)
                return return_text.strip()

    elif language == "java":
        # Java: public ReturnType methodName() {...}
        method_query = """
        (method_declaration
          name: (identifier) @method_name
          type: (_) @return_type)
        """

        matches = parser.query(source_tree, method_query, "java")

        for match in matches:
            name_node = match.get("method_name")
            return_node = match.get("return_type")

            if not name_node or not return_node:
                continue

            name_text = parser.get_node_text(name_node, source_code)
            if name_text == method_name:
                return_text = parser.get_node_text(return_node, source_code)
                return return_text.strip()

    return None


def find_type_in_variable_chain(
    variable_name: str,
    function_body: Any,
    source_code: bytes,
    language: str,
    parser: Any
) -> str | None:
    """
    Trace a variable through assignments to find its type.

    Used to track variables from constructor calls to method invocations.

    Args:
        variable_name: Variable to trace
        function_body: Function body node or text
        source_code: Source code bytes
        language: Language ("go", "python", "java", etc.)
        parser: LanguageParser instance for text extraction

    Returns:
        Type name or None if not found

    Examples:
        Go: validator := NewUserValidator() → UserValidator
        Python: serializer = UserSerializer() → UserSerializer
        Java: UserService service = new UserService() → UserService
    """
    if not function_body or not parser:
        return None

    # Get body text for regex matching
    body_text = parser.get_node_text(function_body, source_code)

    if language == "go":
        # Pattern 1: variable := NewTypeName()
        # Extract type from constructor: NewUserValidator() → UserValidator
        pattern1 = rf'{variable_name}\s*:=\s*New(\w+)\s*\('
        match1 = re.search(pattern1, body_text)
        if match1:
            return match1.group(1)

        # Pattern 2: variable := TypeName{...}
        pattern2 = rf'{variable_name}\s*:=\s*(\*?)(\w+)\s*\{{'
        match2 = re.search(pattern2, body_text)
        if match2:
            return match2.group(2)

        # Pattern 3: var variable TypeName
        pattern3 = rf'\bvar\s+{variable_name}\s+(\*?)(\w+(?:\.\w+)?)'
        match3 = re.search(pattern3, body_text)
        if match3:
            type_text = match3.group(2)
            # Remove package prefix if present
            if '.' in type_text:
                return type_text.split('.')[-1]
            return type_text

    elif language == "python":
        # Pattern 1: variable = TypeName()
        pattern1 = rf'{variable_name}\s*=\s*(\w+)\s*\('
        match1 = re.search(pattern1, body_text)
        if match1:
            return match1.group(1)

    elif language == "java":
        # Pattern 1: TypeName variable = new TypeName()
        pattern1 = rf'(\w+(?:<[^>]+>)?)\s+{variable_name}\s*=\s*new\s+(\w+)'
        match1 = re.search(pattern1, body_text)
        if match1:
            return match1.group(1)

    return None