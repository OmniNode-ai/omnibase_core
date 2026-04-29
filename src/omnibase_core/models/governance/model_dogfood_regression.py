# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDogfoodRegression — a single detected regression between two scorecard runs."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumRegressionSeverity

_MAX_STRING_LENGTH = 10000


class ModelDogfoodRegression(BaseModel):
    """A single detected regression between two scorecard runs."""

    model_config = ConfigDict(frozen=True)

    dimension: str = Field(
        ...,
        description="Which scorecard dimension the regression occurred in",
        max_length=_MAX_STRING_LENGTH,
    )
    field_path: str = Field(
        ...,
        description="Dotted path to the regressed field",
        max_length=_MAX_STRING_LENGTH,
    )
    severity: EnumRegressionSeverity = Field(..., description="CRITICAL, WARN, or NONE")
    previous_value: str = Field(
        ...,
        description="String representation of the previous value",
        max_length=_MAX_STRING_LENGTH,
    )
    current_value: str = Field(
        ...,
        description="String representation of the current value",
        max_length=_MAX_STRING_LENGTH,
    )
    description: str = Field(
        ...,
        description="Human-readable explanation of the regression",
        max_length=_MAX_STRING_LENGTH,
    )
