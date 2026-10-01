# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallCheckInput: everything the pure gate judges (OMN-20295)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_source_file import (
    ModelDirectModelCallSourceFile,
)

__all__ = ["ModelDirectModelCallCheckInput"]


class ModelDirectModelCallCheckInput(BaseModel):
    """The repository's files, the policy, the baseline and its base copy.

    Built by the EFFECT node (node_direct_model_call_check_effect), which
    owns every read; the COMPUTE node judges it without I/O.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    policy: ModelDirectModelCallPolicy = Field(description="The packaged policy")
    repo: str = Field(description="Repository name, the key into sanctioned_packages")
    files: tuple[ModelDirectModelCallSourceFile, ...] = Field(
        description="Every scanned file of the repository"
    )
    today: date = Field(description="The date expiries are judged against")
    baseline_path: str | None = Field(
        default=None, description="Repository-relative path of the committed baseline"
    )
    baseline: tuple[ModelDirectModelCallBaselineEntry, ...] = Field(
        default=(), description="The committed baseline's entries (empty when absent)"
    )
    base_ref: str | None = Field(
        default=None, description="Git ref this baseline may only shrink from"
    )
    base_baseline: tuple[ModelDirectModelCallBaselineEntry, ...] | None = Field(
        default=None,
        description="The baseline's entries at base_ref; None when absent there",
    )
    base_wires_gate: bool = Field(
        default=False, description="True when base_ref already wires this gate"
    )
