"""Model for detailed invariant result for display.

Thread Safety:
    ModelInvariantResultDetail is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.decorators import allow_dict_any


@allow_dict_any(
    reason="violation_details captures invariant-specific structured data which varies by invariant type"
)
class ModelInvariantResultDetail(BaseModel):
    """Detailed invariant result for display.

    Captures the result of an invariant check for both baseline
    and replay executions, including status change detection
    (regression, improvement, unchanged).

    Attributes:
        invariant_name: Name identifier of the invariant.
        invariant_type: Type/category of the invariant.
        baseline_passed: Whether the invariant passed in baseline execution.
        replay_passed: Whether the invariant passed in replay execution.
        status_change: Classification of change between baseline and replay.
        violation_message: Human-readable message if invariant was violated.
        violation_details: Additional structured details about the violation.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    invariant_name: str
    invariant_type: str
    baseline_passed: bool
    replay_passed: bool
    status_change: Literal[
        "unchanged_pass", "unchanged_fail", "regression", "improvement"
    ]
    violation_message: str | None = None
    violation_details: dict[str, Any] | None = None


__all__ = ["ModelInvariantResultDetail"]
