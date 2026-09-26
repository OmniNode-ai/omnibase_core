# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed quota failure for the content-addressed artifact store."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactQuotaExceededError(ModelOnexError):
    """A write would exceed a configured artifact quota."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code=EnumCoreErrorCode.QUOTA_EXCEEDED)


__all__ = ["ArtifactQuotaExceededError"]
