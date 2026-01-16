"""Pipeline-specific exceptions.

This module re-exports pipeline exceptions from the canonical `errors` module.
"""

from omnibase_core.errors import (
    CallableNotFoundError,
    DependencyCycleError,
    DuplicateHookError,
    HookRegistryFrozenError,
    HookTimeoutError,
    HookTypeMismatchError,
    PipelineError,
    UnknownDependencyError,
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
