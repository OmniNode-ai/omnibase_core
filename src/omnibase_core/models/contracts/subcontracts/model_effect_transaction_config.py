"""
Effect Transaction Model.

Transaction boundary configuration for effect operations.
Only applicable to DB operations with the same connection.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import (
    TIMEOUT_DEFAULT_MS,
    TIMEOUT_LONG_MS,
    TIMEOUT_MIN_MS,
)

__all__ = ["ModelEffectTransactionConfig"]


class ModelEffectTransactionConfig(BaseModel):
    """
    Transaction boundary configuration for effect operations.

    Defines database transaction settings including isolation level, rollback
    behavior, and timeout. Transactions are ONLY supported for DB operations
    using the same connection_name - HTTP, Kafka, and Filesystem operations
    do not support transactions.

    Note:
        This model stores configuration only. It does NOT validate constraints
        like "all operations must be DB type" - that validation happens in
        ModelEffectSubcontract.validate_transaction_scope() when the full
        subcontract is available. Setting enabled=True here is always valid;
        the constraint validation occurs at the subcontract level.

    Isolation Levels:
        - read_uncommitted: Lowest isolation, allows dirty reads. Rarely used.
        - read_committed: Default. Each query sees only committed data at query time.
        - repeatable_read: Snapshot at transaction start. No phantom reads.
        - serializable: Highest isolation. Transactions execute as if sequential.

    Important Constraints (enforced by ModelEffectSubcontract validators):
        - Transaction can only be enabled when ALL operations are DB type
        - All DB operations must use the same connection_name
        - SELECT with retry is forbidden in repeatable_read/serializable isolation
        - Raw DB operations are forbidden in transactions

    Attributes:
        enabled: Whether to wrap operations in a transaction. Defaults to False,
            requiring explicit opt-in to ensure intentional transaction usage.
        isolation_level: PostgreSQL isolation level for the transaction.
            Default: "read_committed".
        rollback_on_error: Whether to rollback on any operation failure.
            Defaults to True for atomic semantics.
        timeout_ms: Transaction timeout in milliseconds (TIMEOUT_MIN_MS-TIMEOUT_LONG_MS).
            Default: TIMEOUT_DEFAULT_MS (30 seconds).
            See omnibase_core.constants for timeout constant values.

    Example:
        >>> from omnibase_core.constants import TIMEOUT_DEFAULT_MS
        >>> transaction = ModelEffectTransactionConfig(
        ...     enabled=True,
        ...     isolation_level="read_committed",
        ...     rollback_on_error=True,
        ...     timeout_ms=TIMEOUT_DEFAULT_MS,
        ... )

    See Also:
        - ModelEffectSubcontract.validate_transaction_scope: Validates DB-only constraint
        - ModelEffectSubcontract.validate_select_retry_in_transaction: Snapshot safety
        - ModelEffectSubcontract.validate_no_raw_in_transaction: Raw operation constraint
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(default=False)  # Default false - must explicitly enable
    isolation_level: Literal[
        "read_uncommitted", "read_committed", "repeatable_read", "serializable"
    ] = Field(default="read_committed")
    rollback_on_error: bool = Field(default=True)
    timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS, ge=TIMEOUT_MIN_MS, le=TIMEOUT_LONG_MS
    )
