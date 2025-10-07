from typing import Any

from pydantic import Field

from omnibase_core.models.core.model_semver import ModelSemVer

"""
ModelSignatureMetadata: Metadata for cryptographic signatures.

This model provides structured metadata for digital signatures
with properly typed fields.
"""

from pydantic import BaseModel, Field


class ModelSignatureMetadata(BaseModel):
    """Metadata for cryptographic signatures."""

    signature_version: str = Field(
        default="1.0",
        description="Signature format version",
    )
    timestamp_source: str | None = Field(
        default=None,
        description="Source of timestamp (ntp, local, etc)",
    )
    hardware_security_module: bool | None = Field(
        default=None,
        description="Whether HSM was used",
    )
    certificate_chain_length: int | None = Field(
        default=None,
        description="Length of certificate chain",
    )
    cross_signatures: list[str] = Field(
        default_factory=list,
        description="Cross-signature references",
    )
    notary_service: str | None = Field(
        default=None,
        description="Notary service used if any",
    )
    legal_jurisdiction: str | None = Field(
        default=None,
        description="Legal jurisdiction for signature",
    )
    compliance_assertions: list[str] = Field(
        default_factory=list,
        description="Compliance assertions made",
    )
