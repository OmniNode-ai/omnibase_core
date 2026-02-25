# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelDecisionAlternative - An alternative option considered in a decision.

Represents one alternative option that was evaluated during a decision
in the Decision Store. Enforces the invariant that REJECTED alternatives
must provide a rejection_reason, while CONSIDERED and SELECTED alternatives
must not.

.. versionadded:: 0.7.0
    Added as part of Decision Store infrastructure (OMN-2763)
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ModelDecisionAlternative(BaseModel):
    """An alternative option considered during a decision.

    Represents one option evaluated during a decision recorded in the
    Decision Store. Enforces the rejection_reason invariant: REJECTED
    alternatives must supply a reason; CONSIDERED and SELECTED
    alternatives must not.

    Attributes:
        label: Human-readable label for this alternative.
        status: Evaluation status — CONSIDERED, REJECTED, or SELECTED.
        rejection_reason: Required when status is REJECTED; must be None
            for CONSIDERED and SELECTED.

    Example:
        >>> alt = ModelDecisionAlternative(
        ...     label="PostgreSQL",
        ...     status="SELECTED",
        ... )
        >>> alt.status
        'SELECTED'

        >>> rejected = ModelDecisionAlternative(
        ...     label="MySQL",
        ...     status="REJECTED",
        ...     rejection_reason="Lacks JSON indexing support required by query patterns",
        ... )
        >>> rejected.rejection_reason is not None
        True

    .. versionadded:: 0.7.0
        Added as part of Decision Store infrastructure (OMN-2763)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    """Human-readable label for this alternative."""

    status: Literal["CONSIDERED", "REJECTED", "SELECTED"]
    """Evaluation status of this alternative."""

    rejection_reason: str | None = None
    """Reason for rejection. Required when status is REJECTED; must be None otherwise."""

    @field_validator("label")
    @classmethod
    def validate_label_not_empty(cls, v: str) -> str:
        """Ensure label is a non-empty string after stripping whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("label must not be empty or whitespace-only")
        return stripped

    @model_validator(mode="after")
    def validate_rejection_reason_invariant(self) -> "ModelDecisionAlternative":
        """Enforce rejection_reason invariant.

        REJECTED status requires rejection_reason to be a non-empty string.
        CONSIDERED and SELECTED statuses require rejection_reason to be None.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If the invariant is violated.
        """
        if self.status == "REJECTED":
            if not self.rejection_reason:
                raise ValueError("rejection_reason is required when status is REJECTED")
        elif self.rejection_reason is not None:
            raise ValueError(
                f"rejection_reason must be None when status is {self.status!r}; "
                f"only REJECTED alternatives may provide a rejection_reason"
            )
        return self


__all__ = ["ModelDecisionAlternative"]
