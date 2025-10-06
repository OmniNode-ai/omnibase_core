from typing import Optional

from pydantic import Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

"""
ONEX-Compliant Severity Model

Unified severity model with strong typing and immutable constructor patterns.
Phase 3I remediation: Eliminated all factory methods and conversion anti-patterns.
"""

from pathlib import Path
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field, validator


class ModelSeverity(BaseModel):
    """
    ONEX-compliant severity model with strong typing and validation.

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
        max_length=100,
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
    @validator("name")
    def validate_name_consistency(cls, v, values) -> None:
        """Ensure name and value are consistent."""
        if "value" in values and v.lower() != values["value"]:
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Name '{v}' must match value '{values.get('value', '')}'",
            )
        return v

    @validator("numeric_value")
    def validate_severity_ranges(cls, v, values) -> None:
        """Validate numeric values align with severity expectations."""
        name = values.get("name", "")
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
                    error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                    message=f"Numeric value {v} for {name} must be in range [{min_val}, {max_val}]",
                )
        return v

    @validator("is_critical")
    def validate_critical_consistency(cls, v, values) -> None:
        """Ensure critical flag aligns with severity level."""
        name = values.get("name", "")
        numeric = values.get("numeric_value", 0)

        if name in ["CRITICAL", "FATAL"] and not v:
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Severity {name} must have is_critical=True",
            )
        if name in ["DEBUG", "INFO", "WARNING"] and v:
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Severity {name} cannot have is_critical=True",
            )
        if numeric >= 45 and not v:
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.VALIDATION_ERROR,
                message=f"Numeric value {numeric} requires is_critical=True",
            )

        return v

    def __str__(self) -> str:
        """ONEX-compliant string representation."""
        return self.value

    def __eq__(self, other) -> bool:
        """ONEX-compliant equality comparison - type-safe only."""
        if isinstance(other, ModelSeverity):
            return self.name == other.name and self.numeric_value == other.numeric_value
        return False

    def __lt__(self, other: "ModelSeverity") -> bool:
        """ONEX-compliant severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value < other.numeric_value

    def __le__(self, other: "ModelSeverity") -> bool:
        """ONEX-compliant severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value <= other.numeric_value

    def __gt__(self, other: "ModelSeverity") -> bool:
        """ONEX-compliant severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value > other.numeric_value

    def __ge__(self, other: "ModelSeverity") -> bool:
        """ONEX-compliant severity comparison by numeric value."""
        if not isinstance(other, ModelSeverity):
            raise ModelOnexError(
                error_code=ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH,
                message=f"Cannot compare ModelSeverity with {type(other)}",
            )
        return self.numeric_value >= other.numeric_value

    def __hash__(self) -> int:
        """ONEX-compliant hash for set/dict[str, Any]usage."""
        return hash((self.name, self.numeric_value))

    # ONEX-compliant property methods
    def get_severity_level(self) -> int:
        """Get numeric severity level for comparison."""
        return self.numeric_value

    def is_critical_severity(self) -> bool:
        """Check if this represents critical or fatal severity."""
        return self.is_critical

    def is_blocking_severity(self) -> bool:
        """Check if this severity blocks execution."""
        return self.is_blocking
