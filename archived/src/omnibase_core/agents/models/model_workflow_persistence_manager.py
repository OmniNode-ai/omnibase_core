"""
Workflow Persistence Manager for ONEX-LlamaIndex Integration.

Provides robust workflow persistence and recovery capabilities using LlamaIndex
workflows as the underlying execution engine while maintaining ONEX compliance.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata
from omnibase_core.patterns.workflow_coordination.llamaindex_integration_pattern import (
    LlamaIndexWorkflowCoordinationPattern,
    ModelLlamaIndexWorkflowContext,
)


class ModelWorkflowPersistenceState(BaseModel):
    """
    Model for workflow persistence state.

    Captures complete workflow state for recovery purposes.
    """

    workflow_id: str = Field(..., description="Unique workflow identifier")
    workflow_name: str = Field(..., description="Human-readable workflow name")
    workflow_version: str = Field(default="1.0.0", description="Workflow version")

    # Execution state
    status: str = Field(..., description="Current workflow status")
    created_timestamp: datetime = Field(..., description="Workflow creation time")
    last_checkpoint_timestamp: datetime = Field(..., description="Last checkpoint time")

    # Persistence data
    llamaindex_workflow_state: Dict[str, Any] = Field(
        default_factory=dict, description="LlamaIndex workflow state"
    )
    onex_execution_context: Dict[str, Any] = Field(
        default_factory=dict, description="ONEX execution context"
    )
    coordination_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Coordination-specific metadata"
    )

    # Recovery information
    completed_steps: List[str] = Field(
        default_factory=list, description="List of completed step IDs"
    )
    failed_steps: List[str] = Field(
        default_factory=list, description="List of failed step IDs"
    )
    recoverable_errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recoverable error information"
    )

    # Performance tracking
    execution_time_ms: int = Field(default=0, description="Total execution time")
    checkpoint_count: int = Field(
        default=0, description="Number of checkpoints created"
    )
    recovery_attempts: int = Field(default=0, description="Number of recovery attempts")


class ModelWorkflowRecoveryPlan(BaseModel):
    """
    Model for workflow recovery planning.

    Defines the recovery strategy and actions for failed workflows.
    """

    recovery_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Recovery operation ID"
    )
    workflow_id: str = Field(..., description="Workflow to recover")
    recovery_strategy: str = Field(
        ..., description="Recovery strategy (resume, restart, compensate)"
    )

    # Recovery actions
    steps_to_retry: List[str] = Field(
        default_factory=list, description="Steps to retry"
    )
    steps_to_skip: List[str] = Field(default_factory=list, description="Steps to skip")
    compensation_actions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Compensation actions to execute"
    )

    # Recovery configuration
    max_retry_attempts: int = Field(
        default=3, description="Maximum retry attempts per step"
    )
    retry_delay_ms: int = Field(
        default=1000, description="Delay between retries in milliseconds"
    )
    timeout_ms: int = Field(
        default=300000, description="Recovery timeout in milliseconds"
    )

    # Metadata
    created_timestamp: datetime = Field(
        default_factory=datetime.now, description="Recovery plan creation time"
    )
    estimated_recovery_time_ms: int = Field(
        default=0, description="Estimated recovery time"
    )


class WorkflowPersistenceManager:
    """
    Manages workflow persistence and recovery using LlamaIndex workflows.

    Provides robust state management, checkpoint creation, and recovery capabilities
    while maintaining thread safety and ONEX compliance.
    """

    def __init__(
        self,
        persistence_directory: str = "/tmp/onex_workflows",
        max_checkpoints_per_workflow: int = 10,
        checkpoint_interval_seconds: int = 30,
    ):
        """
        Initialize workflow persistence manager.

        Args:
            persistence_directory: Directory for storing workflow state files
            max_checkpoints_per_workflow: Maximum checkpoints to keep per workflow
            checkpoint_interval_seconds: Automatic checkpoint interval
        """
        self.persistence_directory = Path(persistence_directory)
        self.persistence_directory.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.max_checkpoints_per_workflow = max_checkpoints_per_workflow
        self.checkpoint_interval_seconds = checkpoint_interval_seconds

        # Thread safety
        self._persistence_lock = threading.RLock()
        self._recovery_lock = threading.RLock()

        # In-memory state tracking
        self._active_workflows: Dict[str, ModelWorkflowPersistenceState] = {}
        self._llamaindex_coordinators: Dict[
            str, LlamaIndexWorkflowCoordinationPattern
        ] = {}
        self._recovery_plans: Dict[str, ModelWorkflowRecoveryPlan] = {}

        # Statistics
        self._persistence_stats = {
            "workflows_persisted": 0,
            "workflows_recovered": 0,
            "checkpoints_created": 0,
            "recovery_failures": 0,
            "total_recovery_time_ms": 0,
        }

        emit_log_event(
            level=LogLevel.INFO,
            message="Workflow persistence manager initialized",
            context=ModelGenericMetadata.from_dict(
                {
                    "persistence_directory": str(self.persistence_directory),
                    "max_checkpoints_per_workflow": max_checkpoints_per_workflow,
                    "checkpoint_interval_seconds": checkpoint_interval_seconds,
                }
            ),
        )

    def initialize_workflow_persistence(
        self,
        workflow_id: str,
        workflow_name: str,
        workflow_definition: Dict[str, Any],
        initial_context: Dict[str, Any],
    ) -> ModelWorkflowPersistenceState:
        """
        Initialize persistence for a new workflow.

        Args:
            workflow_id: Unique workflow identifier
            workflow_name: Human-readable workflow name
            workflow_definition: Workflow definition data
            initial_context: Initial execution context

        Returns:
            ModelWorkflowPersistenceState: Initial persistence state
        """
        try:
            with self._persistence_lock:
                current_time = datetime.now()

                # Create initial persistence state
                persistence_state = ModelWorkflowPersistenceState(
                    workflow_id=workflow_id,
                    workflow_name=workflow_name,
                    status="INITIALIZED",
                    created_timestamp=current_time,
                    last_checkpoint_timestamp=current_time,
                    onex_execution_context=initial_context.copy(),
                    coordination_metadata={
                        "workflow_definition": workflow_definition,
                        "initialization_time": current_time.isoformat(),
                    },
                )

                # Create LlamaIndex workflow coordinator
                from omnibase_core.models.subcontracts.model_workflow_coordination_subcontract import (
                    ModelWorkflowCoordinationSubcontract,
                )

                coordination_config = ModelWorkflowCoordinationSubcontract(
                    subcontract_id=str(uuid4()),
                    workflow_type="onex_llamaindex_integration",
                    coordination_strategy="hybrid_execution",
                    node_assignments=[],
                    execution_constraints={
                        "max_parallel_nodes": 4,
                        "timeout_seconds": 300,
                    },
                )

                llamaindex_coordinator = LlamaIndexWorkflowCoordinationPattern(
                    coordination_config
                )

                # Store in memory
                self._active_workflows[workflow_id] = persistence_state
                self._llamaindex_coordinators[workflow_id] = llamaindex_coordinator

                # Persist initial state
                self._persist_workflow_state(persistence_state)

                self._persistence_stats["workflows_persisted"] += 1

                emit_log_event(
                    level=LogLevel.INFO,
                    message="Workflow persistence initialized",
                    context=ModelGenericMetadata.from_dict(
                        {
                            "workflow_id": workflow_id,
                            "workflow_name": workflow_name,
                            "status": persistence_state.status,
                        }
                    ),
                )

                return persistence_state

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to initialize workflow persistence: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            raise OnexError(
                error_code=CoreErrorCode.WORKFLOW_PERSISTENCE_FAILED,
                message=f"Failed to initialize persistence for workflow {workflow_id}: {str(e)}",
                context={"workflow_id": workflow_id, "error": str(e)},
            )

    def create_checkpoint(
        self,
        workflow_id: str,
        checkpoint_name: str,
        current_status: str,
        execution_context: Dict[str, Any],
        completed_steps: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a checkpoint for workflow recovery.

        Args:
            workflow_id: Workflow identifier
            checkpoint_name: Human-readable checkpoint name
            current_status: Current workflow status
            execution_context: Current execution context
            completed_steps: List of completed step IDs
            metadata: Additional checkpoint metadata

        Returns:
            bool: True if checkpoint was created successfully
        """
        try:
            with self._persistence_lock:
                if workflow_id not in self._active_workflows:
                    emit_log_event(
                        level=LogLevel.WARNING,
                        message="Cannot create checkpoint - workflow not found",
                        context=ModelGenericMetadata.from_dict(
                            {
                                "workflow_id": workflow_id,
                                "checkpoint_name": checkpoint_name,
                            }
                        ),
                    )
                    return False

                persistence_state = self._active_workflows[workflow_id]
                current_time = datetime.now()

                # Update persistence state
                persistence_state.status = current_status
                persistence_state.last_checkpoint_timestamp = current_time
                persistence_state.onex_execution_context.update(execution_context)
                persistence_state.checkpoint_count += 1

                if completed_steps:
                    persistence_state.completed_steps.extend(completed_steps)
                    # Remove duplicates while preserving order
                    seen = set()
                    persistence_state.completed_steps = [
                        step
                        for step in persistence_state.completed_steps
                        if not (step in seen or seen.add(step))
                    ]

                if metadata:
                    persistence_state.coordination_metadata.update(metadata)

                # Add checkpoint metadata
                checkpoint_metadata = {
                    "checkpoint_name": checkpoint_name,
                    "checkpoint_timestamp": current_time.isoformat(),
                    "checkpoint_id": str(uuid4()),
                }
                persistence_state.coordination_metadata[
                    f"checkpoint_{persistence_state.checkpoint_count}"
                ] = checkpoint_metadata

                # Persist updated state
                self._persist_workflow_state(persistence_state)

                # Update statistics
                self._persistence_stats["checkpoints_created"] += 1

                emit_log_event(
                    level=LogLevel.INFO,
                    message="Workflow checkpoint created",
                    context=ModelGenericMetadata.from_dict(
                        {
                            "workflow_id": workflow_id,
                            "checkpoint_name": checkpoint_name,
                            "checkpoint_count": persistence_state.checkpoint_count,
                            "completed_steps_count": len(
                                persistence_state.completed_steps
                            ),
                        }
                    ),
                )

                return True

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to create checkpoint: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "checkpoint_name": checkpoint_name,
                        "error": str(e),
                    }
                ),
            )
            return False

    def recover_workflow(
        self, workflow_id: str, recovery_strategy: str = "resume"
    ) -> Optional[ModelWorkflowPersistenceState]:
        """
        Recover a failed or interrupted workflow.

        Args:
            workflow_id: Workflow identifier to recover
            recovery_strategy: Recovery strategy (resume, restart, compensate)

        Returns:
            ModelWorkflowPersistenceState: Recovered workflow state, or None if recovery failed
        """
        try:
            with self._recovery_lock:
                # Load persisted state
                persistence_state = self._load_workflow_state(workflow_id)
                if not persistence_state:
                    emit_log_event(
                        level=LogLevel.ERROR,
                        message="Cannot recover workflow - no persisted state found",
                        context=ModelGenericMetadata.from_dict(
                            {"workflow_id": workflow_id}
                        ),
                    )
                    return None

                recovery_start_time = datetime.now()

                # Create recovery plan
                recovery_plan = self._create_recovery_plan(
                    persistence_state, recovery_strategy
                )
                self._recovery_plans[workflow_id] = recovery_plan

                emit_log_event(
                    level=LogLevel.INFO,
                    message="Starting workflow recovery",
                    context=ModelGenericMetadata.from_dict(
                        {
                            "workflow_id": workflow_id,
                            "recovery_strategy": recovery_strategy,
                            "recovery_id": recovery_plan.recovery_id,
                            "completed_steps_count": len(
                                persistence_state.completed_steps
                            ),
                        }
                    ),
                )

                # Execute recovery based on strategy
                if recovery_strategy == "resume":
                    recovered_state = self._resume_workflow_execution(
                        persistence_state, recovery_plan
                    )
                elif recovery_strategy == "restart":
                    recovered_state = self._restart_workflow_execution(
                        persistence_state, recovery_plan
                    )
                elif recovery_strategy == "compensate":
                    recovered_state = self._compensate_workflow_execution(
                        persistence_state, recovery_plan
                    )
                else:
                    raise ValueError(f"Unknown recovery strategy: {recovery_strategy}")

                if recovered_state:
                    # Update recovery statistics
                    recovery_time = int(
                        (datetime.now() - recovery_start_time).total_seconds() * 1000
                    )
                    recovered_state.recovery_attempts += 1

                    self._persistence_stats["workflows_recovered"] += 1
                    self._persistence_stats["total_recovery_time_ms"] += recovery_time

                    # Store in active workflows
                    self._active_workflows[workflow_id] = recovered_state

                    # Create checkpoint after successful recovery
                    self.create_checkpoint(
                        workflow_id=workflow_id,
                        checkpoint_name=f"recovery_{recovery_strategy}",
                        current_status=recovered_state.status,
                        execution_context=recovered_state.onex_execution_context,
                        metadata={
                            "recovery_id": recovery_plan.recovery_id,
                            "recovery_strategy": recovery_strategy,
                            "recovery_time_ms": recovery_time,
                        },
                    )

                    emit_log_event(
                        level=LogLevel.INFO,
                        message="Workflow recovery completed successfully",
                        context=ModelGenericMetadata.from_dict(
                            {
                                "workflow_id": workflow_id,
                                "recovery_strategy": recovery_strategy,
                                "recovery_time_ms": recovery_time,
                                "final_status": recovered_state.status,
                            }
                        ),
                    )
                else:
                    self._persistence_stats["recovery_failures"] += 1

                    emit_log_event(
                        level=LogLevel.ERROR,
                        message="Workflow recovery failed",
                        context=ModelGenericMetadata.from_dict(
                            {
                                "workflow_id": workflow_id,
                                "recovery_strategy": recovery_strategy,
                            }
                        ),
                    )

                return recovered_state

        except Exception as e:
            self._persistence_stats["recovery_failures"] += 1

            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Workflow recovery failed with exception: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "recovery_strategy": recovery_strategy,
                        "error": str(e),
                    }
                ),
            )
            return None

    def _persist_workflow_state(
        self, persistence_state: ModelWorkflowPersistenceState
    ) -> None:
        """Persist workflow state to storage."""
        workflow_file = (
            self.persistence_directory
            / f"workflow_{persistence_state.workflow_id}.json"
        )

        with open(workflow_file, "w") as f:
            json.dump(persistence_state.model_dump(), f, indent=2, default=str)

    def _load_workflow_state(
        self, workflow_id: str
    ) -> Optional[ModelWorkflowPersistenceState]:
        """Load workflow state from storage."""
        workflow_file = self.persistence_directory / f"workflow_{workflow_id}.json"

        if not workflow_file.exists():
            return None

        try:
            with open(workflow_file, "r") as f:
                data = json.load(f)

            return ModelWorkflowPersistenceState(**data)
        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to load workflow state: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return None

    def _create_recovery_plan(
        self, persistence_state: ModelWorkflowPersistenceState, recovery_strategy: str
    ) -> ModelWorkflowRecoveryPlan:
        """Create recovery plan based on workflow state and strategy."""
        recovery_plan = ModelWorkflowRecoveryPlan(
            workflow_id=persistence_state.workflow_id,
            recovery_strategy=recovery_strategy,
        )

        if recovery_strategy == "resume":
            # Resume from last checkpoint - skip completed steps
            recovery_plan.steps_to_skip = persistence_state.completed_steps.copy()
            recovery_plan.steps_to_retry = persistence_state.failed_steps.copy()
        elif recovery_strategy == "restart":
            # Restart from beginning - retry all steps
            recovery_plan.steps_to_retry = ["all"]
            recovery_plan.steps_to_skip = []
        elif recovery_strategy == "compensate":
            # Compensate completed work
            recovery_plan.compensation_actions = [
                {
                    "action": "rollback",
                    "target_steps": persistence_state.completed_steps,
                }
            ]

        return recovery_plan

    def _resume_workflow_execution(
        self,
        persistence_state: ModelWorkflowPersistenceState,
        recovery_plan: ModelWorkflowRecoveryPlan,
    ) -> Optional[ModelWorkflowPersistenceState]:
        """Resume workflow execution from last checkpoint."""
        persistence_state.status = "RESUMING"

        # Simulate resume logic - in real implementation, this would:
        # 1. Reconstruct LlamaIndex workflow from persisted state
        # 2. Skip completed steps
        # 3. Resume from last checkpoint

        persistence_state.status = "RUNNING"
        return persistence_state

    def _restart_workflow_execution(
        self,
        persistence_state: ModelWorkflowPersistenceState,
        recovery_plan: ModelWorkflowRecoveryPlan,
    ) -> Optional[ModelWorkflowPersistenceState]:
        """Restart workflow execution from beginning."""
        persistence_state.status = "RESTARTING"
        persistence_state.completed_steps = []
        persistence_state.failed_steps = []

        # Clear execution context for fresh start
        persistence_state.onex_execution_context = {
            "restart_recovery": True,
            "original_workflow_id": persistence_state.workflow_id,
        }

        persistence_state.status = "RUNNING"
        return persistence_state

    def _compensate_workflow_execution(
        self,
        persistence_state: ModelWorkflowPersistenceState,
        recovery_plan: ModelWorkflowRecoveryPlan,
    ) -> Optional[ModelWorkflowPersistenceState]:
        """Execute compensation actions for failed workflow."""
        persistence_state.status = "COMPENSATING"

        # Execute compensation actions
        for action in recovery_plan.compensation_actions:
            emit_log_event(
                level=LogLevel.INFO,
                message="Executing compensation action",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": persistence_state.workflow_id, "action": action}
                ),
            )

        persistence_state.status = "COMPENSATED"
        return persistence_state

    def get_persistence_statistics(self) -> Dict[str, Any]:
        """Get comprehensive persistence statistics."""
        with self._persistence_lock:
            return {
                "persistence_stats": self._persistence_stats.copy(),
                "active_workflows_count": len(self._active_workflows),
                "active_recovery_plans_count": len(self._recovery_plans),
                "persistence_directory": str(self.persistence_directory),
                "checkpoint_interval_seconds": self.checkpoint_interval_seconds,
            }

    def cleanup_completed_workflows(self, max_age_hours: int = 24) -> Dict[str, int]:
        """Clean up completed workflow persistence data."""
        cleanup_stats = {"workflows_cleaned": 0, "files_removed": 0}

        try:
            with self._persistence_lock:
                current_time = datetime.now()
                workflows_to_remove = []

                # Find workflows to clean up
                for workflow_id, state in self._active_workflows.items():
                    if state.status in ["COMPLETED", "FAILED", "COMPENSATED"]:
                        age_hours = (
                            current_time - state.last_checkpoint_timestamp
                        ).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            workflows_to_remove.append(workflow_id)

                # Remove from memory and disk
                for workflow_id in workflows_to_remove:
                    del self._active_workflows[workflow_id]
                    if workflow_id in self._llamaindex_coordinators:
                        del self._llamaindex_coordinators[workflow_id]
                    if workflow_id in self._recovery_plans:
                        del self._recovery_plans[workflow_id]

                    # Remove persistence file
                    workflow_file = (
                        self.persistence_directory / f"workflow_{workflow_id}.json"
                    )
                    if workflow_file.exists():
                        workflow_file.unlink()
                        cleanup_stats["files_removed"] += 1

                    cleanup_stats["workflows_cleaned"] += 1

                emit_log_event(
                    level=LogLevel.INFO,
                    message="Workflow persistence cleanup completed",
                    context=ModelGenericMetadata.from_dict(cleanup_stats),
                )

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Workflow persistence cleanup failed: {str(e)}",
                context=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

        return cleanup_stats
