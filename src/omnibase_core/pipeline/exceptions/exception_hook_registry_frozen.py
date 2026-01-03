# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Hook registry frozen exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.pipeline.exceptions.exception_pipeline import PipelineError


class HookRegistryFrozenError(PipelineError):
    """Raised when attempting to modify a frozen registry."""

    def __init__(self, message: str = "Cannot modify frozen hook registry") -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.INVALID_STATE,
            message=message,
        )


__all__ = ["HookRegistryFrozenError"]
