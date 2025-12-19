"""
Test for ModelSerializationSubcontract - Serialization subcontract model.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.models.contracts.subcontracts.model_serialization_subcontract import (
    ModelSerializationSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelSerializationSubcontract:
    """Test the serialization subcontract model."""

    def test_valid_subcontract_creation_defaults(self):
        """Test creating a valid subcontract with all defaults."""
        subcontract = ModelSerializationSubcontract(version=DEFAULT_VERSION)

        assert subcontract.serialization_format == "yaml"
        assert subcontract.enable_canonical_mode is True
        assert subcontract.exclude_none_values is True
        assert subcontract.exclude_defaults is False
        assert subcontract.indent_spaces == 2
        assert subcontract.sort_keys is True
        assert subcontract.enable_compression is False
        assert subcontract.max_serialized_size_bytes == 10485760  # 10MB

    def test_valid_subcontract_creation_custom_values(self):
        """Test creating a valid subcontract with custom values."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "serialization_format": "json",
            "enable_canonical_mode": False,
            "exclude_none_values": False,
            "exclude_defaults": True,
            "indent_spaces": 4,
            "sort_keys": False,
            "enable_compression": True,
            "max_serialized_size_bytes": 5242880,  # 5MB
        }

        subcontract = ModelSerializationSubcontract.model_validate(subcontract_data)

        assert subcontract.serialization_format == "json"
        assert subcontract.enable_canonical_mode is False
        assert subcontract.exclude_none_values is False
        assert subcontract.exclude_defaults is True
        assert subcontract.indent_spaces == 4
        assert subcontract.sort_keys is False
        assert subcontract.enable_compression is True
        assert subcontract.max_serialized_size_bytes == 5242880

    def test_interface_version_exists(self):
        """Test that INTERFACE_VERSION is accessible and correct."""
        assert hasattr(ModelSerializationSubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelSerializationSubcontract.INTERFACE_VERSION, ModelSemVer)
        assert ModelSerializationSubcontract.INTERFACE_VERSION.major == 1
        assert ModelSerializationSubcontract.INTERFACE_VERSION.minor == 0
        assert ModelSerializationSubcontract.INTERFACE_VERSION.patch == 0

    def test_serialization_format_yaml(self):
        """Test yaml format validation and normalization."""
        test_cases = ["yaml", "YAML", "Yaml", "  yaml  "]

        for format_value in test_cases:
            subcontract = ModelSerializationSubcontract(
                version=DEFAULT_VERSION, serialization_format=format_value
            )
            assert subcontract.serialization_format == "yaml"

    def test_serialization_format_json(self):
        """Test json format validation and normalization."""
        test_cases = ["json", "JSON", "Json", "  json  "]

        for format_value in test_cases:
            subcontract = ModelSerializationSubcontract(
                version=DEFAULT_VERSION, serialization_format=format_value
            )
            assert subcontract.serialization_format == "json"

    def test_serialization_format_toml(self):
        """Test toml format validation and normalization."""
        test_cases = ["toml", "TOML", "Toml", "  toml  "]

        for format_value in test_cases:
            subcontract = ModelSerializationSubcontract(
                version=DEFAULT_VERSION, serialization_format=format_value
            )
            assert subcontract.serialization_format == "toml"

    def test_serialization_format_invalid(self):
        """Test that invalid format raises error."""
        invalid_formats = ["xml", "csv", "binary", "invalid", ""]

        for invalid_format in invalid_formats:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelSerializationSubcontract(
                    version=DEFAULT_VERSION, serialization_format=invalid_format
                )

            error_string = str(exc_info.value)
            assert "serialization_format must be one of" in error_string
            assert "yaml" in error_string
            assert "json" in error_string
            assert "toml" in error_string

    def test_indent_spaces_minimum_constraint(self):
        """Test that indent_spaces must be at least 0."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "indent_spaces": -1,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "indent_spaces" in error_string
        assert "greater than or equal to 0" in error_string

    def test_indent_spaces_maximum_constraint(self):
        """Test that indent_spaces cannot exceed 8."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "indent_spaces": 9,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "indent_spaces" in error_string
        assert "less than or equal to 8" in error_string

    def test_indent_spaces_custom_validator_too_high(self):
        """Test custom validator for indent_spaces > 16."""
        # Note: Pydantic constraint (le=8) will catch this before custom validator
        # This test documents the custom validator logic
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "indent_spaces": 20,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "indent_spaces" in error_string

    def test_indent_spaces_boundary_values(self):
        """Test boundary values for indent_spaces."""
        # Minimum valid value
        subcontract = ModelSerializationSubcontract(
            version=DEFAULT_VERSION, indent_spaces=0
        )
        assert subcontract.indent_spaces == 0

        # Maximum valid value
        subcontract = ModelSerializationSubcontract(
            version=DEFAULT_VERSION, indent_spaces=8
        )
        assert subcontract.indent_spaces == 8

    def test_max_serialized_size_minimum_constraint(self):
        """Test that max_serialized_size_bytes must be at least 1KB."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_serialized_size_bytes": 500,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_serialized_size_bytes" in error_string
        assert "greater than or equal to 1024" in error_string

    def test_max_serialized_size_maximum_constraint(self):
        """Test that max_serialized_size_bytes cannot exceed 100MB."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_serialized_size_bytes": 104857601,
        }  # 100MB + 1

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_serialized_size_bytes" in error_string
        assert "less than or equal to 104857600" in error_string

    def test_max_serialized_size_custom_validator_too_low(self):
        """Test custom validator for max_serialized_size_bytes < 1KB."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_serialized_size_bytes": 100,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_serialized_size_bytes" in error_string

    def test_max_serialized_size_custom_validator_too_high(self):
        """Test custom validator for max_serialized_size_bytes > 1GB."""
        # Note: Pydantic constraint (le=104857600) will catch this first
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "max_serialized_size_bytes": 2147483648,
        }  # 2GB

        with pytest.raises(ValidationError) as exc_info:
            ModelSerializationSubcontract.model_validate(subcontract_data)

        error_string = str(exc_info.value)
        assert "max_serialized_size_bytes" in error_string

    def test_max_serialized_size_boundary_values(self):
        """Test boundary values for max_serialized_size_bytes."""
        # Minimum valid value (1KB)
        subcontract = ModelSerializationSubcontract(
            version=DEFAULT_VERSION, max_serialized_size_bytes=1024
        )
        assert subcontract.max_serialized_size_bytes == 1024

        # Maximum valid value (100MB)
        subcontract = ModelSerializationSubcontract(
            version=DEFAULT_VERSION, max_serialized_size_bytes=104857600
        )
        assert subcontract.max_serialized_size_bytes == 104857600

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per model config."""
        subcontract_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "serialization_format": "json",
            "custom_field": "custom_value",
            "unknown_setting": 123,
        }

        subcontract = ModelSerializationSubcontract.model_validate(subcontract_data)

        assert subcontract.serialization_format == "json"
        assert not hasattr(subcontract, "custom_field")
        assert not hasattr(subcontract, "unknown_setting")

    def test_boolean_fields_all_combinations(self):
        """Test all boolean field combinations work correctly."""
        test_cases = [
            # All True
            {
                "version": {"major": 1, "minor": 0, "patch": 0},
                "enable_canonical_mode": True,
                "exclude_none_values": True,
                "exclude_defaults": True,
                "sort_keys": True,
                "enable_compression": True,
            },
            # All False
            {
                "version": {"major": 1, "minor": 0, "patch": 0},
                "enable_canonical_mode": False,
                "exclude_none_values": False,
                "exclude_defaults": False,
                "sort_keys": False,
                "enable_compression": False,
            },
            # Mixed
            {
                "version": {"major": 1, "minor": 0, "patch": 0},
                "enable_canonical_mode": True,
                "exclude_none_values": False,
                "exclude_defaults": True,
                "sort_keys": False,
                "enable_compression": True,
            },
        ]

        for case in test_cases:
            subcontract = ModelSerializationSubcontract.model_validate(case)
            for field, expected_value in case.items():
                if field == "version":
                    # Skip version field - it's converted from dict to ModelSemVer
                    continue
                assert getattr(subcontract, field) == expected_value

    def test_validate_assignment_enabled(self):
        """Test that validate_assignment is enabled in model config."""
        subcontract = ModelSerializationSubcontract(version=DEFAULT_VERSION)

        # Try to assign invalid value after creation
        with pytest.raises(ValidationError):
            subcontract.indent_spaces = 20  # Exceeds maximum

    def test_model_serialization_round_trip(self):
        """Test that model can be serialized and deserialized correctly."""
        original = ModelSerializationSubcontract(
            version=DEFAULT_VERSION,
            serialization_format="json",
            indent_spaces=4,
            max_serialized_size_bytes=20971520,  # 20MB
            enable_compression=True,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = ModelSerializationSubcontract.model_validate(data)

        assert restored.serialization_format == original.serialization_format
        assert restored.indent_spaces == original.indent_spaces
        assert restored.max_serialized_size_bytes == original.max_serialized_size_bytes
        assert restored.enable_compression == original.enable_compression

    def test_model_dump_json_mode(self):
        """Test model_dump with mode='json' for JSON serialization."""
        subcontract = ModelSerializationSubcontract(
            version=DEFAULT_VERSION,
            serialization_format="toml",
            indent_spaces=3,
        )

        json_data = subcontract.model_dump(mode="json")

        assert json_data["serialization_format"] == "toml"
        assert json_data["indent_spaces"] == 3
        assert isinstance(json_data["max_serialized_size_bytes"], int)

    def test_all_formats_with_various_settings(self):
        """Test all format combinations with various settings."""
        formats = ["yaml", "json", "toml"]
        settings = [
            {"indent_spaces": 2, "sort_keys": True},
            {"indent_spaces": 4, "sort_keys": False},
            {"indent_spaces": 0, "sort_keys": True},
        ]

        for fmt in formats:
            for setting in settings:
                subcontract = ModelSerializationSubcontract(
                    version=DEFAULT_VERSION, serialization_format=fmt, **setting
                )
                assert subcontract.serialization_format == fmt
                assert subcontract.indent_spaces == setting["indent_spaces"]
                assert subcontract.sort_keys == setting["sort_keys"]

    def test_realistic_use_cases(self):
        """Test realistic configuration use cases."""
        # Use case 1: Canonical YAML with strict formatting
        yaml_config = ModelSerializationSubcontract(
            version=DEFAULT_VERSION,
            serialization_format="yaml",
            enable_canonical_mode=True,
            exclude_none_values=True,
            indent_spaces=2,
            sort_keys=True,
        )
        assert yaml_config.serialization_format == "yaml"
        assert yaml_config.enable_canonical_mode is True

        # Use case 2: Compact JSON without formatting
        json_config = ModelSerializationSubcontract(
            version=DEFAULT_VERSION,
            serialization_format="json",
            exclude_none_values=True,
            exclude_defaults=True,
            indent_spaces=0,
            enable_compression=True,
        )
        assert json_config.serialization_format == "json"
        assert json_config.indent_spaces == 0

        # Use case 3: Human-readable TOML
        toml_config = ModelSerializationSubcontract(
            version=DEFAULT_VERSION,
            serialization_format="toml",
            indent_spaces=4,
            sort_keys=True,
            exclude_none_values=False,
        )
        assert toml_config.serialization_format == "toml"
        assert toml_config.indent_spaces == 4
