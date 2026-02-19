# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Protocol for event emission in validation orchestrator.

This module provides the protocol interface for event emission,
allowing dependency injection of the event bus.

Related ticket: OMN-1776
"""

from typing import Protocol

__all__ = ["ProtocolEventEmitter"]


class ProtocolEventEmitter(Protocol):
    """Protocol for event emission (allows for DI of event bus)."""

    async def emit(self, event: object) -> None:
        """Emit an event to the event bus."""
        ...
