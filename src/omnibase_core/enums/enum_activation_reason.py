"""
Activation Reason Enum.

Defines the reasons why a capability or handler was activated or skipped
during pipeline execution. Used by the Execution Manifest to provide
explainability for activation decisions.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumActivationReason(StrValueHelper, str, Enum):
    """
    Reason for capability activation or skip.

    This enum provides explainability for why a capability or handler was
    activated or skipped during pipeline execution. It is used by the
    Execution Manifest activation summary to answer "why did this run?"
    or "why was this skipped?".

    Categories of reasons:

    **Activation reasons** (capability ran):
        - PREDICATE_TRUE: Predicate evaluated to true
        - ALWAYS_ACTIVE: No predicate, always runs
        - EXPLICITLY_ENABLED: Explicitly enabled by configuration
        - DEPENDENCY_SATISFIED: All dependencies were satisfied

    **Skip reasons** (capability did not run):
        - PREDICATE_FALSE: Predicate evaluated to false
        - DEPENDENCY_FAILED: Required dependency not satisfied
        - EXPLICITLY_DISABLED: Explicitly disabled by configuration
        - CAPABILITY_MISSING: Required capability not available
        - CONFLICT_DETECTED: Conflicts with another active capability
        - PHASE_MISMATCH: Not applicable to current execution phase
        - TIMEOUT_EXCEEDED: Activation window expired

    Example:
        >>> reason = EnumActivationReason.PREDICATE_TRUE
        >>> reason.value
        'predicate_true'
        >>> reason.is_activation_reason()
        True

        >>> skip = EnumActivationReason.PREDICATE_FALSE
        >>> skip.is_skip_reason()
        True

    See Also:
        - :class:`~omnibase_core.models.manifest.model_capability_activation.ModelCapabilityActivation`:
          Model that uses this enum to explain activation decisions
        - :class:`~omnibase_core.models.manifest.model_activation_summary.ModelActivationSummary`:
          Summary model aggregating activation decisions

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    # Activation reasons (capability ran)
    PREDICATE_TRUE = "predicate_true"
    """Predicate condition evaluated to true, enabling the capability."""

    ALWAYS_ACTIVE = "always_active"
    """No predicate defined; capability always runs."""

    EXPLICITLY_ENABLED = "explicitly_enabled"
    """Capability was explicitly enabled by configuration or contract."""

    DEPENDENCY_SATISFIED = "dependency_satisfied"
    """All required dependencies were satisfied, enabling activation."""

    # Skip reasons (capability did not run)
    PREDICATE_FALSE = "predicate_false"
    """Predicate condition evaluated to false, skipping the capability."""

    DEPENDENCY_FAILED = "dependency_failed"
    """Required dependency was not satisfied or failed."""

    EXPLICITLY_DISABLED = "explicitly_disabled"
    """Capability was explicitly disabled by configuration or contract."""

    CAPABILITY_MISSING = "capability_missing"
    """Required capability is not available in the registry."""

    CONFLICT_DETECTED = "conflict_detected"
    """Capability conflicts with another active capability."""

    PHASE_MISMATCH = "phase_mismatch"
    """Capability is not applicable to the current execution phase."""

    TIMEOUT_EXCEEDED = "timeout_exceeded"
    """Activation window expired before capability could be activated."""

    def is_activation_reason(self) -> bool:
        """
        Check if this reason indicates successful activation.

        Returns:
            True if this reason results in the capability being activated
        """
        return self in self.get_activation_reasons()

    def is_skip_reason(self) -> bool:
        """
        Check if this reason indicates the capability was skipped.

        Returns:
            True if this reason results in the capability being skipped
        """
        return not self.is_activation_reason()

    @classmethod
    def get_activation_reasons(cls) -> list["EnumActivationReason"]:
        """
        Get all reasons that result in activation.

        Returns:
            List of reasons that indicate successful activation
        """
        return [
            cls.PREDICATE_TRUE,
            cls.ALWAYS_ACTIVE,
            cls.EXPLICITLY_ENABLED,
            cls.DEPENDENCY_SATISFIED,
        ]

    @classmethod
    def get_skip_reasons(cls) -> list["EnumActivationReason"]:
        """
        Get all reasons that result in skipping.

        Returns:
            List of reasons that indicate the capability was skipped
        """
        return [
            cls.PREDICATE_FALSE,
            cls.DEPENDENCY_FAILED,
            cls.EXPLICITLY_DISABLED,
            cls.CAPABILITY_MISSING,
            cls.CONFLICT_DETECTED,
            cls.PHASE_MISMATCH,
            cls.TIMEOUT_EXCEEDED,
        ]


# Export for use
__all__ = ["EnumActivationReason"]
