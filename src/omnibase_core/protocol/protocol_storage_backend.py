"""
Storage Backend Protocol for ONEX Checkpoint Storage.
Defines the interface for pluggable storage backends at the root level.
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

# Import the new Pydantic models
from omnibase_core.tools.coordination.hub_generic.v1_0_0.models.model_checkpoint_data import (
    ModelCheckpointData,
)
from omnibase_core.tools.coordination.hub_generic.v1_0_0.models.model_storage_credentials import (
    ModelStorageCredentials,
)
from omnibase_core.tools.coordination.hub_generic.v1_0_0.models.model_storage_result import (
    ModelStorageConfiguration,
    ModelStorageHealthStatus,
    ModelStorageListResult,
    ModelStorageResult,
)


@runtime_checkable
class ProtocolStorageBackend(Protocol):
    """
    Protocol for checkpoint storage backends.
    Follows the same pattern as ProtocolEventBus for consistency.
    """

    def __init__(
        self,
        storage_config: ModelStorageConfiguration,
        credentials: ModelStorageCredentials | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize storage backend with configuration."""
        ...

    def store_checkpoint(
        self,
        checkpoint_data: ModelCheckpointData,
    ) -> ModelStorageResult:
        """
        Store a checkpoint to the backend.

        Args:
            checkpoint_data: The checkpoint data to store

        Returns:
            ModelStorageResult: Result of the storage operation
        """
        ...

    def retrieve_checkpoint(self, checkpoint_id: str) -> ModelStorageResult:
        """
        Retrieve a checkpoint by ID.

        Args:
            checkpoint_id: Unique checkpoint identifier

        Returns:
            ModelStorageResult: Result containing checkpoint data if found
        """
        ...

    def list_checkpoints(
        self,
        workflow_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ModelStorageListResult:
        """
        List checkpoints, optionally filtered by workflow ID.

        Args:
            workflow_id: Optional workflow ID filter
            limit: Optional limit on number of results
            offset: Optional offset for pagination

        Returns:
            ModelStorageListResult: Result containing list of matching checkpoints
        """
        ...

    def delete_checkpoint(self, checkpoint_id: str) -> ModelStorageResult:
        """
        Delete a checkpoint by ID.

        Args:
            checkpoint_id: Unique checkpoint identifier

        Returns:
            ModelStorageResult: Result of the deletion operation
        """
        ...

    def cleanup_expired_checkpoints(
        self,
        retention_hours: int = 72,
    ) -> ModelStorageResult:
        """
        Clean up expired checkpoints based on retention policies.

        Args:
            retention_hours: Hours to retain checkpoints

        Returns:
            ModelStorageResult: Result containing number of checkpoints cleaned up
        """
        ...

    def get_storage_status(self) -> ModelStorageHealthStatus:
        """
        Get storage backend status and health information.

        Returns:
            ModelStorageHealthStatus: Status information including health, capacity, etc.
        """
        ...

    def test_connection(self) -> ModelStorageResult:
        """
        Test connectivity to the storage backend.

        Returns:
            ModelStorageResult: Result of the connection test
        """
        ...

    def initialize_storage(self) -> ModelStorageResult:
        """
        Initialize storage backend (create tables, directories, etc.).

        Returns:
            ModelStorageResult: Result of the initialization operation
        """
        ...

    @property
    def backend_id(self) -> str:
        """Get unique backend identifier."""
        ...

    @property
    def backend_type(self) -> str:
        """Get backend type (filesystem, sqlite, postgresql, etc.)."""
        ...

    @property
    def is_healthy(self) -> bool:
        """Check if backend is healthy and operational."""
        ...


class ProtocolStorageBackendFactory(ABC):
    """
    Abstract factory for creating storage backends.
    Follows the same pattern as ProtocolEventBusFactory.
    """

    @abstractmethod
    def get_storage_backend(
        self,
        backend_type: str,
        storage_config: ModelStorageConfiguration,
        credentials: ModelStorageCredentials | None = None,
        **kwargs: object,
    ) -> ProtocolStorageBackend:
        """
        Create a storage backend instance.

        Args:
            backend_type: Storage backend type (filesystem, sqlite, postgresql)
            storage_config: Storage configuration model
            credentials: Optional authentication credentials
            **kwargs: Additional backend-specific parameters

        Returns:
            ProtocolStorageBackend: Configured storage backend instance
        """
        ...

    @abstractmethod
    def list_available_backends(self) -> list[str]:
        """
        List available storage backend types.

        Returns:
            List[str]: List of available backend type names
        """
        ...

    @abstractmethod
    def validate_backend_config(
        self,
        backend_type: str,
        storage_config: ModelStorageConfiguration,
    ) -> ModelStorageResult:
        """
        Validate configuration for a specific backend type.

        Args:
            backend_type: Storage backend type
            storage_config: Configuration to validate

        Returns:
            ModelStorageResult: Result of the validation operation
        """
        ...

    @abstractmethod
    def get_default_config(self, backend_type: str) -> ModelStorageConfiguration:
        """
        Get default configuration for a backend type.

        Args:
            backend_type: Storage backend type

        Returns:
            ModelStorageConfiguration: Default configuration model for the backend type
        """
        ...
