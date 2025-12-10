from pydantic import Field

"""
Model for contract cache representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
contract caching and performance optimization.

"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.core.model_contract_content import ModelContractContent


class ModelContractCache(BaseModel):
    """Model representing cached contract data with metadata."""

    model_config = ConfigDict(extra="forbid")

    # === CACHE IDENTIFICATION ===
    cache_key: str = Field(default=..., description="Unique cache key for the contract")
    file_path: Path = Field(
        default=..., description="Path to the original contract file"
    )

    # === CACHED CONTENT ===
    content: ModelContractContent = Field(
        default=..., description="Cached contract content"
    )

    # === CACHE METADATA ===
    cached_at: datetime = Field(
        default=..., description="Timestamp when cache was created"
    )
    file_modified_at: datetime = Field(
        default=..., description="Last modification time of source file"
    )
    file_size: int = Field(default=..., description="Size of source file in bytes")
    content_hash: str = Field(default=..., description="Hash of the cached content")

    # === CACHE VALIDITY ===
    is_valid: bool = Field(
        default=True, description="Whether cache entry is still valid"
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation errors if invalid"
    )

    # === ACCESS TRACKING ===
    access_count: int = Field(
        default=0, description="Number of times cache was accessed"
    )
    last_accessed_at: datetime | None = Field(
        default=None, description="Timestamp of last access"
    )

    # === CACHE CONFIGURATION ===
    ttl_seconds: int | None = Field(
        default=None, description="Time-to-live in seconds, None for no expiration"
    )
    max_age_seconds: int | None = Field(
        default=None, description="Maximum age in seconds before refresh"
    )

    def is_expired(self) -> bool:
        """Check if cache entry is expired based on TTL."""
        if self.ttl_seconds is None:
            return False

        age_seconds = (datetime.now() - self.cached_at).total_seconds()
        return age_seconds > self.ttl_seconds

    def is_stale(self) -> bool:
        """Check if cache entry is stale based on max age."""
        if self.max_age_seconds is None:
            return False

        age_seconds = (datetime.now() - self.cached_at).total_seconds()
        return age_seconds > self.max_age_seconds

    def update_access(self) -> None:
        """Update access tracking information."""
        self.access_count += 1
        self.last_accessed_at = datetime.now()

    def invalidate(self, reason: str) -> None:
        """Mark cache entry as invalid with reason."""
        self.is_valid = False
        if reason not in self.validation_errors:
            self.validation_errors.append(reason)
