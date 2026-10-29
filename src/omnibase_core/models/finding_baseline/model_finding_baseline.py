# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The committed baseline document of one hook: ``.onex/baselines/<hook-id>.yaml``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.finding_baseline.model_finding_baseline_entry import (
    ModelFindingBaselineEntry,
)

__all__ = ["ModelFindingBaseline"]


class ModelFindingBaseline(BaseModel):
    """A shrink-only baseline: one file per hook, entries only ever leave.

    Document shape::

        schema_version: 1
        hook: check-no-dict-any
        entries:
          - path: src/pkg/module.py
            rule: dict-any
            text: "values: dict[str, Any] = {}"
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal[1] = 1
    hook: str = Field(min_length=1)
    entries: tuple[ModelFindingBaselineEntry, ...] = Field(default=())
