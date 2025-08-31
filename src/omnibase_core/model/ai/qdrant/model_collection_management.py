"""
Pydantic models for Qdrant collection management operations.

This module defines the data models used for collection creation, configuration,
and management within the Qdrant vector database integration.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelVectorConfig(BaseModel):
    """Model representing vector configuration for a collection."""

    size: int = Field(..., description="Vector dimension size")
    distance: str = Field(
        default="Cosine",
        description="Distance metric for similarity calculation",
    )
    hnsw_config: dict[str, Any] | None = Field(
        None,
        description="HNSW index configuration",
    )
    quantization_config: dict[str, Any] | None = Field(
        None,
        description="Vector quantization configuration",
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v <= 0 or v > 65536:
            msg = "Vector size must be between 1 and 65536"
            raise ValueError(msg)
        return v

    @field_validator("distance")
    @classmethod
    def validate_distance(cls, v):
        allowed_distances = ["Cosine", "Euclidean", "Dot", "Manhattan"]
        if v not in allowed_distances:
            msg = f"Distance must be one of {allowed_distances}"
            raise ValueError(msg)
        return v


class ModelCollectionConfig(BaseModel):
    """Model representing Qdrant collection configuration."""

    vectors: ModelVectorConfig | dict[str, ModelVectorConfig] = Field(
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


class ModelCollectionInfo(BaseModel):
    """Model representing collection information and statistics."""

    name: str = Field(..., description="Collection name")
    status: str = Field(..., description="Collection status")
    vectors_count: int = Field(
        default=0,
        description="Number of vectors in the collection",
    )
    indexed_vectors_count: int = Field(
        default=0,
        description="Number of indexed vectors",
    )
    points_count: int = Field(
        default=0,
        description="Number of points in the collection",
    )
    segments_count: int = Field(default=0, description="Number of segments")
    config: ModelCollectionConfig = Field(..., description="Collection configuration")
    payload_schema: dict[str, str] = Field(
        default_factory=dict,
        description="Payload schema information",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ["green", "yellow", "red", "grey"]
        if v not in allowed_statuses:
            msg = f"Status must be one of {allowed_statuses}"
            raise ValueError(msg)
        return v


class ModelCollectionOperation(BaseModel):
    """Model representing a collection management operation."""

    operation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique operation identifier",
    )
    operation_type: str = Field(..., description="Type of collection operation")
    collection_name: str = Field(..., description="Target collection name")
    config: ModelCollectionConfig | None = Field(
        None,
        description="Collection configuration for create operations",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific parameters",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Operation creation timestamp",
    )

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, v):
        allowed_types = ["create", "delete", "update", "optimize", "backup", "restore"]
        if v not in allowed_types:
            msg = f"Operation type must be one of {allowed_types}"
            raise ValueError(msg)
        return v

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v):
        if not v or len(v.strip()) == 0:
            msg = "Collection name cannot be empty"
            raise ValueError(msg)
        if len(v) > 255:
            msg = "Collection name cannot exceed 255 characters"
            raise ValueError(msg)
        # Check for invalid characters
        invalid_chars = set('<>:"/\\|?*')
        if any(char in v for char in invalid_chars):
            msg = f"Collection name contains invalid characters: {invalid_chars}"
            raise ValueError(
                msg,
            )
        return v.strip()


class ModelCollectionOperationResult(BaseModel):
    """Model representing the result of a collection operation."""

    operation_id: str = Field(..., description="Operation identifier")
    success: bool = Field(..., description="Whether the operation succeeded")
    collection_name: str = Field(..., description="Target collection name")
    operation_type: str = Field(..., description="Type of operation performed")
    execution_time_ms: float = Field(
        ...,
        description="Operation execution time in milliseconds",
    )
    result_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific result data",
    )
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages from the operation",
    )

    @property
    def is_success(self) -> bool:
        """Convenience property for success status."""
        return self.success


class ModelCollectionSnapshot(BaseModel):
    """Model representing a collection snapshot for backup/restore operations."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique snapshot identifier",
    )
    collection_name: str = Field(..., description="Source collection name")
    snapshot_name: str = Field(..., description="Human-readable snapshot name")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Snapshot creation timestamp",
    )
    size_bytes: int = Field(default=0, description="Snapshot size in bytes")
    vectors_count: int = Field(
        default=0,
        description="Number of vectors in the snapshot",
    )
    checksum: str | None = Field(
        None,
        description="Snapshot checksum for integrity verification",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional snapshot metadata",
    )
    status: str = Field(default="creating", description="Snapshot status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ["creating", "completed", "failed", "restoring", "deleted"]
        if v not in allowed_statuses:
            msg = f"Status must be one of {allowed_statuses}"
            raise ValueError(msg)
        return v


class ModelIndexOptimizationConfig(BaseModel):
    """Model representing index optimization configuration."""

    max_optimization_threads: int = Field(
        default=4,
        description="Maximum number of optimization threads",
    )
    deleted_threshold: float = Field(
        default=0.2,
        description="Threshold of deleted vectors to trigger optimization",
    )
    vacuum_min_vector_number: int = Field(
        default=1000,
        description="Minimum vectors required for vacuum operation",
    )
    default_segment_number: int = Field(
        default=0,
        description="Default number of segments",
    )
    max_segment_size: int | None = Field(
        None,
        description="Maximum segment size in KB",
    )
    memmap_threshold: int | None = Field(
        None,
        description="Memory mapping threshold",
    )
    indexing_threshold: int = Field(
        default=20000,
        description="Indexing threshold for new segments",
    )
    flush_interval_sec: int = Field(default=5, description="Flush interval in seconds")
    max_optimization_workers: int = Field(
        default=1,
        description="Maximum optimization workers",
    )

    @field_validator("deleted_threshold")
    @classmethod
    def validate_deleted_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            msg = "Deleted threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v

    @field_validator(
        "max_optimization_threads",
        "vacuum_min_vector_number",
        "flush_interval_sec",
    )
    @classmethod
    def validate_positive_int(cls, v):
        if v <= 0:
            msg = "Value must be positive"
            raise ValueError(msg)
        return v


class ModelClusterInfo(BaseModel):
    """Model representing Qdrant cluster information."""

    peer_id: int = Field(..., description="Peer ID in the cluster")
    uri: str = Field(..., description="Peer URI")
    is_leader: bool = Field(
        default=False,
        description="Whether this peer is the cluster leader",
    )
    raft_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Raft consensus information",
    )
    collections: list[str] = Field(
        default_factory=list,
        description="Collections managed by this peer",
    )
    last_heartbeat: datetime | None = Field(
        None,
        description="Last heartbeat timestamp",
    )
    status: str = Field(default="active", description="Peer status in the cluster")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ["active", "inactive", "recovering", "failed"]
        if v not in allowed_statuses:
            msg = f"Status must be one of {allowed_statuses}"
            raise ValueError(msg)
        return v


class ModelCollectionAlias(BaseModel):
    """Model representing collection alias management."""

    alias_name: str = Field(..., description="Alias name")
    collection_name: str = Field(..., description="Target collection name")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Alias creation timestamp",
    )
    description: str | None = Field(None, description="Alias description")

    @field_validator("alias_name", "collection_name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            msg = "Name cannot be empty"
            raise ValueError(msg)
        if len(v) > 255:
            msg = "Name cannot exceed 255 characters"
            raise ValueError(msg)
        return v.strip()
