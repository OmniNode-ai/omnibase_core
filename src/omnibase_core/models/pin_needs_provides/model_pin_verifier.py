# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A verifier, the pin keys that select it and its declared versions (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.pin_needs_provides.model_pin_verifier_version import (
    ModelPinVerifierVersion,
)


class ModelPinVerifier(BaseModel):
    """One verifier: a pin whose key is one of ``pin_keys`` pins this verifier."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    verifier_name: str = Field(
        min_length=1, description="Name of the verifier, free data"
    )
    pin_keys: tuple[str, ...] = Field(
        min_length=1, description="Keys a caller pins this verifier under"
    )
    versions: tuple[ModelPinVerifierVersion, ...] = Field(
        default_factory=tuple, description="Every version with its declared needs"
    )

    def version(self, value: str) -> ModelPinVerifierVersion | None:
        """The declared entry of a pinned version, if any."""
        return next((entry for entry in self.versions if entry.version == value), None)
