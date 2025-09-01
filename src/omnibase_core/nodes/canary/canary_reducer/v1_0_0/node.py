#!/usr/bin/env python3
"""
Canary Reducer - State aggregation and HTTP service hosting for canary deployments.

This node aggregates state from other canary nodes and hosts HTTP services
for external access to the canary system.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.node_reducer import ModelReducerInput, ModelReducerOutput
from omnibase_core.core.node_reducer_service import NodeReducerService
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus


class ModelCanaryReducerInput(BaseModel):
    """Input model for canary reducer operations."""

    operation_type: str = Field(..., description="Type of reducer operation")
    state_data: dict[str, Any] = Field(
        default_factory=dict,
        description="State data to aggregate",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation parameters",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class ModelCanaryReducerOutput(BaseModel):
    """Output model for canary reducer operations."""

    aggregated_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated state data",
    )
    success: bool = Field(True, description="Whether operation succeeded")
    error_message: str | None = Field(None, description="Error message if failed")
    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class NodeCanaryReducer(NodeReducerService):
    """
    Canary Reducer Node - State aggregation and HTTP service hosting for canary deployments.

    This node aggregates state from other canary nodes and provides HTTP endpoints
    for external monitoring and control of the canary system.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize the Canary Reducer node."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0
        self.aggregated_states = {}

    async def reduce(
        self,
        reducer_input: ModelReducerInput,
    ) -> ModelReducerOutput:
        """
        Perform canary state reduction and aggregation.

        Args:
            reducer_input: Input data for reduction

        Returns:
            ModelReducerOutput: Result of the reduction
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())

        try:
            self.operation_count += 1

            # Parse input
            input_data = ModelCanaryReducerInput.model_validate(reducer_input.data)
            input_data.correlation_id = correlation_id

            self.logger.info(
                "Starting canary reduction: %s [correlation_id=%s]",
                input_data.operation_type,
                correlation_id,
            )

            # Execute the state reduction
            result = await self._execute_canary_reduction(input_data)

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create output
            output = ModelCanaryReducerOutput(
                aggregated_state=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            self.logger.info(
                "Canary reduction completed successfully "
                "[correlation_id=%s, duration=%sms]",
                correlation_id,
                execution_time,
            )

            return ModelReducerOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_reducer",
                    "execution_time_ms": execution_time,
                },
            )

        except Exception as e:
            self.error_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.exception(
                "Canary reduction failed: %s [correlation_id=%s, duration=%sms]",
                e,
                correlation_id,
                execution_time,
            )

            output = ModelCanaryReducerOutput(
                aggregated_state={},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            return ModelReducerOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_reducer",
                    "execution_time_ms": execution_time,
                    "error": True,
                },
            )

    async def _execute_canary_reduction(
        self,
        input_data: ModelCanaryReducerInput,
    ) -> dict[str, Any]:
        """
        Execute the specific canary reduction based on operation type.

        Args:
            input_data: Validated input data

        Returns:
            Dict containing aggregated state
        """
        operation_type = input_data.operation_type
        state_data = input_data.state_data
        parameters = input_data.parameters

        if operation_type == "aggregate_metrics":
            return await self._aggregate_metrics(state_data, parameters)
        if operation_type == "aggregate_health":
            return await self._aggregate_health_status(state_data, parameters)
        if operation_type == "aggregate_deployments":
            return await self._aggregate_deployment_state(state_data, parameters)
        if operation_type == "consolidate_logs":
            return await self._consolidate_logs(state_data, parameters)
        if operation_type == "status_summary":
            return await self._generate_status_summary(state_data, parameters)
        msg = f"Unsupported canary reduction operation: {operation_type}"
        raise ValueError(msg)

    async def _aggregate_metrics(
        self,
        state_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate performance metrics from canary nodes."""
        metric_types = parameters.get("metric_types", ["cpu", "memory", "requests"])

        # Simulate metric aggregation
        aggregated_metrics = {}
        for metric_type in metric_types:
            values = state_data.get(f"{metric_type}_values", [50.0, 45.0, 55.0])
            aggregated_metrics[metric_type] = {
                "average": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }

        # Store in aggregated state
        self.aggregated_states["metrics"] = aggregated_metrics

        return {
            "operation": "aggregate_metrics",
            "metrics": aggregated_metrics,
            "total_nodes": len(state_data),
            "aggregation_timestamp": datetime.now().isoformat(),
        }

    async def _aggregate_health_status(
        self,
        state_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate health status from all canary nodes."""
        nodes = state_data.get("nodes", [])

        health_summary = {
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "total": len(nodes),
        }

        node_statuses = []
        for node in nodes:
            status = node.get("health_status", "unknown")
            node_statuses.append(
                {
                    "node_id": node.get("node_id", "unknown"),
                    "node_type": node.get("node_type", "unknown"),
                    "status": status,
                    "last_check": node.get("last_check", datetime.now().isoformat()),
                },
            )

            if status in health_summary:
                health_summary[status] += 1

        overall_health = "healthy"
        if health_summary["unhealthy"] > 0:
            overall_health = "unhealthy"
        elif health_summary["degraded"] > 0:
            overall_health = "degraded"

        # Store in aggregated state
        self.aggregated_states["health"] = {
            "summary": health_summary,
            "overall": overall_health,
            "nodes": node_statuses,
        }

        return {
            "operation": "aggregate_health",
            "health_summary": health_summary,
            "overall_health": overall_health,
            "node_statuses": node_statuses,
        }

    async def _aggregate_deployment_state(
        self,
        state_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate deployment state across canary system."""
        deployments = state_data.get("deployments", [])

        deployment_summary = {
            "active": 0,
            "completed": 0,
            "failed": 0,
            "rolling_back": 0,
            "total": len(deployments),
        }

        deployment_details = []
        for deployment in deployments:
            status = deployment.get("status", "unknown")
            deployment_details.append(
                {
                    "deployment_id": deployment.get("deployment_id"),
                    "status": status,
                    "progress_percentage": deployment.get("progress", 0),
                    "started_at": deployment.get("started_at"),
                },
            )

            if status in deployment_summary:
                deployment_summary[status] += 1

        # Store in aggregated state
        self.aggregated_states["deployments"] = {
            "summary": deployment_summary,
            "deployments": deployment_details,
        }

        return {
            "operation": "aggregate_deployments",
            "deployment_summary": deployment_summary,
            "deployments": deployment_details,
            "aggregation_time": datetime.now().isoformat(),
        }

    async def _consolidate_logs(
        self,
        state_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Consolidate log entries from canary nodes."""
        log_level = parameters.get("level", "info")
        max_entries = parameters.get("max_entries", 100)

        log_entries = state_data.get("logs", [])
        filtered_logs = [
            log for log in log_entries if log.get("level", "info") == log_level
        ][:max_entries]

        log_stats = {
            "total_logs": len(log_entries),
            "filtered_count": len(filtered_logs),
            "filter_level": log_level,
            "timestamp": datetime.now().isoformat(),
        }

        # Store in aggregated state
        self.aggregated_states["logs"] = {
            "stats": log_stats,
            "entries": filtered_logs,
        }

        return {
            "operation": "consolidate_logs",
            "log_stats": log_stats,
            "log_entries": filtered_logs,
        }

    async def _generate_status_summary(
        self,
        state_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate overall status summary for canary system."""

        # Get current aggregated states
        metrics = self.aggregated_states.get("metrics", {})
        health = self.aggregated_states.get("health", {})
        deployments = self.aggregated_states.get("deployments", {})

        summary = {
            "system_status": health.get("overall", "unknown"),
            "active_deployments": deployments.get("summary", {}).get("active", 0),
            "healthy_nodes": health.get("summary", {}).get("healthy", 0),
            "total_nodes": health.get("summary", {}).get("total", 0),
            "last_updated": datetime.now().isoformat(),
            "uptime_hours": parameters.get("uptime_hours", 24),
        }

        return {
            "operation": "status_summary",
            "summary": summary,
            "detailed_metrics": metrics,
            "detailed_health": health,
            "detailed_deployments": deployments,
        }

    async def get_health_status(self) -> ModelHealthStatus:
        """Get the health status of the canary reducer node."""
        status = EnumHealthStatus.HEALTHY
        details = {
            "node_type": "canary_reducer",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "aggregated_states_count": len(self.aggregated_states),
        }

        # Mark as degraded if error rate is high
        if (
            self.operation_count > 10
            and (self.error_count / self.operation_count) > 0.1
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
            "node_type": "canary_reducer",
            "aggregated_states": list(self.aggregated_states.keys()),
        }

    def get_aggregated_state(self) -> dict[str, Any]:
        """Get the current aggregated state."""
        return self.aggregated_states.copy()
