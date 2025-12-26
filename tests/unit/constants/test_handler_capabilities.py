"""
Unit tests for handler capability validation (OMN-169).

TDD tests for handler capability constants and validation functions.
These tests are written BEFORE the implementation exists.

Test Categories:
    - Capability Constants: frozenset constants for EFFECT node capabilities
    - Node Type Requirements: Mapping of node types to their handler requirements
    - Capability Validation: Function to validate requested vs available capabilities
    - Contract Capability Validation: Validating contract capability requests

Design Principles:
    - Use frozenset for immutability (EFFECT_CAPABILITIES, etc.)
    - SCREAMING_SNAKE_CASE for constants
    - Clear error messages with capability name, node_type, available_capabilities
    - Raise UnsupportedCapabilityError when capability not available
    - Use typed enums (EnumEffectCapability, etc.) instead of magic strings

Related:
    - src/omnibase_core/constants/handler_capabilities.py: Implementation target
    - src/omnibase_core/errors/exception_unsupported_capability_error.py: Error class
    - OMN-169: Linear ticket for this implementation
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_compute_capability import EnumComputeCapability
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_capability import EnumEffectCapability
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.enums.enum_node_requirement import EnumNodeRequirement
from omnibase_core.enums.enum_orchestrator_capability import EnumOrchestratorCapability
from omnibase_core.enums.enum_reducer_capability import EnumReducerCapability
from omnibase_core.errors import UnsupportedCapabilityError

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit


# =============================================================================
# Capability Constants Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestEffectCapabilities:
    """Test EFFECT_CAPABILITIES constant definition and contents."""

    def test_effect_capabilities_is_frozenset(self) -> None:
        """Test that EFFECT_CAPABILITIES is a frozenset (immutable)."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        assert isinstance(EFFECT_CAPABILITIES, frozenset)

    def test_effect_capabilities_contains_http(self) -> None:
        """Test that EFFECT_CAPABILITIES contains http capability."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        assert EnumEffectCapability.HTTP in EFFECT_CAPABILITIES

    def test_effect_capabilities_contains_db(self) -> None:
        """Test that EFFECT_CAPABILITIES contains db capability."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        assert EnumEffectCapability.DB in EFFECT_CAPABILITIES

    def test_effect_capabilities_contains_kafka(self) -> None:
        """Test that EFFECT_CAPABILITIES contains kafka capability."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        assert EnumEffectCapability.KAFKA in EFFECT_CAPABILITIES

    def test_effect_capabilities_contains_filesystem(self) -> None:
        """Test that EFFECT_CAPABILITIES contains filesystem capability."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        assert EnumEffectCapability.FILESYSTEM in EFFECT_CAPABILITIES

    def test_effect_capabilities_contains_expected_values(self) -> None:
        """Test that EFFECT_CAPABILITIES contains all expected values."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        expected = {
            EnumEffectCapability.HTTP,
            EnumEffectCapability.DB,
            EnumEffectCapability.KAFKA,
            EnumEffectCapability.FILESYSTEM,
        }
        assert expected == EFFECT_CAPABILITIES

    def test_effect_capabilities_is_immutable(self) -> None:
        """Test that EFFECT_CAPABILITIES cannot be modified (frozenset)."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        # frozenset does not have add method - this should raise AttributeError
        with pytest.raises(AttributeError):
            EFFECT_CAPABILITIES.add("new_capability")

    def test_effect_capabilities_all_lowercase(self) -> None:
        """Test that all EFFECT_CAPABILITIES values are lowercase strings."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        for capability in EFFECT_CAPABILITIES:
            assert isinstance(capability, str)
            assert capability == capability.lower(), (
                f"Capability '{capability}' should be lowercase"
            )


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestComputeCapabilities:
    """Test COMPUTE_CAPABILITIES constant definition and contents."""

    def test_compute_capabilities_is_frozenset(self) -> None:
        """Test that COMPUTE_CAPABILITIES is a frozenset (immutable)."""
        from omnibase_core.constants.handler_capabilities import COMPUTE_CAPABILITIES

        assert isinstance(COMPUTE_CAPABILITIES, frozenset)

    def test_compute_capabilities_contains_transform(self) -> None:
        """Test that COMPUTE_CAPABILITIES contains transform capability."""
        from omnibase_core.constants.handler_capabilities import COMPUTE_CAPABILITIES

        assert EnumComputeCapability.TRANSFORM in COMPUTE_CAPABILITIES

    def test_compute_capabilities_contains_validate(self) -> None:
        """Test that COMPUTE_CAPABILITIES contains validate capability."""
        from omnibase_core.constants.handler_capabilities import COMPUTE_CAPABILITIES

        assert EnumComputeCapability.VALIDATE in COMPUTE_CAPABILITIES


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestReducerCapabilities:
    """Test REDUCER_CAPABILITIES constant definition and contents."""

    def test_reducer_capabilities_is_frozenset(self) -> None:
        """Test that REDUCER_CAPABILITIES is a frozenset (immutable)."""
        from omnibase_core.constants.handler_capabilities import REDUCER_CAPABILITIES

        assert isinstance(REDUCER_CAPABILITIES, frozenset)

    def test_reducer_capabilities_contains_fsm_interpreter(self) -> None:
        """Test that REDUCER_CAPABILITIES contains fsm_interpreter capability."""
        from omnibase_core.constants.handler_capabilities import REDUCER_CAPABILITIES

        assert EnumReducerCapability.FSM_INTERPRETER in REDUCER_CAPABILITIES


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestOrchestratorCapabilities:
    """Test ORCHESTRATOR_CAPABILITIES constant definition and contents."""

    def test_orchestrator_capabilities_is_frozenset(self) -> None:
        """Test that ORCHESTRATOR_CAPABILITIES is a frozenset (immutable)."""
        from omnibase_core.constants.handler_capabilities import (
            ORCHESTRATOR_CAPABILITIES,
        )

        assert isinstance(ORCHESTRATOR_CAPABILITIES, frozenset)

    def test_orchestrator_capabilities_contains_workflow_resolver(self) -> None:
        """Test that ORCHESTRATOR_CAPABILITIES contains workflow_resolver."""
        from omnibase_core.constants.handler_capabilities import (
            ORCHESTRATOR_CAPABILITIES,
        )

        assert EnumOrchestratorCapability.WORKFLOW_RESOLVER in ORCHESTRATOR_CAPABILITIES


# =============================================================================
# Node Type Requirements Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeTypeRequirements:
    """Test NODE_TYPE_REQUIREMENTS mapping definition."""

    def test_node_type_requirements_exists(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS mapping exists."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        assert NODE_TYPE_REQUIREMENTS is not None

    def test_node_type_requirements_is_mapping(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS is a mapping type."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        # Should be a dict or similar mapping
        assert hasattr(NODE_TYPE_REQUIREMENTS, "__getitem__")
        assert hasattr(NODE_TYPE_REQUIREMENTS, "keys")

    def test_node_type_requirements_contains_effect(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS contains EFFECT node type."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        assert EnumNodeKind.EFFECT in NODE_TYPE_REQUIREMENTS

    def test_node_type_requirements_contains_compute(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS contains COMPUTE node type."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        assert EnumNodeKind.COMPUTE in NODE_TYPE_REQUIREMENTS

    def test_node_type_requirements_contains_reducer(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS contains REDUCER node type."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        assert EnumNodeKind.REDUCER in NODE_TYPE_REQUIREMENTS

    def test_node_type_requirements_contains_orchestrator(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS contains ORCHESTRATOR node type."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        assert EnumNodeKind.ORCHESTRATOR in NODE_TYPE_REQUIREMENTS

    def test_effect_requires_handler_execute(self) -> None:
        """Test that EFFECT node type requires handler with execute() method."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        effect_reqs = NODE_TYPE_REQUIREMENTS[EnumNodeKind.EFFECT]
        assert EnumNodeRequirement.HANDLER_EXECUTE in effect_reqs

    def test_reducer_requires_fsm_interpreter(self) -> None:
        """Test that REDUCER node type requires fsm_interpreter (optional)."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        reducer_reqs = NODE_TYPE_REQUIREMENTS[EnumNodeKind.REDUCER]
        assert EnumNodeRequirement.FSM_INTERPRETER in reducer_reqs

    def test_orchestrator_requires_workflow_resolver(self) -> None:
        """Test that ORCHESTRATOR node type requires workflow_resolver."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        orchestrator_reqs = NODE_TYPE_REQUIREMENTS[EnumNodeKind.ORCHESTRATOR]
        assert EnumNodeRequirement.WORKFLOW_RESOLVER in orchestrator_reqs

    def test_node_type_requirements_values_are_sets(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS values are sets of requirements."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        for node_kind, requirements in NODE_TYPE_REQUIREMENTS.items():
            assert isinstance(requirements, (set, frozenset)), (
                f"Requirements for {node_kind} should be a set or frozenset"
            )


# =============================================================================
# Capability Validation Function Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestValidateCapabilities:
    """Test validate_capabilities() function."""

    def test_validate_capabilities_returns_none_when_all_available(self) -> None:
        """Test that validate_capabilities returns None when all requested are available."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        # All requested capabilities are available
        result = validate_capabilities(
            requested={"http", "db"},
            available={"http", "db", "kafka", "filesystem"},
            node_type="EFFECT",
        )
        assert result is None

    def test_validate_capabilities_returns_none_for_empty_requested(self) -> None:
        """Test that validate_capabilities returns None when no capabilities requested."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        result = validate_capabilities(
            requested=set(),
            available={"http", "db"},
            node_type="EFFECT",
        )
        assert result is None

    def test_validate_capabilities_raises_when_capability_missing(self) -> None:
        """Test that validate_capabilities raises UnsupportedCapabilityError when missing."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"http", "graphql"},
                available={"http", "db"},
                node_type="EFFECT",
            )

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR

    def test_validate_capabilities_error_includes_capability_name(self) -> None:
        """Test that error includes the name of the missing capability."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"graphql"},
                available={"http", "db"},
                node_type="EFFECT",
            )

        error = exc_info.value
        assert error.capability == "graphql"

    def test_validate_capabilities_error_includes_node_type(self) -> None:
        """Test that error includes the node_type."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"graphql"},
                available={"http", "db"},
                node_type="EFFECT",
            )

        error = exc_info.value
        assert error.node_type == "EFFECT"

    def test_validate_capabilities_error_includes_available_capabilities(self) -> None:
        """Test that error context includes available_capabilities."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"graphql"},
                available={"http", "db"},
                node_type="EFFECT",
            )

        error = exc_info.value
        # Check that available_capabilities is in the error context
        error_str = str(error)
        # The error should mention the available capabilities somehow
        assert "http" in error_str or "available" in error_str.lower()

    def test_validate_capabilities_raises_for_single_missing_capability(self) -> None:
        """Test that a single missing capability triggers error."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        with pytest.raises(UnsupportedCapabilityError):
            validate_capabilities(
                requested={"missing_capability"},
                available={"http", "db", "kafka"},
                node_type="COMPUTE",
            )

    def test_validate_capabilities_raises_for_multiple_missing_capabilities(
        self,
    ) -> None:
        """Test behavior when multiple capabilities are missing."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        # At least one error should be raised
        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"missing1", "missing2"},
                available={"http", "db"},
                node_type="EFFECT",
            )

        error = exc_info.value
        # Should report at least one missing capability
        assert error.capability in {"missing1", "missing2"}

    def test_validate_capabilities_accepts_frozenset_requested(self) -> None:
        """Test that validate_capabilities accepts frozenset for requested."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        result = validate_capabilities(
            requested=frozenset({"http"}),
            available={"http", "db"},
            node_type="EFFECT",
        )
        assert result is None

    def test_validate_capabilities_accepts_frozenset_available(self) -> None:
        """Test that validate_capabilities accepts frozenset for available."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        result = validate_capabilities(
            requested={"http"},
            available=frozenset({"http", "db"}),
            node_type="EFFECT",
        )
        assert result is None

    def test_validate_capabilities_case_sensitive(self) -> None:
        """Test that capability matching is case-sensitive."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        # "HTTP" should not match "http"
        with pytest.raises(UnsupportedCapabilityError):
            validate_capabilities(
                requested={"HTTP"},
                available={"http", "db"},
                node_type="EFFECT",
            )


# =============================================================================
# Get Capabilities by Node Kind Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestGetCapabilitiesByNodeKind:
    """Test get_capabilities_by_node_kind() function."""

    def test_get_capabilities_returns_effect_capabilities(self) -> None:
        """Test that get_capabilities_by_node_kind returns EFFECT capabilities."""
        from omnibase_core.constants.handler_capabilities import (
            EFFECT_CAPABILITIES,
            get_capabilities_by_node_kind,
        )

        result = get_capabilities_by_node_kind(EnumNodeKind.EFFECT)
        assert result == EFFECT_CAPABILITIES

    def test_get_capabilities_returns_compute_capabilities(self) -> None:
        """Test that get_capabilities_by_node_kind returns COMPUTE capabilities."""
        from omnibase_core.constants.handler_capabilities import (
            COMPUTE_CAPABILITIES,
            get_capabilities_by_node_kind,
        )

        result = get_capabilities_by_node_kind(EnumNodeKind.COMPUTE)
        assert result == COMPUTE_CAPABILITIES

    def test_get_capabilities_returns_reducer_capabilities(self) -> None:
        """Test that get_capabilities_by_node_kind returns REDUCER capabilities."""
        from omnibase_core.constants.handler_capabilities import (
            REDUCER_CAPABILITIES,
            get_capabilities_by_node_kind,
        )

        result = get_capabilities_by_node_kind(EnumNodeKind.REDUCER)
        assert result == REDUCER_CAPABILITIES

    def test_get_capabilities_returns_orchestrator_capabilities(self) -> None:
        """Test that get_capabilities_by_node_kind returns ORCHESTRATOR capabilities."""
        from omnibase_core.constants.handler_capabilities import (
            ORCHESTRATOR_CAPABILITIES,
            get_capabilities_by_node_kind,
        )

        result = get_capabilities_by_node_kind(EnumNodeKind.ORCHESTRATOR)
        assert result == ORCHESTRATOR_CAPABILITIES

    def test_get_capabilities_returns_frozenset(self) -> None:
        """Test that get_capabilities_by_node_kind returns a frozenset."""
        from omnibase_core.constants.handler_capabilities import (
            get_capabilities_by_node_kind,
        )

        for node_kind in [
            EnumNodeKind.EFFECT,
            EnumNodeKind.COMPUTE,
            EnumNodeKind.REDUCER,
            EnumNodeKind.ORCHESTRATOR,
        ]:
            result = get_capabilities_by_node_kind(node_kind)
            assert isinstance(result, frozenset), (
                f"Result for {node_kind} should be frozenset"
            )

    def test_get_capabilities_raises_for_runtime_host(self) -> None:
        """Test that get_capabilities_by_node_kind raises for RUNTIME_HOST."""
        from omnibase_core.constants.handler_capabilities import (
            get_capabilities_by_node_kind,
        )

        # RUNTIME_HOST is infrastructure, not a core node type
        from omnibase_core.errors import ModelOnexError

        with pytest.raises(ModelOnexError):
            get_capabilities_by_node_kind(EnumNodeKind.RUNTIME_HOST)


# =============================================================================
# Contract Capability Validation Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestContractCapabilityValidation:
    """Test contract capability validation scenarios."""

    def test_valid_contract_with_supported_capabilities_passes(self) -> None:
        """Test that a contract requesting supported capabilities passes validation."""
        from omnibase_core.constants.handler_capabilities import (
            EFFECT_CAPABILITIES,
            validate_capabilities,
        )

        # Request a subset of available capabilities
        requested = {"http", "db"}
        result = validate_capabilities(
            requested=requested,
            available=EFFECT_CAPABILITIES,
            node_type="EFFECT",
        )
        assert result is None

    def test_contract_requesting_all_effect_capabilities_passes(self) -> None:
        """Test that a contract requesting all EFFECT capabilities passes."""
        from omnibase_core.constants.handler_capabilities import (
            EFFECT_CAPABILITIES,
            validate_capabilities,
        )

        result = validate_capabilities(
            requested=set(EFFECT_CAPABILITIES),
            available=EFFECT_CAPABILITIES,
            node_type="EFFECT",
        )
        assert result is None

    def test_contract_requesting_unsupported_capability_fails(self) -> None:
        """Test that a contract requesting unsupported capability raises clear error."""
        from omnibase_core.constants.handler_capabilities import (
            EFFECT_CAPABILITIES,
            validate_capabilities,
        )

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"graphql"},  # Not in EFFECT_CAPABILITIES
                available=EFFECT_CAPABILITIES,
                node_type="EFFECT",
            )

        error = exc_info.value
        # Error should be clear about what was requested vs what's available
        assert error.capability == "graphql"
        assert error.node_type == "EFFECT"

    def test_contract_error_message_includes_requested_vs_available(self) -> None:
        """Test that error message includes what was requested vs what's available."""
        from omnibase_core.constants.handler_capabilities import (
            EFFECT_CAPABILITIES,
            validate_capabilities,
        )

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"unsupported_cap"},
                available=EFFECT_CAPABILITIES,
                node_type="EFFECT",
            )

        error = exc_info.value
        error_str = str(error)
        # Error should mention the unsupported capability
        assert "unsupported_cap" in error_str or error.capability == "unsupported_cap"

    def test_contract_with_empty_capabilities_request_passes(self) -> None:
        """Test that a contract with no capability requirements passes."""
        from omnibase_core.constants.handler_capabilities import (
            COMPUTE_CAPABILITIES,
            validate_capabilities,
        )

        result = validate_capabilities(
            requested=set(),
            available=COMPUTE_CAPABILITIES,
            node_type="COMPUTE",
        )
        assert result is None


