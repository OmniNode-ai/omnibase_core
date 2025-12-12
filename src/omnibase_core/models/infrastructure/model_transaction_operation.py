"""
Transaction Operation Model.

Strongly-typed model for transaction operations, replacing dict[str, Any]
patterns in ModelEffectTransaction and ModelTransaction.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelTransactionOperationData(BaseModel):
    """
    Typed model for transaction operation data.

    Replaces dict[str, Any] operation_data parameter with structured fields.
    Provides flexible storage while maintaining type safety.
    """

    # Core operation data using ModelSchemaValue for type safety
    properties: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Operation properties as typed schema values",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ModelTransactionOperationData:
        """Create from a plain dictionary, converting values to ModelSchemaValue."""
        properties = {
            key: ModelSchemaValue.from_value(value) for key, value in data.items()
        }
        return cls(properties=properties)

    def to_dict(self) -> dict[str, object]:
        """Convert back to plain dictionary."""
        return {key: value.to_value() for key, value in self.properties.items()}

    def get(self, key: str, default: object = None) -> object:
        """Get a value by key, returning default if not found."""
        schema_value = self.properties.get(key)
        if schema_value is None:
            return default
        return schema_value.to_value()

    def set(self, key: str, value: object) -> None:
        """Set a value by key."""
        self.properties[key] = ModelSchemaValue.from_value(value)


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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

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


__all__ = ["ModelTransactionOperation", "ModelTransactionOperationData"]
