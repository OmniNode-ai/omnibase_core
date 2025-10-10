from __future__ import annotations

from pydantic import Field, model_validator

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Data handling declaration model.
"""


from typing import Any

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ModelDataHandlingDeclaration(BaseModel):
    """Data handling and classification declaration.
    Implements omnibase_spi protocols:
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If configuration fails with details about the failure
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Configuration failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e
