"""
Unit tests for compute_contract_fingerprint.py script.

Tests the contract type detection and validation functions, particularly
the split between validate_strict_contract() (enforcement) and
is_strict_contract() (predicate).

Test Categories:
1. validate_strict_contract() - Enforcement function tests
2. is_strict_contract() - Predicate wrapper tests
3. detect_contract_model() - Model detection tests
4. Deprecated 'version' field rejection tests (OMN-1431/OMN-1436)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Load script as module using importlib (cleaner than sys.path manipulation)
_script_path = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "compute_contract_fingerprint.py"
)
_spec = importlib.util.spec_from_file_location(
    "compute_contract_fingerprint", _script_path
)
assert _spec is not None and _spec.loader is not None, (
    f"Failed to load spec from {_script_path}"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# Import functions from loaded module
detect_contract_model = _module.detect_contract_model
is_strict_contract = _module.is_strict_contract
validate_strict_contract = _module.validate_strict_contract

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def strict_contract_data() -> dict[str, object]:
    """Valid strict contract data with all required fields."""
    return {
        "name": "test_contract",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "A test contract",
        "node_type": "COMPUTE_GENERIC",
        "input_model": "omnibase_core.models.ModelInput",
        "output_model": "omnibase_core.models.ModelOutput",
    }


@pytest.fixture
def flexible_contract_data() -> dict[str, object]:
    """Valid flexible contract data (missing strict fields)."""
    return {
        "name": "test_contract",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "node_type": "COMPUTE_GENERIC",
        # Missing: description, input_model, output_model
    }


@pytest.fixture
def deprecated_version_contract_data() -> dict[str, object]:
    """Contract data using deprecated 'version' field."""
    return {
        "name": "test_contract",
        "version": {"major": 1, "minor": 0, "patch": 0},  # Deprecated!
        "description": "A test contract",
        "node_type": "COMPUTE_GENERIC",
        "input_model": "omnibase_core.models.ModelInput",
        "output_model": "omnibase_core.models.ModelOutput",
    }


@pytest.fixture
def both_versions_contract_data() -> dict[str, object]:
    """Contract data with both 'version' and 'contract_version' (still invalid)."""
    return {
        "name": "test_contract",
        "version": {"major": 1, "minor": 0, "patch": 0},  # Deprecated!
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "description": "A test contract",
        "node_type": "COMPUTE_GENERIC",
        "input_model": "omnibase_core.models.ModelInput",
        "output_model": "omnibase_core.models.ModelOutput",
    }


# =============================================================================
# validate_strict_contract() Tests - Enforcement Function
# =============================================================================


class TestValidateStrictContract:
    """Tests for validate_strict_contract() enforcement function."""

    def test_accepts_strict_contract_with_contract_version(
        self, strict_contract_data: dict[str, object]
    ) -> None:
        """Test that strict contracts with contract_version are accepted."""
        result = validate_strict_contract(strict_contract_data)
        assert result is True

    def test_accepts_flexible_contract_with_contract_version(
        self, flexible_contract_data: dict[str, object]
    ) -> None:
        """Test that flexible contracts with contract_version return False."""
        result = validate_strict_contract(flexible_contract_data)
        assert result is False

    def test_rejects_deprecated_version_field(
        self, deprecated_version_contract_data: dict[str, object]
    ) -> None:
        """Test that contracts with deprecated 'version' field are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_strict_contract(deprecated_version_contract_data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        assert "version" in str(error)
        assert "contract_version" in str(error)

    def test_rejects_version_even_when_contract_version_exists(
        self, both_versions_contract_data: dict[str, object]
    ) -> None:
        """Test that deprecated 'version' is rejected even with 'contract_version' present.

        This is the critical migration footgun test - someone adds contract_version
        but forgets to remove version. The system must reject this.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            validate_strict_contract(both_versions_contract_data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        # Verify the error context includes info about both fields being present
        # Context is nested under additional_context.context
        assert error.context is not None
        inner_context = error.context.get("additional_context", {}).get("context", {})
        assert inner_context.get("has_contract_version") is True

    def test_error_includes_migration_guidance(
        self, deprecated_version_contract_data: dict[str, object]
    ) -> None:
        """Test that error message includes helpful migration guidance."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_strict_contract(deprecated_version_contract_data)

        error = exc_info.value
        # Check that context includes actionable guidance
        # Context is nested under additional_context.context
        assert error.context is not None
        inner_context = error.context.get("additional_context", {}).get("context", {})
        assert "suggestion" in inner_context
        assert "OMN-1431" in error.message


# =============================================================================
# is_strict_contract() Tests - Predicate Wrapper
# =============================================================================


class TestIsStrictContract:
    """Tests for is_strict_contract() predicate wrapper.

    This function should never raise exceptions - it wraps validate_strict_contract()
    and returns False on validation failure.
    """

    def test_returns_true_for_strict_contract(
        self, strict_contract_data: dict[str, object]
    ) -> None:
        """Test that strict contracts return True."""
        result = is_strict_contract(strict_contract_data)
        assert result is True

    def test_returns_false_for_flexible_contract(
        self, flexible_contract_data: dict[str, object]
    ) -> None:
        """Test that flexible contracts return False."""
        result = is_strict_contract(flexible_contract_data)
        assert result is False

    def test_returns_false_for_deprecated_version_no_exception(
        self, deprecated_version_contract_data: dict[str, object]
    ) -> None:
        """Test that deprecated 'version' returns False instead of raising.

        Unlike validate_strict_contract(), the predicate should not raise.
        """
        result = is_strict_contract(deprecated_version_contract_data)
        assert result is False

    def test_returns_false_for_both_versions_no_exception(
        self, both_versions_contract_data: dict[str, object]
    ) -> None:
        """Test that 'both versions present' returns False instead of raising."""
        result = is_strict_contract(both_versions_contract_data)
        assert result is False


# =============================================================================
# detect_contract_model() Tests
# =============================================================================


class TestDetectContractModel:
    """Tests for detect_contract_model() function."""

    def test_detects_compute_model_for_strict_contract(
        self, strict_contract_data: dict[str, object]
    ) -> None:
        """Test that COMPUTE_GENERIC maps to ModelContractCompute."""
        model_class = detect_contract_model(strict_contract_data)
        assert model_class is ModelContractCompute

    def test_detects_yaml_model_for_flexible_contract(
        self, flexible_contract_data: dict[str, object]
    ) -> None:
        """Test that flexible contracts use ModelYamlContract."""
        model_class = detect_contract_model(flexible_contract_data)
        assert model_class is ModelYamlContract

    def test_raises_for_deprecated_version_field(
        self, deprecated_version_contract_data: dict[str, object]
    ) -> None:
        """Test that detect_contract_model raises for deprecated 'version' field."""
        with pytest.raises(ModelOnexError) as exc_info:
            detect_contract_model(deprecated_version_contract_data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

    def test_raises_for_missing_node_type(self) -> None:
        """Test that missing node_type raises CONTRACT_VALIDATION_ERROR."""
        contract_data = {
            "name": "test",
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
        }
        with pytest.raises(ModelOnexError) as exc_info:
            detect_contract_model(contract_data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        assert "node_type" in error.message

    def test_raises_for_invalid_node_type_type(self) -> None:
        """Test that non-string node_type raises CONTRACT_VALIDATION_ERROR."""
        contract_data = {
            "name": "test",
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": 123,  # Invalid: not a string
        }
        with pytest.raises(ModelOnexError) as exc_info:
            detect_contract_model(contract_data)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        assert "string" in error.message


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for contract validation."""

    def test_empty_contract_is_flexible(self) -> None:
        """Test that empty contract data returns False (flexible)."""
        result = is_strict_contract({})
        assert result is False

    def test_contract_with_only_node_type(self) -> None:
        """Test contract with only node_type is flexible."""
        contract_data = {"node_type": "COMPUTE_GENERIC"}
        result = is_strict_contract(contract_data)
        assert result is False

    def test_strict_fields_without_contract_version_still_strict(self) -> None:
        """Test that strict fields without contract_version still counts as strict.

        This maintains backward compatibility for contracts being migrated.
        """
        contract_data = {
            "name": "test",
            "description": "A test",
            "node_type": "COMPUTE_GENERIC",
            "input_model": "omnibase_core.models.ModelInput",
            "output_model": "omnibase_core.models.ModelOutput",
            # No contract_version - but has all strict fields
        }
        result = validate_strict_contract(contract_data)
        assert result is True
