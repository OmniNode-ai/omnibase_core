"""
Reserved enum validation for NodeOrchestrator v1.0 contract.

Validates that reserved enum values are not used in v1.0.
Per CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md:
- CONDITIONAL and STREAMING execution modes MUST raise ModelOnexError
- PAUSED workflow state is reserved for v1.1+ (documented but not enforced)

Repository Boundaries (v1.0.5 Informative):
    This module is part of omnibase_core (Core layer) and follows the ONEX
    repository boundary rules:

    SPI -> Core -> Infra (dependency direction)

    - **SPI (Service Provider Interface)**: Parses YAML contracts and generates
      typed Pydantic models. Reserved fields are parsed and preserved during
      contract codegen.

    - **Core (this module)**: Receives fully typed models from SPI/Infra.
      Reserved fields are preserved in typed models. Validation functions
      reject reserved execution modes with ModelOnexError.

    - **Infra (Infrastructure)**: Executes workflows using Core utilities.
      Reserved fields are ignored deterministically by the executor.

    This module provides validation that Core uses to reject reserved modes
    before execution reaches the Infra layer.

Reserved Fields Global Rule (v1.0.4 Normative):
    Any field marked as reserved for v1.1 or later:
    - MUST be parsed by SPI during contract codegen
    - MUST be preserved by Core in typed models
    - MUST be ignored by executor deterministically
    - MUST NOT alter runtime behavior in v1.0 even if set
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "validate_execution_mode",
    "RESERVED_EXECUTION_MODES",
]

# Reserved execution modes (not accepted in v1.0)
RESERVED_EXECUTION_MODES = frozenset(
    {
        EnumExecutionMode.CONDITIONAL,
        EnumExecutionMode.STREAMING,
    }
)


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


# Note on EnumWorkflowStatus.PAUSED:
# ===================================
# Per CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md, EnumWorkflowStatus.PAUSED is reserved
# for v1.1+ but is NOT actively rejected in v1.0. The enum value exists in the type
# system for forward compatibility, but the executor does not implement pause/resume
# semantics. If PAUSED state is encountered:
#
# - It will be parsed and preserved by the type system
# - It will NOT cause validation errors
# - Executor behavior is undefined (treat as informational only)
#
# Reserved Fields Global Rule (v1.0.4 Normative) - Applied to PAUSED:
# =====================================================================
# Per the global normative rule for reserved fields:
#
# 1. MUST be parsed by SPI: The enum value exists and is parseable from YAML/JSON.
#    SPI parses "paused" string into EnumWorkflowStatus.PAUSED during contract codegen.
#
# 2. MUST be preserved by Core: Typed models preserve the PAUSED value in their fields.
#    Core does not strip or convert reserved values - they flow through unchanged.
#
# 3. MUST be ignored by executor deterministically: Workflow executor treats PAUSED
#    as informational metadata only. It does NOT trigger pause/resume behavior in v1.0.
#    The executor continues execution normally regardless of this state value.
#
# 4. MUST NOT alter runtime behavior in v1.0: Even if set, PAUSED has zero effect
#    on workflow execution, step ordering, or action emission in v1.0.
#
# Decision: Accept with warning vs reject is deferred to future ticket if needed.
# Current implementation: No active validation (parse-only, no runtime enforcement).
