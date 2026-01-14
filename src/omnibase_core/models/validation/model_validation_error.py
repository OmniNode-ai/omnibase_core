"""
Validation error model for tracking validation failures.
"""

from __future__ import annotations

import hashlib
from typing import cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import MAX_DESCRIPTION_LENGTH, MAX_NAME_LENGTH
from omnibase_core.enums import EnumSeverity
from omnibase_core.types.typed_dict_validation_error_serialized import (
    TypedDictValidationErrorSerialized,
)

from .model_validation_value import ModelValidationValue


class ModelValidationError(BaseModel):
    """Validation error information.
    Implements Core protocols:
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    message: str = Field(
        default=...,
        description="Error message",
        min_length=1,
        max_length=MAX_DESCRIPTION_LENGTH,
    )
    severity: EnumSeverity = Field(
        default=EnumSeverity.ERROR,
        description="Error severity level",
    )
    field_id: UUID | None = Field(
        default=None,
        description="UUID for field that caused the error",
    )
    field_display_name: str | None = Field(
        default=None,
        description="Human-readable field name that caused the error",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
    )
    error_code: str | None = Field(
        default=None,
        description="Error code for programmatic handling",
        min_length=1,
        max_length=50,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    details: dict[str, ModelValidationValue] | None = Field(
        default=None,
        description="Additional error details",
    )
    line_number: int | None = Field(
        default=None,
        description="Line number where error occurred",
        ge=1,
        le=1000000,
    )
    column_number: int | None = Field(
        default=None,
        description="Column number where error occurred",
        ge=1,
        le=10000,
    )

    def is_critical(self) -> bool:
        """Check if this is a critical error."""
        return bool(self.severity == EnumSeverity.CRITICAL)

    def is_error(self) -> bool:
        """Check if this is an error (error or critical)."""
        return bool(
            self.severity
            in [
                EnumSeverity.ERROR,
                EnumSeverity.CRITICAL,
            ],
        )

    def is_warning(self) -> bool:
        """Check if this is a warning."""
        return bool(self.severity == EnumSeverity.WARNING)

    def is_info(self) -> bool:
        """Check if this is an info message."""
        return bool(self.severity == EnumSeverity.INFO)

    @classmethod
    def create_error(
        cls,
        message: str,
        field_name: str | None = None,
        error_code: str | None = None,
    ) -> ModelValidationError:
        """Create a standard error."""
        field_id = None
        if field_name:
            import hashlib

            field_hash = hashlib.sha256(field_name.encode()).hexdigest()
            field_id = UUID(
                f"{field_hash[:8]}-{field_hash[8:12]}-{field_hash[12:16]}-{field_hash[16:20]}-{field_hash[20:32]}",
            )

        return cls(
            message=message,
            severity=EnumSeverity.ERROR,
            field_id=field_id,
            field_display_name=field_name,
            error_code=error_code,
        )

    @classmethod
    def create_critical(
        cls,
        message: str,
        field_name: str | None = None,
        error_code: str | None = None,
    ) -> ModelValidationError:
        """Create a critical error."""
        field_id = None
        if field_name:
            field_hash = hashlib.sha256(field_name.encode()).hexdigest()
            field_id = UUID(
                f"{field_hash[:8]}-{field_hash[8:12]}-{field_hash[12:16]}-{field_hash[16:20]}-{field_hash[20:32]}",
            )

        return cls(
            message=message,
            severity=EnumSeverity.CRITICAL,
            field_id=field_id,
            field_display_name=field_name,
            error_code=error_code,
        )

    @classmethod
    def create_warning(
        cls,
        message: str,
        field_name: str | None = None,
        error_code: str | None = None,
    ) -> ModelValidationError:
        """Create a warning."""
        field_id = None
        if field_name:
            field_hash = hashlib.sha256(field_name.encode()).hexdigest()
            field_id = UUID(
                f"{field_hash[:8]}-{field_hash[8:12]}-{field_hash[12:16]}-{field_hash[16:20]}-{field_hash[20:32]}",
            )

        return cls(
            message=message,
            severity=EnumSeverity.WARNING,
            field_id=field_id,
            field_display_name=field_name,
            error_code=error_code,
        )

    # from_attributes=True: Required for pytest-xdist parallel execution where
    # model classes may be imported in separate workers with different class identity.
    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True

    def serialize(self) -> TypedDictValidationErrorSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return cast(
            TypedDictValidationErrorSerialized,
            self.model_dump(exclude_none=False, by_alias=True),
        )


# Export for use
__all__ = ["ModelValidationError"]
