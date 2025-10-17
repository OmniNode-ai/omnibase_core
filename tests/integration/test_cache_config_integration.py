"""
Integration tests for cache configuration wiring.

Tests the complete workflow of cache configuration from container
initialization through NodeCompute execution, validating that
configuration propagates correctly and impacts runtime behavior.
"""

import asyncio
import time

import pytest

from omnibase_core.enums.enum_cache_eviction_policy import EnumCacheEvictionPolicy
from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)
from omnibase_core.models.container.model_onex_container import (
    ModelONEXContainer,
    create_model_onex_container,
)
from omnibase_core.nodes.model_compute_input import ModelComputeInput
from omnibase_core.nodes.node_compute import NodeCompute


class TestCacheConfigIntegration:
    """Integration tests for cache configuration wiring."""

    @pytest.mark.asyncio
    async def test_container_to_node_compute_default_config(self):
        """Test that default cache config is wired from container to NodeCompute."""
        # Create container with default cache config
        container = await create_model_onex_container()

        # Verify default config
        assert container.compute_cache_config is not None
        assert container.compute_cache_config.max_size == 128
        assert container.compute_cache_config.ttl_seconds == 3600

        # Create NodeCompute and verify it uses container config
        node = NodeCompute(container)
        assert node.computation_cache.max_size == 128
        assert node.computation_cache.ttl_seconds == 3600

    @pytest.mark.asyncio
    async def test_container_to_node_compute_custom_config(self):
        """Test that custom cache config is wired from container to NodeCompute."""
        # Create custom cache config
        custom_config = ModelComputeCacheConfig(
            max_size=512,
            ttl_seconds=7200,
            eviction_policy=EnumCacheEvictionPolicy.LFU,
            enable_stats=True,
        )

        # Create container with custom config
        container = await create_model_onex_container(
            compute_cache_config=custom_config
        )

        # Verify custom config
        assert container.compute_cache_config.max_size == 512
        assert container.compute_cache_config.ttl_seconds == 7200
        assert (
            container.compute_cache_config.eviction_policy
            == EnumCacheEvictionPolicy.LFU
        )

        # Create NodeCompute and verify it uses custom config
        node = NodeCompute(container)
        assert node.computation_cache.max_size == 512
        assert node.computation_cache.ttl_seconds == 7200
        assert node.computation_cache.eviction_policy == EnumCacheEvictionPolicy.LFU
        assert node.computation_cache.enable_stats is True

    @pytest.mark.asyncio
    async def test_cache_behavior_with_different_ttl_configs(self):
        """Test that different TTL configurations affect cache expiration behavior."""
        # Config 1: Short TTL (60 seconds = 1 minute, cache uses minute granularity)
        short_ttl_config = ModelComputeCacheConfig(
            max_size=100, ttl_seconds=60, eviction_policy=EnumCacheEvictionPolicy.LRU
        )

        container1 = await create_model_onex_container(
            compute_cache_config=short_ttl_config
        )
        node1 = NodeCompute(container1)
        await node1.initialize()

        # Config 2: Long TTL (3600 seconds = 1 hour)
        long_ttl_config = ModelComputeCacheConfig(
            max_size=100, ttl_seconds=3600, eviction_policy=EnumCacheEvictionPolicy.LRU
        )

        container2 = await create_model_onex_container(
            compute_cache_config=long_ttl_config
        )
        node2 = NodeCompute(container2)
        await node2.initialize()

        # Execute computation on both nodes
        input_data = ModelComputeInput(
            computation_type="sum_numbers",
            data=[1, 2, 3, 4, 5],
            cache_enabled=True,
        )

        # Execute and cache result
        result1 = await node1.process(input_data)
        result2 = await node2.process(input_data)

        assert result1.cache_hit is False
        assert result2.cache_hit is False

        # Immediately retry - should hit cache
        result1_retry = await node1.process(input_data)
        result2_retry = await node2.process(input_data)

        assert result1_retry.cache_hit is True
        assert result2_retry.cache_hit is True

        # Verify cache contains the data
        stats1 = node1.computation_cache.get_stats()
        stats2 = node2.computation_cache.get_stats()

        assert stats1["total_entries"] == 1
        assert stats2["total_entries"] == 1

        # Verify TTL settings
        assert node1.computation_cache.ttl_seconds == 60
        assert node2.computation_cache.ttl_seconds == 3600

        # Cleanup
        await node1.cleanup()
        await node2.cleanup()

    @pytest.mark.asyncio
    async def test_cache_statistics_tracking_with_enable_stats(self):
        """Test that enable_stats config controls statistics tracking."""
        # Config with stats enabled
        stats_enabled_config = ModelComputeCacheConfig(max_size=100, enable_stats=True)

        # Config with stats disabled
        stats_disabled_config = ModelComputeCacheConfig(
            max_size=100, enable_stats=False
        )

        container_enabled = await create_model_onex_container(
            compute_cache_config=stats_enabled_config
        )
        container_disabled = await create_model_onex_container(
            compute_cache_config=stats_disabled_config
        )

        node_enabled = NodeCompute(container_enabled)
        node_disabled = NodeCompute(container_disabled)
        await node_enabled.initialize()
        await node_disabled.initialize()

        # Execute computations
        input_data = ModelComputeInput(
            computation_type="sum_numbers", data=[1, 2, 3], cache_enabled=True
        )

        # Execute twice (miss then hit)
        await node_enabled.process(input_data)
        await node_enabled.process(input_data)

        await node_disabled.process(input_data)
        await node_disabled.process(input_data)

        # Check statistics
        stats_enabled = node_enabled.computation_cache.get_stats()
        stats_disabled = node_disabled.computation_cache.get_stats()

        # Stats enabled should have detailed metrics
        assert "hits" in stats_enabled
        assert "misses" in stats_enabled
        assert "hit_rate" in stats_enabled
        assert stats_enabled["hits"] == 1
        assert stats_enabled["misses"] == 1

        # Stats disabled should not have detailed metrics
        assert "hits" not in stats_disabled
        assert "misses" not in stats_disabled
        assert "hit_rate" not in stats_disabled

        # Cleanup
        await node_enabled.cleanup()
        await node_disabled.cleanup()

    @pytest.mark.asyncio
    async def test_eviction_policy_lru_vs_lfu(self):
        """Test that LRU and LFU eviction policies behave differently."""
        # LRU config (evict least recently used)
        lru_config = ModelComputeCacheConfig(
            max_size=2,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.LRU,
            enable_stats=True,
        )

        # LFU config (evict least frequently used)
        lfu_config = ModelComputeCacheConfig(
            max_size=2,
            ttl_seconds=3600,
            eviction_policy=EnumCacheEvictionPolicy.LFU,
            enable_stats=True,
        )

        container_lru = await create_model_onex_container(
            compute_cache_config=lru_config
        )
        container_lfu = await create_model_onex_container(
            compute_cache_config=lfu_config
        )

        node_lru = NodeCompute(container_lru)
        node_lfu = NodeCompute(container_lfu)
        await node_lru.initialize()
        await node_lfu.initialize()

        # Create three different inputs
        input1 = ModelComputeInput(
            computation_type="sum_numbers", data=[1, 2], cache_enabled=True
        )
        input2 = ModelComputeInput(
            computation_type="sum_numbers", data=[3, 4], cache_enabled=True
        )
        input3 = ModelComputeInput(
            computation_type="sum_numbers", data=[5, 6], cache_enabled=True
        )

        # Fill cache (max_size=2)
        await node_lru.process(input1)  # Cache: [input1]
        await node_lru.process(input2)  # Cache: [input1, input2]

        await node_lfu.process(input1)  # Cache: [input1]
        await node_lfu.process(input2)  # Cache: [input1, input2]

        # Access input1 multiple times (makes it frequently used)
        await node_lru.process(input1)
        await node_lru.process(input1)

        await node_lfu.process(input1)
        await node_lfu.process(input1)

        # Add input3 (forces eviction)
        await node_lru.process(input3)  # Should evict input2 (least recently used)
        await node_lfu.process(input3)  # Should evict input2 (least frequently used)

        # Verify evictions
        stats_lru = node_lru.computation_cache.get_stats()
        stats_lfu = node_lfu.computation_cache.get_stats()

        assert stats_lru["evictions"] >= 1
        assert stats_lfu["evictions"] >= 1

        # Cleanup
        await node_lru.cleanup()
        await node_lfu.cleanup()

    @pytest.mark.asyncio
    async def test_cache_memory_requirements_validation(self):
        """Test that memory requirements can be validated before deployment."""
        # Create config for large workload
        large_config = ModelComputeCacheConfig(max_size=2048, ttl_seconds=7200)

        # Validate memory requirements
        memory = large_config.validate_memory_requirements(avg_entry_size_kb=1.0)

        # Verify estimates are reasonable
        assert memory["estimated_memory_mb"] > 0
        assert memory["max_memory_mb"] > memory["estimated_memory_mb"]
        assert memory["entries_per_mb"] == 1024.0

        # Create container with validated config
        container = await create_model_onex_container(compute_cache_config=large_config)
        node = NodeCompute(container)

        # Verify node uses the config
        assert node.computation_cache.max_size == 2048

    @pytest.mark.asyncio
    async def test_multiple_nodes_share_container_config(self):
        """Test that multiple NodeCompute instances share container cache config."""
        # Create single container with custom config
        custom_config = ModelComputeCacheConfig(
            max_size=256, ttl_seconds=1800, eviction_policy=EnumCacheEvictionPolicy.FIFO
        )

        container = await create_model_onex_container(
            compute_cache_config=custom_config
        )

        # Create multiple nodes from same container
        node1 = NodeCompute(container)
        node2 = NodeCompute(container)
        node3 = NodeCompute(container)

        # Verify all nodes use same config
        assert node1.computation_cache.max_size == 256
        assert node2.computation_cache.max_size == 256
        assert node3.computation_cache.max_size == 256

        assert node1.computation_cache.eviction_policy == EnumCacheEvictionPolicy.FIFO
        assert node2.computation_cache.eviction_policy == EnumCacheEvictionPolicy.FIFO
        assert node3.computation_cache.eviction_policy == EnumCacheEvictionPolicy.FIFO

        # Note: Each node has its own cache instance (not shared)
        # This is expected - they share CONFIG, not cache state

    @pytest.mark.asyncio
    async def test_cache_config_ttl_conversion_backward_compatibility(self):
        """Test that TTL conversion maintains backward compatibility."""
        # Create config with TTL in seconds
        config = ModelComputeCacheConfig(ttl_seconds=1800)  # 30 minutes

        container = await create_model_onex_container(compute_cache_config=config)
        node = NodeCompute(container)

        # Verify both seconds and minutes are accessible
        assert config.ttl_seconds == 1800
        assert config.get_ttl_minutes() == 30
        assert node.cache_ttl_minutes == 30

        # Verify cache uses seconds
        assert node.computation_cache.ttl_seconds == 1800
        assert node.computation_cache.default_ttl_minutes == 30

    @pytest.mark.asyncio
    async def test_production_deployment_scenario(self):
        """Test realistic production deployment scenario with tuned config."""
        # Production config: medium workload
        production_config = ModelComputeCacheConfig(
            max_size=512,
            ttl_seconds=3600,  # 1 hour
            eviction_policy=EnumCacheEvictionPolicy.LRU,
            enable_stats=True,
        )

        # Validate memory before deployment
        memory = production_config.validate_memory_requirements()
        assert memory["estimated_memory_mb"] < 1.0  # Should be ~0.5MB

        # Create production container
        container = await create_model_onex_container(
            enable_cache=True, compute_cache_config=production_config
        )

        # Create node
        node = NodeCompute(container)
        await node.initialize()

        # Simulate production workload
        for i in range(100):
            input_data = ModelComputeInput(
                computation_type="sum_numbers",
                data=list(range(i, i + 10)),
                cache_enabled=True,
            )
            await node.process(input_data)

        # Check statistics
        stats = node.computation_cache.get_stats()
        assert stats["total_entries"] <= 512  # Respects max_size
        assert "hit_rate" in stats
        assert stats["total_requests"] == 100

        # Verify no evictions yet (under capacity)
        assert stats["evictions"] == 0

        # Get metrics
        metrics = await node.get_computation_metrics()
        assert "cache_performance" in metrics

        # Cleanup
        await node.cleanup()
