from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import for event type validation
from omnibase_core.constants.constants_event_types import normalize_legacy_event_type
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_event_data import ModelEventData
from .model_event_type import ModelEventType
from .model_onex_event_metadata import ModelOnexEventMetadata
from .model_telemetry_operation_error_metadata import (
    ModelTelemetryOperationErrorMetadata,
)

# Import telemetry metadata classes from separate files
from .model_telemetry_operation_start_metadata import (
    ModelTelemetryOperationStartMetadata,
)
from .model_telemetry_operation_success_metadata import (
    ModelTelemetryOperationSuccessMetadata,
)

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.677980'
# description: Stamped by ToolPython
# entrypoint: python://model_onex_event
# hash: de98dbd4ad2b8aceb9d54f5f0911f0500bb06f4005203f57aa3d6dd44c0b62c8
# last_modified_at: '2025-05-29T14:13:58.847934+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_onex_event.py
# namespace: python://omnibase.model.model_onex_event
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: fe3fe6eb-ac1a-4f91-a5d1-8fba44bbb898
# version: 1.0.0
# === /OmniNode:Metadata ===


class ModelOnexEvent(BaseModel):
    """
    Enterprise-grade ONEX event model for event-driven architecture.

    Uses extensible string-based event types instead of hardcoded enums.
    Supports namespaced event types: core.category.action, user.namespace.action, etc.

    Examples:
        Core event: ModelOnexEvent(event_type="core.node.start", node_id="node-123")
        User event: ModelOnexEvent(event_type="user.mycompany.workflow_complete", node_id="worker-1")
        Plugin event: ModelOnexEvent(event_type="plugin.ai_assistant.completion", node_id="ai-node")
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )

    event_type: str | ModelEventType = Field(
        default=...,
        description="Event type - can be string or ModelEventType object",
    )
    node_id: UUID = Field(
        default=...,
        description="Unique identifier of the node that generated this event",
    )
    metadata: ModelOnexEventMetadata | None = Field(
        default=None,
        description="Optional event metadata",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp",
    )
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for request/response patterns",
    )
    data: ModelEventData | None = Field(default=None, description="Event payload data")

    @field_validator("event_type")
    @classmethod
    def validate_event_type_format(cls, v: object) -> str | ModelEventType:
        """
        Validate event type format and handle both string and ModelEventType inputs.

        Accepts:
        - ModelEventType objects (preferred)
        - String event types: "core.node.start"
        - Legacy enum values: EnumOnexEventType.NODE_START (automatically converted)

        Args:
            v: Event type value (string, enum, or ModelEventType)

        Returns:
            Validated event type (string or ModelEventType)

        Raises:
            ModelOnexError: If event type is invalid
        """
        # If it's already a ModelEventType, return it as-is
        if isinstance(v, ModelEventType):
            return v

        try:
            # Normalize legacy enum values to new string format
            return normalize_legacy_event_type(v)
        except ValueError as e:
            msg = f"Invalid event type: {e}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

    @classmethod
    def create_core_event(
        cls,
        event_type: str,
        node_id: UUID,
        correlation_id: UUID | None = None,
        **kwargs: Any,
    ) -> "ModelOnexEvent":
        """
        Factory method for creating core ONEX events.

        Args:
            event_type: Core event type (e.g., "core.node.start")
            node_id: Node identifier
            correlation_id: Optional correlation ID
            **kwargs: Additional event fields

        Returns:
            ModelOnexEvent instance
        """
        return cls(
            event_type=event_type,
            node_id=node_id,
            correlation_id=correlation_id,
            **kwargs,
        )

    @classmethod
    def create_user_event(
        cls,
        namespace: str,
        action: str,
        node_id: UUID,
        correlation_id: UUID | None = None,
        **kwargs: Any,
    ) -> "ModelOnexEvent":
        """
        Factory method for creating user-defined events.

        Args:
            namespace: User namespace (e.g., "mycompany")
            action: Event action (e.g., "workflow_complete")
            node_id: Node identifier
            correlation_id: Optional correlation ID
            **kwargs: Additional event fields

        Returns:
            ModelOnexEvent instance
        """
        event_type = f"user.{namespace}.{action}"
        return cls(
            event_type=event_type,
            node_id=node_id,
            correlation_id=correlation_id,
            **kwargs,
        )

    @classmethod
    def create_plugin_event(
        cls,
        plugin_name: str,
        action: str,
        node_id: UUID,
        correlation_id: UUID | None = None,
        **kwargs: Any,
    ) -> "ModelOnexEvent":
        """
        Factory method for creating plugin events.

        Args:
            plugin_name: Plugin name (e.g., "ai_assistant")
            action: Event action (e.g., "completion_request")
            node_id: Node identifier
            correlation_id: Optional correlation ID
            **kwargs: Additional event fields

        Returns:
            ModelOnexEvent instance
        """
        event_type = f"plugin.{plugin_name}.{action}"
        return cls(
            event_type=event_type,
            node_id=node_id,
            correlation_id=correlation_id,
            **kwargs,
        )

    def get_event_namespace(self) -> str | None:
        """Get the namespace portion of the event type."""
        if isinstance(self.event_type, ModelEventType):
            return self.event_type.namespace
        parts = str(self.event_type).split(".")
        return parts[0] if parts else None

    def is_core_event(self) -> bool:
        """Check if this is a core ONEX event."""
        return self.get_event_namespace() == "core"

    def is_user_event(self) -> bool:
        """Check if this is a user-defined event."""
        return self.get_event_namespace() == "user"

    def is_plugin_event(self) -> bool:
        """Check if this is a plugin event."""
        return self.get_event_namespace() == "plugin"


# Compatibility alias
OnexEvent = ModelOnexEvent

__all__ = [
    "ModelOnexEvent",
    "ModelTelemetryOperationErrorMetadata",
    "ModelTelemetryOperationStartMetadata",
    "ModelTelemetryOperationSuccessMetadata",
]
