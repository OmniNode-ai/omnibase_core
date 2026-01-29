"""Model for pattern signatures with versioning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives import ModelSemVer


class ModelPatternSignature(BaseModel):
    """Versioned, deterministic signature with stability contract.

    Signatures are SHA256 hashes computed from normalized pattern inputs.
    The signature_version field supports algorithm evolution with
    structured semantic versioning.
    """

    signature: str = Field(
        description="SHA256 hash of normalized pattern inputs",
    )
    signature_version: ModelSemVer = Field(
        description="Semantic version of signature algorithm",
    )
    signature_inputs: tuple[str, ...] = Field(
        description="Ordered list of inputs that were hashed (for debugging)",
    )
    normalization_applied: str = Field(
        description="Normalization method used (e.g., 'lowercase_sort_dedupe')",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
