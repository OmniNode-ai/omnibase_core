# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ComputationCache - Caching layer for expensive computations.
"""

from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.infrastructure.infra_computation_cache import ComputationCache


@pytest.mark.unit
class TestComputationCacheInit:
    """Test ComputationCache initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        cache = ComputationCache()
        assert cache.max_size == 1000
        assert cache.default_ttl_minutes == 30
        assert cache._cache == {}

    def test_init_with_custom_max_size(self):
        """Test initialization with custom max_size."""
        cache = ComputationCache(max_size=500)
        assert cache.max_size == 500
        assert cache.default_ttl_minutes == 30

    def test_init_with_custom_ttl(self):
        """Test initialization with custom TTL."""
        cache = ComputationCache(default_ttl_minutes=60)
        assert cache.max_size == 1000
        assert cache.default_ttl_minutes == 60

    def test_init_with_all_custom_parameters(self):
        """Test initialization with all custom parameters."""
        cache = ComputationCache(max_size=200, default_ttl_minutes=15)
        assert cache.max_size == 200
        assert cache.default_ttl_minutes == 15
        assert cache._cache == {}


@pytest.mark.unit
class TestComputationCacheGet:
    """Test ComputationCache get operations."""

    def test_get_cache_miss(self):
        """Test get() returns None for non-existent key."""
        cache = ComputationCache()
        result = cache.get("missing_key")
        assert result is None

    def test_get_cache_hit(self):
        """Test get() returns cached value for existing key."""
        cache = ComputationCache()
        cache.put("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"

    def test_get_increments_access_count(self):
        """Test get() increments access count."""
        cache = ComputationCache()
        cache.put("test_key", "test_value")

        # Initial access count is 1 from put()
        _, _, access_count = cache._cache["test_key"]
        assert access_count == 1

        # First get increments to 2
        cache.get("test_key")
        _, _, access_count = cache._cache["test_key"]
        assert access_count == 2

        # Second get increments to 3
        cache.get("test_key")
        _, _, access_count = cache._cache["test_key"]
        assert access_count == 3

    def test_get_expired_entry_returns_none(self):
        """Test get() returns None and removes expired entry."""
        cache = ComputationCache()

        # Manually create an expired entry (use UTC for timezone-aware comparison)
        expired_time = datetime.now(UTC) - timedelta(minutes=1)
        cache._cache["expired_key"] = ("value", expired_time, 1)

        result = cache.get("expired_key")
        assert result is None
        assert "expired_key" not in cache._cache

    def test_get_preserves_non_expired_entry(self):
        """Test get() preserves and returns non-expired entry."""
        cache = ComputationCache(default_ttl_minutes=1)
        cache.put("valid_key", "valid_value")

        # Immediately get should work
        result = cache.get("valid_key")
        assert result == "valid_value"
        assert "valid_key" in cache._cache

    def test_get_multiple_keys(self):
        """Test get() works correctly with multiple keys."""
        cache = ComputationCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"


@pytest.mark.unit
class TestComputationCachePut:
    """Test ComputationCache put operations."""

    def test_put_simple_value(self):
        """Test put() stores simple value."""
        cache = ComputationCache()
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_put_with_default_ttl(self):
        """Test put() uses default TTL when not specified."""
        cache = ComputationCache(default_ttl_minutes=30)
        cache.put("key", "value")

        _, expiry, _ = cache._cache["key"]
        expected_expiry = datetime.now(UTC) + timedelta(minutes=30)

        # Allow 1 second tolerance for execution time
        assert abs((expiry - expected_expiry).total_seconds()) < 1

    def test_put_with_custom_ttl(self):
        """Test put() uses custom TTL when specified."""
        cache = ComputationCache(default_ttl_minutes=30)
        cache.put("key", "value", ttl_minutes=60)

        _, expiry, _ = cache._cache["key"]
        expected_expiry = datetime.now(UTC) + timedelta(minutes=60)

        # Allow 1 second tolerance
        assert abs((expiry - expected_expiry).total_seconds()) < 1

    def test_put_initializes_access_count_to_one(self):
        """Test put() initializes access count to 1."""
        cache = ComputationCache()
        cache.put("key", "value")

        _, _, access_count = cache._cache["key"]
        assert access_count == 1

    def test_put_triggers_eviction_when_at_capacity(self):
        """Test put() triggers LRU eviction when at capacity."""
        cache = ComputationCache(max_size=3)

        # Fill cache to capacity
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key2 and key3 to increase their access counts
        cache.get("key2")
        cache.get("key3")

        # Adding key4 should evict key1 (lowest access count)
        cache.put("key4", "value4")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_put_complex_objects(self):
        """Test put() can store complex objects."""
        cache = ComputationCache()

        # Dictionary
        cache.put("dict", {"nested": "value"})
        assert cache.get("dict") == {"nested": "value"}

        # List
        cache.put("list", [1, 2, 3])
        assert cache.get("list") == [1, 2, 3]

        # Tuple
        cache.put("tuple", (1, 2, 3))
        assert cache.get("tuple") == (1, 2, 3)

    def test_put_overwrites_existing_key(self):
        """Test put() overwrites existing key with new value."""
        cache = ComputationCache()
        cache.put("key", "value1")
        assert cache.get("key") == "value1"

        cache.put("key", "value2")
        assert cache.get("key") == "value2"


@pytest.mark.unit
class TestComputationCacheEvictLRU:
    """Test ComputationCache LRU eviction."""

    def test_evict_lru_removes_least_accessed_item(self):
        """Test _evict_lru() removes item with lowest access count."""
        cache = ComputationCache(max_size=10)

        # Add items with different access patterns
        cache.put("key1", "value1")  # access_count=1
        cache.put("key2", "value2")  # access_count=1
        cache.put("key3", "value3")  # access_count=1

        # Increase access counts
        cache.get("key2")  # key2 access_count=2
        cache.get("key3")  # key3 access_count=2
        cache.get("key3")  # key3 access_count=3

        # Manually trigger eviction
        cache._evict_lru()

        # key1 should be evicted (lowest access count)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_evict_lru_on_empty_cache(self):
        """Test _evict_lru() handles empty cache gracefully."""
        cache = ComputationCache()
        cache._evict_lru()  # Should not raise error
        assert cache._cache == {}


@pytest.mark.unit
class TestComputationCacheClear:
    """Test ComputationCache clear operations."""

    def test_clear_empty_cache(self):
        """Test clear() on empty cache."""
        cache = ComputationCache()
        cache.clear()
        assert cache._cache == {}

    def test_clear_populated_cache(self):
        """Test clear() removes all entries."""
        cache = ComputationCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        assert len(cache._cache) == 3

        cache.clear()

        assert cache._cache == {}
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None


@pytest.mark.unit
class TestComputationCacheGetStats:
    """Test ComputationCache statistics."""

    def test_get_stats_empty_cache(self):
        """Test get_stats() on empty cache."""
        cache = ComputationCache(max_size=500)
        stats = cache.get_stats()

        assert stats["total_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["max_size"] == 500

    def test_get_stats_with_valid_entries(self):
        """Test get_stats() with valid entries."""
        cache = ComputationCache(max_size=100)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        stats = cache.get_stats()

        assert stats["total_entries"] == 3
        assert stats["expired_entries"] == 0
        assert stats["valid_entries"] == 3
        assert stats["max_size"] == 100

    def test_get_stats_with_expired_entries(self):
        """Test get_stats() counts expired entries correctly."""
        cache = ComputationCache()

        # Add some valid entries
        cache.put("valid1", "value1", ttl_minutes=60)
        cache.put("valid2", "value2", ttl_minutes=60)

        # Manually add expired entries (use UTC for timezone-aware comparison)
        expired_time = datetime.now(UTC) - timedelta(minutes=1)
        cache._cache["expired1"] = ("value", expired_time, 1)
        cache._cache["expired2"] = ("value", expired_time, 1)

        stats = cache.get_stats()

        assert stats["total_entries"] == 4
        assert stats["expired_entries"] == 2
        assert stats["valid_entries"] == 2

    def test_get_stats_mixed_entries(self):
        """Test get_stats() with mix of valid and expired entries."""
        cache = ComputationCache(max_size=50)

        # Valid entry
        cache.put("valid", "value", ttl_minutes=30)

        # Expired entry (use UTC for timezone-aware comparison)
        expired_time = datetime.now(UTC) - timedelta(minutes=1)
        cache._cache["expired"] = ("value", expired_time, 1)

        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1
        assert stats["valid_entries"] == 1
        assert stats["max_size"] == 50


@pytest.mark.unit
class TestComputationCacheIntegration:
    """Integration tests for ComputationCache."""

    def test_full_cache_lifecycle(self):
        """Test complete cache lifecycle: put, get, expire, evict."""
        cache = ComputationCache(max_size=3, default_ttl_minutes=1)

        # Add entries
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Verify all present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # Check stats
        stats = cache.get_stats()
        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 3

        # Trigger eviction by adding another entry
        cache.put("key4", "value4")

        # key1 should be evicted (lowest access count after puts)
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

        # Clear all
        cache.clear()
        stats = cache.get_stats()
        assert stats["total_entries"] == 0

    def test_cache_behavior_under_load(self):
        """Test cache behavior with many operations."""
        cache = ComputationCache(max_size=10)

        # Add many entries
        for i in range(15):
            cache.put(f"key{i}", f"value{i}")

        # Only last 10 should remain
        stats = cache.get_stats()
        assert stats["total_entries"] <= 10

        # Early keys should be evicted
        assert cache.get("key0") is None
        assert cache.get("key1") is None

        # Recent keys should exist
        assert cache.get("key14") == "value14"
        assert cache.get("key13") == "value13"

    def test_ttl_enforcement(self):
        """Test that TTL is properly enforced."""
        cache = ComputationCache(default_ttl_minutes=1)

        # Add entry that will expire soon (use UTC for timezone-aware comparison)
        expired_time = datetime.now(UTC) - timedelta(seconds=1)
        cache._cache["expired_key"] = ("value", expired_time, 1)

        # Try to get expired entry
        result = cache.get("expired_key")
        assert result is None

        # Entry should be removed
        assert "expired_key" not in cache._cache
