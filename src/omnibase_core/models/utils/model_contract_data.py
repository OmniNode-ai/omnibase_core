"""Contract Data Model.

Discriminated union for contract data to replace Union patterns.
"""

from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_contract_data_type import EnumContractDataType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelContractData(BaseModel):
    """
    Discriminated union for contract data to replace Union patterns.

    Replaces Union[dict[str, ModelSchemaValue], dict[str, object], None] with
    ONEX-compliant discriminated union pattern.
    """

    data_type: EnumContractDataType = Field(
        description="Contract data type discriminator",
    )

    # Data storage fields (only one should be populated based on data_type)
    schema_values: dict[str, ModelSchemaValue] | None = None
    raw_values: dict[str, object] | None = None

    @classmethod
    def from_schema_values(
        cls,
        values: dict[str, ModelSchemaValue],
    ) -> "ModelContractData":
        """Create contract data from schema values."""
        return cls(data_type=EnumContractDataType.SCHEMA_VALUES, schema_values=values)

    @classmethod
    def from_raw_values(cls, values: dict[str, object]) -> "ModelContractData":
        """Create contract data from raw values."""
        return cls(data_type=EnumContractDataType.RAW_VALUES, raw_values=values)

    @classmethod
    def from_none(cls) -> "ModelContractData":
        """Create empty contract data."""
        return cls(data_type=EnumContractDataType.NONE)

    @classmethod
    def from_any(
        cls,
        data: dict[str, ModelSchemaValue] | dict[str, object] | None,
    ) -> "ModelContractData":
        """Create contract data from any supported type with automatic detection."""
        if data is None:
            return cls.from_none()

        # After None check, data is guaranteed to be a dict[str, Any]by type signature
        # Check if dict[str, Any]contains ModelSchemaValue instances
        if data and isinstance(next(iter(data.values())), ModelSchemaValue):
            # Type narrowing: data is now dict[str, ModelSchemaValue]
            schema_data = cast(dict[str, ModelSchemaValue], data)
            return cls.from_schema_values(schema_data)

        # Otherwise treat as dict[str, object]
        raw_data = cast(dict[str, object], data)
        return cls.from_raw_values(raw_data)

    def to_schema_values(self) -> dict[str, ModelSchemaValue] | None:
        """Convert to schema values format."""
        if self.data_type == EnumContractDataType.SCHEMA_VALUES:
            return self.schema_values
        if self.data_type == EnumContractDataType.RAW_VALUES and self.raw_values:
            return {
                k: ModelSchemaValue.from_value(v) for k, v in self.raw_values.items()
            }
        if self.data_type == EnumContractDataType.NONE:
            return None
        return None

    def is_empty(self) -> bool:
        """Check if contract data is empty."""
        return self.data_type == EnumContractDataType.NONE
