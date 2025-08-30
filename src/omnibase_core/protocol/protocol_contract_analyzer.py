"""
Protocol for Contract Analyzer functionality.

Defines the interface for analyzing, validating, and processing
contract documents for code generation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Set

from omnibase_core.model.core.model_schema import ModelSchema
from omnibase_core.model.generation.model_contract_document import \
    ModelContractDocument


@dataclass
class ContractInfo:
    """Information about a loaded contract."""

    node_name: str
    node_version: str
    has_input_state: bool
    has_output_state: bool
    has_definitions: bool
    definition_count: int
    field_count: int
    reference_count: int
    enum_count: int


@dataclass
class ReferenceInfo:
    """Information about a discovered reference."""

    ref_string: str
    ref_type: str  # "internal", "external", "subcontract"
    resolved_type: str
    source_location: str
    target_file: Optional[str] = None


@dataclass
class ContractValidationResult:
    """Result of contract validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]


class ProtocolContractAnalyzer(Protocol):
    """Protocol for contract analysis functionality.

    This protocol defines the interface for loading, validating,
    and analyzing contract documents for code generation.
    """

    def load_contract(self, contract_path: Path) -> ModelContractDocument:
        """Load and parse a contract.yaml file into a validated model.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            Validated ModelContractDocument

        Raises:
            Exception: If contract cannot be loaded or validated
        """
        ...

    def validate_contract(self, contract_path: Path) -> ContractValidationResult:
        """Validate a contract for correctness and completeness.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            ContractValidationResult with validation details
        """
        ...

    def analyze_contract(self, contract_path: Path) -> ContractInfo:
        """Analyze contract structure and gather statistics.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            ContractInfo with analysis results
        """
        ...

    def discover_all_references(
        self, contract: ModelContractDocument
    ) -> List[ReferenceInfo]:
        """Discover all $ref references in a contract.

        Args:
            contract: Contract document to analyze

        Returns:
            List of discovered references with metadata
        """
        ...

    def get_external_dependencies(self, contract: ModelContractDocument) -> Set[str]:
        """Get all external file dependencies of a contract.

        Args:
            contract: Contract document to analyze

        Returns:
            Set of external file paths referenced
        """
        ...

    def get_dependency_graph(self, contract_path: Path) -> Dict[str, Set[str]]:
        """Build a dependency graph starting from a contract.

        Args:
            contract_path: Root contract path

        Returns:
            Dict mapping contract paths to their dependencies
        """
        ...

    def check_circular_references(
        self, contract: ModelContractDocument
    ) -> List[List[str]]:
        """Check for circular references in the contract.

        Args:
            contract: Contract to check

        Returns:
            List of circular reference cycles found
        """
        ...

    def count_fields_in_schema(self, schema: ModelSchema) -> int:
        """Count total fields in a schema including nested objects.

        Args:
            schema: Schema to count fields in

        Returns:
            Total field count
        """
        ...

    def validate_schema(
        self, schema: ModelSchema, location: str
    ) -> Dict[str, List[str]]:
        """Validate a schema object and return issues.

        Args:
            schema: Schema to validate
            location: Location path for error messages

        Returns:
            Dict with 'errors', 'warnings', and 'info' lists
        """
        ...
