# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceRegistryCapability.

Tests all aspects of the capability registry including:
- Basic register/unregister lifecycle
- Duplicate rejection (ModelOnexError when replace=False)
- Replace mode (replace=True allows overwrite)
- Get returns None for unknown capability_id
- list_all returns insertion order
- find_by_tags with match_all=True and match_all=False
- Thread safety with concurrent operations
- count property and clear method
- String representations

OMN-1156: ServiceRegistryCapability unit tests.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from omnibase_core.models.capabilities.model_capability_metadata import (
    ModelCapabilityMetadata,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.services.registry.service_registry_capability import (
    ServiceRegistryCapability,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def registry() -> ServiceRegistryCapability:
    """Create a fresh ServiceRegistryCapability instance."""
    return ServiceRegistryCapability()


@pytest.fixture
def sample_capability() -> ModelCapabilityMetadata:
    """Create a sample capability for testing."""
    return ModelCapabilityMetadata(
        capability="database.relational",
        name="Relational Database",
        version=ModelSemVer(major=1, minor=0, patch=0),
        description="SQL-based relational database operations",
        tags=("storage", "sql", "acid"),
        required_features=("query", "transactions"),
        optional_features=("json_support",),
        example_providers=("PostgreSQL", "MySQL"),
    )


@pytest.fixture
def sample_capability_v2() -> ModelCapabilityMetadata:
    """Create a v2 capability with same ID for replace testing."""
    return ModelCapabilityMetadata(
        capability="database.relational",
        name="Relational Database v2",
        version=ModelSemVer(major=2, minor=0, patch=0),
        description="Enhanced SQL-based relational database operations",
        tags=("storage", "sql", "acid", "v2"),
    )


@pytest.fixture
def nosql_capability() -> ModelCapabilityMetadata:
    """Create a NoSQL capability for testing."""
    return ModelCapabilityMetadata(
        capability="database.nosql",
        name="NoSQL Database",
        version=ModelSemVer(major=1, minor=0, patch=0),
        description="Document/key-value database operations",
        tags=("storage", "nosql", "flexible"),
    )


@pytest.fixture
def cache_capability() -> ModelCapabilityMetadata:
    """Create a cache capability for testing."""
    return ModelCapabilityMetadata(
        capability="cache.memory",
        name="In-Memory Cache",
        version=ModelSemVer(major=1, minor=0, patch=0),
        description="Fast in-memory caching",
        tags=("cache", "memory", "fast"),
    )


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityInstantiation:
    """Tests for registry instantiation."""

    def test_empty_registry_on_creation(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test that a new registry is empty."""
        assert registry.count == 0
        assert registry.list_all() == []

    def test_registry_has_lock(self, registry: ServiceRegistryCapability) -> None:
        """Test that registry has an RLock for thread safety."""
        assert hasattr(registry, "_lock")
        assert isinstance(registry._lock, type(threading.RLock()))


# =============================================================================
# Registration Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityRegistration:
    """Tests for capability registration."""

    def test_register_single_capability(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test registering a single capability."""
        registry.register(sample_capability)

        assert registry.count == 1
        assert registry.get("database.relational") == sample_capability

    def test_register_multiple_capabilities(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
        cache_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test registering multiple capabilities."""
        registry.register(sample_capability)
        registry.register(nosql_capability)
        registry.register(cache_capability)

        assert registry.count == 3
        assert registry.get("database.relational") == sample_capability
        assert registry.get("database.nosql") == nosql_capability
        assert registry.get("cache.memory") == cache_capability

    def test_register_duplicate_raises_model_onex_error(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that registering a duplicate capability_id raises ModelOnexError."""
        registry.register(sample_capability)

        with pytest.raises(ModelOnexError) as exc_info:
            registry.register(sample_capability)

        assert "database.relational" in str(exc_info.value)
        assert "already registered" in str(exc_info.value)
        assert "replace=True" in str(exc_info.value)

    def test_register_with_replace_true_overwrites(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        sample_capability_v2: ModelCapabilityMetadata,
    ) -> None:
        """Test that replace=True allows overwriting."""
        registry.register(sample_capability)
        result1 = registry.get("database.relational")
        assert result1 is not None
        assert result1 == sample_capability
        assert result1.name == "Relational Database"

        registry.register(sample_capability_v2, replace=True)

        assert registry.count == 1  # Still one capability
        result2 = registry.get("database.relational")
        assert result2 is not None
        assert result2 == sample_capability_v2
        assert result2.name == "Relational Database v2"

    def test_register_first_time_with_replace_true(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that replace=True works for first registration too."""
        registry.register(sample_capability, replace=True)

        assert registry.count == 1
        assert registry.get("database.relational") == sample_capability


# =============================================================================
# Unregistration Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityUnregistration:
    """Tests for capability unregistration."""

    def test_unregister_existing_capability(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test unregistering an existing capability returns True."""
        registry.register(sample_capability)
        assert registry.count == 1

        result = registry.unregister("database.relational")

        assert result is True
        assert registry.count == 0
        assert registry.get("database.relational") is None

    def test_unregister_nonexistent_capability(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test unregistering a nonexistent capability returns False."""
        result = registry.unregister("nonexistent.capability")

        assert result is False

    def test_unregister_twice_returns_false_second_time(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that unregistering twice returns False the second time."""
        registry.register(sample_capability)

        first_result = registry.unregister("database.relational")
        second_result = registry.unregister("database.relational")

        assert first_result is True
        assert second_result is False

    def test_unregister_preserves_other_capabilities(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that unregistering one capability preserves others."""
        registry.register(sample_capability)
        registry.register(nosql_capability)

        registry.unregister("database.relational")

        assert registry.count == 1
        assert registry.get("database.relational") is None
        assert registry.get("database.nosql") == nosql_capability


# =============================================================================
# Get Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityGet:
    """Tests for capability lookup."""

    def test_get_existing_capability(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test getting an existing capability."""
        registry.register(sample_capability)

        result = registry.get("database.relational")

        assert result == sample_capability
        assert result.name == "Relational Database"

    def test_get_nonexistent_capability_returns_none(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test getting a nonexistent capability returns None."""
        result = registry.get("nonexistent.capability")

        assert result is None

    def test_get_after_unregister_returns_none(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that get returns None after unregistration."""
        registry.register(sample_capability)
        registry.unregister("database.relational")

        result = registry.get("database.relational")

        assert result is None


# =============================================================================
# List All Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityListAll:
    """Tests for list_all method."""

    def test_list_all_empty_registry(self, registry: ServiceRegistryCapability) -> None:
        """Test list_all on empty registry."""
        result = registry.list_all()

        assert result == []
        assert isinstance(result, list)

    def test_list_all_single_capability(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test list_all with single capability."""
        registry.register(sample_capability)

        result = registry.list_all()

        assert len(result) == 1
        assert result[0] == sample_capability

    def test_list_all_preserves_insertion_order(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
        cache_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that list_all preserves insertion order."""
        registry.register(sample_capability)
        registry.register(nosql_capability)
        registry.register(cache_capability)

        result = registry.list_all()

        assert len(result) == 3
        assert result[0] == sample_capability
        assert result[1] == nosql_capability
        assert result[2] == cache_capability

    def test_list_all_returns_copy(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that list_all returns a copy, not the internal list."""
        registry.register(sample_capability)

        result1 = registry.list_all()
        result2 = registry.list_all()

        assert result1 is not result2
        assert result1 == result2


# =============================================================================
# Find By Tags Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityFindByTags:
    """Tests for find_by_tags method."""

    def test_find_by_tags_empty_registry(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test find_by_tags on empty registry."""
        result = registry.find_by_tags(["storage"])

        assert result == []

    def test_find_by_tags_single_tag_match(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
        cache_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with single tag finds matches."""
        registry.register(sample_capability)  # tags: storage, sql, acid
        registry.register(nosql_capability)  # tags: storage, nosql, flexible
        registry.register(cache_capability)  # tags: cache, memory, fast

        result = registry.find_by_tags(["storage"])

        assert len(result) == 2
        assert sample_capability in result
        assert nosql_capability in result
        assert cache_capability not in result

    def test_find_by_tags_match_any_default(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
        cache_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with multiple tags matches ANY (default)."""
        registry.register(sample_capability)  # tags: storage, sql, acid
        registry.register(nosql_capability)  # tags: storage, nosql, flexible
        registry.register(cache_capability)  # tags: cache, memory, fast

        result = registry.find_by_tags(["sql", "cache"])

        assert len(result) == 2
        assert sample_capability in result  # has sql
        assert cache_capability in result  # has cache
        assert nosql_capability not in result  # has neither

    def test_find_by_tags_match_all_true(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with match_all=True requires ALL tags."""
        registry.register(sample_capability)  # tags: storage, sql, acid
        registry.register(nosql_capability)  # tags: storage, nosql, flexible

        result = registry.find_by_tags(["storage", "sql"], match_all=True)

        assert len(result) == 1
        assert sample_capability in result
        assert nosql_capability not in result

    def test_find_by_tags_match_all_no_matches(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with match_all=True returns empty when no match."""
        registry.register(sample_capability)  # tags: storage, sql, acid
        registry.register(nosql_capability)  # tags: storage, nosql, flexible

        result = registry.find_by_tags(["sql", "nosql"], match_all=True)

        assert result == []

    def test_find_by_tags_preserves_insertion_order(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that find_by_tags preserves insertion order."""
        registry.register(sample_capability)
        registry.register(nosql_capability)

        result = registry.find_by_tags(["storage"])

        assert result[0] == sample_capability
        assert result[1] == nosql_capability

    def test_find_by_tags_no_matches(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with no matching tags."""
        registry.register(sample_capability)

        result = registry.find_by_tags(["nonexistent_tag"])

        assert result == []

    def test_find_by_tags_empty_tags_list_match_any(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with empty tags list (match_any returns none)."""
        registry.register(sample_capability)

        # With empty tags list and match_all=False, any() returns False
        result = registry.find_by_tags([])

        assert result == []

    def test_find_by_tags_empty_tags_list_match_all(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test find_by_tags with empty tags list returns empty (both modes)."""
        registry.register(sample_capability)

        # Empty tag list matches nothing - searching for zero tags returns zero results.
        # This avoids Python's `all([]) == True` trap.
        result = registry.find_by_tags([], match_all=True)

        assert result == []


# =============================================================================
# Count and Clear Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityCountAndClear:
    """Tests for count property and clear method."""

    def test_count_empty_registry(self, registry: ServiceRegistryCapability) -> None:
        """Test count on empty registry."""
        assert registry.count == 0

    def test_count_after_registrations(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test count after registrations."""
        registry.register(sample_capability)
        assert registry.count == 1

        registry.register(nosql_capability)
        assert registry.count == 2

    def test_count_after_unregistration(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test count after unregistration."""
        registry.register(sample_capability)
        assert registry.count == 1

        registry.unregister("database.relational")
        assert registry.count == 0

    def test_clear_empty_registry(self, registry: ServiceRegistryCapability) -> None:
        """Test clear on empty registry (no error)."""
        registry.clear()
        assert registry.count == 0

    def test_clear_removes_all_capabilities(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
        cache_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test that clear removes all capabilities."""
        registry.register(sample_capability)
        registry.register(nosql_capability)
        registry.register(cache_capability)
        assert registry.count == 3

        registry.clear()

        assert registry.count == 0
        assert registry.list_all() == []
        assert registry.get("database.relational") is None


# =============================================================================
# String Representation Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityRepresentation:
    """Tests for string representations."""

    def test_str_empty_registry(self, registry: ServiceRegistryCapability) -> None:
        """Test str representation of empty registry."""
        assert str(registry) == "ServiceRegistryCapability[count=0]"

    def test_str_with_capabilities(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test str representation with capabilities."""
        registry.register(sample_capability)
        registry.register(nosql_capability)

        assert str(registry) == "ServiceRegistryCapability[count=2]"

    def test_repr_empty_registry(self, registry: ServiceRegistryCapability) -> None:
        """Test repr of empty registry."""
        result = repr(registry)

        assert "ServiceRegistryCapability" in result
        assert "[]" in result or "capabilities" in result

    def test_repr_with_capabilities(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test repr with capabilities shows IDs."""
        registry.register(sample_capability)
        registry.register(nosql_capability)

        result = repr(registry)

        assert "ServiceRegistryCapability" in result
        assert "database.relational" in result
        assert "database.nosql" in result


# =============================================================================
# Thread Safety Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_registrations(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test concurrent registrations from multiple threads."""
        num_capabilities = 100
        errors: list[Exception] = []

        def register_capability(i: int) -> None:
            try:
                cap = ModelCapabilityMetadata(
                    capability=f"cap.n{i}",
                    name=f"Capability {i}",
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    description=f"Description {i}",
                    tags=(f"tag{i}",),
                )
                registry.register(cap)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(register_capability, i) for i in range(num_capabilities)
            ]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        assert len(errors) == 0, f"Errors during registration: {errors}"
        assert registry.count == num_capabilities

    def test_concurrent_reads_and_writes(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test concurrent reads and writes."""
        registry.register(sample_capability)
        errors: list[Exception] = []
        results: list[ModelCapabilityMetadata | None] = []
        lock = threading.Lock()
        writer_counter = [0]  # Mutable counter for unique IDs

        def reader() -> None:
            try:
                for _ in range(50):
                    result = registry.get("database.relational")
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        def writer() -> None:
            try:
                for _ in range(50):
                    with lock:
                        unique_id = writer_counter[0]
                        writer_counter[0] += 1
                    cap = ModelCapabilityMetadata(
                        capability=f"writer.n{unique_id}",
                        name=f"Writer Cap {unique_id}",
                        version=ModelSemVer(major=1, minor=0, patch=0),
                        description=f"Description {unique_id}",
                    )
                    registry.register(cap)
            except Exception as e:
                with lock:
                    errors.append(e)

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            for _ in range(3):
                futures.append(executor.submit(reader))
            for _ in range(3):
                futures.append(executor.submit(writer))

            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
        # Original capability should always be accessible
        assert all(r == sample_capability for r in results if r is not None)

    def test_concurrent_register_unregister(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test concurrent register and unregister operations."""
        num_ops = 50
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                cap_id = f"cap.n{i % 10}"
                cap = ModelCapabilityMetadata(
                    capability=cap_id,
                    name=f"Cap {i}",
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    description=f"Description {i}",
                )
                # Try to register (may fail if exists)
                try:
                    registry.register(cap)
                except ModelOnexError:
                    pass  # Expected for duplicates

                # Try to unregister
                registry.unregister(cap_id)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(num_ops)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Errors during concurrent ops: {errors}"

    def test_concurrent_list_all(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
        nosql_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test concurrent list_all operations."""
        registry.register(sample_capability)
        registry.register(nosql_capability)
        errors: list[Exception] = []
        results: list[list[ModelCapabilityMetadata]] = []
        lock = threading.Lock()

        def list_worker() -> None:
            try:
                for _ in range(20):
                    result = registry.list_all()
                    with lock:
                        results.append(result)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(list_worker) for _ in range(5)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Errors during concurrent list_all: {errors}"
        # All results should have 2 items
        assert all(len(r) == 2 for r in results)


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestServiceRegistryCapabilityEdgeCases:
    """Tests for edge cases."""

    def test_capability_with_dots_in_id(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test capability ID with dots (hierarchical naming)."""
        cap = ModelCapabilityMetadata(
            capability="cloud.aws.s3.storage",
            name="AWS S3 Storage",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Amazon S3 storage capability",
        )
        registry.register(cap)

        result = registry.get("cloud.aws.s3.storage")
        assert result == cap

    def test_capability_with_underscores_and_numbers(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test capability ID with underscores and numbers (valid characters)."""
        cap = ModelCapabilityMetadata(
            capability="api_v2.gateway",
            name="API Gateway v2",
            version=ModelSemVer(major=2, minor=0, patch=0),
            description="API gateway capability",
        )
        registry.register(cap)

        result = registry.get("api_v2.gateway")
        assert result == cap

    def test_reregister_after_unregister(
        self,
        registry: ServiceRegistryCapability,
        sample_capability: ModelCapabilityMetadata,
    ) -> None:
        """Test re-registering after unregistering (no ValueError)."""
        registry.register(sample_capability)
        registry.unregister("database.relational")

        # Should not raise
        registry.register(sample_capability)
        assert registry.count == 1
        assert registry.get("database.relational") == sample_capability

    def test_find_by_tags_with_capability_no_tags(
        self, registry: ServiceRegistryCapability
    ) -> None:
        """Test find_by_tags when capability has no tags."""
        cap = ModelCapabilityMetadata(
            capability="no.tags",
            name="No Tags Capability",
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="A capability with no tags",
            tags=(),  # Empty tags
        )
        registry.register(cap)

        # Searching for specific tag should not find capability with no tags
        result = registry.find_by_tags(["anytag"])
        assert result == []

        # Empty tag list returns empty - searching for zero tags matches nothing
        result = registry.find_by_tags([], match_all=True)
        assert result == []
