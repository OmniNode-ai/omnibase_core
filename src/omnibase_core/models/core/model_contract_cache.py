"""Contract cache model for ContractLoader."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ModelContractCache(BaseModel):
    """Cache entry for loaded contracts."""

    cache_key: str = Field(description="Unique cache key")
    file_path: Path = Field(description="Path to contract file")
    content: "ModelContractContent" = Field(
        description="Cached contract content"
    )  # Forward reference
    cached_at: datetime = Field(description="When cached")
    file_modified_at: datetime = Field(description="File modification time")
    file_size: int = Field(description="File size in bytes")
    content_hash: str = Field(description="Content hash for validation")

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def last_modified(self) -> float:
        """Get last modified timestamp for cache validation."""
        return self.file_modified_at.timestamp()


# Import here to avoid circular dependency
from omnibase_core.models.core.model_contract_content import ModelContractContent

ModelContractCache.model_rebuild()
