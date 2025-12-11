"""
Reserved enum validation for NodeOrchestrator v1.0 contract.

Validates that reserved enum values are not used in v1.0.
Per CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md:
- CONDITIONAL and STREAMING execution modes MUST raise ModelOnexError
- PAUSED workflow state is reserved for v1.1+ (documented but not enforced)
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "validate_execution_mode",
    "RESERVED_EXECUTION_MODES",
]

# Reserved execution modes (not accepted in v1.0)
RESERVED_EXECUTION_MODES = {
    EnumExecutionMode.CONDITIONAL,
    EnumExecutionMode.STREAMING,
}


def validate_execution_mode(mode: EnumExecutionMode) -> None:
    """
    Validate execution mode is not reserved for future versions.

    Use this function when you have an EnumExecutionMode instance (type-safe).
    For raw string input (e.g., from YAML config), use validate_execution_mode_string
    from workflow_validator instead.

    Per NodeOrchestrator v1.0 contract:
    - SEQUENTIAL, PARALLEL, BATCH are accepted
    - CONDITIONAL is reserved for v1.1 (NOT accepted in v1.0)
    - STREAMING is reserved for v1.2 (NOT accepted in v1.0)

    Args:
        mode: The execution mode to validate (EnumExecutionMode instance)

    Raises:
        ModelOnexError: If mode is CONDITIONAL or STREAMING (reserved in v1.0)
            - error_code: EnumCoreErrorCode.VALIDATION_ERROR
            - context: {"mode": mode.value, "reserved_modes": [...]}

    See Also:
        validate_execution_mode_string: For raw string input validation

    Example:
        >>> from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
        >>> validate_execution_mode(EnumExecutionMode.SEQUENTIAL)  # OK
        >>> validate_execution_mode(EnumExecutionMode.PARALLEL)    # OK
        >>> validate_execution_mode(EnumExecutionMode.BATCH)       # OK
        >>> validate_execution_mode(EnumExecutionMode.CONDITIONAL) # Raises!
        Traceback (most recent call last):
            ...
        ModelOnexError: Execution mode 'conditional' is reserved for v1.1+ and not accepted in v1.0
    """
    if mode in RESERVED_EXECUTION_MODES:
        version_mapping = {
            EnumExecutionMode.CONDITIONAL: "v1.1+",
            EnumExecutionMode.STREAMING: "v1.2+",
        }
        version = version_mapping.get(mode, "future versions")

        raise ModelOnexError(
            message=f"Execution mode '{mode.value}' is reserved for {version} and not accepted in v1.0",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            mode=mode.value,
            reserved_modes=[m.value for m in RESERVED_EXECUTION_MODES],
            accepted_modes=["sequential", "parallel", "batch"],
            version=version,
        )


# Note on EnumWorkflowState.PAUSED:
# ===================================
# Per CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md, EnumWorkflowState.PAUSED is reserved
# for v1.1+ but is NOT actively rejected in v1.0. The enum value exists in the type
# system for forward compatibility, but the executor does not implement pause/resume
# semantics. If PAUSED state is encountered:
#
# - It will be parsed and preserved by the type system
# - It will NOT cause validation errors
# - Executor behavior is undefined (treat as informational only)
#
# This aligns with Reserved Semantics Rule (v1.0.4):
# - MUST be parsed and preserved
# - MUST NOT influence validation in v1.0
# - MUST be ignored deterministically by executor
#
# Decision: Accept with warning vs reject is deferred to future ticket if needed.
# Current implementation: No active validation (parse-only, no runtime enforcement).
