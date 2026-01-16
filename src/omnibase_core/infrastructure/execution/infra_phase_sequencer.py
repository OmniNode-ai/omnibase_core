"""
Phase Sequencer for Runtime Execution Sequencing.

This module provides functions for converting execution profiles and handler
mappings into executable plans. It validates phase list integrity and enforces
canonical phase ordering.

Purity Constraints
------------------
Most functions in this module are PURE (no side effects, deterministic output
for same input, no global state modification). However, functions that create
execution plans (``create_execution_plan``, ``create_empty_execution_plan``,
``create_default_execution_plan``) use the current timestamp by default.

To achieve pure/deterministic behavior with these functions, provide an explicit
``created_at`` parameter:

.. code-block:: python

    # Impure (uses current time)
    plan = create_execution_plan(profile, mapping)

    # Pure (deterministic)
    plan = create_execution_plan(profile, mapping, created_at=fixed_timestamp)

Thread Safety
-------------
All functions in this module are stateless, making them inherently thread-safe.
The returned ModelExecutionPlan and ModelPhaseStep instances are frozen Pydantic
models that can be safely shared across threads.

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)
from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep


def get_canonical_phase_order() -> list[EnumHandlerExecutionPhase]:
    """
    Return the canonical execution phase order.

    The canonical order is: PREFLIGHT -> BEFORE -> EXECUTE -> AFTER -> EMIT -> FINALIZE

    This function provides a single source of truth for phase ordering
    across the codebase.

    Returns:
        List of EnumHandlerExecutionPhase in canonical order

    Example:
        >>> phases = get_canonical_phase_order()
        >>> phases[0]
        <EnumHandlerExecutionPhase.PREFLIGHT: 'preflight'>
        >>> phases[-1]
        <EnumHandlerExecutionPhase.FINALIZE: 'finalize'>
    """
    return EnumHandlerExecutionPhase.get_ordered_phases()


@standard_error_handling("Phase list validation")
def validate_phase_list(phases: list[str] | tuple[str, ...]) -> bool:
    """
    Validate that a phase list contains valid canonical phases in correct order.

    A valid phase list must:
    1. Contain only valid phase names (preflight, before, execute, after, emit, finalize)
    2. Be a contiguous subsequence of the canonical order
    3. Maintain relative ordering (no phase appears before a phase it should follow)

    Args:
        phases: List of phase names to validate

    Returns:
        True if the phase list is valid, False otherwise

    Example:
        >>> validate_phase_list(["preflight", "before", "execute"])
        True
        >>> validate_phase_list(["execute", "before"])  # Wrong order
        False
        >>> validate_phase_list(["invalid_phase"])  # Invalid phase
        False
        >>> validate_phase_list([])  # Empty is valid
        True
    """
    if not phases:
        return True

    canonical_order = get_canonical_phase_order()
    canonical_strings = [p.value for p in canonical_order]

    # Convert strings to check validity and order
    last_index = -1
    for phase_str in phases:
        phase_lower = phase_str.lower()
        if phase_lower not in canonical_strings:
            return False

        current_index = canonical_strings.index(phase_lower)
        if current_index <= last_index:
            # Phase appears out of order (duplicate or wrong sequence)
            return False
        last_index = current_index

    return True


@standard_error_handling("Strict phase list validation")
def validate_phase_list_strict(
    phases: list[str] | tuple[str, ...],
) -> tuple[bool, str | None]:
    """
    Validate phase list with detailed error message.

    Like validate_phase_list but returns a detailed error message on failure.

    Args:
        phases: List of phase names to validate

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.

    Example:
        >>> is_valid, error = validate_phase_list_strict(["execute", "before"])
        >>> is_valid
        False
        >>> error
        "Phase 'before' appears after 'execute' but should come before it"
    """
    if not phases:
        return True, None

    canonical_order = get_canonical_phase_order()
    canonical_strings = [p.value for p in canonical_order]

    # First pass: check all phases are valid
    for phase_str in phases:
        phase_lower = phase_str.lower()
        if phase_lower not in canonical_strings:
            return (
                False,
                f"Invalid phase '{phase_str}'. Valid phases are: {canonical_strings}",
            )

    # Second pass: check ordering
    last_index = -1
    last_phase = None
    for phase_str in phases:
        phase_lower = phase_str.lower()
        current_index = canonical_strings.index(phase_lower)

        if current_index < last_index:
            return (
                False,
                f"Phase '{phase_str}' appears after '{last_phase}' but should come before it",
            )
        if current_index == last_index:
            return False, f"Duplicate phase '{phase_str}' in phase list"

        last_index = current_index
        last_phase = phase_str

    return True, None


@standard_error_handling("Handler grouping by phase")
def group_handlers_by_phase(
    handler_phase_mapping: dict[str, EnumHandlerExecutionPhase],
) -> dict[EnumHandlerExecutionPhase, list[str]]:
    """
    Group handlers by their assigned execution phase.

    Takes a mapping of handler_id -> phase and groups them into
    a mapping of phase -> list[handler_id].

    Args:
        handler_phase_mapping: Mapping of handler_id to their assigned phase

    Returns:
        Dict mapping each phase to list of handler IDs in that phase

    Example:
        >>> mapping = {
        ...     "h1": EnumHandlerExecutionPhase.EXECUTE,
        ...     "h2": EnumHandlerExecutionPhase.BEFORE,
        ...     "h3": EnumHandlerExecutionPhase.EXECUTE,
        ... }
        >>> grouped = group_handlers_by_phase(mapping)
        >>> sorted(grouped[EnumHandlerExecutionPhase.EXECUTE])
        ['h1', 'h3']
    """
    result: dict[EnumHandlerExecutionPhase, list[str]] = defaultdict(list)

    for handler_id, phase in handler_phase_mapping.items():
        result[phase].append(handler_id)

    return dict(result)


@standard_error_handling("Handler ordering in phase")
def order_handlers_in_phase(
    handlers: list[str],
    policy: ModelExecutionOrderingPolicy | None = None,
) -> list[str]:
    """
    Apply ordering policy to handlers within a phase.

    Orders handlers according to the specified policy. If no policy is provided,
    uses default ordering (alphabetical for determinism).

    Args:
        handlers: List of handler IDs to order
        policy: Optional ordering policy to apply

    Returns:
        Ordered list of handler IDs

    Example:
        >>> handlers = ["z_handler", "a_handler", "m_handler"]
        >>> order_handlers_in_phase(handlers)
        ['a_handler', 'm_handler', 'z_handler']
    """
    if not handlers:
        return []

    # Make a copy to avoid mutating input
    handlers_copy = list(handlers)

    if policy is None:
        # Default: alphabetical for determinism
        return sorted(handlers_copy)

    # Apply tie-breakers in order
    # Currently, we only support alphabetical ordering as the base
    # Priority-based ordering would require additional handler metadata
    #
    # Note: Alphabetical sort is ALWAYS applied as a final fallback to ensure
    # deterministic ordering, regardless of whether the policy explicitly
    # includes "alphabetical" in tie_breakers. This prevents non-deterministic
    # iteration order from dict keys from affecting the output.
    #
    # For topological_sort strategy, we would need dependency information
    # which is not available at this level. The current implementation
    # uses alphabetical as the fallback for determinism.

    handlers_copy.sort()
    return handlers_copy


@standard_error_handling("Execution plan creation")
def create_execution_plan(
    profile: ModelExecutionProfile,
    handler_phase_mapping: dict[str, EnumHandlerExecutionPhase],
    ordering_policy: ModelExecutionOrderingPolicy | None = None,
    created_at: datetime | None = None,
) -> ModelExecutionPlan:
    """
    Convert execution profile and handler mappings into an execution plan.

    This is the main entry point for creating execution plans. It:
    1. Validates the profile's phase list
    2. Groups handlers by phase
    3. Orders handlers within each phase according to policy
    4. Creates an immutable ModelExecutionPlan

    This function is PURE when ``created_at`` is provided: same inputs always
    produce same output. When ``created_at`` is None, uses current time as
    the default.

    Args:
        profile: The execution profile defining phases and ordering policy
        handler_phase_mapping: Mapping of handler_id -> phase they belong to
        ordering_policy: Optional ordering policy override (uses profile's policy if None)
        created_at: Optional timestamp for the plan creation. If None, uses
            ``datetime.now(UTC)``. Providing an explicit value enables
            deterministic/pure behavior for testing.

    Returns:
        ModelExecutionPlan with ordered phases and handlers

    Raises:
        ModelOnexError: If phase list validation fails

    Example:
        >>> from omnibase_core.models.contracts.model_execution_profile import ModelExecutionProfile
        >>> profile = ModelExecutionProfile()
        >>> mapping = {
        ...     "validate_handler": EnumHandlerExecutionPhase.PREFLIGHT,
        ...     "process_handler": EnumHandlerExecutionPhase.EXECUTE,
        ... }
        >>> plan = create_execution_plan(profile, mapping)
        >>> plan.total_handlers()
        2
    """
    # Validate phase list
    is_valid, error_msg = validate_phase_list_strict(profile.phases)
    if not is_valid:
        raise ModelOnexError(
            message=f"Invalid execution profile phase list: {error_msg}",
            error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            context={"phases": profile.phases, "validation_error": error_msg},
        )

    # Determine ordering policy
    effective_policy = ordering_policy or profile.ordering_policy

    # Group handlers by phase
    handlers_by_phase = group_handlers_by_phase(handler_phase_mapping)

    # Build phase steps in canonical order
    phase_steps: list[ModelPhaseStep] = []
    canonical_order = get_canonical_phase_order()

    # Only include phases that are in the profile's phase list
    profile_phases_lower = {p.lower() for p in profile.phases}

    for phase_enum in canonical_order:
        if phase_enum.value not in profile_phases_lower:
            continue

        # Get handlers for this phase
        handlers = handlers_by_phase.get(phase_enum, [])

        # Order handlers according to policy
        ordered_handlers = order_handlers_in_phase(handlers, effective_policy)

        # Create phase step
        # Note: Empty phases (with no handlers) are intentionally included in the plan.
        # This provides visibility into all configured phases and enables phase-level
        # hooks/callbacks even when no handlers are registered for that phase.
        step = ModelPhaseStep(
            phase=phase_enum,
            handler_ids=ordered_handlers,
            ordering_rationale=_generate_ordering_rationale(effective_policy),
        )
        phase_steps.append(step)

    # Use provided timestamp or current time as default
    effective_created_at = created_at if created_at is not None else datetime.now(UTC)

    # Create and return the execution plan
    return ModelExecutionPlan(
        phases=phase_steps,
        source_profile=_get_profile_identifier(profile),
        ordering_policy=effective_policy.strategy if effective_policy else "default",
        created_at=effective_created_at,
    )


def _generate_ordering_rationale(
    policy: ModelExecutionOrderingPolicy | None,
) -> str:
    """
    Generate a human-readable rationale for the ordering applied.

    Args:
        policy: The ordering policy used

    Returns:
        Human-readable description of the ordering strategy
    """
    if policy is None:
        return "Default alphabetical ordering for determinism"

    parts = [f"Strategy: {policy.strategy}"]
    if policy.tie_breakers:
        parts.append(f"Tie-breakers: {', '.join(policy.tie_breakers)}")
    if policy.deterministic_seed:
        parts.append("Deterministic: yes")

    return "; ".join(parts)


def _get_profile_identifier(profile: ModelExecutionProfile) -> str:
    """
    Get an identifier string for the profile.

    Args:
        profile: The execution profile

    Returns:
        Identifier string based on profile configuration
    """
    # Generate identifier from phases (first and last) and policy
    if profile.phases:
        phases_summary = f"{profile.phases[0]}..{profile.phases[-1]}"
    else:
        phases_summary = "empty"

    return f"profile({phases_summary},{profile.ordering_policy.strategy})"


def create_empty_execution_plan(
    source_profile: str | None = None,
    created_at: datetime | None = None,
) -> ModelExecutionPlan:
    """
    Create an empty execution plan with no phases or handlers.

    Useful for representing a null/empty state or for testing.

    This function is PURE when ``created_at`` is provided: same inputs always
    produce same output. When ``created_at`` is None, uses current time as
    the default.

    Args:
        source_profile: Optional identifier for the source profile
        created_at: Optional timestamp for the plan creation. If None, uses
            ``datetime.now(UTC)``. Providing an explicit value enables
            deterministic/pure behavior for testing.

    Returns:
        Empty ModelExecutionPlan

    Example:
        >>> plan = create_empty_execution_plan()
        >>> plan.is_empty()
        True
        >>> plan.total_handlers()
        0
    """
    effective_created_at = created_at if created_at is not None else datetime.now(UTC)
    return ModelExecutionPlan(
        phases=[],
        source_profile=source_profile or "empty",
        ordering_policy="none",
        created_at=effective_created_at,
    )


def create_default_execution_plan(
    handler_phase_mapping: dict[str, EnumHandlerExecutionPhase],
    created_at: datetime | None = None,
) -> ModelExecutionPlan:
    """
    Create an execution plan using default profile settings.

    Convenience function that uses DEFAULT_EXECUTION_PHASES and default
    ordering policy.

    This function is PURE when ``created_at`` is provided: same inputs always
    produce same output. When ``created_at`` is None, uses current time as
    the default.

    Args:
        handler_phase_mapping: Mapping of handler_id -> phase they belong to
        created_at: Optional timestamp for the plan creation. If None, uses
            ``datetime.now(UTC)``. Providing an explicit value enables
            deterministic/pure behavior for testing.

    Returns:
        ModelExecutionPlan with default settings

    Example:
        >>> mapping = {"h1": EnumHandlerExecutionPhase.EXECUTE}
        >>> plan = create_default_execution_plan(mapping)
        >>> plan.has_phase(EnumHandlerExecutionPhase.EXECUTE)
        True
    """
    profile = ModelExecutionProfile(
        phases=DEFAULT_EXECUTION_PHASES,
        ordering_policy=ModelExecutionOrderingPolicy(),
    )
    return create_execution_plan(profile, handler_phase_mapping, created_at=created_at)


def get_phases_for_handlers(
    handler_phase_mapping: dict[str, EnumHandlerExecutionPhase],
) -> list[EnumHandlerExecutionPhase]:
    """
    Get the unique phases that have handlers assigned, in canonical order.

    Args:
        handler_phase_mapping: Mapping of handler_id -> phase

    Returns:
        List of phases with assigned handlers, in canonical order

    Example:
        >>> mapping = {
        ...     "h1": EnumHandlerExecutionPhase.EXECUTE,
        ...     "h2": EnumHandlerExecutionPhase.BEFORE,
        ... }
        >>> phases = get_phases_for_handlers(mapping)
        >>> phases
        [<EnumHandlerExecutionPhase.BEFORE: 'before'>, <EnumHandlerExecutionPhase.EXECUTE: 'execute'>]
    """
    if not handler_phase_mapping:
        return []

    # Get unique phases
    unique_phases = set(handler_phase_mapping.values())

    # Return in canonical order
    canonical = get_canonical_phase_order()
    return [p for p in canonical if p in unique_phases]


# Export for use
__all__ = [
    "create_default_execution_plan",
    "create_empty_execution_plan",
    "create_execution_plan",
    "get_canonical_phase_order",
    "get_phases_for_handlers",
    "group_handlers_by_phase",
    "order_handlers_in_phase",
    "validate_phase_list",
    "validate_phase_list_strict",
]
