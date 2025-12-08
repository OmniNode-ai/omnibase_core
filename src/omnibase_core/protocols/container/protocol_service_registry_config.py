"""
Protocol for service registry configuration.

This module provides the ProtocolServiceRegistryConfig protocol which
defines the interface for comprehensive service registry configuration
including auto-wiring, lazy loading, and monitoring settings.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue


@runtime_checkable
class ProtocolServiceRegistryConfig(Protocol):
    """
    Protocol for service registry configuration.

    Defines the interface for comprehensive service registry configuration
    including auto-wiring, lazy loading, and monitoring settings.
    """

    registry_name: str
    auto_wire_enabled: bool
    lazy_loading_enabled: bool
    circular_dependency_detection: bool
    max_resolution_depth: int
    instance_pooling_enabled: bool
    health_monitoring_enabled: bool
    performance_monitoring_enabled: bool
    configuration: dict[str, ContextValue]


__all__ = ["ProtocolServiceRegistryConfig"]
