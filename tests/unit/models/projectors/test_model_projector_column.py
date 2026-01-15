# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProjectorColumn.

Tests cover:
1. Valid column creation with required fields
2. Source path format validation (event.payload.x pattern)
3. Optional on_event and default fields
4. Column type as string (not enum - extensible)
5. Frozen/immutable behavior
6. Extra fields rejected
7. Serialization roundtrip
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelProjectorColumnCreation:
    """Tests for ModelProjectorColumn creation and validation."""

    def test_valid_column_minimal(self) -> None:
        """Valid column with only required fields."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="node_name",
            type="TEXT",
            source="event.payload.node_name",
        )

        assert column.name == "node_name"
        assert column.type == "TEXT"
        assert column.source == "event.payload.node_name"
        assert column.on_event is None
        assert column.default is None

    def test_valid_column_with_all_fields(self) -> None:
        """Valid column with all fields specified."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="status",
            type="TEXT",
            source="event.payload.status",
            on_event="node.status.changed.v1",
            default="UNKNOWN",
        )

        assert column.name == "status"
        assert column.type == "TEXT"
        assert column.source == "event.payload.status"
        assert column.on_event == "node.status.changed.v1"
        assert column.default == "UNKNOWN"

    def test_various_column_types(self) -> None:
        """Various SQL column types are accepted as strings."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        for col_type in ["UUID", "TEXT", "JSONB", "TIMESTAMPTZ", "INTEGER", "BOOLEAN"]:
            column = ModelProjectorColumn(
                name="test_col",
                type=col_type,
                source="event.payload.value",
            )
            assert column.type == col_type

    def test_name_is_required(self) -> None:
        """Name field is required."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorColumn(type="TEXT", source="event.payload.x")  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_type_is_required(self) -> None:
        """Type field is required."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorColumn(name="col", source="event.payload.x")  # type: ignore[call-arg]

        assert "type" in str(exc_info.value)

    def test_source_is_required(self) -> None:
        """Source field is required."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorColumn(name="col", type="TEXT")  # type: ignore[call-arg]

        assert "source" in str(exc_info.value)


@pytest.mark.unit
class TestModelProjectorColumnSourcePath:
    """Tests for source path format."""

    def test_valid_event_payload_path(self) -> None:
        """Valid event.payload.* source path."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        assert column.source == "event.payload.node_id"

    def test_valid_nested_path(self) -> None:
        """Valid nested source path."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="author_name",
            type="TEXT",
            source="event.payload.author.name",
        )

        assert column.source == "event.payload.author.name"

    def test_valid_metadata_path(self) -> None:
        """Valid event metadata source path."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="event_id",
            type="UUID",
            source="event.metadata.event_id",
        )

        assert column.source == "event.metadata.event_id"

    def test_valid_envelope_path(self) -> None:
        """Valid envelope-level source path."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="sequence_number",
            type="INTEGER",
            source="envelope.sequence_number",
        )

        assert column.source == "envelope.sequence_number"


@pytest.mark.unit
class TestModelProjectorColumnImmutability:
    """Tests for frozen/immutable behavior."""

    def test_column_is_frozen(self) -> None:
        """Column should be immutable after creation."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="test",
            type="TEXT",
            source="event.payload.test",
        )

        with pytest.raises(ValidationError):
            column.name = "new_name"  # type: ignore[misc]

    def test_column_is_hashable(self) -> None:
        """Frozen column should be hashable."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="test",
            type="TEXT",
            source="event.payload.test",
        )

        hash_value = hash(column)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelProjectorColumnExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorColumn(
                name="test",
                type="TEXT",
                source="event.payload.test",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelProjectorColumnSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        original = ModelProjectorColumn(
            name="status",
            type="TEXT",
            source="event.payload.status",
            on_event="node.status.changed.v1",
            default="PENDING",
        )
        data = original.model_dump()
        restored = ModelProjectorColumn.model_validate(data)

        assert restored == original

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        original = ModelProjectorColumn(
            name="created_at",
            type="TIMESTAMPTZ",
            source="event.payload.created_at",
        )
        json_str = original.model_dump_json()
        restored = ModelProjectorColumn.model_validate_json(json_str)

        assert restored == original


@pytest.mark.unit
class TestModelProjectorColumnRepr:
    """Tests for __repr__ method of ModelProjectorColumn."""

    def test_repr_basic(self) -> None:
        """Test basic repr output contains class name and key fields."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="status",
            type="TEXT",
            source="event.payload.status",
        )
        result = repr(column)

        assert "ModelProjectorColumn" in result
        assert "status" in result
        assert "TEXT" in result

    def test_repr_with_uuid_type(self) -> None:
        """Test repr with UUID column type."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )
        result = repr(column)

        assert "ModelProjectorColumn" in result
        assert "node_id" in result
        assert "UUID" in result

    def test_repr_with_various_types(self) -> None:
        """Test repr correctly shows different column types."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        for col_type in ["JSONB", "TIMESTAMPTZ", "INTEGER", "BOOLEAN"]:
            column = ModelProjectorColumn(
                name="test_col",
                type=col_type,
                source="event.payload.value",
            )
            result = repr(column)

            assert "ModelProjectorColumn" in result
            assert "test_col" in result
            assert col_type in result

    def test_repr_concise_format(self) -> None:
        """Test repr is concise and doesn't include optional fields."""
        from omnibase_core.models.projectors import ModelProjectorColumn

        column = ModelProjectorColumn(
            name="status",
            type="TEXT",
            source="event.payload.status",
            on_event="node.status.changed.v1",
            default="UNKNOWN",
        )
        result = repr(column)

        # Repr should be concise - showing name and type only
        assert "ModelProjectorColumn" in result
        assert "status" in result
        assert "TEXT" in result
        # These optional fields should NOT be in the concise repr
        assert "source" not in result.lower()
        assert "on_event" not in result.lower()
        assert "default" not in result.lower()
        assert "UNKNOWN" not in result
