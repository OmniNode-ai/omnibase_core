"""
ModelPolicySeverity: Policy violation severity configuration.

This model represents policy violation severity levels and handling.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ModelPolicySeverity(BaseModel):
    """Policy violation severity configuration."""

    level: str = Field(
        "error",
        description="Severity level: info, warning, error, critical",
        pattern=r"^(info|warning|error|critical)$",
    )

    auto_remediate: bool = Field(
        False, description="Whether to attempt automatic remediation"
    )

    block_operation: bool = Field(
        True, description="Whether to block the operation on violation"
    )

    notify_administrators: bool = Field(
        False, description="Whether to notify administrators on violation"
    )

    log_to_audit: bool = Field(
        True, description="Whether to log violations to audit trail"
    )

    escalation_threshold: int = Field(
        3, description="Number of violations before escalation", ge=1
    )

    remediation_action: Optional[str] = Field(
        None, description="Automatic remediation action to take"
    )

    custom_message: Optional[str] = Field(
        None, description="Custom message for this severity level"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate severity level."""
        valid_levels = {"info", "warning", "error", "critical"}
        if v not in valid_levels:
            raise ValueError(
                f"Invalid severity level: {v}. Must be one of: {valid_levels}"
            )
        return v

    def get_numeric_severity(self) -> int:
        """Get numeric severity value for comparison."""
        severity_map = {"info": 1, "warning": 2, "error": 3, "critical": 4}
        return severity_map.get(self.level, 0)

    def is_blocking(self) -> bool:
        """Check if this severity level should block operations."""
        if self.level in ["error", "critical"]:
            return True
        return self.block_operation
