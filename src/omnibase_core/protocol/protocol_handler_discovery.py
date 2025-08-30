# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-01-27T00:00:00.000000'
# description: Protocol for handler discovery and registration
# entrypoint: python://protocol_handler_discovery
# hash: 0000000000000000000000000000000000000000000000000000000000000000
# last_modified_at: '2025-01-27T00:00:00.000000'
# lifecycle: active
# meta_type: protocol
# metadata_version: 0.1.0
# name: protocol_handler_discovery.py
# namespace: python://omnibase.protocol.protocol_handler_discovery
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 00000000-0000-0000-0000-000000000000
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Protocol for handler discovery and registration.

This protocol defines the interface for discovering and registering file type handlers
without requiring hardcoded imports in the core registry. It enables plugin-based
architecture where handlers can be discovered dynamically.
"""

from abc import ABC, abstractmethod
from typing import Any

from omnibase_core.protocol.protocol_file_type_handler import ProtocolFileTypeHandler


class HandlerInfo:
    """Information about a discovered handler."""

    def __init__(
        self,
        handler_class: type[ProtocolFileTypeHandler],
        name: str,
        source: str,
        priority: int = 0,
        extensions: list[str] | None = None,
        special_files: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.handler_class = handler_class
        self.name = name
        self.source = source  # "core", "runtime", "node-local", "plugin"
        self.priority = priority
        self.extensions = extensions or []
        self.special_files = special_files or []
        self.metadata = metadata or {}


class ProtocolHandlerDiscovery(ABC):
    """
    Protocol for discovering file type handlers.

    Implementations of this protocol can discover handlers from various sources
    (entry points, configuration files, environment variables, etc.) without
    requiring hardcoded imports in the core registry.
    """

    @abstractmethod
    def discover_handlers(self) -> list[HandlerInfo]:
        """
        Discover available handlers.

        Returns:
            List of HandlerInfo objects for discovered handlers
        """

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the name of this discovery source.

        Returns:
            Human-readable name for this discovery source
        """


class ProtocolHandlerRegistry(ABC):
    """
    Protocol for handler registries that support dynamic discovery.

    This protocol extends the basic handler registry with discovery capabilities,
    allowing handlers to be registered from multiple sources without hardcoded imports.
    """

    @abstractmethod
    def register_discovery_source(self, discovery: ProtocolHandlerDiscovery) -> None:
        """
        Register a handler discovery source.

        Args:
            discovery: Handler discovery implementation
        """

    @abstractmethod
    def discover_and_register_handlers(self) -> None:
        """
        Discover and register handlers from all registered discovery sources.
        """

    @abstractmethod
    def register_handler_info(self, handler_info: HandlerInfo) -> None:
        """
        Register a handler from HandlerInfo.

        Args:
            handler_info: Information about the handler to register
        """
