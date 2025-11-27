from pydantic import BaseModel, Field

from .model_log_destination import ModelLogDestination
from .model_log_filter import ModelLogFilter
from .model_log_formatting import ModelLogFormatting


class ModelLogLevel(BaseModel):
    """Extensible log level configuration enabling custom logging levels."""

    level_name: str = Field(
        default=...,
        description="Log level name (e.g., DEBUG, INFO, CUSTOM_TRACE)",
        pattern="^[A-Z][A-Z0-9_]*$",
    )
    numeric_value: int = Field(
        default=...,
        description="Numeric value for comparison and ordering",
        ge=0,
        le=100,
    )
    display_name: str = Field(default=..., description="Human-readable display name")
    color_code: str | None = Field(
        default=None,
        description="Terminal color code for console output",
    )
    output_destinations: list[ModelLogDestination] = Field(
        default_factory=list,
        description="Where to send logs of this level",
    )
    formatting_rules: ModelLogFormatting = Field(
        default_factory=ModelLogFormatting,
        description="How to format logs at this level",
    )
    filters: list[ModelLogFilter] = Field(
        default_factory=list,
        description="Log filters to apply at this level",
    )
    is_error_level: bool = Field(
        default=False,
        description="Whether this represents an error/warning level",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this log level is currently enabled",
    )

    def __lt__(self, other: "ModelLogLevel") -> bool:
        """Enable level comparison for sorting and filtering."""
        return self.numeric_value < other.numeric_value

    def __le__(self, other: "ModelLogLevel") -> bool:
        """Enable level comparison for sorting and filtering."""
        return self.numeric_value <= other.numeric_value

    def __gt__(self, other: "ModelLogLevel") -> bool:
        """Enable level comparison for sorting and filtering."""
        return self.numeric_value > other.numeric_value

    def __ge__(self, other: "ModelLogLevel") -> bool:
        """Enable level comparison for sorting and filtering."""
        return self.numeric_value >= other.numeric_value

    def __eq__(self, other: object) -> bool:
        """Enable level equality comparison."""
        if not isinstance(other, ModelLogLevel):
            return False
        return self.numeric_value == other.numeric_value

    def should_log_message(self, message_level: "ModelLogLevel") -> bool:
        """Check if a message at the given level should be logged."""
        return self.enabled and message_level >= self

    def get_formatted_name(self) -> str:
        """Get formatted name for display."""
        if self.color_code:
            return f"{self.color_code}{self.display_name}\033[0m"
        return self.display_name

    @classmethod
    def create_debug(cls) -> "ModelLogLevel":
        """Factory method for DEBUG level."""
        return cls(
            level_name="DEBUG",
            numeric_value=10,
            display_name="Debug",
            color_code="\033[37m",  # White
            is_error_level=False,
        )

    @classmethod
    def create_info(cls) -> "ModelLogLevel":
        """Factory method for INFO level."""
        return cls(
            level_name="INFO",
            numeric_value=20,
            display_name="Info",
            color_code="\033[32m",  # Green
            is_error_level=False,
        )

    @classmethod
    def create_warning(cls) -> "ModelLogLevel":
        """Factory method for WARNING level."""
        return cls(
            level_name="WARNING",
            numeric_value=30,
            display_name="Warning",
            color_code="\033[33m",  # Yellow
            is_error_level=True,
        )

    @classmethod
    def create_error(cls) -> "ModelLogLevel":
        """Factory method for ERROR level."""
        return cls(
            level_name="ERROR",
            numeric_value=40,
            display_name="Error",
            color_code="\033[31m",  # Red
            is_error_level=True,
        )

    @classmethod
    def create_critical(cls) -> "ModelLogLevel":
        """Factory method for CRITICAL level."""
        return cls(
            level_name="CRITICAL",
            numeric_value=50,
            display_name="Critical",
            color_code="\033[35m",  # Magenta
            is_error_level=True,
        )

    @classmethod
    def create_custom(
        cls,
        name: str,
        numeric_value: int,
        display_name: str,
        is_error: bool = False,
        color: str | None = None,
    ) -> "ModelLogLevel":
        """Factory method for custom log levels."""
        return cls(
            level_name=name.upper(),
            numeric_value=numeric_value,
            display_name=display_name,
            color_code=color,
            is_error_level=is_error,
        )
