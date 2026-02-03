"""
Protocol for node identity in event bus subscriptions.

This module provides the ProtocolNodeIdentity protocol definition used
for identifying nodes when subscribing to event bus topics. The node
identity is used to derive consumer group IDs in the canonical format:
``{env}.{service}.{node_name}.{purpose}.{version}``.

Design Principles:
- Minimal interface: Only the fields needed for consumer group derivation
- Runtime checkable: Supports duck typing with @runtime_checkable
- Decoupled from implementations: Infra's ModelNodeIdentity satisfies this

Example:
    >>> class MyNodeIdentity:
    ...     env = "dev"
    ...     service = "my-service"
    ...     node_name = "my-handler"
    ...     version = "v1"
    ...
    >>> identity = MyNodeIdentity()
    >>> assert isinstance(identity, ProtocolNodeIdentity)  # True via duck typing
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolNodeIdentity(Protocol):
    """
    Protocol for node identity used in event bus subscriptions.

    This protocol defines the minimal interface for identifying a node
    when subscribing to event bus topics. Implementations provide the
    components needed to derive a consumer group ID.

    The consumer group ID is typically derived as:
        ``{env}.{service}.{node_name}.{purpose}.{version}``

    Attributes:
        env: Environment name (e.g., "dev", "staging", "prod").
        service: Service name (e.g., "omniintelligence", "omnimemory").
        node_name: Node or handler name (e.g., "claude_hook_effect").
        version: Version string (e.g., "v1", "v2").

    Example:
        >>> class MyIdentity:
        ...     env = "dev"
        ...     service = "my-service"
        ...     node_name = "my-node"
        ...     version = "v1"
        ...
        >>> identity = MyIdentity()
        >>> # Consumer group: "dev.my-service.my-node.consume.v1"
    """

    @property
    def env(self) -> str:
        """Environment name (e.g., 'dev', 'staging', 'prod')."""
        ...

    @property
    def service(self) -> str:
        """Service name (e.g., 'omniintelligence')."""
        ...

    @property
    def node_name(self) -> str:
        """Node or handler name (e.g., 'claude_hook_effect')."""
        ...

    @property
    def version(self) -> str:
        """Version string (e.g., 'v1')."""
        ...


__all__ = ["ProtocolNodeIdentity"]
