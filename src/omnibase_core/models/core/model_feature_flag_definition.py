# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Feature flag definition model (OMN-7776).

Static, contract-time declaration of a single known feature flag. Frozen and
strict so the registry catalog cannot drift at runtime.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory
from omnibase_core.enums.enum_feature_flag_gate_type import EnumFeatureFlagGateType


class ModelFeatureFlagDefinition(BaseModel):
    """A single feature flag declared in the registry.

    The registry is the single source of truth: this declares the flag's
    identity, default state, owning repo, gate type, and category. Runtime
    resolution (env override) happens in :class:`FeatureFlagRegistry`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Uppercase env-var-style flag identifier, globally unique.",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of what the flag controls.",
    )

    default: bool = Field(
        ...,
        description="Default state when the flag is not overridden by env.",
    )

    owning_repo: str = Field(
        ...,
        min_length=1,
        description="Repository that owns the behavior the flag gates "
        "(e.g. 'omniclaude', 'omnidash', 'omnibase_infra').",
    )

    gate_type: EnumFeatureFlagGateType = Field(
        ...,
        description="Whether the flag gates a rollout cut-over or is permanent.",
    )

    category: EnumFeatureFlagCategory = Field(
        default=EnumFeatureFlagCategory.GENERAL,
        description="Functional domain grouping for dashboard display.",
    )
