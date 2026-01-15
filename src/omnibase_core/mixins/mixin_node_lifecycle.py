from datetime import datetime

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
Node EnumLifecycle Mixin.

This mixin handles:
- Node registration on the event bus
- Node shutdown and graceful cleanup
- Publishing lifecycle events (START, SUCCESS, FAILURE)
- Cleanup event handlers and resources
"""

import atexit
from pathlib import Path
from uuid import UUID, uuid4

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_node_status import EnumNodeStatus
from omnibase_core.enums.enum_registry_execution_mode import EnumRegistryExecutionMode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.core.model_event_type import create_event_type_from_registry
from omnibase_core.models.core.model_log_context import ModelLogContext
from omnibase_core.models.core.model_node_announce_metadata import (
    ModelNodeAnnounceMetadata,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.core.model_onex_event_metadata import ModelOnexEventMetadata
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.typed_dict_lifecycle_event_fields import (
    TypedDictLifecycleEventFields,
)

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem


def _ensure_uuid(value: UUID | None) -> UUID:
    """Ensure value is a UUID, generate if None."""
    if value is None:
        return uuid4()
    return value


def _get_node_id_as_uuid(obj: object) -> UUID:
    """Get node_id as UUID from object, converting if necessary."""
    node_id = getattr(obj, "_node_id", None)
    if isinstance(node_id, UUID):
        return node_id
    if isinstance(node_id, str):
        try:
            return UUID(node_id)
        except (AttributeError, ValueError):
            pass
    # Fallback: generate new UUID if invalid
    return uuid4()


class MixinNodeLifecycle:
    """
    Mixin for node lifecycle management.

    Provides methods for node registration, shutdown, and lifecycle event publishing.
    Uses getattr() for all host class attribute access.
    """

    def _register_node(self) -> None:
        """Register this node on the event bus using NODE_ANNOUNCE (protocol-pure)."""
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        node_id = _get_node_id_as_uuid(self)

        # --- Load node metadata block from node.onex.yaml ---
        try:
            metadata_loader = getattr(self, "metadata_loader", None)
            if metadata_loader and hasattr(metadata_loader, "metadata"):
                metadata_block = metadata_loader.metadata
            else:
                # Create minimal metadata block
                from omnibase_core.models.core.model_node_metadata_block import (
                    ModelNodeMetadataBlock,
                )

                # Use ModelSemVer for version instead of string literal
                default_version = ModelSemVer(major=1, minor=0, patch=0)
                metadata_block = ModelNodeMetadataBlock(
                    name=self.__class__.__name__.lower(),
                    version=default_version,
                    description="Event-driven ONEX node",
                    author="ONEX",
                )
        except PYDANTIC_MODEL_ERRORS as e:  # fallback-ok: registration failure returns early with logging, node registration is non-critical
            # Uses PYDANTIC_MODEL_ERRORS (AttributeError, TypeError, ValidationError, ValueError)
            # to catch metadata loading failures while allowing other exceptions to propagate
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_register_node",
                calling_line=67,
                timestamp=datetime.now().isoformat(),
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
                    EnumRegistryExecutionMode.MEMORY,
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
                schema_version=parse_semver_from_string(
                    getattr(metadata_block, "schema_version", None) or "1.0.0"
                ),
                timestamp=datetime.now(),
                signature_block=getattr(self, "signature_block", None),
                node_version=parse_semver_from_string(
                    getattr(self, "node_version", None)
                    or getattr(metadata_block, "version", None)
                    or "1.0.0"
                ),
                correlation_id=uuid4(),
            )

            event = ModelOnexEvent(
                event_type=create_event_type_from_registry("NODE_ANNOUNCE"),
                node_id=node_id,
                metadata=ModelOnexEventMetadata.from_node_announce(announce),
            )

            # Wrap in envelope before publishing
            envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                payload=event,
                source_tool=node_id,
                correlation_id=announce.correlation_id,
            )
            event_bus.publish(envelope)

            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_register_node",
                calling_line=106,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.INFO,
                f"Node {node_id} announced on event bus (NODE_ANNOUNCE)",
                context=context,
            )

        # fallback-ok: event publishing is non-critical, log and continue
        except Exception as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_register_node",
                calling_line=118,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to publish NODE_ANNOUNCE: {e}",
                context=context,
            )

    def _register_shutdown_hook(self) -> None:
        """Register shutdown hook for cleanup."""

        def shutdown_handler() -> None:
            self._publish_shutdown_event()

        atexit.register(shutdown_handler)

    def _publish_shutdown_event(self) -> None:
        """
        Publish NODE_SHUTDOWN_EVENT for graceful deregistration.
        """
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        node_id = _get_node_id_as_uuid(self)

        try:
            # Create shutdown event
            shutdown_event = ModelNodeShutdownEvent.create_graceful_shutdown(
                node_id=node_id,
                node_name=self.__class__.__name__.lower(),
            )

            # Wrap in envelope and publish event
            envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                payload=shutdown_event,
                source_tool=node_id,
                correlation_id=shutdown_event.correlation_id,
            )
            event_bus.publish(envelope)

            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_shutdown_event",
                calling_line=152,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.INFO,
                f"Published shutdown event for node {node_id}",
                context=context,
            )

        # fallback-ok: shutdown event is non-critical, log and continue
        except Exception as e:
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_publish_shutdown_event",
                calling_line=164,
                timestamp=datetime.now().isoformat(),
                node_id=node_id,
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to publish shutdown event: {e}",
                context=context,
            )

    def emit_node_start(
        self,
        metadata: TypedDictLifecycleEventFields | None = None,
        correlation_id: UUID | None = None,
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
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            # Still generate and return correlation ID even if no event bus
            return uuid4() if correlation_id is None else _ensure_uuid(correlation_id)

        node_id = _get_node_id_as_uuid(self)

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            final_correlation_id = uuid4()
        else:
            final_correlation_id = _ensure_uuid(correlation_id)

        try:
            event = ModelOnexEvent(
                event_type=create_event_type_from_registry("NODE_START"),
                node_id=node_id,
                metadata=ModelOnexEventMetadata(**metadata) if metadata else None,
                correlation_id=final_correlation_id,
            )

            # Wrap in envelope before publishing
            envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                payload=event,
                source_tool=node_id,
                correlation_id=final_correlation_id,
            )
            event_bus.publish(envelope)

        except Exception as e:  # fallback-ok: lifecycle event emission is non-critical, log and continue
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            log_context: dict[str, JsonType] = {
                "event_type": "lifecycle_error",
                "node_id": str(node_id),
                "event_type_label": "NODE_START",
                "error": str(e),
            }
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to emit NODE_START event: {e}",
                log_context,
            )

        return final_correlation_id

    def emit_node_success(
        self,
        metadata: TypedDictLifecycleEventFields | None = None,
        correlation_id: UUID | None = None,
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
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            # Still generate and return correlation ID even if no event bus
            return uuid4() if correlation_id is None else _ensure_uuid(correlation_id)

        node_id = _get_node_id_as_uuid(self)

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            final_correlation_id = uuid4()
        else:
            final_correlation_id = _ensure_uuid(correlation_id)

        try:
            event = ModelOnexEvent(
                event_type=create_event_type_from_registry("NODE_SUCCESS"),
                node_id=node_id,
                metadata=ModelOnexEventMetadata(**metadata) if metadata else None,
                correlation_id=final_correlation_id,
            )

            # Wrap in envelope before publishing
            envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                payload=event,
                source_tool=node_id,
                correlation_id=final_correlation_id,
            )
            event_bus.publish(envelope)

        except Exception as e:  # fallback-ok: lifecycle event emission is non-critical, log and continue
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            log_context: dict[str, JsonType] = {
                "event_type": "lifecycle_error",
                "node_id": str(node_id),
                "event_type_label": "NODE_SUCCESS",
                "error": str(e),
            }
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to emit NODE_SUCCESS event: {e}",
                log_context,
            )

        return final_correlation_id

    def emit_node_failure(
        self,
        metadata: TypedDictLifecycleEventFields | None = None,
        correlation_id: UUID | None = None,
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
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            # Still generate and return correlation ID even if no event bus
            return uuid4() if correlation_id is None else _ensure_uuid(correlation_id)

        node_id = _get_node_id_as_uuid(self)

        # Handle correlation ID using UUID architecture pattern
        if correlation_id is None:
            final_correlation_id = uuid4()
        else:
            final_correlation_id = _ensure_uuid(correlation_id)

        try:
            event = ModelOnexEvent(
                event_type=create_event_type_from_registry("NODE_FAILURE"),
                node_id=node_id,
                metadata=ModelOnexEventMetadata(**metadata) if metadata else None,
                correlation_id=final_correlation_id,
            )

            # Wrap in envelope before publishing
            envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                payload=event,
                source_tool=node_id,
                correlation_id=final_correlation_id,
            )
            event_bus.publish(envelope)

        except Exception as e:  # fallback-ok: lifecycle event emission is non-critical, log and continue
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            log_context: dict[str, JsonType] = {
                "event_type": "lifecycle_error",
                "node_id": str(node_id),
                "event_type_label": "NODE_FAILURE",
                "error": str(e),
            }
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Failed to emit NODE_FAILURE event: {e}",
                log_context,
            )

        return final_correlation_id

    def cleanup_lifecycle_resources(self) -> None:
        """Clean up lifecycle-related resources."""
        # Publish shutdown event if not already done
        self._publish_shutdown_event()

        # Clean up event handlers if available
        if hasattr(self, "cleanup_event_handlers"):
            try:
                self.cleanup_event_handlers()
            # fallback-ok: cleanup failure is non-critical, log and continue
            except Exception as e:
                node_id = _get_node_id_as_uuid(self)
                context = ModelLogContext(
                    calling_module=_COMPONENT_NAME,
                    calling_function="cleanup_lifecycle_resources",
                    calling_line=283,
                    timestamp=datetime.now().isoformat(),
                    node_id=node_id,
                )
                emit_log_event_sync(
                    LogLevel.WARNING,
                    f"Error during event handler cleanup: {e}",
                    context=context,
                )
