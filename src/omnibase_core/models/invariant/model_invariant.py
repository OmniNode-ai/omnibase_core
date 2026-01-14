"""
Invariant model for user-defined validation rules.

Invariants are validation rules that ensure AI model changes are safe before
production deployment. Each invariant defines a specific condition that must
be satisfied for a model to be considered production-ready.

Thread Safety:
    ModelInvariant is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_invariant_type import EnumInvariantType

# Required config keys for each invariant type
# These match the field names from the corresponding config models:
# - ModelSchemaInvariantConfig: json_schema
# - ModelFieldPresenceConfig: fields
# - ModelFieldValueConfig: field_path (expected_value/pattern are optional alternatives)
# - ModelThresholdConfig: metric_name (min_value/max_value are optional)
# - ModelLatencyConfig: max_ms
# - ModelCostConfig: max_cost
# - ModelCustomInvariantConfig: callable_path
_REQUIRED_CONFIG_KEYS: dict[EnumInvariantType, set[str]] = {
    EnumInvariantType.SCHEMA: {"json_schema"},
    EnumInvariantType.FIELD_PRESENCE: {"fields"},
    EnumInvariantType.FIELD_VALUE: {"field_path"},
    EnumInvariantType.THRESHOLD: {"metric_name"},
    EnumInvariantType.LATENCY: {"max_ms"},
    EnumInvariantType.COST: {"max_cost"},
    EnumInvariantType.CUSTOM: {"callable_path"},
}


class ModelInvariant(BaseModel):
    """
    Base model representing a single invariant (validation rule).

    Invariants are user-defined validation rules that specify conditions
    AI models must satisfy before deployment. They can validate metrics,
    behaviors, or other properties of model outputs.

    Attributes:
        id: Unique identifier for the invariant (UUID per ONEX standards).
        name: Human-readable name describing the invariant.
        type: Type of invariant (metric threshold, behavior check, etc.).
        severity: Severity level determining action on violation.
        config: Type-specific configuration parameters.
        enabled: Whether the invariant is currently active.
        description: Optional detailed description of the invariant.

    Config Design Note:
        The `config` field uses `dict[str, object]` instead of a typed union
        (InvariantConfigUnion) for the following reasons:

        1. **YAML Parsing Flexibility**: Config is often loaded from YAML files
           where keys may vary based on user configuration. A generic dict
           allows arbitrary key-value pairs without strict schema enforcement
           at parse time.

        2. **Runtime Validation**: The @model_validator performs runtime
           validation to ensure required keys are present based on the
           invariant type. This gives flexibility while still ensuring
           correctness.

        3. **Extensibility**: New invariant types can be added without
           modifying the config type signature. The validation logic in
           _REQUIRED_CONFIG_KEYS handles type-specific requirements.

        For strictly typed scenarios where compile-time type safety is
        preferred, use the specific config models from
        `omnibase_core.models.invariant.model_invariant_config` directly.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the invariant",
    )
    name: str = Field(
        ...,
        description="Human-readable name describing the invariant",
        min_length=1,
    )
    type: EnumInvariantType = Field(
        ...,
        description="Type of invariant (metric threshold, behavior check, etc.)",
    )
    severity: EnumSeverity = Field(
        default=EnumSeverity.WARNING,
        description="Severity level determining action on violation",
    )
    config: dict[str, object] = Field(
        default_factory=dict,
        description="Type-specific configuration parameters",
    )
    enabled: bool = Field(
        default=True,
        description="Whether the invariant is currently active",
    )
    description: str | None = Field(
        default=None,
        description="Optional detailed description of the invariant",
    )

    @model_validator(mode="after")
    def validate_config_matches_type(self) -> Self:
        """
        Validate that the config dict contains required keys for the invariant type.

        Each invariant type requires specific configuration keys (matching
        the corresponding config model field names):
        - SCHEMA: requires 'json_schema' (ModelSchemaInvariantConfig)
        - FIELD_PRESENCE: requires 'fields' (ModelFieldPresenceConfig)
        - FIELD_VALUE: requires 'field_path' (ModelFieldValueConfig)
        - THRESHOLD: requires 'metric_name' (ModelThresholdConfig)
        - LATENCY: requires 'max_ms' (ModelLatencyConfig)
        - COST: requires 'max_cost' (ModelCostConfig)
        - CUSTOM: requires 'callable_path' (ModelCustomInvariantConfig)

        Raises:
            ValueError: If required config keys are missing for the invariant type.
        """
        required_keys = _REQUIRED_CONFIG_KEYS.get(self.type, set())

        if not required_keys:
            # Unknown type or no requirements - allow any config
            return self

        missing_keys = required_keys - set(self.config.keys())

        if missing_keys:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"Invariant type '{self.type.value}' requires config keys: "
                f"{sorted(required_keys)}. Missing: {sorted(missing_keys)}. "
                f"Provided config keys: {sorted(self.config.keys())}"
            )

        return self


__all__ = ["ModelInvariant"]
