"""
ONEX-Compliant Severity Model

Unified severity model with strong typing and immutable constructor patterns.
Phase 3I remediation: Eliminated all factory methods and conversion anti-patterns.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelSeverity(BaseModel):
    """
    ONEX-compatible severity model with strong typing and validation.

    Provides structured severity handling with proper constructor patterns
    and immutable design following ONEX standards.
    """

    # Core required fields with strong typing
    name: str = Field(
        default=...,
        description="Severity identifier (DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL)",
        pattern="^[A-Z][A-Z_]*$",
        min_length=3,
        max_length=10,
    )

    value: str = Field(
        default=...,
        description="Lowercase canonical value",
        pattern="^[a-z][a-z_]*$",
        min_length=3,
        max_length=10,
    )

    numeric_value: int = Field(
        default=...,
        description="Numeric severity level for comparison (higher = more severe)",
        ge=0,
        le=100,
    )

    # Behavioral properties
    is_blocking: bool = Field(
        default=...,
        description="Whether this severity blocks execution flow",
    )

    is_critical: bool = Field(
        default=...,
        description="Whether this represents critical or fatal severity",
    )

    # Optional descriptive metadata
    description: str = Field(
        default="",
        description="Human-readable severity description",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    color_code: str = Field(
        default="",
        description="ANSI color code for terminal display",
        pattern="^(\033\\[\\d+m|)$",
    )

    emoji: str = Field(
        default="",
        description="Unicode emoji representation",
        max_length=4,
    )

    # ONEX validation constraints
    @field_validator("name")
    @classmethod
    def validate_name_consistency(cls, v: str, info: ValidationInfo) -> str:
        """Ensure name and value are consistent."""
        value = info.data.get("value")
        if value is not None and v.lower() != value:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Name '{v}' must match value '{value}'",
            )
        return v

    @field_validator("numeric_value")
    @classmethod
    def validate_severity_ranges(cls, v: int, info: ValidationInfo) -> int:
        """Validate numeric values align with severity expectations."""
        name = info.data.get("name", "")
        expected_ranges = {
            "DEBUG": (0, 15),
            "INFO": (15, 25),
            "WARNING": (25, 35),
            "ERROR": (35, 45),
            "CRITICAL": (45, 55),
            "FATAL": (55, 100),
        }

        if name in expected_ranges:
            min_val, max_val = expected_ranges[name]
            if not (min_val <= v <= max_val):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Numeric value {v} for {name} must be in range [{min_val}, {max_val}]",
                )
        return v

    @field_validator("is_critical")
    @classmethod
    def validate_critical_consistency(cls, v: bool, info: ValidationInfo) -> bool:
        """Ensure critical flag aligns with severity level."""
        name = info.data.get("name", "")
        numeric = info.data.get("numeric_value", 0)

        if name in ["CRITICAL", "FATAL"] and not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Severity {name} must have is_critical=True",
            )
        if name in ["DEBUG", "INFO", "WARNING"] and v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Severity {name} cannot have is_critical=True",
            )
        if numeric >= 45 and not v:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Numeric value {numeric} requires is_critical=True",
            )

        return v

    def __str__(self) -> str:
        """ONEX-compatible string representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """ONEX-compatible equality comparison - type-safe only."""
        if isinstance(other, ModelSeverity):
            return self.name == other.name and self.numeric_value == other.numeric_value
        return False

    def __lt__(self, other: "ModelSeverity") -> bool:
        """ONEX-compatible severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value < other.numeric_value

    def __le__(self, other: "ModelSeverity") -> bool:
        """ONEX-compatible severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value <= other.numeric_value

    def __gt__(self, other: "ModelSeverity") -> bool:
        """ONEX-compatible severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value > other.numeric_value

    def __ge__(self, other: "ModelSeverity") -> bool:
        """ONEX-compatible severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value >= other.numeric_value

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        Returns:
            int: Hash computed from (name, numeric_value) tuple.
        """
        return hash((self.name, self.numeric_value))

    # ONEX-compatible property methods
    def get_severity_level(self) -> int:
        """Get numeric severity level for comparison."""
        return self.numeric_value

    def is_critical_severity(self) -> bool:
        """Check if this represents critical or fatal severity."""
        return self.is_critical

    def is_blocking_severity(self) -> bool:
        """Check if this severity blocks execution."""
        return self.is_blocking
