#!/usr/bin/env python3
"""
Canary Orchestrator - Workflow coordination for canary deployments.

This node orchestrates workflows in a controlled canary environment, providing
event-driven coordination and workflow management for testing new deployments.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.node_orchestrator import (
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
)
from omnibase_core.core.node_orchestrator_service import NodeOrchestratorService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.node import EnumHealthStatus
from omnibase_core.models.core.model_health_status import ModelHealthStatus
from omnibase_core.nodes.canary.utils.circuit_breaker import (
    ModelCircuitBreakerConfig,
    get_circuit_breaker,
)
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler
from omnibase_core.nodes.canary.utils.metrics_collector import get_metrics_collector
from omnibase_core.utils.node_configuration_utils import UtilsNodeConfiguration


class ModelCanaryOrchestratorInput(BaseModel):
    """Input model for canary orchestrator operations with enhanced validation."""

    workflow_type: str = Field(..., description="Type of workflow to orchestrate")
    workflow_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow execution data",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Orchestration parameters",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")
    timeout_ms: int | None = Field(
        None,
        description="Operation timeout in milliseconds",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Workflow priority (1-10)",
    )

    @field_validator("workflow_type")
    def validate_workflow_type(cls, v):
        allowed_types = {
            "deployment_workflow",
            "testing_workflow",
            "rollback_workflow",
            "health_check_workflow",
            "monitoring_workflow",
        }
        if v not in allowed_types:
            raise ValueError(f"Invalid workflow_type. Must be one of: {allowed_types}")
        return v

    @field_validator("correlation_id")
    def validate_correlation_id(cls, v):
        if v is not None and (len(v) < 8 or len(v) > 128):
            raise ValueError("correlation_id must be between 8-128 characters")
        return v


class ModelCanaryOrchestratorOutput(BaseModel):
    """Output model for canary orchestrator operations."""

    orchestration_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Orchestration result data",
    )
    success: bool = Field(True, description="Whether orchestration succeeded")
    error_message: str | None = Field(None, description="Error message if failed")
    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class NodeCanaryOrchestrator(NodeOrchestratorService):
    """
    Canary Orchestrator Node - Workflow coordination for canary deployments.

    This node orchestrates workflows through event-driven coordination,
    providing safe workflow management for testing new deployment patterns.
    """

    def __init__(self, container: ModelONEXContainer):
        """Initialize the Canary Orchestrator node with production utilities."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize production utilities with container-based DI
        self.config_utils = UtilsNodeConfiguration(container)
        self.error_handler = get_error_handler(self.logger)
        self.metrics_collector = get_metrics_collector("canary_orchestrator")

        # Setup circuit breakers for external services
        # Use timeout from config_utils with fallback
        timeout_ms = self.config_utils.get_timeout_ms("workflow_step", 30000)
        cb_config = ModelCircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            timeout_seconds=timeout_ms / 1000,
        )
        self.workflow_circuit_breaker = get_circuit_breaker(
            "workflow_execution",
            cb_config,
        )
        self.health_circuit_breaker = get_circuit_breaker("health_check", cb_config)

        # Metrics tracking (kept for current standards, enhanced with metrics_collector)
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0

    async def orchestrate(
        self,
        orchestrator_input: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Perform canary workflow orchestration.

        Args:
            orchestrator_input: Input data for orchestration

        Returns:
            ModelOrchestratorOutput: Result of the orchestration
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())

        # Create error handling context
        context = self.error_handler.create_operation_context(
            "orchestrate",
            {
                "input_keys": (
                    list(orchestrator_input.data.keys())
                    if orchestrator_input.data
                    else []
                ),
            },
            correlation_id,
        )

        try:
            self.operation_count += 1

            # Parse input
            input_data = ModelCanaryOrchestratorInput.model_validate(
                orchestrator_input.data,
            )
            input_data.correlation_id = correlation_id

            self.logger.info(
                "Starting canary orchestration: %s [correlation_id=%s]",
                input_data.workflow_type,
                correlation_id,
            )

            # Execute the workflow orchestration
            result = await self._execute_canary_orchestration(input_data)

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create output
            output = ModelCanaryOrchestratorOutput(
                orchestration_result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            self.logger.info(
                "Canary orchestration completed successfully "
                "[correlation_id=%s, duration=%sms]",
                correlation_id,
                execution_time,
            )

            return ModelOrchestratorOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_orchestrator",
                    "execution_time_ms": execution_time,
                },
            )

        except Exception as e:
            self.error_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Handle error with secure error handler
            error_details = self.error_handler.handle_error(
                e,
                context,
                correlation_id,
                "orchestrate",
            )

            output = ModelCanaryOrchestratorOutput(
                orchestration_result={},
                success=False,
                error_message=error_details["message"],
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            return ModelOrchestratorOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_orchestrator",
                    "execution_time_ms": execution_time,
                    "error": True,
                },
            )

    async def _execute_canary_orchestration(
        self,
        input_data: ModelCanaryOrchestratorInput,
    ) -> dict[str, Any]:
        """
        Execute the specific canary orchestration based on workflow type.

        Args:
            input_data: Validated input data

        Returns:
            Dict containing orchestration results
        """
        workflow_type = input_data.workflow_type
        workflow_payload = input_data.workflow_payload
        parameters = input_data.parameters

        if workflow_type == "deployment_workflow":
            return await self._orchestrate_deployment(workflow_payload, parameters)
        if workflow_type == "testing_workflow":
            return await self._orchestrate_testing(workflow_payload, parameters)
        if workflow_type == "rollback_workflow":
            return await self._orchestrate_rollback(workflow_payload, parameters)
        if workflow_type == "health_check_workflow":
            return await self._orchestrate_health_checks(workflow_payload, parameters)
        if workflow_type == "monitoring_workflow":
            return await self._orchestrate_monitoring(workflow_payload, parameters)
        msg = f"Unsupported canary workflow type: {workflow_type}"
        raise ValueError(msg)

    async def _orchestrate_deployment(
        self,
        payload: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Orchestrate canary deployment workflow."""
        deployment_strategy = parameters.get("strategy", "blue_green")
        target_percentage = parameters.get("target_percentage", 10)

        # Simulate deployment orchestration steps
        steps = [
            {"step": "validate_config", "status": "completed", "duration_ms": 100},
            {"step": "prepare_canary", "status": "completed", "duration_ms": 250},
            {"step": "deploy_canary", "status": "completed", "duration_ms": 500},
            {"step": "configure_traffic", "status": "completed", "duration_ms": 150},
        ]

        return {
            "workflow": "deployment_workflow",
            "strategy": deployment_strategy,
            "target_percentage": target_percentage,
            "steps_completed": len(steps),
            "steps": steps,
            "deployment_id": str(uuid.uuid4()),
            "status": "deployed",
        }

    async def _orchestrate_testing(
        self,
        payload: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Orchestrate canary testing workflow."""
        test_types = parameters.get("test_types", ["smoke", "integration"])
        test_duration = parameters.get("duration_minutes", 15)

        # Simulate testing orchestration
        test_results = []
        for test_type in test_types:
            test_results.append(
                {
                    "test_type": test_type,
                    "status": "passed",
                    "duration_ms": 200 + len(test_type) * 10,
                    "test_id": str(uuid.uuid4()),
                },
            )

        return {
            "workflow": "testing_workflow",
            "test_types": test_types,
            "duration_minutes": test_duration,
            "tests_executed": len(test_results),
            "test_results": test_results,
            "overall_status": "passed",
        }

    async def _orchestrate_rollback(
        self,
        payload: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Orchestrate canary rollback workflow."""
        rollback_reason = parameters.get("reason", "manual_trigger")
        preserve_logs = parameters.get("preserve_logs", True)

        # Simulate rollback orchestration steps
        rollback_steps = [
            {"step": "stop_traffic", "status": "completed", "duration_ms": 50},
            {"step": "drain_connections", "status": "completed", "duration_ms": 200},
            {"step": "restore_previous", "status": "completed", "duration_ms": 300},
            {"step": "verify_rollback", "status": "completed", "duration_ms": 150},
        ]

        return {
            "workflow": "rollback_workflow",
            "reason": rollback_reason,
            "preserve_logs": preserve_logs,
            "rollback_steps": rollback_steps,
            "rollback_id": str(uuid.uuid4()),
            "status": "rolled_back",
        }

    async def _orchestrate_health_checks(
        self,
        payload: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Orchestrate health check workflow."""
        check_interval = parameters.get("interval_seconds", 30)
        check_timeout = parameters.get("timeout_seconds", 5)

        # Simulate health check orchestration
        health_checks = [
            {"service": "canary_api", "status": "healthy", "response_time": 45},
            {"service": "canary_db", "status": "healthy", "response_time": 12},
            {"service": "canary_cache", "status": "healthy", "response_time": 8},
        ]

        return {
            "workflow": "health_check_workflow",
            "interval_seconds": check_interval,
            "timeout_seconds": check_timeout,
            "checks_performed": len(health_checks),
            "health_checks": health_checks,
            "overall_health": "healthy",
        }

    async def _orchestrate_monitoring(
        self,
        payload: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Orchestrate monitoring workflow."""
        metrics_to_monitor = parameters.get("metrics", ["cpu", "memory", "requests"])
        alert_thresholds = parameters.get("thresholds", {})

        # Simulate monitoring orchestration
        monitoring_setup = []
        for metric in metrics_to_monitor:
            threshold = alert_thresholds.get(metric, "default")
            monitoring_setup.append(
                {
                    "metric": metric,
                    "threshold": threshold,
                    "status": "active",
                    "monitor_id": str(uuid.uuid4()),
                },
            )

        return {
            "workflow": "monitoring_workflow",
            "metrics_count": len(metrics_to_monitor),
            "monitoring_setup": monitoring_setup,
            "alerting_enabled": len(alert_thresholds) > 0,
            "status": "monitoring_active",
        }

    async def get_health_status(self) -> ModelHealthStatus:
        """Get the health status of the canary orchestrator node."""
        status = EnumHealthStatus.HEALTHY
        details = {
            "node_type": "canary_orchestrator",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
        }

        # Mark as degraded if error rate is high (using configurable thresholds)
        min_operations = int(
            self.config_utils.get_performance_config("min_operations_for_health", 10),
        )
        error_rate_threshold = float(
            self.config_utils.get_performance_config("error_rate_threshold", 0.1),
        )
        if (
            self.operation_count > min_operations
            and (self.error_count / self.operation_count) > error_rate_threshold
        ):
            status = EnumHealthStatus.DEGRADED

        return ModelHealthStatus(
            status=status,
            timestamp=datetime.now(),
            details=details,
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get performance and operational metrics."""
        return {
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "node_type": "canary_orchestrator",
        }
