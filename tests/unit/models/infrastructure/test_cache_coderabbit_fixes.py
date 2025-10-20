"""
Tests for CodeRabbit issues #10, #11, #12, #13 - Cache implementation fixes.

These tests verify:
- Issue #10: EnumCacheEvictionPolicy enum usage
- Issue #11: Eviction policy validation at construction
- Issue #12: TTL precision (no rounding bugs)
- Issue #13: LRU vs LFU implementation correctness
"""

import time
from datetime import timedelta

import pytest

from omnibase_core.enums.enum_cache_eviction_policy import EnumCacheEvictionPolicy
from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache


class TestIssue10EnumUsage:
    """Test Issue #10: EnumCacheEvictionPolicy enum usage in config."""

    def test_config_uses_enum_not_string_pattern(self):
        """Verify config uses EnumCacheEvictionPolicy enum type."""
        # Create config with enum
        config = ModelComputeCacheConfig(eviction_policy=EnumCacheEvictionPolicy.LRU)
        assert config.eviction_policy == EnumCacheEvictionPolicy.LRU
        assert isinstance(config.eviction_policy, EnumCacheEvictionPolicy)

    def test_config_accepts_string_enum_values(self):
        """Verify config accepts string values that match enum (str, Enum pattern)."""
        # Since EnumCacheEvictionPolicy inherits from (str, Enum), it should accept strings
        config = ModelComputeCacheConfig(eviction_policy="lru")
        # Pydantic should coerce to enum
        assert config.eviction_policy == EnumCacheEvictionPolicy.LRU

    def test_config_default_is_enum(self):
        """Verify default eviction_policy is EnumCacheEvictionPolicy.LRU."""
        config = ModelComputeCacheConfig()
        assert config.eviction_policy == EnumCacheEvictionPolicy.LRU
        assert isinstance(config.eviction_policy, EnumCacheEvictionPolicy)


class TestIssue11ValidationAtConstruction:
    """Test Issue #11: Eviction policy validation at ModelComputeCache construction."""

    def test_valid_enum_passes(self):
        """Verify valid EnumCacheEvictionPolicy enum passes."""
        cache = ModelComputeCache(eviction_policy=EnumCacheEvictionPolicy.LRU)
        assert cache.eviction_policy == EnumCacheEvictionPolicy.LRU

        cache = ModelComputeCache(eviction_policy=EnumCacheEvictionPolicy.LFU)
        assert cache.eviction_policy == EnumCacheEvictionPolicy.LFU

        cache = ModelComputeCache(eviction_policy=EnumCacheEvictionPolicy.FIFO)
        assert cache.eviction_policy == EnumCacheEvictionPolicy.FIFO

    def test_valid_string_coerces_to_enum(self):
        """Verify valid string values coerce to enum."""
        cache = ModelComputeCache(eviction_policy="lru")
        assert cache.eviction_policy == EnumCacheEvictionPolicy.LRU

        cache = ModelComputeCache(eviction_policy="lfu")
        assert cache.eviction_policy == EnumCacheEvictionPolicy.LFU

        cache = ModelComputeCache(eviction_policy="fifo")
        assert cache.eviction_policy == EnumCacheEvictionPolicy.FIFO

    def test_invalid_string_raises_error(self):
        """Verify invalid eviction policy raises ValueError at construction."""
        with pytest.raises(ValueError, match="is not a valid EnumCacheEvictionPolicy"):
            ModelComputeCache(eviction_policy="invalid_policy")

        with pytest.raises(ValueError):
            ModelComputeCache(eviction_policy="random")


