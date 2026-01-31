"""Safety policy for database operations.

Defines opt-in flags for potentially dangerous operations.
All default to False (safe by default).
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelDbSafetyPolicy(BaseModel):
    """Safety policy for database operations.

    Opt-in flags for potentially dangerous operations.
    All default to False (safe by default).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    allow_delete_without_where: bool = Field(
        default=False,
        description="Allow DELETE statements without WHERE clause",
    )
    allow_update_without_where: bool = Field(
        default=False,
        description="Allow UPDATE statements without WHERE clause",
    )
    allow_multi_statement: bool = Field(
        default=False,
        description="Allow multiple SQL statements (semicolon-separated)",
    )


__all__ = ["ModelDbSafetyPolicy"]
