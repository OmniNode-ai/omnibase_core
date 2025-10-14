"""
NodeCompute Service Interface - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION
This interface is used by autonomous code generation systems.
Any breaking changes require:
1. Semantic version bump (INTERFACE_VERSION.bump_major())
2. Migration guide for existing implementations
3. Deprecation period with warnings (minimum 1 minor version)
4. Update to code generation templates

STABILITY GUARANTEE:
- All abstract methods are stable interfaces for code generation
- New optional methods may be added in minor versions only
- Existing methods cannot be removed or have signatures changed

Abstract service interface for Compute node implementations providing:
- Pure computation processing with input/output contracts
- Algorithm execution with caching and parallel processing
- Input validation requirements
- Health status reporting

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, Mapping, TypeVar

from omnibase_core.infrastructure.node_compute import (
    ModelComputeInput,
    ModelComputeOutput,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.primitives.model_semver import ModelSemVer

T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")


class NodeComputeService(ABC, Generic[T_Input, T_Output]):
    """
    Stable interface for Compute nodes - DO NOT CHANGE without version bump.

    This abstract base class defines the required methods that all
    Compute node implementations must provide for code generation stability.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    @abstractmethod
    async def execute_compute(
        self,
        input_data: ModelComputeInput[T_Input],
    ) -> ModelComputeOutput[T_Output]:
        """
        Execute the computation operation.

        This is the main entry point for pure computation execution. Implementations
        must handle deterministic operations with proper caching, parallel processing
        support, and performance optimization as specified in their contract.

        Args:
            input_data: Input envelope with computation data and configuration

        Returns:
            ModelComputeOutput: Output envelope with result data and execution metadata

        Raises:
            OnexError: For operation failures with proper error codes
        """

    @abstractmethod
    async def validate_input(
        self,
        input_data: ModelComputeInput[T_Input],
    ) -> bool:
        """
        Validate input data before processing.

        Implementations should check that:
        - Computation type is supported
        - Operation data contains required fields
        - Configuration parameters are within valid ranges
        - Data types are compatible with registered algorithms

        Args:
            input_data: Input to validate

        Returns:
            bool: True if valid, False otherwise

        Raises:
            OnexError: For validation failures with clear error messages
        """

    @abstractmethod
    async def get_health_status(self) -> Mapping[str, ModelSchemaValue]:
        """
        Get current health status of the compute node.

        Implementations should return status information including:
        - Overall health status ("healthy", "degraded", "unhealthy")
        - Cache performance metrics
        - Thread pool status for parallel processing
        - Registered algorithms and their availability
        - Performance metrics and resource usage

        Returns:
            Mapping[str, ModelSchemaValue]: Health status with diagnostic information
        """

    # Optional lifecycle methods (can be overridden for specific behavior)
    async def initialize(self) -> None:
        """Initialize the compute node (optional override)."""

    async def cleanup(self) -> None:
        """Cleanup resources (optional override)."""
