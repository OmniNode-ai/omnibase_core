# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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

    primary_key: str = Field(
        ...,
        description="Column name to use as the primary key",
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
        """Validate that primary_key refers to an existing column.

        Raises:
            ValueError: If primary_key does not match any column name.
        """
        column_names = {col.name for col in self.columns}
        if self.primary_key not in column_names:
            raise ValueError(
                f"primary_key '{self.primary_key}' must reference an existing column. "
                f"Available columns: {sorted(column_names)}"
            )
        return self

    def __hash__(self) -> int:
        """Return hash value for the schema.

        Custom implementation to support hashing with list fields.
        Converts columns and indexes lists to tuples for hashing.
        """
        return hash(
            (
                self.table,
                self.primary_key,
                tuple(self.columns),
                tuple(self.indexes),
                self.version,
            )
        )

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing table name and column count.

        Examples:
            >>> schema = ModelProjectorSchema(
            ...     table="nodes",
            ...     primary_key="node_id",
            ...     columns=[...],
            ... )
            >>> repr(schema)
            "ModelProjectorSchema(table='nodes', columns=1)"
        """
        return (
            f"ModelProjectorSchema(table={self.table!r}, columns={len(self.columns)})"
        )


__all__ = ["ModelProjectorSchema"]
