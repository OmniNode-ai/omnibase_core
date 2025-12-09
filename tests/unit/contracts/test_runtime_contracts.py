#!/usr/bin/env python3
"""
Unit Tests for Runtime Contracts.

This module provides comprehensive validation tests for the runtime orchestrator
YAML contracts located in contracts/runtime/. These contracts define the ONEX
runtime's self-hosted architecture using the 4-node pattern.

Runtime Contracts Tested:
    - runtime_orchestrator.yaml: Main orchestrator coordinating runtime lifecycle
    - contract_loader_effect.yaml: EFFECT node for scanning contract files
    - contract_registry_reducer.yaml: REDUCER node for contract state management
    - node_graph_reducer.yaml: REDUCER node for node graph lifecycle
    - event_bus_wiring_effect.yaml: EFFECT node for event bus subscriptions

Test Coverage:
    - File existence and valid YAML syntax
    - Required fields (node_type, contract_version)
    - Contract validation using MinimalYamlContract
    - Node type classification consistency
    - Directory structure validation

Related:
    - PR #137: Runtime orchestrator contract validation
    - Linear Ticket: OMN-467
"""

import sys
import warnings
from pathlib import Path

import pytest
import yaml

# NOTE: sys.path manipulation required because yaml_contract_validator.py is
# a standalone validation script in scripts/validation/, not a proper Python package.
# This is intentional - validation scripts must work standalone for pre-commit hooks.
# Using .resolve() ensures absolute path; guard check prevents duplicate entries.
VALIDATION_SCRIPTS_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "validation"
)
if str(VALIDATION_SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(VALIDATION_SCRIPTS_PATH))

from yaml_contract_validator import MinimalYamlContract

# Path to the runtime contracts directory
RUNTIME_CONTRACTS_DIR = (
    Path(__file__).parent.parent.parent.parent / "contracts" / "runtime"
)

# Expected runtime contract files
EXPECTED_RUNTIME_CONTRACTS = [
    "runtime_orchestrator.yaml",
    "contract_loader_effect.yaml",
    "contract_registry_reducer.yaml",
    "node_graph_reducer.yaml",
    "event_bus_wiring_effect.yaml",
]

# Expected node types for each contract (uppercase per v0.4.0+)
EXPECTED_NODE_TYPES = {
    "runtime_orchestrator.yaml": "ORCHESTRATOR_GENERIC",
    "contract_loader_effect.yaml": "EFFECT_GENERIC",
    "contract_registry_reducer.yaml": "REDUCER_GENERIC",
    "node_graph_reducer.yaml": "REDUCER_GENERIC",
    "event_bus_wiring_effect.yaml": "EFFECT_GENERIC",
}


@pytest.fixture
def all_contracts() -> dict[str, dict]:
    """Load all runtime contracts."""
    contracts = {}
    for contract_name in EXPECTED_RUNTIME_CONTRACTS:
        contract_path = RUNTIME_CONTRACTS_DIR / contract_name
        if contract_path.exists():
            with open(contract_path, encoding="utf-8") as f:
                contracts[contract_name] = yaml.safe_load(f)
    return contracts


@pytest.mark.unit
class TestRuntimeContractsDirectoryStructure:
    """Tests for runtime contracts directory structure validation."""

    def test_runtime_contracts_directory_exists(self) -> None:
        """Test that the runtime contracts directory exists."""
        assert RUNTIME_CONTRACTS_DIR.exists(), (
            f"Runtime contracts directory not found: {RUNTIME_CONTRACTS_DIR}"
        )
        assert RUNTIME_CONTRACTS_DIR.is_dir(), (
            f"Runtime contracts path is not a directory: {RUNTIME_CONTRACTS_DIR}"
        )

    def test_all_expected_contracts_exist(self) -> None:
        """Test that all expected runtime contract files exist."""
        missing_contracts = []
        for contract_name in EXPECTED_RUNTIME_CONTRACTS:
            contract_path = RUNTIME_CONTRACTS_DIR / contract_name
            if not contract_path.exists():
                missing_contracts.append(contract_name)

        assert not missing_contracts, f"Missing runtime contracts: {missing_contracts}"

    def test_no_unexpected_files_in_runtime_directory(self) -> None:
        """Test that no unexpected files exist in the runtime contracts directory."""
        if not RUNTIME_CONTRACTS_DIR.exists():
            pytest.skip("Runtime contracts directory does not exist")

        yaml_files = list(RUNTIME_CONTRACTS_DIR.glob("*.yaml"))
        unexpected_files = [
            f.name for f in yaml_files if f.name not in EXPECTED_RUNTIME_CONTRACTS
        ]

        # Allow unexpected files but warn about them
        if unexpected_files:
            warnings.warn(
                f"Unexpected files found in runtime contracts directory: {unexpected_files}",
                UserWarning,
                stacklevel=2,
            )
            # This is a soft warning, not a failure
            # Future contracts should be added to EXPECTED_RUNTIME_CONTRACTS


