"""
Validation Subcontract Model.



Dedicated subcontract model for validation functionality providing:
- Fail-fast validation control
- Type checking strictness configuration
- Range and pattern validation settings
- Custom validator enablement
- Error collection and timeout management

This model is composed into node contracts that require validation functionality,
providing clean separation between node logic and validation behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelValidationSubcontract(BaseModel):
    """
    Validation subcontract model for validation functionality.

    Comprehensive validation subcontract providing validation strategies,
    type checking strictness, range and pattern validation controls,
    and error management. Designed for composition into node contracts
    requiring validation functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core validation behavior
    enable_fail_fast: bool = Field(
        default=True,
        description="Stop validation on first error",
    )

    strict_type_checking: bool = Field(
        default=True,
        description="Enforce strict type checking",
    )

    enable_range_validation: bool = Field(
        default=True,
        description="Validate numeric ranges",
    )

    enable_pattern_validation: bool = Field(
        default=True,
        description="Validate string patterns",
    )

    enable_custom_validators: bool = Field(
        default=True,
        description="Enable custom field validators",
    )

    # Error collection and management
    max_validation_errors: int = Field(
        default=100,
        description="Max errors to collect before stopping",
        ge=1,
        le=1000,
    )

    validation_timeout_seconds: float = Field(
        default=5.0,
        description="Validation timeout in seconds",
        ge=0.1,
        le=60.0,
    )

    @model_validator(mode="after")
    def validate_timeout(self) -> "ModelValidationSubcontract":
        """Validate timeout is positive and reasonable."""
        if self.validation_timeout_seconds <= 0:
            msg = "validation_timeout_seconds must be positive"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "validation_timeout_seconds",
                        ),
                        "value": ModelSchemaValue.from_value(
                            str(self.validation_timeout_seconds),
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_max_errors(self) -> "ModelValidationSubcontract":
        """Validate max_validation_errors is reasonable."""
        if self.max_validation_errors < 1:
            msg = "max_validation_errors must be at least 1"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("max_validation_errors"),
                        "value": ModelSchemaValue.from_value(
                            str(self.max_validation_errors),
                        ),
                    },
                ),
            )
        if self.max_validation_errors > 10000:
            msg = "max_validation_errors cannot exceed 10000 for performance"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("max_validation_errors"),
                        "value": ModelSchemaValue.from_value(
                            str(self.max_validation_errors),
                        ),
                    },
                ),
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Validate on assignment after creation
    )
