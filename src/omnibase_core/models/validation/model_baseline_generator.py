# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generator metadata model for violation baselines.

Tracks provenance of baseline files for debugging and auditing.

Related ticket: OMN-1774
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelBaselineGenerator(BaseModel):
    """Metadata about the tool that generated the baseline.

    Tracks provenance for debugging and auditing purposes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tool: str = Field(
        description="Name of the tool that generated this baseline",
    )

    version: str = Field(
        description="Version of the tool that generated this baseline",
    )


__all__ = ["ModelBaselineGenerator"]
