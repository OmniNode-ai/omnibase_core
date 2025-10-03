"""
Advanced Workflow State Manager for WorkflowOrchestratorAgent.

This module provides comprehensive workflow state management with checkpointing,
recovery, persistence, and advanced state transitions for workflow coordination.
"""

import json
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata


class ModelWorkflowCheckpoint(BaseModel):
    """Model for workflow execution checkpoints."""

    checkpoint_id: str = Field(..., description="Unique checkpoint identifier")
    workflow_id: str = Field(..., description="Workflow instance identifier")
    checkpoint_name: str = Field(..., description="Human-readable checkpoint name")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Checkpoint creation time"
    )
    workflow_state: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow state at checkpoint"
    )
    node_states: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Individual node states"
    )
    execution_context: Dict[str, Any] = Field(
        default_factory=dict, description="Execution context at checkpoint"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional checkpoint metadata"
    )
    is_recovery_point: bool = Field(
        default=False, description="Whether this checkpoint can be used for recovery"
    )


class ModelWorkflowStateTransition(BaseModel):
    """Model for workflow state transitions."""

    transition_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique transition identifier"
    )
    workflow_id: str = Field(..., description="Workflow instance identifier")
    from_state: EnumWorkflowStatus = Field(..., description="Previous workflow state")
    to_state: EnumWorkflowStatus = Field(..., description="New workflow state")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Transition timestamp"
    )
    trigger_event: str = Field(..., description="Event that triggered the transition")
    transition_context: Dict[str, Any] = Field(
        default_factory=dict, description="Context for the transition"
    )
    is_valid: bool = Field(default=True, description="Whether the transition is valid")
    error_details: Optional[str] = Field(
        None, description="Error details if transition failed"
    )


