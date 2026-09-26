# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed secret-detection failure for artifact writes."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactSecretDetectedError(ModelOnexError):
    """Raw artifact bytes were refused because they contain a secret."""

    def __init__(self, artifact_ref: str) -> None:
        self.ref = artifact_ref
        super().__init__(
            f"secret detected in artifact {artifact_ref}; raw write refused "
            "(secret_detected sidecar recorded)",
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
        )


__all__ = ["ArtifactSecretDetectedError"]
