# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed goal admission model: ModelGoalCriterionBaseline."""

from __future__ import annotations

import hashlib
import json
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from omnibase_core.models.validation.model_goal_criterion_requirement import (
    ModelGoalCriterionRequirement,
)


class ModelGoalCriterionBaseline(BaseModel):
    """Protected criterion set and the tests/fixtures authorized to bind it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    requirements: tuple[ModelGoalCriterionRequirement, ...] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _criterion_ids_are_unique(self) -> Self:
        criterion_ids = [requirement.criterion_id for requirement in self.requirements]
        if len(set(criterion_ids)) != len(criterion_ids):
            raise ValueError("protected criterion ids must be unique")
        return self

    def content_sha256(self) -> str:
        """Digest the exact protected criterion/check/test baseline."""
        payload = {
            "requirements": [
                {
                    "criterion_id": requirement.criterion_id,
                    "criterion_definition": requirement.criterion_definition,
                    "required_checks": [
                        check.model_dump(mode="json")
                        for check in sorted(
                            requirement.required_checks,
                            key=lambda check: (
                                check.item_id,
                                check.check_type.value,
                                check.check_value_sha256,
                            ),
                        )
                    ],
                    "required_test_selectors": sorted(
                        requirement.required_test_selectors
                    ),
                    "negative_control_selectors": sorted(
                        requirement.negative_control_selectors
                    ),
                    "test_and_fixture_files": [
                        file.model_dump(mode="json")
                        for file in sorted(
                            requirement.test_and_fixture_files,
                            key=lambda file: file.path.as_posix(),
                        )
                    ],
                }
                for requirement in sorted(
                    self.requirements, key=lambda requirement: requirement.criterion_id
                )
            ]
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
