"""
Canary Effect Node - External system interactions for canary deployments.

Simple EFFECT node implementation for testing and validation purposes.
"""

import asyncio
import json
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from omnibase_core.core.node_base import ModelNodeBase


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
    Canary Effect Node - External system interactions for canary deployments.

    Simple EFFECT node that performs basic external operations like file system
    access, API calls simulation, and health checks for testing purposes.
    """

    def __init__(self, contract_path=None, *args, **kwargs):
        from pathlib import Path

        # Use default contract path if not provided
        if contract_path is None:
            contract_path = Path(__file__).parent / "contract.yaml"

        super().__init__(contract_path=contract_path, *args, **kwargs)
        self._operations_count = 0
        self._mock_data = {}

    async def perform_effect(
        self, input_data: ModelCanaryEffectInput
    ) -> ModelCanaryEffectOutput:
        """
        Perform an effect operation with monitoring.

        Args:
            input_data: Input data for the effect operation

        Returns:
            ModelCanaryEffectOutput with operation result
        """
        import time

        start_time = time.time()

        try:
            result = {}

            # Route to appropriate effect operation
            if input_data.operation_type == "health_check":
                result = await self._perform_health_check(input_data.parameters)
            elif input_data.operation_type == "external_api_call":
                result = await self._simulate_api_call(input_data.parameters)
            elif input_data.operation_type == "file_system_operation":
                result = await self._simulate_file_operation(input_data.parameters)
            elif input_data.operation_type == "database_operation":
                result = await self._simulate_database_operation(input_data.parameters)
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

            self._operations_count += 1
            execution_time = int((time.time() - start_time) * 1000)

            return ModelCanaryEffectOutput(
                operation_result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=input_data.correlation_id,
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return ModelCanaryEffectOutput(
                operation_result={},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                correlation_id=input_data.correlation_id,
            )

    async def _perform_health_check(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check operation."""
        # Simulate health check delay
        await asyncio.sleep(0.1)

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
