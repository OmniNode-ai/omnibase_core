"""
Mixin for contract-driven compute pipeline execution.

Provides the execute_compute_pipeline method for NodeCompute instances
that use contract-driven transformation pipelines.
"""
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from omnibase_core.models.compute.model_compute_execution_context import ModelComputeExecutionContext
from omnibase_core.models.compute.model_compute_pipeline_result import ModelComputePipelineResult
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import ModelComputeSubcontract
from omnibase_core.utils.compute_executor import execute_compute_pipeline

if TYPE_CHECKING:
    from uuid import UUID


class MixinComputeExecution:
    """
    Mixin for contract-driven compute pipeline execution.

    Provides the execute_compute_pipeline method that can be used by
    NodeCompute to execute transformation pipelines defined in contracts.

    Usage:
        class MyComputeNode(NodeCompute, MixinComputeExecution):
            async def process(self, input_data):
                result = await self.execute_contract_pipeline(
                    self.contract.compute_operations,
                    input_data.data,
                )
                return result
    """

    # Type hints for attributes that should exist on the mixing class
    node_id: "UUID"

    async def execute_contract_pipeline(
        self,
        contract: ModelComputeSubcontract,
        input_data: Any,
        correlation_id: "UUID | None" = None,
    ) -> ModelComputePipelineResult:
        """
        Execute a contract-driven compute pipeline.

        Args:
            contract: The compute subcontract defining the pipeline
            input_data: Input data to process through the pipeline
            correlation_id: Optional correlation ID for tracing

        Returns:
            ModelComputePipelineResult with success status and step results
        """
        # Build execution context
        context = ModelComputeExecutionContext(
            operation_id=uuid4(),
            correlation_id=correlation_id,
            node_id=str(self.node_id) if hasattr(self, 'node_id') else None,
        )

        # Execute pipeline (sync function, but wrapped for async compatibility)
        result = execute_compute_pipeline(contract, input_data, context)

        return result

    def validate_compute_contract(self, contract: ModelComputeSubcontract) -> list[str]:
        """
        Validate a compute contract at load time.

        Args:
            contract: The compute subcontract to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check for duplicate step names
        step_names = [step.step_name for step in contract.pipeline]
        if len(step_names) != len(set(step_names)):
            duplicates = [name for name in step_names if step_names.count(name) > 1]
            errors.append(f"Duplicate step names: {set(duplicates)}")

        # Validate mapping paths reference existing steps
        executed_steps: set[str] = set()
        for step in contract.pipeline:
            if step.mapping_config:
                for field, path in step.mapping_config.field_mappings.items():
                    if path.startswith("$.steps."):
                        # Extract step name from path
                        remaining = path[8:]  # Remove "$.steps."
                        ref_step = remaining.split(".")[0]
                        if ref_step not in executed_steps:
                            errors.append(
                                f"Step '{step.step_name}' references unknown step '{ref_step}' in mapping"
                            )
            executed_steps.add(step.step_name)

        return errors


__all__ = [
    "MixinComputeExecution",
]
