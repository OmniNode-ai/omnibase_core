"""
ProtocolComputePayloadData - Protocol for polymorphic data in compute pipelines.

This protocol defines the interface for data objects that can be traversed
in compute pipelines. It supports dict-like access, Pydantic models, and
regular Python objects with attributes.

Note:
    This is distinct from ProtocolPayloadData in omnibase_core.protocols which
    provides a full dict-like interface (get, keys, values, items, etc.).
    ProtocolComputePayloadData is a marker protocol with no required methods,
    designed for maximum flexibility in compute pipeline data types.

Design:
    This protocol uses structural subtyping (duck typing) to allow any object
    that supports the required access patterns to be used in pipeline operations.
    The protocol is intentionally minimal to maximize compatibility.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.compute import ProtocolComputePayloadData

        # Dict-like access
        data: ProtocolComputePayloadData = {"key": "value"}

        # Pydantic model
        class UserModel(BaseModel):
            name: str
            age: int

        user: ProtocolComputePayloadData = UserModel(name="Alice", age=30)

        # Regular object with attributes
        @dataclass
        class Config:
            debug: bool = False

        config: ProtocolComputePayloadData = Config()

Related:
    - compute_executor.py: Uses this for pipeline data flows
    - compute_transformations.py: Uses this for transformation inputs
    - compute_path_resolver.py: Uses this for path traversal

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ProtocolComputePayloadData", "ProtocolDictLike"]

from collections.abc import Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolDictLike(Protocol):
    """
    Protocol for objects that support dictionary-like access.

    This protocol defines the minimal interface for dict-like objects
    used in path resolution and data traversal. Objects implementing
    this protocol can be navigated using key-based access.

    Note:
        This protocol is satisfied by:
        - dict instances
        - Mapping implementations
        - Objects with __getitem__ and keys methods
    """

    def __getitem__(self, key: str) -> object:
        """Get a value by key."""
        ...

    def keys(self) -> Iterator[str]:
        """Return the keys of the container."""
        ...

    def __contains__(self, key: object) -> bool:
        """Check if a key exists in the container."""
        ...


@runtime_checkable
class ProtocolComputePayloadData(Protocol):
    """
    Protocol for polymorphic payload data in compute pipelines.

    This protocol is satisfied by any object that can be used as
    data in compute pipeline operations:
    - Dictionaries (dict[str, object])
    - Pydantic BaseModel instances (via model_dump)
    - Regular objects with attributes (via getattr)

    The protocol is minimal by design - it doesn't require specific
    methods since different data types are accessed differently:
    - Dicts: via __getitem__
    - Objects: via getattr

    This protocol is primarily used as a type marker to indicate
    that a parameter accepts polymorphic data. Actual data access
    is handled by the path resolution utilities which check for
    dict vs object at runtime.

    Note:
        This is distinct from ProtocolPayloadData in omnibase_core.protocols
        which provides a full dict-like interface with get(), keys(), values(),
        items(), __getitem__(), and __contains__() methods.

    Thread Safety:
        This protocol makes no thread safety guarantees. The underlying
        data objects should be treated as read-only during pipeline execution.

    Example:
        .. code-block:: python

            def process_data(data: ProtocolComputePayloadData) -> str:
                # Data can be dict, Pydantic model, or object
                if isinstance(data, dict):
                    return str(data.get("value", ""))
                return str(getattr(data, "value", ""))

    .. versionadded:: 0.4.0
    """

    # Marker protocol - no required methods
    # This allows any object to satisfy the protocol
    # Actual access patterns are determined at runtime
