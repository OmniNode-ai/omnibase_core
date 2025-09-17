"""
Collection configuration model for Qdrant collection setup.

This model defines configuration parameters for creating collections,
following ONEX canonical patterns with proper validation.
"""

from typing import TYPE_CHECKING, Any, Union

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from omnibase_core.models.ai.qdrant.model_vector_config import ModelVectorConfig


class ModelCollectionConfig(BaseModel):
    """Model representing Qdrant collection configuration."""

    vectors: Union["ModelVectorConfig", dict[str, "ModelVectorConfig"]] = Field(
        ...,
        description="Vector configuration",
    )
    shard_number: int | None = Field(
        None,
        description="Number of shards for the collection",
    )
    replication_factor: int | None = Field(
        None,
        description="Replication factor for high availability",
    )
    write_consistency_factor: int | None = Field(
        None,
        description="Write consistency requirements",
    )
    on_disk_payload: bool = Field(default=True, description="Store payload on disk")
    hnsw_config: dict[str, Any] | None = Field(
        None,
        description="Global HNSW configuration",
    )
    wal_config: dict[str, Any] | None = Field(
        None,
        description="Write-ahead log configuration",
    )
    optimizers_config: dict[str, Any] | None = Field(
        None,
        description="Index optimizers configuration",
    )

    @field_validator("shard_number")
    @classmethod
    def validate_shard_number(cls, v):
        if v is not None and (v <= 0 or v > 1000):
            msg = "Shard number must be between 1 and 1000"
            raise ValueError(msg)
        return v

    @field_validator("replication_factor")
    @classmethod
    def validate_replication_factor(cls, v):
        if v is not None and (v <= 0 or v > 100):
            msg = "Replication factor must be between 1 and 100"
            raise ValueError(msg)
        return v
