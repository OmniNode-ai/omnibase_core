"""
Container service protocol for ONEX duck typing and dependency injection.

This protocol defines the interface for DI container management operations
that are extracted from ModelNodeBase as part of NODEBASE-001 Phase 2.

Author: ONEX Framework Team
"""

from typing import Any, Protocol

from omnibase_core.decorators import allow_any_type
from omnibase_core.model.core.model_contract_content import ModelContractContent


@allow_any_type(
    "Protocol interfaces require Any types for generic container and service handling",
)
class ProtocolContainerService(Protocol):
    """
    Protocol interface for container service operations.

    Defines duck typing interface for DI container management, service
    registration, and registry lifecycle operations extracted from ModelNodeBase.
    """

    def create_container_from_contract(
        self,
        contract_content: ModelContractContent,
        node_id: str,
        nodebase_ref: Any | None = None,
    ) -> Any:
        """
        Create and configure ONEXContainer from contract dependencies.

        Args:
            contract_content: Loaded contract with dependencies section
            node_id: Node identifier for logging and metadata
            nodebase_ref: Reference to ModelNodeBase instance for version access

        Returns:
            Registry-wrapped container instance with all dependencies registered

        Raises:
            OnexError: If container creation or dependency registration fails
        """
        ...

    def create_service_from_dependency(self, dependency: Any) -> Any | None:
        """
        Create service instance from contract dependency specification.

        Args:
            dependency: Dependency specification from contract with module/class info

        Returns:
            Service instance or None if creation fails

        Raises:
            OnexError: If dependency specification is invalid or service creation fails
        """
        ...

    def validate_container_dependencies(self, container: Any) -> bool:
        """
        Validate container has all required dependencies registered.

        Args:
            container: Container instance to validate

        Returns:
            bool: True if all dependencies are available, False otherwise
        """
        ...

    def get_registry_wrapper(
        self,
        container: Any,
        nodebase_ref: Any | None = None,
    ) -> Any:
        """
        Create registry wrapper around container for backward compatibility.

        Args:
            container: ONEXContainer instance
            nodebase_ref: Reference to ModelNodeBase for version access

        Returns:
            Registry wrapper with get_service and get_node_version methods
        """
        ...

    def update_container_lifecycle(self, registry: Any, nodebase_ref: Any) -> None:
        """
        Update container lifecycle with ModelNodeBase reference and version info.

        Args:
            registry: Registry wrapper instance
            nodebase_ref: ModelNodeBase instance for version and metadata access
        """
        ...
