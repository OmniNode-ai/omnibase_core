# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Database operation definition for repository contracts.

Defines a named operation with:
- Read/write mode
- SQL template with named parameters (:param) or positional ($N with param_order)
- Parameter definitions
- Return type specification
- Safety policy overrides
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.contracts.model_db_param import ModelDbParam
from omnibase_core.models.contracts.model_db_return import ModelDbReturn
from omnibase_core.models.contracts.model_db_safety_policy import ModelDbSafetyPolicy


class ModelDbOperation(BaseModel):
    """Single database operation definition.

    Defines a named operation with:
    - Read/write mode
    - SQL template with named parameters (:param) or positional ($N with param_order)
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
        description="SQL template with named parameters (:param_name) or positional ($1, $2)",
    )

    # Parameters
    params: dict[str, ModelDbParam] = Field(
        default_factory=dict,
        description="Parameter definitions keyed by name",
    )

    # Positional parameter ordering (required when using $N placeholders)
    param_order: tuple[str, ...] | None = Field(
        default=None,
        description=(
            "Maps positional indices to param names. Required when SQL uses $1, $2, etc. "
            "Index 0 maps to $1, index 1 maps to $2, etc. All names must exist in params."
        ),
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

    @model_validator(mode="after")
    def _validate_param_order_references(self) -> "ModelDbOperation":
        """Ensure param_order entries reference valid param names."""
        if self.param_order is None:
            return self

        invalid_refs = [name for name in self.param_order if name not in self.params]
        if invalid_refs:
            msg = (
                f"param_order contains names not found in params: {invalid_refs}. "
                f"Valid param names: {list(self.params.keys())}"
            )
            raise ValueError(msg)

        return self


__all__ = ["ModelDbOperation"]
