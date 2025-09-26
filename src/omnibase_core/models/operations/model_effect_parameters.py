"""
Strongly-typed effect operation parameters model.

Replaces dict[str, Any] usage in effect parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any


class ModelEffectParameters(BaseModel):
    """
    Strongly-typed effect operation parameters.

    Replaces dict[str, Any] with structured effect parameter model.
    """

    target_systems: dict[str, str] = Field(
        default_factory=dict, description="Target system identifiers"
    )
    operation_modes: dict[str, str] = Field(
        default_factory=dict, description="Operation mode settings"
    )
    retry_settings: dict[str, int] = Field(
        default_factory=dict, description="Retry configuration values"
    )
    validation_rules: dict[str, bool] = Field(
        default_factory=dict, description="Validation rule flags"
    )
    external_references: dict[str, str] = Field(
        default_factory=dict, description="External system references"
    )


# Export for use
__all__ = ["ModelEffectParameters"]
