"""
Canary Orchestrator Node - Workflow coordination for canary deployments.

Simple ORCHESTRATOR node implementation for testing and validation purposes.
"""

import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.core.node_base import ModelNodeBase


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelCanaryOrchestratorInput(BaseModel):
    """Input model for Canary Orchestrator operations."""

    operation_type: str = Field(..., description="Type of orchestration operation")
    workflow_id: str = Field(..., description="Unique workflow identifier")
    correlation_id: Optional[str] = Field(
        default=None, description="Request correlation ID"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Operation-specific parameters"
    )


class ModelCanaryOrchestratorOutput(BaseModel):
    """Output model for Canary Orchestrator operations."""

    status: str = Field(..., description="Operation status")
    workflow_result: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow execution result"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )
    execution_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Execution metrics and timing"
    )


class WorkflowExecution:
    """Represents a workflow execution instance."""

    def __init__(self, workflow_id: str, workflow_type: str):
        self.workflow_id = workflow_id
        self.workflow_type = workflow_type
        self.status = WorkflowStatus.PENDING
        self.steps_completed = 0
        self.total_steps = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []


class NodeCanaryOrchestrator(ModelNodeBase):
    """
    Canary Orchestrator Node - Workflow coordination for canary deployments.

    Simple ORCHESTRATOR node that manages workflow execution, coordinates
    between different services, and handles canary deployment orchestration.
    """

    def __init__(self, contract_path=None, *args, **kwargs):
        from pathlib import Path

        # Use default contract path if not provided
        if contract_path is None:
            contract_path = Path(__file__).parent / "contract.yaml"

        super().__init__(contract_path=contract_path, *args, **kwargs)
        self._active_workflows: Dict[str, WorkflowExecution] = {}
        self._completed_workflows: Dict[str, WorkflowExecution] = {}
        self._workflow_count = 0

    async def start_workflow(
        self, input_data: ModelCanaryOrchestratorInput
    ) -> ModelCanaryOrchestratorOutput:
        """
        Start infrastructure workflow.

        Args:
            input_data: Workflow start parameters

        Returns:
            ModelCanaryOrchestratorOutput with workflow status
        """
        try:
            workflow_id = input_data.workflow_id

            # Create workflow execution
            execution = WorkflowExecution(
                workflow_id=workflow_id, workflow_type=input_data.operation_type
            )

            self._active_workflows[workflow_id] = execution

            # Start workflow execution
            if input_data.operation_type == "infrastructure_startup":
                result = await self._execute_infrastructure_startup(execution)
            elif input_data.operation_type == "infrastructure_shutdown":
                result = await self._execute_infrastructure_shutdown(execution)
            elif input_data.operation_type == "canary_deployment":
                result = await self._execute_canary_deployment(
                    execution, input_data.parameters
                )
            else:
                result = await self._execute_generic_workflow(
                    execution, input_data.parameters
                )

            # Move to completed workflows
            if workflow_id in self._active_workflows:
                self._completed_workflows[workflow_id] = self._active_workflows.pop(
                    workflow_id
                )

            self._workflow_count += 1

            return ModelCanaryOrchestratorOutput(
                status="completed",
                workflow_result=result,
                execution_metrics=self._get_execution_metrics(execution),
            )

        except Exception as e:
            if workflow_id in self._active_workflows:
                self._active_workflows[workflow_id].status = WorkflowStatus.FAILED
                self._active_workflows[workflow_id].errors.append(str(e))
                self._completed_workflows[workflow_id] = self._active_workflows.pop(
                    workflow_id
                )

            return ModelCanaryOrchestratorOutput(
                status="failed",
                workflow_result={},
                error_message=str(e),
                execution_metrics={},
            )

    async def stop_workflow(self, workflow_id: str) -> ModelCanaryOrchestratorOutput:
        """
        Stop running workflow.

        Args:
            workflow_id: ID of workflow to stop

        Returns:
            ModelCanaryOrchestratorOutput with stop status
        """
        if workflow_id not in self._active_workflows:
            return ModelCanaryOrchestratorOutput(
                status="not_found",
                workflow_result={},
                error_message=f"Workflow {workflow_id} not found or not active",
            )

        execution = self._active_workflows[workflow_id]
        execution.status = WorkflowStatus.CANCELLED
        execution.end_time = asyncio.get_event_loop().time()

        self._completed_workflows[workflow_id] = self._active_workflows.pop(workflow_id)

        return ModelCanaryOrchestratorOutput(
            status="cancelled",
            workflow_result={"cancelled_at_step": execution.steps_completed},
            execution_metrics=self._get_execution_metrics(execution),
        )

    async def _execute_infrastructure_startup(
        self, execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute infrastructure startup workflow."""
        import time

        execution.start_time = time.time()
        execution.status = WorkflowStatus.RUNNING
        execution.total_steps = 3

        results = {}

        # Step 1: Consul health check
        await asyncio.sleep(0.1)
        execution.steps_completed = 1
        results["consul_health"] = {"status": "healthy", "leader": "localhost:8500"}

        # Step 2: Vault initialization
        await asyncio.sleep(0.2)
        execution.steps_completed = 2
        results["vault_init"] = {"status": "initialized", "sealed": False}

        # Step 3: Kafka cluster verify
        await asyncio.sleep(0.15)
        execution.steps_completed = 3
        results["kafka_cluster"] = {"status": "healthy", "brokers": 3}

        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = time.time()
        execution.results = results

        return results

    async def _execute_infrastructure_shutdown(
        self, execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute infrastructure shutdown workflow."""
        import time

        execution.start_time = time.time()
        execution.status = WorkflowStatus.RUNNING
        execution.total_steps = 3

        results = {}

        # Step 1: Drain Kafka queues
        await asyncio.sleep(0.3)
        execution.steps_completed = 1
        results["kafka_drain"] = {"status": "drained", "messages_processed": 150}

        # Step 2: Vault token revoke
        await asyncio.sleep(0.1)
        execution.steps_completed = 2
        results["vault_cleanup"] = {"status": "tokens_revoked", "count": 5}

        # Step 3: Consul deregister
        await asyncio.sleep(0.05)
        execution.steps_completed = 3
        results["consul_deregister"] = {"status": "deregistered", "services": 8}

        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = time.time()
        execution.results = results

        return results

    async def _execute_canary_deployment(
        self, execution: WorkflowExecution, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute canary deployment workflow."""
        import time

        execution.start_time = time.time()
        execution.status = WorkflowStatus.RUNNING
        execution.total_steps = 5

        results = {}
        service_name = parameters.get("service", "test-service")
        traffic_percentage = parameters.get("traffic_percentage", 10)

        # Step 1: Deploy canary version
        await asyncio.sleep(0.2)
        execution.steps_completed = 1
        results["canary_deploy"] = {
            "service": service_name,
            "version": "v2.1.0-canary",
            "status": "deployed",
        }

        # Step 2: Configure traffic split
        await asyncio.sleep(0.1)
        execution.steps_completed = 2
        results["traffic_split"] = {
            "canary_percentage": traffic_percentage,
            "stable_percentage": 100 - traffic_percentage,
            "status": "configured",
        }

        # Step 3: Health checks
        await asyncio.sleep(0.15)
        execution.steps_completed = 3
        results["health_checks"] = {
            "canary_health": "healthy",
            "stable_health": "healthy",
            "checks_passed": 12,
        }

        # Step 4: Metrics collection
        await asyncio.sleep(0.1)
        execution.steps_completed = 4
        results["metrics"] = {
            "error_rate": 0.01,
            "response_time_p99": 145,
            "success_rate": 99.99,
        }

        # Step 5: Promotion decision
        await asyncio.sleep(0.05)
        execution.steps_completed = 5
        results["promotion"] = {
            "decision": (
                "promote" if results["metrics"]["error_rate"] < 0.05 else "rollback"
            ),
            "reason": "metrics within acceptable thresholds",
        }

        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = time.time()
        execution.results = results

        return results

    async def _execute_generic_workflow(
        self, execution: WorkflowExecution, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a generic workflow."""
        import time

        execution.start_time = time.time()
        execution.status = WorkflowStatus.RUNNING
        execution.total_steps = 2

        # Step 1: Initialize
        await asyncio.sleep(0.05)
        execution.steps_completed = 1

        # Step 2: Process
        await asyncio.sleep(0.1)
        execution.steps_completed = 2

        execution.status = WorkflowStatus.COMPLETED
        execution.end_time = time.time()

        result = {
            "workflow_type": execution.workflow_type,
            "parameters": parameters,
            "status": "completed",
        }
        execution.results = result

        return result

    def _get_execution_metrics(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """Get execution metrics for a workflow."""
        if execution.start_time and execution.end_time:
            duration_ms = int((execution.end_time - execution.start_time) * 1000)
        else:
            duration_ms = 0

        return {
            "duration_ms": duration_ms,
            "steps_completed": execution.steps_completed,
            "total_steps": execution.total_steps,
            "status": execution.status.value,
            "error_count": len(execution.errors),
        }

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status."""
        # Check active workflows
        if workflow_id in self._active_workflows:
            execution = self._active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": execution.status.value,
                "progress": f"{execution.steps_completed}/{execution.total_steps}",
                "active": True,
            }

        # Check completed workflows
        if workflow_id in self._completed_workflows:
            execution = self._completed_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": execution.status.value,
                "progress": f"{execution.steps_completed}/{execution.total_steps}",
                "active": False,
                "results": execution.results,
            }

        return {"workflow_id": workflow_id, "status": "not_found"}

    async def list_workflows(self) -> Dict[str, Any]:
        """List all workflows."""
        active_workflows = [
            {
                "workflow_id": wf_id,
                "status": execution.status.value,
                "progress": f"{execution.steps_completed}/{execution.total_steps}",
            }
            for wf_id, execution in self._active_workflows.items()
        ]

        completed_workflows = [
            {"workflow_id": wf_id, "status": execution.status.value, "completed": True}
            for wf_id, execution in list(self._completed_workflows.items())[
                -10:
            ]  # Last 10
        ]

        return {
            "active_workflows": active_workflows,
            "recent_completed": completed_workflows,
            "total_executed": self._workflow_count,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Orchestrator health status."""
        return {
            "status": "healthy",
            "active_workflows": len(self._active_workflows),
            "total_workflows_executed": self._workflow_count,
            "node_type": "ORCHESTRATOR",
            "node_name": "canary_orchestrator",
        }
