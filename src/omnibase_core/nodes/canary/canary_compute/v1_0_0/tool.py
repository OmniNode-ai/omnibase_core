"""
Canary Compute Node - Business logic processing for canary deployments.

Simple COMPUTE node implementation for testing and validation purposes.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field

from omnibase_core.core.node_base import ModelNodeBase


class ModelCanaryComputeInput(BaseModel):
    """Input model for Canary Compute operations."""

    operation_type: str = Field(..., description="Type of computation to perform")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Input data for computation"
    )
    correlation_id: str = Field(default="", description="Request correlation ID")


class ModelCanaryComputeOutput(BaseModel):
    """Output model for Canary Compute operations."""

    result: Dict[str, Any] = Field(
        default_factory=dict, description="Computation result"
    )
    success: bool = Field(default=True, description="Whether operation succeeded")
    error_message: str = Field(
        default="", description="Error message if operation failed"
    )
    execution_time_ms: int = Field(
        default=0, description="Execution time in milliseconds"
    )
    correlation_id: str = Field(default="", description="Request correlation ID")


class NodeCanaryCompute(ModelNodeBase):
    """
    Canary Compute Node - Business logic processing for canary deployments.

    Simple COMPUTE node that performs basic calculations and data processing
    to validate the canary deployment system.
    """

    def __init__(self, contract_path=None, *args, **kwargs):
        from pathlib import Path

        # Use default contract path if not provided
        if contract_path is None:
            contract_path = Path(__file__).parent / "contract.yaml"

        super().__init__(contract_path=contract_path, *args, **kwargs)
        self._processed_count = 0

    async def process_computation(
        self, input_data: ModelCanaryComputeInput
    ) -> ModelCanaryComputeOutput:
        """
        Process a computation request.

        Args:
            input_data: Input data for the computation

        Returns:
            ModelCanaryComputeOutput with computation result
        """
        import time

        start_time = time.time()

        try:
            result = {}

            # Simple computation based on operation type
            if input_data.operation_type == "add":
                result = self._perform_addition(input_data.data)
            elif input_data.operation_type == "multiply":
                result = self._perform_multiplication(input_data.data)
            elif input_data.operation_type == "aggregate":
                result = self._perform_aggregation(input_data.data)
            else:
                result = {
                    "message": f"Processed {input_data.operation_type}",
                    "data": input_data.data,
                }

            self._processed_count += 1
            execution_time = int((time.time() - start_time) * 1000)

            return ModelCanaryComputeOutput(
                result=result,
                success=True,
                execution_time_ms=execution_time,
                correlation_id=input_data.correlation_id,
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return ModelCanaryComputeOutput(
                result={},
                success=False,
                error_message=f"Computation failed: {type(e).__name__}",
                execution_time_ms=execution_time,
                correlation_id=input_data.correlation_id,
            )

    def _perform_addition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform addition operation."""
        numbers = data.get("numbers", [])
        if not numbers:
            return {"sum": 0, "count": 0}

        total = sum(float(n) for n in numbers if isinstance(n, (int, float)))
        return {"sum": total, "count": len(numbers), "operation": "addition"}

    def _perform_multiplication(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform multiplication operation."""
        numbers = data.get("numbers", [])
        if not numbers:
            return {"product": 1, "count": 0}

        product = 1
        for n in numbers:
            if isinstance(n, (int, float)):
                product *= float(n)

        return {
            "product": product,
            "count": len(numbers),
            "operation": "multiplication",
        }

    def _perform_aggregation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform data aggregation."""
        items = data.get("items", [])
        if not items:
            return {"aggregated": {}, "count": 0}

        # Simple aggregation - count by type
        aggregated = {}
        for item in items:
            item_type = type(item).__name__
            aggregated[item_type] = aggregated.get(item_type, 0) + 1

        return {
            "aggregated": aggregated,
            "count": len(items),
            "operation": "aggregation",
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "status": "healthy",
            "processed_count": self._processed_count,
            "node_type": "COMPUTE",
            "node_name": "canary_compute",
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """Get node metrics."""
        return {
            "processed_requests": self._processed_count,
            "node_type": "COMPUTE",
            "status": "active",
        }
