# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Result model returned by domain plugin lifecycle hooks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

__all__: list[str] = ["ModelDomainPluginResult"]


@dataclass
class ModelDomainPluginResult:
    """Result returned by domain plugin lifecycle hooks.

    Attributes:
        plugin_id: Identifier of the plugin that produced this result.
        success: Whether the operation succeeded.
        message: Human-readable message describing the outcome.
        resources_created: List of resource identifiers created during this operation.
        services_registered: List of service class names registered in container.
        duration_seconds: Time taken for the operation.
        error_message: Error message if operation failed.
        unsubscribe_callbacks: Callbacks to invoke during shutdown for cleanup.
    """

    # string-id-ok: plugin names are human-readable identifiers, not UUIDs
    plugin_id: str
    success: bool
    message: str = ""
    resources_created: list[str] = field(default_factory=list)
    services_registered: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: str | None = None

    unsubscribe_callbacks: list[Callable[[], Awaitable[None]]] = field(
        default_factory=list
    )

    def get_error_message_or_default(self, default: str = "unknown") -> str:
        """Return error_message if set, otherwise the default value."""
        return self.error_message if self.error_message else default

    def __bool__(self) -> bool:
        """Return True if the operation succeeded.

        Warning:
            **Non-standard __bool__ behavior**: Returns ``True`` only when
            ``success`` is True. Differs from typical dataclass behavior.
        """
        return self.success

    @classmethod
    def succeeded(
        cls,
        plugin_id: str,
        message: str = "",
        duration_seconds: float = 0.0,
    ) -> ModelDomainPluginResult:
        """Create a simple success result."""
        return cls(
            plugin_id=plugin_id,
            success=True,
            message=message,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def failed(
        cls,
        plugin_id: str,
        error_message: str,
        message: str = "",
        duration_seconds: float = 0.0,
    ) -> ModelDomainPluginResult:
        """Create a failure result."""
        return cls(
            plugin_id=plugin_id,
            success=False,
            message=message or f"Plugin {plugin_id} failed",
            error_message=error_message,
            duration_seconds=duration_seconds,
        )

    @classmethod
    def skipped(
        cls,
        plugin_id: str,
        reason: str,
    ) -> ModelDomainPluginResult:
        """Create a skipped result (plugin did not activate)."""
        return cls(
            plugin_id=plugin_id,
            success=True,
            message=f"Plugin {plugin_id} skipped: {reason}",
        )
