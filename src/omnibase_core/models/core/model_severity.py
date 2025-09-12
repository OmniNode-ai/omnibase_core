"""
Severity Model

Unified severity model replacing duplicate EnumErrorSeverity and
EnumValidationSeverity enums with a single structured model.
"""

from typing import ClassVar

from pydantic import BaseModel, Field


class ModelSeverity(BaseModel):
    """
    Unified severity model for errors, validation issues, and logging.

    Consolidates EnumErrorSeverity and EnumValidationSeverity into a
    single model with structured fields.
    """

    # Core fields (required)
    name: str = Field(
        ...,
        description="Severity identifier (DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL)",
        pattern="^[A-Z]+$",
    )

    value: str = Field(..., description="Lowercase value for current standards")

    numeric_value: int = Field(
        ...,
        description="Numeric value for comparison (higher = more severe)",
        ge=0,
        le=100,
    )

    # Properties as fields
    is_blocking: bool = Field(
        ...,
        description="Whether this severity level should block execution",
    )

    is_critical: bool = Field(
        default=False,
        description="Whether this is critical or fatal severity",
    )

    # Optional metadata
    description: str = Field(
        default="",
        description="Human-readable description of the severity level",
    )

    color_code: str = Field(
        default="",
        description="Terminal color code for this severity",
    )

    emoji: str = Field(default="", description="Emoji representation for this severity")

    # Class variable for ordering
    _severity_order: ClassVar[dict[str, int]] = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "FATAL": 60,
    }

    # Factory methods for standard severities
    @classmethod
    def DEBUG(cls) -> "ModelSeverity":
        """Debug severity - lowest level, for development."""
        return cls(
            name="DEBUG",
            value="debug",
            numeric_value=10,
            is_blocking=False,
            is_critical=False,
            description="Debug information for development",
            color_code="\033[36m",  # Cyan
            emoji="🐛",
        )

    @classmethod
    def INFO(cls) -> "ModelSeverity":
        """Info severity - informational messages."""
        return cls(
            name="INFO",
            value="info",
            numeric_value=20,
            is_blocking=False,
            is_critical=False,
            description="Informational messages",
            color_code="\033[34m",  # Blue
            emoji="ℹ️",
        )

    @classmethod
    def WARNING(cls) -> "ModelSeverity":
        """Warning severity - potential issues."""
        return cls(
            name="WARNING",
            value="warning",
            numeric_value=30,
            is_blocking=False,
            is_critical=False,
            description="Warning about potential issues",
            color_code="\033[33m",  # Yellow
            emoji="⚠️",
        )

    @classmethod
    def ERROR(cls) -> "ModelSeverity":
        """Error severity - errors that block normal operation."""
        return cls(
            name="ERROR",
            value="error",
            numeric_value=40,
            is_blocking=True,
            is_critical=False,
            description="Errors that prevent normal operation",
            color_code="\033[31m",  # Red
            emoji="❌",
        )

    @classmethod
    def CRITICAL(cls) -> "ModelSeverity":
        """Critical severity - critical errors requiring immediate attention."""
        return cls(
            name="CRITICAL",
            value="critical",
            numeric_value=50,
            is_blocking=True,
            is_critical=True,
            description="Critical errors requiring immediate attention",
            color_code="\033[91m",  # Bright Red
            emoji="🚨",
        )

    @classmethod
    def FATAL(cls) -> "ModelSeverity":
        """Fatal severity - unrecoverable errors."""
        return cls(
            name="FATAL",
            value="fatal",
            numeric_value=60,
            is_blocking=True,
            is_critical=True,
            description="Fatal errors that cannot be recovered",
            color_code="\033[35m",  # Magenta
            emoji="💀",
        )

    @classmethod
    def from_string(cls, severity: str) -> "ModelSeverity":
        """Create ModelSeverity from string for current standards."""
        severity_upper = severity.upper()
        factory_map = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARNING": cls.WARNING,
            "ERROR": cls.ERROR,
            "CRITICAL": cls.CRITICAL,
            "FATAL": cls.FATAL,
        }

        factory = factory_map.get(severity_upper)
        if factory:
            return factory()
        # Unknown severity - default to INFO
        return cls(
            name=severity_upper,
            value=severity.lower(),
            numeric_value=20,
            is_blocking=False,
            is_critical=False,
            description=f"Custom severity: {severity}",
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.value

    def __eq__(self, other) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.value == other or self.name == other.upper()
        if isinstance(other, ModelSeverity):
            return self.name == other.name
        return False

    def __lt__(self, other: "ModelSeverity") -> bool:
        """Enable severity comparison."""
        if isinstance(other, ModelSeverity):
            return self.numeric_value < other.numeric_value
        return NotImplemented

    def __le__(self, other: "ModelSeverity") -> bool:
        """Enable severity comparison."""
        if isinstance(other, ModelSeverity):
            return self.numeric_value <= other.numeric_value
        return NotImplemented

    def __gt__(self, other: "ModelSeverity") -> bool:
        """Enable severity comparison."""
        if isinstance(other, ModelSeverity):
            return self.numeric_value > other.numeric_value
        return NotImplemented

    def __ge__(self, other: "ModelSeverity") -> bool:
        """Enable severity comparison."""
        if isinstance(other, ModelSeverity):
            return self.numeric_value >= other.numeric_value
        return NotImplemented

    # Compatibility methods
    def get_numeric_value(self) -> int:
        """Get numeric value for comparison (higher = more severe)."""
        return self.numeric_value

    def is_critical_or_above(self) -> bool:
        """Check if this is critical or fatal severity."""
        return self.is_critical
