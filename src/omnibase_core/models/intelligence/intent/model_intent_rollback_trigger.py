# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent rollback trigger signal model.

Represents a signal recommending that execution results for a specific intent
should be reverted. Rollback triggers are produced when outcome analysis
detects that the intent produced adverse results (e.g., regressions, test
failures, quality degradation).

Part of the Intent Intelligence Framework (OMN-2486).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelIntentRollbackTrigger"]


class ModelIntentRollbackTrigger(BaseModel):
    """Signal to revert execution results based on outcome analysis.

    Produced by the outcome analysis subsystem when post-execution metrics
    indicate that changes produced by an intent should be reverted. Downstream
    systems consume this signal to initiate automated or human-reviewed rollback.

    Attributes:
        intent_id: The intent whose execution results should be reverted.
        trigger_reason: Explanation of why rollback is being recommended.
        outcome_label: Label describing the observed outcome that triggered
            the rollback recommendation (e.g., ``"test_failure"``,
            ``"quality_regression"``, ``"security_violation"``).
        rollback_recommended: Whether rollback is actively recommended.
            ``True`` means the system recommends reverting; ``False`` means
            this is an informational signal only.
        triggered_at: Timestamp when this trigger was produced (UTC).
            Callers must inject this value — no ``datetime.now()`` defaults.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import UTC, datetime
        >>> trigger = ModelIntentRollbackTrigger(
        ...     intent_id=uuid4(),
        ...     trigger_reason="3 unit tests regressed after applying changes",
        ...     outcome_label="test_failure",
        ...     rollback_recommended=True,
        ...     triggered_at=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    intent_id: UUID = Field(
        description="The intent whose execution results should be reverted",
    )
    trigger_reason: str = Field(
        description="Explanation of why rollback is being recommended",
    )
    outcome_label: str = Field(
        description=(
            "Label describing the observed outcome that triggered the rollback recommendation "
            "(e.g., 'test_failure', 'quality_regression', 'security_violation')"
        ),
    )
    rollback_recommended: bool = Field(
        description=(
            "Whether rollback is actively recommended. "
            "True means the system recommends reverting; "
            "False means this is an informational signal only."
        ),
    )
    triggered_at: datetime = Field(
        description=(
            "Timestamp when this trigger was produced (UTC). "
            "Callers must inject this value — no datetime.now() defaults."
        ),
    )
