# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured authorization failure for restricted artifact reads."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactUnauthorizedError(ModelOnexError):
    """Raised when a principal cannot read a restricted artifact kind."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message, error_code=EnumCoreErrorCode.PERMISSION_DENIED
        )


__all__ = ["ArtifactUnauthorizedError"]
