"""
Projector Schema Model.

Defines the database schema for a projection, including table name, primary key,
columns, indexes, and optional versioning.

This module provides:
    - :class:`ModelProjectorSchema`: Pydantic model for projector schema definition

Schema Components:
    - **table**: The target database table name
    - **primary_key**: The column to use as primary key
    - **columns**: List of column definitions (ModelProjectorColumn)
    - **indexes**: Optional list of index definitions (ModelProjectorIndex)
    - **version**: Optional schema version for migration tracking (ModelSemVer)

Example Usage:
    >>> from omnibase_core.models.projectors import (
    ...     ModelProjectorColumn,
    ...     ModelProjectorIndex,
    ...     ModelProjectorSchema,
    ... )
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> # Define columns
    >>> columns = [
    ...     ModelProjectorColumn(
    ...         name="node_id",
    ...         type="UUID",
    ...         source="event.payload.node_id",
    ...     ),
    ...     ModelProjectorColumn(
    ...         name="status",
    ...         type="TEXT",
    ...         source="event.payload.status",
    ...         default="UNKNOWN",
    ...     ),
    ... ]
    >>>
    >>> # Define indexes
    >>> indexes = [
    ...     ModelProjectorIndex(columns=["status"]),
    ... ]
    >>>
    >>> # Create schema
    >>> schema = ModelProjectorSchema(
    ...     table="node_projections",
    ...     primary_key="node_id",
    ...     columns=columns,
    ...     indexes=indexes,
    ...     version=ModelSemVer(major=1, minor=0, patch=0),
    ... )

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1166 projector contract models.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.projectors.model_projector_column import ModelProjectorColumn
from omnibase_core.models.projectors.model_projector_index import ModelProjectorIndex


class ModelProjectorSchema(BaseModel):
    """Database schema for projection.

    Defines the complete schema for a projection table, including the table name,
    primary key, column definitions, optional indexes, and optional version for
    migration tracking.

    Attributes:
        table: The target database table name. Must be a valid SQL identifier.
        primary_key: The column name to use as the primary key. Must correspond
            to one of the defined columns.
        columns: List of column definitions. Must contain at least one column.
            Each column specifies how event data maps to the projection table.
        indexes: Optional list of index definitions. Defaults to empty list.
            Indexes can improve query performance on frequently accessed columns.
        version: Optional schema version using semantic versioning. Useful for
            tracking schema migrations and compatibility.

    Examples:
        Create a minimal schema:

        >>> from omnibase_core.models.projectors import (
        ...     ModelProjectorColumn,
        ...     ModelProjectorSchema,
        ... )
        >>> column = ModelProjectorColumn(
        ...     name="node_id",
        ...     type="UUID",
        ...     source="event.payload.node_id",
        ... )
        >>> schema = ModelProjectorSchema(
        ...     table="nodes",
        ...     primary_key="node_id",
        ...     columns=[column],
        ... )

        Create a schema with indexes and version:

        >>> from omnibase_core.models.projectors import ModelProjectorIndex
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> schema = ModelProjectorSchema(
        ...     table="nodes",
        ...     primary_key="node_id",
        ...     columns=[
        ...         ModelProjectorColumn(
        ...             name="node_id",
        ...             type="UUID",
        ...             source="event.payload.node_id",
        ...         ),
        ...         ModelProjectorColumn(
        ...             name="status",
        ...             type="TEXT",
        ...             source="event.payload.status",
        ...         ),
        ...     ],
        ...     indexes=[ModelProjectorIndex(columns=["status"])],
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ... )

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. When running tests with pytest-xdist,
        each worker process imports the class independently, creating separate
        class objects. The ``from_attributes=True`` flag enables Pydantic's
        "duck typing" mode, allowing fixtures from one worker to be validated
        in another.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    table: str = Field(
        ...,
        description="Target database table name for the projection",
    )

    primary_key: str | list[str] = Field(
        ...,
        description=(
            "Column name(s) to use as the primary key. Can be a single column name "
            "(str) or a list of column names for composite primary keys."
        ),
    )

    columns: list[ModelProjectorColumn] = Field(
        ...,
        description="List of column definitions. Must contain at least one column.",
        min_length=1,
    )

    indexes: list[ModelProjectorIndex] = Field(
        default_factory=list,
        description=(
            "Optional list of index definitions for the projection table. "
            "Defaults to an empty list if not specified."
        ),
        json_schema_extra={"default": []},
    )

    version: ModelSemVer | None = Field(
        default=None,
        description="Optional schema version for migration tracking",
    )

    @model_validator(mode="after")
    def validate_primary_key_exists_in_columns(self) -> Self:
        """Validate that primary_key refers to existing column(s).

        Supports both single column primary keys (str) and composite
        primary keys (list[str]).

        Raises:
            ValueError: If any primary_key column does not match a column name.
        """
        column_names = {col.name for col in self.columns}
        # Normalize to list for uniform handling
        pk_columns = (
            [self.primary_key]
            if isinstance(self.primary_key, str)
            else self.primary_key
        )
        missing = [col for col in pk_columns if col not in column_names]
        if missing:
            raise ValueError(
                f"primary_key column(s) {missing} must reference existing columns. "
                f"Available columns: {sorted(column_names)}"
            )
        return self

    @model_validator(mode="after")
    def validate_index_columns_exist_in_schema(self) -> Self:
        """Validate that all index columns reference existing schema columns.

        Each index can specify one or more columns. This validator ensures that
        every column referenced by an index actually exists in the schema's
        column definitions.

        Raises:
            ValueError: If any index column does not match an existing column name.
        """
        column_names = {col.name for col in self.columns}
        for index in self.indexes:
            for col_name in index.columns:
                if col_name not in column_names:
                    raise ValueError(
                        f"Index column '{col_name}' must reference an existing column. "
                        f"Available columns: {sorted(column_names)}"
                    )
        return self

    @model_validator(mode="after")
    def validate_no_duplicate_column_names(self) -> Self:
        """Validate that all column names are unique.

        Column names must be unique within a schema to avoid ambiguity in
        SQL queries and data mapping.

        Raises:
            ValueError: If any column name appears more than once.
        """
        column_names = [col.name for col in self.columns]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in column_names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            raise ValueError(
                f"Duplicate column names are not allowed: {sorted(duplicates)}"
            )
        return self

    @model_validator(mode="after")
    def validate_no_duplicate_index_names(self) -> Self:
        """Validate that all explicit index names are unique.

        Index names must be unique within a schema when explicitly provided.
        Indexes without explicit names (name=None) are allowed and do not
        conflict with each other.

        Raises:
            ValueError: If any explicit index name appears more than once.
        """
        # Only check indexes with explicit names (skip None)
        explicit_names = [idx.name for idx in self.indexes if idx.name is not None]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in explicit_names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            raise ValueError(
                f"Duplicate index names are not allowed: {sorted(duplicates)}"
            )
        return self

    def __hash__(self) -> int:
        """Return hash value for the schema.

        Custom implementation to support hashing with list fields.
        Converts columns, indexes, and primary_key lists to tuples for hashing.
        """
        # Normalize primary_key to tuple for hashing
        pk_tuple = (
            (self.primary_key,)
            if isinstance(self.primary_key, str)
            else tuple(self.primary_key)
        )
        return hash(
            (
                self.table,
                pk_tuple,
                tuple(self.columns),
                tuple(self.indexes),
                self.version,
            )
        )

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing table name, column count, index count,
            and version for better debugging visibility.

        Examples:
            >>> schema = ModelProjectorSchema(
            ...     table="nodes",
            ...     primary_key="node_id",
            ...     columns=[...],
            ... )
            >>> repr(schema)
            "ModelProjectorSchema(table='nodes', columns=1, indexes=0, version=None)"

            >>> schema_with_version = ModelProjectorSchema(
            ...     table="nodes",
            ...     primary_key="node_id",
            ...     columns=[...],
            ...     indexes=[...],
            ...     version=ModelSemVer(major=1, minor=0, patch=0),
            ... )
            >>> repr(schema_with_version)
            "ModelProjectorSchema(table='nodes', columns=1, indexes=2, version=1.0.0)"
        """
        version_str = str(self.version) if self.version is not None else "None"
        return (
            f"ModelProjectorSchema(table={self.table!r}, columns={len(self.columns)}, "
            f"indexes={len(self.indexes)}, version={version_str})"
        )


__all__ = ["ModelProjectorSchema"]
