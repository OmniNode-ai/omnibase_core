#!/usr/bin/env python3
"""
Canary Reducer - State aggregation and HTTP service hosting for canary deployments.

This node aggregates state from other canary nodes and hosts HTTP services
for external access to the canary system.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.node_reducer import ModelReducerInput, ModelReducerOutput
from omnibase_core.core.node_reducer_service import NodeReducerService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.nodes.canary.utils.circuit_breaker import (
    ModelCircuitBreakerConfig,
    get_circuit_breaker,
)
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler
from omnibase_core.nodes.canary.utils.metrics_collector import get_metrics_collector
from omnibase_core.utils.node_configuration_utils import UtilsNodeConfiguration


class ModelCanaryReducerInput(BaseModel):
    """Input model for canary reducer operations with enhanced validation."""

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
    timeout_ms: int | None = Field(
        None, description="Operation timeout in milliseconds"
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Reduction priority (1-10)"
    )

    @field_validator("operation_type")
    def validate_operation_type(cls, v):
        allowed_types = {
            "aggregate_metrics",
            "aggregate_health",
            "aggregate_deployments",
            "consolidate_logs",
            "status_summary",
        }
        if v not in allowed_types:
            raise ValueError(f"Invalid operation_type. Must be one of: {allowed_types}")
        return v

    @field_validator("correlation_id")
    def validate_correlation_id(cls, v):
        if v is not None and (len(v) < 8 or len(v) > 128):
            raise ValueError("correlation_id must be between 8-128 characters")
        return v


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

    def __init__(self, container: ModelONEXContainer):
        """Initialize the Canary Reducer node with production utilities."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize production utilities with container-based DI
        self.config_utils = UtilsNodeConfiguration(container)
        self.error_handler = get_error_handler(self.logger)
        self.metrics_collector = get_metrics_collector("canary_reducer")

        # Setup circuit breakers for external services
        # Use timeout from config_utils with fallback
        timeout_ms = self.config_utils.get_timeout_ms("circuit_breaker", 10000)
        cb_config = ModelCircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            timeout_seconds=timeout_ms / 1000,
        )
        self.aggregation_circuit_breaker = get_circuit_breaker(
            "state_aggregation", cb_config
        )
        self.health_circuit_breaker = get_circuit_breaker(
            "health_aggregation", cb_config
        )

        # State management and metrics tracking
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0
        self.aggregated_states = {}

    async def reduce(
        self,
        reducer_input: ModelReducerInput,
    ) -> ModelReducerOutput:
        """
        Perform canary state reduction and aggregation with comprehensive monitoring.

        Args:
            reducer_input: Input data for reduction

        Returns:
            ModelReducerOutput: Result of the reduction
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())
        operation_id = str(uuid.uuid4())

        # Start metrics collection
        await self.metrics_collector.record_operation_start(operation_id, "reduce")

        # Create error handling context
        context = self.error_handler.create_operation_context(
            "reduce",
            {
                "input_keys": (
                    list(reducer_input.data.keys()) if reducer_input.data else []
                )
            },
            correlation_id,
        )

        try:
            self.operation_count += 1

            # Parse and validate input
            input_data = ModelCanaryReducerInput.model_validate(reducer_input.data)
            input_data.correlation_id = correlation_id

            self.logger.info(
                "Starting canary reduction: %s [correlation_id=%s]",
                input_data.operation_type,
                correlation_id,
            )

            # Execute the state reduction with circuit breaker protection
            result = await self.aggregation_circuit_breaker.call(
                lambda: self._execute_canary_reduction(input_data),
                fallback=lambda: self._get_fallback_result(input_data.operation_type),
            )

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Record successful operation
            await self.metrics_collector.record_operation_end(
                operation_id, "reduce", True
            )
            self.metrics_collector.record_custom_metric(
                "reduction.execution_time",
                execution_time,
                "histogram",
                {"operation_type": input_data.operation_type},
            )

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

            # Handle error with secure error handler
            error_details = self.error_handler.handle_error(
                e, context, correlation_id, "reduce"
            )

            # Record failed operation
            await self.metrics_collector.record_operation_end(
                operation_id, "reduce", False, type(e).__name__
            )

            output = ModelCanaryReducerOutput(
                aggregated_state={},
                success=False,
                error_message=error_details["message"],
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
        # Log unsupported operation type for monitoring
        self.metrics_collector.increment_counter(
            "reduction.unsupported_type", {"operation_type": operation_type}
        )
        msg = f"Unsupported canary reduction operation: {operation_type}"
        raise ValueError(msg)

    async def _aggregate_metrics(
        self,
        state_data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate performance metrics from canary nodes with configuration-driven behavior."""
        metric_types = parameters.get("metric_types", ["cpu", "memory", "requests"])
        max_retention = int(
            self.config_utils.get_performance_setting("metrics_retention_count", 1000)
        )

        # Simulate metric aggregation delay only in debug mode
        debug_mode = bool(self.config_utils.get_security_setting("debug_mode", False))
        if debug_mode:
            delay_ms = float(
                self.config_utils.get_business_logic_setting(
                    "api_simulation_delay_ms", 100
                )
            )
            await asyncio.sleep(delay_ms / 1000 / 2)

        aggregated_metrics = {}
        for metric_type in metric_types:
            values = state_data.get(f"{metric_type}_values", [50.0, 45.0, 55.0])
            # Apply retention limits
            if len(values) > max_retention:
                values = values[-max_retention:]

            if values:  # Ensure we have data to aggregate
                aggregated_metrics[metric_type] = {
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "retention_applied": len(values) > max_retention,
                }

                # Record metric aggregation
                self.metrics_collector.record_custom_metric(
                    f"aggregation.{metric_type}.average",
                    aggregated_metrics[metric_type]["average"],
                    "gauge",
                    {"metric_type": metric_type},
                )
            else:
                aggregated_metrics[metric_type] = {
                    "average": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0,
                    "retention_applied": False,
                }

        # Store in aggregated state with timestamp
        self.aggregated_states["metrics"] = {
            "data": aggregated_metrics,
            "last_updated": datetime.now().isoformat(),
            "config_source": "environment",
        }

        # Record successful aggregation
        self.metrics_collector.increment_counter(
            "aggregation.metrics.completed", {"metrics_count": str(len(metric_types))}
        )

        return {
            "operation": "aggregate_metrics",
            "metrics": aggregated_metrics,
            "total_nodes": len(state_data),
            "aggregation_timestamp": datetime.now().isoformat(),
            "config_retention_limit": max_retention,
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
        max_entries = parameters.get(
            "max_entries",
            int(self.config_utils.get_performance_setting("cache_max_size", 1000)),
        )

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
        """Get the health status of the canary reducer node with comprehensive metrics."""
        # Use configuration for health thresholds
        error_rate_threshold = float(
            self.config_utils.get_performance_setting("error_rate_threshold", 0.1)
        )
        min_operations = int(
            self.config_utils.get_performance_setting("min_operations_for_health", 10)
        )

        status = EnumHealthStatus.HEALTHY

        # Get comprehensive metrics from metrics collector
        node_metrics = self.metrics_collector.get_node_metrics()

        details = {
            "node_type": "canary_reducer",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "aggregated_states_count": len(self.aggregated_states),
            "aggregated_state_keys": list(self.aggregated_states.keys()),
            "metrics_summary": node_metrics.model_dump(),
            "circuit_breakers": {
                "aggregation": self.aggregation_circuit_breaker.get_stats(),
                "health": self.health_circuit_breaker.get_stats(),
            },
            "config_loaded": True,
        }

        # Mark as degraded based on configurable thresholds
        if (
            self.operation_count >= min_operations
            and (self.error_count / self.operation_count) > error_rate_threshold
        ):
            status = EnumHealthStatus.DEGRADED

        return ModelHealthStatus(
            status=status,
            timestamp=datetime.now(),
            details=details,
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive performance and operational metrics."""
        node_metrics = self.metrics_collector.get_node_metrics()

        return {
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "node_type": "canary_reducer",
            "aggregated_states": list(self.aggregated_states.keys()),
            "detailed_metrics": node_metrics.model_dump(),
            "circuit_breaker_stats": {
                "aggregation": self.aggregation_circuit_breaker.get_stats(),
                "health": self.health_circuit_breaker.get_stats(),
            },
            "config_status": "loaded",
        }

    def _get_fallback_result(self, operation_type: str) -> dict[str, Any]:
        """Get fallback result when aggregation circuit breaker is open."""
        return {
            "operation": operation_type,
            "status": "fallback",
            "message": "Aggregation failed, using fallback response",
            "fallback_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "aggregated_state": {},
        }

    def get_aggregated_state(self) -> dict[str, Any]:
        """Get the current aggregated state."""
        return self.aggregated_states.copy()
