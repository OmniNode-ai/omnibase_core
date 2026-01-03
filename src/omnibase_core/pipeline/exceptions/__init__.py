# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Pipeline-specific exceptions."""

from omnibase_core.pipeline.exceptions.exception_callable_not_found import (
    CallableNotFoundError,
)
from omnibase_core.pipeline.exceptions.exception_dependency_cycle import (
    DependencyCycleError,
)
from omnibase_core.pipeline.exceptions.exception_duplicate_hook import (
    DuplicateHookError,
)
from omnibase_core.pipeline.exceptions.exception_hook_registry_frozen import (
    HookRegistryFrozenError,
)
from omnibase_core.pipeline.exceptions.exception_hook_timeout import HookTimeoutError
from omnibase_core.pipeline.exceptions.exception_hook_type_mismatch import (
    HookTypeMismatchError,
)
from omnibase_core.pipeline.exceptions.exception_pipeline import PipelineError
from omnibase_core.pipeline.exceptions.exception_unknown_dependency import (
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
