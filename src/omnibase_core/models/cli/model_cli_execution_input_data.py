"""
CLI Execution Input Data Model.

Represents input data for CLI execution with proper validation.
Replaces dict[str, Any] for input data with structured typing.
"""

from __future__ import annotations

from pathlib import Path

# Removed Any import - using object for ONEX compliance
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_cli_input_value_type import EnumCliInputValueType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.exceptions.onex_error import OnexError

# Input data values use discriminated union pattern with runtime validation


class ModelCliExecutionInputData(BaseModel):
    """
    Structured input data for CLI execution.

    Replaces dict[str, Any] for input_data to provide
    type safety and validation for execution inputs.
    Uses discriminated union pattern for strong typing.
    """

    # Data identification
    key: str = Field(..., description="Input data key identifier")
    value_type: EnumCliInputValueType = Field(
        ...,
        description="Type discriminator for the input value",
    )
    value: object = Field(
        ...,
        description="Input data value - validated against value_type discriminator",
    )

    # Data metadata
    data_type: EnumDataType = Field(..., description="Type of input data")
    is_sensitive: bool = Field(default=False, description="Whether data is sensitive")
    is_required: bool = Field(default=False, description="Whether data is required")

    # Validation
    description: str = Field(default="", description="Data description")
    validation_pattern: str = Field(
        default="",
        description="Regex pattern for validation",
    )

    @field_validator("value")
    @classmethod
    def validate_value_matches_type(cls, v: object, info: ValidationInfo) -> object:
        """Validate value matches declared value_type."""
        if "value_type" not in info.data:
            return v

        value_type = info.data["value_type"]

        if value_type == EnumCliInputValueType.STRING and not isinstance(v, str):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="String value type must contain str data",
            )
        if value_type == EnumCliInputValueType.INTEGER and not isinstance(v, int):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Integer value type must contain int data",
            )
        if value_type == EnumCliInputValueType.FLOAT and not isinstance(v, float):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Float value type must contain float data",
            )
        if value_type == EnumCliInputValueType.BOOLEAN and not isinstance(v, bool):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean value type must contain bool data",
            )
        if value_type == EnumCliInputValueType.PATH and not isinstance(v, Path):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Path value type must contain Path data",
            )
        if value_type == EnumCliInputValueType.UUID and not isinstance(v, UUID):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="UUID value type must contain UUID data",
            )
        if value_type == EnumCliInputValueType.STRING_LIST and not (
            isinstance(v, list) and all(isinstance(item, str) for item in v)
        ):
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="StringList value type must contain list[str] data",
            )

        return v

    def get_string_value(self) -> str:
        """Get value as string representation."""
        if isinstance(self.value, Path):
            return str(self.value)
        if isinstance(self.value, list):
            return ",".join(str(v) for v in self.value)
        return str(self.value)

    def get_typed_value(self) -> object:
        """Get the properly typed value."""
        return self.value

    def is_path_value(self) -> bool:
        """Check if this is a Path value."""
        return isinstance(self.value, Path)

    def is_uuid_value(self) -> bool:
        """Check if this is a UUID value."""
        return isinstance(self.value, UUID)

    @classmethod
    def from_string(
        cls, key: str, value: str, **kwargs: object
    ) -> ModelCliExecutionInputData:
        """Create input data from string value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.STRING,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )

    @classmethod
    def from_integer(
        cls, key: str, value: int, **kwargs: object
    ) -> ModelCliExecutionInputData:
        """Create input data from integer value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.INTEGER,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )

    @classmethod
    def from_float(
        cls, key: str, value: float, **kwargs: object
    ) -> ModelCliExecutionInputData:
        """Create input data from float value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.FLOAT,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )

    @classmethod
    def from_boolean(
        cls,
        key: str,
        value: bool,
        **kwargs: object,
    ) -> ModelCliExecutionInputData:
        """Create input data from boolean value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.BOOLEAN,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )

    @classmethod
    def from_path(
        cls, key: str, value: Path, **kwargs: object
    ) -> ModelCliExecutionInputData:
        """Create input data from Path value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.PATH,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )

    @classmethod
    def from_uuid(
        cls, key: str, value: UUID, **kwargs: object
    ) -> ModelCliExecutionInputData:
        """Create input data from UUID value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.UUID,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )

    @classmethod
    def from_string_list(
        cls,
        key: str,
        value: list[str],
        **kwargs: object,
    ) -> ModelCliExecutionInputData:
        """Create input data from string list value."""
        # Extract known fields with proper types from kwargs
        data_type = kwargs.get("data_type", EnumDataType.TEXT)
        is_sensitive = kwargs.get("is_sensitive", False)
        is_required = kwargs.get("is_required", False)
        description = kwargs.get("description", "")
        validation_pattern = kwargs.get("validation_pattern", "")

        # Type validation for extracted kwargs
        if not isinstance(data_type, EnumDataType):
            data_type = EnumDataType.TEXT
        if not isinstance(is_sensitive, bool):
            is_sensitive = False
        if not isinstance(is_required, bool):
            is_required = False
        if not isinstance(description, str):
            description = ""
        if not isinstance(validation_pattern, str):
            validation_pattern = ""

        return cls(
            key=key,
            value_type=EnumCliInputValueType.STRING_LIST,
            value=value,
            data_type=data_type,
            is_sensitive=is_sensitive,
            is_required=is_required,
            description=description,
            validation_pattern=validation_pattern,
        )


# Export for use
__all__ = ["ModelCliExecutionInputData"]
