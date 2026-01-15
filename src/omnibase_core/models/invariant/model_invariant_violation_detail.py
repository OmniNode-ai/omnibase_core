"""
Invariant violation detail model for debugging invariant failures.

Provides detailed information about a single invariant violation,
including what failed, why it failed, and suggestions for fixing it.

Thread Safety:
    ModelInvariantViolationDetail is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_comparison_type import EnumComparisonType
from omnibase_core.enums.enum_invariant_type import EnumInvariantType
from omnibase_core.models.invariant.model_invariant_definition import (
    InvariantConfigUnion,
)


class ModelInvariantViolationDetail(BaseModel):
    """
    Detailed information about a single invariant violation.

    Provides debugging context to understand and fix invariant failures,
    including what failed, why it failed, and how to fix it.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    # Invariant Information
    invariant_id: UUID = Field(..., description="Unique identifier of the invariant")
    invariant_name: str = Field(..., description="Human-readable name of the invariant")
    invariant_type: EnumInvariantType = Field(
        ..., description="Type of invariant validation"
    )
    severity: EnumSeverity = Field(..., description="Severity level of the violation")

    # What Failed
    field_path: str | None = Field(
        default=None,
        description="Path to the failed field, e.g., 'response.choices.0.message'",
    )
    actual_value: Any = Field(
        default=None, description="Actual value observed during evaluation"
    )
    expected_value: Any = Field(
        default=None, description="Expected value per the invariant configuration"
    )

    # Why It Failed
    message: str = Field(
        ..., description="Human-readable message describing the failure"
    )
    explanation: str = Field(..., description="Detailed explanation with context")

    # Comparison Details
    comparison_type: EnumComparisonType = Field(
        ..., description="How values were compared"
    )
    operator: str | None = Field(
        default=None, description="Comparison operator used, e.g., '>=', '<=', '=='"
    )

    # Context
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the evaluation occurred",
    )
    config_snapshot: InvariantConfigUnion | None = Field(
        default=None,
        description="The invariant config used for this evaluation",
    )

    # Debugging Helpers
    suggestion: str | None = Field(
        default=None, description="Actionable suggestion for fixing the violation"
    )
    related_fields: list[str] = Field(
        default_factory=list, description="Other relevant fields to inspect"
    )

    def format_comparison(self) -> str:
        """
        Format actual vs expected for display.

        Returns:
            Formatted string like "Expected: >= 0.8, Got: 0.65"
        """
        if self.operator:
            return (
                f"Expected: {self.operator} {self._format_value(self.expected_value)}, "
                f"Got: {self._format_value(self.actual_value)}"
            )
        return (
            f"Expected: {self._format_value(self.expected_value)}, "
            f"Got: {self._format_value(self.actual_value)}"
        )

    def format_explanation(self) -> str:
        """
        Generate detailed explanation with context.

        Returns:
            Context-aware explanation based on invariant type.
        """
        if self.invariant_type == EnumInvariantType.FIELD_VALUE:
            return (
                f"The field '{self.field_path}' has value "
                f"{self._format_value(self.actual_value)} "
                f"but was expected to be {self._format_expectation()}."
            )
        elif self.invariant_type == EnumInvariantType.LATENCY:
            if isinstance(self.actual_value, (int, float)) and isinstance(
                self.expected_value, (int, float)
            ):
                over_by = self.actual_value - self.expected_value
                over_pct = (
                    (over_by / self.expected_value) * 100 if self.expected_value else 0
                )
                return (
                    f"The operation took {self.actual_value}ms to respond, "
                    f"which is {over_by:.0f}ms ({over_pct:.0f}%) over the "
                    f"{self.expected_value}ms limit."
                )
            return self.explanation
        elif self.invariant_type == EnumInvariantType.SCHEMA:
            return (
                f"The field '{self.field_path}' has type "
                f"{type(self.actual_value).__name__} "
                f"but the schema requires {self._format_value(self.expected_value)}."
            )
        elif self.invariant_type == EnumInvariantType.FIELD_PRESENCE:
            return (
                f"The required field '{self.field_path}' is missing from the response."
            )
        elif self.invariant_type == EnumInvariantType.THRESHOLD:
            return (
                f"The metric value {self._format_value(self.actual_value)} "
                f"is outside the allowed threshold of {self._format_expectation()}."
            )
        return self.explanation

    def to_log_entry(self) -> str:
        """
        Single-line format for logging.

        Returns:
            Compact log entry with key information.
        """
        severity_str = self.severity.value.upper()
        field_info = f" at {self.field_path}" if self.field_path else ""
        return f"[{severity_str}] {self.invariant_name}{field_info}: {self.message}"

    def to_dict_for_display(self) -> dict[str, str]:
        """
        Dict with string values for UI display.

        Returns:
            Dictionary with all values converted to strings.
        """
        return {
            "invariant_id": str(self.invariant_id),
            "invariant_name": self.invariant_name,
            "invariant_type": self.invariant_type.value,
            "severity": self.severity.value,
            "field_path": self.field_path or "",
            "actual_value": self._format_value(self.actual_value),
            "expected_value": self._format_value(self.expected_value),
            "message": self.message,
            "explanation": self.explanation,
            "comparison_type": self.comparison_type.value,
            "operator": self.operator or "",
            "evaluated_at": self.evaluated_at.isoformat(),
            "suggestion": self.suggestion or "",
            "related_fields": ", ".join(self.related_fields),
        }

    def _format_value(self, value: Any, max_length: int = 100) -> str:
        """Format a value for display, truncating if needed."""
        if value is None:
            return "null"
        str_value = str(value)
        if len(str_value) > max_length:
            return str_value[: max_length - 3] + "..."
        return str_value

    def _format_expectation(self) -> str:
        """Format the expected value with operator if present."""
        if self.operator:
            return f"{self.operator} {self._format_value(self.expected_value)}"
        return self._format_value(self.expected_value)


__all__ = ["ModelInvariantViolationDetail"]
