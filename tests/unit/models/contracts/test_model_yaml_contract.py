# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test for ModelYamlContract - YAML contract validation model.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


@pytest.mark.unit
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

    def test_contract_with_legacy_node_type_fails(self):
        """Test contract with legacy bare node type values now fails validation."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "compute",  # Legacy bare value - should now fail validation
        }

        with pytest.raises(OnexError) as exc_info:
            ModelYamlContract.model_validate(contract_data)

        # Verify error mentions invalid node_type
        error_string = str(exc_info.value)
        assert "node_type" in error_string
        assert "compute" in error_string

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


@pytest.mark.unit
class TestLegacyNodeTypeRejection:
    """Tests verifying legacy node type values are rejected (backward compatibility removed)."""

    @pytest.mark.parametrize(
        "legacy_value",
        [
            "compute",
            "effect",
            "reducer",
            "orchestrator",
            "COMPUTE",
            "EFFECT",
            "REDUCER",
            "ORCHESTRATOR",
        ],
    )
    def test_legacy_values_are_rejected(self, legacy_value: str) -> None:
        """Legacy bare node type values are no longer accepted and raise errors."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": legacy_value,
        }

        with pytest.raises(OnexError) as exc_info:
            ModelYamlContract.model_validate(contract_data)

        # Verify error mentions invalid node_type
        error_string = str(exc_info.value)
        assert "node_type" in error_string

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
    def test_generic_variants_are_accepted(self, generic_value: str) -> None:
        """GENERIC variants are the canonical values and should be accepted."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": generic_value,
        }

        contract = ModelYamlContract.model_validate(contract_data)
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
    def test_specific_node_types_are_accepted(self, specific_type: str) -> None:
        """Specific node types are valid and should be accepted."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": specific_type,
        }

        contract = ModelYamlContract.model_validate(contract_data)
        assert contract.node_type == EnumNodeType[specific_type]

    @pytest.mark.parametrize(
        "mixed_case_value",
        ["Compute", "ComPuTe", "cOMPUTE"],
    )
    def test_mixed_case_legacy_values_are_rejected(self, mixed_case_value: str) -> None:
        """Mixed case legacy values are also rejected."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": mixed_case_value,
        }

        with pytest.raises(OnexError):
            ModelYamlContract.model_validate(contract_data)
