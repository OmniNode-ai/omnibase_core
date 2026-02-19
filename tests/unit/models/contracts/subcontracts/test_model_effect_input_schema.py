# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEffectInputSchema - v1.1 preparation.

This model is reserved for v1.1 with minimal implementation in v1.0.
Tests verify basic model behavior: construction, frozen, and extra="forbid".

Implements: ,
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts import ModelEffectInputSchema


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelEffectInputSchema:
    """Test suite for ModelEffectInputSchema model."""

    def test_effect_input_schema_default_construction(self) -> None:
        """Verify ModelEffectInputSchema can be constructed with defaults."""
        schema = ModelEffectInputSchema()
        assert schema.required_fields == []
        assert schema.optional_fields == []

    def test_effect_input_schema_with_required_fields(self) -> None:
        """Verify ModelEffectInputSchema accepts required_fields."""
        schema = ModelEffectInputSchema(
            required_fields=["user_id", "timestamp", "nested.field"]
        )
        assert schema.required_fields == ["user_id", "timestamp", "nested.field"]
        assert schema.optional_fields == []

    def test_effect_input_schema_with_optional_fields(self) -> None:
        """Verify ModelEffectInputSchema accepts optional_fields."""
        schema = ModelEffectInputSchema(
            optional_fields=["description", "metadata.tags"]
        )
        assert schema.required_fields == []
        assert schema.optional_fields == ["description", "metadata.tags"]

    def test_effect_input_schema_with_both_field_types(self) -> None:
        """Verify ModelEffectInputSchema accepts both required and optional fields."""
        schema = ModelEffectInputSchema(
            required_fields=["id", "name"],
            optional_fields=["description", "tags"],
        )
        assert schema.required_fields == ["id", "name"]
        assert schema.optional_fields == ["description", "tags"]

    def test_effect_input_schema_frozen(self) -> None:
        """Verify model is frozen (immutable after creation)."""
        schema = ModelEffectInputSchema(
            required_fields=["id"],
            optional_fields=["name"],
        )
        with pytest.raises(ValidationError):
            schema.required_fields = ["new_id"]  # type: ignore[misc]

        with pytest.raises(ValidationError):
            schema.optional_fields = ["new_name"]  # type: ignore[misc]

    def test_effect_input_schema_forbids_extra(self) -> None:
        """Verify extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputSchema(
                required_fields=["id"],
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value)

    def test_effect_input_schema_empty_lists_valid(self) -> None:
        """Verify empty lists are valid for both field types."""
        schema = ModelEffectInputSchema(
            required_fields=[],
            optional_fields=[],
        )
        assert schema.required_fields == []
        assert schema.optional_fields == []

    def test_effect_input_schema_nested_field_format(self) -> None:
        """Verify nested field format (e.g., 'nested.field') is accepted."""
        schema = ModelEffectInputSchema(
            required_fields=["user.profile.name", "user.settings.theme"],
            optional_fields=["metadata.tags", "config.options.debug"],
        )
        assert len(schema.required_fields) == 2
        assert len(schema.optional_fields) == 2
        assert "user.profile.name" in schema.required_fields
        assert "metadata.tags" in schema.optional_fields


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelEffectInputSchemaExport:
    """Test that ModelEffectInputSchema is properly exported from subcontracts module."""

    def test_import_from_subcontracts(self) -> None:
        """Test model can be imported from subcontracts module."""
        from omnibase_core.models.contracts.subcontracts import ModelEffectInputSchema

        # Verify it's the same class as direct import
        from omnibase_core.models.contracts.subcontracts.model_effect_input_schema import (
            ModelEffectInputSchema as DirectModelEffectInputSchema,
        )

        assert ModelEffectInputSchema is DirectModelEffectInputSchema

    def test_model_in_subcontracts_all(self) -> None:
        """Test model is in subcontracts __all__."""
        from omnibase_core.models.contracts import subcontracts

        assert "ModelEffectInputSchema" in subcontracts.__all__