class TestIssue12TTLPrecision:
    """Test Issue #12: TTL seconds rounding bug - verify no truncation."""

    def test_ttl_seconds_no_truncation_short_durations(self):
        """Verify TTL doesn't truncate short durations (e.g., 59s → 0)."""
        # Test 59 seconds (should NOT become 0 minutes and be lost)
        cache = ModelComputeCache(ttl_seconds=59)
        assert cache.ttl == timedelta(seconds=59)
        assert cache.ttl.total_seconds() == 59

        # Test 1 second
        cache = ModelComputeCache(ttl_seconds=1)
        assert cache.ttl == timedelta(seconds=1)
        assert cache.ttl.total_seconds() == 1

        # Test 30 seconds
        cache = ModelComputeCache(ttl_seconds=30)
        assert cache.ttl == timedelta(seconds=30)
        assert cache.ttl.total_seconds() == 30

    def test_ttl_timedelta_precision_in_put(self):
        """Verify put() method preserves TTL precision."""
        cache = ModelComputeCache(ttl_seconds=45)  # 45 seconds

        # Put with default TTL
        cache.put("key1", "value1")

        # Verify entry exists immediately
        assert cache.get("key1") == "value1"

        # Put with custom TTL in minutes
        cache.put("key2", "value2", ttl_minutes=1)  # 60 seconds

        # Both should be retrievable
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

    def test_ttl_uses_timedelta_not_integer_division(self):
        """Verify TTL is stored as timedelta for precision."""
        cache = ModelComputeCache(ttl_seconds=90)  # 1.5 minutes

        # Verify internal storage uses timedelta
        assert isinstance(cache.ttl, timedelta)
        assert cache.ttl.total_seconds() == 90

        # default_ttl_minutes can use integer division, but ttl should be precise
        assert cache.default_ttl_minutes == 1  # Integer division is OK here
        assert cache.ttl.total_seconds() == 90  # But actual TTL is precise


class TestIssue13LRUvsLFU:
    """Test Issue #13: LRU vs LFU implementation correctness (CRITICAL BUG)."""

    def test_lru_uses_monotonic_timestamp(self):
        """Verify LRU uses monotonic() timestamp for recency, not access count."""
        cache = ModelComputeCache(
            max_size=3,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.LRU,
        )

        # Add entries with delays to ensure different timestamps
        cache.put("key1", "value1")
        time.sleep(0.01)  # Small delay

        cache.put("key2", "value2")
        time.sleep(0.01)

        cache.put("key3", "value3")
        time.sleep(0.01)

        # Access key1 multiple times (making it frequently accessed)
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")  # key1 has highest access count now

        time.sleep(0.01)

        # Access key2 once (making it most recently used)
        cache.get("key2")

        # Now add key4, forcing eviction
        # LRU should evict key3 (least recently used, accessed at insertion only)
        # NOT key2 (most recently accessed) or key1 (most frequently accessed)
        cache.put("key4", "value4")

        # Verify key3 was evicted (least recently used)
        assert cache.get("key3") is None, "LRU should evict key3 (least recently used)"

        # Verify key1 and key2 are still cached
        assert cache.get("key1") == "value1", "key1 should still be cached"
        assert cache.get("key2") == "value2", "key2 should still be cached"
        assert cache.get("key4") == "value4", "key4 should be cached"

    def test_lfu_uses_access_count(self):
        """Verify LFU uses access count, not timestamp."""
        cache = ModelComputeCache(
            max_size=3,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.LFU,
        )

        # Add entries
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 multiple times (making it frequently accessed)
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")  # key1: 4 accesses

        # Access key2 moderately
        cache.get("key2")
        cache.get("key2")  # key2: 2 accesses

        # key3: 0 accesses (only insertion)

        # Now add key4, forcing eviction
        # LFU should evict key3 (least frequently used, 0 accesses)
        cache.put("key4", "value4")

        # Verify key3 was evicted (least frequently used)
        assert (
            cache.get("key3") is None
        ), "LFU should evict key3 (least frequently used)"

        # Verify key1 and key2 are still cached
        assert cache.get("key1") == "value1", "key1 should still be cached"
        assert cache.get("key2") == "value2", "key2 should still be cached"
        assert cache.get("key4") == "value4", "key4 should be cached"

    def test_lru_evicts_by_recency_not_frequency(self):
        """Verify LRU evicts by recency (timestamp), NOT by frequency (access count)."""
        cache = ModelComputeCache(
            max_size=2,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.LRU,
        )

        # Add key1 and access it many times
        cache.put("key1", "value1")
        time.sleep(0.01)
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")  # key1 is frequently accessed

        time.sleep(0.01)

        # Add key2 and never access it again
        cache.put("key2", "value2")

        time.sleep(0.01)

        # Add key3, forcing eviction
        # LRU should evict key1 (least recently used, despite high access count)
        # NOT key2 (most recently added)
        cache.put("key3", "value3")

        # If LRU is using timestamp correctly:
        # - key1 was accessed before key2 was added, so key1 is less recent
        # - key2 was added most recently, so it's more recent than key1
        # Therefore, key1 should be evicted
        assert (
            cache.get("key1") is None
        ), "LRU should evict key1 (least recently used, despite high frequency)"
        assert cache.get("key2") == "value2", "key2 should still be cached"
        assert cache.get("key3") == "value3", "key3 should be cached"

    def test_lfu_evicts_by_frequency_not_recency(self):
        """Verify LFU evicts by frequency (access count), NOT by recency (timestamp)."""
        cache = ModelComputeCache(
            max_size=2,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.LFU,
        )

        # Add key1 and access it many times
        cache.put("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")  # key1: 3 accesses

        time.sleep(0.01)

        # Add key2 (only 1 access from insertion)
        cache.put("key2", "value2")

        time.sleep(0.01)

        # Add key3, forcing eviction
        # LFU should evict key2 (least frequently used, only 1 access)
        # NOT key1 (most frequently used, despite being accessed earlier)
        cache.put("key3", "value3")

        # Verify key2 was evicted (least frequently used)
        assert (
            cache.get("key2") is None
        ), "LFU should evict key2 (least frequently used)"
        assert (
            cache.get("key1") == "value1"
        ), "key1 should still be cached (most frequently used)"
        assert cache.get("key3") == "value3", "key3 should be cached"

    def test_fifo_evicts_oldest_insertion(self):
        """Verify FIFO evicts oldest insertion regardless of access."""
        cache = ModelComputeCache(
            max_size=3,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.FIFO,
        )

        # Add entries in order
        cache.put("key1", "value1")  # First in
        time.sleep(0.01)
        cache.put("key2", "value2")
        time.sleep(0.01)
        cache.put("key3", "value3")

        # Access key1 many times (shouldn't matter for FIFO)
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")

        # Add key4, forcing eviction
        # FIFO should evict key1 (first in, first out)
        cache.put("key4", "value4")

        # Verify key1 was evicted (first in)
        assert cache.get("key1") is None, "FIFO should evict key1 (first in)"
        assert cache.get("key2") == "value2", "key2 should still be cached"
        assert cache.get("key3") == "value3", "key3 should still be cached"
        assert cache.get("key4") == "value4", "key4 should be cached"