class ModelWorkflowRecoveryPlan(BaseModel):
    """Model for workflow recovery plans."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique recovery plan identifier",
    )
    workflow_id: str = Field(..., description="Workflow instance identifier")
    failure_context: Dict[str, Any] = Field(..., description="Context of the failure")
    recovery_strategy: str = Field(..., description="Selected recovery strategy")
    recovery_steps: List[Dict[str, Any]] = Field(
        default_factory=list, description="Ordered recovery steps"
    )
    estimated_recovery_time_ms: int = Field(
        ..., description="Estimated recovery time in milliseconds"
    )
    recovery_probability: float = Field(
        ..., description="Probability of successful recovery (0.0-1.0)"
    )
    checkpoint_references: List[str] = Field(
        default_factory=list, description="Relevant checkpoint IDs"
    )
    created_timestamp: datetime = Field(
        default_factory=datetime.now, description="Plan creation timestamp"
    )


class WorkflowStateManager:
    """
    Advanced workflow state manager with checkpointing, recovery, and persistence.

    Provides comprehensive state management for workflow instances including:
    - State transition validation and tracking
    - Checkpoint creation and management
    - Recovery plan generation and execution
    - Workflow state persistence and restoration
    - Advanced state analytics and monitoring
    """

    def __init__(self):
        """Initialize the workflow state manager."""
        # Thread-safe state storage
        self._workflow_states: Dict[str, EnumWorkflowStatus] = {}
        self._workflow_states_lock = threading.RLock()

        # Checkpoint management
        self._checkpoints: Dict[str, ModelWorkflowCheckpoint] = {}
        self._checkpoints_by_workflow: Dict[str, List[str]] = {}
        self._checkpoints_lock = threading.RLock()

        # State transition tracking
        self._state_transitions: Dict[str, List[ModelWorkflowStateTransition]] = {}
        self._state_transitions_lock = threading.RLock()

        # Recovery management
        self._recovery_plans: Dict[str, ModelWorkflowRecoveryPlan] = {}
        self._recovery_plans_lock = threading.RLock()

        # Configuration
        self._max_checkpoints_per_workflow = 10
        self._checkpoint_retention_hours = 24
        self._transition_history_limit = 100

        # State transition rules
        self._valid_transitions: Dict[EnumWorkflowStatus, Set[EnumWorkflowStatus]] = {
            EnumWorkflowStatus.PENDING: {
                EnumWorkflowStatus.RUNNING,
                EnumWorkflowStatus.CANCELLED,
            },
            EnumWorkflowStatus.RUNNING: {
                EnumWorkflowStatus.COMPLETED,
                EnumWorkflowStatus.FAILED,
                EnumWorkflowStatus.CANCELLED,
            },
            EnumWorkflowStatus.COMPLETED: set(),  # Terminal state
            EnumWorkflowStatus.FAILED: {
                EnumWorkflowStatus.RUNNING,  # For retry/recovery
                EnumWorkflowStatus.CANCELLED,
            },
            EnumWorkflowStatus.CANCELLED: set(),  # Terminal state
            EnumWorkflowStatus.SIMULATED: {
                EnumWorkflowStatus.RUNNING,
                EnumWorkflowStatus.COMPLETED,
            },
        }

    def initialize_workflow_state(
        self,
        workflow_id: str,
        initial_state: EnumWorkflowStatus = EnumWorkflowStatus.PENDING,
    ) -> bool:
        """
        Initialize state tracking for a new workflow.

        Args:
            workflow_id: Unique workflow identifier
            initial_state: Initial workflow state

        Returns:
            bool: True if initialization successful
        """
        try:
            with self._workflow_states_lock:
                if workflow_id in self._workflow_states:
                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Workflow state already exists for {workflow_id}",
                        metadata=ModelGenericMetadata.from_dict(
                            {
                                "workflow_id": workflow_id,
                                "existing_state": self._workflow_states[
                                    workflow_id
                                ].value,
                            }
                        ),
                    )
                    return False

                self._workflow_states[workflow_id] = initial_state

            # Initialize transition history
            with self._state_transitions_lock:
                self._state_transitions[workflow_id] = []

                # Record initial state as a transition
                initial_transition = ModelWorkflowStateTransition(
                    workflow_id=workflow_id,
                    from_state=initial_state,  # Same as to_state for initialization
                    to_state=initial_state,
                    trigger_event="workflow_initialization",
                    transition_context={"action": "initialize"},
                )

                self._state_transitions[workflow_id].append(initial_transition)

            # Initialize checkpoint tracking
            with self._checkpoints_lock:
                self._checkpoints_by_workflow[workflow_id] = []

            emit_log_event(
                level=LogLevel.INFO,
                message="Workflow state initialized",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "initial_state": initial_state.value}
                ),
            )

            return True

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to initialize workflow state: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return False

    def transition_workflow_state(
        self,
        workflow_id: str,
        new_state: EnumWorkflowStatus,
        trigger_event: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Transition workflow to a new state with validation.

        Args:
            workflow_id: Unique workflow identifier
            new_state: Target workflow state
            trigger_event: Event that triggered the transition
            context: Additional transition context

        Returns:
            bool: True if transition successful
        """
        try:
            with self._workflow_states_lock:
                current_state = self._workflow_states.get(workflow_id)

                if current_state is None:
                    emit_log_event(
                        level=LogLevel.ERROR,
                        message=f"Workflow state not found for {workflow_id}",
                        metadata=ModelGenericMetadata.from_dict(
                            {
                                "workflow_id": workflow_id,
                                "requested_new_state": new_state.value,
                            }
                        ),
                    )
                    return False

                # Validate transition
                if new_state not in self._valid_transitions.get(current_state, set()):
                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Invalid state transition attempted",
                        metadata=ModelGenericMetadata.from_dict(
                            {
                                "workflow_id": workflow_id,
                                "from_state": current_state.value,
                                "to_state": new_state.value,
                                "trigger_event": trigger_event,
                            }
                        ),
                    )

                    # Record invalid transition
                    invalid_transition = ModelWorkflowStateTransition(
                        workflow_id=workflow_id,
                        from_state=current_state,
                        to_state=new_state,
                        trigger_event=trigger_event,
                        transition_context=context or {},
                        is_valid=False,
                        error_details="Invalid state transition",
                    )

                    with self._state_transitions_lock:
                        self._state_transitions[workflow_id].append(invalid_transition)

                        # Limit transition history
                        if (
                            len(self._state_transitions[workflow_id])
                            > self._transition_history_limit
                        ):
                            self._state_transitions[workflow_id] = (
                                self._state_transitions[workflow_id][
                                    -self._transition_history_limit :
                                ]
                            )

                    return False

                # Perform transition
                self._workflow_states[workflow_id] = new_state

            # Record successful transition
            transition = ModelWorkflowStateTransition(
                workflow_id=workflow_id,
                from_state=current_state,
                to_state=new_state,
                trigger_event=trigger_event,
                transition_context=context or {},
            )

            with self._state_transitions_lock:
                self._state_transitions[workflow_id].append(transition)

                # Limit transition history
                if (
                    len(self._state_transitions[workflow_id])
                    > self._transition_history_limit
                ):
                    self._state_transitions[workflow_id] = self._state_transitions[
                        workflow_id
                    ][-self._transition_history_limit :]

            emit_log_event(
                level=LogLevel.INFO,
                message="Workflow state transition completed",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "from_state": current_state.value,
                        "to_state": new_state.value,
                        "trigger_event": trigger_event,
                    }
                ),
            )

            return True

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to transition workflow state: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return False

    def create_checkpoint(
        self,
        workflow_id: str,
        checkpoint_name: str,
        workflow_state: Dict[str, Any],
        node_states: Optional[Dict[str, Dict[str, Any]]] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        is_recovery_point: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Create a workflow checkpoint for state preservation.

        Args:
            workflow_id: Unique workflow identifier
            checkpoint_name: Human-readable checkpoint name
            workflow_state: Current workflow state data
            node_states: Individual node states
            execution_context: Current execution context
            is_recovery_point: Whether this can be used for recovery
            metadata: Additional checkpoint metadata

        Returns:
            Optional[str]: Checkpoint ID if successful, None otherwise
        """
        try:
            checkpoint = ModelWorkflowCheckpoint(
                checkpoint_id=str(uuid4()),
                workflow_id=workflow_id,
                checkpoint_name=checkpoint_name,
                workflow_state=workflow_state,
                node_states=node_states or {},
                execution_context=execution_context or {},
                is_recovery_point=is_recovery_point,
                metadata=metadata or {},
            )

            with self._checkpoints_lock:
                # Store checkpoint
                self._checkpoints[checkpoint.checkpoint_id] = checkpoint

                # Add to workflow's checkpoint list
                if workflow_id not in self._checkpoints_by_workflow:
                    self._checkpoints_by_workflow[workflow_id] = []

                self._checkpoints_by_workflow[workflow_id].append(
                    checkpoint.checkpoint_id
                )

                # Enforce checkpoint limits per workflow
                workflow_checkpoints = self._checkpoints_by_workflow[workflow_id]
                if len(workflow_checkpoints) > self._max_checkpoints_per_workflow:
                    # Remove oldest checkpoint
                    oldest_checkpoint_id = workflow_checkpoints.pop(0)
                    if oldest_checkpoint_id in self._checkpoints:
                        del self._checkpoints[oldest_checkpoint_id]

                        emit_log_event(
                            level=LogLevel.DEBUG,
                            message="Removed oldest checkpoint due to limit",
                            metadata=ModelGenericMetadata.from_dict(
                                {
                                    "workflow_id": workflow_id,
                                    "removed_checkpoint_id": oldest_checkpoint_id,
                                    "checkpoint_limit": self._max_checkpoints_per_workflow,
                                }
                            ),
                        )

            emit_log_event(
                level=LogLevel.INFO,
                message="Workflow checkpoint created",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "checkpoint_name": checkpoint_name,
                        "is_recovery_point": is_recovery_point,
                    }
                ),
            )

            return checkpoint.checkpoint_id

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to create checkpoint: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return None

    def get_workflow_state(self, workflow_id: str) -> Optional[EnumWorkflowStatus]:
        """
        Get current workflow state.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Optional[EnumWorkflowStatus]: Current state or None if not found
        """
        with self._workflow_states_lock:
            return self._workflow_states.get(workflow_id)

    def get_state_history(self, workflow_id: str) -> List[ModelWorkflowStateTransition]:
        """
        Get workflow state transition history.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            List[ModelWorkflowStateTransition]: Ordered list of transitions
        """
        with self._state_transitions_lock:
            return self._state_transitions.get(workflow_id, []).copy()

    def get_checkpoints(self, workflow_id: str) -> List[ModelWorkflowCheckpoint]:
        """
        Get all checkpoints for a workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            List[ModelWorkflowCheckpoint]: List of checkpoints
        """
        with self._checkpoints_lock:
            checkpoint_ids = self._checkpoints_by_workflow.get(workflow_id, [])
            return [
                self._checkpoints[checkpoint_id]
                for checkpoint_id in checkpoint_ids
                if checkpoint_id in self._checkpoints
            ]

    def get_recovery_checkpoints(
        self, workflow_id: str
    ) -> List[ModelWorkflowCheckpoint]:
        """
        Get recovery-enabled checkpoints for a workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            List[ModelWorkflowCheckpoint]: List of recovery checkpoints
        """
        checkpoints = self.get_checkpoints(workflow_id)
        return [cp for cp in checkpoints if cp.is_recovery_point]

    def generate_recovery_plan(
        self,
        workflow_id: str,
        failure_context: Dict[str, Any],
        recovery_strategy: str = "checkpoint_rollback",
    ) -> Optional[ModelWorkflowRecoveryPlan]:
        """
        Generate a recovery plan for a failed workflow.

        Args:
            workflow_id: Unique workflow identifier
            failure_context: Context of the failure
            recovery_strategy: Recovery strategy to use

        Returns:
            Optional[ModelWorkflowRecoveryPlan]: Recovery plan if generated successfully
        """
        try:
            # Get available recovery checkpoints
            recovery_checkpoints = self.get_recovery_checkpoints(workflow_id)

            # Generate recovery steps based on strategy
            recovery_steps = []
            checkpoint_refs = []
            estimated_time = 0
            recovery_probability = 0.0

            if recovery_strategy == "checkpoint_rollback":
                if recovery_checkpoints:
                    # Use most recent recovery checkpoint
                    latest_checkpoint = max(
                        recovery_checkpoints, key=lambda cp: cp.timestamp
                    )
                    checkpoint_refs.append(latest_checkpoint.checkpoint_id)

                    recovery_steps = [
                        {
                            "step": "restore_from_checkpoint",
                            "checkpoint_id": latest_checkpoint.checkpoint_id,
                            "estimated_time_ms": 500,
                        },
                        {
                            "step": "reset_workflow_state",
                            "target_state": "running",
                            "estimated_time_ms": 100,
                        },
                        {
                            "step": "resume_execution",
                            "resume_point": latest_checkpoint.checkpoint_name,
                            "estimated_time_ms": 1000,
                        },
                    ]

                    estimated_time = sum(
                        step.get("estimated_time_ms", 0) for step in recovery_steps
                    )
                    recovery_probability = (
                        0.8  # 80% success rate for checkpoint rollback
                    )

                else:
                    # No checkpoints available - full restart
                    recovery_steps = [
                        {
                            "step": "full_restart",
                            "restart_type": "clean",
                            "estimated_time_ms": 2000,
                        }
                    ]
                    estimated_time = 2000
                    recovery_probability = 0.6  # 60% success rate for full restart

            elif recovery_strategy == "partial_retry":
                # Identify failed nodes and retry only those
                failed_nodes = failure_context.get("failed_nodes", [])

                for node_id in failed_nodes:
                    recovery_steps.append(
                        {
                            "step": "retry_node",
                            "node_id": node_id,
                            "retry_count": 3,
                            "estimated_time_ms": 800,
                        }
                    )

                estimated_time = len(failed_nodes) * 800
                recovery_probability = 0.7  # 70% success rate for partial retry

            elif recovery_strategy == "compensating_actions":
                # Generate compensating actions based on failure context
                recovery_steps = [
                    {
                        "step": "execute_compensation",
                        "compensation_type": "side_effect_reversal",
                        "estimated_time_ms": 1500,
                    },
                    {
                        "step": "clean_partial_state",
                        "cleanup_scope": "affected_resources",
                        "estimated_time_ms": 800,
                    },
                ]

                estimated_time = 2300
                recovery_probability = 0.75  # 75% success rate for compensating actions

            else:
                # Unknown strategy - abort
                recovery_steps = [
                    {
                        "step": "abort_workflow",
                        "cleanup_resources": True,
                        "estimated_time_ms": 500,
                    }
                ]

                estimated_time = 500
                recovery_probability = (
                    1.0  # 100% success rate for abort (always succeeds)
                )

            # Create recovery plan
            recovery_plan = ModelWorkflowRecoveryPlan(
                workflow_id=workflow_id,
                failure_context=failure_context,
                recovery_strategy=recovery_strategy,
                recovery_steps=recovery_steps,
                estimated_recovery_time_ms=estimated_time,
                recovery_probability=recovery_probability,
                checkpoint_references=checkpoint_refs,
            )

            # Store recovery plan
            with self._recovery_plans_lock:
                self._recovery_plans[recovery_plan.plan_id] = recovery_plan

            emit_log_event(
                level=LogLevel.INFO,
                message="Recovery plan generated",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "plan_id": recovery_plan.plan_id,
                        "strategy": recovery_strategy,
                        "estimated_time_ms": estimated_time,
                        "probability": recovery_probability,
                    }
                ),
            )

            return recovery_plan

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to generate recovery plan: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return None

    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired checkpoints and old transition data.

        Returns:
            Dict[str, int]: Cleanup statistics
        """
        try:
            current_time = datetime.now()
            expiry_threshold = current_time - timedelta(
                hours=self._checkpoint_retention_hours
            )

            checkpoints_removed = 0

            # Clean up expired checkpoints
            with self._checkpoints_lock:
                expired_checkpoints = [
                    checkpoint_id
                    for checkpoint_id, checkpoint in self._checkpoints.items()
                    if checkpoint.timestamp < expiry_threshold
                ]

                for checkpoint_id in expired_checkpoints:
                    checkpoint = self._checkpoints[checkpoint_id]
                    workflow_id = checkpoint.workflow_id

                    # Remove from main storage
                    del self._checkpoints[checkpoint_id]

                    # Remove from workflow's checkpoint list
                    if workflow_id in self._checkpoints_by_workflow:
                        try:
                            self._checkpoints_by_workflow[workflow_id].remove(
                                checkpoint_id
                            )
                        except ValueError:
                            pass  # Already removed

                    checkpoints_removed += 1

            # Clean up old transition data for completed workflows
            transitions_cleaned = 0
            with self._workflow_states_lock, self._state_transitions_lock:
                completed_workflows = [
                    workflow_id
                    for workflow_id, state in self._workflow_states.items()
                    if state
                    in [EnumWorkflowStatus.COMPLETED, EnumWorkflowStatus.CANCELLED]
                ]

                for workflow_id in completed_workflows:
                    transitions = self._state_transitions.get(workflow_id, [])

                    # Keep only recent transitions for completed workflows
                    if transitions:
                        last_transition = transitions[-1]
                        if last_transition.timestamp < expiry_threshold:
                            # Keep only the last transition for historical record
                            self._state_transitions[workflow_id] = [last_transition]
                            transitions_cleaned += len(transitions) - 1

            emit_log_event(
                level=LogLevel.INFO,
                message="Cleanup completed",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "checkpoints_removed": checkpoints_removed,
                        "transitions_cleaned": transitions_cleaned,
                        "retention_hours": self._checkpoint_retention_hours,
                    }
                ),
            )

            return {
                "checkpoints_removed": checkpoints_removed,
                "transitions_cleaned": transitions_cleaned,
                "retention_hours": self._checkpoint_retention_hours,
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Cleanup failed: {str(e)}",
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )
            return {"checkpoints_removed": 0, "transitions_cleaned": 0, "error": str(e)}

    def get_state_analytics(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics about workflow states and transitions.

        Args:
            workflow_id: Specific workflow ID or None for global analytics

        Returns:
            Dict[str, Any]: Analytics data
        """
        try:
            if workflow_id:
                # Workflow-specific analytics
                with (
                    self._workflow_states_lock,
                    self._state_transitions_lock,
                    self._checkpoints_lock,
                ):
                    current_state = self._workflow_states.get(workflow_id)
                    transitions = self._state_transitions.get(workflow_id, [])
                    checkpoints = self.get_checkpoints(workflow_id)
                    recovery_checkpoints = [
                        cp for cp in checkpoints if cp.is_recovery_point
                    ]

                    analytics = {
                        "workflow_id": workflow_id,
                        "current_state": current_state.value if current_state else None,
                        "total_transitions": len(transitions),
                        "invalid_transitions": len(
                            [t for t in transitions if not t.is_valid]
                        ),
                        "total_checkpoints": len(checkpoints),
                        "recovery_checkpoints": len(recovery_checkpoints),
                        "state_distribution": {},
                        "avg_transition_time": 0.0,
                    }

                    if transitions:
                        # Calculate state distribution
                        state_counts = {}
                        transition_times = []

                        for i, transition in enumerate(transitions):
                            to_state = transition.to_state.value
                            state_counts[to_state] = state_counts.get(to_state, 0) + 1

                            # Calculate transition time (if next transition exists)
                            if i < len(transitions) - 1:
                                next_transition = transitions[i + 1]
                                time_diff = (
                                    next_transition.timestamp - transition.timestamp
                                ).total_seconds() * 1000
                                transition_times.append(time_diff)

                        analytics["state_distribution"] = state_counts
                        if transition_times:
                            analytics["avg_transition_time"] = sum(
                                transition_times
                            ) / len(transition_times)

                    return analytics

            else:
                # Global analytics
                with (
                    self._workflow_states_lock,
                    self._state_transitions_lock,
                    self._checkpoints_lock,
                ):
                    # Count states
                    state_distribution = {}
                    for state in self._workflow_states.values():
                        state_distribution[state.value] = (
                            state_distribution.get(state.value, 0) + 1
                        )

                    # Count transitions
                    total_transitions = sum(
                        len(transitions)
                        for transitions in self._state_transitions.values()
                    )
                    invalid_transitions = sum(
                        len([t for t in transitions if not t.is_valid])
                        for transitions in self._state_transitions.values()
                    )

                    # Count checkpoints
                    total_checkpoints = len(self._checkpoints)
                    recovery_checkpoints = len(
                        [
                            cp
                            for cp in self._checkpoints.values()
                            if cp.is_recovery_point
                        ]
                    )

                    return {
                        "scope": "global",
                        "total_workflows": len(self._workflow_states),
                        "state_distribution": state_distribution,
                        "total_transitions": total_transitions,
                        "invalid_transitions": invalid_transitions,
                        "transition_error_rate": (
                            invalid_transitions / max(total_transitions, 1)
                        )
                        * 100,
                        "total_checkpoints": total_checkpoints,
                        "recovery_checkpoints": recovery_checkpoints,
                        "checkpoint_recovery_ratio": (
                            recovery_checkpoints / max(total_checkpoints, 1)
                        )
                        * 100,
                    }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to generate analytics: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return {"error": str(e), "workflow_id": workflow_id}
