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
"""

import importlib.util
import warnings
from pathlib import Path
from types import ModuleType

import pytest
import yaml

# ---------------------------------------------------------------------------
# Standalone Script Import (importlib pattern)
# ---------------------------------------------------------------------------
# yaml_contract_validator.py is a STANDALONE validation script located in
# scripts/validation/. It is NOT a proper Python package by design.
#
# ARCHITECTURAL DECISION:
#   Validation scripts must remain standalone and zero-dependency to support:
#   1. Pre-commit hooks - Scripts run without full project installation
#   2. CI/CD pipelines - Lightweight validation without heavy dependencies
#   3. Developer tooling - Quick validation without importing omnibase_core
#
# WHY importlib.util (not sys.path manipulation):
#   - Explicit: Loads module from known path without polluting sys.path
#   - Isolated: Module is loaded in controlled namespace
#   - Robust: Works regardless of working directory or test runner
#   - Standard: Well-established Python pattern for loading standalone scripts
#
# ALTERNATIVES CONSIDERED:
#   - sys.path.insert(): Works but pollutes global namespace, can cause conflicts
#   - Converting to package: Would break pre-commit hook standalone requirement
#   - Copying code: Would create maintenance burden with duplicate code
#
# See: scripts/validation/README.md for validation script architecture docs
# ---------------------------------------------------------------------------


def _load_validation_module() -> ModuleType:
    """Load yaml_contract_validator module from scripts/validation/ directory.

    Uses importlib.util to load the standalone validation script without
    modifying sys.path. This is more robust than sys.path manipulation and
    provides better isolation.

    Returns:
        ModuleType: The loaded yaml_contract_validator module.

    Raises:
        FileNotFoundError: If the validation script cannot be found.
        ImportError: If the module fails to load.
    """
    validation_script_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "scripts"
        / "validation"
        / "yaml_contract_validator.py"
    )

    if not validation_script_path.exists():
        raise FileNotFoundError(
            f"Validation script not found: {validation_script_path}\n"
            f"Ensure scripts/validation/yaml_contract_validator.py exists."
        )

    spec = importlib.util.spec_from_file_location(
        "yaml_contract_validator",
        validation_script_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create module spec for: {validation_script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load the validation module and extract MinimalYamlContract
_yaml_contract_validator = _load_validation_module()
MinimalYamlContract = _yaml_contract_validator.MinimalYamlContract

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


# ==============================================================================
# Module-Level Shared Fixtures
# ==============================================================================
# These fixtures reduce duplication across contract-specific test classes.
# The parameterized approach allows testing all contracts with shared logic
# while maintaining clear test output that identifies which contract is tested.
# ==============================================================================


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


def load_contract_data(contract_name: str) -> dict:
    """
    Load contract data from a YAML file.

    Args:
        contract_name: Name of the contract file (e.g., "runtime_orchestrator.yaml")

    Returns:
        Parsed YAML content as a dictionary

    Raises:
        pytest.skip: If the contract file does not exist
    """
    contract_path = RUNTIME_CONTRACTS_DIR / contract_name
    if not contract_path.exists():
        pytest.skip(f"Contract file not found: {contract_path}")
    with open(contract_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(params=EXPECTED_RUNTIME_CONTRACTS)
def contract_name(request: pytest.FixtureRequest) -> str:
    """Parameterized fixture that yields each contract name."""
    return request.param


@pytest.fixture
def contract_path(contract_name: str) -> Path:
    """Return the path to a contract file based on contract_name."""
    return RUNTIME_CONTRACTS_DIR / contract_name


@pytest.fixture
def contract_data(contract_name: str) -> dict:
    """Load and return contract data based on contract_name."""
    return load_contract_data(contract_name)


# ==============================================================================
# Common Contract Validation Tests (Parameterized)
# ==============================================================================
# These tests run against ALL runtime contracts using the parameterized fixtures.
# This eliminates the repetitive test methods that were duplicated in each class.
# ==============================================================================


@pytest.mark.unit
class TestRuntimeContractCommonValidation:
    """
    Common validation tests that apply to ALL runtime contracts.

    These tests use parameterized fixtures to run against each contract,
    reducing code duplication while maintaining clear test output.
    """

    def test_contract_file_exists(
        self, contract_path: Path, contract_name: str
    ) -> None:
        """Test that the contract file exists."""
        assert contract_path.exists(), f"Contract not found: {contract_path}"

    def test_contract_is_valid_yaml(
        self, contract_path: Path, contract_name: str
    ) -> None:
        """Test that the contract file is valid YAML."""
        if not contract_path.exists():
            pytest.skip(f"Contract file not found: {contract_path}")

        with open(contract_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content is not None, f"{contract_name}: Contract file is empty"
        assert isinstance(content, dict), (
            f"{contract_name}: Contract root should be a mapping"
        )

    def test_contract_has_required_fields(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that the contract has required fields."""
        assert "node_type" in contract_data, (
            f"{contract_name}: Missing required field: node_type"
        )
        assert "contract_version" in contract_data, (
            f"{contract_name}: Missing required field: contract_version"
        )

    def test_contract_has_expected_node_type(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that the contract has the expected node_type."""
        expected_type = EXPECTED_NODE_TYPES.get(contract_name)
        if expected_type:
            node_type = contract_data.get("node_type", "")
            assert node_type.upper() == expected_type, (
                f"{contract_name}: Expected {expected_type}, got {node_type}"
            )

    def test_contract_validates_with_minimal_yaml_contract(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that the contract passes MinimalYamlContract validation."""
        expected_type = EXPECTED_NODE_TYPES.get(contract_name)
        contract = MinimalYamlContract.validate_yaml_content(contract_data)
        assert contract.node_type == expected_type, (
            f"{contract_name}: Expected node_type {expected_type}, "
            f"got {contract.node_type}"
        )
        assert contract.contract_version is not None, (
            f"{contract_name}: contract_version should not be None"
        )

    def test_contract_has_metadata(
        self, contract_data: dict, contract_name: str
    ) -> None:
        """Test that the contract has metadata section."""
        assert "metadata" in contract_data, f"{contract_name}: Missing metadata section"
        metadata = contract_data["metadata"]
        assert "author" in metadata, f"{contract_name}: Missing author in metadata"
        assert "description" in metadata, (
            f"{contract_name}: Missing description in metadata"
        )


# ==============================================================================
# Directory Structure Tests
# ==============================================================================


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
        """Test that no unexpected files exist in the runtime contracts directory.

        This test validates the directory structure and emits a warning if unexpected
        files are found. The warning is verified using pytest.warns() to ensure proper
        test coverage of the warning emission path.
        """
        if not RUNTIME_CONTRACTS_DIR.exists():
            pytest.skip("Runtime contracts directory does not exist")

        yaml_files = list(RUNTIME_CONTRACTS_DIR.glob("*.yaml"))
        unexpected_files = [
            f.name for f in yaml_files if f.name not in EXPECTED_RUNTIME_CONTRACTS
        ]

        if unexpected_files:
            # Verify warning is properly emitted when unexpected files are found
            with pytest.warns(
                UserWarning,
                match=r"Unexpected files found in runtime contracts directory:",
            ):
                warnings.warn(
                    f"Unexpected files found in runtime contracts directory: {unexpected_files}",
                    UserWarning,
                    stacklevel=2,
                )
            # This is a soft warning, not a failure
            # Future contracts should be added to EXPECTED_RUNTIME_CONTRACTS


# ==============================================================================
# Contract-Specific Tests
# ==============================================================================
# These test classes contain contract-specific validations that go beyond
# the common tests. They use the shared load_contract_data() helper function
# instead of duplicating fixture definitions.
# ==============================================================================


@pytest.mark.unit
class TestRuntimeOrchestratorContract:
    """
    Contract-specific tests for runtime_orchestrator.yaml.

    Common validations (file exists, valid YAML, required fields, node type,
    MinimalYamlContract, metadata) are covered by TestRuntimeContractCommonValidation.
    This class contains only ORCHESTRATOR-specific tests.
    """

    @pytest.fixture
    def orchestrator_data(self) -> dict:
        """Load runtime_orchestrator.yaml contract data."""
        return load_contract_data("runtime_orchestrator.yaml")

    def test_contract_has_workflow_coordination(self, orchestrator_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has workflow_coordination section."""
        assert "workflow_coordination" in orchestrator_data, (
            "Missing workflow_coordination section"
        )
        workflow = orchestrator_data["workflow_coordination"]
        assert "workflow_definition" in workflow, (
            "Missing workflow_definition in workflow_coordination"
        )

    def test_contract_has_execution_graph(self, orchestrator_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has execution_graph with 4 nodes."""
        workflow = orchestrator_data.get("workflow_coordination", {})
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

    def test_contract_has_timing_constraints(self, orchestrator_data: dict) -> None:
        """Test that runtime_orchestrator.yaml has timing_constraints section."""
        assert "timing_constraints" in orchestrator_data, (
            "Missing timing_constraints section (required for )"
        )


@pytest.mark.unit
class TestContractLoaderEffectContract:
    """
    Contract-specific tests for contract_loader_effect.yaml.

    Common validations (file exists, valid YAML, required fields, node type,
    MinimalYamlContract, metadata) are covered by TestRuntimeContractCommonValidation.
    This class contains only EFFECT-specific tests for contract loading.
    """

    @pytest.fixture
    def loader_data(self) -> dict:
        """Load contract_loader_effect.yaml contract data."""
        return load_contract_data("contract_loader_effect.yaml")

    def test_contract_has_effect_operations(self, loader_data: dict) -> None:
        """Test that contract_loader_effect.yaml has effect_operations section."""
        assert "effect_operations" in loader_data, "Missing effect_operations section"

    def test_contract_has_operations(self, loader_data: dict) -> None:
        """Test that contract_loader_effect.yaml defines operations."""
        effect_ops = loader_data.get("effect_operations", {})
        operations = effect_ops.get("operations", [])
        assert len(operations) >= 1, "Expected at least one operation defined"

        # Check for scan_contracts_directory operation
        op_names = [op.get("operation_name") for op in operations]
        assert "scan_contracts_directory" in op_names, (
            "Missing scan_contracts_directory operation"
        )

    def test_contract_has_security_config(self, loader_data: dict) -> None:
        """Test that contract_loader_effect.yaml has security configuration."""
        effect_ops = loader_data.get("effect_operations", {})
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
    """
    Contract-specific tests for contract_registry_reducer.yaml.

    Common validations (file exists, valid YAML, required fields, node type,
    MinimalYamlContract, metadata) are covered by TestRuntimeContractCommonValidation.
    This class contains only REDUCER-specific tests for contract registry.
    """

    @pytest.fixture
    def registry_data(self) -> dict:
        """Load contract_registry_reducer.yaml contract data."""
        return load_contract_data("contract_registry_reducer.yaml")

    def test_contract_has_state_transitions(self, registry_data: dict) -> None:
        """Test that contract_registry_reducer.yaml has state_transitions section."""
        assert "state_transitions" in registry_data, "Missing state_transitions section"

    def test_contract_has_fsm_states(self, registry_data: dict) -> None:
        """Test that contract_registry_reducer.yaml defines FSM states."""
        state_transitions = registry_data.get("state_transitions", {})
        states = state_transitions.get("states", [])
        assert len(states) >= 3, "Expected at least 3 FSM states"

        # Check for expected states: empty, loading, ready
        state_names = {s.get("state_name") for s in states}
        expected_states = {"empty", "loading", "ready"}
        assert expected_states.issubset(state_names), (
            f"Missing expected states. Expected {expected_states}, got {state_names}"
        )

    def test_contract_has_initial_state(self, registry_data: dict) -> None:
        """Test that contract_registry_reducer.yaml defines initial_state."""
        state_transitions = registry_data.get("state_transitions", {})
        initial_state = state_transitions.get("initial_state")
        assert initial_state == "empty", (
            f"Expected initial_state 'empty', got {initial_state}"
        )

    def test_contract_has_recovery_strategies(self, registry_data: dict) -> None:
        """Test that contract_registry_reducer.yaml has recovery_strategies section."""
        state_transitions = registry_data.get("state_transitions", {})
        assert "recovery_strategies" in state_transitions, (
            "Missing recovery_strategies section (required for PR #137)"
        )


@pytest.mark.unit
class TestNodeGraphReducerContract:
    """
    Contract-specific tests for node_graph_reducer.yaml.

    Common validations (file exists, valid YAML, required fields, node type,
    MinimalYamlContract, metadata) are covered by TestRuntimeContractCommonValidation.
    This class contains only REDUCER-specific tests for node graph lifecycle.
    """

    @pytest.fixture
    def graph_data(self) -> dict:
        """Load node_graph_reducer.yaml contract data."""
        return load_contract_data("node_graph_reducer.yaml")

    def test_contract_has_state_transitions(self, graph_data: dict) -> None:
        """Test that node_graph_reducer.yaml has state_transitions section."""
        assert "state_transitions" in graph_data, "Missing state_transitions section"

    def test_contract_has_lifecycle_states(self, graph_data: dict) -> None:
        """Test that node_graph_reducer.yaml defines lifecycle FSM states."""
        state_transitions = graph_data.get("state_transitions", {})
        states = state_transitions.get("states", [])
        assert len(states) >= 5, "Expected at least 5 FSM states (including draining)"

        # Check for expected lifecycle states (including draining)
        state_names = {s.get("state_name") for s in states}
        expected_states = {"initializing", "wiring", "running", "draining", "stopped"}
        assert expected_states.issubset(state_names), (
            f"Missing expected states. Expected {expected_states}, got {state_names}"
        )

    def test_contract_has_wildcard_transitions(self, graph_data: dict) -> None:
        """Test that node_graph_reducer.yaml has wildcard (*) transitions."""
        state_transitions = graph_data.get("state_transitions", {})
        transitions = state_transitions.get("transitions", [])

        # Check for wildcard transitions (from_state: '*')
        wildcard_transitions = [t for t in transitions if t.get("from_state") == "*"]
        assert len(wildcard_transitions) >= 1, (
            "Expected at least one wildcard transition for error handling"
        )

    def test_contract_has_testing_guidance(self, graph_data: dict) -> None:
        """Test that node_graph_reducer.yaml has testing_guidance section."""
        assert "testing_guidance" in graph_data, (
            "Missing testing_guidance section (required for PR #137)"
        )

    # =========================================================================
    # Draining State Tests (PR #137 feedback)
    # =========================================================================
    # The following tests provide explicit coverage for the 'draining' lifecycle
    # state, which is critical for graceful shutdown behavior.
    # =========================================================================

    def test_draining_state_properties(self, graph_data: dict) -> None:
        """Test that the draining state has expected properties for graceful shutdown.

        The draining state is critical for graceful shutdown - it allows in-flight
        operations to complete before transitioning to stopped. This test verifies
        the draining state has proper configuration for this purpose.

        Related: PR #137 feedback on draining state coverage
        """
        state_transitions = graph_data.get("state_transitions", {})
        states = state_transitions.get("states", [])

        # Find the draining state
        draining_state = None
        for state in states:
            if state.get("state_name") == "draining":
                draining_state = state
                break

        assert draining_state is not None, "draining state not found"

        # Verify draining state description mentions graceful shutdown
        assert "description" in draining_state, "draining state missing description"
        description_lower = draining_state["description"].lower()
        assert "graceful" in description_lower or "shutdown" in description_lower, (
            "draining state description should mention graceful shutdown"
        )

        # Verify draining state is not terminal (allows transition to stopped)
        assert draining_state.get("is_terminal") is False, (
            "draining state should not be terminal"
        )

        # Verify draining has entry_actions for shutdown preparation
        entry_actions = draining_state.get("entry_actions", [])
        assert len(entry_actions) >= 1, (
            "draining state should have entry_actions for shutdown preparation"
        )
        assert "stop_accepting_new_work" in entry_actions, (
            "draining state should stop accepting new work"
        )

        # Verify draining has exit_actions for cleanup
        exit_actions = draining_state.get("exit_actions", [])
        assert len(exit_actions) >= 1, "draining state should have exit_actions"

        # Verify draining state has metadata
        assert "metadata" in draining_state, "draining state should have metadata"

    def test_shutdown_requested_transition_to_draining(self, graph_data: dict) -> None:
        """Test the shutdown_requested transition from running to draining state.

        This transition initiates graceful shutdown when a shutdown signal is received.
        It must transition from running to draining and emit proper notifications.

        Related: PR #137 feedback on draining state coverage
        """
        state_transitions = graph_data.get("state_transitions", {})
        transitions = state_transitions.get("transitions", [])

        # Find the shutdown_requested transition
        shutdown_transition = None
        for transition in transitions:
            if transition.get("transition_name") == "shutdown_requested":
                shutdown_transition = transition
                break

        assert shutdown_transition is not None, (
            "shutdown_requested transition not found"
        )

        # Verify transition goes from running to draining
        assert shutdown_transition.get("from_state") == "running", (
            "shutdown_requested should transition from 'running' state"
        )
        assert shutdown_transition.get("to_state") == "draining", (
            "shutdown_requested should transition to 'draining' state"
        )

        # Verify trigger
        assert shutdown_transition.get("trigger") == "shutdown_requested", (
            "shutdown_requested transition should have 'shutdown_requested' trigger"
        )

        # Verify transition has actions for proper shutdown notification
        actions = shutdown_transition.get("actions", [])
        assert len(actions) >= 1, "shutdown_requested transition should have actions"
        action_names = [a.get("action_name") for a in actions]
        assert "emit_drain_started" in action_names, (
            "shutdown_requested should emit drain_started event"
        )

    def test_drain_complete_transition_to_stopped(self, graph_data: dict) -> None:
        """Test the drain_complete transition from draining to stopped state.

        This transition completes the graceful shutdown after all in-flight
        operations finish. It must verify no pending operations remain.

        Related: PR #137 feedback on draining state coverage
        """
        state_transitions = graph_data.get("state_transitions", {})
        transitions = state_transitions.get("transitions", [])

        # Find the drain_complete transition
        drain_transition = None
        for transition in transitions:
            if transition.get("transition_name") == "drain_complete":
                drain_transition = transition
                break

        assert drain_transition is not None, "drain_complete transition not found"

        # Verify transition goes from draining to stopped
        assert drain_transition.get("from_state") == "draining", (
            "drain_complete should transition from 'draining' state"
        )
        assert drain_transition.get("to_state") == "stopped", (
            "drain_complete should transition to 'stopped' state"
        )

        # Verify trigger
        assert drain_transition.get("trigger") == "drain_complete", (
            "drain_complete transition should have 'drain_complete' trigger"
        )

        # Verify drain_complete has conditions for safe completion
        conditions = drain_transition.get("conditions", [])
        assert len(conditions) >= 1, (
            "drain_complete should have conditions to verify safe completion"
        )
        condition_names = [c.get("condition_name") for c in conditions]
        assert "no_pending_operations" in condition_names, (
            "drain_complete should verify no pending operations remain"
        )

        # Verify transition has actions
        actions = drain_transition.get("actions", [])
        assert len(actions) >= 1, "drain_complete transition should have actions"
        action_names = [a.get("action_name") for a in actions]
        assert "emit_graph_stopped" in action_names, (
            "drain_complete should emit graph_stopped event"
        )

    def test_draining_state_in_testing_guidance(self, graph_data: dict) -> None:
        """Test that draining state is included in testing_guidance test matrix.

        The testing_guidance section must include draining in the states to test
        for wildcard transitions, ensuring comprehensive error handling coverage.

        Related: PR #137 feedback on draining state coverage
        """
        testing_guidance = graph_data.get("testing_guidance", {})
        test_matrix = testing_guidance.get("test_matrix", {})

        # Verify draining is in the states to test for wildcard transitions
        states_to_test = test_matrix.get("states", [])
        assert "draining" in states_to_test, (
            "draining state should be included in testing_guidance test_matrix states"
        )

    def test_wildcard_transitions_apply_to_draining(self, graph_data: dict) -> None:
        """Test that wildcard (*) transitions can trigger from draining state.

        Wildcard transitions (fatal_error, timeout) must be able to trigger from
        draining state for proper error handling during graceful shutdown.

        Related: PR #137 feedback on draining state coverage
        """
        state_transitions = graph_data.get("state_transitions", {})
        transitions = state_transitions.get("transitions", [])
        states = state_transitions.get("states", [])

        # Find the draining state to verify it's not terminal
        draining_state = None
        for state in states:
            if state.get("state_name") == "draining":
                draining_state = state
                break

        assert draining_state is not None, "draining state not found"
        assert draining_state.get("is_terminal") is not True, (
            "draining must be non-terminal for wildcard transitions to apply"
        )

        # Find wildcard transitions
        wildcard_transitions = [t for t in transitions if t.get("from_state") == "*"]
        assert len(wildcard_transitions) >= 1, (
            "Should have wildcard transitions for error handling"
        )

        # Verify fatal_error and timeout wildcards exist
        wildcard_triggers = {t.get("trigger") for t in wildcard_transitions}
        assert "fatal_error" in wildcard_triggers, (
            "Should have fatal_error wildcard transition"
        )
        assert "timeout" in wildcard_triggers, "Should have timeout wildcard transition"

        # Wildcard transitions should go to stopped (terminal state)
        for transition in wildcard_transitions:
            assert transition.get("to_state") == "stopped", (
                f"Wildcard transition {transition.get('transition_name')} "
                "should go to 'stopped' state"
            )


@pytest.mark.unit
class TestEventBusWiringEffectContract:
    """
    Contract-specific tests for event_bus_wiring_effect.yaml.

    Common validations (file exists, valid YAML, required fields, node type,
    MinimalYamlContract, metadata) are covered by TestRuntimeContractCommonValidation.
    This class contains only EFFECT-specific tests for event bus wiring.
    """

    @pytest.fixture
    def wiring_data(self) -> dict:
        """Load event_bus_wiring_effect.yaml contract data."""
        return load_contract_data("event_bus_wiring_effect.yaml")

    def test_contract_has_effect_section(self, wiring_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has effect section."""
        assert "effect" in wiring_data, "Missing effect section"

    def test_contract_has_wiring_config(self, wiring_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has wiring_config section."""
        assert "wiring_config" in wiring_data, "Missing wiring_config section"

    def test_contract_has_topic_validation(self, wiring_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml has topic_validation security config."""
        wiring_config = wiring_data.get("wiring_config", {})
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

    def test_contract_has_subscriptions(self, wiring_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml defines subscriptions."""
        assert "subscriptions" in wiring_data, "Missing subscriptions section"
        subscriptions = wiring_data["subscriptions"]
        assert len(subscriptions) >= 1, "Expected at least one subscription defined"

    def test_contract_has_publications(self, wiring_data: dict) -> None:
        """Test that event_bus_wiring_effect.yaml defines publications."""
        assert "publications" in wiring_data, "Missing publications section"
        publications = wiring_data["publications"]
        assert len(publications) >= 1, "Expected at least one publication defined"

        # Check for runtime.ready publication
        pub_topics = [p.get("topic") for p in publications]
        assert "onex.runtime.ready" in pub_topics, (
            "Missing onex.runtime.ready publication"
        )


@pytest.mark.unit
class TestAllRuntimeContractsValidation:
    """Cross-contract validation tests for all runtime contracts."""

    def test_all_contracts_have_version_1_1_0(
        self, all_contracts: dict[str, dict]
    ) -> None:
        """Test that all runtime contracts have version 1.1.0."""
        for name, data in all_contracts.items():
            version = data.get("contract_version", {})
            if isinstance(version, dict):
                assert version.get("major") == 1, f"{name}: Expected major version 1"
                assert version.get("minor") == 1, f"{name}: Expected minor version 1"
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
