"""Tests for contract validation in Reducer Pattern Engine Phase 3."""

import pytest
from pydantic import ValidationError

from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.contracts.model_contract_reducer_pattern_engine import (
    ModelContractReducerPatternEngine,
)


class TestContractValidation:
    """Test contract validation for Reducer Pattern Engine Phase 3 simplified model."""

    def test_default_contract_creation(self):
        """Test that default contract can be created successfully."""
        contract = ModelContractReducerPatternEngine()

        assert contract.name == "reducer_pattern_engine"
        assert (
            contract.description
            == "Multi-workflow reducer pattern engine with ONEX compliance"
        )
        assert contract.pattern_type == "execution_pattern"
        assert len(contract.supported_workflows) == 3
        assert "DATA_ANALYSIS" in contract.supported_workflows
        assert "REPORT_GENERATION" in contract.supported_workflows
        assert "DOCUMENT_REGENERATION" in contract.supported_workflows
        assert contract.max_concurrent_workflows == 100
        assert contract.isolation_level == "instance_based"

        # Test dependencies
        assert len(contract.dependencies) == 3
        assert "ProtocolContainer" in contract.dependencies
        assert "ProtocolEventBus" in contract.dependencies
        assert "ProtocolSchemaLoader" in contract.dependencies

    def test_contract_with_structured_dependencies(self):
        """Test contract validation with structured dependency format."""
        contract_data = {
            "dependencies": [
                {
                    "name": "container",
                    "type": "protocol",
                    "class_name": "ProtocolContainer",
                    "module": "omnibase.protocol.protocol_container",
                },
                {
                    "name": "event_bus",
                    "type": "protocol",
                    "class_name": "ProtocolEventBus",
                    "module": "omnibase.protocol.protocol_event_bus",
                },
            ],
        }

        contract = ModelContractReducerPatternEngine(**contract_data)

        # Dependencies should be normalized to class names
        assert len(contract.dependencies) == 2
        assert "ProtocolContainer" in contract.dependencies
        assert "ProtocolEventBus" in contract.dependencies

    def test_dependency_validation_missing_required_fields(self):
        """Test that missing required fields in dependencies raise validation error."""
        contract_data = {
            "dependencies": [
                {
                    "name": "container",
                    # Missing "type" and "class_name" fields
                    "module": "omnibase.protocol.protocol_container",
                },
            ],
        }

        with pytest.raises(ValueError, match="missing required fields"):
            ModelContractReducerPatternEngine(**contract_data)

    def test_dependency_validation_invalid_type(self):
        """Test that invalid dependency type raises validation error."""
        contract_data = {
            "dependencies": [
                {
                    "name": "container",
                    "type": "invalid_type",  # Invalid type
                    "class_name": "ProtocolContainer",
                    "module": "omnibase.protocol.protocol_container",
                },
            ],
        }

        with pytest.raises(ValueError, match="invalid type"):
            ModelContractReducerPatternEngine(**contract_data)

    def test_dependency_validation_protocol_naming(self):
        """Test that protocol dependencies must follow naming convention."""
        contract_data = {
            "dependencies": [
                {
                    "name": "container",
                    "type": "protocol",
                    "class_name": "InvalidContainer",  # Should start with "Protocol"
                    "module": "omnibase.protocol.protocol_container",
                },
            ],
        }

        with pytest.raises(ValueError, match="must start with 'Protocol'"):
            ModelContractReducerPatternEngine(**contract_data)

    def test_dependency_validation_empty_class_name(self):
        """Test that empty class_name raises validation error."""
        contract_data = {
            "dependencies": [
                {
                    "name": "container",
                    "type": "protocol",
                    "class_name": "",  # Empty class name
                    "module": "omnibase.protocol.protocol_container",
                },
            ],
        }

        with pytest.raises(ValueError, match="invalid class_name"):
            ModelContractReducerPatternEngine(**contract_data)

    def test_dependency_validation_string_dependencies(self):
        """Test that simple string dependencies work correctly."""
        contract_data = {
            "dependencies": [
                "ProtocolContainer",
                "ProtocolEventBus",
                "ProtocolSchemaLoader",
            ],
        }

        contract = ModelContractReducerPatternEngine(**contract_data)

        assert len(contract.dependencies) == 3
        assert "ProtocolContainer" in contract.dependencies
        assert "ProtocolEventBus" in contract.dependencies
        assert "ProtocolSchemaLoader" in contract.dependencies

    def test_supported_workflows_validation(self):
        """Test supported workflows validation."""
        contract_data = {"supported_workflows": []}  # Empty list should fail validation

        with pytest.raises(ValidationError):
            ModelContractReducerPatternEngine(**contract_data)

    def test_max_concurrent_workflows_validation(self):
        """Test max_concurrent_workflows boundary validation."""
        # Test minimum boundary
        contract_data = {"max_concurrent_workflows": 0}
        with pytest.raises(ValidationError):
            ModelContractReducerPatternEngine(**contract_data)

        # Test maximum boundary
        contract_data = {"max_concurrent_workflows": 1001}
        with pytest.raises(ValidationError):
            ModelContractReducerPatternEngine(**contract_data)

        # Test valid values
        contract = ModelContractReducerPatternEngine(max_concurrent_workflows=50)
        assert contract.max_concurrent_workflows == 50

        contract = ModelContractReducerPatternEngine(max_concurrent_workflows=1000)
        assert contract.max_concurrent_workflows == 1000
