"""
Model for contract cache entries.

This model represents cached contract data with metadata
for cache management and performance optimization.
"""

import time
from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.core.models.model_contract_content import ModelContractContent


class ModelContractCacheEntry(BaseModel):
    """Represents a cached contract with metadata."""

    contract_path: str = Field(..., description="Original contract file path")
    contract_content: ModelContractContent = Field(
        ...,
        description="Cached contract data",
    )
    cached_at: float = Field(
        default_factory=time.time,
        description="Timestamp when cached",
    )
    access_count: int = Field(default=0, description="Number of cache accesses")
    last_accessed: float = Field(
        default_factory=time.time,
        description="Last access timestamp",
    )
    file_modified_time: float | None = Field(
        None,
        description="File modification time when cached",
    )

    def is_stale(self, current_file_time: float | None = None) -> bool:
        """
        Check if cache entry is stale.

        Args:
            current_file_time: Current file modification time

        Returns:
            bool: True if cache is stale, False if still valid
        """
        if current_file_time is None:
            # If we can't check file time, consider cache valid
            return False

        # Cache is stale if file has been modified since caching
        return (
            self.file_modified_time is not None
            and current_file_time > self.file_modified_time
        )

    def update_access(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()

    @classmethod
    def create_from_contract(
        cls,
        contract_path: Path,
        contract_content: ModelContractContent,
        file_modified_time: float | None = None,
    ) -> "ModelContractCacheEntry":
        """
        Create cache entry from contract data.

        Args:
            contract_path: Path to contract file
            contract_content: Contract content to cache
            file_modified_time: File modification time

        Returns:
            ModelContractCacheEntry: New cache entry
        """
        return cls(
            contract_path=str(contract_path),
            contract_content=contract_content,
            file_modified_time=file_modified_time,
        )
