# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured refusal when an artifact payload contains a detected secret."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError


class ArtifactSecretDetectedError(ModelOnexError):
    """Raised after refusing raw bytes that match a secret pattern."""

    def __init__(self, ref: str) -> None:
        self.ref = ref
        super().__init__(
            message=(
                f"secret detected in artifact {ref}; raw write refused "
                "(secret_detected sidecar recorded)"
            ),
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
        )


__all__ = ["ArtifactSecretDetectedError"]
