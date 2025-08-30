"""ModelRetentionPolicy: Event retention and compaction configuration"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelRetentionPolicy(BaseModel):
    """Event retention and compaction configuration"""

    ttl_seconds: Optional[int] = Field(
        None, description="Time-to-live in seconds, null for default topic retention"
    )
    compaction_key: Optional[str] = Field(
        None, description="Key for log compaction, enables latest-value semantics"
    )
