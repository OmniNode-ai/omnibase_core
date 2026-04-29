# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval suite model for a versioned collection of eval tasks."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.governance.model_eval_task import ModelEvalTask

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 500


class ModelEvalSuite(BaseModel):
    """A versioned collection of eval tasks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-id-ok: user-facing suite identifier (e.g., eval-suite-alpha)
    suite_id: str = Field(..., description="Unique suite identifier", max_length=200)
    name: str = Field(..., description="Human-readable suite name", max_length=500)
    description: str = Field(
        default="", description="Suite description", max_length=_MAX_STRING_LENGTH
    )
    tasks: list[ModelEvalTask] = Field(
        ..., description="Tasks in this suite", max_length=_MAX_LIST_ITEMS
    )
    created_at: datetime = Field(..., description="When the suite was created")
    # string-version-ok: semver stored as str for YAML wire serialization
    version: str = Field(..., description="Suite version (semver)", max_length=50)
