# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProjectorSchema.

Tests cover:
1. Valid schema with minimal fields (table, primary_key, columns)
2. Valid schema with all fields (including indexes and version)
3. Required fields validation (table, primary_key, columns)
4. columns must be non-empty list
5. Frozen/immutable behavior
6. Extra fields rejected
7. Serialization roundtrip (dict and JSON)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelProjectorSchemaCreation:
    """Tests for ModelProjectorSchema creation and validation."""

    def test_valid_schema_minimal(self) -> None:
        """Valid schema with only required fields."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        assert schema.table == "node_projections"
        assert schema.primary_key == "node_id"
        assert len(schema.columns) == 1
        assert schema.columns[0].name == "node_id"
        assert schema.indexes == []
        assert schema.version is None

    def test_valid_schema_with_all_fields(self) -> None:
        """Valid schema with all fields specified."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
                on_event="node.status.changed.v1",
                default="UNKNOWN",
            ),
            ModelProjectorColumn(
                name="created_at",
                type="TIMESTAMPTZ",
                source="event.payload.created_at",
            ),
        ]

        indexes = [
            ModelProjectorIndex(columns=["status"]),
            ModelProjectorIndex(
                name="idx_created",
                columns=["created_at"],
                type="btree",
            ),
        ]

        version = ModelSemVer(major=1, minor=0, patch=0)

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            indexes=indexes,
            version=version,
        )

        assert schema.table == "node_projections"
        assert schema.primary_key == "node_id"
        assert len(schema.columns) == 3
        assert len(schema.indexes) == 2
        assert schema.version is not None
        assert schema.version.major == 1
        assert schema.version.minor == 0
        assert schema.version.patch == 0

    def test_valid_schema_multiple_columns(self) -> None:
        """Schema with multiple columns of different types."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(name="id", type="UUID", source="event.payload.id"),
            ModelProjectorColumn(name="name", type="TEXT", source="event.payload.name"),
            ModelProjectorColumn(
                name="data", type="JSONB", source="event.payload.data"
            ),
            ModelProjectorColumn(
                name="count", type="INTEGER", source="event.payload.count"
            ),
            ModelProjectorColumn(
                name="active", type="BOOLEAN", source="event.payload.active"
            ),
        ]

        schema = ModelProjectorSchema(
            table="multi_type_table",
            primary_key="id",
            columns=columns,
        )

        assert len(schema.columns) == 5
        assert schema.columns[0].type == "UUID"
        assert schema.columns[1].type == "TEXT"
        assert schema.columns[2].type == "JSONB"
        assert schema.columns[3].type == "INTEGER"
        assert schema.columns[4].type == "BOOLEAN"


@pytest.mark.unit
class TestModelProjectorSchemaRequiredFields:
    """Tests for required field validation."""

    def test_table_is_required(self) -> None:
        """Table field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(  # type: ignore[call-arg]
                primary_key="node_id",
                columns=[column],
            )

        assert "table" in str(exc_info.value)

    def test_primary_key_is_required(self) -> None:
        """Primary key field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(  # type: ignore[call-arg]
                table="node_projections",
                columns=[column],
            )

        assert "primary_key" in str(exc_info.value)

    def test_columns_is_required(self) -> None:
        """Columns field is required."""
        from omnibase_core.models.projectors import ModelProjectorSchema

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(  # type: ignore[call-arg]
                table="node_projections",
                primary_key="node_id",
            )

        assert "columns" in str(exc_info.value)

    def test_columns_cannot_be_empty(self) -> None:
        """Columns list cannot be empty."""
        from omnibase_core.models.projectors import ModelProjectorSchema

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(
                table="node_projections",
                primary_key="node_id",
                columns=[],
            )

        # Error should indicate list length or empty list issue
        error_str = str(exc_info.value).lower()
        assert "columns" in error_str or "list" in error_str


@pytest.mark.unit
class TestModelProjectorSchemaImmutability:
    """Tests for frozen/immutable behavior."""

    def test_schema_is_frozen(self) -> None:
        """Schema should be immutable after creation."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        with pytest.raises(ValidationError):
            schema.table = "new_table"  # type: ignore[misc]

    def test_schema_primary_key_immutable(self) -> None:
        """Primary key should be immutable after creation."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        with pytest.raises(ValidationError):
            schema.primary_key = "new_key"  # type: ignore[misc]

    def test_schema_is_hashable(self) -> None:
        """Frozen schema should be hashable."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        hash_value = hash(schema)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelProjectorSchemaExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(
                table="node_projections",
                primary_key="node_id",
                columns=[column],
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelProjectorSchemaSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
                on_event="node.status.changed.v1",
                default="PENDING",
            ),
        ]

        indexes = [
            ModelProjectorIndex(columns=["status"]),
        ]

        version = ModelSemVer(major=1, minor=2, patch=3)

        original = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            indexes=indexes,
            version=version,
        )

        data = original.model_dump()
        restored = ModelProjectorSchema.model_validate(data)

        assert restored.table == original.table
        assert restored.primary_key == original.primary_key
        assert len(restored.columns) == len(original.columns)
        assert len(restored.indexes) == len(original.indexes)
        assert restored.version is not None
        assert restored.version.major == 1
        assert restored.version.minor == 2
        assert restored.version.patch == 3

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
        ]

        original = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
        )

        json_str = original.model_dump_json()
        restored = ModelProjectorSchema.model_validate_json(json_str)

        assert restored.table == original.table
        assert restored.primary_key == original.primary_key
        assert len(restored.columns) == len(original.columns)

    def test_to_dict_minimal_schema(self) -> None:
        """Minimal schema serialization produces expected keys."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        data = schema.model_dump()

        assert "table" in data
        assert "primary_key" in data
        assert "columns" in data
        assert "indexes" in data
        assert "version" in data
        assert data["table"] == "node_projections"
        assert data["primary_key"] == "node_id"
        assert data["indexes"] == []
        assert data["version"] is None


@pytest.mark.unit
class TestModelProjectorSchemaWithIndexes:
    """Tests for schema with indexes."""

    def test_schema_with_single_index(self) -> None:
        """Schema with a single index."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
            ),
        ]

        indexes = [
            ModelProjectorIndex(columns=["status"]),
        ]

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            indexes=indexes,
        )

        assert len(schema.indexes) == 1
        assert schema.indexes[0].columns == ["status"]

    def test_schema_with_composite_index(self) -> None:
        """Schema with a composite index on multiple columns."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
            ),
            ModelProjectorColumn(
                name="created_at",
                type="TIMESTAMPTZ",
                source="event.payload.created_at",
            ),
        ]

        indexes = [
            ModelProjectorIndex(
                name="idx_status_created",
                columns=["status", "created_at"],
                unique=True,
            ),
        ]

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            indexes=indexes,
        )

        assert len(schema.indexes) == 1
        assert schema.indexes[0].name == "idx_status_created"
        assert schema.indexes[0].columns == ["status", "created_at"]
        assert schema.indexes[0].unique is True

    def test_schema_with_gin_index(self) -> None:
        """Schema with a GIN index for JSONB column."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="metadata",
                type="JSONB",
                source="event.payload.metadata",
            ),
        ]

        indexes = [
            ModelProjectorIndex(
                columns=["metadata"],
                type="gin",
            ),
        ]

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            indexes=indexes,
        )

        assert len(schema.indexes) == 1
        assert schema.indexes[0].type == "gin"


