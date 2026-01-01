"""Tests for ModelProjectorIndex.

Tests cover:
1. Valid index creation with required fields
2. Default values (type="btree", unique=False)
3. Index type validation (btree, gin, hash only)
4. Auto-generated name behavior
5. Frozen/immutable behavior
6. Extra fields rejected
7. Serialization roundtrip
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelProjectorIndexCreation:
    """Tests for ModelProjectorIndex creation and validation."""

    def test_valid_index_minimal(self) -> None:
        """Valid index with only required columns field."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["user_id"])

        assert index.columns == ["user_id"]
        assert index.type == "btree"  # default
        assert index.unique is False  # default
        assert index.name is None  # auto-generated if not provided

    def test_valid_index_with_all_fields(self) -> None:
        """Valid index with all fields specified."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(
            name="idx_user_created",
            columns=["user_id", "created_at"],
            type="btree",
            unique=True,
        )

        assert index.name == "idx_user_created"
        assert index.columns == ["user_id", "created_at"]
        assert index.type == "btree"
        assert index.unique is True

    def test_valid_gin_index(self) -> None:
        """Valid GIN index type."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["tags"], type="gin")

        assert index.type == "gin"

    def test_valid_hash_index(self) -> None:
        """Valid hash index type."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["lookup_key"], type="hash")

        assert index.type == "hash"

    def test_columns_is_required(self) -> None:
        """Columns field is required."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorIndex()

        assert "columns" in str(exc_info.value)

    def test_columns_must_be_non_empty(self) -> None:
        """Columns list must have at least one element."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorIndex(columns=[])

        assert "columns" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelProjectorIndexTypeValidation:
    """Tests for index type validation."""

    def test_invalid_index_type_rejected(self) -> None:
        """Only btree, gin, hash are allowed."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorIndex(columns=["id"], type="brin")  # type: ignore[arg-type]

        # Should mention the invalid type or list valid options
        error_str = str(exc_info.value).lower()
        assert "type" in error_str or "brin" in error_str

    def test_index_type_is_case_sensitive(self) -> None:
        """Index type must be lowercase."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        with pytest.raises(ValidationError):
            ModelProjectorIndex(columns=["id"], type="BTREE")  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelProjectorIndexImmutability:
    """Tests for frozen/immutable behavior."""

    def test_index_is_frozen(self) -> None:
        """Index should be immutable after creation."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["user_id"])

        with pytest.raises(ValidationError):
            index.unique = True  # type: ignore[misc]

    def test_index_is_hashable(self) -> None:
        """Frozen index should be hashable."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["user_id"])

        # Should not raise
        hash_value = hash(index)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelProjectorIndexExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorIndex(
                columns=["user_id"],
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelProjectorIndexSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        original = ModelProjectorIndex(
            name="idx_test",
            columns=["col1", "col2"],
            type="gin",
            unique=True,
        )
        data = original.model_dump()
        restored = ModelProjectorIndex.model_validate(data)

        assert restored == original

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        original = ModelProjectorIndex(columns=["id"], type="hash", unique=False)
        json_str = original.model_dump_json()
        restored = ModelProjectorIndex.model_validate_json(json_str)

        assert restored == original
