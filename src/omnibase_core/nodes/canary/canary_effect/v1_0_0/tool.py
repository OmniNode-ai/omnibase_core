"""
Canary Effect Node - External system interactions for canary deployments.

Enhanced EFFECT node with configuration management, error handling,
circuit breakers, and metrics collection for production readiness.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.node_base import ModelNodeBase
from omnibase_core.nodes.canary.config.canary_config import get_canary_config
from omnibase_core.nodes.canary.utils.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerException,
    get_circuit_breaker,
)
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler
from omnibase_core.nodes.canary.utils.metrics_collector import get_metrics_collector


class ModelCanaryEffectInput(BaseModel):
    """Input model for Canary Effect operations."""

    operation_type: str = Field(..., description="Type of effect operation to perform")
    target_system: Optional[str] = Field(
        default=None, description="Target system for effect operation"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Operation-specific parameters"
    )
    correlation_id: Optional[str] = Field(
        default=None, description="Request correlation ID"
    )

    @field_validator("operation_type")
    def validate_operation_type(cls, v):
        """Validate operation type against allowed values."""
        allowed_operations = {
            "health_check",
            "external_api_call",
            "file_system_operation",
            "database_operation",
            "message_queue_operation",
            "canary_deployment",
            "traffic_routing",
            "rollback_operation",
            "monitoring_alert",
        }
        if v not in allowed_operations:
            raise ValueError(
                f"Invalid operation_type: {v}. Must be one of {allowed_operations}"
            )
        return v

    @field_validator("correlation_id")
    def validate_correlation_id(cls, v):
        """Validate correlation ID format if provided."""
        if v is not None:
            if not isinstance(v, str):
                raise ValueError("correlation_id must be a string")
            if len(v) < 8 or len(v) > 128:
                raise ValueError("correlation_id must be between 8 and 128 characters")
            if not v.replace("-", "").replace("_", "").isalnum():
                raise ValueError(
                    "correlation_id must contain only alphanumeric characters, hyphens, and underscores"
                )
        return v


class ModelCanaryEffectOutput(BaseModel):
    """Output model for Canary Effect operations."""

    operation_result: Dict[str, Any] = Field(
        default_factory=dict, description="Result data from the effect operation"
    )
    success: bool = Field(default=True, description="Whether operation succeeded")
    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )
    execution_time_ms: int = Field(
        default=0, description="Execution time in milliseconds"
    )
    correlation_id: Optional[str] = Field(
        default=None, description="Request correlation ID"
    )


class NodeCanaryEffect(ModelNodeBase):
    """
    Enhanced Canary Effect Node - External system interactions with production features.

    Production-ready EFFECT node with configuration management, error handling,
    circuit breakers, metrics collection, and comprehensive monitoring.
    """

    def __init__(self, contract_path=None, *args, **kwargs):
        from pathlib import Path

        # Use default contract path if not provided
        if contract_path is None:
            contract_path = Path(__file__).parent / "contract.yaml"

        super().__init__(contract_path=contract_path, *args, **kwargs)

        # Initialize configuration and utilities
        self.config = get_canary_config()
        self.error_handler = get_error_handler()
        self.metrics_collector = get_metrics_collector("canary_effect")

        # Setup circuit breakers for different external services
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            timeout_seconds=self.config.timeouts.api_call_timeout_ms / 1000,
        )
        self.api_circuit_breaker = get_circuit_breaker("external_api", cb_config)
        self.db_circuit_breaker = get_circuit_breaker("database", cb_config)
        self.file_circuit_breaker = get_circuit_breaker("filesystem", cb_config)

        # Legacy compatibility
        self._operations_count = 0
        self._mock_data = {}

    async def perform_effect(
        self, input_data: ModelCanaryEffectInput
    ) -> ModelCanaryEffectOutput:
        """
        Perform an effect operation with comprehensive monitoring and error handling.

        Args:
            input_data: Input data for the effect operation

        Returns:
            ModelCanaryEffectOutput with operation result
        """
        # Generate operation ID for tracking
        operation_id = str(uuid.uuid4())
        correlation_id = input_data.correlation_id or str(uuid.uuid4())

        # Validate correlation_id if provided
        if (
            input_data.correlation_id
            and not self.error_handler.validate_correlation_id(correlation_id)
        ):
            raise ValueError("Invalid correlation_id format")

        # Record operation start for metrics
        await self.metrics_collector.record_operation_start(
            operation_id, input_data.operation_type
        )

        # Create operation context for error handling
        operation_context = self.error_handler.create_operation_context(
            operation_name=f"effect_{input_data.operation_type}",
            input_data=input_data.model_dump(),
            correlation_id=correlation_id,
        )

        try:
            # Route to appropriate effect operation with circuit breaker protection
            if input_data.operation_type == "health_check":
                result = await self._perform_health_check(input_data.parameters)
            elif input_data.operation_type == "external_api_call":
                result = await self.api_circuit_breaker.call(
                    lambda: self._simulate_api_call(input_data.parameters),
                    fallback=lambda: {"status": "unavailable", "fallback": True},
                )
            elif input_data.operation_type == "file_system_operation":
                result = await self.file_circuit_breaker.call(
                    lambda: self._simulate_file_operation(input_data.parameters),
                    fallback=lambda: {"status": "unavailable", "fallback": True},
                )
            elif input_data.operation_type == "database_operation":
                result = await self.db_circuit_breaker.call(
                    lambda: self._simulate_database_operation(input_data.parameters),
                    fallback=lambda: {"status": "unavailable", "fallback": True},
                )
            elif input_data.operation_type == "message_queue_operation":
                result = await self._simulate_message_queue_operation(
                    input_data.parameters
                )
            else:
                result = {
                    "message": f"Performed {input_data.operation_type}",
                    "target": input_data.target_system,
                    "parameters": input_data.parameters,
                }

            # Record successful operation
            execution_time = await self.metrics_collector.record_operation_end(
                operation_id, input_data.operation_type, True
            )

            # Record custom metrics
            self.metrics_collector.record_custom_metric(
                "effect.operations.total",
                1,
                "counter",
                {"operation_type": input_data.operation_type, "success": "true"},
            )

            self._operations_count += 1

            return ModelCanaryEffectOutput(
                operation_result=result,
                success=True,
                execution_time_ms=int(execution_time),
                correlation_id=correlation_id,
            )

        except CircuitBreakerException as e:
            # Handle circuit breaker failures
            execution_time = await self.metrics_collector.record_operation_end(
                operation_id, input_data.operation_type, False, "circuit_breaker_open"
            )

            self.metrics_collector.increment_counter(
                "effect.circuit_breaker.trips",
                {"service": e.service_name, "operation": input_data.operation_type},
            )

            error_info = self.error_handler.handle_error(
                error=e,
                context=operation_context,
                correlation_id=correlation_id,
                operation_name="effect_operation",
            )

            return ModelCanaryEffectOutput(
                operation_result={
                    "circuit_breaker_open": True,
                    "service": e.service_name,
                },
                success=False,
                error_message=error_info["message"],
                execution_time_ms=int(execution_time),
                correlation_id=correlation_id,
            )

        except Exception as e:
            # Handle general exceptions with enhanced error handling
            execution_time = await self.metrics_collector.record_operation_end(
                operation_id, input_data.operation_type, False, type(e).__name__
            )

            error_info = self.error_handler.handle_error(
                error=e,
                context=operation_context,
                correlation_id=correlation_id,
                operation_name="effect_operation",
            )

            self.metrics_collector.record_custom_metric(
                "effect.operations.errors",
                1,
                "counter",
                {
                    "operation_type": input_data.operation_type,
                    "error_type": type(e).__name__,
                },
            )

            return ModelCanaryEffectOutput(
                operation_result={"error_id": error_info["error_id"]},
                success=False,
                error_message=error_info["message"],
                execution_time_ms=int(execution_time),
                correlation_id=correlation_id,
            )

    async def _perform_health_check(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check operation with configurable delay."""
        # Use configurable delay instead of hardcoded value
        delay_ms = self.config.business_logic.api_simulation_delay_ms
        await asyncio.sleep(delay_ms / 1000)

        return {
            "status": "healthy",
            "checks": {"connectivity": "ok", "resources": "ok", "dependencies": "ok"},
            "timestamp": "2025-09-01T15:00:00Z",
        }

    async def _simulate_api_call(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate external API call."""
        # Simulate API call delay
        await asyncio.sleep(0.2)

        endpoint = parameters.get("endpoint", "/api/test")
        method = parameters.get("method", "GET")

        # Mock response based on endpoint
        mock_responses = {
            "/api/users": {"users": [{"id": 1, "name": "Test User"}]},
            "/api/status": {"status": "ok", "version": "1.0.0"},
            "/api/data": {"data": list(range(10)), "count": 10},
        }

        response_data = mock_responses.get(endpoint, {"message": "Mock API response"})

        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": 200,
            "response": response_data,
            "headers": {"content-type": "application/json"},
        }

    async def _simulate_file_operation(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate file system operation."""
        operation = parameters.get("operation", "read")
        file_path = parameters.get("file_path", "/tmp/test.txt")

        # Simulate file operation delay
        await asyncio.sleep(0.05)

        if operation == "read":
            # Store mock data for consistency
            if file_path not in self._mock_data:
                self._mock_data[file_path] = f"Mock file content for {file_path}"

            return {
                "operation": "read",
                "file_path": file_path,
                "content": self._mock_data[file_path],
                "size_bytes": len(self._mock_data[file_path]),
            }

        elif operation == "write":
            content = parameters.get("content", "Mock content")
            self._mock_data[file_path] = content

            return {
                "operation": "write",
                "file_path": file_path,
                "bytes_written": len(content),
                "status": "success",
            }

        return {"operation": operation, "file_path": file_path, "status": "completed"}

    async def _simulate_database_operation(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate database operation."""
        # Simulate database delay
        await asyncio.sleep(0.15)

        query = parameters.get("query", "SELECT 1")
        operation = parameters.get("operation", "select")

        return {
            "operation": operation,
            "query": query,
            "rows_affected": 1 if operation in ["insert", "update", "delete"] else 0,
            "result_count": 1 if operation == "select" else 0,
            "execution_time_ms": 150,
        }

    async def _simulate_message_queue_operation(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate message queue operation."""
        # Simulate queue operation delay
        await asyncio.sleep(0.05)

        operation = parameters.get("operation", "publish")
        topic = parameters.get("topic", "canary.test")
        message = parameters.get("message", {"test": "data"})

        return {
            "operation": operation,
            "topic": topic,
            "message": message,
            "message_id": f"msg_{self._operations_count}",
            "status": "success",
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check canary effect node health."""
        return {
            "status": "healthy",
            "operations_count": self._operations_count,
            "node_type": "EFFECT",
            "node_name": "canary_effect",
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance and operational metrics."""
        return {
            "operations_processed": self._operations_count,
            "mock_data_entries": len(self._mock_data),
            "node_type": "EFFECT",
            "status": "active",
        }
