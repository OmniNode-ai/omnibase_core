# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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
