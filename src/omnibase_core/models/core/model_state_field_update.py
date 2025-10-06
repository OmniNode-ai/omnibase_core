"""
Model State Field Update.

Update for a single state field.
"""

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_state_update_operation import EnumStateUpdateOperation
from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_schema_value import ModelSchemaValue


class ModelStateFieldUpdate(BaseModel):
    """Update for a single state field."""

    field_path: str = Field(
        default=...,
        description="Dot-separated path to the field (e.g., 'user.profile.name')",
    )
    operation: EnumStateUpdateOperation = Field(
        default=...,
        description="Operation to perform on the field",
    )
    value: ModelSchemaValue | None = Field(
        default=None,
        description="Value to use in the operation (not needed for DELETE)",
    )
    condition: str | None = Field(
        default=None,
        description="Optional condition expression that must be true for update to apply",
    )

    @model_validator(mode="after")
    def validate_value_for_operation(self) -> "ModelStateFieldUpdate":
        """Validate that value is appropriate for the operation."""
        if self.operation == EnumStateUpdateOperation.DELETE and self.value is not None:
            msg = "DELETE operation should not have a value"
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        if (
            self.operation
            in [
                EnumStateUpdateOperation.INCREMENT,
                EnumStateUpdateOperation.DECREMENT,
            ]
            and self.value is not None
        ):
            # Check if the value is numeric when converted
            actual_value = self.value.to_value()
            if not isinstance(actual_value, int | float):
                msg = f"{self.operation} operation requires numeric value or None"
                raise ModelOnexError(
                    error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        return self
