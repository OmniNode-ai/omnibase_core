# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for TypedDictWorkflowState.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.types.typed_dict_workflow_state import TypedDictWorkflowState


@pytest.mark.unit
class TestTypedDictWorkflowState:
    """Test TypedDictWorkflowState functionality."""

    def test_typed_dict_workflow_state_creation(self):
        """Test creating TypedDictWorkflowState with all required fields."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "step_1",
            "total_steps": 5,
            "completed_steps": 2,
            "status": "running",
            "created_at": now,
            "updated_at": now,
        }

        assert workflow_state["workflow_id"] == workflow_id
        assert workflow_state["current_step"] == "step_1"
        assert workflow_state["total_steps"] == 5
        assert workflow_state["completed_steps"] == 2
        assert workflow_state["status"] == "running"
        assert workflow_state["created_at"] == now
        assert workflow_state["updated_at"] == now

    def test_typed_dict_workflow_state_different_statuses(self):
        """Test TypedDictWorkflowState with different status values."""
        statuses = ["pending", "running", "completed", "failed"]
        workflow_id = uuid4()
        now = datetime.now()

        for status in statuses:
            workflow_state: TypedDictWorkflowState = {
                "workflow_id": workflow_id,
                "current_step": f"step_for_{status}",
                "total_steps": 3,
                "completed_steps": (
                    1 if status == "pending" else 3 if status == "completed" else 2
                ),
                "status": status,
                "created_at": now,
                "updated_at": now,
            }

            assert workflow_state["status"] == status
            assert isinstance(workflow_state["workflow_id"], UUID)

    def test_typed_dict_workflow_state_field_types(self):
        """Test that all fields have correct types."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "validation_step",
            "total_steps": 10,
            "completed_steps": 7,
            "status": "running",
            "created_at": now,
            "updated_at": now,
        }

        assert isinstance(workflow_state["workflow_id"], UUID)
        assert isinstance(workflow_state["current_step"], str)
        assert isinstance(workflow_state["total_steps"], int)
        assert isinstance(workflow_state["completed_steps"], int)
        assert isinstance(workflow_state["status"], str)
        assert isinstance(workflow_state["created_at"], datetime)
        assert isinstance(workflow_state["updated_at"], datetime)

    def test_typed_dict_workflow_state_progress_calculation(self):
        """Test workflow state progress calculation."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "step_3",
            "total_steps": 5,
            "completed_steps": 2,
            "status": "running",
            "created_at": now,
            "updated_at": now,
        }

        progress_percentage = (
            workflow_state["completed_steps"] / workflow_state["total_steps"]
        ) * 100
        assert progress_percentage == 40.0

    def test_typed_dict_workflow_state_completed_workflow(self):
        """Test TypedDictWorkflowState for completed workflow."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "final_step",
            "total_steps": 4,
            "completed_steps": 4,
            "status": "completed",
            "created_at": now,
            "updated_at": now,
        }

        assert workflow_state["completed_steps"] == workflow_state["total_steps"]
        assert workflow_state["status"] == "completed"

    def test_typed_dict_workflow_state_failed_workflow(self):
        """Test TypedDictWorkflowState for failed workflow."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "error_step",
            "total_steps": 6,
            "completed_steps": 3,
            "status": "failed",
            "created_at": now,
            "updated_at": now,
        }

        assert workflow_state["status"] == "failed"
        assert workflow_state["completed_steps"] < workflow_state["total_steps"]

    def test_typed_dict_workflow_state_pending_workflow(self):
        """Test TypedDictWorkflowState for pending workflow."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "initial_step",
            "total_steps": 3,
            "completed_steps": 0,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }

        assert workflow_state["status"] == "pending"
        assert workflow_state["completed_steps"] == 0

    def test_typed_dict_workflow_state_different_timestamps(self):
        """Test TypedDictWorkflowState with different created_at and updated_at."""
        workflow_id = uuid4()
        created_at = datetime(2024, 1, 1, 10, 0, 0)
        updated_at = datetime(2024, 1, 1, 11, 30, 0)

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "step_2",
            "total_steps": 3,
            "completed_steps": 1,
            "status": "running",
            "created_at": created_at,
            "updated_at": updated_at,
        }

        assert workflow_state["created_at"] == created_at
        assert workflow_state["updated_at"] == updated_at
        assert workflow_state["created_at"] < workflow_state["updated_at"]

    def test_typed_dict_workflow_state_step_names(self):
        """Test TypedDictWorkflowState with different step names."""
        workflow_id = uuid4()
        now = datetime.now()

        step_names = [
            "initialization",
            "data_validation",
            "processing",
            "finalization",
            "cleanup",
        ]

        for i, step_name in enumerate(step_names):
            workflow_state: TypedDictWorkflowState = {
                "workflow_id": workflow_id,
                "current_step": step_name,
                "total_steps": len(step_names),
                "completed_steps": i,
                "status": "running",
                "created_at": now,
                "updated_at": now,
            }

            assert workflow_state["current_step"] == step_name

    def test_typed_dict_workflow_state_zero_steps(self):
        """Test TypedDictWorkflowState with zero total steps (edge case)."""
        workflow_id = uuid4()
        now = datetime.now()

        workflow_state: TypedDictWorkflowState = {
            "workflow_id": workflow_id,
            "current_step": "no_steps",
            "total_steps": 0,
            "completed_steps": 0,
            "status": "completed",
            "created_at": now,
            "updated_at": now,
        }

        assert workflow_state["total_steps"] == 0
        assert workflow_state["completed_steps"] == 0
        assert workflow_state["status"] == "completed"
