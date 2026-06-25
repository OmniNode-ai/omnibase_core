# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Model-B rollup-coverage gap model (OMN-13574).

Represents a single gap between the airtight-rollup requirement declared under
``model_b_rollup_enforcement`` in validator-requirements.yaml and a repo's live
rollup workflow ``needs`` graph: a spec-required validator whose covering CI
job is absent, not transitively required by the rollup, or swallows failure
with ``continue-on-error: true``.

Related ticket: OMN-13574 (Model B pilot), epic OMN-13573.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelRollupCoverageGap"]


class ModelRollupCoverageGap(BaseModel):
    """A single Model-B rollup-coverage gap."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Target repo whose rollup graph is being verified")
    validator: str = Field(
        description=(
            "Validator logical name (key in validator-requirements.yaml), or "
            "'<rollup>' for a gap about the rollup job itself"
        )
    )
    detail: str = Field(description="Human-readable detail describing the coverage gap")
