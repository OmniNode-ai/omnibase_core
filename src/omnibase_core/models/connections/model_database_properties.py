"""
Database connection properties sub-model.

Part of the connection properties restructuring to reduce string field violations.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ModelDatabaseProperties(BaseModel):
    """Database-specific connection properties."""

    # Entity references with UUID + display name pattern
    database_id: UUID | None = Field(
        default=None,
        description="Database UUID reference",
    )
    database_display_name: str | None = Field(
        default=None,
        description="Database display name",
    )
    schema_id: UUID | None = Field(default=None, description="Schema UUID reference")
    schema_display_name: str | None = Field(
        default=None,
        description="Schema display name",
    )

    # Database configuration (non-string)
    charset: str | None = Field(default=None, description="Character set")
    collation: str | None = Field(default=None, description="Collation")

    def get_database_identifier(self) -> str | None:
        """Get database identifier for display purposes."""
        if self.database_display_name:
            return self.database_display_name
        if self.database_id:
            return str(self.database_id)
        return None

    def get_schema_identifier(self) -> str | None:
        """Get schema identifier for display purposes."""
        if self.schema_display_name:
            return self.schema_display_name
        if self.schema_id:
            return str(self.schema_id)
        return None


# Export the model
__all__ = ["ModelDatabaseProperties"]
