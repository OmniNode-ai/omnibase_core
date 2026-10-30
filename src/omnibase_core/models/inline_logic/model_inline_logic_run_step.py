# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A workflow ``run:`` step as the inline-logic check reads it (OMN-21534)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelInlineLogicRunStep"]


class ModelInlineLogicRunStep(BaseModel):
    """One ``run:`` step: where it sits, its effective shell and its script text."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    job: str
    step: str
    shell: str | None = None
    run: str
