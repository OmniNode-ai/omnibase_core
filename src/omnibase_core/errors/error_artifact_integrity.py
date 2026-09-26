# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed integrity failure for content-addressed artifacts."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactIntegrityError(ModelOnexError):
    """Persisted artifact bytes or metadata violate the content contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code=EnumCoreErrorCode.SECURITY_VIOLATION)


__all__ = ["ArtifactIntegrityError"]
