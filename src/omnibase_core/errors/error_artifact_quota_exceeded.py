# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured quota failure for artifact writes."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactQuotaExceededError(ModelOnexError):
    """Raised when a write exceeds per-artifact or per-scope quota."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, error_code=EnumCoreErrorCode.QUOTA_EXCEEDED)


__all__ = ["ArtifactQuotaExceededError"]
