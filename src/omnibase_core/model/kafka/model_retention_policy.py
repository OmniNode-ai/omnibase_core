"""ModelRetentionPolicy: Event retention and compaction configuration"""

from pydantic import BaseModel, Field


class ModelRetentionPolicy(BaseModel):
    """Event retention and compaction configuration"""

    ttl_seconds: int | None = Field(
        None,
        description="Time-to-live in seconds, null for default topic retention",
    )
    compaction_key: str | None = Field(
        None,
        description="Key for log compaction, enables latest-value semantics",
    )
