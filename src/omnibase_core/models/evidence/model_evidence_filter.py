"""Evidence filtering for partial exports.

This module provides filtering options for exporting subsets of evidence
based on invariant IDs, status, confidence, and date ranges.

Thread Safety:
    This model is immutable (frozen=True) and thread-safe.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelEvidenceFilter(BaseModel):
    """Filter for partial evidence exports.

    Allows filtering evidence by various criteria. All filters are combined
    with AND logic (all conditions must match).

    Attributes:
        invariant_ids: Filter to specific invariant IDs (None = all).
        status: Filter by pass/fail status ("passed", "failed", or "all").
        min_confidence: Minimum confidence score (0.0-1.0).
        start_date: Filter to evidence after this date.
        end_date: Filter to evidence before this date.

    Date Handling:
        Naive datetimes (without tzinfo) are treated as UTC for comparison.
        Use timezone-aware datetimes (e.g., ``datetime.now(UTC)``) to avoid
        ambiguity.

    Thread Safety:
        This model is immutable (frozen=True) and thread-safe.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    invariant_ids: tuple[str, ...] | None = Field(
        default=None,
        description="Filter to specific invariant IDs (None = all, tuple must be non-empty). Tuple is immutable for thread safety.",
    )
    status: Literal["passed", "failed", "all"] = Field(
        default="all",
        description="Filter by pass/fail status",
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score (0.0-1.0)",
    )
    start_date: datetime | None = Field(
        default=None,
        description="Filter to evidence after this date",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Filter to evidence before this date",
    )

    @staticmethod
    def _normalize_datetime(dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone.

        Naive datetimes are assumed to be UTC.

        Args:
            dt: The datetime to normalize.

        Returns:
            Timezone-aware datetime in UTC.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    @model_validator(mode="after")
    def validate_date_range(self) -> "ModelEvidenceFilter":
        """Ensure start_date is before end_date if both provided.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If start_date is after end_date.
        """
        if self.start_date and self.end_date:
            # Normalize to UTC for safe comparison
            start = self._normalize_datetime(self.start_date)
            end = self._normalize_datetime(self.end_date)
            if start > end:
                msg = "start_date must be before end_date"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_invariant_ids(self) -> "ModelEvidenceFilter":
        """Ensure invariant_ids is None or non-empty if provided.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If invariant_ids is an empty tuple.
        """
        if self.invariant_ids is not None and len(self.invariant_ids) == 0:
            msg = "invariant_ids must be None (all) or a non-empty tuple of IDs"
            raise ValueError(msg)
        return self

    def matches_confidence(self, confidence: float) -> bool:
        """Check if a confidence score passes the filter.

        Args:
            confidence: The confidence score to check (0.0-1.0).

        Returns:
            True if confidence >= min_confidence, False otherwise.
        """
        return confidence >= self.min_confidence

    def matches_status(self, passed: bool) -> bool:
        """Check if a pass/fail status passes the filter.

        Args:
            passed: True if the evidence passed, False if failed.

        Returns:
            True if status matches the filter, False otherwise.
        """
        if self.status == "all":
            return True
        return (self.status == "passed") == passed

    def matches_invariant(self, invariant_key: str) -> bool:
        """Check if an invariant key passes the filter.

        Args:
            invariant_key: The invariant identifier to check.

        Returns:
            True if invariant_ids is None (all) or key is in the filter.
        """
        if self.invariant_ids is None:
            return True
        return invariant_key in self.invariant_ids

    def matches_date(self, date: datetime) -> bool:
        """Check if a date passes the filter.

        Handles both timezone-aware and naive datetimes safely by
        normalizing to UTC before comparison.

        Args:
            date: The date to check.

        Returns:
            True if date is within the start_date/end_date range.
        """
        normalized_date = self._normalize_datetime(date)
        if self.start_date:
            normalized_start = self._normalize_datetime(self.start_date)
            if normalized_date < normalized_start:
                return False
        if self.end_date:
            normalized_end = self._normalize_datetime(self.end_date)
            if normalized_date > normalized_end:
                return False
        return True


__all__ = ["ModelEvidenceFilter"]
