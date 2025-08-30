"""
Signature block model for ONEX node metadata.
"""

from typing import Optional

from pydantic import BaseModel


class ModelSignatureBlock(BaseModel):
    """Digital signature information for ONEX nodes."""

    signature: Optional[str] = None
    algorithm: Optional[str] = None
    signed_by: Optional[str] = None
    issued_at: Optional[str] = None
