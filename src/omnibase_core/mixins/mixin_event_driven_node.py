from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_mixin_types import TypedDictIntrospectionData

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-04T03:00:00.000000'
# description: Composed event-driven node mixin using focused mixins
# entrypoint: python://mixin_event_driven_node
# lifecycle: active
# meta_type: mixin
# metadata_version: 0.1.0
# name: mixin_event_driven_node.py
# namespace: python://omnibase.mixin.mixin_event_driven_node
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# version: 2.0.0
# === /OmniNode:Metadata ===

"""
Event-Driven Node Mixin.

This mixin provides event-driven capabilities for ONEX nodes by composing
focused mixins for different concerns:

- MixinIntrospectionPublisher: Auto-publishing introspection events
- MixinEventHandler: Handling incoming event requests
- MixinNodeLifecycle: Node registration and lifecycle management

Usage:
    class MyNode(MixinEventDrivenNode):
        def __init__(self, node_id: UUID, event_bus: ProtocolEventBus, ...):
            super().__init__(node_id=node_id, event_bus=event_bus, ...)
"""

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.discovery.base_discovery_registry import BaseDiscoveryRegistry

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# EnumToolNames removed - using direct string references
from omnibase_core.mixins.mixin_event_handler import MixinEventHandler
from omnibase_core.mixins.mixin_introspection_publisher import (
    MixinIntrospectionPublisher,
)
from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle
from omnibase_core.mixins.mixin_request_response_introspection import (
    MixinRequestResponseIntrospection,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.protocols import ProtocolEventBus, ProtocolSchemaLoader


class MixinEventDrivenNode(
    MixinEventHandler,
    MixinNodeLifecycle,
    MixinIntrospectionPublisher,
    MixinRequestResponseIntrospection,
):
    """
    Canonical mixin for event-driven ONEX nodes.

    Composes focused mixins to provide:
    - Automatic node registration and lifecycle management
    - Event handler setup for introspection and discovery requests
    - Auto-publishing of introspection events for service discovery
    - Request-response introspection for real-time discovery
    - All communication via event bus with no direct side effects
    """

    def __init__(
        self,
        node_id: UUID,
        event_bus: ProtocolEventBus,
        metadata_loader: ProtocolSchemaLoader | None = None,
        registry: "BaseDiscoveryRegistry | None" = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._node_id = node_id

        # ProtocolEventBus is now mandatory - no fallbacks
        if not event_bus:
            raise ModelOnexError(
                EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
                "ProtocolEventBus is mandatory for MixinEventDrivenNode - must be provided via dependency injection",
            )

        self.event_bus = event_bus
        self._event_bus = self.event_bus  # Make available for mixins

        # Metadata loader injection/fallback
        if (
            metadata_loader is None
            and registry is not None
            and hasattr(registry, "get_tool")
        ):
            metadata_loader_cls = registry.get_tool("tool_metadata_loader")
            if metadata_loader_cls is not None:
                # Handle both class and instance cases
                if isinstance(metadata_loader_cls, type):
                    metadata_loader = metadata_loader_cls()
                else:
                    # Already instantiated by registry
                    metadata_loader = metadata_loader_cls

        if metadata_loader is None:
            raise ModelOnexError(
                EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
                "[MixinEventDrivenNode] metadata_loader (ProtocolSchemaLoader) must be provided via DI/registry per ONEX standards.",
            )
        self.metadata_loader: ProtocolSchemaLoader = metadata_loader

        # Initialize all capabilities
        self._setup_event_handlers()
        self._setup_request_response_introspection()
        self._register_node()
        self._publish_introspection_event()
        self._register_shutdown_hook()

    @property
    def node_id(self) -> UUID:
        """Get the node ID."""
        return self._node_id

    def get_node_name(self) -> str:
        """Get the node name."""
        return self.__class__.__name__.lower()

    def get_node_version(self) -> str:
        """Get the node version."""
        try:
            metadata_loader = getattr(self, "metadata_loader", None)
            if metadata_loader and hasattr(metadata_loader, "metadata"):
                metadata = metadata_loader.metadata
                if metadata and hasattr(metadata, "version"):
                    return str(metadata.version)
            # Use ModelSemVer for default version instead of string literal
            default_version = ModelSemVer(major=0, minor=0, patch=0)
            return str(default_version)
        except (AttributeError, ValueError) as e:
            msg = f"Failed to load node version from metadata: {e}"
            raise ModelOnexError(
                EnumCoreErrorCode.METADATA_LOAD_FAILED,
                msg,
            )

    def get_capabilities(self) -> list[str]:
        """Get node capabilities."""
        return ["introspection", "discovery", "lifecycle"]

    def supports_introspection(self) -> bool:
        """Check if node supports introspection."""
        return True

    def get_introspection_data(self) -> TypedDictIntrospectionData:
        """Get introspection data."""
        try:
            # Use the method from MixinIntrospectionPublisher
            data = self._gather_introspection_data()
            if hasattr(data, "model_dump"):
                # Performance optimization: use direct attribute access where possible
                # instead of model_dump() to avoid full serialization overhead
                node_name = getattr(data, "node_name", None) or self.get_node_name()
                version = getattr(data, "version", None) or self.get_node_version()

                # Handle nested capabilities - only dump if needed
                capabilities_obj = getattr(data, "capabilities", None)
                if capabilities_obj is not None:
                    # Try direct access first, then model_dump if it's a model
                    actions = getattr(capabilities_obj, "actions", None)
                    if actions is None and hasattr(capabilities_obj, "model_dump"):
                        # Only serialize the actions field if direct access failed
                        cap_dict = capabilities_obj.model_dump(include={"actions"})
                        actions = cap_dict.get("actions", ["health_check"])
                    elif actions is None and isinstance(capabilities_obj, dict):
                        actions = capabilities_obj.get("actions", ["health_check"])
                    elif actions is None:
                        actions = ["health_check"]
                else:
                    actions = ["health_check"]

                return {
                    "node_name": str(node_name),
                    "node_id": str(self._node_id),
                    "version": str(version),
                    "capabilities": actions,
                    "status": "active",
                    "event_types_handled": ["introspection", "discovery"],
                }
            # Fallback for dict-like data
            return {
                "node_name": self.get_node_name(),
                "node_id": str(self._node_id),
                "version": self.get_node_version(),
                "capabilities": ["health_check"],
                "status": "active",
                "event_types_handled": ["introspection", "discovery"],
            }
        except (
            Exception
        ):  # fallback-ok: introspection is non-critical, return minimal metadata
            return {
                "node_name": self.get_node_name(),
                "node_id": str(self._node_id),
                "version": self.get_node_version(),
                "capabilities": ["health_check"],
                "status": "active",
                "event_types_handled": ["introspection", "discovery"],
            }

    def cleanup_event_handlers(self) -> None:
        """Clean up all event handlers and resources."""
        # Clean up request-response introspection
        try:
            self._teardown_request_response_introspection()
        except AttributeError:
            pass

        # Clean up event handlers from parent mixins
        try:
            # Call cleanup from MixinEventHandler if available
            super().cleanup_event_handlers()
        except AttributeError:
            pass

        # Clean up lifecycle resources from MixinNodeLifecycle
        try:
            self.cleanup_lifecycle_resources()
        except AttributeError:
            pass
