"""
ModelCostLedger - Budget state machine with cost tracking and escalation.

Defines the ModelCostLedger model which manages a budget state machine,
tracking multiple cost entries and providing budget monitoring with
warning thresholds and escalation capabilities.

This is a pure data model with immutable operations (all mutations
return new instances).

.. versionadded:: 0.6.0
    Added as part of OmniMemory cost tracking infrastructure (OMN-1240)
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError
from omnibase_core.models.omnimemory.model_cost_entry import ModelCostEntry
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCostLedger(BaseModel):
    """Budget state machine with cost tracking and escalation.

    Manages a collection of cost entries within a budget, providing
    monitoring for warning thresholds and hard ceilings, as well as
    budget escalation capabilities.

    Attributes:
        ledger_id: Unique identifier for this ledger (auto-generated).
        budget_total: Total budget amount in USD.
        budget_remaining: Remaining budget (budget_total - total_spent).
        entries: Immutable tuple of cost entries in this ledger.
        total_spent: Running total of all costs in USD.
        escalation_count: Number of times the budget has been escalated.
        last_escalation_reason: Reason for the most recent escalation.
        warning_threshold: Fraction of budget that triggers warning (0-1).
        hard_ceiling: Fraction of budget that represents hard limit (up to 2.0).

    Note:
        This model is frozen (immutable). All mutation methods return new
        instances rather than modifying in place. Cost values use Python
        floats for convenience.

    Example:
        >>> from datetime import datetime, UTC
        >>> from omnibase_core.models.omnimemory import ModelCostEntry, ModelCostLedger
        >>>
        >>> ledger = ModelCostLedger(budget_total=10.0)
        >>> ledger.budget_remaining
        10.0
        >>> ledger.is_warning()
        False
        >>>
        >>> entry = ModelCostEntry(
        ...     timestamp=datetime.now(UTC),
        ...     operation="chat_completion",
        ...     model_used="gpt-4",
        ...     tokens_in=100,
        ...     tokens_out=50,
        ...     cost=8.50,
        ...     cumulative_total=8.50,
        ... )
        >>> updated_ledger = ledger.with_entry(entry)
        >>> updated_ledger.is_warning()
        True
        >>> updated_ledger.budget_remaining
        1.5

    .. versionadded:: 0.6.0
        Added as part of OmniMemory cost tracking infrastructure (OMN-1240)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Required Fields ===

    ledger_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ledger identifier",
    )

    budget_total: float = Field(
        ...,
        gt=0.0,
        description="Total budget amount in USD",
    )

    # === Computed/Derived Fields ===

    budget_remaining: float = Field(
        default=0.0,
        description="Remaining budget (computed as budget_total - total_spent). Can be negative when overspent.",
    )

    entries: tuple[ModelCostEntry, ...] = Field(
        default=(),
        description="Immutable tuple of cost entries",
    )

    total_spent: float = Field(
        default=0.0,
        ge=0.0,
        description="Running total of all costs in USD",
    )

    # === Escalation Tracking ===

    escalation_count: int = Field(
        default=0,
        ge=0,
        description="Number of times budget has been escalated",
    )

    last_escalation_reason: str | None = Field(
        default=None,
        description="Reason for the most recent budget escalation",
    )

    # === Threshold Configuration ===

    warning_threshold: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
        description="Fraction of budget that triggers warning (0 < x <= 1)",
    )

    hard_ceiling: float = Field(
        default=1.0,
        gt=0.0,
        le=2.0,
        description="Fraction of budget that represents hard limit (up to 2.0 for escalation)",
    )

    # === Validators ===

    @field_validator("last_escalation_reason")
    @classmethod
    def validate_escalation_reason_not_empty(cls, v: str | None) -> str | None:
        """Ensure escalation reason is not an empty string.

        Args:
            v: The escalation reason to validate.

        Returns:
            The validated escalation reason or None.

        Raises:
            ValueError: If the reason is an empty string.
        """
        if v is not None and len(v.strip()) == 0:
            raise ValueError(
                "last_escalation_reason cannot be an empty string; use None instead"
            )
        return v

    @model_validator(mode="after")
    def validate_thresholds_and_budget(self) -> "ModelCostLedger":
        """Validate threshold ordering and budget consistency.

        Ensures that:
        1. hard_ceiling > warning_threshold
        2. budget_remaining equals budget_total - total_spent (if not explicitly set)

        Returns:
            The validated model instance.

        Raises:
            ValueError: If thresholds are incorrectly ordered or budget inconsistent.
        """
        if self.hard_ceiling <= self.warning_threshold:
            raise ValueError(
                f"hard_ceiling ({self.hard_ceiling}) must be greater than "
                f"warning_threshold ({self.warning_threshold})"
            )

        # Validate budget_remaining consistency
        expected_remaining = self.budget_total - self.total_spent
        # Allow small floating point differences
        if abs(self.budget_remaining - expected_remaining) > 1e-9:
            raise ValueError(
                f"budget_remaining ({self.budget_remaining}) must equal "
                f"budget_total - total_spent ({expected_remaining})"
            )

        return self

    @model_validator(mode="after")
    def validate_entries_cumulative_totals(self) -> "ModelCostLedger":
        """Validate that entries have consistent cumulative_total values.

        Ensures that each entry's cumulative_total is consistent with the
        previous entry's cumulative_total plus the current entry's cost.
        The first entry's cumulative_total can be any value (representing
        prior spending not tracked as entries).

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any entry has inconsistent cumulative_total.
        """
        if len(self.entries) < 2:
            return self

        for i in range(1, len(self.entries)):
            prev_entry = self.entries[i - 1]
            curr_entry = self.entries[i]
            expected_cumulative = prev_entry.cumulative_total + curr_entry.cost
            # Allow small floating point differences
            if abs(curr_entry.cumulative_total - expected_cumulative) > 1e-9:
                raise ValueError(
                    f"Entry {i} has cumulative_total {curr_entry.cumulative_total} "
                    f"but expected {expected_cumulative} "
                    f"(previous cumulative_total {prev_entry.cumulative_total} + "
                    f"cost {curr_entry.cost})"
                )

        return self

    @model_validator(mode="before")
    @classmethod
    def compute_budget_remaining(cls, data: object) -> SerializedDict:
        """Compute budget_remaining from budget_total and total_spent if not provided.

        Args:
            data: The raw input data (typically a dictionary).

        Returns:
            The data with budget_remaining computed if needed.
        """
        if isinstance(data, dict):
            budget_total = data.get("budget_total", 0.0)
            total_spent = data.get("total_spent", 0.0)

            # Only compute if not explicitly provided
            if "budget_remaining" not in data:
                data["budget_remaining"] = budget_total - total_spent

            return data

        return {}  # Return empty dict for non-dict input (Pydantic will fail validation)

    # === Immutable Mutation Methods ===

    def with_entry(self, entry: ModelCostEntry) -> "ModelCostLedger":
        """Add an entry and return a new ledger instance with updated totals.

        Creates a new ModelCostLedger with the entry appended to the entries
        tuple and totals recalculated.

        Args:
            entry: The cost entry to add.

        Returns:
            A new ModelCostLedger instance with the entry added.

        Raises:
            OnexError: If entry's cumulative_total does not match expected
                cumulative total (self.total_spent + entry.cost).

        Example:
            >>> from datetime import datetime, UTC
            >>> ledger = ModelCostLedger(budget_total=10.0)
            >>> entry = ModelCostEntry(
            ...     timestamp=datetime.now(UTC),
            ...     operation="completion",
            ...     model_used="gpt-4",
            ...     tokens_in=100,
            ...     tokens_out=50,
            ...     cost=0.50,
            ...     cumulative_total=0.50,
            ... )
            >>> new_ledger = ledger.with_entry(entry)
            >>> new_ledger.total_spent
            0.5
            >>> len(new_ledger.entries)
            1

        .. versionadded:: 0.6.0
        """
        new_total_spent = self.total_spent + entry.cost

        # Validate cumulative_total consistency with small tolerance for floats
        if abs(entry.cumulative_total - new_total_spent) > 1e-9:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Entry cumulative_total ({entry.cumulative_total}) does not match "
                    f"expected cumulative total ({new_total_spent})"
                ),
            )

        new_budget_remaining = self.budget_total - new_total_spent

        return ModelCostLedger(
            ledger_id=self.ledger_id,
            budget_total=self.budget_total,
            budget_remaining=new_budget_remaining,
            entries=(*self.entries, entry),
            total_spent=new_total_spent,
            escalation_count=self.escalation_count,
            last_escalation_reason=self.last_escalation_reason,
            warning_threshold=self.warning_threshold,
            hard_ceiling=self.hard_ceiling,
        )

    def is_warning(self) -> bool:
        """Check if spending has reached or exceeded the warning threshold.

        The warning threshold is a fraction of the total budget. When
        total_spent >= warning_threshold * budget_total, this returns True.

        Returns:
            True if spending is at or above warning level, False otherwise.

        Example:
            >>> ledger = ModelCostLedger(budget_total=100.0, warning_threshold=0.8)
            >>> ledger.is_warning()  # 0% spent
            False
            >>> ledger_80 = ModelCostLedger(
            ...     budget_total=100.0,
            ...     total_spent=80.0,
            ...     budget_remaining=20.0,
            ...     warning_threshold=0.8,
            ... )
            >>> ledger_80.is_warning()  # 80% spent
            True

        .. versionadded:: 0.6.0
        """
        return self.total_spent >= self.warning_threshold * self.budget_total

    def is_exceeded(self) -> bool:
        """Check if spending has reached or exceeded the hard ceiling.

        The hard ceiling is a fraction of the total budget (up to 2.0 for
        escalation scenarios). When total_spent >= hard_ceiling * budget_total,
        this returns True.

        Returns:
            True if spending is at or above hard ceiling, False otherwise.

        Example:
            >>> ledger = ModelCostLedger(budget_total=100.0, hard_ceiling=1.0)
            >>> ledger.is_exceeded()  # 0% spent
            False
            >>> ledger_full = ModelCostLedger(
            ...     budget_total=100.0,
            ...     total_spent=100.0,
            ...     budget_remaining=0.0,
            ...     hard_ceiling=1.0,
            ... )
            >>> ledger_full.is_exceeded()  # 100% spent
            True

        .. versionadded:: 0.6.0
        """
        return self.total_spent >= self.hard_ceiling * self.budget_total

    def with_escalation(
        self, additional_budget: float, reason: str
    ) -> "ModelCostLedger":
        """Escalate the budget and return a new ledger instance.

        Increases the total budget by the specified amount and records
        the escalation reason.

        Args:
            additional_budget: Amount to add to budget_total (must be > 0).
            reason: Explanation for why the budget is being escalated.

        Returns:
            A new ModelCostLedger instance with increased budget.

        Raises:
            OnexError: If additional_budget <= 0 or reason is empty.

        Example:
            >>> ledger = ModelCostLedger(budget_total=100.0)
            >>> escalated = ledger.with_escalation(50.0, "Project scope increased")
            >>> escalated.budget_total
            150.0
            >>> escalated.escalation_count
            1
            >>> escalated.last_escalation_reason
            'Project scope increased'

        .. versionadded:: 0.6.0
        """
        if additional_budget <= 0:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"additional_budget must be positive, got {additional_budget}",
            )
        if not reason or len(reason.strip()) == 0:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="reason cannot be empty",
            )

        new_budget_total = self.budget_total + additional_budget
        new_budget_remaining = new_budget_total - self.total_spent

        return ModelCostLedger(
            ledger_id=self.ledger_id,
            budget_total=new_budget_total,
            budget_remaining=new_budget_remaining,
            entries=self.entries,
            total_spent=self.total_spent,
            escalation_count=self.escalation_count + 1,
            last_escalation_reason=reason,
            warning_threshold=self.warning_threshold,
            hard_ceiling=self.hard_ceiling,
        )

    # === Utility Properties ===

    @property
    def entry_count(self) -> int:
        """Get the number of entries in this ledger.

        Returns:
            Number of cost entries recorded.
        """
        return len(self.entries)

    @property
    def budget_utilization(self) -> float:
        """Get the current budget utilization as a fraction.

        Returns:
            Fraction of budget spent (total_spent / budget_total).
        """
        return self.total_spent / self.budget_total

    @property
    def budget_utilization_pct(self) -> float:
        """Get the current budget utilization as a percentage.

        Returns:
            Percentage of budget spent (0-100+). Can exceed 100 if overspent.

        Example:
            >>> ledger = ModelCostLedger(budget_total=100.0, total_spent=75.0, budget_remaining=25.0)
            >>> ledger.budget_utilization_pct
            75.0
        """
        return self.budget_utilization * 100

    # === Utility Methods ===

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        utilization_pct = self.budget_utilization * 100
        status = (
            "EXCEEDED"
            if self.is_exceeded()
            else "WARNING"
            if self.is_warning()
            else "OK"
        )
        return (
            f"CostLedger(${self.total_spent:.2f}/${self.budget_total:.2f} "
            f"[{utilization_pct:.1f}%] {status}, entries={self.entry_count})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelCostLedger(ledger_id={self.ledger_id!r}, "
            f"budget_total={self.budget_total!r}, "
            f"total_spent={self.total_spent!r}, "
            f"budget_remaining={self.budget_remaining!r}, "
            f"entry_count={self.entry_count}, "
            f"escalation_count={self.escalation_count!r})"
        )


# Export for use
__all__ = ["ModelCostLedger"]
