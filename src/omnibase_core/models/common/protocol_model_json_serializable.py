from __future__ import annotations

"""
ModelProtocolJsonSerializable

Protocol for values that can be JSON serialized.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelProtocolJsonSerializable(Protocol):
    """Protocol for values that can be JSON serialized."""

    # Built-in types that implement this: str, int, float, bool, list[Any], dict[str, Any], None
