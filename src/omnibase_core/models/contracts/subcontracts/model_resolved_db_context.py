"""
Resolved Database Context Model for NodeEffect Handler Contract.

This model represents a resolved (template-free) database context that handlers receive
after template resolution by the effect executor.

Thread Safety:
    This model is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

See Also:
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


class ModelResolvedDbContext(BaseModel):
    """
    Resolved database context for SQL operations.

    All template placeholders have been resolved by the effect executor.
    Query parameters are resolved to actual values ready for execution.

    Attributes:
        handler_type: Discriminator field for database handler type.
        operation: Database operation type (select, insert, update, delete, upsert, raw).
        connection_name: Name of the database connection to use.
        query: Fully resolved SQL query (no template placeholders).
        params: Resolved query parameter values in order.
        timeout_ms: Query timeout in milliseconds (1s - 10min).
        fetch_size: Number of rows to fetch per batch (None for default).
        read_only: Whether the operation is read-only (enables optimizations).

    Example resolved values:
        - query: "SELECT * FROM users WHERE id = $1" (was: "${QUERY_TEMPLATE}")
        - params: [123] (was: ["${user_id}"])
    """

    handler_type: Literal[EnumEffectHandlerType.DB] = Field(
        default=EnumEffectHandlerType.DB,
        description="Handler type discriminator for database operations",
    )

    operation: Literal["select", "insert", "update", "delete", "upsert", "raw"] = Field(
        ...,
        description="Database operation type",
    )

    connection_name: str = Field(
        ...,
        min_length=1,
        description="Name of the database connection to use",
    )

    query: str = Field(
        ...,
        min_length=1,
        description="Fully resolved SQL query (no template placeholders)",
    )

    params: list[str | int | float | bool | None] = Field(
        default_factory=list,
        description="Resolved query parameter values in order",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Query timeout in milliseconds (1s - 10min)",
    )

    fetch_size: int | None = Field(
        default=None,
        ge=1,
        description="Number of rows to fetch per batch (None for default)",
    )

    read_only: bool = Field(
        default=False,
        description="Whether the operation is read-only (enables optimizations)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )
