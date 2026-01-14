"""
Data handling declaration model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelDataHandlingDeclaration(BaseModel):
    """Data handling and classification declaration.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    processes_sensitive_data: bool = Field(
        default=...,
        description="Whether this component processes sensitive data requiring special handling",
    )
    data_residency_required: str | None = Field(
        default=None,
        description="Required data residency region (e.g., 'EU', 'US', 'GDPR-compliant')",
        min_length=2,
        max_length=50,
        pattern=r"^[A-Z][A-Z0-9_-]*$",
    )
    data_classification: EnumDataClassification | None = Field(
        default=None,
        description="Data classification level following security standards",
    )

    @model_validator(mode="after")
    def validate_data_handling_consistency(self) -> ModelDataHandlingDeclaration:
        """Validate consistency between fields."""
        # If processing sensitive data, should have classification or residency requirements
        if self.processes_sensitive_data:
            if not self.data_classification and not self.data_residency_required:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="When processing sensitive data, either data_classification or "
                    "data_residency_required must be specified",
                )

            # Certain classifications require residency requirements
            if self.data_classification in [
                EnumDataClassification.CONFIDENTIAL,
                EnumDataClassification.RESTRICTED,
            ]:
                if not self.data_residency_required:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Data classification '{self.data_classification}' requires "
                        "data_residency_required to be specified",
                    )

        return self

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Returns True for well-constructed instances. Override in subclasses
        for custom validation logic.
        """
        # Basic validation - Pydantic handles field constraints
        # Override in specific models for custom validation
        return True
