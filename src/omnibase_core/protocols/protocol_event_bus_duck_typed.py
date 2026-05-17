# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Duck-typed event bus protocol for optional publish method access."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolEventBusDuckTyped(Protocol):
    """Protocol for duck-typed event bus method access.

    This protocol defines the interface for event bus operations that may not be
    present on all event bus implementations. It is used with cast() to provide
    type-safe access to optional methods while maintaining compatibility with
    legacy event bus implementations.

    The protocol is runtime_checkable to support hasattr() checks before method calls.
    """

    def publish(self, event: object) -> None:
        """Synchronous publish method."""
        ...

    async def publish_async(self, envelope: object) -> None:
        """Asynchronous publish method."""
        ...


__all__ = ["ProtocolEventBusDuckTyped"]
