"""ModelUnionPattern - Represents a Union type pattern for static analysis.

This module provides the ModelUnionPattern class used by union validation tools
to represent and analyze Union type definitions found in Python source code.

The class is designed to be lightweight and hashable for use in pattern
detection and deduplication across files.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only

Example:
    >>> pattern = ModelUnionPattern(["str", "int", "None"], line=42, file_path="model.py")
    >>> pattern.get_signature()
    'Union[None, int, str]'
    >>> pattern.type_count
    3
"""


class ModelUnionPattern:
    """Represents a Union type pattern extracted from source code for analysis.

    This class encapsulates information about a Union type definition found
    in Python source code, including the types it contains and its location.
    Used by union validation tools for pattern classification and detection.

    Attributes:
        types: Sorted list of type names in the union (sorted for comparison).
        line: Line number where the union was defined (1-based).
        file_path: Path to the file containing the union.
        type_count: Number of types in the union.

    Example:
        >>> pattern = ModelUnionPattern(["int", "str"], line=10, file_path="test.py")
        >>> pattern.get_signature()
        'Union[int, str]'
        >>> hash(pattern) == hash(ModelUnionPattern(["str", "int"], 20, "other.py"))
        True
    """

    def __init__(self, types: list[str], line: int, file_path: str) -> None:
        """Initialize a ModelUnionPattern instance.

        Args:
            types: List of type names in the union. Will be sorted for
                consistent comparison and hashing.
            line: Line number where the union is defined (1-based).
            file_path: Path to the source file containing the union.
        """
        self.types = sorted(types)  # Sort for consistent comparison
        self.line = line
        self.file_path = file_path
        self.type_count = len(types)

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        The hash is computed from the sorted types tuple only, so patterns
        with the same types in different files will hash to the same value.

        Returns:
            int: Hash computed from the sorted union types tuple.
        """
        return hash(tuple(self.types))

    def __eq__(self, other: object) -> bool:
        """Check equality with another ModelUnionPattern.

        Two patterns are equal if they have the same types (ignoring order,
        line number, and file path). This allows detecting repeated patterns
        across different locations.

        Args:
            other: Object to compare against.

        Returns:
            True if other is a ModelUnionPattern with the same types.
        """
        return isinstance(other, ModelUnionPattern) and self.types == other.types

    def get_signature(self) -> str:
        """Get a string signature for this union pattern.

        Returns:
            String representation in Union[...] format with sorted types.

        Example:
            >>> pattern = ModelUnionPattern(["bool", "str"], 1, "test.py")
            >>> pattern.get_signature()
            'Union[bool, str]'
        """
        return f"Union[{', '.join(self.types)}]"
