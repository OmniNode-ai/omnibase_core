"""
Action Config Parameter Model - ONEX Standards Compliant.

Strongly-typed model for action configuration parameters.
Replaces dict[str, ModelActionConfigValue] with proper structure.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_action_config_value import ModelActionConfigValue


class ModelActionConfigParameter(BaseModel):
    """
    Strongly-typed action configuration parameter.

    Provides structured configuration with proper validation
    and type safety for FSM transition actions.
    """

    parameter_name: str = Field(
        ...,
        description="Name of the configuration parameter",
        min_length=1,
    )

    parameter_value: ModelActionConfigValue = Field(
        ...,
        description="Strongly-typed parameter value",
    )

    is_required: bool = Field(
        default=False,
        description="Whether this parameter is required for the action",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the parameter purpose",
    )

    validation_rule: str | None = Field(
        default=None,
        description="Optional validation rule for this parameter",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
