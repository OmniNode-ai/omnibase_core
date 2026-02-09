"""Enumeration for evidence quality tiers in pattern learning.

Defines the evidence quality levels that gate pattern promotion in the
OmniNode intelligence system. Patterns MUST accumulate sufficient evidence
at each tier before being promoted to the next lifecycle state.

Evidence Tier Ordering (lowest to highest):
    UNMEASURED < OBSERVED < MEASURED < VERIFIED

Higher tiers require more rigorous evidence collection. Promotion decisions
MUST check evidence_tier to determine whether a pattern has sufficient
backing for its current lifecycle state.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumEvidenceTier"]

# Numeric weights for tier ordering (higher = stronger evidence)
_TIER_WEIGHTS: dict[str, int] = {
    "unmeasured": 0,
    "observed": 10,
    "measured": 20,
    "verified": 30,
}


@unique
class EnumEvidenceTier(StrValueHelper, str, Enum):
    """Evidence quality tiers for learned pattern promotion.

    Gates evidence-based promotion in the pattern lifecycle. Each tier
    represents a progressively stronger level of empirical backing for
    a learned pattern.

    Tier Progression::

        UNMEASURED --[first observation]--> OBSERVED
        OBSERVED --[quantitative data]--> MEASURED
        MEASURED --[independent validation]--> VERIFIED

    Promotion Eligibility:
        - UNMEASURED: No evidence collected yet (default for new patterns)
        - OBSERVED: Anecdotal evidence from workflow executions
        - MEASURED: Quantitative metrics (success rate, latency impact, etc.)
        - VERIFIED: Independently validated through controlled experiments

    Ordering:
        Tiers support comparison operators for threshold checks::

            if pattern.evidence_tier >= EnumEvidenceTier.MEASURED:
                allow_production_promotion(pattern)

    Example:
        .. code-block:: python

            from omnibase_core.enums.pattern_learning import EnumEvidenceTier

            tier = EnumEvidenceTier.OBSERVED

            # Threshold check using ordering
            if tier >= EnumEvidenceTier.MEASURED:
                promote_pattern(pattern)
            else:
                schedule_measurement(pattern)

            # Direct comparison
            assert EnumEvidenceTier.UNMEASURED < EnumEvidenceTier.OBSERVED
            assert EnumEvidenceTier.OBSERVED < EnumEvidenceTier.MEASURED
            assert EnumEvidenceTier.MEASURED < EnumEvidenceTier.VERIFIED

    .. versionadded:: 0.13.2
    """

    UNMEASURED = "unmeasured"
    """No evidence collected yet.

    Default tier for newly discovered patterns. The pattern has been
    identified but no empirical data supports its effectiveness.
    """

    OBSERVED = "observed"
    """Anecdotal evidence from workflow executions.

    The pattern has been observed in successful workflows but lacks
    quantitative measurement. Sufficient for CANDIDATE lifecycle state.
    """

    MEASURED = "measured"
    """Quantitative metrics collected.

    The pattern has measurable data (success rate, latency impact,
    error reduction, etc.). Sufficient for PROVISIONAL lifecycle state.
    """

    VERIFIED = "verified"
    """Independently validated through controlled experiments.

    The pattern has been verified through A/B testing, controlled
    rollouts, or independent reproduction. Required for VALIDATED
    lifecycle state in production.
    """

    def get_numeric_value(self) -> int:
        """Return numeric weight for tier ordering (higher = stronger evidence)."""
        return _TIER_WEIGHTS[self.value]

    def __lt__(self, other: str) -> bool:
        """Enable evidence tier comparison."""
        if isinstance(other, EnumEvidenceTier):
            return self.get_numeric_value() < other.get_numeric_value()
        return super().__lt__(other)

    def __le__(self, other: str) -> bool:
        """Enable evidence tier comparison."""
        if isinstance(other, EnumEvidenceTier):
            return self.get_numeric_value() <= other.get_numeric_value()
        return super().__le__(other)

    def __gt__(self, other: str) -> bool:
        """Enable evidence tier comparison."""
        if isinstance(other, EnumEvidenceTier):
            return self.get_numeric_value() > other.get_numeric_value()
        return super().__gt__(other)

    def __ge__(self, other: str) -> bool:
        """Enable evidence tier comparison."""
        if isinstance(other, EnumEvidenceTier):
            return self.get_numeric_value() >= other.get_numeric_value()
        return super().__ge__(other)
