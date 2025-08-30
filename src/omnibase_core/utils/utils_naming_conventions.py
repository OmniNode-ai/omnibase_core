"""
Shared naming convention utilities for ONEX code generation.

This module provides standardized string conversion utilities used across
multiple code generation tools to ensure consistency.
"""

import re
from typing import List


def pascal_case(s: str) -> str:
    """
    Convert a string to PascalCase.

    Handles snake_case, kebab-case, and already PascalCase strings.

    Args:
        s: Input string to convert

    Returns:
        String in PascalCase format

    Examples:
        >>> pascal_case("node_generator")
        'NodeGenerator'
        >>> pascal_case("node-generator")
        'NodeGenerator'
        >>> pascal_case("NodeGenerator")
        'NodeGenerator'
        >>> pascal_case("XMLHttpRequest")
        'XMLHttpRequest'
    """
    if not s:
        return ""

    # Handle already PascalCase (preserve existing case for acronyms)
    if s and s[0].isupper() and "_" not in s and "-" not in s:
        return s

    # Convert from snake_case or kebab-case
    return "".join(word.capitalize() for word in re.split(r"[_\-]", s) if word)


def snake_case(s: str) -> str:
    """
    Convert a string to snake_case.

    Handles PascalCase, camelCase, and kebab-case strings.

    Args:
        s: Input string to convert

    Returns:
        String in snake_case format

    Examples:
        >>> snake_case("NodeGenerator")
        'node_generator'
        >>> snake_case("nodeGenerator")
        'node_generator'
        >>> snake_case("node-generator")
        'node_generator'
        >>> snake_case("XMLHttpRequest")
        'xml_http_request'
    """
    if not s:
        return ""

    # Handle kebab-case first
    s = s.replace("-", "_")

    # Insert underscores before uppercase letters (except at start)
    result: List[str] = []
    for i, char in enumerate(s):
        if char.isupper() and i > 0:
            # Only add underscore if previous char isn't already an underscore
            if result and result[-1] != "_":
                result.append("_")
        result.append(char.lower())

    return "".join(result)


def camel_case(s: str) -> str:
    """
    Convert a string to camelCase.

    Handles snake_case, kebab-case, and PascalCase strings.

    Args:
        s: Input string to convert

    Returns:
        String in camelCase format

    Examples:
        >>> camel_case("node_generator")
        'nodeGenerator'
        >>> camel_case("NodeGenerator")
        'nodeGenerator'
        >>> camel_case("node-generator")
        'nodeGenerator'
    """
    if not s:
        return ""

    # Convert to PascalCase first, then lowercase the first character
    pascal = pascal_case(s)
    if not pascal:
        return ""

    return pascal[0].lower() + pascal[1:] if len(pascal) > 1 else pascal.lower()


def kebab_case(s: str) -> str:
    """
    Convert a string to kebab-case.

    Handles snake_case, PascalCase, and camelCase strings.

    Args:
        s: Input string to convert

    Returns:
        String in kebab-case format

    Examples:
        >>> kebab_case("node_generator")
        'node-generator'
        >>> kebab_case("NodeGenerator")
        'node-generator'
        >>> kebab_case("nodeGenerator")
        'node-generator'
    """
    if not s:
        return ""

    # Convert to snake_case first, then replace underscores with hyphens
    return snake_case(s).replace("_", "-")


def screaming_snake_case(s: str) -> str:
    """
    Convert a string to SCREAMING_SNAKE_CASE.

    Used for constants and environment variables.

    Args:
        s: Input string to convert

    Returns:
        String in SCREAMING_SNAKE_CASE format

    Examples:
        >>> screaming_snake_case("node_generator")
        'NODE_GENERATOR'
        >>> screaming_snake_case("NodeGenerator")
        'NODE_GENERATOR'
        >>> screaming_snake_case("max-retry-count")
        'MAX_RETRY_COUNT'
    """
    if not s:
        return ""

    return snake_case(s).upper()


