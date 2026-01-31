"""Protocols Namespace Model.

Provides an immutable namespace for resolved protocol dependencies.

This model enables ergonomic access to protocol dependencies via attribute
or dictionary syntax while enforcing immutability after initialization.
Used by contract-driven nodes to access resolved protocol instances.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


class ModelProtocolsNamespace:
    """
    Immutable namespace for resolved protocol dependencies.

    Provides multiple access patterns for resolved protocols:
    - Attribute access: self.protocols.logger
    - Dict access: self.protocols["logger"]
    - Iteration: for name in self.protocols
    - Membership: "logger" in self.protocols

    CRITICAL: This class is immutable after initialization.
    Any attempt to modify attributes after creation will raise AttributeError.

    Attributes:
        _frozen: Flag indicating whether the namespace is frozen.
        _protocols: Internal dict storing protocol name to instance mapping.

    Example:
        ```python
        protocols = ModelProtocolsNamespace({
            "logger": LoggerService(),
            "event_bus": EventBusService(),
        })

        # Attribute access
        logger = protocols.logger

        # Dict access
        event_bus = protocols["event_bus"]

        # Membership test
        if "logger" in protocols:
            print("Logger available")

        # Iteration
        for name in protocols:
            print(f"Protocol: {name}")
        ```

    Thread Safety:
        This class is thread-safe after initialization because it is
        immutable. The frozen state prevents any modifications.
    """

    __slots__ = ("_frozen", "_protocols")

    def __init__(self, protocols: dict[str, Any | None]) -> None:
        """
        Initialize the protocols namespace and freeze it.

        Args:
            protocols: Dict mapping protocol names to resolved instances.
                       Values may be None for optional protocols.
        """
        # Use object.__setattr__ to bypass our __setattr__ override
        # pydantic-bypass-ok: Required for frozen namespace initialization
        object.__setattr__(self, "_protocols", dict(protocols))
        object.__setattr__(self, "_frozen", True)

    def __getattr__(self, name: str) -> Any:
        """
        Get a protocol by attribute access.

        Args:
            name: The protocol name to retrieve.

        Returns:
            The resolved protocol instance.

        Raises:
            AttributeError: If the protocol name is not found.
        """
        # Avoid infinite recursion for internal attributes
        if name.startswith("_"):
            # error-ok: Standard Python AttributeError for missing private attributes
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        protocols = object.__getattribute__(self, "_protocols")
        if name in protocols:
            return protocols[name]

        available = sorted(protocols.keys())
        # error-ok: Standard Python AttributeError for missing attributes per __getattr__ contract
        raise AttributeError(f"Protocol '{name}' not found. Available: {available}")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Prevent attribute modification after initialization.

        Args:
            name: The attribute name.
            value: The value to set.

        Raises:
            AttributeError: Always, if the namespace is frozen.
        """
        # Check if we're frozen (use object.__getattribute__ to avoid recursion)
        try:
            frozen = object.__getattribute__(self, "_frozen")
        except AttributeError:
            # Not frozen yet (during __init__), allow the set
            # pydantic-bypass-ok: Required for initialization before frozen
            object.__setattr__(self, name, value)
            return

        if frozen:
            # error-ok: Standard Python AttributeError for immutable objects per __setattr__ contract
            raise AttributeError(
                "ModelProtocolsNamespace is immutable after initialization"
            )

        # pydantic-bypass-ok: Required for initialization before frozen
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        """
        Prevent attribute deletion.

        Args:
            name: The attribute name.

        Raises:
            AttributeError: Always, namespace is immutable.
        """
        # error-ok: Standard Python AttributeError for immutable objects per __delattr__ contract
        raise AttributeError(
            "ModelProtocolsNamespace is immutable after initialization"
        )

    def __getitem__(self, name: str) -> Any:
        """
        Get a protocol by dict-style access.

        Args:
            name: The protocol name to retrieve.

        Returns:
            The resolved protocol instance.

        Raises:
            KeyError: If the protocol name is not found.
        """
        protocols = object.__getattribute__(self, "_protocols")
        if name in protocols:
            return protocols[name]

        available = sorted(protocols.keys())
        # error-ok: Standard Python KeyError for missing keys per __getitem__ contract
        raise KeyError(f"Protocol '{name}' not found. Available: {available}")

    def __contains__(self, name: object) -> bool:
        """
        Check if a protocol name exists in the namespace.

        Args:
            name: The protocol name to check.

        Returns:
            True if the protocol exists, False otherwise.
        """
        protocols = object.__getattribute__(self, "_protocols")
        return name in protocols

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over protocol names.

        Returns:
            Iterator yielding protocol names.
        """
        protocols = object.__getattribute__(self, "_protocols")
        return iter(protocols)

    def __len__(self) -> int:
        """
        Get the number of protocols in the namespace.

        Returns:
            Number of protocols.
        """
        protocols = object.__getattribute__(self, "_protocols")
        return len(protocols)

    def keys(self) -> list[str]:
        """
        Get a list of protocol names.

        Returns:
            List of protocol names in the namespace.
        """
        protocols = object.__getattribute__(self, "_protocols")
        return list(protocols.keys())

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a protocol with a default fallback.

        Args:
            name: The protocol name to retrieve.
            default: Value to return if protocol not found.

        Returns:
            The resolved protocol instance, or default if not found.
        """
        protocols = object.__getattribute__(self, "_protocols")
        return protocols.get(name, default)

    def __repr__(self) -> str:
        """
        Return a debug representation of the namespace.

        Returns:
            String representation showing protocol names and their types.

        Example:
            >>> ns = ModelProtocolsNamespace({"logger": LoggerService(), "cache": None})
            >>> repr(ns)
            "ModelProtocolsNamespace({'cache': None, 'logger': LoggerService})"
        """
        protocols = object.__getattribute__(self, "_protocols")
        items = {
            k: type(v).__name__ if v is not None else None
            for k, v in sorted(protocols.items())
        }
        return f"ModelProtocolsNamespace({items})"


__all__ = ["ModelProtocolsNamespace"]
