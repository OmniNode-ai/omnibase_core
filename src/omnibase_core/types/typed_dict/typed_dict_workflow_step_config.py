"""TypedDict for workflow step configuration from YAML."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictWorkflowStepConfig(TypedDict):
    """TypedDict for workflow step configuration from YAML."""

    step_name: str
    step_type: str
    timeout_ms: NotRequired[int]
    depends_on: NotRequired[list[str]]


__all__ = ["TypedDictWorkflowStepConfig"]
