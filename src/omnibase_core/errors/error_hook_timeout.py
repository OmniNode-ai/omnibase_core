# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Hook timeout exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


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


__all__ = ["HookTimeoutError"]
