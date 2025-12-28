"""
ProtocolCompute - Protocol for computation nodes.

This module provides the protocol definition for nodes that implement
the COMPUTE pattern with pure transformation capabilities.

OMN-662: Node Protocol Definitions for ONEX Four-Node Architecture.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.compute.model_compute_input import ModelComputeInput
    from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
    from omnibase_core.models.contracts.model_contract_compute import (
        ModelContractCompute,
    )


@runtime_checkable
class ProtocolCompute(Protocol):
    """
    Protocol for computation nodes.

    Defines the interface for nodes that implement the COMPUTE pattern
    with pure transformation and optional caching/parallelism support.

    COMPUTE nodes are:
    - Pure: Same inputs always produce same outputs
    - Stateless: No side effects or persistent state
    - Cacheable: Results can be memoized for identical inputs
    - Parallelizable: Independent computations can run concurrently

    Example:
        class MyCompute:
            async def process(
                self,
                input_data: ModelComputeInput[list[int]],
            ) -> ModelComputeOutput[int]:
                return ModelComputeOutput(
                    result=sum(input_data.data),
                    operation_id=input_data.operation_id,
                    computation_type=input_data.computation_type,
                    processing_time_ms=0.5,
                )

        node: ProtocolCompute = MyCompute()  # Type-safe!
    """

    async def process(
        self,
        input_data: ModelComputeInput[Any],
    ) -> ModelComputeOutput[Any]:
        """
        Execute pure computation on strongly-typed input.

        This is the core computation interface. Implementations must:
        - Accept ModelComputeInput with typed data payload
        - Return ModelComputeOutput with typed result
        - Be deterministic (same input → same output)
        - Not perform side effects

        Args:
            input_data: Computation input with data, operation_id, and configuration.

        Returns:
            Computation output with result, metrics, and cache status.

        Raises:
            ModelOnexError: If input validation fails or computation encounters
                an error condition (e.g., unsupported computation_type).
        """
        ...

    async def execute_compute(
        self,
        contract: ModelContractCompute,
    ) -> ModelComputeOutput[Any]:
        """
        Execute computation from contract specification.

        Contract-based entry point for ONEX interface. Converts contract
        configuration to ModelComputeInput and delegates to process().

        Args:
            contract: Contract with input_state and algorithm configuration.

        Returns:
            Computation output matching process() return type.

        Raises:
            ModelOnexError: If contract validation fails or the computation
                encounters an error during execution.
        """
        ...

    def register_computation(
        self,
        computation_type: str,
        computation_func: Callable[..., Any],
    ) -> None:
        """
        Register a custom computation function.

        Allows dynamic registration of computation algorithms. Each
        computation_type maps to a pure function for processing.

        Args:
            computation_type: String identifier for the computation.
            computation_func: Pure function to execute.

        Raises:
            ModelOnexError: If type already registered or function not callable.
        """
        ...

    async def get_computation_metrics(self) -> dict[str, dict[str, float]]:
        """
        Get detailed computation performance metrics.

        Returns metrics for:
        - Per-computation-type performance statistics
        - Cache hit rates and lookup times
        - Execution mode information

        Returns:
            Dictionary with computation-specific and infrastructure metrics.
        """
        ...


__all__ = ["ProtocolCompute"]
