from __future__ import annotations

import uuid

"""
TypedDict for workflow state.
"""


from datetime import datetime
from typing import Dict, TypedDict
from uuid import UUID


class TypedDictWorkflowState(TypedDict):
    """TypedDict for workflow state."""

    workflow_id: UUID
    current_step: str
    total_steps: int
    completed_steps: int
    status: str  # "pending", "running", "completed", "failed"
    created_at: datetime
    updated_at: datetime
