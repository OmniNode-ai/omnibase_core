"""
NodeReducer Service Interface - ONEX Standards Compliant.

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

Abstract service interface for Reducer node implementations providing:
- Data aggregation and state reduction processing
- Streaming support for large datasets
- Conflict resolution strategies
- Input validation requirements
- Health status reporting

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict

from omnibase_core.infrastructure.node_reducer import (
    ModelReducerInput,
    ModelReducerOutput,
)
from omnibase_core.primitives.model_semver import ModelSemVer


class NodeReducerService(ABC):
    """
    Stable interface for Reducer nodes - DO NOT CHANGE without version bump.

    This abstract base class defines the required methods that all
    Reducer node implementations must provide for code generation stability.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    @abstractmethod
    async def process_reduction(
        self,
        input_data: ModelReducerInput[Any],
    ) -> ModelReducerOutput[Any]:
        """
        Process the reduction operation.

        This is the main entry point for data aggregation and state reduction. Implementations
        must handle streaming data processing, conflict resolution, and state management
        as specified in their contract.

        Args:
            input_data: Input envelope with reduction data and configuration

        Returns:
            ModelReducerOutput: Output envelope with result data and execution metadata

        Raises:
            OnexError: For operation failures with proper error codes
        """

    @abstractmethod
    async def validate_input(
        self,
        input_data: ModelReducerInput[Any],
    ) -> bool:
        """
        Validate input data before processing.

        Implementations should check that:
        - Reduction type is supported
        - Operation data contains required fields
        - Conflict resolution strategy is valid
        - Streaming configuration is within valid ranges
        - Data format is compatible with reduction operations

        Args:
            input_data: Input to validate

        Returns:
            bool: True if valid, False otherwise

        Raises:
            OnexError: For validation failures with clear error messages
        """

    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status of the reducer node.

        Implementations should return status information including:
        - Overall health status ("healthy", "degraded", "unhealthy")
        - Streaming window status and buffer sizes
        - Conflict resolution statistics
        - Registered reduction functions and their availability
        - Performance metrics and memory usage

        Returns:
            Dict[str, Any]: Health status dictionary with diagnostic information
        """

    # Optional lifecycle methods (can be overridden for specific behavior)
    async def initialize(self) -> None:
        """Initialize the reducer node (optional override)."""

    async def cleanup(self) -> None:
        """Cleanup resources (optional override)."""
