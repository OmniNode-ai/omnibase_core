"""
Effect Transaction Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Transaction boundary configuration for effect operations.
Only applicable to DB operations with the same connection.

Implements: OMN-524
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectTransactionConfig"]


class ModelEffectTransactionConfig(BaseModel):
    """
    Transaction boundary configuration.

    SCOPE: DB operations only, same connection only.
    HTTP, Kafka, and Filesystem do not support transactions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=False)  # Default false - must explicitly enable
    isolation_level: Literal[
        "read_uncommitted", "read_committed", "repeatable_read", "serializable"
    ] = Field(default="read_committed")
    rollback_on_error: bool = Field(default=True)
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
