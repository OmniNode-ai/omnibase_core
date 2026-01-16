"""Invariant violation breakdown model for corpus replay aggregation.

Breaks down invariant violations by type and severity for reporting
during corpus replay comparisons (OMN-1195).

Thread Safety:
    ModelInvariantViolationBreakdown is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field


class ModelInvariantViolationBreakdown(BaseModel):
    """Breakdown of invariant violations by type and severity.

    Aggregates violation data from corpus replay comparisons, providing
    counts by violation type (e.g., output_equivalence, latency, cost)
    and by severity level (e.g., debug, info, warning, error, critical, fatal).

    Attributes:
        total_violations: Total number of violations (failures in replay).
        by_type: Count of violations grouped by type (e.g., {"output_equivalence": 3}).
        by_severity: Count of violations grouped by severity level.
        new_violations: Violations that failed in replay but passed in baseline (regressions).
        fixed_violations: Violations that passed in replay but failed in baseline (improvements).

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total_violations: int = Field(
        ...,
        ge=0,
        description="Total number of violations (failures in replay)",
    )
    by_type: dict[str, int] = Field(
        ...,
        description="Count of violations grouped by type",
    )
    by_severity: dict[str, int] = Field(
        ...,
        description="Count of violations grouped by severity level",
    )
    new_violations: int = Field(
        ...,
        ge=0,
        description="Violations that failed in replay but passed in baseline (regressions)",
    )
    new_critical_violations: int = Field(
        ...,
        ge=0,
        description="Critical violations that failed in replay but passed in baseline",
    )
    fixed_violations: int = Field(
        ...,
        ge=0,
        description="Violations that passed in replay but failed in baseline (improvements)",
    )

    @classmethod
    def from_violation_deltas(
        cls,
        deltas: list[dict[str, object]],
    ) -> "ModelInvariantViolationBreakdown":
        """Aggregate violation deltas into a breakdown.

        Takes a list of violation delta records and produces a summary
        breakdown by type and severity. A violation is counted when
        replay_passed is False.

        Args:
            deltas: List of violation delta dictionaries. Each dict should contain:
                - type: str - The violation type (e.g., "output_equivalence", "latency")
                - severity: str - The severity level (e.g., "critical", "warning", "info")
                - baseline_passed: bool - Whether the invariant passed in baseline
                - replay_passed: bool - Whether the invariant passed in replay

        Returns:
            ModelInvariantViolationBreakdown with aggregated counts.
        """
        if not deltas:
            return cls(
                total_violations=0,
                by_type={},
                by_severity={},
                new_violations=0,
                new_critical_violations=0,
                fixed_violations=0,
            )

        # Count violations (replay_passed=False means it's a current violation)
        type_counter: Counter[str] = Counter()
        severity_counter: Counter[str] = Counter()
        new_count = 0
        new_critical_count = 0
        fixed_count = 0

        for delta in deltas:
            baseline_passed = bool(delta.get("baseline_passed", True))
            replay_passed = bool(delta.get("replay_passed", True))
            violation_type = str(delta.get("type", "unknown"))
            severity = str(delta.get("severity", "info"))

            # Count as violation if it failed in replay
            if not replay_passed:
                type_counter[violation_type] += 1
                severity_counter[severity] += 1

                # New violation: passed in baseline but failed in replay (regression)
                if baseline_passed:
                    new_count += 1
                    # Track new critical violations specifically
                    if severity == "critical":
                        new_critical_count += 1

            # Fixed violation: failed in baseline but passed in replay (improvement)
            if not baseline_passed and replay_passed:
                fixed_count += 1

        total = sum(type_counter.values())

        return cls(
            total_violations=total,
            by_type=dict(type_counter),
            by_severity=dict(severity_counter),
            new_violations=new_count,
            new_critical_violations=new_critical_count,
            fixed_violations=fixed_count,
        )


__all__ = ["ModelInvariantViolationBreakdown"]
