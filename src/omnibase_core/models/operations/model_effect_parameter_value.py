from __future__ import annotations

import uuid
from typing import Union

from pydantic import Field, ValidationInfo, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Strongly-typed effect parameter value model.

Represents discriminated union for effect parameter values.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_effect_parameter_type import EnumEffectParameterType
from omnibase_core.errors.error_codes import (
    EnumCoreErrorCode,
)


class ModelEffectParameterValue(BaseModel):
    """
    Discriminated union for effect parameter values.

    Replaces Union[TargetSystemParameter, OperationModeParameter, ...] with
    ONEX-compliant discriminated union pattern.
    """

    parameter_type: EnumEffectParameterType = Field(
        description="Effect parameter type discriminator",
    )
    name: str = Field(default=..., description="Parameter name")
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
            raise ModelOnexError(
                message=f"Field {field_name} is required for parameter type {parameter_type}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
            raise ModelOnexError(
                message=f"Field {field_name} is required for parameter type {parameter_type}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelEffectParameterValue"]
