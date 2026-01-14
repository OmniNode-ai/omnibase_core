"""
Regex Flags Model.

Discriminated union for regex flags to replace Union[re.DOTALL, re.IGNORECASE, re.MULTILINE]
patterns commonly used in validation scripts and text processing.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_regex_flag_type import EnumRegexFlagType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelRegexFlags(BaseModel):
    """
    Discriminated union for regex flags.

    Replaces Union[re.DOTALL, re.IGNORECASE, re.MULTILINE] with structured flag handling.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    flag_type: EnumRegexFlagType = Field(
        description="Type discriminator for regex flag",
    )

    # Flag value storage
    flag_value: int = Field(description="The actual regex flag value")

    @model_validator(mode="after")
    def validate_flag_value(self) -> ModelRegexFlags:
        """Ensure flag value matches the declared type."""
        expected_values = {
            EnumRegexFlagType.DOTALL: re.DOTALL,
            EnumRegexFlagType.IGNORECASE: re.IGNORECASE,
            EnumRegexFlagType.MULTILINE: re.MULTILINE,
        }

        if self.flag_type in expected_values:
            if self.flag_value != expected_values[self.flag_type]:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Flag value {self.flag_value} doesn't match type {self.flag_type}",
                )
        elif self.flag_type == EnumRegexFlagType.COMBINED:
            # For combined flags, just ensure it's a valid positive integer
            if not isinstance(self.flag_value, int) or self.flag_value <= 0:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Invalid combined flag value: {self.flag_value}",
                )

        return self

    @classmethod
    def dotall(cls) -> ModelRegexFlags:
        """Create DOTALL flag."""
        return cls(flag_type=EnumRegexFlagType.DOTALL, flag_value=re.DOTALL)

    @classmethod
    def ignorecase(cls) -> ModelRegexFlags:
        """Create IGNORECASE flag."""
        return cls(flag_type=EnumRegexFlagType.IGNORECASE, flag_value=re.IGNORECASE)

    @classmethod
    def multiline(cls) -> ModelRegexFlags:
        """Create MULTILINE flag."""
        return cls(flag_type=EnumRegexFlagType.MULTILINE, flag_value=re.MULTILINE)

    @classmethod
    def combined(cls, *flags: int) -> ModelRegexFlags:
        """Create combined flag from multiple flags."""
        combined_value = 0
        for flag in flags:
            combined_value |= flag
        return cls(flag_type=EnumRegexFlagType.COMBINED, flag_value=combined_value)

    @classmethod
    def dotall_ignorecase_multiline(cls) -> ModelRegexFlags:
        """Create common combination of DOTALL | IGNORECASE | MULTILINE."""
        return cls.combined(re.DOTALL, re.IGNORECASE, re.MULTILINE)

    @classmethod
    def ignorecase_multiline(cls) -> ModelRegexFlags:
        """Create common combination of IGNORECASE | MULTILINE."""
        return cls.combined(re.IGNORECASE, re.MULTILINE)

    @classmethod
    def dotall_multiline(cls) -> ModelRegexFlags:
        """Create common combination of DOTALL | MULTILINE."""
        return cls.combined(re.DOTALL, re.MULTILINE)

    def get_flag(self) -> int:
        """Get the actual regex flag value."""
        return self.flag_value

    def as_int(self) -> int:
        """Get flag as integer."""
        return self.flag_value

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelRegexFlags"]
