#!/usr/bin/env python3

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.node_effect import (
    EffectType,
    ModelEffectInput,
    ModelEffectOutput,
)
from omnibase_core.core.node_effect_service import NodeEffectService
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus


class ModelCanaryEffectInput(BaseModel):
    """Input model for canary effect operations."""

    operation_type: str = Field(..., description="Type of canary effect operation")
    target_system: str | None = Field(None, description="Target system for effect")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation parameters",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class ModelCanaryEffectOutput(BaseModel):
    """Output model for canary effect operations."""

    operation_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation result data",
    )
    success: bool = Field(True, description="Whether operation succeeded")
    error_message: str | None = Field(None, description="Error message if failed")
    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class NodeCanaryEffect(NodeEffectService):
    """
    Canary Effect Node - Generic external system interaction capabilities for canary deployments.

    This node handles external side effects in a controlled canary environment, providing
    monitoring, logging, and safe failure modes for testing new functionality.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize the Canary Effect node."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0

    async def perform_effect(
        self,
        effect_input: ModelEffectInput,
        effect_type: EffectType = EffectType.API_CALL,
    ) -> ModelEffectOutput:
        """
        Perform a canary effect operation with monitoring and safety controls.

        Args:
            effect_input: Input data for the effect operation
            effect_type: Type of effect to perform

        Returns:
            ModelEffectOutput: Result of the effect operation
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())

        try:
            self.operation_count += 1

            # Parse input
            input_data = ModelCanaryEffectInput.model_validate(effect_input.data)
            input_data.correlation_id = correlation_id

            self.logger.info(
                f"Starting canary effect operation: {input_data.operation_type} "
                f"[correlation_id={correlation_id}]",
            )

            # Perform the actual effect operation
            result = await self._execute_canary_operation(input_data, effect_type)

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create output
            output = ModelCanaryEffectOutput(
                operation_result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            self.logger.info(
                f"Canary effect operation completed successfully "
                f"[correlation_id={correlation_id}, duration={execution_time}ms]",
            )

            return ModelEffectOutput(
                data=output.model_dump(),
                metadata={
                    "effect_type": effect_type.value,
                    "node_type": "canary_effect",
                    "execution_time_ms": execution_time,
                },
            )

        except Exception as e:
            self.error_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.exception(
                f"Canary effect operation failed: {e!s} "
                f"[correlation_id={correlation_id}, duration={execution_time}ms]",
            )

            output = ModelCanaryEffectOutput(
                operation_result={},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            return ModelEffectOutput(
                data=output.model_dump(),
                metadata={
                    "effect_type": effect_type.value,
                    "node_type": "canary_effect",
                    "execution_time_ms": execution_time,
                    "error": True,
                },
            )

    async def _execute_canary_operation(
        self,
        input_data: ModelCanaryEffectInput,
        effect_type: EffectType,
    ) -> dict[str, Any]:
        """
        Execute the specific canary operation based on type.

        Args:
            input_data: Validated input data
            effect_type: Type of effect to perform

        Returns:
            Dict containing operation results
        """
        operation_type = input_data.operation_type
        parameters = input_data.parameters

        if operation_type == "health_check":
            return await self._perform_health_check(parameters)
        if operation_type == "external_api_call":
            return await self._perform_external_api_call(parameters)
        if operation_type == "file_system_operation":
            return await self._perform_file_system_operation(parameters)
        if operation_type == "database_operation":
            return await self._perform_database_operation(parameters)
        if operation_type == "message_queue_operation":
            return await self._perform_message_queue_operation(parameters)
        msg = f"Unsupported canary operation type: {operation_type}"
        raise ValueError(msg)

    async def _perform_health_check(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Perform health check operation."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
        }

    async def _perform_external_api_call(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate external API call for canary testing."""
        # Simulate API call delay
        await asyncio.sleep(0.1)

        return {
            "api_response": "simulated_response",
            "status_code": 200,
            "parameters_echoed": parameters,
        }

    async def _perform_file_system_operation(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform safe file system operations for canary testing."""
        operation = parameters.get("operation", "read")

        if operation == "read":
            return {"operation": "read", "result": "file_content_simulated"}
        if operation == "write":
            return {"operation": "write", "result": "write_successful_simulated"}
        msg = f"Unsupported file system operation: {operation}"
        raise ValueError(msg)

    async def _perform_database_operation(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate database operations for canary testing."""
        query_type = parameters.get("query_type", "select")

        return {
            "query_type": query_type,
            "result": f"database_{query_type}_simulated",
            "rows_affected": parameters.get("expected_rows", 1),
        }

    async def _perform_message_queue_operation(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate message queue operations for canary testing."""
        operation = parameters.get("operation", "publish")

        return {
            "operation": operation,
            "result": f"message_queue_{operation}_simulated",
            "message_id": str(uuid.uuid4()),
        }

    async def get_health_status(self) -> ModelHealthStatus:
        """Get the health status of the canary effect node."""
        status = EnumHealthStatus.HEALTHY
        details = {
            "node_type": "canary_effect",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
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
            "node_type": "canary_effect",
        }
