"""
TypedDict for workflow state.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID


class TypedDictWorkflowState(TypedDict):
    workflow_id: UUID
    current_step: str
    total_steps: int
    completed_steps: int
    status: str  # See EnumWorkflowStatus for valid values
    created_at: datetime
    updated_at: datetime


__all__ = ["TypedDictWorkflowState"]