class TestCacheInternalStorage:
    """Test cache internal storage for LRU/LFU correctness."""

    def test_lru_internal_storage_uses_float_timestamp(self):
        """Verify LRU stores float timestamps (from monotonic()) in cache entries."""
        cache = ModelComputeCache(
            max_size=10,
            eviction_policy=EnumCacheEvictionPolicy.LRU,
        )

        cache.put("test_key", "test_value")

        # Access internal storage
        value, expiry, access_metric = cache._cache["test_key"]

        # LRU should store float timestamp
        assert isinstance(access_metric, float), "LRU should store float timestamp"
        assert access_metric > 0, "Timestamp should be positive"

    def test_lfu_internal_storage_uses_int_count(self):
        """Verify LFU stores int access counts in cache entries."""
        cache = ModelComputeCache(
            max_size=10,
            eviction_policy=EnumCacheEvictionPolicy.LFU,
        )

        cache.put("test_key", "test_value")

        # Access internal storage
        value, expiry, access_metric = cache._cache["test_key"]

        # LFU should store int count (starts at 1)
        assert isinstance(access_metric, int), "LFU should store int access count"
        assert access_metric == 1, "Initial access count should be 1"

        # Access the key
        cache.get("test_key")

        # Check updated count
        value, expiry, access_metric = cache._cache["test_key"]
        assert access_metric == 2, "Access count should increment to 2"

    def test_fifo_internal_storage_uses_insertion_order(self):
        """Verify FIFO stores insertion order in cache entries."""
        cache = ModelComputeCache(
            max_size=10,
            eviction_policy=EnumCacheEvictionPolicy.FIFO,
        )

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Check insertion orders
        _, _, order1 = cache._cache["key1"]
        _, _, order2 = cache._cache["key2"]
        _, _, order3 = cache._cache["key3"]

        assert order1 < order2 < order3, "FIFO should maintain insertion order"
        assert all(
            isinstance(o, int) for o in [order1, order2, order3]
        ), "FIFO should use int for order"
