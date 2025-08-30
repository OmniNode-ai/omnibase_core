"""
Consul KV store operation models.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_conflict_resolution_strategy import \
    EnumConflictResolutionStrategy
from omnibase_core.enums.enum_kv_operation_type import EnumKVOperationType


class ModelKVEntry(BaseModel):
    """Represents a Consul KV entry."""

    key: str = Field(..., description="The KV key path")
    value: Union[str, Dict[str, Any], List[Any]] = Field(
        ..., description="The value stored in the KV entry"
    )
    modify_index: int = Field(
        0, description="Consul modify index for optimistic locking"
    )
    create_index: int = Field(0, description="Consul create index")
    flags: int = Field(0, description="Consul flags for the entry")
    session: Optional[str] = Field(None, description="Session ID if entry is locked")


class ModelNodeMetadata(BaseModel):
    """Node metadata structure for KV storage."""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(
        ..., description="Type of the node (registry, service, worker, etc.)"
    )
    version: str = Field(..., description="Node version")
    status: str = Field(
        "active", description="Node status: active, deprecated, archived"
    )
    capabilities: List[str] = Field(
        default_factory=list, description="List of node capabilities"
    )
    trust_level: str = Field("medium", description="Trust level: low, medium, high")
    endpoints: Dict[str, str] = Field(
        default_factory=dict, description="Service endpoints (service, health, metrics)"
    )
    metadata_hash: str = Field(..., description="SHA256 hash of metadata for integrity")
    last_updated: str = Field(..., description="ISO timestamp of last update")
    signature: Optional[str] = Field(
        None, description="Digital signature for verification"
    )
    tags: List[str] = Field(
        default_factory=list, description="Node tags for categorization"
    )
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )


class ModelSyncResult(BaseModel):
    """Result of a KV sync operation."""

    success: bool = Field(..., description="Whether the sync was successful")
    operation: EnumKVOperationType = Field(
        ..., description="Type of operation performed"
    )
    key: str = Field(..., description="KV key that was synced")
    modify_index: Optional[int] = Field(None, description="New modify index after sync")
    conflict_detected: bool = Field(
        False, description="Whether a conflict was detected"
    )
    conflict_resolution: Optional[EnumConflictResolutionStrategy] = Field(
        None, description="Strategy used to resolve conflict"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if sync failed"
    )
    sync_duration_ms: float = Field(..., description="Time taken for sync operation")
    local_hash: Optional[str] = Field(None, description="Hash of local data")
    remote_hash: Optional[str] = Field(None, description="Hash of remote data")


class ModelKVChangeEvent(BaseModel):
    """Event representing a change in Consul KV."""

    key: str = Field(..., description="KV key that changed")
    operation: EnumKVOperationType = Field(..., description="Type of change operation")
    old_value: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Previous value (for updates/deletes)"
    )
    new_value: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="New value (for creates/updates)"
    )
    modify_index: int = Field(..., description="Consul modify index")
    timestamp: str = Field(..., description="ISO timestamp when change occurred")
    datacenter: str = Field(
        "dc1", description="Consul datacenter where change occurred"
    )


class ModelConfigurationProfile(BaseModel):
    """Configuration profile with inheritance support."""

    profile_id: str = Field(..., description="Unique profile identifier")
    extends: Optional[str] = Field(None, description="Parent profile to inherit from")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration key-value pairs"
    )
    overrides: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration overrides"
    )
    environment: str = Field("production", description="Target environment")
    last_updated: str = Field(..., description="ISO timestamp of last update")
    version: str = Field("1.0.0", description="Profile version")
    active: bool = Field(True, description="Whether profile is active")


class ModelKVSyncConfig(BaseModel):
    """Configuration for KV synchronization."""

    bidirectional: bool = Field(True, description="Enable bidirectional sync")
    conflict_resolution: EnumConflictResolutionStrategy = Field(
        EnumConflictResolutionStrategy.TIMESTAMP_WINS,
        description="Default conflict resolution strategy",
    )
    sync_interval: int = Field(30, description="Sync interval in seconds")
    batch_size: int = Field(100, description="Maximum entries to sync per batch")
    require_signature: bool = Field(
        True, description="Require digital signatures on writes"
    )
    hash_algorithm: str = Field(
        "sha256", description="Hash algorithm for integrity checks"
    )
    signature_algorithm: str = Field(
        "ed25519", description="Digital signature algorithm"
    )
    namespaces: Dict[str, str] = Field(
        default_factory=lambda: {
            "nodes": "onex/nodes",
            "config": "onex/config",
            "profiles": "onex/config/profile",
        },
        description="KV namespace mappings",
    )


class ModelKVBatch(BaseModel):
    """Batch of KV operations."""

    operations: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of KV operations in the batch"
    )
    batch_id: str = Field(..., description="Unique batch identifier")
    total_operations: int = Field(
        ..., description="Total number of operations in batch"
    )
    created_at: str = Field(..., description="ISO timestamp when batch was created")


class ModelKVWatch(BaseModel):
    """Configuration for watching KV changes."""

    key_prefix: str = Field(..., description="KV key prefix to watch")
    recursive: bool = Field(True, description="Watch all keys under prefix recursively")
    timeout: int = Field(300, description="Watch timeout in seconds")
    last_index: int = Field(0, description="Last Consul index for long polling")
    datacenter: Optional[str] = Field(None, description="Specific datacenter to watch")


class ModelKVWatchResult(BaseModel):
    """Result of KV watch operation."""

    success: bool = Field(..., description="Whether the watch operation was successful")
    changes: List[ModelKVChangeEvent] = Field(
        default_factory=list, description="List of KV changes detected"
    )
    last_index: int = Field(..., description="Latest Consul index after watch")
    watch_duration_ms: float = Field(
        ..., description="Duration of watch operation in milliseconds"
    )
    timeout_occurred: bool = Field(False, description="Whether the watch timed out")
    error_message: Optional[str] = Field(
        None, description="Error message if watch failed"
    )
