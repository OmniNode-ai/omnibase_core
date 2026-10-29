# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Rule data of the bare-feature-flag check, read from its ``.validation.yaml`` rule rows."""

from pydantic import BaseModel, ConfigDict, Field


class ModelBareFeatureFlagRules(BaseModel):
    """Patterns, approved names and segments and message templates; never code."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    python_pattern: str = Field(min_length=1)
    ts_pattern: str = Field(min_length=1)
    comment_prefixes: tuple[str, ...] = Field(min_length=1)
    approved_basenames: tuple[str, ...] = Field(default=())
    approved_path_segments: tuple[str, ...] = Field(default=())
    violation_template: str = Field(min_length=1)
    exempt_with_reason_pattern: str = Field(min_length=1)
    exempt_bare_pattern: str = Field(min_length=1)
    bare_exemption_template: str = Field(min_length=1)
    exemption_template: str = Field(min_length=1)
