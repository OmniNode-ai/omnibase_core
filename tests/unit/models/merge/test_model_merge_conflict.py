# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelMergeConflict and EnumMergeConflictType."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumMergeConflictType
from omnibase_core.models.merge import ModelMergeConflict


@pytest.mark.unit
class TestEnumMergeConflictType:
    """Tests for EnumMergeConflictType enum."""

    @pytest.mark.unit
    def test_enum_values(self) -> None:
        """Test that all expected enum values exist."""
        assert EnumMergeConflictType.TYPE_MISMATCH.value == "type_mismatch"
        assert EnumMergeConflictType.INCOMPATIBLE.value == "incompatible"
        assert EnumMergeConflictType.REQUIRED_MISSING.value == "required_missing"
        assert EnumMergeConflictType.SCHEMA_VIOLATION.value == "schema_violation"
        assert EnumMergeConflictType.LIST_CONFLICT.value == "list_conflict"
        assert EnumMergeConflictType.NULLABLE_VIOLATION.value == "nullable_violation"
        assert EnumMergeConflictType.CONSTRAINT_CONFLICT.value == "constraint_conflict"

    @pytest.mark.unit
    def test_enum_count(self) -> None:
        """Test that we have exactly 7 conflict types."""
        assert len(EnumMergeConflictType) == 7

    @pytest.mark.unit
    def test_str_representation(self) -> None:
        """Test string representation returns value."""
        assert str(EnumMergeConflictType.TYPE_MISMATCH) == "type_mismatch"
        assert str(EnumMergeConflictType.LIST_CONFLICT) == "list_conflict"

    @pytest.mark.unit
    def test_repr_representation(self) -> None:
        """Test repr returns detailed format."""
        assert (
            repr(EnumMergeConflictType.TYPE_MISMATCH)
            == "EnumMergeConflictType.TYPE_MISMATCH"
        )

    @pytest.mark.unit
    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        conflict_type = EnumMergeConflictType("type_mismatch")
        assert conflict_type == EnumMergeConflictType.TYPE_MISMATCH

    @pytest.mark.unit
    def test_enum_invalid_value(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumMergeConflictType("invalid_type")


@pytest.mark.unit
class TestModelMergeConflict:
    """Tests for ModelMergeConflict model."""

    @pytest.mark.unit
    def test_minimal_conflict(self) -> None:
        """Test creating a minimal conflict with required fields only."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.field == "timeout_ms"
        assert conflict.base_value == 5000
        assert conflict.patch_value == "invalid"
        assert conflict.conflict_type == EnumMergeConflictType.TYPE_MISMATCH
        assert conflict.message is None
        assert conflict.suggested_resolution is None

    @pytest.mark.unit
    def test_full_conflict(self) -> None:
        """Test creating a conflict with all fields."""
        conflict = ModelMergeConflict(
            field="descriptor.timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            message="Expected int, got str",
            suggested_resolution="Provide an integer value for timeout_ms",
        )
        assert conflict.field == "descriptor.timeout_ms"
        assert conflict.message == "Expected int, got str"
        assert (
            conflict.suggested_resolution == "Provide an integer value for timeout_ms"
        )

    @pytest.mark.unit
    def test_field_required(self) -> None:
        """Test that field is required."""
        with pytest.raises(ValidationError):
            ModelMergeConflict(
                base_value=5000,
                patch_value="invalid",
                conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            )  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_field_cannot_be_empty(self) -> None:
        """Test that field cannot be empty string."""
        with pytest.raises(ValidationError):
            ModelMergeConflict(
                field="",
                base_value=5000,
                patch_value="invalid",
                conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            )

    @pytest.mark.unit
    def test_base_value_required(self) -> None:
        """Test that base_value is required."""
        with pytest.raises(ValidationError):
            ModelMergeConflict(
                field="timeout_ms",
                patch_value="invalid",
                conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            )  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_patch_value_required(self) -> None:
        """Test that patch_value is required."""
        with pytest.raises(ValidationError):
            ModelMergeConflict(
                field="timeout_ms",
                base_value=5000,
                conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            )  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_conflict_type_required(self) -> None:
        """Test that conflict_type is required."""
        with pytest.raises(ValidationError):
            ModelMergeConflict(
                field="timeout_ms",
                base_value=5000,
                patch_value="invalid",
            )  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        with pytest.raises(ValidationError):
            conflict.field = "new_field"  # type: ignore[misc]

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelMergeConflict(
                field="timeout_ms",
                base_value=5000,
                patch_value="invalid",
                conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
                extra_field="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelMergeConflictHelperMethods:
    """Tests for ModelMergeConflict helper methods."""

    @pytest.mark.unit
    def test_is_type_error_true(self) -> None:
        """Test is_type_error returns True for TYPE_MISMATCH."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.is_type_error() is True

    @pytest.mark.unit
    def test_is_type_error_false(self) -> None:
        """Test is_type_error returns False for other types."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value=None,
            conflict_type=EnumMergeConflictType.NULLABLE_VIOLATION,
        )
        assert conflict.is_type_error() is False

    @pytest.mark.unit
    def test_is_list_conflict_true(self) -> None:
        """Test is_list_conflict returns True for LIST_CONFLICT."""
        conflict = ModelMergeConflict(
            field="handlers",
            base_value=["handler_a"],
            patch_value={"add": ["handler_a"], "remove": ["handler_a"]},
            conflict_type=EnumMergeConflictType.LIST_CONFLICT,
        )
        assert conflict.is_list_conflict() is True

    @pytest.mark.unit
    def test_is_list_conflict_false(self) -> None:
        """Test is_list_conflict returns False for other types."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.is_list_conflict() is False

    @pytest.mark.unit
    def test_is_schema_violation_true(self) -> None:
        """Test is_schema_violation returns True for SCHEMA_VIOLATION."""
        conflict = ModelMergeConflict(
            field="name",
            base_value="valid_name",
            patch_value="x" * 1000,  # Too long
            conflict_type=EnumMergeConflictType.SCHEMA_VIOLATION,
        )
        assert conflict.is_schema_violation() is True

    @pytest.mark.unit
    def test_is_required_missing_true(self) -> None:
        """Test is_required_missing returns True for REQUIRED_MISSING."""
        conflict = ModelMergeConflict(
            field="required_field",
            base_value="must_have",
            patch_value=None,
            conflict_type=EnumMergeConflictType.REQUIRED_MISSING,
        )
        assert conflict.is_required_missing() is True

    @pytest.mark.unit
    def test_is_constraint_conflict_true_for_constraint_conflict(self) -> None:
        """Test is_constraint_conflict returns True for CONSTRAINT_CONFLICT."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value={"min": 1000},
            patch_value={"max": 500},
            conflict_type=EnumMergeConflictType.CONSTRAINT_CONFLICT,
        )
        assert conflict.is_constraint_conflict() is True

    @pytest.mark.unit
    def test_is_constraint_conflict_true_for_incompatible(self) -> None:
        """Test is_constraint_conflict returns True for INCOMPATIBLE."""
        conflict = ModelMergeConflict(
            field="mode",
            base_value="sync",
            patch_value="async",
            conflict_type=EnumMergeConflictType.INCOMPATIBLE,
        )
        assert conflict.is_constraint_conflict() is True

    @pytest.mark.unit
    def test_is_constraint_conflict_false(self) -> None:
        """Test is_constraint_conflict returns False for unrelated types."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.is_constraint_conflict() is False


@pytest.mark.unit
class TestModelMergeConflictFieldPath:
    """Tests for field path handling methods."""

    @pytest.mark.unit
    def test_get_field_path_parts_simple(self) -> None:
        """Test get_field_path_parts for simple field."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.get_field_path_parts() == ["timeout_ms"]

    @pytest.mark.unit
    def test_get_field_path_parts_nested(self) -> None:
        """Test get_field_path_parts for nested field."""
        conflict = ModelMergeConflict(
            field="descriptor.timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.get_field_path_parts() == ["descriptor", "timeout_ms"]

    @pytest.mark.unit
    def test_get_field_path_parts_deeply_nested(self) -> None:
        """Test get_field_path_parts for deeply nested field."""
        conflict = ModelMergeConflict(
            field="a.b.c.d",
            base_value=1,
            patch_value=2,
            conflict_type=EnumMergeConflictType.INCOMPATIBLE,
        )
        assert conflict.get_field_path_parts() == ["a", "b", "c", "d"]

    @pytest.mark.unit
    def test_get_parent_field_simple(self) -> None:
        """Test get_parent_field for simple field returns None."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.get_parent_field() is None

    @pytest.mark.unit
    def test_get_parent_field_nested(self) -> None:
        """Test get_parent_field for nested field."""
        conflict = ModelMergeConflict(
            field="descriptor.timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.get_parent_field() == "descriptor"

    @pytest.mark.unit
    def test_get_parent_field_deeply_nested(self) -> None:
        """Test get_parent_field for deeply nested field."""
        conflict = ModelMergeConflict(
            field="a.b.c.d",
            base_value=1,
            patch_value=2,
            conflict_type=EnumMergeConflictType.INCOMPATIBLE,
        )
        assert conflict.get_parent_field() == "a.b.c"


@pytest.mark.unit
class TestModelMergeConflictRepresentation:
    """Tests for ModelMergeConflict string representations."""

    @pytest.mark.unit
    def test_str_with_message(self) -> None:
        """Test __str__ when message is provided."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            message="Expected int, got str",
        )
        result = str(conflict)
        assert "timeout_ms" in result
        assert "Expected int, got str" in result

    @pytest.mark.unit
    def test_str_without_message(self) -> None:
        """Test __str__ when message is not provided."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        result = str(conflict)
        assert "timeout_ms" in result
        assert "type_mismatch" in result

    @pytest.mark.unit
    def test_repr(self) -> None:
        """Test __repr__ format."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        result = repr(conflict)
        assert "ModelMergeConflict" in result
        assert "timeout_ms" in result
        assert "TYPE_MISMATCH" in result
        assert "5000" in result
        assert "invalid" in result


@pytest.mark.unit
class TestModelMergeConflictValueTypes:
    """Tests for various value types in ModelMergeConflict."""

    @pytest.mark.unit
    def test_none_values(self) -> None:
        """Test that None values are accepted for base_value and patch_value."""
        conflict = ModelMergeConflict(
            field="optional_field",
            base_value=None,
            patch_value="new_value",
            conflict_type=EnumMergeConflictType.NULLABLE_VIOLATION,
        )
        assert conflict.base_value is None
        assert conflict.patch_value == "new_value"

    @pytest.mark.unit
    def test_list_values(self) -> None:
        """Test that list values are accepted."""
        conflict = ModelMergeConflict(
            field="handlers",
            base_value=["handler_a", "handler_b"],
            patch_value=["handler_c"],
            conflict_type=EnumMergeConflictType.INCOMPATIBLE,
        )
        assert conflict.base_value == ["handler_a", "handler_b"]
        assert conflict.patch_value == ["handler_c"]

    @pytest.mark.unit
    def test_dict_values(self) -> None:
        """Test that dict values are accepted."""
        conflict = ModelMergeConflict(
            field="config",
            base_value={"timeout": 5000, "retries": 3},
            patch_value={"timeout": "invalid"},
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.base_value == {"timeout": 5000, "retries": 3}
        assert conflict.patch_value == {"timeout": "invalid"}

    @pytest.mark.unit
    def test_mixed_types(self) -> None:
        """Test that mixed types are accepted (base int, patch str)."""
        conflict = ModelMergeConflict(
            field="value",
            base_value=42,
            patch_value="forty-two",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.base_value == 42
        assert conflict.patch_value == "forty-two"

    @pytest.mark.unit
    def test_boolean_values(self) -> None:
        """Test that boolean values are accepted."""
        conflict = ModelMergeConflict(
            field="enabled",
            base_value=True,
            patch_value="yes",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        assert conflict.base_value is True
        assert conflict.patch_value == "yes"


@pytest.mark.unit
class TestModelMergeConflictSerialization:
    """Tests for ModelMergeConflict serialization."""

    @pytest.mark.unit
    def test_model_dump(self) -> None:
        """Test model_dump produces expected output."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
            message="Expected int, got str",
        )
        data = conflict.model_dump()
        assert data["field"] == "timeout_ms"
        assert data["base_value"] == 5000
        assert data["patch_value"] == "invalid"
        assert data["conflict_type"] == EnumMergeConflictType.TYPE_MISMATCH
        assert data["message"] == "Expected int, got str"
        assert data["suggested_resolution"] is None

    @pytest.mark.unit
    def test_model_dump_json(self) -> None:
        """Test model_dump_json produces valid JSON."""
        conflict = ModelMergeConflict(
            field="timeout_ms",
            base_value=5000,
            patch_value="invalid",
            conflict_type=EnumMergeConflictType.TYPE_MISMATCH,
        )
        json_str = conflict.model_dump_json()
        assert '"field":"timeout_ms"' in json_str
        assert '"base_value":5000' in json_str
        assert '"conflict_type":"type_mismatch"' in json_str

    @pytest.mark.unit
    def test_model_validate(self) -> None:
        """Test model_validate from dictionary."""
        data = {
            "field": "timeout_ms",
            "base_value": 5000,
            "patch_value": "invalid",
            "conflict_type": "type_mismatch",
            "message": "Type error",
        }
        conflict = ModelMergeConflict.model_validate(data)
        assert conflict.field == "timeout_ms"
        assert conflict.conflict_type == EnumMergeConflictType.TYPE_MISMATCH
        assert conflict.message == "Type error"

    @pytest.mark.unit
    def test_from_attributes(self) -> None:
        """Test that from_attributes=True works for object conversion."""

        class ConflictLike:
            field = "test_field"
            base_value = 100
            patch_value = "wrong"
            conflict_type = EnumMergeConflictType.TYPE_MISMATCH
            message = None
            suggested_resolution = None

        obj = ConflictLike()
        conflict = ModelMergeConflict.model_validate(obj, from_attributes=True)
        assert conflict.field == "test_field"
        assert conflict.base_value == 100
