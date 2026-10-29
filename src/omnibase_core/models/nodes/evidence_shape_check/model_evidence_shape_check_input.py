# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""PR body text consumed by the pure evidence-shape validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelEvidenceShapeCheckInput(BaseModel):
    """PR body whose Evidence-Source block shape is checked."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pr_body: str
