# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Migration Validation Result Model."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelMigrationValidationResult(BaseModel):
    """Before/after validation result for a handler migration.

    Verifies that the migrated handler can be loaded via contract
    dispatch and produces equivalent outputs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_path: str = Field(..., description="Path to migrated handler")
    contract_dispatch_loads: bool = Field(
        ..., description="Whether handler loads successfully via contract routing"
    )
    test_inputs_count: int = Field(..., description="Number of test inputs run", ge=0)
    tests_passed: int = Field(
        ..., description="Number of tests that produced equivalent output", ge=0
    )
    tests_failed: int = Field(
        ..., description="Number of tests that produced different output", ge=0
    )
    failure_details: list[str] = Field(
        default_factory=list, description="Details of any failed equivalence tests"
    )
    passed: bool = Field(
        ..., description="Overall pass/fail: all tests passed and dispatch loads"
    )

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        """Enforce test count and passed-flag invariants."""
        if self.tests_passed + self.tests_failed != self.test_inputs_count:
            msg = (
                f"tests_passed ({self.tests_passed}) "
                f"+ tests_failed ({self.tests_failed}) "
                f"!= test_inputs_count ({self.test_inputs_count})"
            )
            raise ValueError(msg)
        if self.passed and (
            not self.contract_dispatch_loads
            or self.tests_failed != 0
            or self.tests_passed != self.test_inputs_count
        ):
            msg = (
                "passed=True requires contract_dispatch_loads=True, "
                "tests_failed=0, and all tests passed"
            )
            raise ValueError(msg)
        return self
