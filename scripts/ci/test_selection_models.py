# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pydantic output contract for change-aware test selection."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class EnumFullSuiteReason(StrEnum):
    SHARED_MODULE = "shared_module"
    THRESHOLD_MODULES = "threshold_modules"
    TEST_INFRASTRUCTURE = "test_infrastructure"
    MAIN_BRANCH = "main_branch"
    MERGE_GROUP = "merge_group"
    SCHEDULED = "scheduled"
    FEATURE_FLAG_OFF = "feature_flag_off"


TestPath = Annotated[
    str,
    StringConstraints(pattern=r"^tests(/[A-Za-z0-9_./-]+)?/$|^tests/$"),
]
ModuleName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", min_length=1),
]


class ModelTestSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_paths: list[TestPath] = Field(..., min_length=1)
    split_count: int = Field(..., ge=1, le=40)
    is_full_suite: bool
    full_suite_reason: EnumFullSuiteReason | None = Field(default=None)
    matrix: list[int] = Field(...)

    @model_validator(mode="after")
    def validate_full_suite_reason(self) -> Self:
        if self.is_full_suite and self.full_suite_reason is None:
            raise ValueError("full_suite_reason required when is_full_suite=True")
        if not self.is_full_suite and self.full_suite_reason is not None:
            raise ValueError("full_suite_reason forbidden when is_full_suite=False")
        if len(self.matrix) != self.split_count:
            raise ValueError(
                f"matrix length {len(self.matrix)} must equal split_count {self.split_count}"
            )
        return self
