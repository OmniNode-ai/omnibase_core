# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed authorization failure for restricted artifact reads."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactUnauthorizedError(ModelOnexError):
    """A principal is not authorized to read a restricted artifact."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code=EnumCoreErrorCode.PERMISSION_DENIED)


__all__ = ["ArtifactUnauthorizedError"]
