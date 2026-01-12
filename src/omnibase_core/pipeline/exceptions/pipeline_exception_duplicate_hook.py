# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Duplicate hook exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.pipeline.exceptions.pipeline_exception import PipelineError


class DuplicateHookError(PipelineError):
    """Raised when registering a hook with duplicate name."""

    def __init__(self, hook_name: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            message=f"Hook with name '{hook_name}' already registered",
            context={"hook_name": hook_name},
        )


__all__ = ["DuplicateHookError"]
