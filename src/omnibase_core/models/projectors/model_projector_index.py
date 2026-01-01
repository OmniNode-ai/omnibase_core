"""
Index definition model for projection tables.

This module provides the ModelProjectorIndex class for defining database
indexes on projection tables, supporting btree, gin, and hash index types.

Version: 1.0.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelProjectorIndex",
]


class ModelProjectorIndex(BaseModel):
    """
    Index definition for projection table.

    Defines a database index to be created on a projection table. Supports
    common PostgreSQL index types: btree (default), gin, and hash.

    Core Concepts:
    - **name**: Optional index name. If not provided, the database or
      materialization layer will auto-generate one.
    - **columns**: Required list of columns to index. Must contain at least
      one column name.
    - **type**: Index type - btree (default, B-tree), gin (GIN for arrays/JSONB),
      or hash (hash index).
    - **unique**: Whether to enforce unique constraint on indexed columns.

    Example:
        ```python
        # Simple btree index on user_id
        index = ModelProjectorIndex(columns=["user_id"])

        # Unique composite index with explicit name
        index = ModelProjectorIndex(
            name="idx_user_created",
            columns=["user_id", "created_at"],
            type="btree",
            unique=True,
        )

        # GIN index for JSONB/array column
        index = ModelProjectorIndex(
            columns=["tags"],
            type="gin",
        )
        ```

    ONEX v2.0 Compliance:
    - Suffix-based naming: ModelProjectorIndex
    - Pydantic v2 with ConfigDict
    - Frozen/immutable after creation
    - Extra fields rejected (strict validation)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str | None = Field(
        default=None,
        description="Index name. Auto-generated if not provided.",
    )

    columns: list[str] = Field(
        ...,
        description="Columns to index. Must contain at least one column.",
        min_length=1,
    )

    type: Literal["btree", "gin", "hash"] = Field(
        default="btree",
        description="Index type: btree (default), gin, or hash.",
    )

    unique: bool = Field(
        default=False,
        description="Whether to enforce unique constraint on indexed columns.",
    )

    def __hash__(self) -> int:
        """Return hash value for the index.

        Custom implementation to support hashing with list field.
        Converts columns list to tuple for hashing.
        """
        return hash((self.name, tuple(self.columns), self.type, self.unique))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ModelProjectorIndex(name={self.name!r}, columns={self.columns!r}, "
            f"type={self.type!r}, unique={self.unique})"
        )
