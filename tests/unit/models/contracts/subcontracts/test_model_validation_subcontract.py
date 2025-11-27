"""
Test for ModelValidationSubcontract - Validation subcontract model.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_validation_subcontract import (
    ModelValidationSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelValidationSubcontract:
    """Test the validation subcontract model."""

    def test_valid_subcontract_creation_defaults(self):
        """Test creating a valid subcontract with all defaults."""
        subcontract = ModelValidationSubcontract(version=DEFAULT_VERSION)

        assert subcontract.enable_fail_fast is True
        assert subcontract.strict_type_checking is True
        assert subcontract.enable_range_validation is True
        assert subcontract.enable_pattern_validation is True
        assert subcontract.enable_custom_validators is True
        assert subcontract.max_validation_errors == 100
        assert subcontract.validation_timeout_seconds == 5.0

    def test_valid_subcontract_creation_custom_values(self):
        """Test creating a valid subcontract with custom values."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "enable_fail_fast": False,
            "strict_type_checking": False,
            "enable_range_validation": False,
            "enable_pattern_validation": False,
            "enable_custom_validators": False,
            "max_validation_errors": 50,
            "validation_timeout_seconds": 10.0,
        }

        subcontract = ModelValidationSubcontract.model_validate(subcontract_data)

        assert subcontract.enable_fail_fast is False
        assert subcontract.strict_type_checking is False
        assert subcontract.enable_range_validation is False
        assert subcontract.enable_pattern_validation is False
        assert subcontract.enable_custom_validators is False
        assert subcontract.max_validation_errors == 50
        assert subcontract.validation_timeout_seconds == 10.0

    def test_interface_version_exists(self):
        """Test that INTERFACE_VERSION is accessible and correct."""
        assert hasattr(ModelValidationSubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelValidationSubcontract.INTERFACE_VERSION, ModelSemVer)
        assert ModelValidationSubcontract.INTERFACE_VERSION.major == 1
        assert ModelValidationSubcontract.INTERFACE_VERSION.minor == 0
        assert ModelValidationSubcontract.INTERFACE_VERSION.patch == 0

    def test_max_validation_errors_minimum_constraint(self):
        """Test that max_validation_errors must be at least 1."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_validation_errors": 0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_validation_errors" in error_string
        assert "greater than or equal to 1" in error_string

    def test_max_validation_errors_maximum_constraint(self):
        """Test that max_validation_errors cannot exceed 1000."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_validation_errors": 1001,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_validation_errors" in error_string
        assert "less than or equal to 1000" in error_string

    def test_max_validation_errors_custom_validator_too_low(self):
        """Test custom validator for max_validation_errors < 1."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_validation_errors": -5,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_validation_errors" in error_string

    def test_max_validation_errors_custom_validator_too_high(self):
        """Test custom validator for max_validation_errors > 10000."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_validation_errors": 15000,
        }

        # This should fail at pydantic constraint first (le=1000)
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_validation_errors" in error_string

    def test_validation_timeout_minimum_constraint(self):
        """Test that validation_timeout_seconds must be at least 0.1."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "validation_timeout_seconds": 0.05,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "validation_timeout_seconds" in error_string
        assert "greater than or equal to 0.1" in error_string

    def test_validation_timeout_maximum_constraint(self):
        """Test that validation_timeout_seconds cannot exceed 60.0."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "validation_timeout_seconds": 70.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "validation_timeout_seconds" in error_string
        assert "less than or equal to 60" in error_string

    def test_validation_timeout_custom_validator_zero(self):
        """Test that zero timeout is rejected by pydantic constraint."""
        # Zero values are caught by pydantic ge=0.1 constraint
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "validation_timeout_seconds": 0.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "validation_timeout_seconds" in error_string
        assert "greater than or equal to 0.1" in error_string

    def test_validation_timeout_custom_validator_negative(self):
        """Test custom validator rejects negative timeout."""
        # Negative values should be caught by pydantic ge=0.1 constraint first
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "validation_timeout_seconds": -1.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "validation_timeout_seconds" in error_string

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per model config."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "enable_fail_fast": True,
            "custom_field": "custom_value",
            "unknown_setting": 123,
        }

        subcontract = ModelValidationSubcontract.model_validate(subcontract_data)

        assert subcontract.enable_fail_fast is True
        assert not hasattr(subcontract, "custom_field")
        assert not hasattr(subcontract, "unknown_setting")

    def test_boolean_fields_all_combinations(self):
        """Test all boolean field combinations work correctly."""
        version_data = {"major": 1, "minor": 0, "patch": 0}
        test_cases = [
            # All True
            {
                "version": version_data,
                "enable_fail_fast": True,
                "strict_type_checking": True,
                "enable_range_validation": True,
                "enable_pattern_validation": True,
                "enable_custom_validators": True,
            },
            # All False
            {
                "version": version_data,
                "enable_fail_fast": False,
                "strict_type_checking": False,
                "enable_range_validation": False,
                "enable_pattern_validation": False,
                "enable_custom_validators": False,
            },
            # Mixed
            {
                "version": version_data,
                "enable_fail_fast": True,
                "strict_type_checking": False,
                "enable_range_validation": True,
                "enable_pattern_validation": False,
                "enable_custom_validators": True,
            },
        ]

        for case in test_cases:
            subcontract = ModelValidationSubcontract.model_validate(case)
            for field, expected_value in case.items():
                if field != "version":
                    assert getattr(subcontract, field) == expected_value

    def test_edge_case_max_errors_boundary_values(self):
        """Test boundary values for max_validation_errors."""
        # Minimum valid value
        subcontract = ModelValidationSubcontract(
            version=DEFAULT_VERSION, max_validation_errors=1
        )
        assert subcontract.max_validation_errors == 1

        # Maximum valid value
        subcontract = ModelValidationSubcontract(
            version=DEFAULT_VERSION, max_validation_errors=1000
        )
        assert subcontract.max_validation_errors == 1000

    def test_edge_case_timeout_boundary_values(self):
        """Test boundary values for validation_timeout_seconds."""
        # Minimum valid value
        subcontract = ModelValidationSubcontract(
            version=DEFAULT_VERSION, validation_timeout_seconds=0.1
        )
        assert subcontract.validation_timeout_seconds == 0.1

        # Maximum valid value
        subcontract = ModelValidationSubcontract(
            version=DEFAULT_VERSION, validation_timeout_seconds=60.0
        )
        assert subcontract.validation_timeout_seconds == 60.0

    def test_validate_assignment_enabled(self):
        """Test that validate_assignment is enabled in model config."""
        subcontract = ModelValidationSubcontract(version=DEFAULT_VERSION)

        # Try to assign invalid value after creation
        with pytest.raises(ValidationError):
            subcontract.max_validation_errors = 2000  # Exceeds maximum

    def test_model_serialization_round_trip(self):
        """Test that model can be serialized and deserialized correctly."""
        original = ModelValidationSubcontract(
            version=DEFAULT_VERSION,
            enable_fail_fast=False,
            max_validation_errors=200,
            validation_timeout_seconds=15.5,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = ModelValidationSubcontract.model_validate(data)

        assert restored.enable_fail_fast == original.enable_fail_fast
        assert restored.max_validation_errors == original.max_validation_errors
        assert (
            restored.validation_timeout_seconds == original.validation_timeout_seconds
        )

    def test_model_dump_json_mode(self):
        """Test model_dump with mode='json' for JSON serialization."""
        subcontract = ModelValidationSubcontract(
            version=DEFAULT_VERSION,
            enable_fail_fast=True,
            max_validation_errors=150,
        )

        json_data = subcontract.model_dump(mode="json")

        assert json_data["enable_fail_fast"] is True
        assert json_data["max_validation_errors"] == 150
        assert isinstance(json_data["validation_timeout_seconds"], float)
