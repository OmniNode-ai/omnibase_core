"""
CLI Command Option Model.

Represents command-line options and flags with proper validation.
Replaces dict[str, Any] for command options with structured typing.
"""

from __future__ import annotations

# Removed Any import - using object for ONEX compliance
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_cli_option_value_type import EnumCliOptionValueType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError


class ModelCliCommandOption(BaseModel):
    """
    Structured command option with discriminated union typing.

    Uses type discriminator pattern to provide type safety
    and validation for CLI command configurations.
    """

    # Option identification - UUID-based entity references
    option_id: UUID = Field(..., description="Unique identifier for the option")
    option_display_name: str | None = Field(
        None,
        description="Human-readable option name (e.g., '--verbose', '-v')",
    )
    value: object = Field(
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
        default=False,
        description="Whether option accepts multiple values",
    )

    # Validation
    description: str = Field(default="", description="Option description")
    valid_choices: list[str] = Field(
        default_factory=list,
        description="Valid choices for option value",
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: object, info: ValidationInfo) -> object:
        """Validate that value matches its declared type."""
        if hasattr(info, "data") and "value_type" in info.data:
            value_type = info.data["value_type"]

            if value_type == EnumCliOptionValueType.STRING and not isinstance(v, str):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"String value type must contain str data, got {type(v)}",
                )
            if value_type == EnumCliOptionValueType.INTEGER and not isinstance(
                v,
                int,
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Integer value type must contain int data, got {type(v)}",
                )
            if value_type == EnumCliOptionValueType.BOOLEAN and not isinstance(
                v,
                bool,
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Boolean value type must contain bool data, got {type(v)}",
                )
            if value_type == EnumCliOptionValueType.FLOAT and not isinstance(
                v,
                (int, float),
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Float value type must contain float data, got {type(v)}",
                )
            if value_type == EnumCliOptionValueType.STRING_LIST and not (
                isinstance(v, list) and all(isinstance(item, str) for item in v)
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"StringList value type must contain list[str] data, got {type(v)}",
                )
            if value_type == EnumCliOptionValueType.UUID and not isinstance(v, UUID):
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

    def get_typed_value(self) -> object:
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
        cls,
        option_id: UUID,
        value: str,
        **kwargs: object,
    ) -> ModelCliCommandOption:
        """Create command option from string value."""
        # Extract known fields with proper types from kwargs
        option_display_name = kwargs.get("option_display_name", None)
        is_flag = kwargs.get("is_flag", False)
        is_required = kwargs.get("is_required", False)
        is_multiple = kwargs.get("is_multiple", False)
        description = kwargs.get("description", "")
        valid_choices = kwargs.get("valid_choices", [])

        # Type validation for extracted kwargs
        if option_display_name is not None and not isinstance(option_display_name, str):
            option_display_name = None
        if not isinstance(is_flag, bool):
            is_flag = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(is_multiple, bool):
            is_multiple = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(valid_choices, list) or not all(
            isinstance(choice, str) for choice in valid_choices
        ):
            valid_choices = []

        return cls(
            option_id=option_id,
            option_display_name=option_display_name,
            value_type=EnumCliOptionValueType.STRING,
            value=value,
            is_flag=is_flag,
            is_required=is_required,
            is_multiple=is_multiple,
            description=description,
            valid_choices=valid_choices,
        )

    @classmethod
    def from_integer(
        cls,
        option_id: UUID,
        value: int,
        **kwargs: object,
    ) -> ModelCliCommandOption:
        """Create command option from integer value."""
        # Extract known fields with proper types from kwargs
        option_display_name = kwargs.get("option_display_name", None)
        is_flag = kwargs.get("is_flag", False)
        is_required = kwargs.get("is_required", False)
        is_multiple = kwargs.get("is_multiple", False)
        description = kwargs.get("description", "")
        valid_choices = kwargs.get("valid_choices", [])

        # Type validation for extracted kwargs
        if option_display_name is not None and not isinstance(option_display_name, str):
            option_display_name = None
        if not isinstance(is_flag, bool):
            is_flag = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(is_multiple, bool):
            is_multiple = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(valid_choices, list) or not all(
            isinstance(choice, str) for choice in valid_choices
        ):
            valid_choices = []

        return cls(
            option_id=option_id,
            option_display_name=option_display_name,
            value_type=EnumCliOptionValueType.INTEGER,
            value=value,
            is_flag=is_flag,
            is_required=is_required,
            is_multiple=is_multiple,
            description=description,
            valid_choices=valid_choices,
        )

    @classmethod
    def from_float(
        cls,
        option_id: UUID,
        value: float,
        **kwargs: object,
    ) -> ModelCliCommandOption:
        """Create command option from float value."""
        # Extract known fields with proper types from kwargs
        option_display_name = kwargs.get("option_display_name", None)
        is_flag = kwargs.get("is_flag", False)
        is_required = kwargs.get("is_required", False)
        is_multiple = kwargs.get("is_multiple", False)
        description = kwargs.get("description", "")
        valid_choices = kwargs.get("valid_choices", [])

        # Type validation for extracted kwargs
        if option_display_name is not None and not isinstance(option_display_name, str):
            option_display_name = None
        if not isinstance(is_flag, bool):
            is_flag = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(is_multiple, bool):
            is_multiple = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(valid_choices, list) or not all(
            isinstance(choice, str) for choice in valid_choices
        ):
            valid_choices = []

        return cls(
            option_id=option_id,
            option_display_name=option_display_name,
            value_type=EnumCliOptionValueType.FLOAT,
            value=value,
            is_flag=is_flag,
            is_required=is_required,
            is_multiple=is_multiple,
            description=description,
            valid_choices=valid_choices,
        )

    @classmethod
    def from_boolean(
        cls,
        option_id: UUID,
        value: bool,
        **kwargs: object,
    ) -> ModelCliCommandOption:
        """Create command option from boolean value."""
        # Extract known fields with proper types from kwargs
        option_display_name = kwargs.get("option_display_name", None)
        is_flag = kwargs.get("is_flag", False)
        is_required = kwargs.get("is_required", False)
        is_multiple = kwargs.get("is_multiple", False)
        description = kwargs.get("description", "")
        valid_choices = kwargs.get("valid_choices", [])

        # Type validation for extracted kwargs
        if option_display_name is not None and not isinstance(option_display_name, str):
            option_display_name = None
        if not isinstance(is_flag, bool):
            is_flag = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(is_multiple, bool):
            is_multiple = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(valid_choices, list) or not all(
            isinstance(choice, str) for choice in valid_choices
        ):
            valid_choices = []

        return cls(
            option_id=option_id,
            option_display_name=option_display_name,
            value_type=EnumCliOptionValueType.BOOLEAN,
            value=value,
            is_flag=is_flag,
            is_required=is_required,
            is_multiple=is_multiple,
            description=description,
            valid_choices=valid_choices,
        )

    @classmethod
    def from_uuid(
        cls, option_id: UUID, value: UUID, **kwargs: object
    ) -> ModelCliCommandOption:
        """Create command option from UUID value."""
        # Extract known fields with proper types from kwargs
        option_display_name = kwargs.get("option_display_name", None)
        is_flag = kwargs.get("is_flag", False)
        is_required = kwargs.get("is_required", False)
        is_multiple = kwargs.get("is_multiple", False)
        description = kwargs.get("description", "")
        valid_choices = kwargs.get("valid_choices", [])

        # Type validation for extracted kwargs
        if option_display_name is not None and not isinstance(option_display_name, str):
            option_display_name = None
        if not isinstance(is_flag, bool):
            is_flag = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(is_multiple, bool):
            is_multiple = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(valid_choices, list) or not all(
            isinstance(choice, str) for choice in valid_choices
        ):
            valid_choices = []

        return cls(
            option_id=option_id,
            option_display_name=option_display_name,
            value_type=EnumCliOptionValueType.UUID,
            value=value,
            is_flag=is_flag,
            is_required=is_required,
            is_multiple=is_multiple,
            description=description,
            valid_choices=valid_choices,
        )

    @classmethod
    def from_string_list(
        cls,
        option_id: UUID,
        value: list[str],
        **kwargs: object,
    ) -> ModelCliCommandOption:
        """Create command option from string list value."""
        # Extract known fields with proper types from kwargs
        option_display_name = kwargs.get("option_display_name", None)
        is_flag = kwargs.get("is_flag", False)
        is_required = kwargs.get("is_required", False)
        is_multiple = kwargs.get("is_multiple", False)
        description = kwargs.get("description", "")
        valid_choices = kwargs.get("valid_choices", [])

        # Type validation for extracted kwargs
        if option_display_name is not None and not isinstance(option_display_name, str):
            option_display_name = None
        if not isinstance(is_flag, bool):
            is_flag = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(is_multiple, bool):
            is_multiple = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(valid_choices, list) or not all(
            isinstance(choice, str) for choice in valid_choices
        ):
            valid_choices = []

        return cls(
            option_id=option_id,
            option_display_name=option_display_name,
            value_type=EnumCliOptionValueType.STRING_LIST,
            value=value,
            is_flag=is_flag,
            is_required=is_required,
            is_multiple=is_multiple,
            description=description,
            valid_choices=valid_choices,
        )


# Export for use
__all__ = ["ModelCliCommandOption"]
