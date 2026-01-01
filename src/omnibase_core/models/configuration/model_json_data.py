"""
ONEX-Compliant JSON Data Model for Configuration System

Phase 3I remediation: Eliminated factory methods and conversion anti-patterns.
Strong typing with generic container patterns following ONEX standards.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_json_value_type import EnumJsonValueType
from omnibase_core.models.configuration.model_json_field import ModelJsonField
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelJsonData(BaseModel):
    """
    ONEX-compatible strongly typed JSON data model.

    Provides structured JSON data handling with proper constructor patterns
    and immutable design following ONEX standards.
    """

    fields: dict[str, ModelJsonField] = Field(
        default_factory=dict,
        description="Strongly typed JSON fields with ONEX compliance",
    )

    # Optional metadata for validation and context
    schema_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="JSON data schema version",
    )

    total_field_count: int = Field(
        default=0,
        description="Total number of fields for validation",
        ge=0,
    )

    # ONEX validation constraints
    @field_validator("fields")
    @classmethod
    def validate_field_consistency(
        cls, v: dict[str, ModelJsonField], info: ValidationInfo
    ) -> dict[str, ModelJsonField]:
        """Ensure field count matches actual fields."""
        total_field_count = info.data.get("total_field_count", 0)
        if len(v) != total_field_count:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Field count mismatch: expected {total_field_count}, got {len(v)}",
            )
        return v

    @field_validator("total_field_count", mode="before")
    @classmethod
    def calculate_field_count(cls, v: object, info: ValidationInfo) -> int:
        """Auto-calculate field count for validation."""
        fields = info.data.get("fields", {})
        if isinstance(fields, dict):
            return len(fields)
        # v is int or int-like when not calculating from fields
        if isinstance(v, int):
            return v
        if v is None:
            return 0
        # Handle string representation of int
        if isinstance(v, str) and v.isdigit():
            return int(v)
        # Raise error for unexpected types instead of silently returning 0
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"total_field_count must be int, str (digit), or None, got {type(v).__name__}",
        )

    def get_field_value(self, field_name: str) -> str | float | bool | list[str] | None:
        """ONEX-compatible field value accessor."""
        if field_name not in self.fields:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                message=f"Field '{field_name}' not found",
            )
        return self.fields[field_name].get_typed_value()

    def has_field(self, field_name: str) -> bool:
        """Check if field exists in the JSON data."""
        return field_name in self.fields

    def get_field_type(self, field_name: str) -> EnumJsonValueType:
        """Get the type of a specific field."""
        if field_name not in self.fields:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                message=f"Field '{field_name}' not found",
            )
        return self.fields[field_name].field_type
