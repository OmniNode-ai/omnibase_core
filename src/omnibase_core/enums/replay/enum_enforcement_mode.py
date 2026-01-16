"""
EnumEnforcementMode - Enforcement mode enum for replay safety infrastructure.

This module provides the EnumEnforcementMode enum that determines how the
replay safety enforcer handles non-deterministic effects during replay.

Design:
    Four enforcement modes support different execution contexts:
    - STRICT: Raise exception on non-deterministic effect (ideal for CI/testing)
    - WARN: Log warning but continue execution (useful for gradual migration)
    - PERMISSIVE: Allow with audit trail (for production monitoring)
    - MOCKED: Inject deterministic mocks automatically (for testing)

Usage:
    .. code-block:: python

        from omnibase_core.enums.replay import EnumEnforcementMode

        # Strict mode for CI/testing - fails on non-deterministic effects
        mode = EnumEnforcementMode.STRICT

        # Warning mode for gradual migration
        mode = EnumEnforcementMode.WARN

        # Permissive mode with audit trail
        mode = EnumEnforcementMode.PERMISSIVE

        # Mock mode for testing - automatically injects mocks
        mode = EnumEnforcementMode.MOCKED

Related:
    - OMN-1150: Replay Safety Enforcement
    - EnumEffectDeterminism: Classification of effect determinism
    - EnumNonDeterministicSource: Source of non-determinism
    - ModelEnforcementDecision: Decision outcome model

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["EnumEnforcementMode"]

from enum import Enum


class EnumEnforcementMode(str, Enum):
    """
    Enforcement mode for replay safety.

    Determines how the enforcer handles non-deterministic effects during replay.

    Values:
        STRICT: Raise exception on non-deterministic effect. Use in CI/testing
            environments where determinism is required.
        WARN: Log warning but continue execution. Use during gradual migration
            to replay safety or for monitoring purposes.
        PERMISSIVE: Allow with audit trail. Use in production when full
            determinism cannot be guaranteed but audit is needed.
        MOCKED: Inject deterministic mocks automatically. Use in testing
            to automatically stub non-deterministic effects.

    Example:
        >>> from omnibase_core.enums.replay import EnumEnforcementMode
        >>> mode = EnumEnforcementMode.STRICT
        >>> mode.value
        'strict'
        >>> mode == EnumEnforcementMode.STRICT
        True

    .. versionadded:: 0.6.3
    """

    STRICT = "strict"
    WARN = "warn"
    PERMISSIVE = "permissive"
    MOCKED = "mocked"
