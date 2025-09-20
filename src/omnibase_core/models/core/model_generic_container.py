"""
Generic Container Models.

Provides type-safe container patterns with proper generics support.
These models implement common container operations while maintaining type safety
through bounded generics and proper TypeVar constraints.
"""

from typing import Any, Callable, Generic, Iterator, Protocol, TypeVar, Union
from uuid import UUID, uuid4
from datetime import datetime, UTC

from pydantic import BaseModel, Field, field_validator, model_validator

# Type variables for generic containers
T = TypeVar("T")  # Content type
K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type
M = TypeVar("M")  # Metadata type
T_covariant = TypeVar("T_covariant", covariant=True)  # For read-only operations

# Bounded type variables
T_BaseModel = TypeVar("T_BaseModel", bound=BaseModel)  # Must be BaseModel
T_Serializable = TypeVar("T_Serializable", bound="Serializable")  # Must be serializable


class Serializable(Protocol):
    """Protocol for objects that can be serialized."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Serializable":
        """Create from dictionary representation."""
        ...


class Cacheable(Protocol[T_covariant]):
    """Protocol for objects that can be cached."""

    def get_cache_key(self) -> str:
        """Get the cache key for this object."""
        ...

    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        ...


class ModelGenericContainer(BaseModel, Generic[T]):
    """
    Generic container with type-safe operations.

    Provides a foundation for type-safe containers with common operations
    like storage, retrieval, and lifecycle management while preserving type information.
    """

    # Container metadata
    container_id: UUID = Field(default_factory=uuid4, description="Unique container identifier")
    name: str | None = Field(default=None, description="Container name")
    description: str | None = Field(default=None, description="Container description")

    # Container content
    content: T | None = Field(default=None, description="Container content")

    # Container properties
    is_readonly: bool = Field(default=False, description="Whether container is read-only")
    max_age_seconds: int | None = Field(default=None, description="Maximum age before expiration")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Container tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation time")
    updated_at: datetime | None = Field(default=None, description="Last update time")

    model_config = {"arbitrary_types_allowed": True}

    # No field validator needed - readonly is checked in set_content method

    def set_content(self, content: T) -> bool:
        """
        Set container content.

        Args:
            content: Content to store

        Returns:
            True if content was set, False if readonly
        """
        if self.is_readonly:
            return False

        self.content = content
        self.updated_at = datetime.now(UTC)
        return True

    def get_content(self) -> T | None:
        """Get container content."""
        if self.is_expired():
            return None
        return self.content

    def has_content(self) -> bool:
        """Check if container has content."""
        return self.content is not None and not self.is_expired()

    def clear_content(self) -> bool:
        """
        Clear container content.

        Returns:
            True if content was cleared, False if readonly
        """
        if self.is_readonly:
            return False

        self.content = None
        self.updated_at = datetime.now(UTC)
        return True

    def is_expired(self) -> bool:
        """Check if container has expired."""
        if self.max_age_seconds is None:
            return False

        if self.updated_at is None:
            age = (datetime.now(UTC) - self.created_at).total_seconds()
        else:
            age = (datetime.now(UTC) - self.updated_at).total_seconds()

        return age > self.max_age_seconds

    def get_age_seconds(self) -> float:
        """Get container age in seconds."""
        if self.updated_at is None:
            return (datetime.now(UTC) - self.created_at).total_seconds()
        else:
            return (datetime.now(UTC) - self.updated_at).total_seconds()

    def set_readonly(self, readonly: bool = True) -> None:
        """Set readonly status."""
        self.is_readonly = readonly
        self.updated_at = datetime.now(UTC)

    def map(self, mapper: Callable[[T], V]) -> "ModelGenericContainer[V]":
        """
        Map content to a new type.

        Args:
            mapper: Function to transform content

        Returns:
            New container with mapped content
        """
        new_content = None
        if self.content is not None and not self.is_expired():
            new_content = mapper(self.content)

        return ModelGenericContainer[V](
            name=f"{self.name}_mapped" if self.name else None,
            description=self.description,
            content=new_content,
            is_readonly=self.is_readonly,
            max_age_seconds=self.max_age_seconds,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def filter(self, predicate: Callable[[T], bool]) -> "ModelGenericContainer[T]":
        """
        Filter content based on a predicate.

        Args:
            predicate: Function that returns True if content should be kept

        Returns:
            New container with filtered content
        """
        new_content = None
        if (self.content is not None and
            not self.is_expired() and
            predicate(self.content)):
            new_content = self.content

        return ModelGenericContainer[T](
            name=f"{self.name}_filtered" if self.name else None,
            description=self.description,
            content=new_content,
            is_readonly=self.is_readonly,
            max_age_seconds=self.max_age_seconds,
            tags=self.tags.copy(),
            metadata=self.metadata.copy()
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "container_id": str(self.container_id),
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "has_content": self.has_content(),
            "is_readonly": self.is_readonly,
            "is_expired": self.is_expired(),
            "age_seconds": self.get_age_seconds(),
            "max_age_seconds": self.max_age_seconds,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ModelKeyValueContainer(BaseModel, Generic[K, V]):
    """
    Generic key-value container with type-safe operations.

    Provides type-safe storage and retrieval of key-value pairs with
    additional features like expiration, caching, and metadata.
    """

    # Container metadata
    container_id: UUID = Field(default_factory=uuid4, description="Unique container identifier")
    name: str | None = Field(default=None, description="Container name")

    # Key-value storage
    data: dict[K, V] = Field(default_factory=dict, description="Key-value data")

    # Container properties
    max_size: int | None = Field(default=None, description="Maximum number of entries")
    allow_overwrites: bool = Field(default=True, description="Allow overwriting existing keys")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation time")

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode='after')
    def validate_constraints(self) -> 'ModelKeyValueContainer[K, V]':
        """Validate container constraints."""
        if self.max_size is not None and len(self.data) > self.max_size:
            raise ValueError(f"Container size {len(self.data)} exceeds maximum {self.max_size}")
        return self

    def set(self, key: K, value: V) -> bool:
        """
        Set a key-value pair.

        Args:
            key: Key to set
            value: Value to associate with key

        Returns:
            True if set successfully, False if rejected
        """
        # Check if key exists and overwrites are not allowed
        if key in self.data and not self.allow_overwrites:
            return False

        # Check size limit for new keys
        if (key not in self.data and
            self.max_size is not None and
            len(self.data) >= self.max_size):
            return False

        self.data[key] = value
        return True

    def get(self, key: K) -> V | None:
        """Get value by key."""
        return self.data.get(key)

    def get_or_default(self, key: K, default: V) -> V:
        """Get value by key or return default."""
        return self.data.get(key, default)

    def has_key(self, key: K) -> bool:
        """Check if key exists."""
        return key in self.data

    def remove(self, key: K) -> bool:
        """
        Remove a key-value pair.

        Args:
            key: Key to remove

        Returns:
            True if removed, False if not found
        """
        if key in self.data:
            del self.data[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all key-value pairs."""
        self.data.clear()

    def size(self) -> int:
        """Get number of key-value pairs."""
        return len(self.data)

    def is_empty(self) -> bool:
        """Check if container is empty."""
        return len(self.data) == 0

    def keys(self) -> list[K]:
        """Get all keys."""
        return list(self.data.keys())

    def values(self) -> list[V]:
        """Get all values."""
        return list(self.data.values())

    def items(self) -> list[tuple[K, V]]:
        """Get all key-value pairs."""
        return list(self.data.items())

    def filter_by_key(self, predicate: Callable[[K], bool]) -> "ModelKeyValueContainer[K, V]":
        """
        Filter entries by key predicate.

        Args:
            predicate: Function that returns True for keys to keep

        Returns:
            New container with filtered entries
        """
        filtered_data = {k: v for k, v in self.data.items() if predicate(k)}
        return ModelKeyValueContainer[K, V](
            name=f"{self.name}_key_filtered" if self.name else None,
            data=filtered_data,
            max_size=self.max_size,
            allow_overwrites=self.allow_overwrites,
            metadata=self.metadata.copy()
        )

    def filter_by_value(self, predicate: Callable[[V], bool]) -> "ModelKeyValueContainer[K, V]":
        """
        Filter entries by value predicate.

        Args:
            predicate: Function that returns True for values to keep

        Returns:
            New container with filtered entries
        """
        filtered_data = {k: v for k, v in self.data.items() if predicate(v)}
        return ModelKeyValueContainer[K, V](
            name=f"{self.name}_value_filtered" if self.name else None,
            data=filtered_data,
            max_size=self.max_size,
            allow_overwrites=self.allow_overwrites,
            metadata=self.metadata.copy()
        )

    def map_values(self, mapper: Callable[[V], T]) -> "ModelKeyValueContainer[K, T]":
        """
        Map values to a new type.

        Args:
            mapper: Function to transform values

        Returns:
            New container with mapped values
        """
        mapped_data = {k: mapper(v) for k, v in self.data.items()}
        return ModelKeyValueContainer[K, T](
            name=f"{self.name}_mapped" if self.name else None,
            data=mapped_data,
            max_size=self.max_size,
            allow_overwrites=self.allow_overwrites,
            metadata=self.metadata.copy()
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "container_id": str(self.container_id),
            "name": self.name,
            "data": dict(self.data),  # Convert to regular dict
            "size": self.size(),
            "max_size": self.max_size,
            "allow_overwrites": self.allow_overwrites,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class ModelCachingContainer(ModelGenericContainer[T]):
    """
    Container with caching capabilities.

    Extends generic container with caching features like cache validation,
    refresh policies, and cache statistics.
    """

    # Caching properties
    cache_hit_count: int = Field(default=0, description="Number of cache hits")
    cache_miss_count: int = Field(default=0, description="Number of cache misses")
    last_access_time: datetime | None = Field(default=None, description="Last access time")
    auto_refresh: bool = Field(default=False, description="Auto-refresh expired content")

    model_config = {"arbitrary_types_allowed": True}

    def get_content_with_cache(self) -> T | None:
        """Get content with cache tracking."""
        self.last_access_time = datetime.now(UTC)

        if self.has_content():
            self.cache_hit_count += 1
            return self.content
        else:
            self.cache_miss_count += 1
            if self.auto_refresh and self.is_expired():
                # Could trigger refresh logic here
                pass
            return None

    def get_cache_hit_ratio(self) -> float:
        """Get cache hit ratio."""
        total_accesses = self.cache_hit_count + self.cache_miss_count
        if total_accesses == 0:
            return 0.0
        return self.cache_hit_count / total_accesses

    def reset_cache_stats(self) -> None:
        """Reset cache statistics."""
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        self.last_access_time = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with cache stats."""
        base_dict = super().to_dict()
        base_dict.update({
            "cache_hit_count": self.cache_hit_count,
            "cache_miss_count": self.cache_miss_count,
            "cache_hit_ratio": self.get_cache_hit_ratio(),
            "last_access_time": self.last_access_time.isoformat() if self.last_access_time else None,
            "auto_refresh": self.auto_refresh
        })
        return base_dict


# Factory functions for common container types
def create_container(content: Any | None = None, **kwargs: Any) -> ModelGenericContainer[Any]:
    """Create a generic container."""
    return ModelGenericContainer[Any](content=content, **kwargs)


def create_key_value_container(data: dict[Any, Any] | None = None, **kwargs: Any) -> ModelKeyValueContainer[Any, Any]:
    """Create a key-value container."""
    return ModelKeyValueContainer[Any, Any](data=data or {}, **kwargs)


def create_caching_container(content: Any | None = None, **kwargs: Any) -> ModelCachingContainer[Any]:
    """Create a caching container."""
    return ModelCachingContainer[Any](content=content, **kwargs)


# Export for use
__all__ = [
    "ModelGenericContainer",
    "ModelKeyValueContainer",
    "ModelCachingContainer",
    "Serializable",
    "Cacheable",
    "create_container",
    "create_key_value_container",
    "create_caching_container",
]