def enum_member_name(s: str) -> str:
    """
    Convert a string to a valid Python enum member name.

    Handles special characters and ensures valid Python identifiers.

    Args:
        s: Input string to convert

    Returns:
        String suitable for use as Python enum member name

    Examples:
        >>> enum_member_name("success")
        'SUCCESS'
        >>> enum_member_name("partial-success")
        'PARTIAL_SUCCESS'
        >>> enum_member_name("404-not-found")
        '_404_NOT_FOUND'
        >>> enum_member_name("error!")
        'ERROR_'
    """
    if not s:
        return ""

    # Replace non-alphanumeric characters with underscores
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", s)

    # Convert to screaming snake case
    result = screaming_snake_case(cleaned)

    # Ensure it starts with a letter or underscore (Python identifier requirement)
    if result and result[0].isdigit():
        result = f"_{result}"

    return result


def class_name_from_snake_case(s: str) -> str:
    """
    Convert snake_case to a proper class name.

    Adds "Model" prefix if not present and converts to PascalCase.

    Args:
        s: Input string in snake_case

    Returns:
        String suitable for use as a class name

    Examples:
        >>> class_name_from_snake_case("node_generator_input_state")
        'ModelNodeGeneratorInputState'
        >>> class_name_from_snake_case("model_user_config")
        'ModelUserConfig'
    """
    if not s:
        return ""

    pascal = pascal_case(s)

    # Add Model prefix if not already present
    if not pascal.startswith("Model"):
        pascal = f"Model{pascal}"

    return pascal


def file_name_from_class_name(class_name: str) -> str:
    """
    Convert a class name to appropriate file name.

    Converts PascalCase to snake_case and adds appropriate prefix.

    Args:
        class_name: Class name in PascalCase

    Returns:
        String suitable for use as a file name

    Examples:
        >>> file_name_from_class_name("ModelNodeGeneratorInputState")
        'model_node_generator_input_state.py'
        >>> file_name_from_class_name("ToolContractToModel")
        'tool_contract_to_model.py'
    """
    if not class_name:
        return ""

    return f"{snake_case(class_name)}.py"


def split_words(s: str) -> List[str]:
    """
    Split a string into constituent words.

    Handles various naming conventions and returns individual words.

    Args:
        s: Input string to split

    Returns:
        List of words in lowercase

    Examples:
        >>> split_words("NodeGenerator")
        ['node', 'generator']
        >>> split_words("node_generator")
        ['node', 'generator']
        >>> split_words("node-generator")
        ['node', 'generator']
        >>> split_words("XMLHttpRequest")
        ['xml', 'http', 'request']
    """
    if not s:
        return []

    # First handle kebab-case and snake_case
    s = s.replace("-", "_")

    # Split on underscores
    parts = s.split("_")

    # Further split PascalCase/camelCase within each part
    words: List[str] = []
    for part in parts:
        if not part:
            continue

        # Split on case changes
        word_parts = re.findall(r"[A-Z]*[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)", part)
        if not word_parts:
            # Handle all-caps or single chars
            word_parts = [part]

        words.extend(word.lower() for word in word_parts if word)

    return words


def validate_python_identifier(name: str) -> bool:
    """
    Check if a string is a valid Python identifier.

    Args:
        name: String to validate

    Returns:
        True if valid Python identifier, False otherwise

    Examples:
        >>> validate_python_identifier("valid_name")
        True
        >>> validate_python_identifier("123invalid")
        False
        >>> validate_python_identifier("class")
        False
    """
    if not name:
        return False

    import builtins

    return name.isidentifier() and not hasattr(builtins, name)


def sanitize_for_python(name: str) -> str:
    """
    Sanitize a string to be a valid Python identifier.

    Args:
        name: String to sanitize

    Returns:
        Valid Python identifier

    Examples:
        >>> sanitize_for_python("123invalid")
        '_123invalid'
        >>> sanitize_for_python("my-var")
        'my_var'
        >>> sanitize_for_python("class")
        'class_'
    """
    if not name:
        return "_"

    # Replace invalid characters
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)

    # Ensure starts with letter or underscore
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"

    # Handle Python keywords
    import builtins
    import keyword

    if (
        hasattr(builtins, sanitized)
        or keyword.iskeyword(sanitized)
        or sanitized
        in [
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        ]
    ):
        sanitized = f"{sanitized}_"

    return sanitized
