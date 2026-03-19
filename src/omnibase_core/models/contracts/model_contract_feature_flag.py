# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-declared feature flag model.

Defines the schema for feature flags declared in contract YAML ``feature_flags:``
blocks. Each flag carries identity, default state, optional env-var binding,
category, and ownership metadata.

Flags declared here flow through introspection -> registration projections ->
registry API -> omnidash toggle dashboard.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory


class ModelContractFeatureFlag(BaseModel):
    """A single feature flag declared in a contract YAML.

    Frozen and strict (extra="forbid") to enforce contract-time correctness.
    Runtime resolution and env overrides happen in the infra layer, not here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Snake-case flag identifier. Must be globally unique across contracts.",
    )

    description: str = Field(
        default="",
        description="Human-readable description of what the flag controls.",
    )

    default_value: bool = Field(
        default=False,
        description="Contract author's intended default. Overridden by env/Infisical at runtime.",
    )

    env_var: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Uppercase env var name for runtime resolution. "
        "Maps contract flag to environment variable during env-based override.",
    )

    category: EnumFeatureFlagCategory = Field(
        default=EnumFeatureFlagCategory.GENERAL,
        description="Functional domain grouping for dashboard display.",
    )

    owner: str | None = Field(
        default=None,
        description="Free-text owner identifier (team or service name). "
        "Migration-grade metadata — normalization deferred to Phase B.",
    )
