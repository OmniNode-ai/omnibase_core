# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for RegistryProvider."""

import concurrent.futures
import threading
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.providers import ModelProviderDescriptor
from omnibase_core.services.registry.registry_provider import RegistryProvider

# Fixed UUIDs for deterministic tests
TEST_UUID_1 = UUID("11111111-1111-1111-1111-111111111111")
TEST_UUID_2 = UUID("22222222-2222-2222-2222-222222222222")
TEST_UUID_3 = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def registry() -> RegistryProvider:
    """Fixture providing an empty RegistryProvider."""
    return RegistryProvider()


@pytest.fixture
def db_provider() -> ModelProviderDescriptor:
    """Fixture providing a database provider descriptor."""
    return ModelProviderDescriptor(
        provider_id=TEST_UUID_1,
        capabilities=["database.relational", "database.postgresql"],
        adapter="test.adapters.PostgresAdapter",
        connection_ref="secrets://postgres/primary",
        tags=["production", "primary"],
    )


@pytest.fixture
def cache_provider() -> ModelProviderDescriptor:
    """Fixture providing a cache provider descriptor."""
    return ModelProviderDescriptor(
        provider_id=TEST_UUID_2,
        capabilities=["cache.redis", "cache.distributed"],
        adapter="test.adapters.RedisAdapter",
        connection_ref="secrets://redis/cluster",
        tags=["production", "secondary"],
    )


@pytest.fixture
def staging_provider() -> ModelProviderDescriptor:
    """Fixture providing a staging provider descriptor."""
    return ModelProviderDescriptor(
        provider_id=TEST_UUID_3,
        capabilities=["database.relational"],
        adapter="test.adapters.PostgresAdapter",
        connection_ref="secrets://postgres/staging",
        tags=["staging"],
    )


