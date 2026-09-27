# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
FilterCondition model.
"""

from pydantic import BaseModel, ConfigDict, Field

from .model_filter_operator import ModelFilterOperator


class ModelFilterCondition(BaseModel):
    """Individual filter condition."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(default=..., description="Field to filter on")
    operator: ModelFilterOperator = Field(default=..., description="Filter operator")
    negate: bool = Field(default=False, description="Negate the condition")


# Compatibility alias
FilterCondition = ModelFilterCondition
