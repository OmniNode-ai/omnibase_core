"""
Transaction Operation Model.

Strongly-typed model for transaction operations, replacing dict[str, Any]
patterns in ModelEffectTransaction and ModelTransaction.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.infrastructure.model_transaction_operation_data import (
    ModelTransactionOperationData,
)


class ModelTransactionOperation(BaseModel):
    """
    Strongly-typed model for a single transaction operation.

    Replaces dict[str, Any] operations in transaction models.
    """

    name: str = Field(
        default=...,
        description="Operation name/identifier",
    )
    data: ModelTransactionOperationData = Field(
        default_factory=ModelTransactionOperationData,
        description="Operation data as typed model",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the operation was recorded",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    @classmethod
    def create(
        cls,
        name: str,
        data: dict[str, object] | ModelTransactionOperationData | None = None,
        timestamp: datetime | None = None,
    ) -> ModelTransactionOperation:
        """Create a transaction operation with optional data."""
        if data is None:
            operation_data = ModelTransactionOperationData()
        elif isinstance(data, dict):
            operation_data = ModelTransactionOperationData.from_dict(data)
        else:
            operation_data = data

        return cls(
            name=name,
            data=operation_data,
            timestamp=timestamp or datetime.now(),
        )


# Re-export from split module
from omnibase_core.models.infrastructure.model_transaction_operation_data import (
    ModelTransactionOperationData,
)

__all__ = ["ModelTransactionOperation", "ModelTransactionOperationData"]
