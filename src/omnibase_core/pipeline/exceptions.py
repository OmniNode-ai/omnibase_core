# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline-specific exceptions.

Re-exports all pipeline exceptions from their individual modules.
"""

# Re-export from errors module (per ONEX file location convention)
from omnibase_core.errors.error_callable_not_found import CallableNotFoundError
from omnibase_core.errors.error_dependency_cycle import DependencyCycleError
from omnibase_core.errors.error_duplicate_hook import DuplicateHookError
from omnibase_core.errors.error_hook_registry_frozen import HookRegistryFrozenError
from omnibase_core.errors.error_hook_timeout import HookTimeoutError
from omnibase_core.errors.error_hook_type_mismatch import HookTypeMismatchError
from omnibase_core.errors.error_pipeline import PipelineError
from omnibase_core.errors.error_unknown_dependency import UnknownDependencyError

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
