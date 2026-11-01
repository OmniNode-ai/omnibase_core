# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The verifiers' needs declaration, read as data (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.pin_needs_provides.model_pin_verifier import ModelPinVerifier


class ModelPinNeedsDeclaration(BaseModel):
    """Every declared verifier; one pin key selects at most one verifier."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    verifiers: tuple[ModelPinVerifier, ...] = Field(
        default_factory=tuple, description="Declared verifiers"
    )

    @model_validator(mode="after")
    def _one_verifier_per_pin_key(self) -> ModelPinNeedsDeclaration:
        seen: dict[str, str] = {}
        for verifier in self.verifiers:
            for key in verifier.pin_keys:
                if key in seen:
                    raise ValueError(
                        f"pin key {key!r} selects both {seen[key]!r} and {verifier.verifier_name!r}"
                    )
                seen[key] = verifier.verifier_name
            values = [entry.version for entry in verifier.versions]
            if len(values) != len(set(values)):
                raise ValueError(
                    f"{verifier.verifier_name!r} declares one version twice"
                )
        return self

    def verifier_for(self, pin_key: str) -> ModelPinVerifier | None:
        """The verifier a pin key selects, if any."""
        return next((v for v in self.verifiers if pin_key in v.pin_keys), None)
