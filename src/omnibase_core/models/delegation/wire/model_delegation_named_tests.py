# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Named tests on the delegation wire (OMN-17427).

A code answer is graded on tests the request names. The deployed lane has no
caller workspace, so a request carries the test sources inline and the consumer
runs them in a sandbox against the answer.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.delegation.wire.model_delegation_named_test_file import (
    ModelDelegationNamedTestFile,
    inside_workspace,
)

MAX_NAMED_TESTS = 20
MAX_NAMED_TEST_FILES = 20


class ModelDelegationNamedTests(BaseModel):
    """The tests a delegation names, their sources, and the file the answer goes to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    test_ids: tuple[str, ...] = Field(
        ...,
        min_length=1,
        max_length=MAX_NAMED_TESTS,
        description="Workspace-relative pytest node ids, run one at a time.",
    )
    answer_path: str = Field(
        ...,
        min_length=1,
        description="Workspace-relative file the answer's code is written to.",
    )
    test_files: tuple[ModelDelegationNamedTestFile, ...] = Field(
        ...,
        min_length=1,
        max_length=MAX_NAMED_TEST_FILES,
        description="Test files the request carries, written into the sandbox.",
    )

    @model_validator(mode="after")
    def _validate_paths(self) -> Self:
        if not inside_workspace(self.answer_path):
            raise ValueError("answer_path must stay inside the workspace")
        if any(f.path == self.answer_path for f in self.test_files):
            raise ValueError("a test file cannot be written over answer_path")
        for test_id in self.test_ids:
            path = PurePosixPath(test_id.split("::", 1)[0])
            if not test_id.strip() or test_id.startswith("-"):
                raise ValueError(f"test id {test_id!r} is not a pytest node id")
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"test id {test_id!r} must stay inside the workspace")
        return self


__all__: list[str] = [
    "MAX_NAMED_TESTS",
    "MAX_NAMED_TEST_FILES",
    "ModelDelegationNamedTests",
]
