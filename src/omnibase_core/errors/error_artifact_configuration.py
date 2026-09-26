# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed invalid-configuration failure for artifact operations."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactConfigurationError(ModelOnexError):
    """An artifact-store option violates its declared contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code=EnumCoreErrorCode.INVALID_CONFIGURATION)


__all__ = ["ArtifactConfigurationError"]
