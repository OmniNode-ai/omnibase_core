"""
Signature block model for ONEX node metadata.
"""

from pydantic import BaseModel


class ModelSignatureBlock(BaseModel):
    """Digital signature information for ONEX nodes."""

    signature: str | None = None
    algorithm: str | None = None
    signed_by: str | None = None
    issued_at: str | None = None
