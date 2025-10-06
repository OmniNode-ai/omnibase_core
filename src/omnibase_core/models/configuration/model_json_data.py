from typing import Optional, Union

from pydantic import Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer

"""
ONEX-Compliant JSON Data Model for Configuration System

Phase 3I remediation: Eliminated factory methods and conversion anti-patterns.
Strong typing with generic container patterns following ONEX standards.
"""

from typing import Any, Optional, Union

from pydantic import BaseModel, Field, validator

from omnibase_core.enums.enum_json_value_type import EnumJsonValueType
from omnibase_core.models.configuration.model_json_field import ModelJsonField


class ModelJsonData(BaseModel):
    """
    ONEX-compliant strongly typed JSON data model.

    Provides structured JSON data handling with proper constructor patterns
    and immutable design following ONEX standards.
    """

    fields: dict[str, ModelJsonField] = Field(
        default_factory=dict,
        description="Strongly typed JSON fields with ONEX compliance",
    )

    # Optional metadata for validation and context
    schema_version: ModelSemVer = Field(
        default="1.0",
        description="JSON data schema version",
        pattern="^\\d+\\.\\d+$",
    )

    total_field_count: int = Field(
        default=0,
        description="Total number of fields for validation",
        ge=0,
    )

    # ONEX validation constraints
    @validator("fields")
    def validate_field_consistency(cls, v: Any, values: dict[str, Any]) -> Any:
        """Ensure field count matches actual fields."""
        if len(v) != values.get("total_field_count", 0):
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Field count mismatch: expected {values.get('total_field_count', 0)}, got {len(v)}",
            )
        return v

    @validator("total_field_count", pre=True, always=True)
    def calculate_field_count(cls, v: Any, values: dict[str, Any]) -> Any:
        """Auto-calculate field count for validation."""
        fields = values.get("fields", {})
        return len(fields) if isinstance(fields, dict) else v

    def get_field_value(self, field_name: str) -> Any:
        """ONEX-compliant field value accessor."""
        if field_name not in self.fields:
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.ITEM_NOT_REGISTERED,
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
                error_code=ModelCoreErrorCode.ITEM_NOT_REGISTERED,
                message=f"Field '{field_name}' not found",
            )
        return self.fields[field_name].field_type
