# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline-specific exceptions."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class PipelineError(ModelOnexError):
    """Base exception for pipeline errors."""


class HookRegistryFrozenError(PipelineError):
    """Raised when attempting to modify a frozen registry."""

    def __init__(self, message: str = "Cannot modify frozen hook registry") -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.INVALID_STATE,
            message=message,
        )


class DuplicateHookError(PipelineError):
    """Raised when registering a hook with duplicate ID."""

    def __init__(self, hook_id: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            message=f"Hook with ID '{hook_id}' already registered",
            context={"hook_id": hook_id},
        )


class UnknownDependencyError(PipelineError):
    """Raised when a hook references an unknown dependency."""

    def __init__(self, hook_id: str, unknown_dep: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Hook '{hook_id}' references unknown dependency '{unknown_dep}'",
            context={
                "hook_id": hook_id,
                "unknown_dependency": unknown_dep,
                "validation_kind": "unknown_dependency",
            },
        )


class DependencyCycleError(PipelineError):
    """Raised when hook dependencies form a cycle."""

    def __init__(self, cycle: list[str]) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Dependency cycle detected: {' -> '.join(cycle)}",
            context={"cycle": cycle, "validation_kind": "dependency_cycle"},
        )


class HookTypeMismatchError(PipelineError):
    """Raised when hook type doesn't match contract type (when enforced)."""

    def __init__(
        self, hook_id: str, hook_category: str, contract_category: str
    ) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Hook '{hook_id}' category '{hook_category}' doesn't match contract category '{contract_category}'",
            context={
                "hook_id": hook_id,
                "hook_category": hook_category,
                "contract_category": contract_category,
                "validation_kind": "hook_type_mismatch",
            },
        )


class HookTimeoutError(PipelineError):
    """Raised when a hook exceeds its configured timeout."""

    def __init__(self, hook_id: str, timeout_seconds: float) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.TIMEOUT,
            message=f"Hook '{hook_id}' exceeded timeout of {timeout_seconds}s",
            context={
                "hook_id": hook_id,
                "timeout_seconds": timeout_seconds,
            },
        )


class CallableNotFoundError(PipelineError):
    """Raised when a callable reference is not found in the registry."""

    def __init__(self, callable_ref: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.NOT_FOUND,
            message=f"Callable not found in registry: {callable_ref}",
            context={"callable_ref": callable_ref},
        )


__all__ = [
    "CallableNotFoundError",
    "DependencyCycleError",
    "DuplicateHookError",
    "HookRegistryFrozenError",
    "HookTimeoutError",
    "HookTypeMismatchError",
    "PipelineError",
    "UnknownDependencyError",
]
