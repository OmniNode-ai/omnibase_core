"""
EnumEffectDeterminism - Effect determinism classification enum for replay.

This module provides the EnumEffectDeterminism enum that classifies effects
based on their determinism characteristics for replay safety enforcement.

Design:
    Three classification levels capture effect determinism:
    - DETERMINISTIC: Effect always produces same output for same input
    - NON_DETERMINISTIC: Effect may produce different outputs for same input
    - UNKNOWN: Effect determinism cannot be determined statically

Usage:
    .. code-block:: python

        from omnibase_core.enums.replay import EnumEffectDeterminism

        # Pure computation effects are deterministic
        determinism = EnumEffectDeterminism.DETERMINISTIC

        # Network calls are non-deterministic
        determinism = EnumEffectDeterminism.NON_DETERMINISTIC

        # Unclassified effects default to unknown
        determinism = EnumEffectDeterminism.UNKNOWN

Related:
    - OMN-1150: Replay Safety Enforcement
    - EnumEnforcementMode: How to handle non-deterministic effects
    - EnumNonDeterministicSource: Source of non-determinism
    - ModelEnforcementDecision: Decision outcome model

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["EnumEffectDeterminism"]

from enum import Enum


class EnumEffectDeterminism(str, Enum):
    """
    Effect determinism classification.

    Classifies effects based on whether they produce consistent outputs
    for the same inputs across different executions.

    Values:
        DETERMINISTIC: Effect always produces same output for same input.
            Examples: Pure computations, cached lookups, static data reads.
        NON_DETERMINISTIC: Effect may produce different outputs for same input.
            Examples: Network calls, random number generation, time-based logic.
        UNKNOWN: Effect determinism cannot be determined statically.
            Used when classification requires runtime analysis or is not yet
            implemented for a particular effect type.

    Example:
        >>> from omnibase_core.enums.replay import EnumEffectDeterminism
        >>> determinism = EnumEffectDeterminism.DETERMINISTIC
        >>> determinism.value
        'deterministic'
        >>> determinism == EnumEffectDeterminism.NON_DETERMINISTIC
        False

    .. versionadded:: 0.6.3
    """

    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non_deterministic"
    UNKNOWN = "unknown"
