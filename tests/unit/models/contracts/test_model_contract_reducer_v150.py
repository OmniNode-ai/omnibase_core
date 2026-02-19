# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for ModelContractReducer v1.5.0 changes.

Tests the v1.5.0 updates to ModelContractReducer including:
- Fingerprint field validation (valid/invalid patterns)
- state_machine alias backwards compatibility with state_transitions
- Frozen model behavior (immutability)
- Interface version verification

Test Categories:
1. Fingerprint Validation Tests
2. State Machine Alias Tests (backwards compatibility)
3. Frozen Model Tests (immutability)
4. Interface Version Tests

Requirements from v1.5.0:
- fingerprint field: pattern r"^\\d+\\.\\d+\\.\\d+:[a-f0-9]{12}$" (e.g., "1.0.0:a1b2c3d4e5f6")
- state_machine field with alias="state_transitions" for YAML backwards compatibility
- frozen=True in model_config for thread safety and immutability
- INTERFACE_VERSION = ModelSemVer(major=1, minor=5, patch=0)
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def get_minimal_reducer_contract_data(**overrides: Any) -> dict[str, Any]:
    """Create minimal valid ModelContractReducer data with optional overrides.

    This helper provides the required base class fields (name, contract_version,
    description, input_model, output_model) with sensible defaults, allowing tests
    to override specific fields as needed.
    """
    base_data: dict[str, Any] = {
        "name": "test_reducer_contract",
        "contract_version": ModelSemVer(major=1, minor=0, patch=0),
        "description": "Test reducer contract for v1.5.0 validation",
        "input_model": "omnibase_core.models.test.ModelTestInput",
        "output_model": "omnibase_core.models.test.ModelTestOutput",
        "node_type": EnumNodeType.REDUCER_GENERIC,
    }
    base_data.update(overrides)
    return base_data


