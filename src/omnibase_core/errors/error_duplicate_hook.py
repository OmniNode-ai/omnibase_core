# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Duplicate hook exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class DuplicateHookError(PipelineError):
    """Raised when registering a hook with duplicate ID."""

    def __init__(self, hook_id: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            message=f"Hook with ID '{hook_id}' already registered",
            context={"hook_id": hook_id},
        )


__all__ = ["DuplicateHookError"]