@pytest.mark.unit
class TestModelProjectorSchemaWithVersion:
    """Tests for schema versioning."""

    def test_schema_with_version(self) -> None:
        """Schema with explicit version."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
        ]

        version = ModelSemVer(major=2, minor=1, patch=0)

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            version=version,
        )

        assert schema.version is not None
        assert schema.version.major == 2
        assert schema.version.minor == 1
        assert schema.version.patch == 0
        assert str(schema.version) == "2.1.0"

    def test_schema_version_from_dict(self) -> None:
        """Schema version can be provided as dict for validation."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
        ]

        # Version as dict (common when deserializing from YAML/JSON)
        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            version={"major": 1, "minor": 0, "patch": 0},  # type: ignore[arg-type]
        )

        assert schema.version is not None
        assert schema.version.major == 1


@pytest.mark.unit
class TestModelProjectorSchemaPrimaryKeyValidation:
    """Tests for primary key validation against columns."""

    def test_primary_key_must_exist_in_columns(self) -> None:
        """Validation fails when primary_key references non-existent column."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(
                table="node_projections",
                primary_key="non_existent_column",
                columns=[column],
            )

        error_str = str(exc_info.value)
        assert "primary_key" in error_str
        assert "non_existent_column" in error_str
        assert "node_id" in error_str

    def test_primary_key_valid_when_in_columns(self) -> None:
        """Validation passes when primary_key matches an existing column."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
            ),
        ]

        # Should not raise - primary_key matches existing column
        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
        )

        assert schema.primary_key == "node_id"
        assert len(schema.columns) == 2

    def test_primary_key_can_reference_any_column(self) -> None:
        """Primary key can reference any column, not just the first one."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="id",
                type="UUID",
                source="event.payload.id",
            ),
            ModelProjectorColumn(
                name="external_ref",
                type="TEXT",
                source="event.payload.external_ref",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
            ),
        ]

        # Using second column as primary key
        schema = ModelProjectorSchema(
            table="refs",
            primary_key="external_ref",
            columns=columns,
        )

        assert schema.primary_key == "external_ref"

    def test_primary_key_validation_error_shows_available_columns(self) -> None:
        """Validation error message lists all available column names."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="alpha",
                type="TEXT",
                source="event.payload.alpha",
            ),
            ModelProjectorColumn(
                name="beta",
                type="TEXT",
                source="event.payload.beta",
            ),
            ModelProjectorColumn(
                name="gamma",
                type="TEXT",
                source="event.payload.gamma",
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorSchema(
                table="test",
                primary_key="delta",
                columns=columns,
            )

        error_str = str(exc_info.value)
        # Error should show available columns sorted
        assert "alpha" in error_str
        assert "beta" in error_str
        assert "gamma" in error_str
