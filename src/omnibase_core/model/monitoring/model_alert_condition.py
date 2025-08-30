"""
Model for alert condition.

Alert condition definition for monitoring.
"""

from pydantic import BaseModel, Field


class ModelAlertCondition(BaseModel):
    """Alert condition definition."""

    condition_id: str = Field(..., description="Unique condition identifier")
    metric_name: str = Field(..., description="Metric being monitored")
    operator: str = Field(..., description="Comparison operator (>, <, ==, etc.)")
    threshold_value: float = Field(..., description="Threshold value")
    duration_seconds: int = Field(
        0, ge=0, description="Duration condition must persist"
    )

    evaluation_window: int = Field(60, gt=0, description="Evaluation window in seconds")
    hysteresis_percent: float = Field(
        5.0, ge=0, description="Hysteresis percentage to prevent flapping"
    )

    enabled: bool = Field(True, description="Whether condition is active")

    def evaluate(self, current_value: float, duration_met: bool) -> bool:
        """Evaluate if condition is met."""
        if not self.enabled:
            return False

        # Simple evaluation - would be more sophisticated in production
        if self.operator == ">":
            condition_met = current_value > self.threshold_value
        elif self.operator == "<":
            condition_met = current_value < self.threshold_value
        elif self.operator == ">=":
            condition_met = current_value >= self.threshold_value
        elif self.operator == "<=":
            condition_met = current_value <= self.threshold_value
        elif self.operator == "==":
            condition_met = abs(current_value - self.threshold_value) < 0.001
        else:
            return False

        return condition_met and (self.duration_seconds == 0 or duration_met)
