"""Shared utilities for schema extraction across extractors."""

from __future__ import annotations

import re
from typing import Tuple, List, Optional

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