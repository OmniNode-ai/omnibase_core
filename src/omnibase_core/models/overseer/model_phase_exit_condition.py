# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelPhaseExitCondition — typed exit condition for a session phase (OMN-11226)."""

from __future__ import annotations

from typing import Literal, Self

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
    def _validate_condition_payload(self) -> Self:
        if self.condition_type == "pr_state":
            self._validate_pr_state_payload()
        elif self.condition_type == "worker_count":
            self._validate_worker_count_payload()
        elif self.condition_type == "time_elapsed":
            self._validate_time_elapsed_payload()
        elif self.condition_type == "custom_probe":
            self._validate_custom_probe_payload()
        elif self.condition_type == "task_complete":
            self._validate_task_complete_payload()
        return self

    def _validate_pr_state_payload(self) -> None:
        if self.repo and self.pr_number is not None and self.required_state is not None:
            return
        msg = "pr_state requires repo, pr_number, and required_state"
        raise ValueError(msg)  # error-ok: Pydantic validator requires ValueError

    def _validate_worker_count_payload(self) -> None:
        if self.operator is not None and self.value is not None:
            return
        msg = "worker_count requires operator and value"
        raise ValueError(msg)  # error-ok: Pydantic validator requires ValueError

    def _validate_time_elapsed_payload(self) -> None:
        if self.value is not None:
            return
        msg = "time_elapsed requires value"
        raise ValueError(msg)  # error-ok: Pydantic validator requires ValueError

    def _validate_custom_probe_payload(self) -> None:
        if self.command and self.expected_exit_code is not None:
            return
        msg = "custom_probe requires command and expected_exit_code"
        raise ValueError(msg)  # error-ok: Pydantic validator requires ValueError

    def _validate_task_complete_payload(self) -> None:
        if self.task_name:
            return
        msg = "task_complete requires task_name"
        raise ValueError(msg)  # error-ok: Pydantic validator requires ValueError


__all__ = ["ModelPhaseExitCondition"]