def create_minimal_reducer_contract(**overrides: Any) -> ModelContractReducer:
    """Create a minimal valid ModelContractReducer instance with optional overrides."""
    return ModelContractReducer(**get_minimal_reducer_contract_data(**overrides))


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelContractReducerFingerprint:
    """Tests for fingerprint field validation."""

    def test_fingerprint_valid_format_basic(self) -> None:
        """Test that valid fingerprint format is accepted (basic semver)."""
        contract = create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f6")
        assert contract.fingerprint == "1.0.0:a1b2c3d4e5f6"

    def test_fingerprint_valid_format_zero_version(self) -> None:
        """Test that valid fingerprint with 0.0.0 version is accepted."""
        contract = create_minimal_reducer_contract(fingerprint="0.0.0:000000000000")
        assert contract.fingerprint == "0.0.0:000000000000"

    def test_fingerprint_valid_format_large_version(self) -> None:
        """Test that valid fingerprint with large version numbers is accepted."""
        contract = create_minimal_reducer_contract(
            fingerprint="100.200.300:abcdef123456"
        )
        assert contract.fingerprint == "100.200.300:abcdef123456"

    def test_fingerprint_valid_format_current_version(self) -> None:
        """Test that valid fingerprint with current project version is accepted."""
        contract = create_minimal_reducer_contract(fingerprint="0.4.0:123456789abc")
        assert contract.fingerprint == "0.4.0:123456789abc"

    def test_fingerprint_valid_format_all_hex_chars(self) -> None:
        """Test that all valid hex characters (a-f, 0-9) are accepted."""
        contract = create_minimal_reducer_contract(fingerprint="1.5.0:abcdef012345")
        assert contract.fingerprint == "1.5.0:abcdef012345"

    def test_fingerprint_none_allowed(self) -> None:
        """Test that fingerprint can be None (optional field)."""
        contract = create_minimal_reducer_contract(fingerprint=None)
        assert contract.fingerprint is None

    def test_fingerprint_default_is_none(self) -> None:
        """Test that fingerprint defaults to None when not provided."""
        contract = create_minimal_reducer_contract()
        assert contract.fingerprint is None

    def test_fingerprint_invalid_missing_colon(self) -> None:
        """Test that fingerprint without colon separator is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0a1b2c3d4e5f6")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_wrong_semver_format(self) -> None:
        """Test that fingerprint with wrong semver format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0:a1b2c3d4e5f6")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_hex_too_short(self) -> None:
        """Test that fingerprint with hex shorter than 12 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_hex_too_long(self) -> None:
        """Test that fingerprint with hex longer than 12 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f67")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_uppercase_hex(self) -> None:
        """Test that fingerprint with uppercase hex chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0:A1B2C3D4E5F6")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_non_hex_chars(self) -> None:
        """Test that fingerprint with non-hex characters (g-z) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0:ghijklmnopqr")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_negative_version(self) -> None:
        """Test that fingerprint with negative version is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="-1.0.0:a1b2c3d4e5f6")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_empty_string(self) -> None:
        """Test that empty string fingerprint is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_special_chars_in_hex(self) -> None:
        """Test that fingerprint with special chars in hex is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3-d4e5f")
        assert "fingerprint" in str(exc_info.value).lower()

    def test_fingerprint_invalid_spaces(self) -> None:
        """Test that fingerprint with spaces is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_minimal_reducer_contract(fingerprint="1.0.0: a1b2c3d4e5f6")
        assert "fingerprint" in str(exc_info.value).lower()


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelContractReducerStateMachineAlias:
    """Tests for state_machine field with state_transitions alias."""

    def _create_minimal_fsm_subcontract(self) -> ModelFSMSubcontract:
        """Create a minimal valid FSM subcontract for testing."""
        model_version = ModelSemVer(major=1, minor=0, patch=0)
        return ModelFSMSubcontract(
            version=model_version,
            state_machine_name="test_fsm",
            state_machine_version=model_version,
            description="Test FSM for reducer contract",
            states=[
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="idle",
                    state_type="operational",
                    description="Initial idle state",
                ),
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="processing",
                    state_type="operational",
                    description="Processing state",
                ),
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="completed",
                    state_type="terminal",
                    description="Terminal completed state",
                    is_terminal=True,
                    is_recoverable=False,  # Terminal states cannot be recoverable
                ),
            ],
            initial_state="idle",
            terminal_states=["completed"],
            transitions=[
                ModelFSMStateTransition(
                    version=model_version,
                    transition_name="start_processing",
                    from_state="idle",
                    to_state="processing",
                    trigger="start",
                ),
                ModelFSMStateTransition(
                    version=model_version,
                    transition_name="complete_processing",
                    from_state="processing",
                    to_state="completed",
                    trigger="finish",
                ),
            ],
        )

    def test_state_machine_field_direct_access(self) -> None:
        """Test accessing state_machine field directly."""
        fsm = self._create_minimal_fsm_subcontract()
        contract = create_minimal_reducer_contract(state_machine=fsm)
        assert contract.state_machine is not None
        assert contract.state_machine.state_machine_name == "test_fsm"
        assert contract.state_machine.initial_state == "idle"

    def test_state_machine_none_by_default(self) -> None:
        """Test that state_machine is None by default."""
        contract = create_minimal_reducer_contract()
        assert contract.state_machine is None

    def test_state_transitions_alias_backwards_compat_via_model_validate(self) -> None:
        """Test that state_transitions alias works for YAML/dict compatibility."""
        fsm = self._create_minimal_fsm_subcontract()
        # Simulate YAML parsing: use state_transitions key (the alias)
        contract_data = get_minimal_reducer_contract_data(
            state_transitions=fsm.model_dump()
        )
        contract = ModelContractReducer.model_validate(contract_data)
        assert contract.state_machine is not None
        assert contract.state_machine.state_machine_name == "test_fsm"

    def test_state_machine_via_dict_with_field_name(self) -> None:
        """Test that state_machine can be set via dict using field name."""
        fsm = self._create_minimal_fsm_subcontract()
        contract_data = get_minimal_reducer_contract_data(
            state_machine=fsm.model_dump()
        )
        contract = ModelContractReducer.model_validate(contract_data)
        assert contract.state_machine is not None
        assert contract.state_machine.state_machine_name == "test_fsm"

    def test_state_machine_with_fsm_subcontract_instance(self) -> None:
        """Test state_machine field with ModelFSMSubcontract instance."""
        fsm = self._create_minimal_fsm_subcontract()
        contract = create_minimal_reducer_contract(state_machine=fsm)

        # Verify FSM properties are accessible
        assert contract.state_machine is not None
        assert isinstance(contract.state_machine, ModelFSMSubcontract)
        assert contract.state_machine.state_machine_name == "test_fsm"
        assert contract.state_machine.initial_state == "idle"
        assert len(contract.state_machine.states) == 3
        assert len(contract.state_machine.transitions) == 2
        assert "completed" in contract.state_machine.terminal_states

    def test_state_machine_preserves_fsm_configuration(self) -> None:
        """Test that FSM configuration is preserved in state_machine field."""
        fsm = self._create_minimal_fsm_subcontract()
        contract = create_minimal_reducer_contract(state_machine=fsm)

        assert contract.state_machine is not None
        # Verify specific FSM configuration
        state_names = [s.state_name for s in contract.state_machine.states]
        assert "idle" in state_names
        assert "processing" in state_names
        assert "completed" in state_names

        # Verify transitions
        transition_triggers = [t.trigger for t in contract.state_machine.transitions]
        assert "start" in transition_triggers
        assert "finish" in transition_triggers

    def test_populate_by_name_allows_both_field_and_alias(self) -> None:
        """Test that populate_by_name=True allows both field name and alias."""
        fsm = self._create_minimal_fsm_subcontract()

        # Test with field name (state_machine)
        contract1 = ModelContractReducer.model_validate(
            get_minimal_reducer_contract_data(state_machine=fsm.model_dump())
        )
        assert contract1.state_machine is not None

        # Test with alias (state_transitions)
        contract2 = ModelContractReducer.model_validate(
            get_minimal_reducer_contract_data(state_transitions=fsm.model_dump())
        )
        assert contract2.state_machine is not None

        # Both should result in same state_machine content
        assert (
            contract1.state_machine.state_machine_name
            == contract2.state_machine.state_machine_name
        )

    def test_both_state_machine_and_state_transitions_provided(self) -> None:
        """Test behavior when both field name and alias are provided simultaneously.

        Documents Pydantic's behavior when both state_machine (field name)
        and state_transitions (alias) are provided in the same dict/YAML input.

        Expected Behavior (Pydantic v2 with extra='forbid'):
        - When both the field name AND the alias are present in input data,
          Pydantic raises a ValidationError with "Extra inputs are not permitted".
        - This occurs because the model has extra='forbid' configured, which
          rejects any fields not defined in the model schema.
        - When both state_machine (field) and state_transitions (alias) are
          provided, Pydantic maps state_transitions to state_machine via the
          alias, then sees state_machine as an "extra" undeclared field.

        IMPORTANT: This behavior ensures YAML contracts cannot accidentally
        specify both keys with different values, which would create ambiguity.
        Contracts MUST use either state_machine OR state_transitions, not both.
        """
        # Create two different FSM subcontracts to test the rejection
        model_version = ModelSemVer(major=1, minor=0, patch=0)

        # FSM for field name (state_machine)
        fsm_field_name = ModelFSMSubcontract(
            version=model_version,
            state_machine_name="fsm_via_field_name",
            state_machine_version=model_version,
            description="FSM provided via state_machine field name",
            states=[
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="field_initial",
                    state_type="operational",
                    description="Initial state from field name FSM",
                ),
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="field_terminal",
                    state_type="terminal",
                    description="Terminal state from field name FSM",
                    is_terminal=True,
                    is_recoverable=False,  # Terminal states cannot be recoverable
                ),
            ],
            initial_state="field_initial",
            terminal_states=["field_terminal"],
            transitions=[
                ModelFSMStateTransition(
                    version=model_version,
                    transition_name="field_transition",
                    from_state="field_initial",
                    to_state="field_terminal",
                    trigger="complete",
                ),
            ],
        )

        # FSM for alias (state_transitions)
        fsm_alias = ModelFSMSubcontract(
            version=model_version,
            state_machine_name="fsm_via_alias",
            state_machine_version=model_version,
            description="FSM provided via state_transitions alias",
            states=[
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="alias_initial",
                    state_type="operational",
                    description="Initial state from alias FSM",
                ),
                ModelFSMStateDefinition(
                    version=model_version,
                    state_name="alias_terminal",
                    state_type="terminal",
                    description="Terminal state from alias FSM",
                    is_terminal=True,
                    is_recoverable=False,  # Terminal states cannot be recoverable
                ),
            ],
            initial_state="alias_initial",
            terminal_states=["alias_terminal"],
            transitions=[
                ModelFSMStateTransition(
                    version=model_version,
                    transition_name="alias_transition",
                    from_state="alias_initial",
                    to_state="alias_terminal",
                    trigger="complete",
                ),
            ],
        )

        # Create contract data with BOTH keys present
        contract_data = get_minimal_reducer_contract_data()
        contract_data["state_machine"] = fsm_field_name.model_dump()
        contract_data["state_transitions"] = fsm_alias.model_dump()

        # Pydantic should raise ValidationError due to extra='forbid'
        # when both field name and alias are provided simultaneously
        with pytest.raises(ValidationError) as exc_info:
            ModelContractReducer.model_validate(contract_data)

        # Verify the error is about extra inputs not being permitted
        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "not permitted" in error_str, (
            "Error should indicate extra inputs are not permitted. "
            "When both state_machine (field) and state_transitions (alias) "
            "are provided, Pydantic sees one as an extra field and rejects it "
            "because extra='forbid' is configured on ModelContractReducer."
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelContractReducerFrozen:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self) -> None:
        """Test that model has frozen=True in config."""
        assert ModelContractReducer.model_config.get("frozen") is True

    def test_mutation_raises_error_fingerprint(self) -> None:
        """Test that attempting to modify fingerprint raises ValidationError."""
        contract = create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f6")
        with pytest.raises(ValidationError):
            contract.fingerprint = "2.0.0:fedcba654321"  # type: ignore[misc]

    def test_mutation_raises_error_node_type(self) -> None:
        """Test that attempting to modify node_type raises ValidationError."""
        contract = create_minimal_reducer_contract()
        with pytest.raises(ValidationError):
            contract.node_type = EnumNodeType.COMPUTE_GENERIC  # type: ignore[misc]

    def test_mutation_raises_error_order_preserving(self) -> None:
        """Test that attempting to modify order_preserving raises ValidationError."""
        contract = create_minimal_reducer_contract(order_preserving=False)
        with pytest.raises(ValidationError):
            contract.order_preserving = True  # type: ignore[misc]

    def test_mutation_raises_error_incremental_processing(self) -> None:
        """Test that attempting to modify incremental_processing raises ValidationError."""
        contract = create_minimal_reducer_contract(incremental_processing=True)
        with pytest.raises(ValidationError):
            contract.incremental_processing = False  # type: ignore[misc]

    def test_mutation_raises_error_result_caching_enabled(self) -> None:
        """Test that attempting to modify result_caching_enabled raises ValidationError."""
        contract = create_minimal_reducer_contract(result_caching_enabled=True)
        with pytest.raises(ValidationError):
            contract.result_caching_enabled = False  # type: ignore[misc]

    def test_mutation_raises_error_partial_results_enabled(self) -> None:
        """Test that attempting to modify partial_results_enabled raises ValidationError."""
        contract = create_minimal_reducer_contract(partial_results_enabled=True)
        with pytest.raises(ValidationError):
            contract.partial_results_enabled = False  # type: ignore[misc]

    def test_frozen_preserves_immutability_correlation_id(self) -> None:
        """Test that correlation_id cannot be changed after creation."""
        from uuid import uuid4

        contract = create_minimal_reducer_contract()
        original_correlation_id = contract.correlation_id
        new_uuid = uuid4()

        with pytest.raises(ValidationError):
            contract.correlation_id = new_uuid  # type: ignore[misc]

        # Original value should be unchanged
        assert contract.correlation_id == original_correlation_id

    def test_frozen_preserves_immutability_node_name(self) -> None:
        """Test that node_name cannot be changed after creation."""
        contract = create_minimal_reducer_contract(node_name="original_name")
        with pytest.raises(ValidationError):
            contract.node_name = "new_name"  # type: ignore[misc]

        # Original value should be unchanged
        assert contract.node_name == "original_name"

    def test_frozen_model_not_hashable_with_nested_mutable_objects(self) -> None:
        """Test that frozen model with nested non-frozen objects is not hashable.

        This is expected behavior: ModelContractReducer contains nested objects like
        ModelPerformanceRequirements that are not frozen/hashable, making the
        parent model unhashable even though it has frozen=True in its config.
        This is a limitation of Pydantic's frozen model implementation.
        """
        contract = create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f6")

        # Frozen models with nested mutable objects should NOT be hashable
        with pytest.raises(TypeError, match="unhashable type"):
            hash(contract)

    def test_frozen_model_immutability_enforced_despite_hash_limitation(self) -> None:
        """Test that immutability is still enforced even though hashing fails.

        The frozen=True config still provides value by preventing field modifications,
        even if the model cannot be hashed due to nested mutable objects.
        """
        contract = create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f6")

        # Verify immutability is still enforced
        with pytest.raises(ValidationError):
            contract.fingerprint = "2.0.0:000000000000"  # type: ignore[misc]

        # Original value should be unchanged
        assert contract.fingerprint == "1.0.0:a1b2c3d4e5f6"


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelContractReducerVersion:
    """Tests for interface version."""

    def test_interface_version_is_150(self) -> None:
        """Test that INTERFACE_VERSION is 1.5.0."""
        version = ModelContractReducer.INTERFACE_VERSION
        assert version.major == 1
        assert version.minor == 5
        assert version.patch == 0

    def test_interface_version_is_model_semver(self) -> None:
        """Test that INTERFACE_VERSION is a ModelSemVer instance."""
        version = ModelContractReducer.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)

    def test_interface_version_string_representation(self) -> None:
        """Test that INTERFACE_VERSION has correct string representation."""
        version = ModelContractReducer.INTERFACE_VERSION
        assert str(version) == "1.5.0"

    def test_interface_version_is_class_variable(self) -> None:
        """Test that INTERFACE_VERSION is a class variable, not instance variable."""
        # Should be accessible from class
        assert hasattr(ModelContractReducer, "INTERFACE_VERSION")

        # Should be same object for all instances
        contract1 = create_minimal_reducer_contract(name="contract1")
        contract2 = create_minimal_reducer_contract(name="contract2")
        assert contract1.INTERFACE_VERSION is contract2.INTERFACE_VERSION
        assert ModelContractReducer.INTERFACE_VERSION is contract1.INTERFACE_VERSION


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelFSMSubcontractVersion:
    """Tests for ModelFSMSubcontract interface version (related to v1.5.0 changes)."""

    def test_fsm_subcontract_interface_version_is_150(self) -> None:
        """Test that ModelFSMSubcontract INTERFACE_VERSION is 1.5.0."""
        version = ModelFSMSubcontract.INTERFACE_VERSION
        assert version.major == 1
        assert version.minor == 5
        assert version.patch == 0

    def test_fsm_subcontract_interface_version_is_model_semver(self) -> None:
        """Test that ModelFSMSubcontract INTERFACE_VERSION is a ModelSemVer instance."""
        version = ModelFSMSubcontract.INTERFACE_VERSION
        assert isinstance(version, ModelSemVer)

    def test_fsm_subcontract_frozen_model(self) -> None:
        """Test that ModelFSMSubcontract has frozen=True in config."""
        assert ModelFSMSubcontract.model_config.get("frozen") is True


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelContractReducerModelConfig:
    """Tests for model configuration settings."""

    def test_extra_forbid_rejects_unknown_fields(self) -> None:
        """Test that extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractReducer(
                **get_minimal_reducer_contract_data(),
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unknown" in str(exc_info.value).lower()
        )

    def test_validate_default_validates_default_values(self) -> None:
        """Test that validate_default=True validates default values."""
        # Default contract should validate without errors
        contract = create_minimal_reducer_contract()
        assert contract is not None

    def test_populate_by_name_enabled(self) -> None:
        """Test that populate_by_name=True is configured."""
        assert ModelContractReducer.model_config.get("populate_by_name") is True

    def test_use_enum_values_false(self) -> None:
        """Test that use_enum_values=False keeps enum objects."""
        contract = create_minimal_reducer_contract()
        # Should be enum object, not string
        assert isinstance(contract.node_type, EnumNodeType)
        assert contract.node_type == EnumNodeType.REDUCER_GENERIC


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelContractReducerSerialization:
    """Tests for serialization with v1.5.0 fields."""

    def test_model_dump_includes_fingerprint(self) -> None:
        """Test that model_dump includes fingerprint field."""
        contract = create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f6")
        dumped = contract.model_dump()
        assert "fingerprint" in dumped
        assert dumped["fingerprint"] == "1.0.0:a1b2c3d4e5f6"

    def test_model_dump_includes_none_fingerprint(self) -> None:
        """Test that model_dump includes None fingerprint when not set."""
        contract = create_minimal_reducer_contract()
        dumped = contract.model_dump()
        assert "fingerprint" in dumped
        assert dumped["fingerprint"] is None

    def test_roundtrip_serialization_preserves_fingerprint(self) -> None:
        """Test roundtrip serialization preserves fingerprint."""
        original = create_minimal_reducer_contract(fingerprint="1.5.0:abcdef123456")
        dumped = original.model_dump()
        restored = ModelContractReducer.model_validate(dumped)
        assert restored.fingerprint == original.fingerprint

    def test_to_yaml_includes_fingerprint(self) -> None:
        """Test that to_yaml() includes fingerprint field."""
        contract = create_minimal_reducer_contract(fingerprint="1.0.0:a1b2c3d4e5f6")
        yaml_str = contract.to_yaml()
        assert "fingerprint" in yaml_str
        assert "1.0.0:a1b2c3d4e5f6" in yaml_str
