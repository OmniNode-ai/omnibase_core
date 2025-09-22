"""
CLI Command Option Model.

Represents command-line options and flags with proper validation.
Replaces dict[str, Any] for command options with structured typing.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_cli_option_value_type import EnumCliOptionValueType
from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...exceptions.onex_error import OnexError
from ...utils.uuid_utilities import uuid_from_string


class ModelCliCommandOption(BaseModel):
    """
    Structured command option with discriminated union typing.

    Uses type discriminator pattern to provide type safety
    and validation for CLI command configurations.
    """

    # Option identification - UUID-based entity references
    option_id: UUID = Field(..., description="Unique identifier for the option")
    option_display_name: str | None = Field(
        None, description="Human-readable option name (e.g., '--verbose', '-v')"
    )
    value: Any = Field(
        ...,
        description="Option value - validated against value_type discriminator",
    )
    value_type: EnumCliOptionValueType = Field(
        ...,
        description="Type discriminator for the option value",
    )

    # Option metadata
    is_flag: bool = Field(default=False, description="Whether this is a boolean flag")
    is_required: bool = Field(default=False, description="Whether option is required")
    is_multiple: bool = Field(
        default=False, description="Whether option accepts multiple values"
    )

    # Validation
    description: str = Field(default="", description="Option description")
    valid_choices: list[str] = Field(
        default_factory=list, description="Valid choices for option value"
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: Any, info) -> Any:
        """Validate that value matches its declared type."""
        if hasattr(info, "data") and "value_type" in info.data:
            value_type = info.data["value_type"]

            if value_type == EnumCliOptionValueType.STRING and not isinstance(v, str):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"String value type must contain str data, got {type(v)}",
                )
            elif value_type == EnumCliOptionValueType.INTEGER and not isinstance(
                v, int
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Integer value type must contain int data, got {type(v)}",
                )
            elif value_type == EnumCliOptionValueType.BOOLEAN and not isinstance(
                v, bool
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Boolean value type must contain bool data, got {type(v)}",
                )
            elif value_type == EnumCliOptionValueType.FLOAT and not isinstance(
                v, (int, float)
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Float value type must contain float data, got {type(v)}",
                )
            elif value_type == EnumCliOptionValueType.STRING_LIST and not (
                isinstance(v, list) and all(isinstance(item, str) for item in v)
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"StringList value type must contain list[str] data, got {type(v)}",
                )
            elif value_type == EnumCliOptionValueType.UUID and not isinstance(v, UUID):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"UUID value type must contain UUID data, got {type(v)}",
                )

        return v

    def get_string_value(self) -> str:
        """Get value as string representation."""
        if isinstance(self.value, list):
            return ",".join(str(v) for v in self.value)
        return str(self.value)

    def get_typed_value(self) -> Any:
        """Get the properly typed value."""
        return self.value

    def is_boolean_flag(self) -> bool:
        """Check if this is a boolean flag option."""
        return self.is_flag and isinstance(self.value, bool)

    @property
    def option_name(self) -> str:
        """Get option name with fallback to UUID-based name."""
        return self.option_display_name or f"option_{str(self.option_id)[:8]}"

    @classmethod
    def from_string(
        cls, option_id: UUID, value: str, **kwargs
    ) -> ModelCliCommandOption:
        """Create command option from string value."""
        return cls(
            option_id=option_id,
            value_type=EnumCliOptionValueType.STRING,
            value=value,
            **kwargs,
        )

    @classmethod
    def from_integer(
        cls, option_id: UUID, value: int, **kwargs
    ) -> ModelCliCommandOption:
        """Create command option from integer value."""
        return cls(
            option_id=option_id,
            value_type=EnumCliOptionValueType.INTEGER,
            value=value,
            **kwargs,
        )

    @classmethod
    def from_float(
        cls, option_id: UUID, value: float, **kwargs
    ) -> ModelCliCommandOption:
        """Create command option from float value."""
        return cls(
            option_id=option_id,
            value_type=EnumCliOptionValueType.FLOAT,
            value=value,
            **kwargs,
        )

    @classmethod
    def from_boolean(
        cls, option_id: UUID, value: bool, **kwargs
    ) -> ModelCliCommandOption:
        """Create command option from boolean value."""
        return cls(
            option_id=option_id,
            value_type=EnumCliOptionValueType.BOOLEAN,
            value=value,
            **kwargs,
        )

    @classmethod
    def from_uuid(cls, option_id: UUID, value: UUID, **kwargs) -> ModelCliCommandOption:
        """Create command option from UUID value."""
        return cls(
            option_id=option_id,
            value_type=EnumCliOptionValueType.UUID,
            value=value,
            **kwargs,
        )

    @classmethod
    def from_string_list(
        cls, option_id: UUID, value: list[str], **kwargs
    ) -> ModelCliCommandOption:
        """Create command option from string list value."""
        return cls(
            option_id=option_id,
            value_type=EnumCliOptionValueType.STRING_LIST,
            value=value,
            **kwargs,
        )


# Export for use
__all__ = ["ModelCliCommandOption"]
