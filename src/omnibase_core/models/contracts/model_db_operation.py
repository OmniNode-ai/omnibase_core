"""Database operation definition for repository contracts.

Defines a named operation with:
- Read/write mode
- SQL template with named parameters (:param)
- Parameter definitions
- Return type specification
- Safety policy overrides
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_db_param import ModelDbParam
from omnibase_core.models.contracts.model_db_return import ModelDbReturn
from omnibase_core.models.contracts.model_db_safety_policy import ModelDbSafetyPolicy


class ModelDbOperation(BaseModel):
    """Single database operation definition.

    Defines a named operation with:
    - Read/write mode
    - SQL template with named parameters (:param)
    - Parameter definitions
    - Return type specification
    - Safety policy overrides
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Operation mode
    mode: Literal["read", "write"] = Field(
        ...,
        description="Operation mode: read (SELECT) or write (INSERT/UPDATE/DELETE)",
    )

    # SQL template
    sql: str = Field(
        ...,
        min_length=1,
        description="SQL template with named parameters (:param_name)",
    )

    # Parameters
    params: dict[str, ModelDbParam] = Field(
        default_factory=dict,
        description="Parameter definitions keyed by name",
    )

    # Return type
    returns: ModelDbReturn = Field(
        ...,
        description="Return type definition",
    )

    # Safety policy (opt-in dangerous operations)
    safety_policy: ModelDbSafetyPolicy = Field(
        default_factory=ModelDbSafetyPolicy,
        description="Safety policy overrides",
    )

    # Documentation
    description: str | None = Field(default=None, max_length=1000)


__all__ = ["ModelDbOperation"]
