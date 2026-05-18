# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelPhaseExitCondition — typed exit condition for a session phase (OMN-11226)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class ModelPhaseExitCondition(BaseModel):
    """A single typed exit condition for a ModelSessionPhaseSpec."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    condition_type: Literal[
        "pr_state", "worker_count", "custom_probe", "task_complete", "time_elapsed"
    ]

    # pr_state
    repo: str | None = None
    pr_number: int | None = None
    required_state: Literal["merged", "closed", "open"] | None = None

    # worker_count / time_elapsed
    operator: Literal["eq", "lt", "gt", "le", "ge"] | None = None
    value: int | None = None

    # custom_probe
    command: str | None = None
    expected_exit_code: int | None = None

    # task_complete
    task_name: str | None = None

    @model_validator(mode="after")
    def _validate_condition_payload(self) -> ModelPhaseExitCondition:
        if self.condition_type == "pr_state":
            if not self.repo or self.pr_number is None or self.required_state is None:
                msg = "pr_state requires repo, pr_number, and required_state"
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
        elif self.condition_type == "worker_count":
            if self.operator is None or self.value is None:
                msg = "worker_count requires operator and value"
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
        elif self.condition_type == "time_elapsed":
            if self.value is None:
                msg = "time_elapsed requires value"
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
        elif self.condition_type == "custom_probe":
            if not self.command or self.expected_exit_code is None:
                msg = "custom_probe requires command and expected_exit_code"
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
        elif self.condition_type == "task_complete":
            if not self.task_name:
                msg = "task_complete requires task_name"
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
        return self


__all__ = ["ModelPhaseExitCondition"]
