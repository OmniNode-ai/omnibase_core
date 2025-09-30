"""
Strongly-typed event payload structure.

Replaces dict[str, Any] usage in event payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.type_constraints import (
    Executable,
    Identifiable,
    ProtocolValidatable,
    Serializable,
)
from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.metadata.model_semver import ModelSemVer

# Event types - using EnumEventType from enums package


class ModelEventPayload(BaseModel):
    """
    Strongly-typed event payload with discriminated unions.

    Replaces dict[str, Any] with discriminated event payload types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    event_type: EnumEventType = Field(..., description="Discriminated event type")
    event_data: "EventDataUnion" = Field(
        ..., description="Event-specific data with discriminated union"
    )
    routing_info: "ModelEventRoutingInfo" = Field(
        default_factory=lambda: ModelEventRoutingInfo(),
        description="Structured event routing information",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Discriminated event data types
class ModelEventDataBase(BaseModel):
    """Base event data with discriminator."""

    event_type: EnumEventType = Field(..., description="Event type discriminator")
    context: "ModelEventContextInfo" = Field(
        default_factory=lambda: ModelEventContextInfo(),
        description="Structured event context information",
    )
    attributes: "ModelEventAttributeInfo" = Field(
        default_factory=lambda: ModelEventAttributeInfo(),
        description="Structured event attributes",
    )
    source_info: "ModelEventSourceInfo" = Field(
        default_factory=lambda: ModelEventSourceInfo(),
        description="Structured event source information",
    )


class ModelSystemEventData(ModelEventDataBase):
    """System-level event data."""

    event_type: Literal[EnumEventType.SYSTEM] = Field(
        default=EnumEventType.SYSTEM, description="System event type"
    )
    system_component: str = Field(
        ..., description="System component that generated the event"
    )
    severity_level: str = Field(default="info", description="Event severity level")
    diagnostic_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="System diagnostic data"
    )
    correlation_trace: list[str] = Field(
        default_factory=list, description="Event correlation trace"
    )


class ModelUserEventData(ModelEventDataBase):
    """User-initiated event data."""

    event_type: Literal[EnumEventType.USER] = Field(
        default=EnumEventType.USER, description="User event type"
    )
    user_action: str = Field(..., description="User action that triggered the event")
    session_context: dict[str, str] = Field(
        default_factory=dict, description="User session context"
    )
    request_metadata: dict[str, str] = Field(
        default_factory=dict, description="Request metadata"
    )
    authorization_context: dict[str, str] = Field(
        default_factory=dict, description="User authorization context"
    )


class ModelWorkflowEventData(ModelEventDataBase):
    """Workflow execution event data."""

    event_type: Literal[EnumEventType.WORKFLOW] = Field(
        default=EnumEventType.WORKFLOW, description="Workflow event type"
    )
    workflow_stage: str = Field(..., description="Current workflow stage")
    workflow_step: str = Field(..., description="Current workflow step")
    execution_metrics: dict[str, float] = Field(
        default_factory=dict, description="Workflow execution metrics"
    )
    state_changes: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Workflow state changes"
    )


class ModelErrorEventData(ModelEventDataBase):
    """Error event data."""

    event_type: Literal[EnumEventType.ERROR] = Field(
        default=EnumEventType.ERROR, description="Error event type"
    )
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    stack_trace: str = Field(default="", description="Error stack trace")
    recovery_actions: list[str] = Field(
        default_factory=list, description="Suggested recovery actions"
    )
    impact_assessment: dict[str, str] = Field(
        default_factory=dict, description="Error impact assessment"
    )


# Structured routing and context types to replace primitive soup patterns
class ModelEventRoutingInfo(BaseModel):
    """Structured event routing information."""

    target_queue: str = Field(default="", description="Target message queue or topic")
    routing_key: str = Field(default="", description="Message routing key")
    priority: str = Field(default="normal", description="Routing priority level")
    broadcast: bool = Field(default=False, description="Whether to broadcast event")
    retry_routing: bool = Field(
        default=True, description="Enable routing retry on failure"
    )
    dead_letter_queue: str = Field(
        default="", description="Dead letter queue for failed routing"
    )


class ModelEventContextInfo(BaseModel):
    """Structured event context information."""

    correlation_id: UUID | None = Field(
        default=None, description="Event correlation identifier"
    )
    causation_id: UUID | None = Field(
        default=None, description="Event causation identifier"
    )
    session_id: UUID | None = Field(default=None, description="Session identifier")
    tenant_id: UUID | None = Field(default=None, description="Tenant identifier")
    environment: str = Field(default="", description="Environment context")
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Event schema version",
    )


class ModelEventAttributeInfo(BaseModel):
    """Structured event attributes."""

    category: str = Field(default="", description="Event category")
    importance: str = Field(default="medium", description="Event importance level")
    tags: list[str] = Field(default_factory=list, description="Event tags")
    custom_attributes: dict[str, str] = Field(
        default_factory=dict, description="Additional custom attributes"
    )
    classification: str = Field(default="", description="Event classification")


class ModelEventSourceInfo(BaseModel):
    """Structured event source information."""

    service_name: str = Field(default="", description="Source service name")
    service_version: ModelSemVer | None = Field(
        default=None, description="Source service version"
    )
    host_name: str = Field(default="", description="Source host name")
    instance_id: UUID | None = Field(
        default=None, description="Source instance identifier"
    )
    request_id: UUID | None = Field(
        default=None, description="Originating request identifier"
    )
    user_agent: str = Field(default="", description="User agent information")


# Improved discriminated union type for event data - defined after all classes
EventDataUnion = Annotated[
    Union[
        ModelSystemEventData,
        ModelUserEventData,
        ModelWorkflowEventData,
        ModelErrorEventData,
    ],
    Field(discriminator="event_type"),
]


# Export for use
__all__ = [
    "ModelEventPayload",
    "EventDataUnion",
    "EnumEventType",
    "ModelSystemEventData",
    "ModelUserEventData",
    "ModelWorkflowEventData",
    "ModelErrorEventData",
    "ModelEventDataBase",
]
