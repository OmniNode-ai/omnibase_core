"""
ProtocolReplaySafetyEnforcer - Protocol for replay safety enforcement.

This protocol defines the interface for enforcing replay safety policies
on non-deterministic effects during pipeline execution.

Design:
    Uses dependency inversion - Core defines the interface, and implementations
    provide enforcement logic based on configurable modes (STRICT, WARN,
    PERMISSIVE, MOCKED).

Architecture:
    The enforcer integrates with the replay infrastructure to classify effects
    and enforce policies. During replay, non-deterministic effects are either
    blocked (STRICT), logged (WARN), allowed with audit (PERMISSIVE), or
    automatically mocked (MOCKED).

Usage:
    .. code-block:: python

        from omnibase_core.protocols.replay import ProtocolReplaySafetyEnforcer
        from omnibase_core.services.replay.service_replay_safety_enforcer import (
            ServiceReplaySafetyEnforcer,
        )
        from omnibase_core.enums.replay import EnumEnforcementMode

        # Create enforcer in strict mode for CI/testing
        enforcer: ProtocolReplaySafetyEnforcer = ServiceReplaySafetyEnforcer(
            mode=EnumEnforcementMode.STRICT
        )

        # Enforce policy on an effect
        decision = enforcer.enforce(
            effect_type="http.get",
            effect_metadata={"url": "https://api.example.com"},
        )

        if decision.decision == "blocked":
            raise RuntimeError(decision.reason)

Key Invariant:
    Enforcement mode determines behavior consistently across all effects.

Related:
    - OMN-1150: Replay Safety Enforcement
    - EnumEnforcementMode: Enforcement mode configuration
    - EnumEffectDeterminism: Effect determinism classification
    - EnumNonDeterministicSource: Source of non-determinism
    - ModelEnforcementDecision: Decision outcome model
    - ServiceReplaySafetyEnforcer: Default implementation

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["ProtocolReplaySafetyEnforcer"]

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
    from omnibase_core.enums.replay.enum_non_deterministic_source import (
        EnumNonDeterministicSource,
    )
    from omnibase_core.models.replay.model_enforcement_decision import (
        ModelEnforcementDecision,
    )
    from omnibase_core.types.type_json import JsonType


@runtime_checkable
class ProtocolReplaySafetyEnforcer(Protocol):
    """
    Protocol for replay safety enforcement.

    Defines the interface for enforcing replay safety policies on effects
    during pipeline execution. Implementations classify effects and apply
    enforcement actions based on the configured mode.

    Enforcement Modes:
        - STRICT: Raise exception on non-deterministic effect
        - WARN: Log warning but continue execution
        - PERMISSIVE: Allow with audit trail
        - MOCKED: Inject deterministic mocks automatically

    Thread Safety:
        Implementations should be thread-safe for the classification methods.
        The audit trail may require synchronization for concurrent access.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.replay import ProtocolReplaySafetyEnforcer

            class MockEnforcer:
                '''Test implementation that allows everything.'''

                def classify_effect(
                    self,
                    effect_type: str,
                    effect_metadata: dict[str, JsonType] | None = None,
                ) -> tuple[EnumEffectDeterminism, EnumNonDeterministicSource | None]:
                    return EnumEffectDeterminism.DETERMINISTIC, None

                def enforce(
                    self,
                    effect_type: str,
                    effect_metadata: dict[str, JsonType] | None = None,
                ) -> ModelEnforcementDecision:
                    ...

                def get_mock_value(
                    self,
                    source: EnumNonDeterministicSource,
                ) -> Any:
                    return None

                def get_audit_trail(self) -> list[ModelEnforcementDecision]:
                    return []

                def reset(self) -> None:
                    pass

            # Verify protocol compliance
            enforcer: ProtocolReplaySafetyEnforcer = MockEnforcer()
            assert isinstance(enforcer, ProtocolReplaySafetyEnforcer)

    .. versionadded:: 0.6.3
    """

    def classify_effect(
        self,
        effect_type: str,
        effect_metadata: dict[str, JsonType] | None = None,
    ) -> tuple[EnumEffectDeterminism, EnumNonDeterministicSource | None]:
        """
        Classify an effect as deterministic or non-deterministic.

        Analyzes the effect type and metadata to determine if the effect
        is deterministic (same input -> same output) or non-deterministic.

        Args:
            effect_type: Type identifier for the effect (e.g., "http.get",
                "time.now", "random.randint").
            effect_metadata: Optional metadata about the effect for more
                precise classification.

        Returns:
            tuple[EnumEffectDeterminism, EnumNonDeterministicSource | None]:
                A tuple of (determinism classification, source of non-determinism).
                The source is None for deterministic or unknown effects.

        Example:
            .. code-block:: python

                determinism, source = enforcer.classify_effect("time.now")
                # Returns (EnumEffectDeterminism.NON_DETERMINISTIC,
                #          EnumNonDeterministicSource.TIME)

                determinism, source = enforcer.classify_effect("compute.hash")
                # Returns (EnumEffectDeterminism.DETERMINISTIC, None)
        """
        ...

    def enforce(
        self,
        effect_type: str,
        effect_metadata: dict[str, JsonType] | None = None,
    ) -> ModelEnforcementDecision:
        """
        Enforce replay safety policy for an effect.

        Classifies the effect and applies the enforcement policy based on
        the configured mode. Returns a decision about whether the effect
        is allowed, blocked, warned, or mocked.

        Args:
            effect_type: Type identifier for the effect.
            effect_metadata: Optional metadata about the effect.

        Returns:
            ModelEnforcementDecision: The enforcement decision with action,
                reason, and any mock values if applicable.

        Example:
            .. code-block:: python

                decision = enforcer.enforce("http.get", {"url": "..."})
                if decision.decision == "blocked":
                    raise RuntimeError(decision.reason)
                elif decision.decision == "mocked":
                    result = decision.mocked_value
        """
        ...

    def get_mock_value(
        self,
        source: EnumNonDeterministicSource,
    ) -> Any:
        """
        Get mocked value for a non-deterministic source.

        Returns a deterministic mock value appropriate for the source type.
        Used when mode is MOCKED to provide reproducible values.

        Args:
            source: The source of non-determinism to mock.

        Returns:
            Any: A deterministic mock value appropriate for the source.
                - TIME: Returns datetime from time injector
                - RANDOM: Returns float from RNG injector
                - UUID: Returns UUID from UUID injector
                - NETWORK: Returns empty dict (requires effect recorder)
                - DATABASE: Returns empty dict (requires effect recorder)
                - FILESYSTEM: Returns empty string
                - ENVIRONMENT: Returns empty string

        Example:
            .. code-block:: python

                mock_time = enforcer.get_mock_value(
                    EnumNonDeterministicSource.TIME
                )
                # Returns datetime from time injector
        """
        ...

    def get_audit_trail(self) -> list[ModelEnforcementDecision]:
        """
        Get all enforcement decisions made.

        Returns a copy of the audit trail containing all enforcement
        decisions made during this session. Useful for debugging and
        compliance auditing.

        Returns:
            list[ModelEnforcementDecision]: Copy of all enforcement decisions.

        Example:
            .. code-block:: python

                decisions = enforcer.get_audit_trail()
                blocked = [d for d in decisions if d.decision == "blocked"]
                print(f"Blocked {len(blocked)} non-deterministic effects")
        """
        ...

    def reset(self) -> None:
        """
        Reset enforcer state for new replay session.

        Clears the audit trail and resets any internal state. Call this
        before starting a new replay session to ensure clean state.

        Example:
            .. code-block:: python

                enforcer.reset()
                # Start new replay session with clean state
        """
        ...
