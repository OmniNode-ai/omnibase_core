"""Enumeration for pattern learning lifecycle states.

Defines the lifecycle stages for learned patterns in the OmniNode intelligence
system. These states gate injection eligibility - injectors MUST check
lifecycle_state before using patterns in manifest injection.

Lifecycle Flow:
    CANDIDATE -> PROVISIONAL -> VALIDATED -> DEPRECATED
                     |              |
                     +-> DEPRECATED <+

Patterns progress through validation stages before being eligible for
production use. Deprecated patterns are retained for historical analysis
but excluded from injection.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumPatternLifecycleState"]


@unique
class EnumPatternLifecycleState(StrValueHelper, str, Enum):
    """Lifecycle states for learned patterns.

    These states gate injection eligibility - injectors MUST check
    lifecycle_state before using patterns. Only VALIDATED patterns
    should be used in production manifest injection.

    State Transitions::

        CANDIDATE --[initial validation]--> PROVISIONAL
        PROVISIONAL --[observation period]--> VALIDATED
        PROVISIONAL --[validation fails]--> DEPRECATED
        VALIDATED --[no longer relevant]--> DEPRECATED

    Injection Eligibility:
        - CANDIDATE: Not eligible (too new, unvalidated)
        - PROVISIONAL: Limited eligibility (testing/staging only)
        - VALIDATED: Full eligibility (production use)
        - DEPRECATED: Not eligible (excluded from injection)

    Example:
        .. code-block:: python

            from omnibase_core.enums.pattern_learning import EnumPatternLifecycleState

            pattern_state = EnumPatternLifecycleState.VALIDATED

            # Check injection eligibility
            if pattern_state == EnumPatternLifecycleState.VALIDATED:
                apply_pattern_to_manifest(pattern)
            elif pattern_state == EnumPatternLifecycleState.PROVISIONAL:
                # Only in staging
                if is_staging_environment():
                    apply_pattern_to_manifest(pattern)

    .. versionadded:: 0.9.8
    """

    CANDIDATE = "candidate"
    """Newly discovered pattern, not yet validated.

    Patterns enter this state when first extracted from successful workflows.
    They require initial validation before progressing to PROVISIONAL.
    """

    PROVISIONAL = "provisional"
    """Passed initial validation, under observation.

    Patterns in this state have passed basic validation checks but are still
    being monitored for false positives and effectiveness. May be used in
    testing/staging environments only.
    """

    VALIDATED = "validated"
    """Fully validated, safe for production use.

    Patterns in this state have passed all validation gates and the
    observation period. They are eligible for production manifest injection.
    """

    DEPRECATED = "deprecated"
    """No longer recommended, excluded from injection.

    Patterns enter this state when they are superseded, cause issues,
    or are no longer relevant. They are retained for historical analysis
    but excluded from injection workflows.
    """
