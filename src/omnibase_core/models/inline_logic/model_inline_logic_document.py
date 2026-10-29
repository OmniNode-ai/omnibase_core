# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The run steps and check values of a workflow or a ticket contract (OMN-21534)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.inline_logic.model_inline_logic_check_value import (
    ModelInlineLogicCheckValue,
)
from omnibase_core.models.inline_logic.model_inline_logic_run_step import (
    ModelInlineLogicRunStep,
)

__all__ = ["ModelInlineLogicDocument"]


def _refused(message: str) -> ModelOnexError:
    """A workflow or contract of the wrong shape is a load error, never a clean pass."""
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def _step_label(step: dict[str, object], index: int) -> str:
    """The step's name, else its id, else its position."""
    for key in ("name", "id"):
        label = step.get(key)
        if isinstance(label, str) and label:
            return label
    return str(index)


def _shell_of(holder: object) -> str | None:
    """The ``defaults.run.shell`` of a workflow or job mapping, when it names one."""
    if not isinstance(holder, dict):
        return None
    defaults = holder.get("defaults")
    run = defaults.get("run") if isinstance(defaults, dict) else None
    shell = run.get("shell") if isinstance(run, dict) else None
    return shell if isinstance(shell, str) else None


def _run_steps(data: dict[str, object]) -> list[dict[str, object]]:
    jobs = data["jobs"]
    if not isinstance(jobs, dict):
        raise _refused("jobs must be a mapping")
    steps: list[dict[str, object]] = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            raise _refused(f"job {job_name!r} must be a mapping")
        job_steps = job.get("steps", [])
        if not isinstance(job_steps, list):
            raise _refused(f"job {job_name!r}: steps must be a list")
        shell_default = _shell_of(job) or _shell_of(data)
        for index, step in enumerate(job_steps):
            if not isinstance(step, dict) or not isinstance(step.get("run"), str):
                continue
            shell = step.get("shell", shell_default)
            steps.append(
                {
                    "job": str(job_name),
                    "step": _step_label(step, index),
                    "shell": shell if isinstance(shell, str) else None,
                    "run": step["run"],
                }
            )
    return steps


def _check_values(data: dict[str, object]) -> list[dict[str, object]]:
    evidence = data["dod_evidence"]
    if not isinstance(evidence, list):
        raise _refused("dod_evidence must be a list")
    values: list[dict[str, object]] = []
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise _refused("each dod_evidence item must be a mapping")
        checks = item.get("checks", [])
        if not isinstance(checks, list):
            raise _refused("checks must be a list")
        for check in checks:
            if isinstance(check, dict) and isinstance(check.get("check_value"), str):
                values.append(
                    {
                        "evidence_ref": str(item.get("id", index)),
                        "check_type": check.get("check_type"),
                        "check_value": check["check_value"],
                    }
                )
    return values


class ModelInlineLogicDocument(BaseModel):
    """Every ``run:`` step of a workflow, or every ``check_value`` of a ticket contract.

    A workflow is a mapping with ``jobs``; a ticket contract is a mapping with
    ``dod_evidence``. Anything else is refused, so a file that is neither is never a
    clean pass.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    run_steps: tuple[ModelInlineLogicRunStep, ...] = ()
    check_values: tuple[ModelInlineLogicCheckValue, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data: object) -> object:
        """Read the workflow or contract mapping into its two fact lists."""
        if not isinstance(data, dict):
            raise _refused("expected a workflow or ticket contract mapping")
        if "jobs" in data:
            return {"run_steps": _run_steps(data)}
        if "dod_evidence" in data:
            return {"check_values": _check_values(data)}
        raise _refused("expected a workflow (jobs) or a ticket contract (dod_evidence)")