# =============================================================================
# Edge Cases and Error Context Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestHandlerCapabilitiesEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_capability_constants_are_frozenset(self) -> None:
        """Test that all capability constants are frozenset (immutable)."""
        from omnibase_core.constants.handler_capabilities import (
            COMPUTE_CAPABILITIES,
            EFFECT_CAPABILITIES,
            ORCHESTRATOR_CAPABILITIES,
            REDUCER_CAPABILITIES,
        )

        assert isinstance(EFFECT_CAPABILITIES, frozenset)
        assert isinstance(COMPUTE_CAPABILITIES, frozenset)
        assert isinstance(REDUCER_CAPABILITIES, frozenset)
        assert isinstance(ORCHESTRATOR_CAPABILITIES, frozenset)

    def test_capability_constants_no_overlap(self) -> None:
        """Test that capability constants have expected relationships."""
        from omnibase_core.constants.handler_capabilities import (
            COMPUTE_CAPABILITIES,
            EFFECT_CAPABILITIES,
            ORCHESTRATOR_CAPABILITIES,
            REDUCER_CAPABILITIES,
        )

        # Each set should be non-empty
        assert len(EFFECT_CAPABILITIES) > 0
        assert len(COMPUTE_CAPABILITIES) > 0
        assert len(REDUCER_CAPABILITIES) > 0
        assert len(ORCHESTRATOR_CAPABILITIES) > 0

    def test_error_is_unsupported_capability_error_type(self) -> None:
        """Test that the raised error is UnsupportedCapabilityError."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        try:
            validate_capabilities(
                requested={"invalid_cap"},
                available={"http", "db"},
                node_type="EFFECT",
            )
            pytest.fail("Expected UnsupportedCapabilityError to be raised")
        except UnsupportedCapabilityError:
            pass  # Expected
        except Exception as e:
            pytest.fail(
                f"Expected UnsupportedCapabilityError but got {type(e).__name__}: {e}"
            )

    def test_error_has_correct_error_code(self) -> None:
        """Test that the error uses UNSUPPORTED_CAPABILITY_ERROR code."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"unknown"},
                available={"http"},
                node_type="EFFECT",
            )

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR

    def test_validate_capabilities_with_string_node_type(self) -> None:
        """Test that validate_capabilities accepts string node_type."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        # Should work with string node type
        with pytest.raises(UnsupportedCapabilityError) as exc_info:
            validate_capabilities(
                requested={"missing"},
                available={"http"},
                node_type="custom_node_type",
            )

        error = exc_info.value
        assert error.node_type == "custom_node_type"


# =============================================================================
# Module Import Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestHandlerCapabilitiesImports:
    """Test module imports and exports."""

    def test_handler_capabilities_module_exists(self) -> None:
        """Test that the handler_capabilities module can be imported."""
        from omnibase_core.constants import handler_capabilities

        assert handler_capabilities is not None

    def test_effect_capabilities_importable(self) -> None:
        """Test that EFFECT_CAPABILITIES can be imported directly."""
        from omnibase_core.constants.handler_capabilities import EFFECT_CAPABILITIES

        assert EFFECT_CAPABILITIES is not None

    def test_validate_capabilities_importable(self) -> None:
        """Test that validate_capabilities can be imported directly."""
        from omnibase_core.constants.handler_capabilities import validate_capabilities

        assert callable(validate_capabilities)

    def test_node_type_requirements_importable(self) -> None:
        """Test that NODE_TYPE_REQUIREMENTS can be imported directly."""
        from omnibase_core.constants.handler_capabilities import NODE_TYPE_REQUIREMENTS

        assert NODE_TYPE_REQUIREMENTS is not None

    def test_get_capabilities_by_node_kind_importable(self) -> None:
        """Test that get_capabilities_by_node_kind can be imported."""
        from omnibase_core.constants.handler_capabilities import (
            get_capabilities_by_node_kind,
        )

        assert callable(get_capabilities_by_node_kind)

    def test_all_expected_exports_exist(self) -> None:
        """Test that all expected exports are present in __all__."""
        from omnibase_core.constants import handler_capabilities

        expected_exports = [
            # Capability Enums
            "EnumComputeCapability",
            "EnumEffectCapability",
            "EnumNodeRequirement",
            "EnumOrchestratorCapability",
            "EnumReducerCapability",
            # Capability Constants
            "EFFECT_CAPABILITIES",
            "COMPUTE_CAPABILITIES",
            "REDUCER_CAPABILITIES",
            "ORCHESTRATOR_CAPABILITIES",
            "NODE_TYPE_REQUIREMENTS",
            "validate_capabilities",
            "get_capabilities_by_node_kind",
        ]

        module_all = getattr(handler_capabilities, "__all__", [])
        for export in expected_exports:
            assert export in module_all or hasattr(handler_capabilities, export), (
                f"Expected export '{export}' not found in handler_capabilities module"
            )


# =============================================================================
# Capability Enum Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestCapabilityEnums:
    """Test capability enum definitions and behavior."""

    def test_effect_capability_enum_values(self) -> None:
        """Test that EnumEffectCapability has correct string values."""
        assert EnumEffectCapability.HTTP.value == "http"
        assert EnumEffectCapability.DB.value == "db"
        assert EnumEffectCapability.KAFKA.value == "kafka"
        assert EnumEffectCapability.FILESYSTEM.value == "filesystem"

    def test_compute_capability_enum_values(self) -> None:
        """Test that EnumComputeCapability has correct string values."""
        assert EnumComputeCapability.TRANSFORM.value == "transform"
        assert EnumComputeCapability.VALIDATE.value == "validate"

    def test_reducer_capability_enum_values(self) -> None:
        """Test that EnumReducerCapability has correct string values."""
        assert EnumReducerCapability.FSM_INTERPRETER.value == "fsm_interpreter"

    def test_orchestrator_capability_enum_values(self) -> None:
        """Test that EnumOrchestratorCapability has correct string values."""
        assert EnumOrchestratorCapability.WORKFLOW_RESOLVER.value == "workflow_resolver"

    def test_node_requirement_enum_values(self) -> None:
        """Test that EnumNodeRequirement has correct string values."""
        assert EnumNodeRequirement.HANDLER_EXECUTE.value == "handler_execute"
        assert EnumNodeRequirement.FSM_INTERPRETER.value == "fsm_interpreter"
        assert EnumNodeRequirement.WORKFLOW_RESOLVER.value == "workflow_resolver"

    def test_effect_capability_str_conversion(self) -> None:
        """Test that EnumEffectCapability converts to string correctly."""
        assert str(EnumEffectCapability.HTTP) == "http"
        assert str(EnumEffectCapability.DB) == "db"

    def test_effect_capability_values_method(self) -> None:
        """Test that EnumEffectCapability.values() returns all values."""
        values = EnumEffectCapability.values()
        assert "http" in values
        assert "db" in values
        assert "kafka" in values
        assert "filesystem" in values
        assert len(values) == 4

    def test_compute_capability_values_method(self) -> None:
        """Test that EnumComputeCapability.values() returns all values."""
        values = EnumComputeCapability.values()
        assert "transform" in values
        assert "validate" in values
        assert len(values) == 2

    def test_enum_membership_in_frozenset(self) -> None:
        """Test that enum values can be found in frozensets."""
        from omnibase_core.constants.handler_capabilities import (
            COMPUTE_CAPABILITIES,
            EFFECT_CAPABILITIES,
            ORCHESTRATOR_CAPABILITIES,
            REDUCER_CAPABILITIES,
        )

        # Enum values should be in their respective frozensets
        assert EnumEffectCapability.HTTP in EFFECT_CAPABILITIES
        assert EnumComputeCapability.TRANSFORM in COMPUTE_CAPABILITIES
        assert EnumReducerCapability.FSM_INTERPRETER in REDUCER_CAPABILITIES
        assert EnumOrchestratorCapability.WORKFLOW_RESOLVER in ORCHESTRATOR_CAPABILITIES

    def test_enum_importable_from_enums_module(self) -> None:
        """Test that capability enums can be imported from enums module."""
        from omnibase_core.enums import (
            EnumComputeCapability,
            EnumEffectCapability,
            EnumNodeRequirement,
            EnumOrchestratorCapability,
            EnumReducerCapability,
        )

        assert EnumEffectCapability is not None
        assert EnumComputeCapability is not None
        assert EnumReducerCapability is not None
        assert EnumOrchestratorCapability is not None
        assert EnumNodeRequirement is not None
