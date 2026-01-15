"""
Dynamic Event Type Model.

enables plugin extensibility and contract-driven event type registration.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_json_schema import ModelJsonSchema
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventType(BaseModel):
    """
    Dynamic event type model enabling plugin extensibility.

    to register their own event types dynamically.
    """

    event_name: str = Field(
        default=...,
        description="Event type identifier",
        pattern="^[A-Z][A-Z0-9_]*$",
    )
    namespace: str = Field(
        default="onex",
        description="Event namespace to avoid conflicts",
    )
    description: str = Field(default=..., description="Human-readable description")
    schema_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Event schema version",
    )
    payload_schema: ModelJsonSchema | None = Field(
        default=None,
        description="Expected payload schema",
    )
    deprecated: bool = Field(
        default=False,
        description="Whether event type is deprecated",
    )
    category: str | None = Field(
        default=None, description="Event category for grouping"
    )
    severity: str | None = Field(
        default=None,
        description="Event severity level",
        pattern="^(info|warning|error|critical)$",
    )

    @classmethod
    def from_contract_data(
        cls,
        event_name: str,
        namespace: str = "onex",
        description: str | None = None,
        **kwargs: object,
    ) -> "ModelEventType":
        """
        ONEX-compatible factory method using Pydantic model_validate.

        Replaces from_contract_event() with proper validation.
        """
        validated_data = {
            "event_name": event_name,
            "namespace": namespace,
            "description": description or f"{event_name} event",
            **kwargs,
        }
        return cls.model_validate(validated_data)

    @property
    def qualified_name(self) -> str:
        """Fully qualified event name."""
        return f"{self.namespace}:{self.event_name}"

    def matches(self, event_name: str) -> bool:
        """Check if this event type matches the given event name."""
        return self.event_name == event_name

    def is_compatible_with(self, other: "ModelEventType") -> bool:
        """Check if this event type is compatible with another."""
        return (
            self.event_name == other.event_name
            and self.namespace == other.namespace
            and self.schema_version.major == other.schema_version.major
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.event_name

    def __eq__(self, other: object) -> bool:
        """Enable comparison with strings for current standards."""
        if isinstance(other, str):
            return self.event_name == other
        return super().__eq__(other)


# Compatibility utilities
def get_event_type_value(event_type: str | ModelEventType) -> str:
    """Get string value from event type for current standards."""
    if isinstance(event_type, str):
        return event_type
    return event_type.event_name


def create_event_type_from_registry(
    event_name: str,
    namespace: str = "onex",
    description: str | None = None,
) -> ModelEventType:
    """
    ONEX-compatible event type creation with registry lookup.

    Replaces create_event_type_from_string() with proper validation.
    Uses Pydantic validation throughout.

    If event type is not registered, creates a new one with default schema_version 1.0.0.
    """
    from .model_event_type_registry import get_event_type_registry

    registry = get_event_type_registry()
    existing = registry.get_event_type(event_name)
    if existing:
        return existing

    # Create event type using ONEX-compatible validation
    # schema_version is required - use default 1.0.0 for unregistered event types
    validated_data = {
        "event_name": event_name,
        "namespace": namespace,
        "description": description or f"Registry event type: {event_name}",
        "schema_version": ModelSemVer(major=1, minor=0, patch=0),
    }
    return ModelEventType.model_validate(validated_data)


def is_event_equal(
    event_type: str | ModelEventType,
    other: str | ModelEventType,
) -> bool:
    """Compare event types for equality (supports mixed types)."""
    event_name1 = get_event_type_value(event_type)
    event_name2 = get_event_type_value(other)
    return event_name1 == event_name2
