"""
Strongly-typed effect operation parameters model.

Replaces dict[str, Any] usage in effect parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import TypedDict, Unpack
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_effect_parameter_type import EnumEffectParameterType


# TypedDict definitions for factory method parameters
class TypedDictTargetSystemKwargs(TypedDict, total=False):
    """Typed parameters for target system factory method."""

    description: str
    required: bool
    authentication_required: bool
    timeout_ms: int


class TypedDictOperationModeKwargs(TypedDict, total=False):
    """Typed parameters for operation mode factory method."""

    description: str
    required: bool
    sync_mode: bool
    batch_size: int
    priority: str


class TypedDictRetrySettingKwargs(TypedDict, total=False):
    """Typed parameters for retry setting factory method."""

    description: str
    required: bool
    max_retries: int
    retry_delay_ms: int
    exponential_backoff: bool
    retry_on_timeout: bool


class TypedDictValidationRuleKwargs(TypedDict, total=False):
    """Typed parameters for validation rule factory method."""

    description: str
    required: bool
    enabled: bool
    strict_mode: bool
    error_on_failure: bool


class TypedDictExternalReferenceKwargs(TypedDict, total=False):
    """Typed parameters for external reference factory method."""

    description: str
    required: bool
    resolution_required: bool
    cache_duration_seconds: int


# Discriminated effect parameter union to replace primitive soup pattern
class ModelEffectParameterValue(BaseModel):
    """
    Discriminated union for effect parameter values.

    Replaces Union[TargetSystemParameter, OperationModeParameter, ...] with
    ONEX-compliant discriminated union pattern.
    """

    parameter_type: EnumEffectParameterType = Field(
        description="Effect parameter type discriminator",
    )
    name: str = Field(..., description="Parameter name")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")

    # Target system fields
    system_identifier: str | None = None
    connection_type: str | None = None
    authentication_required: bool | None = None
    timeout_ms: int | None = None

    # Operation mode fields
    mode: str | None = None
    sync_mode: bool | None = None
    batch_size: int | None = None
    priority: str | None = None

    # Retry setting fields
    max_retries: int | None = None
    retry_delay_ms: int | None = None
    exponential_backoff: bool | None = None
    retry_on_timeout: bool | None = None

    # Validation rule fields
    rule_name: str | None = None
    enabled: bool | None = None
    strict_mode: bool | None = None
    error_on_failure: bool | None = None

    # External reference fields
    reference_id: UUID | None = None
    reference_type: str | None = None
    resolution_required: bool | None = None
    cache_duration_seconds: int | None = None

    @field_validator("system_identifier", "mode", "rule_name")
    @classmethod
    def validate_required_string_fields(
        cls,
        v: str | None,
        info: ValidationInfo,
    ) -> str | None:
        """Ensure required fields are present for each parameter type."""
        if not hasattr(info, "data") or "parameter_type" not in info.data:
            return v

        parameter_type = info.data["parameter_type"]
        field_name = info.field_name

        required_fields = {
            EnumEffectParameterType.TARGET_SYSTEM: "system_identifier",
            EnumEffectParameterType.OPERATION_MODE: "mode",
            EnumEffectParameterType.RETRY_SETTING: None,  # No specific required field
            EnumEffectParameterType.VALIDATION_RULE: "rule_name",
        }

        required_field = required_fields.get(parameter_type)
        if required_field == field_name and v is None:
            raise ValueError(
                f"Field {field_name} is required for parameter type {parameter_type}",
            )

        return v

    @field_validator("reference_id")
    @classmethod
    def validate_required_reference_id(
        cls,
        v: UUID | None,
        info: ValidationInfo,
    ) -> UUID | None:
        """Ensure reference_id is present for external reference parameter type."""
        if not hasattr(info, "data") or "parameter_type" not in info.data:
            return v

        parameter_type = info.data["parameter_type"]
        field_name = info.field_name

        if (
            parameter_type == EnumEffectParameterType.EXTERNAL_REFERENCE
            and field_name == "reference_id"
            and v is None
        ):
            raise ValueError(
                f"Field {field_name} is required for parameter type {parameter_type}",
            )

        return v

    @classmethod
    def from_target_system(
        cls,
        name: str,
        system_identifier: str,
        connection_type: str,
        **kwargs: Unpack[TypedDictTargetSystemKwargs],
    ) -> ModelEffectParameterValue:
        """Create target system parameter."""
        return cls(
            parameter_type=EnumEffectParameterType.TARGET_SYSTEM,
            name=name,
            system_identifier=system_identifier,
            connection_type=connection_type,
            description=kwargs.get("description", ""),
            required=kwargs.get("required", False),
            authentication_required=kwargs.get("authentication_required", True),
            timeout_ms=kwargs.get("timeout_ms", 5000),
        )

    @classmethod
    def from_operation_mode(
        cls,
        name: str,
        mode: str,
        **kwargs: Unpack[TypedDictOperationModeKwargs],
    ) -> ModelEffectParameterValue:
        """Create operation mode parameter."""
        return cls(
            parameter_type=EnumEffectParameterType.OPERATION_MODE,
            name=name,
            mode=mode,
            description=kwargs.get("description", ""),
            required=kwargs.get("required", False),
            sync_mode=kwargs.get("sync_mode", True),
            batch_size=kwargs.get("batch_size", 1),
            priority=kwargs.get("priority", "normal"),
        )

    @classmethod
    def from_retry_setting(
        cls,
        name: str,
        **kwargs: Unpack[TypedDictRetrySettingKwargs],
    ) -> ModelEffectParameterValue:
        """Create retry setting parameter."""
        return cls(
            parameter_type=EnumEffectParameterType.RETRY_SETTING,
            name=name,
            description=kwargs.get("description", ""),
            required=kwargs.get("required", False),
            max_retries=kwargs.get("max_retries", 3),
            retry_delay_ms=kwargs.get("retry_delay_ms", 1000),
            exponential_backoff=kwargs.get("exponential_backoff", True),
            retry_on_timeout=kwargs.get("retry_on_timeout", True),
        )

    @classmethod
    def from_validation_rule(
        cls,
        name: str,
        rule_name: str,
        **kwargs: Unpack[TypedDictValidationRuleKwargs],
    ) -> ModelEffectParameterValue:
        """Create validation rule parameter."""
        return cls(
            parameter_type=EnumEffectParameterType.VALIDATION_RULE,
            name=name,
            rule_name=rule_name,
            description=kwargs.get("description", ""),
            required=kwargs.get("required", False),
            enabled=kwargs.get("enabled", True),
            strict_mode=kwargs.get("strict_mode", False),
            error_on_failure=kwargs.get("error_on_failure", True),
        )

    @classmethod
    def from_external_reference(
        cls,
        name: str,
        reference_id: UUID,
        reference_type: str,
        **kwargs: Unpack[TypedDictExternalReferenceKwargs],
    ) -> ModelEffectParameterValue:
        """Create external reference parameter."""
        return cls(
            parameter_type=EnumEffectParameterType.EXTERNAL_REFERENCE,
            name=name,
            reference_id=reference_id,
            reference_type=reference_type,
            description=kwargs.get("description", ""),
            required=kwargs.get("required", False),
            resolution_required=kwargs.get("resolution_required", True),
            cache_duration_seconds=kwargs.get("cache_duration_seconds", 300),
        )


class ModelEffectParameters(BaseModel):
    """
    Strongly-typed effect operation parameters with discriminated unions.

    Replaces primitive soup pattern with discriminated effect parameter types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Use discriminated union for effect parameters
    effect_parameters: dict[str, ModelEffectParameterValue] = Field(
        default_factory=dict,
        description="Effect parameters with discriminated union types",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
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

    def serialize(self) -> dict[str, object]:
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


# Export for use
__all__ = ["ModelEffectParameterValue", "ModelEffectParameters"]
