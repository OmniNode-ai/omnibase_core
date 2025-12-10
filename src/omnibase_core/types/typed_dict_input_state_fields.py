"""TypedDict for input state fields structure.

ONEX Architectural Pattern:
- TypedDict definitions belong in types/ directory
- Class name: TypedDictInputStateFields (TypedDict prefix)
- File name: typed_dict_input_state_fields.py (typed_dict_ prefix)
"""

from typing import TypedDict


class TypedDictInputStateFields(TypedDict, total=False):
    """Type-safe input state fields structure for metadata operations."""

    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str


__all__ = ["TypedDictInputStateFields"]
