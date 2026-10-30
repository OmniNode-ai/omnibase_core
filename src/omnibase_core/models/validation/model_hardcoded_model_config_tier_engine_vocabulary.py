# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tier and engine vocabulary of the hardcoded model-configuration guard (OMN-21463)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelHardcodedModelConfigTierEngineVocabulary(BaseModel):
    """The names families T and N judge. Data of ``policy.yaml``; the operator's
    private vocabulary may extend each list. The detector spells none of them."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tier_aliases: tuple[str, ...] = Field(
        default=(), description="Model tier aliases, as whole values (T)"
    )
    tier_keys: tuple[str, ...] = Field(
        default=(),
        description="Policy-shaped keys whose tier-alias value is a finding (T)",
    )
    engine_names: tuple[str, ...] = Field(
        default=(), description="Engine names of the engine ladder (N)"
    )
    unbaselinable_files: tuple[str, ...] = Field(
        default=(),
        description=(
            "Files the plan names as audited findings (D.3): fixed, never "
            "admitted to a baseline (OMN-21537)"
        ),
    )
    python_suffixes: tuple[str, ...] = Field(
        default=(), description="File suffixes judged on their syntax tree"
    )
    slash_comment_suffixes: tuple[str, ...] = Field(
        default=(), description="File suffixes whose comments start with a double slash"
    )
    no_comment_suffixes: tuple[str, ...] = Field(
        default=(), description="File suffixes that have no comments"
    )
    scanned_suffixes: tuple[str, ...] = Field(
        default=(), description="File suffixes the gate scans"
    )
    scanned_names: tuple[str, ...] = Field(
        default=(), description="Extensionless file names the gate scans"
    )
