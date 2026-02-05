"""Database return type definition for repository contracts.

Declares shape tightly enough that:
- Infra can deserialize deterministically
- Domains can bind to a stable interface

Fields:
    model_ref: Fully qualified model class name for return type.
    many: True for list of rows, False for single row.
    fields: Declared projection fields for SQL SELECT validation.
    strict: Enforce projection match (None=auto, True=always, False=lenient).
    allow_select_star: Explicit escape hatch for SELECT * when strict mode is active.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelDbReturn(BaseModel):
    """Database return type definition for repository contracts.

    Declares shape tightly enough that:
    - Infra can deserialize deterministically
    - Domains can bind to a stable interface

    Supports field projection validation to ensure SQL queries return
    the expected columns, catching mismatches at contract validation time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Model reference (fully qualified import path)
    model_ref: str = Field(
        ...,
        min_length=1,
        description="Fully qualified model class name for return type (e.g., 'omnibase_spi.models:ModelPattern')",
    )

    # Cardinality
    many: bool = Field(
        default=False,
        description="True for list of rows, False for single row",
    )

    # Field projection validation (OMN-1790)
    fields: list[str] | None = Field(
        default=None,
        description="Declared projection fields. When present, strict validation is enabled by default.",
    )
    strict: bool | None = Field(
        default=None,
        description="Enforce projection match. None = auto (strict if fields present), True = always strict, False = lenient.",
    )
    allow_select_star: bool = Field(
        default=False,
        description="Explicit escape hatch for SELECT * when strict mode is active. Emits warning even when allowed.",
    )

    @field_validator("fields", mode="after")
    @classmethod
    def validate_fields_unique(cls, v: list[str] | None) -> list[str] | None:
        """Validate that fields list is non-empty and contains unique values.

        Performs both case-sensitive and case-insensitive uniqueness checks
        because SQL column names are case-insensitive in most databases and
        the projection validator uses case-insensitive comparison.
        """
        if v is not None:
            if len(v) == 0:
                raise ValueError("fields list cannot be empty when provided")
            if len(v) != len(set(v)):
                raise ValueError(f"fields must be unique, got duplicates: {v}")
            # Case-insensitive uniqueness (SQL columns are case-insensitive)
            lower_fields = [f.lower() for f in v]
            if len(lower_fields) != len(set(lower_fields)):
                raise ValueError(
                    f"fields must be unique (case-insensitive), got duplicates: {v}"
                )
        return v


__all__ = ["ModelDbReturn"]
