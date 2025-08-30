"""
Contract Analyzer Utility for ONEX Contract Generation.

Handles loading, validation, and analysis of contract documents.
Provides consistent contract processing across all ONEX tools.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.model.core.model_schema import ModelSchema
from omnibase_core.model.generation.model_contract_document import ModelContractDocument
from omnibase_core.utils.generation.utility_schema_composer import UtilitySchemaComposer
from omnibase_core.utils.generation.utility_schema_loader import UtilitySchemaLoader


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
    target_file: str | None = None


@dataclass
class ContractValidationResult:
    """Result of contract validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]


class UtilityContractAnalyzer:
    """
    Utility for analyzing and validating contract documents.

    Handles:
    - Contract loading and parsing
    - Contract validation
    - Reference discovery and analysis
    - Dependency analysis
    - Schema structure analysis
    """

    def __init__(self, reference_resolver=None, enum_generator=None, file_reader=None):
        """
        Initialize the contract analyzer.

        Args:
            reference_resolver: Optional reference resolver for $ref handling
            enum_generator: Optional enum generator for enum discovery
            file_reader: Optional file reader for loading contracts
        """
        self.reference_resolver = reference_resolver
        self.enum_generator = enum_generator
        self.file_reader = file_reader
        self._contract_cache = {}

        # Initialize schema composition utilities
        self.schema_loader = UtilitySchemaLoader()
        self.schema_composer = UtilitySchemaComposer(self.schema_loader)

    def load_contract(self, contract_path: Path) -> ModelContractDocument:
        """
        Load and parse a contract.yaml file into a validated model.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            Validated ModelContractDocument

        Raises:
            Exception: If contract cannot be loaded or validated
        """
        # Check cache first
        cache_key = str(contract_path.resolve())
        if cache_key in self._contract_cache:
            emit_log_event(
                LogLevelEnum.DEBUG,
                f"Using cached contract for {contract_path}",
                {"path": str(contract_path)},
            )
            return self._contract_cache[cache_key]

        # Load from file
        emit_log_event(
            LogLevelEnum.INFO,
            f"Loading contract from {contract_path}",
            {"path": str(contract_path)},
        )

        # Use file reader if available, otherwise fall back to direct file access
        if self.file_reader:
            # CRITICAL: Need to compose schemas even when using file reader

            # Load raw contract data first
            with open(contract_path) as f:
                contract_data = yaml.safe_load(f)

            # Compose schemas before creating ModelContractDocument
            emit_log_event(
                LogLevelEnum.INFO,
                "🔍 TRACE: Composing external schema references (file reader path)",
                {"contract_path": str(contract_path)},
            )

            try:
                if "definitions" in contract_data:
                    original_count = len(contract_data["definitions"])
                    composed_definitions = (
                        self.schema_composer.compose_contract_definitions(
                            contract_data,
                            contract_path,
                        )
                    )

                    # DEBUG: Check what we got from composition
                    if "SemVerModel" in composed_definitions:
                        semver_composed = composed_definitions["SemVerModel"]

                    contract_data["definitions"] = composed_definitions

                    emit_log_event(
                        LogLevelEnum.INFO,
                        f"Schema composition completed (file reader path): {original_count} definitions processed",
                        {
                            "original_definitions": original_count,
                            "composed_definitions": len(composed_definitions),
                            "composition_successful": True,
                        },
                    )

            except Exception as e:
                emit_log_event(
                    LogLevelEnum.ERROR,
                    f"Schema composition failed (file reader path): {e}",
                    {
                        "contract_path": str(contract_path),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

            # Convert to ModelContractDocument
            contract = ModelContractDocument(**contract_data)
        else:
            with open(contract_path) as f:
                contract_data = yaml.safe_load(f)

            # CRITICAL: Compose schemas before creating ModelContractDocument
            emit_log_event(
                LogLevelEnum.INFO,
                "🔍 TRACE: Composing external schema references",
                {"contract_path": str(contract_path)},
            )

            try:
                # Compose all definitions with external references resolved
                if "definitions" in contract_data:
                    original_count = len(contract_data["definitions"])
                    composed_definitions = (
                        self.schema_composer.compose_contract_definitions(
                            contract_data,
                            contract_path,
                        )
                    )

                    # DEBUG: Check what we got from composition
                    if "SemVerModel" in composed_definitions:
                        semver_composed = composed_definitions["SemVerModel"]
                        emit_log_event(
                            LogLevelEnum.INFO,
                            f"DEBUG: SemVerModel after composition - type: {semver_composed.get('type')}, properties: {list(semver_composed.get('properties', {}).keys())}",
                            {
                                "composed_type": semver_composed.get("type"),
                                "composed_properties": list(
                                    semver_composed.get("properties", {}).keys(),
                                ),
                                "composed_required": semver_composed.get(
                                    "required",
                                    [],
                                ),
                            },
                        )

                    contract_data["definitions"] = composed_definitions

                    emit_log_event(
                        LogLevelEnum.INFO,
                        f"Schema composition completed: {original_count} definitions processed",
                        {
                            "original_definitions": original_count,
                            "composed_definitions": len(composed_definitions),
                            "composition_successful": True,
                        },
                    )
                else:
                    emit_log_event(
                        LogLevelEnum.DEBUG,
                        "No definitions found in contract - skipping schema composition",
                        {"contract_path": str(contract_path)},
                    )

            except Exception as e:
                emit_log_event(
                    LogLevelEnum.ERROR,
                    f"Schema composition failed: {e}",
                    {
                        "contract_path": str(contract_path),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                # Continue with original definitions if composition fails
                emit_log_event(
                    LogLevelEnum.WARNING,
                    "Falling back to original definitions due to composition failure",
                    {"contract_path": str(contract_path)},
                )

            # Convert to ModelContractDocument for validation
            contract = ModelContractDocument(**contract_data)

        # Cache for future use
        self._contract_cache[cache_key] = contract

        return contract

    def validate_contract(self, contract_path: Path) -> ContractValidationResult:
        """
        Validate a contract for correctness and completeness.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            ContractValidationResult with validation details
        """
        errors = []
        warnings = []
        info = []

        try:
            # Try to load the contract
            contract = self.load_contract(contract_path)

            # Required field validation
            if not contract.node_name:
                errors.append("Missing required field: node_name")

            if not contract.node_version:
                errors.append("Missing required field: node_version")

            # Schema validation
            if not contract.input_state and not contract.output_state:
                warnings.append(
                    "Contract has neither input_state nor output_state defined",
                )

            # Validate input_state if present
            if contract.input_state:
                input_issues = self._validate_schema(
                    contract.input_state,
                    "input_state",
                )
                errors.extend(input_issues["errors"])
                warnings.extend(input_issues["warnings"])
                info.extend(input_issues["info"])

            # Validate output_state if present
            if contract.output_state:
                output_issues = self._validate_schema(
                    contract.output_state,
                    "output_state",
                )
                errors.extend(output_issues["errors"])
                warnings.extend(output_issues["warnings"])
                info.extend(output_issues["info"])

            # Validate definitions if present
            if contract.definitions:
                for def_name, def_schema in contract.definitions.items():
                    def_issues = self._validate_schema(
                        def_schema,
                        f"definitions.{def_name}",
                    )
                    errors.extend(def_issues["errors"])
                    warnings.extend(def_issues["warnings"])
                    info.extend(def_issues["info"])

            # Check for circular references
            circular_refs = self._check_circular_references(contract)
            if circular_refs:
                for cycle in circular_refs:
                    errors.append(f"Circular reference detected: {' -> '.join(cycle)}")

            is_valid = len(errors) == 0

        except Exception as e:
            errors.append(f"Failed to load contract: {e!s}")
            is_valid = False

        return ContractValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
        )

    def analyze_contract(self, contract_path: Path) -> ContractInfo:
        """
        Analyze contract structure and gather statistics.

        Args:
            contract_path: Path to contract.yaml file

        Returns:
            ContractInfo with analysis results
        """
        contract = self.load_contract(contract_path)

        # Count fields
        field_count = 0
        if contract.input_state:
            field_count += self._count_fields_in_schema(contract.input_state)
        if contract.output_state:
            field_count += self._count_fields_in_schema(contract.output_state)

        # Count definitions
        definition_count = len(contract.definitions) if contract.definitions else 0

        # Count references
        all_refs = self.discover_all_references(contract)
        reference_count = len(all_refs)

        # Count enums
        enum_count = 0
        if self.enum_generator:
            enum_infos = self.enum_generator.discover_enums_from_contract(contract)
            enum_count = len(enum_infos)

        return ContractInfo(
            node_name=contract.node_name,
            node_version=contract.node_version,
            has_input_state=contract.input_state is not None,
            has_output_state=contract.output_state is not None,
            has_definitions=bool(contract.definitions),
            definition_count=definition_count,
            field_count=field_count,
            reference_count=reference_count,
            enum_count=enum_count,
        )

    def discover_all_references(
        self,
        contract: ModelContractDocument,
    ) -> list[ReferenceInfo]:
        """
        Discover all $ref references in a contract.

        Args:
            contract: Contract document to analyze

        Returns:
            List of discovered references with metadata
        """
        references = []

        # Check input_state
        if contract.input_state:
            refs = self._collect_references_from_schema(
                contract.input_state,
                "input_state",
            )
            references.extend(refs)

        # Check output_state
        if contract.output_state:
            refs = self._collect_references_from_schema(
                contract.output_state,
                "output_state",
            )
            references.extend(refs)

        # Check definitions
        if contract.definitions:
            for def_name, def_schema in contract.definitions.items():
                refs = self._collect_references_from_schema(
                    def_schema,
                    f"definitions.{def_name}",
                )
                references.extend(refs)

        return references

    def get_external_dependencies(self, contract: ModelContractDocument) -> set[str]:
        """
        Get all external file dependencies of a contract.

        Args:
            contract: Contract document to analyze

        Returns:
            Set of external file paths referenced
        """
        references = self.discover_all_references(contract)
        external_files = set()

        for ref in references:
            if ref.ref_type in ["external", "subcontract"] and ref.target_file:
                external_files.add(ref.target_file)

        return external_files

    def get_dependency_graph(self, contract_path: Path) -> dict[str, set[str]]:
        """
        Build a dependency graph starting from a contract.

        Args:
            contract_path: Root contract path

        Returns:
            Dict mapping contract paths to their dependencies
        """
        graph = {}
        to_process = [str(contract_path.resolve())]
        processed = set()

        while to_process:
            current = to_process.pop(0)
            if current in processed:
                continue

            processed.add(current)

            try:
                contract = self.load_contract(Path(current))
                dependencies = self.get_external_dependencies(contract)

                graph[current] = dependencies

                # Add dependencies to processing queue
                for dep in dependencies:
                    dep_path = Path(current).parent / dep
                    if dep_path.exists():
                        to_process.append(str(dep_path.resolve()))

            except Exception as e:
                emit_log_event(
                    LogLevelEnum.WARNING,
                    f"Failed to analyze dependencies for {current}: {e}",
                    {"path": current, "error": str(e)},
                )
                graph[current] = set()

        return graph

    # Private helper methods

    def _validate_schema(
        self,
        schema: ModelSchema,
        location: str,
    ) -> dict[str, list[str]]:
        """Validate a schema object and return issues."""
        errors = []
        warnings = []
        info = []

        # Check for empty schemas
        if not schema.properties and schema.schema_type == "object":
            warnings.append(f"{location}: Object schema has no properties defined")

        # Check for missing descriptions
        if not schema.description:
            info.append(f"{location}: Schema has no description")

        # Check array items
        if schema.schema_type == "array" and not schema.items:
            errors.append(f"{location}: Array schema missing items definition")

        # Recursively validate nested schemas
        if schema.properties:
            for prop_name, prop_schema in schema.properties.items():
                nested_issues = self._validate_schema(
                    prop_schema,
                    f"{location}.{prop_name}",
                )
                errors.extend(nested_issues["errors"])
                warnings.extend(nested_issues["warnings"])
                info.extend(nested_issues["info"])

        return {"errors": errors, "warnings": warnings, "info": info}

    def _count_fields_in_schema(self, schema: ModelSchema) -> int:
        """Count total fields in a schema including nested objects."""
        count = 0

        if schema.properties:
            count += len(schema.properties)

            # Recursively count nested fields
            for prop_schema in schema.properties.values():
                if prop_schema.schema_type == "object":
                    count += self._count_fields_in_schema(prop_schema)
                elif prop_schema.schema_type == "array" and prop_schema.items:
                    if prop_schema.items.schema_type == "object":
                        count += self._count_fields_in_schema(prop_schema.items)

        return count

    def _collect_references_from_schema(
        self,
        schema: ModelSchema,
        location: str,
    ) -> list[ReferenceInfo]:
        """Collect all references from a schema object."""
        references = []

        # Check for direct reference
        if schema.ref:
            ref_info = self._analyze_reference(schema.ref, location)
            references.append(ref_info)

        # Check properties
        if schema.properties:
            for prop_name, prop_schema in schema.properties.items():
                refs = self._collect_references_from_schema(
                    prop_schema,
                    f"{location}.{prop_name}",
                )
                references.extend(refs)

        # Check array items
        if schema.items:
            refs = self._collect_references_from_schema(schema.items, f"{location}[]")
            references.extend(refs)

        return references

    def _analyze_reference(self, ref_string: str, location: str) -> ReferenceInfo:
        """Analyze a single reference string."""
        # Determine reference type
        if ref_string.startswith("#/definitions/"):
            ref_type = "internal"
            target_file = None
        elif "#/" in ref_string:
            file_part, _ = ref_string.split("#/", 1)
            if file_part.startswith("contracts/"):
                ref_type = "subcontract"
            else:
                ref_type = "external"
            target_file = file_part
        else:
            ref_type = "unknown"
            target_file = None

        # Resolve type name
        if self.reference_resolver:
            resolved_type = self.reference_resolver.resolve_ref(ref_string)
        else:
            # Simple fallback
            parts = ref_string.split("/")
            resolved_type = f"Model{parts[-1]}" if parts else "Unknown"

        return ReferenceInfo(
            ref_string=ref_string,
            ref_type=ref_type,
            resolved_type=resolved_type,
            source_location=location,
            target_file=target_file,
        )

    def _check_circular_references(
        self,
        contract: ModelContractDocument,
    ) -> list[list[str]]:
        """Check for circular references in the contract."""
        cycles = []

        # Build reference graph
        ref_graph = {}

        # Add internal definitions to graph
        if contract.definitions:
            for def_name in contract.definitions:
                def_path = f"#/definitions/{def_name}"
                refs = self._get_refs_from_schema(contract.definitions[def_name])
                ref_graph[def_path] = refs

        # Find cycles using DFS
        visited = set()
        rec_stack = []

        def find_cycle(node: str) -> list[str] | None:
            if node in rec_stack:
                # Found cycle
                cycle_start = rec_stack.index(node)
                return rec_stack[cycle_start:] + [node]

            if node in visited:
                return None

            visited.add(node)
            rec_stack.append(node)

            if node in ref_graph:
                for neighbor in ref_graph[node]:
                    cycle = find_cycle(neighbor)
                    if cycle:
                        return cycle

            rec_stack.pop()
            return None

        # Check all nodes
        for node in ref_graph:
            if node not in visited:
                cycle = find_cycle(node)
                if cycle:
                    cycles.append(cycle)

        return cycles

    def _get_refs_from_schema(self, schema: ModelSchema) -> list[str]:
        """Get all direct references from a schema."""
        refs = []

        if schema.ref:
            refs.append(schema.ref)

        if schema.properties:
            for prop_schema in schema.properties.values():
                refs.extend(self._get_refs_from_schema(prop_schema))

        if schema.items:
            refs.extend(self._get_refs_from_schema(schema.items))

        return refs
