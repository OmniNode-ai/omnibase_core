# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDelegationHealth — health of the delegation classifier and per-task-type routing."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus


class ModelDelegationHealth(BaseModel):
    """Health of the delegation classifier and per-task-type routing."""

    model_config = ConfigDict(frozen=True)

    task_type_coverage: dict[str, EnumDogfoodStatus] = Field(
        default_factory=dict, description="Per-task-type classifier coverage status"
    )
    classifier_coverage_pct: float = Field(
        ...,
        description="Overall classifier coverage as a percentage (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )
    model_health: EnumDogfoodStatus = Field(
        ..., description="Health of the underlying inference model"
    )
    status: EnumDogfoodStatus = Field(
        ..., description="Overall delegation health status"
    )
