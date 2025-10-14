"""
NodeOrchestrator Service Interface - ONEX Standards Compliant.

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

Abstract service interface for Orchestrator node implementations providing:
- Workflow coordination and control flow management
- Thunk emission patterns for deferred execution
- Conditional branching and parallel coordination
- Input validation requirements
- Health status reporting

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Mapping

from omnibase_core.infrastructure.node_orchestrator import (
    ModelOrchestratorInput,
    ModelOrchestratorOutput,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.primitives.model_semver import ModelSemVer


class NodeOrchestratorService(ABC):
    """
    Stable interface for Orchestrator nodes - DO NOT CHANGE without version bump.

    This abstract base class defines the required methods that all
    Orchestrator node implementations must provide for code generation stability.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    @abstractmethod
    async def execute_orchestrate(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Execute the orchestration operation.

        This is the main entry point for workflow coordination and control flow management.
        Implementations must handle thunk emission, conditional branching, parallel execution
        coordination, and dependency management as specified in their contract.

        Args:
            input_data: Input envelope with workflow data and configuration

        Returns:
            ModelOrchestratorOutput: Output envelope with result data and execution metadata

        Raises:
            OnexError: For operation failures with proper error codes
        """

    @abstractmethod
    async def validate_input(
        self,
        input_data: ModelOrchestratorInput,
    ) -> bool:
        """
        Validate input data before processing.

        Implementations should check that:
        - Workflow ID is valid and unique
        - Workflow steps are well-formed
        - Execution mode is supported
        - Dependency graph has no cycles
        - Configuration parameters are within valid ranges
        - Thunk definitions are valid

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
        Get current health status of the orchestrator node.

        Implementations should return status information including:
        - Overall health status ("healthy", "degraded", "unhealthy")
        - Active workflow count and status
        - Thunk emission queue status
        - Load balancer metrics
        - Registered condition functions
        - Performance metrics and coordination overhead

        Returns:
            Mapping[str, ModelSchemaValue]: Health status with diagnostic information
        """

    # Optional lifecycle methods (can be overridden for specific behavior)
    async def initialize(self) -> None:
        """Initialize the orchestrator node (optional override)."""

    async def cleanup(self) -> None:
        """Cleanup resources (optional override)."""
