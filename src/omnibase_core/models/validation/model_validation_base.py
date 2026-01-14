"""
Mixin for models that need validation capabilities.

This provides a standard validation container and common validation
methods that can be inherited by any model requiring validation.
"""

from __future__ import annotations

from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.types.typed_dict_validation_base_serialized import (
    TypedDictValidationBaseSerialized,
)

from .model_validation_container import ModelValidationContainer


class ModelValidationBase(BaseModel):
    """
    Mixin for models that need validation capabilities.

    This provides a standard validation container and common validation
    methods that can be inherited by any model requiring validation.
    Implements Core protocols:
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    validation: ModelValidationContainer = Field(
        default_factory=lambda: ModelValidationContainer(),
        description="Validation results container",
    )

    def validate_instance(self) -> bool:
        """Check if model is valid (no validation errors) (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        return self.validation.validate_instance()

    def has_validation_errors(self) -> bool:
        """Check if there are validation errors."""
        return self.validation.has_errors()

    def has_critical_validation_errors(self) -> bool:
        """Check if there are critical validation errors."""
        return self.validation.has_critical_errors()

    def add_validation_error(
        self,
        message: str,
        field: str | None = None,
        error_code: str | None = None,
        critical: bool = False,
    ) -> None:
        """Add a validation error to this model."""
        if critical:
            self.validation.add_critical_error(message, field, error_code)
        else:
            self.validation.add_error(message, field, error_code)

    def add_validation_warning(self, message: str) -> None:
        """Add a validation warning to this model."""
        self.validation.add_warning(message)

    def get_validation_summary(self) -> str:
        """Get validation summary for this model."""
        return self.validation.get_error_summary()

    def validate_model_data(self) -> None:
        """
        Override in subclasses for custom validation logic.

        This method should populate the validation container with
        any errors or warnings found during validation.

        Base implementation performs fundamental model validation checks.
        """
        # Import only what we need to avoid circular imports
        import importlib

        try:
            # Dynamic import to avoid circular import issues
            enum_module = importlib.import_module(
                "omnibase_core.enums.enum_core_error_code",
            )
            # Get error code strings with fallbacks
            validation_error_code = enum_module.EnumCoreErrorCode.VALIDATION_ERROR.value
            internal_error_code = enum_module.EnumCoreErrorCode.INTERNAL_ERROR.value
        except (AttributeError, ImportError):
            # Fallback if enum module not available or attributes missing
            validation_error_code = "VALIDATION_ERROR"
            internal_error_code = "INTERNAL_ERROR"

        try:
            # Validate the validation container exists and is properly configured
            # Note: self.validation is never None due to default_factory, but we validate it's working
            if not hasattr(self.validation, "add_error"):
                # This shouldn't happen with proper ModelValidationContainer, but safety check
                return

            # Validate model fields are accessible and properly typed
            try:
                # Use class-level model_fields to avoid deprecation warning
                model_fields = self.__class__.model_fields
                if not model_fields:
                    self.add_validation_warning(
                        "Model has no defined fields - this may indicate a configuration issue",
                    )
                else:
                    # Check for fields that are required but None
                    for field_name, field_info in model_fields.items():
                        if field_name == "validation":
                            continue  # Skip validation field itself

                        field_value = getattr(self, field_name, None)

                        # Check if required field is None/empty
                        # Note: is_required() is a method in Pydantic v2
                        if (
                            hasattr(field_info, "is_required")
                            and callable(field_info.is_required)
                            and field_info.is_required()
                            and field_value is None
                        ):
                            self.add_validation_error(
                                message=f"Required field '{field_name}' is None or missing",
                                field=field_name,
                                error_code=validation_error_code,
                            )
            except PYDANTIC_MODEL_ERRORS as field_error:
                self.add_validation_error(
                    message=f"Failed to access model fields: {field_error!s}",
                    field="model_structure",
                    error_code=internal_error_code,
                )

            # Validate that model can be serialized (basic integrity check)
            try:
                model_dict = self.model_dump(exclude={"validation"})
                # Note: model_dump() always returns dict[str, Any], so no need to check isinstance
                # This is just to ensure the serialization process works
                if not model_dict:
                    self.add_validation_error(
                        message="Model serialization succeeded but returned empty dictionary",
                        field="model_integrity",
                        error_code=validation_error_code,
                    )
            except (
                Exception
            ) as serialize_error:  # fallback-ok: serialization can raise any exception
                self.add_validation_error(
                    message=f"Model serialization failed: {serialize_error!s}",
                    field="model_integrity",
                    error_code=validation_error_code,
                )

            # Check for circular references in model structure
            try:
                # Attempt to convert to JSON to detect circular references
                import json

                json.dumps(self.model_dump(exclude={"validation"}), default=str)
            except (
                Exception
            ) as json_error:  # fallback-ok: model_dump/json can raise any exception
                if "circular reference" in str(json_error).lower() or isinstance(
                    json_error,
                    RecursionError,
                ):
                    self.add_validation_error(
                        message="Model contains circular references that prevent serialization",
                        field="model_structure",
                        error_code=validation_error_code,
                        critical=True,
                    )
                else:
                    self.add_validation_warning(
                        f"Model may have serialization issues: {json_error!s}",
                    )

        except (
            AttributeError,
            TypeError,
            ValueError,
            RuntimeError,
        ) as unexpected_error:
            # For base validation, we'll add the error to the validation container
            # rather than raising ONEX errors to avoid circular import issues
            self.add_validation_error(
                message=f"Unexpected error during model validation: {unexpected_error!s}",
                field="validation_system",
                error_code=(
                    validation_error_code
                    if "validation_error_code" in locals()
                    else "VALIDATION_ERROR"
                ),
                critical=True,
            )

    def perform_validation(self) -> bool:
        """
        Perform validation and return success status.

        This calls validate_model_data() and returns True if no errors.
        """
        # Clear previous validation results
        self.validation.clear_all()

        # Run custom validation
        self.validate_model_data()

        # Return success status
        return self.validate_instance()

    # Protocol method implementations

    def serialize(self) -> TypedDictValidationBaseSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return cast(
            TypedDictValidationBaseSerialized,
            self.model_dump(exclude_none=False, by_alias=True),
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelValidationBase"]
