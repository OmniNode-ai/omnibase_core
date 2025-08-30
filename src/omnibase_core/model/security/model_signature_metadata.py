"""
ModelSignatureMetadata: Metadata for cryptographic signatures.

This model provides structured metadata for digital signatures
with properly typed fields.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelSignatureMetadata(BaseModel):
    """Metadata for cryptographic signatures."""

    signature_version: str = Field(
        default="1.0", description="Signature format version"
    )
    timestamp_source: Optional[str] = Field(
        None, description="Source of timestamp (ntp, local, etc)"
    )
    hardware_security_module: Optional[bool] = Field(
        None, description="Whether HSM was used"
    )
    certificate_chain_length: Optional[int] = Field(
        None, description="Length of certificate chain"
    )
    cross_signatures: List[str] = Field(
        default_factory=list, description="Cross-signature references"
    )
    notary_service: Optional[str] = Field(
        None, description="Notary service used if any"
    )
    legal_jurisdiction: Optional[str] = Field(
        None, description="Legal jurisdiction for signature"
    )
    compliance_assertions: List[str] = Field(
        default_factory=list, description="Compliance assertions made"
    )
