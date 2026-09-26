# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed missing-resource failure for artifact reads."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactNotFoundError(ModelOnexError):
    """An artifact blob or metadata sidecar does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code=EnumCoreErrorCode.FILE_NOT_FOUND)


__all__ = ["ArtifactNotFoundError"]
