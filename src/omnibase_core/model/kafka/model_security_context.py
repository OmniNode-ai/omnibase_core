"""ModelSecurityContext: Security context for payload integrity and confidentiality"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelSecurityContext(BaseModel):
    """Security context for payload integrity and confidentiality"""

    signature: Optional[str] = Field(
        None, description="HMAC-SHA256 signature of payload for integrity verification"
    )
    signing_key_id: Optional[str] = Field(
        None, description="Key identifier used for signature verification"
    )
    encryption_key_id: Optional[str] = Field(
        None, description="Key identifier if payload is encrypted"
    )
