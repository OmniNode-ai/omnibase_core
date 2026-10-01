# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalCriterionRequirement."""

from __future__ import annotations

from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.models.validation.model_goal_protected_baseline_file import (
    ModelGoalProtectedBaselineFile,
)
from omnibase_core.models.validation.model_goal_required_check_binding import (
    ModelGoalRequiredCheckBinding,
)


class ModelGoalCriterionRequirement(BaseModel):
    """Protected criterion, its required checks, and immutable test inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_id: str = Field(..., min_length=1, max_length=128)
    criterion_definition: str = Field(..., min_length=1, max_length=4000)
    required_checks: tuple[ModelGoalRequiredCheckBinding, ...] = Field(
        ..., min_length=1
    )
    required_test_selectors: tuple[str, ...] = Field(..., min_length=1)
    negative_control_selectors: tuple[str, ...] = Field(..., min_length=1)
    test_and_fixture_files: tuple[ModelGoalProtectedBaselineFile, ...] = Field(
        ..., min_length=1
    )

    @field_validator("criterion_id")
    @classmethod
    def _criterion_id_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("criterion_id must not be blank")
        return value

    @field_validator("criterion_definition")
    @classmethod
    def _criterion_definition_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("criterion_definition must not be blank")
        return value

    @model_validator(mode="after")
    def _bindings_are_unique(self) -> Self:
        check_keys = [
            (binding.item_id, binding.check_type) for binding in self.required_checks
        ]
        file_paths = [file.path for file in self.test_and_fixture_files]
        required_selectors = self.required_test_selectors
        negative_selectors = self.negative_control_selectors
        fixture_paths = {path.as_posix() for path in file_paths}
        if len(set(check_keys)) != len(check_keys):
            raise ValueError("criterion required checks must be unique")
        if len(set(file_paths)) != len(file_paths):
            raise ValueError("criterion test and fixture paths must be unique")
        if len(set(required_selectors)) != len(required_selectors) or any(
            not selector.strip() for selector in required_selectors
        ):
            raise ValueError("required test selectors must be unique and nonblank")
        if len(set(negative_selectors)) != len(negative_selectors) or any(
            not selector.strip() for selector in negative_selectors
        ):
            raise ValueError("negative control selectors must be unique and nonblank")
        if not set(negative_selectors).issubset(set(required_selectors)):
            raise ValueError("negative controls must be included in required selectors")
        for selector in required_selectors:
            selector_path = selector.split("::", maxsplit=1)[0]
            if selector_path not in fixture_paths:
                raise ValueError(
                    "each test selector must name a protected baseline file"
                )
        return self
