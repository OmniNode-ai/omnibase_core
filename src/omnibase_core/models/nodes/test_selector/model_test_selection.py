# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pydantic output contract for change-aware test selection.

Canonical home (OMN-14700) for the shapes previously defined in
``scripts/ci/test_selection_models.py``. Moved verbatim — same field names,
constraints, and validator — so the ``node_test_selector_compute`` handler and
the ``detect_test_paths.py`` oracle emit the identical model.
"""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from omnibase_core.enums.enum_full_suite_reason import EnumFullSuiteReason

__all__ = [
    "ModelTestSelection",
    "ModuleName",
    "TestPath",
]


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

    # An empty list is the "provably zero test impact" selection (a docs-only
    # diff, OMN-14910 / OMN-14753): distinct from "at least one path selected."
    # min_length=1 was removed so the selector can represent "run nothing" without
    # falling back to the full tests/unit/ tree.
    selected_paths: list[TestPath] = Field(...)
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
