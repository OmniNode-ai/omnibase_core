#!/usr/bin/env python3
"""
Canary Compute - Business logic processing for canary deployments.

This node handles computational tasks in a controlled canary environment, providing
data processing, algorithm execution, and business logic computation without side effects.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator

from omnibase_core.core.node_compute import ModelComputeInput, ModelComputeOutput
from omnibase_core.core.node_compute_service import NodeComputeService
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.nodes.canary.config.canary_config import get_canary_config
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler


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

    @validator("operation_type")
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
                f"Invalid operation_type: {v}. Must be one of {allowed_operations}"
            )
        return v

    @validator("correlation_id")
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


class NodeCanaryCompute(NodeComputeService):
    """
    Canary Compute Node - Business logic processing for canary deployments.

    This node handles computational tasks without side effects, providing
    safe processing capabilities for testing new business logic.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize the Canary Compute node."""
        super().__init__(container)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = get_canary_config()
        self.error_handler = get_error_handler(self.logger)
        self.operation_count = 0
        self.success_count = 0
        self.error_count = 0

    async def compute(
        self,
        compute_input: ModelComputeInput,
    ) -> ModelComputeOutput:
        """
        Perform a canary computation operation.

        Args:
            compute_input: Input data for the computation

        Returns:
            ModelComputeOutput: Result of the computation
        """
        start_time = datetime.now()
        correlation_id = str(uuid.uuid4())

        try:
            self.operation_count += 1

            # Parse and validate input data
            input_data = ModelCanaryComputeInput.model_validate(compute_input.data)

            # Use provided correlation_id or generate new one
            if input_data.correlation_id:
                correlation_id = input_data.correlation_id
                # Validate the provided correlation_id
                if not self.error_handler.validate_correlation_id(correlation_id):
                    raise ValueError("Invalid correlation_id format")
            else:
                input_data.correlation_id = correlation_id

            # Create operation context for error handling
            operation_context = self.error_handler.create_operation_context(
                operation_name=f"compute_{input_data.operation_type}",
                input_data=input_data.model_dump(),
                correlation_id=correlation_id,
            )

            self.logger.info(
                "Starting canary compute operation: %s [correlation_id=%s]",
                input_data.operation_type,
                correlation_id,
            )

            # Perform the actual computation with timeout
            result = await self._execute_canary_computation(input_data)

            self.success_count += 1
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create output
            output = ModelCanaryComputeOutput(
                computation_result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            self.logger.info(
                "Canary compute operation completed successfully "
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

            # Handle error with enhanced security
            error_info = self.error_handler.handle_error(
                error=e,
                context=locals(),
                correlation_id=correlation_id,
                operation_name="compute_operation",
            )

            output = ModelCanaryComputeOutput(
                computation_result={},
                success=False,
                error_message=error_info["message"],
                execution_time_ms=execution_time,
                correlation_id=correlation_id,
            )

            return ModelComputeOutput(
                data=output.model_dump(),
                metadata={
                    "node_type": "canary_compute",
                    "execution_time_ms": execution_time,
                    "error": True,
                    "error_id": error_info["error_id"],
                },
            )

    async def _execute_canary_computation(
        self,
        input_data: ModelCanaryComputeInput,
    ) -> dict[str, Any]:
        """
        Execute the specific canary computation based on type.

        Args:
            input_data: Validated input data

        Returns:
            Dict containing computation results
        """
        operation_type = input_data.operation_type
        data_payload = input_data.data_payload
        parameters = input_data.parameters

        if operation_type == "data_validation":
            return await self._validate_data(data_payload, parameters)
        if operation_type == "business_logic":
            return await self._execute_business_logic(data_payload, parameters)
        if operation_type == "data_transformation":
            return await self._transform_data(data_payload, parameters)
        if operation_type == "calculation":
            return await self._perform_calculation(data_payload, parameters)
        if operation_type == "algorithm_execution":
            return await self._execute_algorithm(data_payload, parameters)
        msg = f"Unsupported canary compute operation: {operation_type}"
        raise ValueError(msg)

    async def _validate_data(
        self,
        data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate data structure and content."""
        validation_rules = parameters.get("rules", [])
        errors = []
        warnings = []

        # Basic validation logic
        for rule in validation_rules:
            field = rule.get("field")
            rule_type = rule.get("type")

            if field not in data:
                if rule.get("required", False):
                    errors.append(f"Required field '{field}' missing")
                continue

            value = data[field]

            if rule_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field}' must be string")
            elif rule_type == "number" and not isinstance(value, int | float):
                errors.append(f"Field '{field}' must be number")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_fields": len(data),
        }

    async def _execute_business_logic(
        self,
        data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute business logic rules on data."""
        logic_type = parameters.get("logic_type", "default")

        if logic_type == "customer_scoring":
            # Customer scoring logic using configurable thresholds
            config = self.config.business_logic
            score = 0

            if data.get("purchase_history", 0) > config.customer_purchase_threshold:
                score += config.customer_purchase_score_points
            if data.get("loyalty_years", 0) > config.customer_loyalty_years_threshold:
                score += config.customer_loyalty_score_points
            if (
                data.get("support_tickets", 0)
                < config.customer_support_tickets_threshold
            ):
                score += config.customer_support_score_points

            return {
                "logic_type": logic_type,
                "customer_score": score,
                "tier": (
                    "premium"
                    if score > config.customer_premium_score_threshold
                    else "standard"
                ),
                "processed_fields": list(data.keys()),
                "thresholds_used": {
                    "purchase_threshold": config.customer_purchase_threshold,
                    "loyalty_years_threshold": config.customer_loyalty_years_threshold,
                    "support_tickets_threshold": config.customer_support_tickets_threshold,
                    "premium_score_threshold": config.customer_premium_score_threshold,
                },
            }

        return {
            "logic_type": logic_type,
            "result": "business_logic_executed",
            "input_processed": True,
        }

    async def _transform_data(
        self,
        data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Transform data structure according to rules."""
        transformation = parameters.get("transformation", "normalize")

        if transformation == "normalize":
            # Simple normalization
            normalized = {}
            for key, value in data.items():
                if isinstance(value, str):
                    normalized[key] = value.lower().strip()
                elif isinstance(value, int | float):
                    normalized[key] = float(value)
                else:
                    normalized[key] = value

            return {
                "transformation": transformation,
                "original_fields": len(data),
                "transformed_data": normalized,
            }

        return {
            "transformation": transformation,
            "result": "data_transformed",
            "original_count": len(data),
        }

    async def _perform_calculation(
        self,
        data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform mathematical calculations on data."""
        calculation_type = parameters.get("calculation", "sum")
        numeric_fields = [k for k, v in data.items() if isinstance(v, int | float)]

        if not numeric_fields:
            return {
                "calculation": calculation_type,
                "result": 0,
                "message": "No numeric fields found",
            }

        values = [data[field] for field in numeric_fields]

        if calculation_type == "sum":
            result = sum(values)
        elif calculation_type == "average":
            result = sum(values) / len(values)
        elif calculation_type == "max":
            result = max(values)
        elif calculation_type == "min":
            result = min(values)
        else:
            result = sum(values)  # default to sum

        return {
            "calculation": calculation_type,
            "result": result,
            "fields_processed": numeric_fields,
            "value_count": len(values),
        }

    async def _execute_algorithm(
        self,
        data: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute algorithmic processing on data."""
        algorithm = parameters.get("algorithm", "simple_sort")

        if algorithm == "simple_sort":
            # Sort data by keys
            sorted_keys = sorted(data.keys())
            sorted_data = {k: data[k] for k in sorted_keys}

            return {
                "algorithm": algorithm,
                "original_order": list(data.keys()),
                "sorted_order": sorted_keys,
                "sorted_data": sorted_data,
            }

        return {
            "algorithm": algorithm,
            "result": "algorithm_executed",
            "data_processed": len(data),
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
        }

        # Mark as degraded if error rate is high (using configurable thresholds)
        config = self.config.performance
        if (
            self.operation_count > config.min_operations_for_health
            and (self.error_count / self.operation_count) > config.error_rate_threshold
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
            "node_type": "canary_compute",
        }
