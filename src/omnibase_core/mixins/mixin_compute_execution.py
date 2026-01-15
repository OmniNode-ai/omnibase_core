"""
Mixin for contract-driven compute pipeline execution.

This module provides a mixin class that adds contract-driven pipeline execution
capabilities to NodeCompute instances. It wraps the synchronous pipeline executor
in an async-compatible interface and provides contract validation utilities.

Thread Safety:
    The mixin methods are stateless and operate on passed arguments only.
    The underlying execute_compute_pipeline function is pure and thread-safe.
    However, the mixing class (e.g., NodeCompute) may have its own thread-safety
    constraints - consult the mixing class documentation.

Usage:
    This mixin is designed to be used with NodeCompute or similar node classes
    that need to execute contract-driven transformation pipelines.

Example:
    >>> from omnibase_core.mixins import MixinComputeExecution
    >>> from omnibase_core.nodes import NodeCompute
    >>>
    >>> class MyTransformNode(NodeCompute, MixinComputeExecution):
    ...     async def process(self, input_data):
    ...         result = await self.execute_contract_pipeline(
    ...             self.contract.compute_operations,
    ...             input_data.data,
    ...             correlation_id=input_data.correlation_id,
    ...         )
    ...         return result

See Also:
    - omnibase_core.utils.util_compute_executor: Core pipeline execution logic
    - omnibase_core.models.contracts.subcontracts: Contract models
    - omnibase_core.nodes.node_compute: Base NodeCompute class
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

from collections import Counter
from uuid import UUID, uuid4

from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.compute.model_compute_pipeline_result import (
    ModelComputePipelineResult,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.utils.util_compute_executor import execute_compute_pipeline


class MixinComputeExecution:
    """
    Mixin for contract-driven compute pipeline execution.

    Provides async pipeline execution and contract validation methods for
    NodeCompute instances that use contract-driven transformation pipelines.
    This mixin wraps the synchronous pipeline executor in an async-compatible
    interface for use in async node processing methods.

    Thread Safety:
        The mixin methods themselves are stateless and thread-safe. However,
        the mixing class may have thread-safety constraints. When using with
        NodeCompute, each instance should be used from a single thread or
        with appropriate synchronization.

    Attributes:
        node_id (UUID): Expected to be provided by the mixing class. Used to
            populate the execution context for tracing purposes.

    Example:
        >>> class MyComputeNode(NodeCompute, MixinComputeExecution):
        ...     async def process(self, input_data):
        ...         # Validate contract at startup (optional but recommended)
        ...         errors = self.validate_compute_contract(self.contract.compute_operations)
        ...         if errors:
        ...             raise ValueError(f"Invalid contract: {errors}")
        ...
        ...         # Execute the pipeline
        ...         result = await self.execute_contract_pipeline(
        ...             self.contract.compute_operations,
        ...             input_data.data,
        ...         )
        ...         return result
    """

    # Type hints for attributes that should exist on the mixing class
    node_id: UUID

    async def execute_contract_pipeline(
        self,
        contract: ModelComputeSubcontract,
        input_data: object,  # object: pipeline accepts dict, Pydantic model, or JSON-compatible data
        correlation_id: UUID | None = None,
    ) -> ModelComputePipelineResult:
        """
        Execute a contract-driven compute pipeline asynchronously.

        Wraps the synchronous execute_compute_pipeline function in an async
        interface for use in async node processing methods. Creates an execution
        context with operation tracking information.

        Thread Safety:
            This method is async but the underlying pipeline execution is synchronous.
            The function is pure and does not modify shared state, making it safe
            for concurrent use from multiple async tasks.

        Args:
            contract: The compute subcontract defining the pipeline steps,
                transformations, and mappings to execute.
            input_data: Input data to process through the pipeline. Can be a
                dictionary, Pydantic model, or any JSON-compatible structure.
            correlation_id: Optional UUID for distributed tracing. If provided,
                will be included in the execution context for correlation with
                upstream/downstream operations.

        Returns:
            ModelComputePipelineResult containing:
                - success: Whether all steps completed successfully
                - output: Final pipeline output, or None on failure
                - processing_time_ms: Total execution time
                - steps_executed: List of executed step names
                - step_results: Individual results for each step
                - Error details if the pipeline failed

        Example:
            >>> result = await self.execute_contract_pipeline(
            ...     self.contract.compute_operations,
            ...     {"text": "hello world"},
            ...     correlation_id=request.correlation_id,
            ... )
            >>> if result.success:
            ...     return result.output
            ... else:
            ...     raise PipelineError(result.error_message)
        """
        # Build execution context
        context = ModelComputeExecutionContext(
            operation_id=uuid4(),
            correlation_id=correlation_id,
            node_id=(
                str(self.node_id)
                if hasattr(self, "node_id") and self.node_id is not None
                else None
            ),
        )

        # Execute pipeline (sync function, but wrapped for async compatibility)
        result = execute_compute_pipeline(contract, input_data, context)

        return result

    def validate_compute_contract(self, contract: ModelComputeSubcontract) -> list[str]:
        """
        Validate a compute contract at load time.

        Performs static validation of the contract structure to catch configuration
        errors before runtime execution. This should be called during node
        initialization to fail fast on invalid contracts.

        Thread Safety:
            This method is pure and stateless - safe for concurrent use.

        Validation Checks:
            1. Duplicate step names: Each step must have a unique name
            2. Forward references: Mapping paths can only reference steps that
               execute before the current step

        Args:
            contract: The compute subcontract to validate.

        Returns:
            A list of validation error messages. Empty list indicates the
            contract is valid. Each error message describes a specific
            validation failure.

        Example:
            >>> errors = self.validate_compute_contract(contract)
            >>> if errors:
            ...     for error in errors:
            ...         logger.error(f"Contract validation error: {error}")
            ...     raise ValueError(f"Invalid contract: {len(errors)} errors found")

        Note:
            This performs static analysis only. Runtime errors (e.g., type
            mismatches, missing input fields) are caught during pipeline execution.
        """
        errors: list[str] = []

        # Check for duplicate step names using Counter for O(n) performance
        step_names = [step.step_name for step in contract.pipeline]
        name_counts = Counter(step_names)
        duplicates = {name for name, count in name_counts.items() if count > 1}
        if duplicates:
            errors.append(f"Duplicate step names: {duplicates}")

        # Validate mapping paths reference existing steps
        executed_steps: set[str] = set()
        for step in contract.pipeline:
            if step.mapping_config is not None:
                for _field, path in step.mapping_config.field_mappings.items():
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