@pytest.mark.unit
class TestRegistryProviderLifecycle:
    """Tests for register/unregister lifecycle."""

    def test_register_single_provider(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test registering a single provider."""
        registry.register(db_provider)

        assert len(registry) == 1
        assert str(db_provider.provider_id) in registry

    def test_register_multiple_providers(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test registering multiple providers."""
        registry.register(db_provider)
        registry.register(cache_provider)

        assert len(registry) == 2
        assert str(db_provider.provider_id) in registry
        assert str(cache_provider.provider_id) in registry

    def test_unregister_existing_provider(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test unregistering an existing provider returns True."""
        registry.register(db_provider)

        result = registry.unregister(str(db_provider.provider_id))

        assert result is True
        assert len(registry) == 0
        assert str(db_provider.provider_id) not in registry

    def test_unregister_nonexistent_provider(self, registry: RegistryProvider) -> None:
        """Test unregistering a nonexistent provider returns False."""
        result = registry.unregister("nonexistent-id")

        assert result is False

    def test_unregister_twice_returns_false_second_time(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test unregistering the same provider twice."""
        registry.register(db_provider)

        first_result = registry.unregister(str(db_provider.provider_id))
        second_result = registry.unregister(str(db_provider.provider_id))

        assert first_result is True
        assert second_result is False


@pytest.mark.unit
class TestRegistryProviderDuplicateHandling:
    """Tests for duplicate provider_id handling."""

    def test_duplicate_without_replace_raises_error(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test registering duplicate provider_id raises ModelOnexError."""
        registry.register(db_provider)

        with pytest.raises(ModelOnexError) as exc_info:
            registry.register(db_provider)

        assert "already registered" in str(exc_info.value)
        assert str(db_provider.provider_id) in str(exc_info.value)

    def test_duplicate_with_replace_true_succeeds(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test registering duplicate with replace=True overwrites."""
        registry.register(db_provider)

        # Create updated provider with same ID but different tags
        updated_provider = ModelProviderDescriptor(
            provider_id=db_provider.provider_id,
            capabilities=db_provider.capabilities,
            adapter=db_provider.adapter,
            connection_ref=db_provider.connection_ref,
            tags=["updated", "new-tag"],
        )

        registry.register(updated_provider, replace=True)

        assert len(registry) == 1
        retrieved = registry.get(str(db_provider.provider_id))
        assert retrieved is not None
        assert "updated" in retrieved.tags
        assert "new-tag" in retrieved.tags

    def test_replace_false_is_default(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test that replace=False is the default behavior."""
        registry.register(db_provider)

        # Call without replace parameter should fail
        with pytest.raises(ModelOnexError):
            registry.register(db_provider)


@pytest.mark.unit
class TestRegistryProviderGet:
    """Tests for get method."""

    def test_get_existing_provider(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test getting an existing provider returns it."""
        registry.register(db_provider)

        result = registry.get(str(db_provider.provider_id))

        assert result is not None
        assert result.provider_id == db_provider.provider_id
        assert result == db_provider

    def test_get_nonexistent_provider_returns_none(
        self, registry: RegistryProvider
    ) -> None:
        """Test getting a nonexistent provider returns None."""
        result = registry.get("nonexistent-id")

        assert result is None

    def test_get_after_unregister_returns_none(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test getting a provider after unregistering returns None."""
        registry.register(db_provider)
        registry.unregister(str(db_provider.provider_id))

        result = registry.get(str(db_provider.provider_id))

        assert result is None


@pytest.mark.unit
class TestRegistryProviderFindByCapability:
    """Tests for find_by_capability method."""

    def test_find_by_capability_single_match(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test finding providers with a matching capability."""
        registry.register(db_provider)

        results = registry.find_by_capability("database.relational")

        assert len(results) == 1
        assert results[0] == db_provider

    def test_find_by_capability_multiple_matches(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        staging_provider: ModelProviderDescriptor,
    ) -> None:
        """Test finding multiple providers with same capability."""
        registry.register(db_provider)
        registry.register(staging_provider)

        results = registry.find_by_capability("database.relational")

        assert len(results) == 2
        provider_ids = {p.provider_id for p in results}
        assert db_provider.provider_id in provider_ids
        assert staging_provider.provider_id in provider_ids

    def test_find_by_capability_no_match(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test finding providers with no matching capability returns empty list."""
        registry.register(db_provider)

        results = registry.find_by_capability("messaging.kafka")

        assert len(results) == 0

    def test_find_by_capability_empty_registry(
        self, registry: RegistryProvider
    ) -> None:
        """Test finding in empty registry returns empty list."""
        results = registry.find_by_capability("database.relational")

        assert len(results) == 0

    def test_find_by_capability_exact_match_required(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test that capability matching is exact (not partial)."""
        registry.register(db_provider)

        # Partial matches should not work
        assert len(registry.find_by_capability("database")) == 0
        assert len(registry.find_by_capability("relational")) == 0
        assert len(registry.find_by_capability("database.rel")) == 0


@pytest.mark.unit
class TestRegistryProviderFindByTags:
    """Tests for find_by_tags method."""

    def test_find_by_tags_any_match_default(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
        staging_provider: ModelProviderDescriptor,
    ) -> None:
        """Test find_by_tags with default match_all=False (any match)."""
        registry.register(db_provider)
        registry.register(cache_provider)
        registry.register(staging_provider)

        # Both production providers should match
        results = registry.find_by_tags(["production"])

        assert len(results) == 2
        provider_ids = {p.provider_id for p in results}
        assert db_provider.provider_id in provider_ids
        assert cache_provider.provider_id in provider_ids

    def test_find_by_tags_any_match_multiple_tags(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        staging_provider: ModelProviderDescriptor,
    ) -> None:
        """Test find_by_tags with multiple tags (any match)."""
        registry.register(db_provider)
        registry.register(staging_provider)

        # Either production OR staging should match
        results = registry.find_by_tags(["production", "staging"])

        assert len(results) == 2

    def test_find_by_tags_match_all_true(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test find_by_tags with match_all=True requires all tags."""
        registry.register(db_provider)  # production, primary
        registry.register(cache_provider)  # production, secondary

        # Only db_provider has both production AND primary
        results = registry.find_by_tags(["production", "primary"], match_all=True)

        assert len(results) == 1
        assert results[0] == db_provider

    def test_find_by_tags_match_all_no_matches(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test find_by_tags match_all with no full matches."""
        registry.register(db_provider)  # production, primary

        # db_provider has production but not staging
        results = registry.find_by_tags(["production", "staging"], match_all=True)

        assert len(results) == 0

    def test_find_by_tags_empty_tags_list(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test find_by_tags with empty tags list returns empty (any fails)."""
        registry.register(db_provider)

        # With match_all=False and empty tags, any() returns False
        results = registry.find_by_tags([])

        assert len(results) == 0

    def test_find_by_tags_empty_tags_match_all(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test find_by_tags with empty tags and match_all returns all."""
        registry.register(db_provider)

        # With match_all=True and empty tags, all() returns True (vacuous truth)
        results = registry.find_by_tags([], match_all=True)

        assert len(results) == 1

    def test_find_by_tags_no_matches(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test find_by_tags with no matching tags."""
        registry.register(db_provider)

        results = registry.find_by_tags(["nonexistent-tag"])

        assert len(results) == 0


@pytest.mark.unit
class TestRegistryProviderListAll:
    """Tests for list_all method."""

    def test_list_all_empty_registry(self, registry: RegistryProvider) -> None:
        """Test list_all on empty registry returns empty list."""
        results = registry.list_all()

        assert results == []

    def test_list_all_returns_all_providers(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test list_all returns all registered providers."""
        registry.register(db_provider)
        registry.register(cache_provider)

        results = registry.list_all()

        assert len(results) == 2
        provider_ids = {p.provider_id for p in results}
        assert db_provider.provider_id in provider_ids
        assert cache_provider.provider_id in provider_ids

    def test_list_all_preserves_insertion_order(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
        staging_provider: ModelProviderDescriptor,
    ) -> None:
        """Test list_all preserves insertion order."""
        registry.register(db_provider)
        registry.register(cache_provider)
        registry.register(staging_provider)

        results = registry.list_all()

        assert results[0] == db_provider
        assert results[1] == cache_provider
        assert results[2] == staging_provider

    def test_list_all_after_unregister(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test list_all after unregistering a provider."""
        registry.register(db_provider)
        registry.register(cache_provider)
        registry.unregister(str(db_provider.provider_id))

        results = registry.list_all()

        assert len(results) == 1
        assert results[0] == cache_provider


@pytest.mark.unit
class TestRegistryProviderListCapabilities:
    """Tests for list_capabilities method."""

    def test_list_capabilities_empty_registry(self, registry: RegistryProvider) -> None:
        """Test list_capabilities on empty registry returns empty set."""
        results = registry.list_capabilities()

        assert results == set()

    def test_list_capabilities_single_provider(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test list_capabilities with single provider."""
        registry.register(db_provider)

        results = registry.list_capabilities()

        assert results == {"database.relational", "database.postgresql"}

    def test_list_capabilities_multiple_providers(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test list_capabilities aggregates from all providers."""
        registry.register(db_provider)
        registry.register(cache_provider)

        results = registry.list_capabilities()

        expected = {
            "database.relational",
            "database.postgresql",
            "cache.redis",
            "cache.distributed",
        }
        assert results == expected

    def test_list_capabilities_deduplicates(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        staging_provider: ModelProviderDescriptor,
    ) -> None:
        """Test list_capabilities deduplicates shared capabilities."""
        registry.register(db_provider)
        registry.register(staging_provider)

        results = registry.list_capabilities()

        # Both have database.relational, but it should appear once
        assert "database.relational" in results
        # Count occurrences - should be exactly one
        assert len([c for c in results if c == "database.relational"]) == 1


@pytest.mark.unit
class TestRegistryProviderThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_register_unregister(self, registry: RegistryProvider) -> None:
        """Test concurrent register/unregister operations are thread-safe."""
        errors: list[Exception] = []
        num_operations = 100

        def register_provider(i: int) -> None:
            try:
                provider = ModelProviderDescriptor(
                    provider_id=uuid4(),
                    capabilities=["test.capability"],
                    adapter="test.Adapter",
                    connection_ref="env://TEST",
                    tags=[f"tag-{i}"],
                )
                registry.register(provider)
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(register_provider, i) for i in range(num_operations)
            ]
            concurrent.futures.wait(futures)

        assert len(errors) == 0
        assert len(registry) == num_operations

    def test_concurrent_read_operations(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test concurrent read operations are thread-safe."""
        registry.register(db_provider)
        registry.register(cache_provider)

        errors: list[Exception] = []
        num_operations = 100

        def read_operations() -> None:
            try:
                registry.get(str(db_provider.provider_id))
                registry.find_by_capability("database.relational")
                registry.find_by_tags(["production"])
                registry.list_all()
                registry.list_capabilities()
                len(registry)
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_operations) for _ in range(num_operations)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0

    def test_concurrent_register_and_read(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test concurrent register and read operations."""
        registry.register(db_provider)

        errors: list[Exception] = []
        stop_event = threading.Event()

        def reader() -> None:
            while not stop_event.is_set():
                try:
                    registry.list_all()
                    registry.find_by_capability("test.capability")
                except Exception as e:
                    errors.append(e)

        def writer() -> None:
            for i in range(50):
                try:
                    provider = ModelProviderDescriptor(
                        provider_id=uuid4(),
                        capabilities=["test.capability"],
                        adapter="test.Adapter",
                        connection_ref="env://TEST",
                    )
                    registry.register(provider)
                except Exception as e:
                    errors.append(e)

        # Start multiple reader threads
        reader_threads = [threading.Thread(target=reader) for _ in range(3)]
        for t in reader_threads:
            t.start()

        # Run writer
        writer_thread = threading.Thread(target=writer)
        writer_thread.start()
        writer_thread.join()

        # Stop readers
        stop_event.set()
        for t in reader_threads:
            t.join()

        assert len(errors) == 0


@pytest.mark.unit
class TestRegistryProviderClear:
    """Tests for clear method."""

    def test_clear_empty_registry(self, registry: RegistryProvider) -> None:
        """Test clearing an empty registry is safe."""
        registry.clear()

        assert len(registry) == 0

    def test_clear_removes_all_providers(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test clear removes all providers."""
        registry.register(db_provider)
        registry.register(cache_provider)
        assert len(registry) == 2

        registry.clear()

        assert len(registry) == 0
        assert registry.get(str(db_provider.provider_id)) is None
        assert registry.get(str(cache_provider.provider_id)) is None


@pytest.mark.unit
class TestRegistryProviderDunderMethods:
    """Tests for dunder methods (__len__, __contains__, __repr__)."""

    def test_len_empty(self, registry: RegistryProvider) -> None:
        """Test __len__ on empty registry."""
        assert len(registry) == 0

    def test_len_with_providers(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test __len__ with registered providers."""
        registry.register(db_provider)
        assert len(registry) == 1

        registry.register(cache_provider)
        assert len(registry) == 2

    def test_contains_registered(
        self, registry: RegistryProvider, db_provider: ModelProviderDescriptor
    ) -> None:
        """Test __contains__ for registered provider."""
        registry.register(db_provider)

        assert str(db_provider.provider_id) in registry

    def test_contains_not_registered(self, registry: RegistryProvider) -> None:
        """Test __contains__ for unregistered provider."""
        assert "nonexistent-id" not in registry

    def test_repr(self, registry: RegistryProvider) -> None:
        """Test __repr__ shows provider count."""
        assert "RegistryProvider(providers=0)" in repr(registry)

    def test_repr_with_providers(
        self,
        registry: RegistryProvider,
        db_provider: ModelProviderDescriptor,
        cache_provider: ModelProviderDescriptor,
    ) -> None:
        """Test __repr__ with registered providers."""
        registry.register(db_provider)
        registry.register(cache_provider)

        assert "RegistryProvider(providers=2)" in repr(registry)
