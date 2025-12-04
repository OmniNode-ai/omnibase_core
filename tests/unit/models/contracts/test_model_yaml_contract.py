"""
Test for ModelYamlContract - YAML contract validation model.
"""

import warnings

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


class TestModelYamlContract:
    """Test the YAML contract validation model."""

    def test_valid_contract_creation(self):
        """Test creating a valid contract with all required fields."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "COMPUTE_GENERIC",
            "description": "Test contract",
        }

        contract = ModelYamlContract.model_validate(contract_data)

        assert contract.contract_version.major == 1
        assert contract.contract_version.minor == 0
        assert contract.contract_version.patch == 0
        assert contract.node_type == EnumNodeType.COMPUTE_GENERIC
        assert contract.description == "Test contract"

    def test_contract_with_legacy_node_type(self):
        """Test contract with legacy compute node type (triggers deprecation warning)."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "compute",  # Legacy lowercase - should trigger deprecation warning
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            contract = ModelYamlContract.model_validate(contract_data)

            # Verify deprecation warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        assert contract.node_type == EnumNodeType.COMPUTE_GENERIC

    def test_missing_contract_version_fails(self):
        """Test that contracts require explicit contract_version."""
        contract_data = {"node_type": "COMPUTE_GENERIC"}

        with pytest.raises(ValidationError) as exc_info:
            ModelYamlContract.model_validate(contract_data)

        # Verify error mentions contract_version field
        error_string = str(exc_info.value)
        assert "contract_version" in error_string

    def test_missing_node_type_fails(self):
        """Test that missing node_type causes validation error."""
        contract_data = {"contract_version": {"major": 1, "minor": 0, "patch": 0}}

        with pytest.raises(ValidationError) as exc_info:
            ModelYamlContract.model_validate(contract_data)

        # Use string representation for validation error checking
        error_string = str(exc_info.value)
        assert "node_type" in error_string
        assert "missing" in error_string.lower()

    def test_invalid_node_type_fails(self):
        """Test that invalid node_type causes validation error."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "INVALID_TYPE",
        }

        with pytest.raises(OnexError) as exc_info:
            ModelYamlContract.model_validate(contract_data)

        # Use string representation for validation error checking
        error_string = str(exc_info.value)
        assert "node_type" in error_string
        assert "INVALID_TYPE" in error_string

    def test_validate_yaml_content_classmethod(self):
        """Test the validate_yaml_content classmethod."""
        yaml_data = {
            "contract_version": {"major": 2, "minor": 1, "patch": 3},
            "node_type": "EFFECT_GENERIC",
            "description": "Effect contract",
        }

        contract = ModelYamlContract.validate_yaml_content(yaml_data)

        assert contract.contract_version.major == 2
        assert contract.contract_version.minor == 1
        assert contract.contract_version.patch == 3
        assert contract.node_type == EnumNodeType.EFFECT_GENERIC
        assert contract.description == "Effect contract"

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed in contracts but ignored per model config."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "COMPUTE_GENERIC",
            "description": "Test contract",
            "custom_field": "custom_value",
            "metadata": {"author": "test"},
        }

        contract = ModelYamlContract.model_validate(contract_data)

        assert contract.contract_version.major == 1
        assert contract.node_type == EnumNodeType.COMPUTE_GENERIC
        assert contract.description == "Test contract"
        # Extra fields are ignored per model config (extra="ignore")
        assert not hasattr(contract, "custom_field")
        assert not hasattr(contract, "metadata")


class TestDeprecationWarnings:
    """Tests for deprecation warnings on legacy enum values."""

    @pytest.mark.parametrize(
        ("legacy_value", "expected_enum"),
        [
            ("compute", EnumNodeType.COMPUTE_GENERIC),
            ("effect", EnumNodeType.EFFECT_GENERIC),
            ("reducer", EnumNodeType.REDUCER_GENERIC),
            ("orchestrator", EnumNodeType.ORCHESTRATOR_GENERIC),
            # Also test uppercase legacy values
            ("COMPUTE", EnumNodeType.COMPUTE_GENERIC),
            ("EFFECT", EnumNodeType.EFFECT_GENERIC),
            ("REDUCER", EnumNodeType.REDUCER_GENERIC),
            ("ORCHESTRATOR", EnumNodeType.ORCHESTRATOR_GENERIC),
        ],
    )
    def test_legacy_values_emit_deprecation_warning(
        self, legacy_value: str, expected_enum: EnumNodeType
    ) -> None:
        """Legacy lowercase/uppercase bare values should emit DeprecationWarning."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": legacy_value,
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            contract = ModelYamlContract.model_validate(contract_data)

            # Verify deprecation warning was raised
            assert len(w) == 1, f"Expected 1 warning for '{legacy_value}', got {len(w)}"
            assert issubclass(
                w[0].category, DeprecationWarning
            ), f"Expected DeprecationWarning, got {w[0].category}"

        # Verify the mapping is correct
        assert contract.node_type == expected_enum

    @pytest.mark.parametrize(
        "generic_value",
        [
            "COMPUTE_GENERIC",
            "EFFECT_GENERIC",
            "REDUCER_GENERIC",
            "ORCHESTRATOR_GENERIC",
            "RUNTIME_HOST_GENERIC",
        ],
    )
    def test_generic_variants_do_not_emit_warning(self, generic_value: str) -> None:
        """GENERIC variants should not emit any warning."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": generic_value,
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            contract = ModelYamlContract.model_validate(contract_data)

            # No deprecation warnings should be raised
            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert (
                len(deprecation_warnings) == 0
            ), f"Unexpected DeprecationWarning for '{generic_value}': {deprecation_warnings}"

        # Verify the enum was correctly resolved
        assert contract.node_type == EnumNodeType[generic_value]

    @pytest.mark.parametrize(
        "specific_type",
        [
            "TRANSFORMER",
            "AGGREGATOR",
            "GATEWAY",
            "VALIDATOR",
            "FUNCTION",
            "TOOL",
            "AGENT",
            "MODEL",
            "PLUGIN",
            "SCHEMA",
            "NODE",
            "WORKFLOW",
            "SERVICE",
        ],
    )
    def test_specific_node_types_do_not_emit_warning(self, specific_type: str) -> None:
        """Specific node types (non-legacy) should not emit any warning."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": specific_type,
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            contract = ModelYamlContract.model_validate(contract_data)

            # No deprecation warnings should be raised
            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert (
                len(deprecation_warnings) == 0
            ), f"Unexpected DeprecationWarning for '{specific_type}': {deprecation_warnings}"

        # Verify the enum was correctly resolved
        assert contract.node_type == EnumNodeType[specific_type]

    @pytest.mark.parametrize(
        ("legacy_value", "expected_replacement"),
        [
            ("compute", "COMPUTE_GENERIC"),
            ("effect", "EFFECT_GENERIC"),
            ("reducer", "REDUCER_GENERIC"),
            ("orchestrator", "ORCHESTRATOR_GENERIC"),
        ],
    )
    def test_deprecation_message_contains_migration_hint(
        self, legacy_value: str, expected_replacement: str
    ) -> None:
        """Deprecation message should hint at the correct replacement."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": legacy_value,
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ModelYamlContract.model_validate(contract_data)

            assert len(w) == 1
            message = str(w[0].message)

            # Check that the message contains migration guidance
            assert (
                "deprecated" in message.lower()
            ), f"Message should mention 'deprecated': {message}"
            assert (
                expected_replacement in message
            ), f"Message should contain replacement '{expected_replacement}': {message}"
            assert (
                legacy_value in message
            ), f"Message should contain original value '{legacy_value}': {message}"

    def test_enum_value_direct_access_does_not_warn(self) -> None:
        """Direct access to EnumNodeType members should not emit warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Access all GENERIC variants directly
            _ = EnumNodeType.COMPUTE_GENERIC
            _ = EnumNodeType.EFFECT_GENERIC
            _ = EnumNodeType.REDUCER_GENERIC
            _ = EnumNodeType.ORCHESTRATOR_GENERIC
            _ = EnumNodeType.RUNTIME_HOST_GENERIC

            # Access specific types
            _ = EnumNodeType.TRANSFORMER
            _ = EnumNodeType.AGGREGATOR

            # No deprecation warnings should be raised for direct enum access
            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            assert (
                len(deprecation_warnings) == 0
            ), f"Direct enum access should not warn: {deprecation_warnings}"

    def test_deprecation_warning_category_is_correct(self) -> None:
        """Verify the warning is specifically DeprecationWarning (not UserWarning etc.)."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "compute",
        }

        with pytest.warns(DeprecationWarning, match="deprecated"):
            ModelYamlContract.model_validate(contract_data)

    def test_mixed_case_legacy_value_emits_warning(self) -> None:
        """Mixed case legacy values should also emit warnings."""
        # Test mixed case variations
        mixed_cases = ["Compute", "COMPUTE", "ComPuTe", "cOMPUTE"]

        for value in mixed_cases:
            contract_data = {
                "contract_version": {"major": 1, "minor": 0, "patch": 0},
                "node_type": value,
            }

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                contract = ModelYamlContract.model_validate(contract_data)

                # All should trigger deprecation warning
                deprecation_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, DeprecationWarning)
                ]
                assert (
                    len(deprecation_warnings) == 1
                ), f"Expected 1 warning for '{value}', got {len(deprecation_warnings)}"

            assert contract.node_type == EnumNodeType.COMPUTE_GENERIC
