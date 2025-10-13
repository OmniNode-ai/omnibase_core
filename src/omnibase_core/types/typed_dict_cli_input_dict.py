from __future__ import annotations

import uuid

"""
CLI Input Dictionary TypedDict.

Provides TypedDict for CLI input parameters with proper typing.
"""


from typing import TypedDict
from uuid import UUID


class TypedDictCliInputDict(TypedDict, total=False):
    """Type definition for CLI input dict[str, Any]ionary."""

    action: str
    output_format: str
    verbose: bool
    request_id: UUID
    execution_context: str | None
    target_node: str | None
    category_filter: str | None


# Export for use
__all__ = ["TypedDictCliInputDict"]
