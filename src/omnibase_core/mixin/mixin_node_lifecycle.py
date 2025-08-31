# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-04T02:45:00.000000'
# description: Node lifecycle management mixin for event-driven nodes
# entrypoint: python://mixin_node_lifecycle
# lifecycle: active
# meta_type: mixin
# metadata_version: 0.1.0
# name: mixin_node_lifecycle.py
# namespace: python://omnibase.mixin.mixin_node_lifecycle
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Node Lifecycle Mixin.

This mixin handles:
- Node registration on the event bus
- Node shutdown and graceful cleanup
- Publishing lifecycle events (START, SUCCESS, FAILURE)
- Cleanup event handlers and resources
"""

import atexit
import datetime
from pathlib import Path
from uuid import UUID, uuid4

from omnibase.enums.enum_node_status import EnumNodeStatus

from omnibase_core.core.core_structured_logging import emit_log_event_sync
from omnibase_core.core.core_uuid_service import UUIDService
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_registry_execution_mode import RegistryExecutionModeEnum
from omnibase_core.model.core.model_event_type import create_event_type_from_string
from omnibase_core.model.core.model_log_context import ModelLogContext
from omnibase_core.model.core.model_node_announce_metadata import (
    ModelNodeAnnounceMetadata,
)
from omnibase_core.model.core.model_onex_event import OnexEvent
from omnibase_core.model.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem


class MixinNodeLifecycle:
    """
    Mixin for node lifecycle management.

    Provides methods for node registration, shutdown, and lifecycle event publishing.
    Uses getattr() for all host class attribute access.
    """

    def _register_node(self) -> None:
        """Register this node on the event bus using NODE_ANNOUNCE (protocol-pure)."""
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        node_id = getattr(self, "_node_id", "unknown")

        # --- Load node metadata block from node.onex.yaml ---
        try:
            metadata_loader = getattr(self, "metadata_loader", None)
            if metadata_loader and hasattr(metadata_loader, "metadata"):
                metadata_block = metadata_loader.metadata
            else:
                # Create minimal metadata block
                from omnibase_core.model.core.model_node_metadata import (
                    NodeMetadataBlock,
                )

                metadata_block = NodeMetadataBlock(
                    name=self.__class__.__name__.lower(),
                    version="1.0.0",
                    description="Event-driven ONEX node",
                    author="ONEX",
                )
        except Exception as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_register_node",
                calling_line=67,
                timestamp=datetime.datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to load node metadata for NODE_ANNOUNCE: {e}",
                context=context,
            )
            return

        # --- Construct ModelNodeAnnounceMetadata ---
        try:
            announce = ModelNodeAnnounceMetadata(
                node_id=node_id,
                metadata_block=metadata_block,
                status=getattr(self, "status", EnumNodeStatus.ACTIVE),
                execution_mode=getattr(
                    self,
                    "execution_mode",
                    RegistryExecutionModeEnum.MEMORY,
                ),
                inputs=getattr(self, "inputs", getattr(metadata_block, "inputs", None)),
                outputs=getattr(
                    self,
                    "outputs",
                    getattr(metadata_block, "outputs", None),
                ),
                graph_binding=getattr(self, "graph_binding", None),
                trust_state=getattr(self, "trust_state", None),
                ttl=getattr(self, "ttl", None),
                schema_version=getattr(metadata_block, "schema_version", "1.0.0"),
                timestamp=datetime.datetime.now(),
                signature_block=getattr(self, "signature_block", None),
                node_version=getattr(
                    self,
                    "node_version",
                    getattr(metadata_block, "version", "1.0.0"),
                ),
                correlation_id=uuid4(),
            )

            event = OnexEvent(
                event_type=create_event_type_from_string("NODE_ANNOUNCE"),
                node_id=node_id,
                metadata=announce,
            )
            event_bus.publish(event)

            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_register_node",
                calling_line=106,
                timestamp=datetime.datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.INFO,
                f"Node {node_id} announced on event bus (NODE_ANNOUNCE)",
                context=context,
            )

        except Exception as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_register_node",
                calling_line=118,
                timestamp=datetime.datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to publish NODE_ANNOUNCE: {e}",
                context=context,
            )

    def _register_shutdown_hook(self) -> None:
        """Register shutdown hook for cleanup."""

        def shutdown_handler():
            self._publish_shutdown_event()

        atexit.register(shutdown_handler)

    def _publish_shutdown_event(self) -> None:
        """
        Publish NODE_SHUTDOWN_EVENT for graceful deregistration.
        """
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        node_id = getattr(self, "_node_id", "unknown")

        try:
            # Create shutdown event
            shutdown_event = ModelNodeShutdownEvent.create_graceful_shutdown(
                node_id=node_id,
                node_name=self.__class__.__name__.lower(),
            )

            # Publish event
            event_bus.publish(shutdown_event)

            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_shutdown_event",
                calling_line=152,
                timestamp=datetime.datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.INFO,
                f"Published shutdown event for node {node_id}",
                context=context,
            )

        except Exception as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_shutdown_event",
                calling_line=164,
                timestamp=datetime.datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to publish shutdown event: {e}",
                context=context,
            )

    def emit_node_start(
        self,
        metadata: dict | None = None,
        correlation_id: str | UUID | None = None,
    ) -> UUID:
        """
        Emit NODE_START event.

        Entry point pattern: Generates correlation ID if not provided.

        Args:
            metadata: Optional metadata for the event
            correlation_id: Correlation ID for tracking (auto-generated if not provided)

        Returns:
            UUID: The correlation ID used for the event
        """
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            # Still generate and return correlation ID even if no event bus
            return (
                UUIDService.generate_correlation_id()
                if correlation_id is None
                else UUIDService.ensure_uuid(correlation_id)
            )

        node_id = getattr(self, "_node_id", "unknown")

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            final_correlation_id = UUIDService.generate_correlation_id()
        else:
            final_correlation_id = UUIDService.ensure_uuid(correlation_id)

        try:
            event = OnexEvent(
                event_type=create_event_type_from_string("NODE_START"),
                node_id=node_id,
                metadata=metadata,
                correlation_id=str(final_correlation_id),
            )
            event_bus.publish(event)

        except Exception as e:
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to emit NODE_START event: {e}",
                final_correlation_id,
                event_type="lifecycle_error",
                data={"node_id": node_id, "event_type": "NODE_START", "error": str(e)},
            )

        return final_correlation_id

    def emit_node_success(
        self,
        metadata: dict | None = None,
        correlation_id: str | UUID | None = None,
    ) -> UUID:
        """
        Emit NODE_SUCCESS event.

        Entry point pattern: Generates correlation ID if not provided.

        Args:
            metadata: Optional metadata for the event
            correlation_id: Correlation ID for tracking (auto-generated if not provided)

        Returns:
            UUID: The correlation ID used for the event
        """
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            # Still generate and return correlation ID even if no event bus
            return (
                UUIDService.generate_correlation_id()
                if correlation_id is None
                else UUIDService.ensure_uuid(correlation_id)
            )

        node_id = getattr(self, "_node_id", "unknown")

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            final_correlation_id = UUIDService.generate_correlation_id()
        else:
            final_correlation_id = UUIDService.ensure_uuid(correlation_id)

        try:
            event = OnexEvent(
                event_type=create_event_type_from_string("NODE_SUCCESS"),
                node_id=node_id,
                metadata=metadata,
                correlation_id=str(final_correlation_id),
            )
            event_bus.publish(event)

        except Exception as e:
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to emit NODE_SUCCESS event: {e}",
                final_correlation_id,
                event_type="lifecycle_error",
                data={
                    "node_id": node_id,
                    "event_type": "NODE_SUCCESS",
                    "error": str(e),
                },
            )

        return final_correlation_id

    def emit_node_failure(
        self,
        metadata: dict | None = None,
        correlation_id: str | UUID | None = None,
    ) -> UUID:
        """
        Emit NODE_FAILURE event.

        Entry point pattern: Generates correlation ID if not provided.

        Args:
            metadata: Optional metadata for the event
            correlation_id: Correlation ID for tracking (auto-generated if not provided)

        Returns:
            UUID: The correlation ID used for the event
        """
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            # Still generate and return correlation ID even if no event bus
            return (
                UUIDService.generate_correlation_id()
                if correlation_id is None
                else UUIDService.ensure_uuid(correlation_id)
            )

        node_id = getattr(self, "_node_id", "unknown")

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            final_correlation_id = UUIDService.generate_correlation_id()
        else:
            final_correlation_id = UUIDService.ensure_uuid(correlation_id)

        try:
            event = OnexEvent(
                event_type=create_event_type_from_string("NODE_FAILURE"),
                node_id=node_id,
                metadata=metadata,
                correlation_id=str(final_correlation_id),
            )
            event_bus.publish(event)

        except Exception as e:
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to emit NODE_FAILURE event: {e}",
                final_correlation_id,
                event_type="lifecycle_error",
                data={
                    "node_id": node_id,
                    "event_type": "NODE_FAILURE",
                    "error": str(e),
                },
            )

        return final_correlation_id

    def cleanup_lifecycle_resources(self) -> None:
        """Clean up lifecycle-related resources."""
        # Publish shutdown event if not already done
        self._publish_shutdown_event()

        # Clean up event handlers if available
        if hasattr(self, "cleanup_event_handlers"):
            try:
                self.cleanup_event_handlers()  # type: ignore
            except Exception as e:
                node_id = getattr(self, "_node_id", "unknown")
                context = ModelLogContext(
                    calling_module=_COMPONENT_NAME,
                    calling_function="cleanup_lifecycle_resources",
                    calling_line=283,
                    timestamp=datetime.datetime.now().isoformat(),
                    node_id=node_id,
                )
                emit_log_event_sync(
                    LogLevel.WARNING,
                    f"Error during event handler cleanup: {e}",
                    context=context,
                )
