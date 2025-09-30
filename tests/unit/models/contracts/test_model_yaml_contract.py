"""
Test for ModelYamlContract - YAML contract validation model.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.contracts.model_yaml_contract import ModelYamlContract


class TestModelYamlContract:
    """Test the YAML contract validation model."""

    def test_valid_contract_creation(self):
        """Test creating a valid contract with all required fields."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "COMPUTE",
            "description": "Test contract",
        }

        contract = ModelYamlContract.model_validate(contract_data)

        assert contract.contract_version.major == 1
        assert contract.contract_version.minor == 0
        assert contract.contract_version.patch == 0
        assert contract.node_type == EnumNodeType.COMPUTE
        assert contract.description == "Test contract"

    def test_contract_with_legacy_node_type(self):
        """Test contract with legacy compute node type."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "compute",  # Legacy lowercase
        }

        contract = ModelYamlContract.model_validate(contract_data)

        assert contract.node_type == EnumNodeType.COMPUTE

    def test_missing_contract_version_fails(self):
        """Test that missing contract_version causes validation error."""
        contract_data = {"node_type": "COMPUTE"}

        with pytest.raises(ValidationError) as exc_info:
            ModelYamlContract.model_validate(contract_data)

        # Use string representation for validation error checking
        error_string = str(exc_info.value)
        assert "contract_version" in error_string
        assert "missing" in error_string.lower()

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
            "node_type": "EFFECT",
            "description": "Effect contract",
        }

        contract = ModelYamlContract.validate_yaml_content(yaml_data)

        assert contract.contract_version.major == 2
        assert contract.contract_version.minor == 1
        assert contract.contract_version.patch == 3
        assert contract.node_type == EnumNodeType.EFFECT
        assert contract.description == "Effect contract"

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed in contracts but ignored per model config."""
        contract_data = {
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "COMPUTE",
            "description": "Test contract",
            "custom_field": "custom_value",
            "metadata": {"author": "test"},
        }

        contract = ModelYamlContract.model_validate(contract_data)

        assert contract.contract_version.major == 1
        assert contract.node_type == EnumNodeType.COMPUTE
        assert contract.description == "Test contract"
        # Extra fields are ignored per model config (extra="ignore")
        assert not hasattr(contract, "custom_field")
        assert not hasattr(contract, "metadata")
