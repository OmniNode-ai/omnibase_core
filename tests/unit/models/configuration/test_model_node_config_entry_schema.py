# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelNodeConfigEntry and ModelNodeConfigSchema.

Tests validation constraints including:
- Literal type constraints for value_type/config_type
- Default value type validation
- Bool/int coercion prevention
- Alias behavior for ModelNodeConfigSchema
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.configuration.model_node_config_entry import (
    ModelNodeConfigEntry,
)
from omnibase_core.models.configuration.model_node_config_schema import (
    ModelNodeConfigSchema,
)


@pytest.mark.unit
class TestModelNodeConfigEntry:
    """Test cases for ModelNodeConfigEntry."""

    def test_valid_int_entry(self) -> None:
        """Test valid int configuration entry."""
        entry = ModelNodeConfigEntry(
            key="compute.max_workers",
            value_type="int",
            default=4,
        )
        assert entry.key == "compute.max_workers"
        assert entry.value_type == "int"
        assert entry.default == 4

    def test_valid_float_entry(self) -> None:
        """Test valid float configuration entry."""
        entry = ModelNodeConfigEntry(
            key="compute.threshold",
            value_type="float",
            default=100.5,
        )
        assert entry.value_type == "float"
        assert entry.default == 100.5

    def test_valid_float_entry_with_int_default(self) -> None:
        """Test float entry accepts int default value."""
        entry = ModelNodeConfigEntry(
            key="compute.threshold",
            value_type="float",
            default=100,
        )
        assert entry.value_type == "float"
        assert entry.default == 100

    def test_valid_bool_entry(self) -> None:
        """Test valid bool configuration entry."""
        entry = ModelNodeConfigEntry(
            key="feature.enabled",
            value_type="bool",
            default=True,
        )
        assert entry.value_type == "bool"
        assert entry.default is True

    def test_valid_str_entry(self) -> None:
        """Test valid str configuration entry."""
        entry = ModelNodeConfigEntry(
            key="config.name",
            value_type="str",
            default="production",
        )
        assert entry.value_type == "str"
        assert entry.default == "production"

    def test_invalid_value_type_rejected(self) -> None:
        """Test that invalid value_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigEntry(
                key="test.key",
                value_type="invalid",  # type: ignore[arg-type]
                default="test",
            )
        assert "value_type" in str(exc_info.value)

    def test_int_default_for_bool_rejected(self) -> None:
        """Test that int default is rejected for bool type (prevents coercion)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigEntry(
                key="test.key",
                value_type="bool",
                default=1,  # int, not bool
            )
        assert "must be bool" in str(exc_info.value)

    def test_zero_default_for_bool_rejected(self) -> None:
        """Test that 0 default is rejected for bool type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigEntry(
                key="test.key",
                value_type="bool",
                default=0,  # int, not bool
            )
        assert "must be bool" in str(exc_info.value)

    def test_str_default_for_int_rejected(self) -> None:
        """Test that str default is rejected for int type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigEntry(
                key="test.key",
                value_type="int",
                default="not_an_int",
            )
        assert "must be int" in str(exc_info.value)

    def test_float_default_for_int_rejected(self) -> None:
        """Test that float default is rejected for int type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigEntry(
                key="test.key",
                value_type="int",
                default=4.5,
            )
        assert "must be int" in str(exc_info.value)

    def test_int_default_for_str_rejected(self) -> None:
        """Test that int default is rejected for str type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigEntry(
                key="test.key",
                value_type="str",
                default=42,
            )
        assert "must be str" in str(exc_info.value)

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable (frozen)."""
        entry = ModelNodeConfigEntry(
            key="test.key",
            value_type="int",
            default=4,
        )
        with pytest.raises(ValidationError):
            entry.key = "new.key"  # type: ignore[misc]


@pytest.mark.unit
class TestModelNodeConfigSchema:
    """Test cases for ModelNodeConfigSchema."""

    def test_valid_schema_with_alias(self) -> None:
        """Test valid schema using 'type' alias."""
        schema = ModelNodeConfigSchema(
            key="compute.max_workers",
            type="int",  # Using alias
            default=4,
        )
        assert schema.key == "compute.max_workers"
        assert schema.config_type == "int"  # Accessing via field name
        assert schema.default == 4

    def test_valid_schema_with_field_name(self) -> None:
        """Test valid schema using 'config_type' field name."""
        schema = ModelNodeConfigSchema(
            key="compute.max_workers",
            config_type="int",  # Using field name
            default=4,
        )
        assert schema.config_type == "int"

    def test_model_dump_with_alias(self) -> None:
        """Test model_dump with by_alias=True returns 'type'."""
        schema = ModelNodeConfigSchema(
            key="compute.max_workers",
            type="int",
            default=4,
        )
        dumped = schema.model_dump(by_alias=True)
        assert "type" in dumped
        assert dumped["type"] == "int"
        assert "config_type" not in dumped

    def test_model_dump_without_alias(self) -> None:
        """Test model_dump without alias returns 'config_type'."""
        schema = ModelNodeConfigSchema(
            key="compute.max_workers",
            type="int",
            default=4,
        )
        dumped = schema.model_dump()
        assert "config_type" in dumped
        assert dumped["config_type"] == "int"
        # 'type' may or may not be in the output depending on Pydantic version

    def test_int_default_for_bool_rejected(self) -> None:
        """Test that int default is rejected for bool type."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigSchema(
                key="test.key",
                type="bool",
                default=1,
            )
        assert "must be bool" in str(exc_info.value)

    def test_invalid_type_rejected(self) -> None:
        """Test that invalid type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeConfigSchema(
                key="test.key",
                type="invalid",  # type: ignore[arg-type]
                default="test",
            )
        # Check for validation error in type field
        assert "type" in str(exc_info.value).lower()

    def test_valid_float_with_int_default(self) -> None:
        """Test float type accepts int default value."""
        schema = ModelNodeConfigSchema(
            key="compute.threshold",
            type="float",
            default=100,
        )
        assert schema.config_type == "float"
        assert schema.default == 100

    def test_valid_bool_true(self) -> None:
        """Test bool type with True default."""
        schema = ModelNodeConfigSchema(
            key="feature.enabled",
            type="bool",
            default=True,
        )
        assert schema.config_type == "bool"
        assert schema.default is True

    def test_valid_bool_false(self) -> None:
        """Test bool type with False default."""
        schema = ModelNodeConfigSchema(
            key="feature.disabled",
            type="bool",
            default=False,
        )
        assert schema.config_type == "bool"
        assert schema.default is False

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable (frozen)."""
        schema = ModelNodeConfigSchema(
            key="test.key",
            type="int",
            default=4,
        )
        with pytest.raises(ValidationError):
            schema.key = "new.key"  # type: ignore[misc]
