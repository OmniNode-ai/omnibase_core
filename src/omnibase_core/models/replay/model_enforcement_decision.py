"""
ModelEnforcementDecision - Enforcement decision model for replay safety.

This module provides the ModelEnforcementDecision model that captures the
outcome of replay safety enforcement decisions for effect execution.

Design:
    Enforcement decisions record the analysis and outcome for each effect:
    - What type of effect was evaluated
    - Whether it was determined to be deterministic or not
    - The source of non-determinism if applicable
    - What enforcement mode was in effect
    - The decision outcome (allowed, blocked, warned, mocked)
    - Reasoning and any mock values injected

Architecture:
    During replay execution, the safety enforcer evaluates each effect
    and produces a ModelEnforcementDecision. This enables:
    - Audit trails for compliance
    - Debugging of replay failures
    - Gradual migration to deterministic execution
    - Automatic mock injection for testing

Thread Safety:
    ModelEnforcementDecision is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelEnforcementDecision
        from omnibase_core.enums.replay import (
            EnumEffectDeterminism,
            EnumEnforcementMode,
            EnumNonDeterministicSource,
        )
        from datetime import datetime, timezone

        # Create a decision for a blocked non-deterministic effect
        decision = ModelEnforcementDecision(
            effect_type="http.get",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.NETWORK,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Network effects are non-deterministic in strict mode",
            timestamp=datetime.now(timezone.utc),
        )

        # Create a decision with mock injection
        mocked_decision = ModelEnforcementDecision(
            effect_type="time.now",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.TIME,
            mode=EnumEnforcementMode.MOCKED,
            decision="mocked",
            reason="Time effect mocked with recorded value",
            timestamp=datetime.now(timezone.utc),
            mock_injected=True,
            original_value=None,
            mocked_value="2024-06-15T12:00:00Z",
        )

Related:
    - OMN-1150: Replay Safety Enforcement
    - EnumEnforcementMode: Enforcement mode configuration
    - EnumEffectDeterminism: Effect determinism classification
    - EnumNonDeterministicSource: Source of non-determinism

.. versionadded:: 0.6.3
"""

__all__ = ["ModelEnforcementDecision", "EnforcementOutcome"]

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Type alias for enforcement decision outcomes
EnforcementOutcome = Literal["allowed", "blocked", "warned", "mocked"]

from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
from omnibase_core.enums.replay.enum_enforcement_mode import EnumEnforcementMode
from omnibase_core.enums.replay.enum_non_deterministic_source import (
    EnumNonDeterministicSource,
)


class ModelEnforcementDecision(BaseModel):
    """
    Outcome of replay safety enforcement for an effect.

    Records the analysis and decision for each effect evaluated during
    replay execution, enabling audit trails and debugging.

    Attributes:
        effect_type: Type identifier for the effect (e.g., "http.get",
            "time.now", "random.randint"). Used for categorization and
            pattern matching in enforcement rules.
        determinism: Classification of the effect's determinism. Indicates
            whether the effect produces consistent outputs.
        source: Source of non-determinism if applicable. None for
            deterministic effects or unknown sources.
        mode: Enforcement mode in effect when decision was made.
            Determines how non-deterministic effects are handled.
        decision: The enforcement outcome. One of:
            - "allowed": Effect permitted to execute
            - "blocked": Effect blocked from executing (raises exception)
            - "warned": Effect permitted with warning logged
            - "mocked": Effect stubbed with deterministic mock
        reason: Human-readable explanation for the decision.
            Useful for debugging and audit trails.
        timestamp: When the enforcement decision was made (UTC).
            Used for temporal correlation and debugging.
        mock_injected: Whether a mock value was injected. True when
            mode is MOCKED and effect was stubbed.
        original_value: The original value that would have been returned
            by the non-deterministic effect. None if not captured or
            if mock was proactive.
        mocked_value: The deterministic mock value that was injected.
            None if no mock was used.

    Example:
        >>> from datetime import datetime, timezone
        >>> from omnibase_core.enums.replay import (
        ...     EnumEffectDeterminism,
        ...     EnumEnforcementMode,
        ...     EnumNonDeterministicSource,
        ... )
        >>> decision = ModelEnforcementDecision(
        ...     effect_type="random.randint",
        ...     determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
        ...     source=EnumNonDeterministicSource.RANDOM,
        ...     mode=EnumEnforcementMode.STRICT,
        ...     decision="blocked",
        ...     reason="Random effects blocked in strict mode",
        ...     timestamp=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        ... )
        >>> decision.decision
        'blocked'

    Thread Safety:
        Thread-safe. Model is frozen (immutable) after creation.

    .. versionadded:: 0.6.3
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    effect_type: str = Field(
        ...,
        description="Type identifier for the effect (e.g., 'http.get', 'time.now').",
    )
    determinism: EnumEffectDeterminism = Field(
        ...,
        description="Classification of the effect's determinism.",
    )
    source: EnumNonDeterministicSource | None = Field(
        default=None,
        description="Source of non-determinism if applicable.",
    )
    mode: EnumEnforcementMode = Field(
        ...,
        description="Enforcement mode in effect when decision was made.",
    )
    decision: EnforcementOutcome = Field(
        ...,
        description="Enforcement outcome: 'allowed', 'blocked', 'warned', or 'mocked'.",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation for the decision.",
    )
    timestamp: datetime = Field(
        ...,
        description="When the enforcement decision was made (UTC).",
    )
    mock_injected: bool = Field(
        default=False,
        description="Whether a mock value was injected.",
    )
    original_value: Any | None = Field(
        default=None,
        description="Original value from non-deterministic effect if captured.",
    )
    mocked_value: Any | None = Field(
        default=None,
        description="Deterministic mock value that was injected.",
    )
