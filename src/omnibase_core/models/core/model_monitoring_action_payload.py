"""
Monitoring Action Payload Model.

Payload for monitoring actions (monitor, collect, report, alert).
"""

from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelMonitoringActionPayload(ModelActionPayloadBase):
    """Payload for monitoring actions (monitor, collect, report, alert)."""

    metrics: list[str] = Field(
        default_factory=list,
        description="Metrics to monitor/collect",
    )
    interval_seconds: int | None = Field(
        default=None,
        description="Monitoring interval in seconds",
    )
    threshold: float | None = Field(default=None, description="Threshold for alerts")
    output_format: str | None = Field(
        default=None, description="Output format for reports"
    )

    @field_validator("action_type")
    @classmethod
    def validate_monitoring_action(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid monitoring action."""
        from omnibase_core.models.core.model_predefined_categories import QUERY

        if v.category != QUERY:
            msg = f"Invalid monitoring action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
