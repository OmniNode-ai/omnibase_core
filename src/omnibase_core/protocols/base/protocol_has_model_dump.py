"""
HasModelDump Protocol.

Protocol for objects that support Pydantic model_dump method. This protocol
ensures compatibility with Pydantic models and other objects that provide
dictionary serialization via model_dump.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolHasModelDump(Protocol):
    """
    Protocol for objects that support Pydantic model_dump method.

    This protocol ensures compatibility with Pydantic models and other
    objects that provide dictionary serialization via model_dump.
    """

    def model_dump(
        self, mode: str | None = None
    ) -> dict[str, str | int | float | bool | list[object] | dict[str, object]]:
        """Serialize the model to a dictionary."""
        ...


__all__ = ["ProtocolHasModelDump"]
