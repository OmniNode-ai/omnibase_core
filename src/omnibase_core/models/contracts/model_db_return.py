"""Database return type definition for repository contracts.

Declares shape tightly enough that:
- Infra can deserialize deterministically
- Domains can bind to a stable interface

v1: Simple model_ref + many. No fields validation (deferred to OMN-1790).
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelDbReturn(BaseModel):
    """Database return type definition for repository contracts.

    Declares shape tightly enough that:
    - Infra can deserialize deterministically
    - Domains can bind to a stable interface

    v1: Simple model_ref + many. No fields validation (deferred to OMN-1790).
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


__all__ = ["ModelDbReturn"]
