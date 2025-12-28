"""
ModelPolicySeverity: Policy violation severity configuration.

This model represents policy violation severity levels and handling.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelPolicySeverity(BaseModel):
    """Policy violation severity configuration.

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(from_attributes=True)

    level: str = Field(
        default="error",
        description="Severity level: info, warning, error, critical",
        pattern=r"^(info|warning|error|critical)$",
    )

    auto_remediate: bool = Field(
        default=False,
        description="Whether to attempt automatic remediation",
    )

    block_operation: bool = Field(
        default=True,
        description="Whether to block the operation on violation",
    )

    notify_administrators: bool = Field(
        default=False,
        description="Whether to notify administrators on violation",
    )

    log_to_audit: bool = Field(
        default=True,
        description="Whether to log violations to audit trail",
    )

    escalation_threshold: int = Field(
        default=3,
        description="Number of violations before escalation",
        ge=1,
    )

    remediation_action: str | None = Field(
        default=None,
        description="Automatic remediation action to take",
    )

    custom_message: str | None = Field(
        default=None,
        description="Custom message for this severity level",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate severity level."""
        valid_levels = {"info", "warning", "error", "critical"}
        if v not in valid_levels:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid severity level: {v}. Must be one of: {valid_levels}",
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