@pytest.mark.unit
class TestRuntimeOrchestratorContract:
    """Tests for runtime_orchestrator.yaml contract validation."""

    @pytest.fixture
    def contract_path(self) -> Path:
        """Return path to runtime_orchestrator.yaml."""
        return RUNTIME_CONTRACTS_DIR / "runtime_orchestrator.yaml"

    @pytest.fixture
    def contract_data(self, contract_path: Path) -> dict:
        """Load and return contract data."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")
        with open(contract_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_contract_file_exists(self, contract_path: Path) -> None:
        """Test that runtime_orchestrator.yaml exists."""
        assert contract_path.exists(), f"Contract not found: {contract_path}"

    def test_contract_is_valid_yaml(self, contract_path: Path) -> None:
        """Test that runtime_orchestrator.yaml is valid YAML."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        with open(contract_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None, "Contract file is empty"
        assert isinstance(content, dict), "Contract root should be a mapping"

    def test_contract_has_required_fields(self, contract_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has required fields."""
        assert "node_type" in contract_data, "Missing required field: node_type"
        assert "contract_version" in contract_data, (
            "Missing required field: contract_version"
        )

    def test_contract_node_type_is_orchestrator(self, contract_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has ORCHESTRATOR_GENERIC node_type."""
        node_type = contract_data.get("node_type", "")
        assert node_type.upper() == "ORCHESTRATOR_GENERIC", (
            f"Expected ORCHESTRATOR_GENERIC, got {node_type}"
        )

    def test_contract_validates_with_minimal_yaml_contract(
        self, contract_data: dict
    ) -> None:
        """Test that runtime_orchestrator.yaml passes MinimalYamlContract validation."""
        contract = MinimalYamlContract.validate_yaml_content(contract_data)
        assert contract.node_type == "ORCHESTRATOR_GENERIC"
        assert contract.contract_version is not None

    def test_contract_has_workflow_coordination(self, contract_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has workflow_coordination section."""
        assert "workflow_coordination" in contract_data, (
            "Missing workflow_coordination section"
        )
        workflow = contract_data["workflow_coordination"]
        assert "workflow_definition" in workflow, (
            "Missing workflow_definition in workflow_coordination"
        )

    def test_contract_has_execution_graph(self, contract_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has execution_graph with 4 nodes."""
        workflow = contract_data.get("workflow_coordination", {})
        workflow_def = workflow.get("workflow_definition", {})
        exec_graph = workflow_def.get("execution_graph", {})
        nodes = exec_graph.get("nodes", [])

        assert len(nodes) == 4, f"Expected 4 nodes in execution graph, got {len(nodes)}"

        # Verify expected node IDs
        node_ids = {node.get("node_id") for node in nodes}
        expected_ids = {
            "contract_loader",
            "contract_registry",
            "node_graph",
            "event_bus_wiring",
        }
        assert node_ids == expected_ids, (
            f"Unexpected node IDs. Expected {expected_ids}, got {node_ids}"
        )

    def test_contract_has_timing_constraints(self, contract_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has timing_constraints section."""
        assert "timing_constraints" in contract_data, (
            "Missing timing_constraints section (required for OMN-467)"
        )

    def test_contract_has_metadata(self, contract_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has metadata section."""
        assert "metadata" in contract_data, "Missing metadata section"
        metadata = contract_data["metadata"]
        assert "author" in metadata, "Missing author in metadata"
        assert "description" in metadata, "Missing description in metadata"


@pytest.mark.unit
class TestContractLoaderEffectContract:
    """Tests for contract_loader_effect.yaml contract validation."""

    @pytest.fixture
    def contract_path(self) -> Path:
        """Return path to contract_loader_effect.yaml."""
        return RUNTIME_CONTRACTS_DIR / "contract_loader_effect.yaml"

    @pytest.fixture
    def contract_data(self, contract_path: Path) -> dict:
        """Load and return contract data."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")
        with open(contract_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_contract_file_exists(self, contract_path: Path) -> None:
        """Test that contract_loader_effect.yaml exists."""
        assert contract_path.exists(), f"Contract not found: {contract_path}"

    def test_contract_is_valid_yaml(self, contract_path: Path) -> None:
        """Test that contract_loader_effect.yaml is valid YAML."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        with open(contract_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None, "Contract file is empty"
        assert isinstance(content, dict), "Contract root should be a mapping"

    def test_contract_has_required_fields(self, contract_data: dict) -> None:
        """Test that contract_loader_effect.yaml has required fields."""
        assert "node_type" in contract_data, "Missing required field: node_type"
        assert "contract_version" in contract_data, (
            "Missing required field: contract_version"
        )

    def test_contract_node_type_is_effect(self, contract_data: dict) -> None:
        """Test that contract_loader_effect.yaml has EFFECT_GENERIC node_type."""
        node_type = contract_data.get("node_type", "")
        assert node_type.upper() == "EFFECT_GENERIC", (
            f"Expected EFFECT_GENERIC, got {node_type}"
        )

    def test_contract_validates_with_minimal_yaml_contract(
        self, contract_data: dict
    ) -> None:
        """Test that contract_loader_effect.yaml passes MinimalYamlContract validation."""
        contract = MinimalYamlContract.validate_yaml_content(contract_data)
        assert contract.node_type == "EFFECT_GENERIC"
        assert contract.contract_version is not None

    def test_contract_has_effect_operations(self, contract_data: dict) -> None:
        """Test that contract_loader_effect.yaml has effect_operations section."""
        assert "effect_operations" in contract_data, "Missing effect_operations section"

    def test_contract_has_operations(self, contract_data: dict) -> None:
        """Test that contract_loader_effect.yaml defines operations."""
        effect_ops = contract_data.get("effect_operations", {})
        operations = effect_ops.get("operations", [])
        assert len(operations) >= 1, "Expected at least one operation defined"

        # Check for scan_contracts_directory operation
        op_names = [op.get("operation_name") for op in operations]
        assert "scan_contracts_directory" in op_names, (
            "Missing scan_contracts_directory operation"
        )

    def test_contract_has_security_config(self, contract_data: dict) -> None:
        """Test that contract_loader_effect.yaml has security configuration."""
        effect_ops = contract_data.get("effect_operations", {})
        operations = effect_ops.get("operations", [])

        # Check that scan operation has security config
        for op in operations:
            if op.get("operation_name") == "scan_contracts_directory":
                io_config = op.get("io_config", {})
                assert "security" in io_config, (
                    "Missing security config in scan_contracts_directory"
                )
                break


@pytest.mark.unit
class TestContractRegistryReducerContract:
    """Tests for contract_registry_reducer.yaml contract validation."""

    @pytest.fixture
    def contract_path(self) -> Path:
        """Return path to contract_registry_reducer.yaml."""
        return RUNTIME_CONTRACTS_DIR / "contract_registry_reducer.yaml"

    @pytest.fixture
    def contract_data(self, contract_path: Path) -> dict:
        """Load and return contract data."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")
        with open(contract_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_contract_file_exists(self, contract_path: Path) -> None:
        """Test that contract_registry_reducer.yaml exists."""
        assert contract_path.exists(), f"Contract not found: {contract_path}"

    def test_contract_is_valid_yaml(self, contract_path: Path) -> None:
        """Test that contract_registry_reducer.yaml is valid YAML."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        with open(contract_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None, "Contract file is empty"
        assert isinstance(content, dict), "Contract root should be a mapping"

    def test_contract_has_required_fields(self, contract_data: dict) -> None:
        """Test that contract_registry_reducer.yaml has required fields."""
        assert "node_type" in contract_data, "Missing required field: node_type"
        assert "contract_version" in contract_data, (
            "Missing required field: contract_version"
        )

    def test_contract_node_type_is_reducer(self, contract_data: dict) -> None:
        """Test that contract_registry_reducer.yaml has REDUCER_GENERIC node_type."""
        node_type = contract_data.get("node_type", "")
        assert node_type.upper() == "REDUCER_GENERIC", (
            f"Expected REDUCER_GENERIC, got {node_type}"
        )

    def test_contract_validates_with_minimal_yaml_contract(
        self, contract_data: dict
    ) -> None:
        """Test that contract_registry_reducer.yaml passes MinimalYamlContract validation."""
        contract = MinimalYamlContract.validate_yaml_content(contract_data)
        assert contract.node_type == "REDUCER_GENERIC"
        assert contract.contract_version is not None

    def test_contract_has_state_transitions(self, contract_data: dict) -> None:
        """Test that contract_registry_reducer.yaml has state_transitions section."""
        assert "state_transitions" in contract_data, "Missing state_transitions section"

    def test_contract_has_fsm_states(self, contract_data: dict) -> None:
        """Test that contract_registry_reducer.yaml defines FSM states."""
        state_transitions = contract_data.get("state_transitions", {})
        states = state_transitions.get("states", [])
        assert len(states) >= 3, "Expected at least 3 FSM states"

        # Check for expected states: empty, loading, ready
        state_names = {s.get("state_name") for s in states}
        expected_states = {"empty", "loading", "ready"}
        assert expected_states.issubset(state_names), (
            f"Missing expected states. Expected {expected_states}, got {state_names}"
        )

    def test_contract_has_initial_state(self, contract_data: dict) -> None:
        """Test that contract_registry_reducer.yaml defines initial_state."""
        state_transitions = contract_data.get("state_transitions", {})
        initial_state = state_transitions.get("initial_state")
        assert initial_state == "empty", (
            f"Expected initial_state 'empty', got {initial_state}"
        )

    def test_contract_has_recovery_strategies(self, contract_data: dict) -> None:
        """Test that contract_registry_reducer.yaml has recovery_strategies section."""
        state_transitions = contract_data.get("state_transitions", {})
        assert "recovery_strategies" in state_transitions, (
            "Missing recovery_strategies section (required for PR #137)"
        )


@pytest.mark.unit
class TestNodeGraphReducerContract:
    """Tests for node_graph_reducer.yaml contract validation."""

    @pytest.fixture
    def contract_path(self) -> Path:
        """Return path to node_graph_reducer.yaml."""
        return RUNTIME_CONTRACTS_DIR / "node_graph_reducer.yaml"

    @pytest.fixture
    def contract_data(self, contract_path: Path) -> dict:
        """Load and return contract data."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")
        with open(contract_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_contract_file_exists(self, contract_path: Path) -> None:
        """Test that node_graph_reducer.yaml exists."""
        assert contract_path.exists(), f"Contract not found: {contract_path}"

    def test_contract_is_valid_yaml(self, contract_path: Path) -> None:
        """Test that node_graph_reducer.yaml is valid YAML."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        with open(contract_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None, "Contract file is empty"
        assert isinstance(content, dict), "Contract root should be a mapping"

    def test_contract_has_required_fields(self, contract_data: dict) -> None:
        """Test that node_graph_reducer.yaml has required fields."""
        assert "node_type" in contract_data, "Missing required field: node_type"
        assert "contract_version" in contract_data, (
            "Missing required field: contract_version"
        )

    def test_contract_node_type_is_reducer(self, contract_data: dict) -> None:
        """Test that node_graph_reducer.yaml has REDUCER_GENERIC node_type."""
        node_type = contract_data.get("node_type", "")
        assert node_type.upper() == "REDUCER_GENERIC", (
            f"Expected REDUCER_GENERIC, got {node_type}"
        )

    def test_contract_validates_with_minimal_yaml_contract(
        self, contract_data: dict
    ) -> None:
        """Test that node_graph_reducer.yaml passes MinimalYamlContract validation."""
        contract = MinimalYamlContract.validate_yaml_content(contract_data)
        assert contract.node_type == "REDUCER_GENERIC"
        assert contract.contract_version is not None

    def test_contract_has_state_transitions(self, contract_data: dict) -> None:
        """Test that node_graph_reducer.yaml has state_transitions section."""
        assert "state_transitions" in contract_data, "Missing state_transitions section"

    def test_contract_has_lifecycle_states(self, contract_data: dict) -> None:
        """Test that node_graph_reducer.yaml defines lifecycle FSM states."""
        state_transitions = contract_data.get("state_transitions", {})
        states = state_transitions.get("states", [])
        assert len(states) >= 5, "Expected at least 5 FSM states (including draining)"

        # Check for expected lifecycle states (including draining)
        state_names = {s.get("state_name") for s in states}
        expected_states = {"initializing", "wiring", "running", "draining", "stopped"}
        assert expected_states.issubset(state_names), (
            f"Missing expected states. Expected {expected_states}, got {state_names}"
        )

    def test_contract_has_wildcard_transitions(self, contract_data: dict) -> None:
        """Test that node_graph_reducer.yaml has wildcard (*) transitions for error handling."""
        state_transitions = contract_data.get("state_transitions", {})
        transitions = state_transitions.get("transitions", [])

        # Check for wildcard transitions (from_state: '*')
        wildcard_transitions = [t for t in transitions if t.get("from_state") == "*"]
        assert len(wildcard_transitions) >= 1, (
            "Expected at least one wildcard transition for error handling"
        )

    def test_contract_has_testing_guidance(self, contract_data: dict) -> None:
        """Test that node_graph_reducer.yaml has testing_guidance section."""
        assert "testing_guidance" in contract_data, (
            "Missing testing_guidance section (required for PR #137)"
        )


@pytest.mark.unit
class TestEventBusWiringEffectContract:
    """Tests for event_bus_wiring_effect.yaml contract validation."""

    @pytest.fixture
    def contract_path(self) -> Path:
        """Return path to event_bus_wiring_effect.yaml."""
        return RUNTIME_CONTRACTS_DIR / "event_bus_wiring_effect.yaml"

    @pytest.fixture
    def contract_data(self, contract_path: Path) -> dict:
        """Load and return contract data."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")
        with open(contract_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_contract_file_exists(self, contract_path: Path) -> None:
        """Test that event_bus_wiring_effect.yaml exists."""
        assert contract_path.exists(), f"Contract not found: {contract_path}"

    def test_contract_is_valid_yaml(self, contract_path: Path) -> None:
        """Test that event_bus_wiring_effect.yaml is valid YAML."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        with open(contract_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None, "Contract file is empty"
        assert isinstance(content, dict), "Contract root should be a mapping"

    def test_contract_has_required_fields(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has required fields."""
        assert "node_type" in contract_data, "Missing required field: node_type"
        assert "contract_version" in contract_data, (
            "Missing required field: contract_version"
        )

    def test_contract_node_type_is_effect(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has EFFECT_GENERIC node_type."""
        node_type = contract_data.get("node_type", "")
        assert node_type.upper() == "EFFECT_GENERIC", (
            f"Expected EFFECT_GENERIC, got {node_type}"
        )

    def test_contract_validates_with_minimal_yaml_contract(
        self, contract_data: dict
    ) -> None:
        """Test that event_bus_wiring_effect.yaml passes MinimalYamlContract validation."""
        contract = MinimalYamlContract.validate_yaml_content(contract_data)
        assert contract.node_type == "EFFECT_GENERIC"
        assert contract.contract_version is not None

    def test_contract_has_effect_section(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has effect section."""
        assert "effect" in contract_data, "Missing effect section"

    def test_contract_has_wiring_config(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has wiring_config section."""
        assert "wiring_config" in contract_data, "Missing wiring_config section"

    def test_contract_has_topic_validation(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has topic_validation security config."""
        wiring_config = contract_data.get("wiring_config", {})
        assert "topic_validation" in wiring_config, (
            "Missing topic_validation in wiring_config (security requirement)"
        )

        topic_validation = wiring_config["topic_validation"]
        assert topic_validation.get("enabled") is True, (
            "topic_validation should be enabled"
        )
        assert "allowed_pattern" in topic_validation, (
            "Missing allowed_pattern in topic_validation"
        )
        assert "deny_patterns" in topic_validation, (
            "Missing deny_patterns in topic_validation"
        )

    def test_contract_has_subscriptions(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml defines subscriptions."""
        assert "subscriptions" in contract_data, "Missing subscriptions section"
        subscriptions = contract_data["subscriptions"]
        assert len(subscriptions) >= 1, "Expected at least one subscription defined"

    def test_contract_has_publications(self, contract_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml defines publications."""
        assert "publications" in contract_data, "Missing publications section"
        publications = contract_data["publications"]
        assert len(publications) >= 1, "Expected at least one publication defined"

        # Check for runtime.ready publication
        pub_topics = [p.get("topic") for p in publications]
        assert "onex.runtime.ready" in pub_topics, (
            "Missing onex.runtime.ready publication"
        )


@pytest.mark.unit
class TestAllRuntimeContractsValidation:
    """Cross-contract validation tests for all runtime contracts."""

    def test_all_contracts_have_version_1_0_0(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that all runtime contracts have version 1.0.0."""
        for name, data in all_contracts.items():
            version = data.get("contract_version", {})
            if isinstance(version, dict):
                assert version.get("major") == 1, f"{name}: Expected major version 1"
                assert version.get("minor") == 0, f"{name}: Expected minor version 0"
                assert version.get("patch") == 0, f"{name}: Expected patch version 0"

    def test_all_contracts_pass_minimal_validation(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that all runtime contracts pass MinimalYamlContract validation."""
        for name, data in all_contracts.items():
            try:
                contract = MinimalYamlContract.validate_yaml_content(data)
                assert contract.node_type in EXPECTED_NODE_TYPES.values(), (
                    f"{name}: Unexpected node_type {contract.node_type}"
                )
            except Exception as e:
                pytest.fail(f"{name}: Validation failed with {e}")

    def test_all_contracts_have_metadata(self, all_contracts: dict[str, dict]) -> None:
        """Test that all runtime contracts have metadata section."""
        for name, data in all_contracts.items():
            assert "metadata" in data, f"{name}: Missing metadata section"
            metadata = data["metadata"]
            assert "author" in metadata, f"{name}: Missing author in metadata"
            assert "description" in metadata, f"{name}: Missing description in metadata"
            assert "tags" in metadata, f"{name}: Missing tags in metadata"

    def test_all_contracts_have_correct_node_type(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that all runtime contracts have the expected node_type."""
        for name, data in all_contracts.items():
            expected_type = EXPECTED_NODE_TYPES.get(name)
            if expected_type:
                actual_type = data.get("node_type", "").upper()
                assert actual_type == expected_type, (
                    f"{name}: Expected {expected_type}, got {actual_type}"
                )

    def test_effect_contracts_have_operations(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that EFFECT contracts have operations defined."""
        effect_contracts = [
            "contract_loader_effect.yaml",
            "event_bus_wiring_effect.yaml",
        ]
        for name in effect_contracts:
            if name in all_contracts:
                data = all_contracts[name]
                # Check for either effect_operations or effect section
                has_operations = "effect_operations" in data or "effect" in data
                assert has_operations, f"{name}: Missing effect operations section"

    def test_reducer_contracts_have_state_transitions(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that REDUCER contracts have state_transitions defined."""
        reducer_contracts = [
            "contract_registry_reducer.yaml",
            "node_graph_reducer.yaml",
        ]
        for name in reducer_contracts:
            if name in all_contracts:
                data = all_contracts[name]
                assert "state_transitions" in data, (
                    f"{name}: Missing state_transitions section"
                )

    def test_linear_ticket_references(self, all_contracts: dict[str, dict]) -> None:
        """Test that runtime contracts reference the correct Linear ticket."""
        for name, data in all_contracts.items():
            metadata = data.get("metadata", {})
            linear_ticket = metadata.get("linear_ticket")
            # Linear ticket should be OMN-467 for runtime contracts
            if linear_ticket:
                assert linear_ticket == "OMN-467", (
                    f"{name}: Expected Linear ticket OMN-467, got {linear_ticket}"
                )


@pytest.mark.unit
class TestContractVersionFormats:
    """Tests for contract_version format handling across runtime contracts."""

    def test_contract_version_dict_format(self, all_contracts: dict[str, dict]) -> None:
        """Test that contract_version uses dict format with major/minor/patch."""
        for name, data in all_contracts.items():
            version = data.get("contract_version")
            assert version is not None, f"{name}: Missing contract_version"
            assert isinstance(version, dict), (
                f"{name}: contract_version should be dict format"
            )
            assert "major" in version, f"{name}: Missing major in contract_version"
            assert "minor" in version, f"{name}: Missing minor in contract_version"
            assert "patch" in version, f"{name}: Missing patch in contract_version"

    def test_contract_version_values_are_integers(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that contract_version values are integers."""
        for name, data in all_contracts.items():
            version = data.get("contract_version", {})
            if isinstance(version, dict):
                assert isinstance(version.get("major"), int), (
                    f"{name}: major should be integer"
                )
                assert isinstance(version.get("minor"), int), (
                    f"{name}: minor should be integer"
                )
                assert isinstance(version.get("patch"), int), (
                    f"{name}: patch should be integer"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
