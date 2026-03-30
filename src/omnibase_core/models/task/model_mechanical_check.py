# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A single mechanical DoD check that can be executed independently."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_check_type import EnumCheckType


class ModelMechanicalCheck(BaseModel):
    """A single mechanical DoD check that can be executed independently."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    criterion: str = Field(
        ..., description="Human-readable description of what is checked"
    )
    check: str = Field(..., description="Shell command or probe to execute")
    check_type: EnumCheckType = Field(
        default=EnumCheckType.COMMAND_EXIT_0,
        description="Type of mechanical check (enum-constrained)",
    )
