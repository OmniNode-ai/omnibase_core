"""
Tool discovery service protocol for ONEX duck typing and tool instantiation.

This protocol defines the interface for tool discovery and instantiation operations
that are extracted from ModelNodeBase as part of NODEBASE-001 Phase 3.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import Any, Protocol

from omnibase_core.decorators import allow_any_type
from omnibase_core.model.core.model_contract_content import ModelContractContent


@allow_any_type(
    "Protocol interfaces require Any types for generic tool and registry handling",
)
class ProtocolToolDiscoveryService(Protocol):
    """
    Protocol interface for tool discovery service operations.

    Defines duck typing interface for tool class discovery, validation,
    instantiation, and registry resolution extracted from ModelNodeBase.
    """

    def resolve_tool_from_contract(
        self,
        contract_content: ModelContractContent,
        registry: Any,
        contract_path: Path,
    ) -> Any:
        """
        Resolve and instantiate tool from contract specification.

        Args:
            contract_content: Loaded contract with tool specification
            registry: Registry/container for tool instantiation
            contract_path: Path to contract file for module resolution

        Returns:
            Instantiated tool instance

        Raises:
            OnexError: If tool resolution or instantiation fails
        """
        ...

    def discover_tool_class_from_module(
        self,
        module_path: str,
        tool_class_name: str,
    ) -> type:
        """
        Discover tool class from module path.

        Args:
            module_path: Python module path (e.g., 'omnibase.tools.xyz.node')
            tool_class_name: Name of tool class to find

        Returns:
            Tool class type

        Raises:
            OnexError: If module import or class discovery fails
        """
        ...

    def instantiate_tool_with_container(
        self,
        tool_class: type,
        container: Any,
    ) -> Any:
        """
        Instantiate tool with DI container.

        Args:
            tool_class: Tool class to instantiate
            container: DI container for tool dependencies

        Returns:
            Instantiated tool instance

        Raises:
            OnexError: If tool instantiation fails
        """
        ...

    def resolve_tool_from_registry(
        self,
        registry: Any,
        tool_class_name: str,
    ) -> Any | None:
        """
        Resolve tool from legacy registry pattern.

        Args:
            registry: Legacy registry with get_tool method
            tool_class_name: Tool class name to resolve

        Returns:
            Tool instance or None if not found

        Raises:
            OnexError: If registry resolution fails
        """
        ...

    def build_module_path_from_contract(
        self,
        contract_path: Path,
    ) -> str:
        """
        Build module path from contract file path.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            Python module path for tool's node.py file

        Raises:
            OnexError: If module path construction fails
        """
        ...

    def validate_module_path(
        self,
        module_path: str,
    ) -> bool:
        """
        Validate module path for security and correctness.

        Args:
            module_path: Python module path to validate

        Returns:
            bool: True if module path is valid

        Raises:
            OnexError: If module path is invalid or insecure
        """
        ...

    def convert_class_name_to_registry_key(
        self,
        class_name: str,
    ) -> str:
        """
        Convert tool class name to registry key format.

        Args:
            class_name: Tool class name (e.g., ToolContractValidator)

        Returns:
            Registry key in snake_case format (e.g., contract_validator)
        """
        ...
