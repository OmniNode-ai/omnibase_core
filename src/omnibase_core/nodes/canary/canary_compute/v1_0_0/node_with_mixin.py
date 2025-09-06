#!/usr/bin/env python3
"""
Canary Compute - Business logic processing with error handling mixin.

This demonstrates how to use the error handling mixin instead of manual
error handling code duplication. The mixin provides secure error handling,
circuit breakers, metrics collection, and configuration management.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.node_compute import ModelComputeInput, ModelComputeOutput
from omnibase_core.core.node_compute_service import NodeComputeService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.model.subcontracts.model_error_handling_subcontract import (
    GetConfigurationInput,
    HandleErrorInput,
    ModelErrorHandlingSubcontract,
    RecordMetricsInput,
)
from omnibase_core.utils.node_configuration_utils import UtilsNodeConfiguration


class ModelCanaryComputeInput(BaseModel):
    """Input model for canary compute operations."""

    operation_type: str = Field(..., description="Type of compute operation")
    data_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for computation",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation parameters",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")

    @field_validator("operation_type")
    def validate_operation_type(cls, v):
        """Validate operation type against allowed values."""
        allowed_operations = {
            "add",
            "multiply",
            "aggregate",
            "customer_score",
            "risk_assessment",
            "data_transformation",
            "health_metrics",
            "statistical_analysis",
        }
        if v not in allowed_operations:
            raise ValueError(
                f"Invalid operation_type. Must be one of: {allowed_operations}"
            )
        return v


class ModelCanaryComputeOutput(BaseModel):
    """Output model for canary compute operations."""

    computation_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Computation result data",
    )
    success: bool = Field(True, description="Whether computation succeeded")
    error_message: str | None = Field(None, description="Error message if failed")
    execution_time_ms: int | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(None, description="Request correlation ID")


class NodeCanaryComputeWithMixin(NodeComputeService):
    """
    Canary Compute Node with Error Handling Mixin.

    This demonstrates the clean approach using the error handling mixin
    instead of manually duplicating error handling code across nodes.
    """

    def __init__(self, container: ModelONEXContainer):
        """Initialize the Canary Compute node with mixin capabilities."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_utils = UtilsNodeConfiguration(container)

        # Initialize error handling mixin (replaces manual utilities)
        self.error_handling = ModelErrorHandlingSubcontract(
            initialized=True, initialization_timestamp=datetime.now(timezone.utc)
        )

        # Basic counters (metrics will be handled by mixin)
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0

    async def compute(
        self,
        compute_input: ModelComputeInput,
    ) -> ModelComputeOutput:
        """
        Perform a canary computation operation using mixin capabilities.

        Args:
            compute_input: Input data for the computation

        Returns:
            ModelComputeOutput: Result of the computation
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())

        # Create operation context for mixin
        context = {
            "operation": "compute",
            "input_keys": list(compute_input.data.keys()) if compute_input.data else [],
            "node_type": "COMPUTE",
        }

        try:
            self.operation_count += 1

            # Parse and validate input using mixin validation
            input_data = ModelCanaryComputeInput.model_validate(compute_input.data)
            input_data.correlation_id = correlation_id

            self.logger.info(
                "Starting canary computation: %s [correlation_id=%s]",
                input_data.operation_type,
                correlation_id,
            )

            # Execute computation
            result = await self._execute_canary_computation(input_data)

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Record metrics using mixin
            await self._record_operation_metrics(
                input_data.operation_type, True, execution_time, context
            )

            # Create output
            output = ModelCanaryComputeOutput(
                computation_result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            self.logger.info(
                "Canary computation completed successfully "
                "[correlation_id=%s, duration=%sms]",
                correlation_id,
                execution_time,
            )

            return ModelComputeOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_compute",
                    "execution_time_ms": execution_time,
                },
            )

        except Exception as e:
            self.error_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Handle error using mixin instead of manual error handler
            error_details = await self._handle_error_with_mixin(
                e, context, correlation_id, "compute"
            )

            # Record error metrics using mixin
            await self._record_operation_metrics(
                input_data.operation_type if "input_data" in locals() else "unknown",
                False,
                execution_time,
                context,
            )

            output = ModelCanaryComputeOutput(
                computation_result={},
                success=False,
                error_message=error_details["message"],
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            return ModelComputeOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_compute",
                    "execution_time_ms": execution_time,
                    "error": True,
                },
            )

    async def _handle_error_with_mixin(
        self,
        error: Exception,
        context: dict[str, Any],
        correlation_id: str,
        operation_name: str,
    ) -> dict[str, Any]:
        """Handle error using mixin capabilities."""
        # Validate input using mixin model
        error_input = HandleErrorInput(
            error=error,
            context=context,
            correlation_id=correlation_id,
            operation_name=operation_name,
        )

        # In a real implementation, this would call the mixin's handle_error action
        # For now, we simulate the secure error handling behavior
        safe_message = f"Computation operation '{operation_name}' failed"
        if not self.error_handling.error_handling.sanitize_production_errors:
            safe_message += f": {type(error).__name__}"

        return {
            "message": safe_message,
            "error_id": str(uuid.uuid4()),
            "safe_context": {
                k: v
                for k, v in context.items()
                if k not in ["sensitive_data", "credentials"]
            },
            "correlation_id": correlation_id,
        }

    async def _record_operation_metrics(
        self,
        operation_name: str,
        success: bool,
        duration_ms: int,
        metadata: dict[str, Any],
    ) -> None:
        """Record operation metrics using mixin capabilities."""
        # Validate input using mixin model
        metrics_input = RecordMetricsInput(
            operation_name=operation_name,
            success=success,
            duration_ms=duration_ms,
            metadata=metadata,
        )

        # In a real implementation, this would call the mixin's record_metrics action
        # For now, we simulate the metrics recording
        self.logger.debug(
            "Recording metrics: operation=%s, success=%s, duration=%sms",
            operation_name,
            success,
            duration_ms,
        )

    async def _execute_canary_computation(
        self,
        input_data: ModelCanaryComputeInput,
    ) -> dict[str, Any]:
        """
        Execute the specific canary computation based on operation type.

        Args:
            input_data: Validated input data

        Returns:
            Dict containing computation results
        """
        operation_type = input_data.operation_type
        data_payload = input_data.data_payload
        parameters = input_data.parameters

        if operation_type == "add":
            return await self._compute_add(data_payload, parameters)
        elif operation_type == "multiply":
            return await self._compute_multiply(data_payload, parameters)
        elif operation_type == "aggregate":
            return await self._compute_aggregate(data_payload, parameters)
        elif operation_type == "customer_score":
            return await self._compute_customer_score(data_payload, parameters)
        elif operation_type == "risk_assessment":
            return await self._compute_risk_assessment(data_payload, parameters)
        elif operation_type == "data_transformation":
            return await self._compute_data_transformation(data_payload, parameters)
        elif operation_type == "health_metrics":
            return await self._compute_health_metrics(data_payload, parameters)
        elif operation_type == "statistical_analysis":
            return await self._compute_statistical_analysis(data_payload, parameters)
        else:
            msg = f"Unsupported canary compute operation: {operation_type}"
            raise ValueError(msg)

    async def _compute_add(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute addition operation."""
        num1 = payload.get("num1", 0)
        num2 = payload.get("num2", 0)
        result = num1 + num2
        return {
            "operation": "add",
            "inputs": {"num1": num1, "num2": num2},
            "result": result,
            "computation_type": "arithmetic",
        }

    async def _compute_multiply(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute multiplication operation."""
        num1 = payload.get("num1", 1)
        num2 = payload.get("num2", 1)
        result = num1 * num2
        return {
            "operation": "multiply",
            "inputs": {"num1": num1, "num2": num2},
            "result": result,
            "computation_type": "arithmetic",
        }

    async def _compute_aggregate(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute data aggregation."""
        data_list = payload.get("data", [])
        aggregation_type = parameters.get("type", "sum")

        if aggregation_type == "sum":
            result = sum(data_list) if data_list else 0
        elif aggregation_type == "avg":
            result = sum(data_list) / len(data_list) if data_list else 0
        elif aggregation_type == "max":
            result = max(data_list) if data_list else 0
        elif aggregation_type == "min":
            result = min(data_list) if data_list else 0
        else:
            result = len(data_list)

        return {
            "operation": "aggregate",
            "aggregation_type": aggregation_type,
            "input_count": len(data_list),
            "result": result,
            "computation_type": "statistical",
        }

    async def _compute_customer_score(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute customer scoring."""
        customer_data = payload.get("customer", {})
        score_factors = parameters.get("factors", ["age", "income", "history"])

        base_score = 100
        for factor in score_factors:
            factor_value = customer_data.get(factor, 0)
            base_score += factor_value * 0.1

        return {
            "operation": "customer_score",
            "customer_id": customer_data.get("id", "unknown"),
            "score": round(base_score, 2),
            "factors_used": score_factors,
            "computation_type": "business_logic",
        }

    async def _compute_risk_assessment(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute risk assessment."""
        risk_data = payload.get("risk_factors", {})
        threshold = parameters.get("threshold", 50)

        risk_score = sum(risk_data.values()) / len(risk_data) if risk_data else 0
        risk_level = "high" if risk_score > threshold else "low"

        return {
            "operation": "risk_assessment",
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "threshold": threshold,
            "factors_count": len(risk_data),
            "computation_type": "business_logic",
        }

    async def _compute_data_transformation(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute data transformation."""
        input_data = payload.get("data", [])
        transform_type = parameters.get("transform", "normalize")

        if transform_type == "normalize" and input_data:
            max_val = max(input_data)
            min_val = min(input_data)
            range_val = max_val - min_val if max_val != min_val else 1
            transformed = [(x - min_val) / range_val for x in input_data]
        else:
            transformed = input_data

        return {
            "operation": "data_transformation",
            "transform_type": transform_type,
            "input_count": len(input_data),
            "output_count": len(transformed),
            "transformed_data": transformed[:10],  # Limit output size
            "computation_type": "data_processing",
        }

    async def _compute_health_metrics(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute health metrics."""
        metrics = payload.get("metrics", {})

        health_score = 100
        for metric, value in metrics.items():
            threshold_good = float(
                self.config_utils.get_performance_config(
                    "health_score_threshold_good", 0.6
                )
            )
            if value < threshold_good:  # Use configurable threshold
                health_score -= 10

        return {
            "operation": "health_metrics",
            "health_score": max(0, health_score),
            "metrics_count": len(metrics),
            "status": "healthy" if health_score > 70 else "degraded",
            "computation_type": "monitoring",
        }

    async def _compute_statistical_analysis(
        self, payload: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute statistical analysis."""
        data = payload.get("data", [])

        if not data:
            return {
                "operation": "statistical_analysis",
                "error": "No data provided",
                "computation_type": "statistical",
            }

        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std_dev = variance**0.5

        return {
            "operation": "statistical_analysis",
            "sample_size": len(data),
            "mean": round(mean, 4),
            "variance": round(variance, 4),
            "std_deviation": round(std_dev, 4),
            "computation_type": "statistical",
        }

    async def get_health_status(self) -> ModelHealthStatus:
        """Get the health status of the canary compute node."""
        status = EnumHealthStatus.HEALTHY
        details = {
            "node_type": "canary_compute",
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "mixin_capabilities": self.error_handling.get_enabled_capabilities(),
        }

        # Use mixin configuration for health thresholds
        min_ops = int(
            self.config_utils.get_performance_config("min_operations_for_health", 10)
        )
        error_threshold = float(
            self.config_utils.get_performance_config("error_rate_threshold", 0.1)
        )

        if (
            self.operation_count > min_ops
            and (self.error_count / self.operation_count) > error_threshold
        ):
            status = EnumHealthStatus.DEGRADED

        return ModelHealthStatus(
            status=status,
            timestamp=datetime.now(),
            details=details,
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get performance and operational metrics with mixin info."""
        return {
            "operation_count": self.operation_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(1, self.operation_count),
            "node_type": "canary_compute",
            "mixin_enabled": self.error_handling.initialized,
            "mixin_capabilities": self.error_handling.get_enabled_capabilities(),
        }
