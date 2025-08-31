"""
Protocol definition for contract service operations.

This protocol defines the interface for contract loading, parsing, validation,
and caching operations following ONEX duck typing standards.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from omnibase_core.core.models.model_contract_content import ModelContractContent
from omnibase_core.model.core.model_semver import ModelSemVer


@runtime_checkable
class ProtocolContractService(Protocol):
    """
    Protocol for contract service operations following ONEX standards.

    This protocol defines the contract for services that handle:
    - Contract loading and parsing from YAML files
    - Contract validation and structure verification
    - Contract caching for performance optimization
    - Contract metadata extraction and processing

    Duck typing ensures any implementation with these methods
    can be used interchangeably in ModelNodeBase and other consumers.
    """

    def load_contract(self, contract_path: Path) -> ModelContractContent:
        """
        Load and parse a contract from file system.

        Args:
            contract_path: Path to the contract YAML file

        Returns:
            ModelContractContent: Fully parsed contract with all references resolved

        Raises:
            OnexError: If contract loading or parsing fails
        """
        ...

    def validate_contract(self, contract: ModelContractContent) -> bool:
        """
        Validate contract structure and content.

        Args:
            contract: Contract to validate

        Returns:
            bool: True if contract is valid, False otherwise

        Raises:
            OnexError: If validation encounters critical errors
        """
        ...

    def get_cached_contract(
        self,
        contract_path: Path,
    ) -> ModelContractContent | None:
        """
        Retrieve contract from cache if available.

        Args:
            contract_path: Path to the contract file

        Returns:
            Optional[ModelContractContent]: Cached contract or None if not cached
        """
        ...

    def cache_contract(
        self,
        contract_path: Path,
        contract: ModelContractContent,
    ) -> bool:
        """
        Cache a contract for future retrieval.

        Args:
            contract_path: Path to the contract file
            contract: Contract to cache

        Returns:
            bool: True if caching succeeded, False otherwise
        """
        ...

    def clear_cache(self, contract_path: Path | None = None) -> int:
        """
        Clear contract cache.

        Args:
            contract_path: Specific contract to remove, or None to clear all

        Returns:
            int: Number of contracts removed from cache
        """
        ...

    def extract_node_id(self, contract: ModelContractContent) -> str:
        """
        Extract node ID from contract.

        Args:
            contract: Contract to extract ID from

        Returns:
            str: Node identifier
        """
        ...

    def extract_version(self, contract: ModelContractContent) -> ModelSemVer:
        """
        Extract semantic version from contract.

        Args:
            contract: Contract to extract version from

        Returns:
            ModelSemVer: Semantic version object
        """
        ...

    def extract_dependencies(
        self,
        contract: ModelContractContent,
    ) -> list[dict[str, str]]:
        """
        Extract dependency list from contract.

        Args:
            contract: Contract to extract dependencies from

        Returns:
            List[Dict[str, str]]: List of dependency specifications
        """
        ...

    def extract_tool_class_name(self, contract: ModelContractContent) -> str:
        """
        Extract main tool class name from contract.

        Args:
            contract: Contract to extract tool class from

        Returns:
            str: Main tool class name
        """
        ...

    def extract_event_patterns(self, contract: ModelContractContent) -> list[str]:
        """
        Extract event subscription patterns from contract.

        Args:
            contract: Contract to extract patterns from

        Returns:
            List[str]: List of event patterns
        """
        ...

    def health_check(self) -> dict[str, object]:
        """
        Perform health check on contract service.

        Returns:
            Dict[str, object]: Health check results with status and metrics
        """
        ...
