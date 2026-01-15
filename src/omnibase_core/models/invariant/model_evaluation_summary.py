"""Evaluation summary model for invariant batch evaluation results.

Thread Safety:
    ModelEvaluationSummary is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.invariant.model_invariant_result import ModelInvariantResult


class ModelEvaluationSummary(BaseModel):
    """Summary of evaluating all invariants in a set.

    Provides aggregate statistics and individual results from evaluating
    an entire ModelInvariantSet against an output.

    Attributes:
        results: List of individual invariant evaluation results.
        passed_count: Number of invariants that passed.
        failed_count: Number of invariants that failed.
        critical_failures: Number of failed invariants with CRITICAL severity.
        fatal_failures: Number of failed invariants with FATAL severity.
        warning_failures: Number of failed invariants with WARNING severity.
        error_failures: Number of failed invariants with ERROR severity.
        info_failures: Number of failed invariants with INFO or DEBUG severity.
        overall_passed: True if all critical/fatal invariants passed.
        total_duration_ms: Total time to evaluate all invariants in milliseconds.
        evaluated_at: Timestamp when evaluation completed.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    results: list[ModelInvariantResult] = Field(
        ...,
        description="List of individual invariant evaluation results",
    )
    passed_count: int = Field(
        ...,
        ge=0,
        description="Number of invariants that passed",
    )
    failed_count: int = Field(
        ...,
        ge=0,
        description="Number of invariants that failed",
    )
    critical_failures: int = Field(
        ...,
        ge=0,
        description="Number of failed invariants with CRITICAL severity",
    )
    fatal_failures: int = Field(
        default=0,
        ge=0,
        description="Number of failed invariants with FATAL severity",
    )
    warning_failures: int = Field(
        ...,
        ge=0,
        description="Number of failed invariants with WARNING severity",
    )
    error_failures: int = Field(
        default=0,
        ge=0,
        description="Number of failed invariants with ERROR severity",
    )
    info_failures: int = Field(
        default=0,
        ge=0,
        description="Number of failed invariants with INFO or DEBUG severity",
    )
    overall_passed: bool = Field(
        ...,
        description="True if all critical and fatal invariants passed",
    )
    total_duration_ms: float = Field(
        ...,
        ge=0,
        description="Total evaluation time in milliseconds",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when evaluation completed",
    )


__all__ = ["ModelEvaluationSummary"]
