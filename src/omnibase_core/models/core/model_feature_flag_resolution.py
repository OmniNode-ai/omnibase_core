# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Feature flag resolution model (OMN-7776).

The typed result of resolving a registered flag against an environment mapping.
Carries the declared metadata plus the resolved state and its provenance so the
dashboard can render both the value and where it came from.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory
from omnibase_core.enums.enum_feature_flag_gate_type import EnumFeatureFlagGateType


class ModelFeatureFlagResolution(BaseModel):
    """Resolved state of a single feature flag.

    ``source`` is ``"default"`` when the declared default applied and
    ``"env"`` when an environment override was used.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Flag identifier.")
    enabled: bool = Field(..., description="Resolved on/off state.")
    raw_value: str | None = Field(
        default=None,
        description="Raw env-var value that produced the resolution, if any.",
    )
    source: str = Field(
        ...,
        pattern=r"^(default|env)$",
        description="Provenance of the resolved value: 'default' or 'env'.",
    )
    description: str = Field(..., description="Flag description from the registry.")
    default: bool = Field(..., description="Declared default state.")
    owning_repo: str = Field(..., description="Repo that owns the flag.")
    gate_type: EnumFeatureFlagGateType = Field(
        ..., description="Migration or permanent."
    )
    category: EnumFeatureFlagCategory = Field(..., description="Functional grouping.")
