from typing import Union

"""
ModelUnionPattern

Represents a Union pattern for analysis.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


class ModelUnionPattern:
    """Represents a Union pattern for analysis."""

    def __init__(self, types: list[str], line: int, file_path: str):
        self.types = sorted(types)  # Sort for consistent comparison
        self.line = line
        self.file_path = file_path
        self.type_count = len(types)

    def __hash__(self) -> int:
        return hash(tuple(self.types))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ModelUnionPattern) and self.types == other.types

    def get_signature(self) -> str:
        """Get a string signature for this union pattern."""
        return f"Union[{', '.join(self.types)}]"
