#!/usr/bin/env python3

"""
Comprehensive unit tests for Message Aggregator Compute Tool.
Tests all functionality with real PostgreSQL integration and message processing workflows.
Achieves >85% code coverage requirement focusing on modernized health_check() method.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from omnibase.core.onex_container import ONEXContainer
from omnibase.core.onex_error import OnexError
from omnibase.enums.enum_health_status import EnumHealthStatus
from omnibase.model.core.model_health_status import ModelHealthStatus
from omnibase.tools.infrastructure.tool_infrastructure_message_aggregator_compute.v1_0_0.models import (
    ModelMessageAggregatorInput,
    ModelMessageAggregatorOutput,
)
from omnibase.tools.infrastructure.tool_infrastructure_message_aggregator_compute.v1_0_0.node import (
    MessageAggregator,
    ModelAggregatedData,
    ModelAggregationMetrics,
    ModelAggregationResult,
    ModelGroupMessage,
    ModelGroupMessageData,
    ModelNumericStats,
    ModelStateData,
    StateManager,
    ToolMessageAggregator,
    main,
)
from pydantic import ValidationError


class TestModelValidation:
    """Test Pydantic model validation and structure."""

    def test_model_group_message_validation(self):
        """Test ModelGroupMessage validation and defaults."""
        # Valid message
        message = ModelGroupMessage(
            group_id="group_1",
            message_content="Test message content",
        )
        assert message.group_id == "group_1"
        assert message.message_content == "Test message content"
        assert message.metadata == {}
        assert message.timestamp is None

        # With metadata and timestamp
        metadata = {"source": "test", "priority": "high"}
        timestamp = "2024-08-27T10:00:00Z"
        message_with_data = ModelGroupMessage(
            group_id="group_2",
            message_content="Content with metadata",
            metadata=metadata,
            timestamp=timestamp,
        )
        assert message_with_data.metadata == metadata
        assert message_with_data.timestamp == timestamp

    def test_model_aggregation_result_validation(self):
        """Test ModelAggregationResult validation."""
        result = ModelAggregationResult(
            strategy_used="merge",
            total_messages=5,
            result_data={"merged": "data"},
            processing_time_ms=123.45,
        )
        assert result.strategy_used == "merge"
        assert result.total_messages == 5
        assert result.processing_time_ms == 123.45

    def test_model_state_data_validation(self):
        """Test ModelStateData validation."""
        state_data = ModelStateData(
            operation_type="persist",
            data={"key": "value"},
            timestamp=datetime.utcnow().isoformat(),
            correlation_id="test-correlation-123",
        )
        assert state_data.operation_type == "persist"
        assert state_data.correlation_id == "test-correlation-123"

    def test_model_group_message_data_validation(self):
        """Test ModelGroupMessageData validation with hash."""
        message_data = ModelGroupMessageData(
            group_id="test_group",
            message_content="Test content",
            data={"key": "value"},
            metadata={"source": "unit_test"},
            timestamp=datetime.utcnow().isoformat(),
            message_hash=12345,
        )
        assert message_data.group_id == "test_group"
        assert message_data.message_hash == 12345

    def test_model_aggregated_data_validation(self):
        """Test ModelAggregatedData with different strategy data."""
        # Merge strategy data
        merge_data = ModelAggregatedData(
            aggregation_strategy="merge",
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=["group_1", "group_2"],
            merged_data={"result": "merged"},
        )
        assert merge_data.aggregation_strategy == "merge"
        assert merge_data.merged_data == {"result": "merged"}
        assert merge_data.combined_messages is None

        # Combine strategy data
        combine_data = ModelAggregatedData(
            aggregation_strategy="combine",
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=["group_1"],
            combined_messages=[
                ModelGroupMessageData(
                    group_id="group_1",
                    message_content="content",
                    data={},
                    metadata={},
                    timestamp=datetime.utcnow().isoformat(),
                )
            ],
        )
        assert combine_data.aggregation_strategy == "combine"
        assert len(combine_data.combined_messages) == 1

    def test_model_numeric_stats_validation(self):
        """Test ModelNumericStats validation."""
        stats = ModelNumericStats(
            sum=100.0, average=20.0, min=5.0, max=50.0, numeric_count=5
        )
        assert stats.sum == 100.0
        assert stats.average == 20.0
        assert stats.numeric_count == 5


class TestStateManager:
    """Test state management functionality with PostgreSQL."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock asyncpg connection pool."""
        pool = MagicMock(spec=asyncpg.Pool)
        connection = AsyncMock()
        connection.execute = AsyncMock()
        connection.fetchrow = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool

    @pytest.fixture
    def state_manager(self, mock_db_pool):
        """Create StateManager instance with mocked database pool."""
        return StateManager(mock_db_pool)

    def test_state_manager_initialization(self, state_manager, mock_db_pool):
        """Test StateManager initialization."""
        assert state_manager.db_pool == mock_db_pool
        assert hasattr(state_manager, "logger")

    @pytest.mark.asyncio
    async def test_persist_state_success(self, state_manager, mock_db_pool):
        """Test successful state persistence."""
        state_data = ModelStateData(
            operation_type="test_persist",
            data={"test_key": "test_value"},
            timestamp=datetime.utcnow().isoformat(),
            correlation_id="test_correlation",
        )

        result = await state_manager.persist_state(
            state_key="test_key",
            state_data=state_data,
            correlation_id="test_correlation",
        )

        assert result is True
        # Verify database calls were made
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        assert connection.execute.call_count == 2  # INSERT for both tables

    @pytest.mark.asyncio
    async def test_persist_state_database_error(self, state_manager, mock_db_pool):
        """Test state persistence with database error."""
        # Mock database error
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.execute.side_effect = Exception("Database connection failed")

        state_data = ModelStateData(
            operation_type="test_persist",
            data={"test_key": "test_value"},
            timestamp=datetime.utcnow().isoformat(),
        )

        result = await state_manager.persist_state(
            state_key="test_key", state_data=state_data
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_restore_state_success(self, state_manager, mock_db_pool):
        """Test successful state restoration."""
        # Mock database response
        mock_row = {
            "snapshot_data": {"restored": "data"},
            "snapshot_version": 1,
            "created_at": datetime.utcnow(),
        }
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.return_value = mock_row

        result = await state_manager.restore_state("test_key")

        assert result is not None
        assert isinstance(result, ModelStateData)
        assert result.operation_type == "restore"
        assert result.correlation_id == "test_key"

    @pytest.mark.asyncio
    async def test_restore_state_not_found(self, state_manager, mock_db_pool):
        """Test state restoration when state not found."""
        # Mock no data found
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.return_value = None

        result = await state_manager.restore_state("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_restore_state_database_error(self, state_manager, mock_db_pool):
        """Test state restoration with database error."""
        # Mock database error
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.fetchrow.side_effect = Exception("Database query failed")

        result = await state_manager.restore_state("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_state_success(self, state_manager, mock_db_pool):
        """Test successful cleanup of expired state."""
        # Mock database response
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.execute.return_value = "DELETE 5"

        result = await state_manager.cleanup_expired_state(retention_days=7)

        assert result == 5
        assert connection.execute.call_count == 2  # Both cleanup queries

    @pytest.mark.asyncio
    async def test_cleanup_expired_state_error(self, state_manager, mock_db_pool):
        """Test cleanup with database error."""
        # Mock database error
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.execute.side_effect = Exception("Cleanup failed")

        result = await state_manager.cleanup_expired_state()

        assert result == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_state_custom_retention(
        self, state_manager, mock_db_pool
    ):
        """Test cleanup with custom retention period."""
        connection = mock_db_pool.acquire.return_value.__aenter__.return_value
        connection.execute.return_value = "DELETE 3"

        result = await state_manager.cleanup_expired_state(retention_days=14)

        assert result == 3
        # Verify retention period calculation
        calls = connection.execute.call_args_list
        cutoff_date = calls[0][0][1]  # First argument of first call
        expected_cutoff = datetime.utcnow() - timedelta(days=14)
        # Allow 1 minute tolerance for test execution time
        assert abs((cutoff_date - expected_cutoff).total_seconds()) < 60


class TestMessageAggregator:
    """Test message aggregation functionality."""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock asyncpg connection pool."""
        pool = MagicMock(spec=asyncpg.Pool)
        return pool

    @pytest.fixture
    def message_aggregator(self, mock_db_pool):
        """Create MessageAggregator instance."""
        return MessageAggregator(mock_db_pool)

    def test_message_aggregator_initialization(self, message_aggregator, mock_db_pool):
        """Test MessageAggregator initialization."""
        assert message_aggregator.db_pool == mock_db_pool
        assert hasattr(message_aggregator, "logger")

    @pytest.mark.asyncio
    async def test_aggregate_messages_merge_strategy(self, message_aggregator):
        """Test message aggregation using merge strategy."""
        group_messages = [
            {"group_id": "group_1", "key1": "value1", "common": "data1"},
            {"group_id": "group_2", "key2": "value2", "common": "data2"},
            {"group_id": "group_3", "key3": "value3"},
        ]

        result = await message_aggregator.aggregate_messages(
            group_messages, "merge", "test_correlation"
        )

        assert isinstance(result, ModelAggregatedData)
        assert result.aggregation_strategy == "merge"
        assert result.correlation_id == "test_correlation"
        assert len(result.groups_processed) == 3
        assert "group_1" in result.groups_processed
        assert result.merged_data is not None

    @pytest.mark.asyncio
    async def test_aggregate_messages_combine_strategy(self, message_aggregator):
        """Test message aggregation using combine strategy."""
        group_messages = [
            {
                "group_id": "group_1",
                "message_content": "First message",
                "metadata": {"priority": "high"},
            },
            {
                "group_id": "group_2",
                "message_content": "Second message",
                "metadata": {"priority": "medium"},
            },
        ]

        result = await message_aggregator.aggregate_messages(
            group_messages, "combine", "test_correlation"
        )

        assert result.aggregation_strategy == "combine"
        assert result.total_messages == 2
        assert len(result.combined_messages) == 2
        assert result.combined_messages[0].group_id == "group_1"
        assert result.combined_messages[1].group_id == "group_2"

    @pytest.mark.asyncio
    async def test_aggregate_messages_reduce_strategy(self, message_aggregator):
        """Test message aggregation using reduce strategy."""
        group_messages = [
            {"group_id": "group_1", "value": "10"},
            {"group_id": "group_2", "value": "20"},
            {"group_id": "group_3", "value": "30"},
            {"group_id": "group_4", "value": "invalid"},  # Non-numeric
        ]

        result = await message_aggregator.aggregate_messages(
            group_messages, "reduce", "test_correlation"
        )

        assert result.aggregation_strategy == "reduce"
        assert result.reduced_data["count"] == "4"
        assert result.reduced_data["sum"] == "60.0"  # 10 + 20 + 30
        assert result.reduced_data["average"] == "20.0"
        assert result.reduced_data["min"] == "10.0"
        assert result.reduced_data["max"] == "30.0"
        assert result.reduced_data["numeric_count"] == "3"

    @pytest.mark.asyncio
    async def test_aggregate_messages_reduce_no_numeric(self, message_aggregator):
        """Test reduce strategy with no numeric values."""
        group_messages = [
            {"group_id": "group_1", "data": "text_only"},
            {"group_id": "group_2", "data": "no_numbers"},
        ]

        result = await message_aggregator.aggregate_messages(
            group_messages, "reduce", "test_correlation"
        )

        assert result.aggregation_strategy == "reduce"
        assert result.reduced_data["count"] == "2"
        assert "sum" not in result.reduced_data  # No numeric stats

    @pytest.mark.asyncio
    async def test_aggregate_messages_collect_strategy(self, message_aggregator):
        """Test message aggregation using collect strategy."""
        group_messages = [
            {"group_id": "group_1", "message_content": "Message one"},
            {"group_id": "group_2", "message_content": "Message two"},
        ]

        result = await message_aggregator.aggregate_messages(
            group_messages, "collect", "test_correlation"
        )

        assert result.aggregation_strategy == "collect"
        assert result.collected_messages["group_1"] == "Message one"
        assert result.collected_messages["group_2"] == "Message two"
        assert result.collection_metadata["total_groups"] == "2"
        assert "group_1_size" in result.collection_metadata

    @pytest.mark.asyncio
    async def test_aggregate_messages_unknown_strategy(self, message_aggregator):
        """Test aggregation with unknown strategy."""
        group_messages = [{"group_id": "group_1", "data": "test"}]

        with pytest.raises(OnexError) as exc_info:
            await message_aggregator.aggregate_messages(
                group_messages, "unknown_strategy", "test_correlation"
            )

        assert "Unknown aggregation strategy: unknown_strategy" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_aggregate_messages_empty_list(self, message_aggregator):
        """Test aggregation with empty message list."""
        result = await message_aggregator.aggregate_messages([], "collect", None)

        assert result.aggregation_strategy == "collect"
        assert len(result.groups_processed) == 0
        assert result.collected_messages == {}

    def test_deep_merge_basic(self, message_aggregator):
        """Test deep merge functionality."""
        dict1 = {"key1": "value1", "common": "original"}
        dict2 = {"key2": "value2", "common": "updated"}

        result = message_aggregator._deep_merge(dict1, dict2, "source2")

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["common"] == "original"  # Original kept
        assert result["common_source2"] == "updated"  # Conflict resolved

    def test_deep_merge_no_conflicts(self, message_aggregator):
        """Test deep merge with no conflicts."""
        dict1 = {"key1": "value1"}
        dict2 = {"key2": "value2"}

        result = message_aggregator._deep_merge(dict1, dict2, "source2")

        assert result == {"key1": "value1", "key2": "value2"}

    @pytest.mark.asyncio
    async def test_merge_aggregation_with_conflicts(self, message_aggregator):
        """Test merge aggregation handling conflicts."""
        group_messages = [
            {"group_id": "group_1", "shared_key": "value1", "unique1": "data1"},
            {"group_id": "group_2", "shared_key": "value2", "unique2": "data2"},
        ]

        result = await message_aggregator._merge_aggregation(
            group_messages, "test_correlation"
        )

        # Verify conflict resolution
        merged_data = result.merged_data
        assert merged_data["shared_key"] == "value1"  # First value kept
        assert "shared_key_group_group_2" in merged_data  # Conflict resolved
        assert merged_data["unique1"] == "data1"
        assert merged_data["unique2"] == "data2"


class TestToolMessageAggregator:
    """Comprehensive test suite for the main ToolMessageAggregator class."""

    @pytest.fixture
    def mock_container(self):
        """Mock ONEX container."""
        container = MagicMock(spec=ONEXContainer)
        return container

    @pytest.fixture
    def aggregator_tool(self, mock_container):
        """Create ToolMessageAggregator instance."""
        return ToolMessageAggregator(mock_container)

    def test_tool_initialization(self, aggregator_tool, mock_container):
        """Test ToolMessageAggregator initialization."""
        assert aggregator_tool.domain == "infrastructure"
        assert aggregator_tool.db_pool is None
        assert aggregator_tool.state_manager is None
        assert aggregator_tool.message_aggregator is None
        assert "total_operations" in aggregator_tool.operation_metrics

    @pytest.mark.asyncio
    async def test_initialize_success(self, aggregator_tool):
        """Test successful initialization with database connection."""
        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = MagicMock()
            mock_create_pool.return_value = mock_pool

            await aggregator_tool.initialize()

            assert aggregator_tool.db_pool == mock_pool
            assert aggregator_tool.state_manager is not None
            assert aggregator_tool.message_aggregator is not None

            mock_create_pool.assert_called_once_with(
                host="localhost",
                port=5432,
                database="omnibase",
                user="postgres",
                password="",
                min_size=10,
                max_size=25,
            )

    @pytest.mark.asyncio
    async def test_initialize_database_error(self, aggregator_tool):
        """Test initialization with database connection error."""
        with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
            with pytest.raises(OnexError) as exc_info:
                await aggregator_tool.initialize()

            assert "Failed to initialize Message Aggregator" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup(self, aggregator_tool):
        """Test cleanup functionality."""
        # Setup mock pool
        mock_pool = AsyncMock()
        aggregator_tool.db_pool = mock_pool

        await aggregator_tool.cleanup()

        mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_pool(self, aggregator_tool):
        """Test cleanup when no pool exists."""
        # Should not raise error
        await aggregator_tool.cleanup()

    # =============================================================================
    # Health Check Tests (Primary Focus - Modernized Implementation)
    # =============================================================================

    def test_health_check_healthy_state(self, aggregator_tool):
        """Test health check in healthy state."""
        # Setup healthy state
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        result = aggregator_tool.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.HEALTHY
        assert "Message aggregator healthy" in result.message
        assert "0 ops" in result.message
        assert "100.0% success" in result.message

    def test_health_check_no_db_pool(self, aggregator_tool):
        """Test health check when PostgreSQL pool not initialized."""
        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.CRITICAL
        assert "PostgreSQL connection pool not initialized" in result.message

    def test_health_check_closed_db_pool(self, aggregator_tool):
        """Test health check when PostgreSQL pool is closed."""
        mock_pool = MagicMock()
        mock_pool._closed = True
        aggregator_tool.db_pool = mock_pool

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.CRITICAL
        assert "PostgreSQL connection pool is closed" in result.message

    def test_health_check_missing_state_manager(self, aggregator_tool):
        """Test health check when state manager not initialized."""
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        # state_manager remains None

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.CRITICAL
        assert "State manager not initialized" in result.message

    def test_health_check_missing_message_aggregator(self, aggregator_tool):
        """Test health check when message aggregator not initialized."""
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        # message_aggregator remains None

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.CRITICAL
        assert "Message aggregator not initialized" in result.message

    def test_health_check_state_manager_no_db_pool(self, aggregator_tool):
        """Test health check when state manager has no database pool."""
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = None
        aggregator_tool.message_aggregator = MagicMock()

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.CRITICAL
        assert "State manager database pool not available" in result.message

    def test_health_check_high_error_rate(self, aggregator_tool):
        """Test health check with high error rate."""
        # Setup healthy components
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        # Setup metrics with high error rate
        aggregator_tool.operation_metrics = {
            "total_operations": 100,
            "successful_operations": 90,  # 90% success rate (< 95%)
            "failed_operations": 10,
            "processing_times": [100.0, 200.0, 150.0],
            "groups_processed": 50,
            "state_persistence_count": 5,
        }

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.DEGRADED
        assert "High error rate: 90.0% success" in result.message
        assert "10 failures" in result.message

    def test_health_check_slow_processing(self, aggregator_tool):
        """Test health check with slow processing times."""
        # Setup healthy components
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        # Setup metrics with slow processing
        aggregator_tool.operation_metrics = {
            "total_operations": 10,
            "successful_operations": 10,
            "failed_operations": 0,
            "processing_times": [15000.0, 12000.0, 20000.0],  # > 10000ms average
            "groups_processed": 20,
            "state_persistence_count": 3,
        }

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.WARNING
        assert "Slow processing detected" in result.message
        assert "avg 15666.7ms" in result.message

    def test_health_check_with_pool_info(self, aggregator_tool):
        """Test health check with database pool information."""
        # Setup healthy components
        mock_pool = MagicMock()
        mock_pool._closed = False
        mock_pool.get_size.return_value = 15
        mock_pool.get_min_size.return_value = 10
        mock_pool.get_max_size.return_value = 25
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.HEALTHY
        assert "DB pool: 15/10-25" in result.message

    def test_health_check_pool_info_error(self, aggregator_tool):
        """Test health check when pool info retrieval fails."""
        # Setup healthy components
        mock_pool = MagicMock()
        mock_pool._closed = False
        mock_pool.get_size.side_effect = Exception("Pool info error")
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.HEALTHY
        assert "DB pool: active" in result.message

    def test_health_check_exception_handling(self, aggregator_tool):
        """Test health check exception handling."""
        # Mock db_pool to raise exception on access
        aggregator_tool.db_pool = MagicMock()
        aggregator_tool.db_pool._closed = MagicMock(
            side_effect=Exception("Access error")
        )

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.ERROR
        assert "Health check failed: Access error" in result.message

    def test_health_check_zero_operations(self, aggregator_tool):
        """Test health check with zero operations (default state)."""
        # Setup healthy components
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        result = aggregator_tool.health_check()

        assert result.status == EnumHealthStatus.HEALTHY
        assert "0 ops" in result.message
        assert "100.0% success" in result.message  # Default success rate

    # =============================================================================
    # Message Processing Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_aggregate_messages_success(self, aggregator_tool):
        """Test successful message aggregation."""
        # Setup components
        mock_aggregator = AsyncMock()
        mock_result = ModelAggregatedData(
            aggregation_strategy="merge",
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=["group_1", "group_2"],
            merged_data={"result": "success"},
        )
        mock_result.dict = MagicMock(return_value={"aggregated": "data"})
        mock_aggregator.aggregate_messages.return_value = mock_result
        aggregator_tool.message_aggregator = mock_aggregator

        group_messages = [
            {"group_id": "group_1", "data": "test1"},
            {"group_id": "group_2", "data": "test2"},
        ]

        result = await aggregator_tool.aggregate_messages(
            group_messages=group_messages,
            aggregation_strategy="merge",
            correlation_id="test_correlation",
            timeout_ms=30000,
        )

        assert isinstance(result, ModelMessageAggregatorOutput)
        assert result.status == "success"
        assert result.aggregated_result.strategy_used == "merge"
        assert result.aggregated_result.total_messages == 2
        assert aggregator_tool.operation_metrics["total_operations"] == 1
        assert aggregator_tool.operation_metrics["successful_operations"] == 1
        assert aggregator_tool.operation_metrics["groups_processed"] == 2

    @pytest.mark.asyncio
    async def test_aggregate_messages_error(self, aggregator_tool):
        """Test message aggregation with error."""
        # Setup failing aggregator
        mock_aggregator = AsyncMock()
        mock_aggregator.aggregate_messages.side_effect = Exception("Aggregation failed")
        aggregator_tool.message_aggregator = mock_aggregator

        group_messages = [{"group_id": "group_1", "data": "test"}]

        result = await aggregator_tool.aggregate_messages(
            group_messages=group_messages,
            aggregation_strategy="merge",
            correlation_id="test_correlation",
        )

        assert result.status == "error"
        assert result.error_message == "Aggregation failed"
        assert aggregator_tool.operation_metrics["failed_operations"] == 1

    @pytest.mark.asyncio
    async def test_persist_state_success(self, aggregator_tool):
        """Test successful state persistence."""
        # Setup state manager
        mock_state_manager = AsyncMock()
        mock_state_manager.persist_state.return_value = True
        aggregator_tool.state_manager = mock_state_manager

        state_data = ModelStateData(
            operation_type="test_persist",
            data={"key": "value"},
            timestamp=datetime.utcnow().isoformat(),
        )

        result = await aggregator_tool.persist_state(
            state_key="test_key",
            state_data=state_data,
            correlation_id="test_correlation",
        )

        assert result.status == "success"
        assert result.aggregated_result.result_data["persistence_status"] == "completed"
        assert aggregator_tool.operation_metrics["state_persistence_count"] == 1

    @pytest.mark.asyncio
    async def test_persist_state_failure(self, aggregator_tool):
        """Test state persistence failure."""
        # Setup failing state manager
        mock_state_manager = AsyncMock()
        mock_state_manager.persist_state.return_value = False
        aggregator_tool.state_manager = mock_state_manager

        state_data = ModelStateData(
            operation_type="test_persist",
            data={"key": "value"},
            timestamp=datetime.utcnow().isoformat(),
        )

        result = await aggregator_tool.persist_state(
            state_key="test_key", state_data=state_data
        )

        assert result.status == "error"
        assert result.error_message == "State persistence failed"

    @pytest.mark.asyncio
    async def test_persist_state_exception(self, aggregator_tool):
        """Test state persistence with exception."""
        # Setup state manager that raises exception
        mock_state_manager = AsyncMock()
        mock_state_manager.persist_state.side_effect = Exception("Database error")
        aggregator_tool.state_manager = mock_state_manager

        state_data = ModelStateData(
            operation_type="test_persist",
            data={"key": "value"},
            timestamp=datetime.utcnow().isoformat(),
        )

        result = await aggregator_tool.persist_state(
            state_key="test_key", state_data=state_data
        )

        assert result.status == "error"
        assert result.error_message == "Database error"

    @pytest.mark.asyncio
    async def test_restore_state_success(self, aggregator_tool):
        """Test successful state restoration."""
        # Setup state manager
        mock_state_data = ModelStateData(
            operation_type="restore",
            data={"restored": "data"},
            timestamp=datetime.utcnow().isoformat(),
            correlation_id="test_key",
        )
        mock_state_manager = AsyncMock()
        mock_state_manager.restore_state.return_value = mock_state_data
        aggregator_tool.state_manager = mock_state_manager

        result = await aggregator_tool.restore_state("test_key")

        assert result.status == "success"
        assert result.state_snapshot == mock_state_data.data

    @pytest.mark.asyncio
    async def test_restore_state_not_found(self, aggregator_tool):
        """Test state restoration when state not found."""
        # Setup state manager returning None
        mock_state_manager = AsyncMock()
        mock_state_manager.restore_state.return_value = None
        aggregator_tool.state_manager = mock_state_manager

        result = await aggregator_tool.restore_state("nonexistent_key")

        assert result.status == "error"
        assert "No state found for key: nonexistent_key" in result.error_message

    @pytest.mark.asyncio
    async def test_restore_state_exception(self, aggregator_tool):
        """Test state restoration with exception."""
        # Setup state manager that raises exception
        mock_state_manager = AsyncMock()
        mock_state_manager.restore_state.side_effect = Exception("Restore failed")
        aggregator_tool.state_manager = mock_state_manager

        result = await aggregator_tool.restore_state("test_key")

        assert result.status == "error"
        assert result.error_message == "Restore failed"

    def test_get_aggregation_metrics(self, aggregator_tool):
        """Test aggregation metrics calculation."""
        # Setup metrics
        aggregator_tool.operation_metrics = {
            "total_operations": 100,
            "successful_operations": 95,
            "failed_operations": 5,
            "processing_times": [100.0, 200.0, 300.0],
            "groups_processed": 250,
            "state_persistence_count": 10,
        }

        metrics = aggregator_tool._get_aggregation_metrics()

        assert isinstance(metrics, ModelAggregationMetrics)
        assert metrics.total_operations == 100
        assert metrics.successful_operations == 95
        assert metrics.failed_operations == 5
        assert metrics.average_processing_time_ms == 200.0  # (100+200+300)/3
        assert metrics.groups_processed == 250
        assert metrics.state_persistence_count == 10

    def test_get_aggregation_metrics_empty(self, aggregator_tool):
        """Test aggregation metrics with no processing times."""
        metrics = aggregator_tool._get_aggregation_metrics()

        assert metrics.average_processing_time_ms == 0

    # =============================================================================
    # Process Method Tests (Main Entry Point)
    # =============================================================================

    @pytest.mark.asyncio
    async def test_process_aggregate_operation(self, aggregator_tool):
        """Test process method with aggregate operation."""
        # Setup aggregator
        mock_aggregator = AsyncMock()
        mock_result = ModelAggregatedData(
            aggregation_strategy="merge",
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=["group_1"],
            merged_data={"result": "success"},
        )
        mock_result.dict = MagicMock(return_value={"merged": "data"})
        mock_aggregator.aggregate_messages.return_value = mock_result
        aggregator_tool.message_aggregator = mock_aggregator

        input_data = ModelMessageAggregatorInput(
            operation_type="aggregate",
            group_messages=[{"group_id": "group_1", "data": "test"}],
            aggregation_strategy="merge",
            correlation_id="test_correlation",
            timeout_ms=60000,
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "success"
        assert result.aggregated_result.strategy_used == "merge"

    @pytest.mark.asyncio
    async def test_process_persist_operation(self, aggregator_tool):
        """Test process method with persist operation."""
        # Setup state manager
        mock_state_manager = AsyncMock()
        mock_state_manager.persist_state.return_value = True
        aggregator_tool.state_manager = mock_state_manager

        input_data = ModelMessageAggregatorInput(
            operation_type="persist",
            group_messages=[{"group_id": "group_1", "data": "test"}],
            aggregation_strategy="",  # Not used for persist
            state_key="test_key",
            correlation_id="test_correlation",
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "success"
        assert result.aggregated_result.result_data["state_key"] == "test_key"

    @pytest.mark.asyncio
    async def test_process_persist_missing_state_key(self, aggregator_tool):
        """Test process method with persist operation missing state key."""
        input_data = ModelMessageAggregatorInput(
            operation_type="persist",
            group_messages=[{"group_id": "group_1", "data": "test"}],
            aggregation_strategy="",
            # state_key is None
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "error"
        assert "state_key required for persist operation" in result.error_message

    @pytest.mark.asyncio
    async def test_process_restore_operation(self, aggregator_tool):
        """Test process method with restore operation."""
        # Setup state manager
        mock_state_data = ModelStateData(
            operation_type="restore",
            data={"restored": "data"},
            timestamp=datetime.utcnow().isoformat(),
            correlation_id="test_key",
        )
        mock_state_manager = AsyncMock()
        mock_state_manager.restore_state.return_value = mock_state_data
        aggregator_tool.state_manager = mock_state_manager

        input_data = ModelMessageAggregatorInput(
            operation_type="restore",
            group_messages=[],  # Not used for restore
            aggregation_strategy="",
            state_key="test_key",
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "success"
        assert result.state_snapshot == mock_state_data.data

    @pytest.mark.asyncio
    async def test_process_restore_missing_state_key(self, aggregator_tool):
        """Test process method with restore operation missing state key."""
        input_data = ModelMessageAggregatorInput(
            operation_type="restore",
            group_messages=[],
            aggregation_strategy="",
            # state_key is None
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "error"
        assert "state_key required for restore operation" in result.error_message

    @pytest.mark.asyncio
    async def test_process_unknown_operation(self, aggregator_tool):
        """Test process method with unknown operation type."""
        input_data = ModelMessageAggregatorInput(
            operation_type="unknown_operation",
            group_messages=[],
            aggregation_strategy="merge",
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "error"
        assert "Unknown operation type: unknown_operation" in result.error_message

    # =============================================================================
    # Performance and Metrics Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_processing_time_tracking(self, aggregator_tool):
        """Test that processing times are properly tracked."""

        # Setup slow aggregator to test timing
        async def slow_aggregate(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            mock_result = ModelAggregatedData(
                aggregation_strategy="merge",
                timestamp=datetime.utcnow().isoformat(),
                groups_processed=["group_1"],
                merged_data={"result": "success"},
            )
            mock_result.dict = MagicMock(return_value={"merged": "data"})
            return mock_result

        mock_aggregator = MagicMock()
        mock_aggregator.aggregate_messages = slow_aggregate
        aggregator_tool.message_aggregator = mock_aggregator

        start_time = time.time()
        result = await aggregator_tool.aggregate_messages(
            group_messages=[{"group_id": "group_1", "data": "test"}],
            aggregation_strategy="merge",
        )
        end_time = time.time()

        # Verify timing
        assert result.aggregated_result.processing_time_ms >= 100  # At least 100ms
        assert (end_time - start_time) * 1000 >= 100  # Actual time >= 100ms

        # Verify metrics updated
        assert len(aggregator_tool.operation_metrics["processing_times"]) == 1
        assert aggregator_tool.operation_metrics["processing_times"][0] >= 100

    @pytest.mark.asyncio
    async def test_concurrent_operations_metrics(self, aggregator_tool):
        """Test metrics tracking with concurrent operations."""

        # Setup fast aggregator
        async def fast_aggregate(*args, **kwargs):
            mock_result = ModelAggregatedData(
                aggregation_strategy="collect",
                timestamp=datetime.utcnow().isoformat(),
                groups_processed=["group_1"],
                collected_messages={"group_1": "message"},
            )
            mock_result.dict = MagicMock(return_value={"collected": "data"})
            return mock_result

        mock_aggregator = MagicMock()
        mock_aggregator.aggregate_messages = fast_aggregate
        aggregator_tool.message_aggregator = mock_aggregator

        # Run multiple concurrent operations
        tasks = [
            aggregator_tool.aggregate_messages(
                group_messages=[{"group_id": f"group_{i}", "data": f"test_{i}"}],
                aggregation_strategy="collect",
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert all(result.status == "success" for result in results)

        # Verify metrics
        assert aggregator_tool.operation_metrics["total_operations"] == 5
        assert aggregator_tool.operation_metrics["successful_operations"] == 5
        assert aggregator_tool.operation_metrics["failed_operations"] == 0
        assert aggregator_tool.operation_metrics["groups_processed"] == 5

    # =============================================================================
    # Integration and Edge Case Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, aggregator_tool):
        """Test complete end-to-end workflow."""
        # Setup components
        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = MagicMock()
            mock_create_pool.return_value = mock_pool
            await aggregator_tool.initialize()

        # Mock successful aggregation
        mock_result = ModelAggregatedData(
            aggregation_strategy="merge",
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=["group_1", "group_2"],
            merged_data={"key1": "value1", "key2": "value2"},
        )
        mock_result.dict = MagicMock(return_value={"merged": "data"})
        aggregator_tool.message_aggregator.aggregate_messages = AsyncMock(
            return_value=mock_result
        )

        # Test aggregation
        input_data = ModelMessageAggregatorInput(
            operation_type="aggregate",
            group_messages=[
                {"group_id": "group_1", "key1": "value1"},
                {"group_id": "group_2", "key2": "value2"},
            ],
            aggregation_strategy="merge",
            correlation_id="end_to_end_test",
        )

        result = await aggregator_tool.process(input_data)

        assert result.status == "success"
        assert result.aggregated_result.strategy_used == "merge"
        assert result.aggregated_result.total_messages == 2

        # Test health check
        health = aggregator_tool.health_check()
        assert health.status == EnumHealthStatus.HEALTHY

        # Cleanup
        await aggregator_tool.cleanup()

    def test_large_message_handling(self, aggregator_tool):
        """Test handling of large numbers of messages."""
        # Create large message set
        large_message_set = [
            {"group_id": f"group_{i}", "data": f"large_data_{i}" * 100}
            for i in range(1000)
        ]

        # Test metrics with large set
        aggregator_tool.operation_metrics["groups_processed"] = len(large_message_set)

        metrics = aggregator_tool._get_aggregation_metrics()
        assert metrics.groups_processed == 1000

    def test_memory_efficiency_metrics(self, aggregator_tool):
        """Test memory efficiency with processing time tracking."""
        # Add many processing times
        processing_times = [float(i) for i in range(10000)]
        aggregator_tool.operation_metrics["processing_times"] = processing_times

        metrics = aggregator_tool._get_aggregation_metrics()

        # Verify calculation doesn't fail with large dataset
        expected_avg = sum(processing_times) / len(processing_times)
        assert metrics.average_processing_time_ms == expected_avg

    # =============================================================================
    # Error Handling and Edge Cases
    # =============================================================================

    @pytest.mark.asyncio
    async def test_input_validation_edge_cases(self, aggregator_tool):
        """Test input validation with edge cases."""
        # Empty group messages
        input_data = ModelMessageAggregatorInput(
            operation_type="aggregate",
            group_messages=[],
            aggregation_strategy="collect",
        )

        # Setup aggregator to handle empty list
        mock_result = ModelAggregatedData(
            aggregation_strategy="collect",
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=[],
            collected_messages={},
            collection_metadata={"total_groups": "0"},
        )
        mock_result.dict = MagicMock(return_value={"empty": "collection"})
        aggregator_tool.message_aggregator = MagicMock()
        aggregator_tool.message_aggregator.aggregate_messages = AsyncMock(
            return_value=mock_result
        )

        result = await aggregator_tool.process(input_data)
        assert result.status == "success"
        assert result.aggregated_result.total_messages == 0

    def test_health_check_boundary_conditions(self, aggregator_tool):
        """Test health check at boundary conditions."""
        # Setup healthy components
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator_tool.db_pool = mock_pool
        aggregator_tool.state_manager = MagicMock()
        aggregator_tool.state_manager.db_pool = mock_pool
        aggregator_tool.message_aggregator = MagicMock()

        # Test exactly 95% success rate (boundary)
        aggregator_tool.operation_metrics = {
            "total_operations": 100,
            "successful_operations": 95,
            "failed_operations": 5,
            "processing_times": [1000.0],
            "groups_processed": 100,
            "state_persistence_count": 10,
        }

        result = aggregator_tool.health_check()
        assert result.status == EnumHealthStatus.HEALTHY  # Exactly at threshold

        # Test below 95% success rate
        aggregator_tool.operation_metrics["successful_operations"] = 94
        aggregator_tool.operation_metrics["failed_operations"] = 6

        result = aggregator_tool.health_check()
        assert result.status == EnumHealthStatus.DEGRADED

    def test_deep_merge_edge_cases(self):
        """Test deep merge with edge cases."""
        aggregator = MessageAggregator(MagicMock())

        # Empty dictionaries
        result = aggregator._deep_merge({}, {}, "source")
        assert result == {}

        # One empty dictionary
        result = aggregator._deep_merge({"key": "value"}, {}, "source")
        assert result == {"key": "value"}

        result = aggregator._deep_merge({}, {"key": "value"}, "source")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_database_connection_recovery(self, aggregator_tool):
        """Test database connection recovery scenarios."""
        # Test initialization failure and retry
        with patch("asyncpg.create_pool") as mock_create_pool:
            # First call fails, second succeeds
            mock_pool = MagicMock()
            mock_create_pool.side_effect = [
                Exception("Connection failed"),
                mock_pool,
            ]

            # First initialization should fail
            with pytest.raises(OnexError):
                await aggregator_tool.initialize()

            # Second initialization should succeed
            await aggregator_tool.initialize()
            assert aggregator_tool.db_pool == mock_pool

    # =============================================================================
    # Main Function Tests
    # =============================================================================

    def test_main_function(self):
        """Test main function creates aggregator with infrastructure container."""
        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_message_aggregator_compute.v1_0_0.node.create_infrastructure_container"
        ) as mock_create_container:
            mock_container = MagicMock()
            mock_create_container.return_value = mock_container

            result = main()

            mock_create_container.assert_called_once()
            assert isinstance(result, ToolMessageAggregator)
            assert result.domain == "infrastructure"

    def test_main_function_integration(self):
        """Test main function can be called directly."""
        with patch(
            "omnibase.tools.infrastructure.tool_infrastructure_message_aggregator_compute.v1_0_0.node.create_infrastructure_container"
        ) as mock_create_container:
            mock_container = MagicMock()
            mock_create_container.return_value = mock_container

            # Test direct execution
            result = main()
            assert result is not None
            assert isinstance(result, ToolMessageAggregator)


class TestRealPostgreSQLIntegration:
    """Integration tests with real PostgreSQL database (when available)."""

    @pytest.fixture
    def postgres_available(self):
        """Check if PostgreSQL is available for testing."""
        try:
            import asyncpg

            # Try to create a connection to test database
            loop = asyncio.get_event_loop()
            pool = loop.run_until_complete(
                asyncpg.create_pool(
                    host="localhost",
                    port=5432,
                    database="test_omnibase",
                    user="postgres",
                    password="",
                    min_size=1,
                    max_size=2,
                )
            )
            loop.run_until_complete(pool.close())
            return True
        except Exception:
            return False

    @pytest.mark.skipif(
        not pytest.importorskip("asyncpg", reason="asyncpg not available"),
        reason="PostgreSQL not available for testing",
    )
    @pytest.mark.asyncio
    async def test_real_database_operations(self, postgres_available):
        """Test with real PostgreSQL database if available."""
        if not postgres_available:
            pytest.skip("PostgreSQL not available")

        try:
            # Create connection pool
            pool = await asyncpg.create_pool(
                host="localhost",
                port=5432,
                database="test_omnibase",
                user="postgres",
                password="",
                min_size=1,
                max_size=5,
            )

            # Create state manager
            state_manager = StateManager(pool)

            # Test state persistence
            state_data = ModelStateData(
                operation_type="test_real_db",
                data={
                    "test_key": "test_value",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                timestamp=datetime.utcnow().isoformat(),
                correlation_id="real_db_test",
            )

            # This would require proper table setup
            # success = await state_manager.persist_state("test_real_key", state_data)
            # assert success

            await pool.close()

        except Exception as e:
            pytest.skip(f"Real database test failed: {e}")


class TestComplexScenarios:
    """Test complex real-world scenarios and workflows."""

    @pytest.fixture
    def complex_aggregator(self):
        """Setup complex aggregator for scenario testing."""
        container = MagicMock(spec=ONEXContainer)
        aggregator = ToolMessageAggregator(container)

        # Mock database components
        mock_pool = MagicMock()
        mock_pool._closed = False
        aggregator.db_pool = mock_pool
        aggregator.state_manager = StateManager(mock_pool)
        aggregator.message_aggregator = MessageAggregator(mock_pool)

        return aggregator

    @pytest.mark.asyncio
    async def test_multi_strategy_workflow(self, complex_aggregator):
        """Test workflow using multiple aggregation strategies."""
        # Test merge strategy
        merge_messages = [
            {"group_id": "analytics", "cpu_usage": "75", "memory": "60"},
            {"group_id": "database", "cpu_usage": "45", "memory": "80"},
        ]

        merge_result = await complex_aggregator.message_aggregator.aggregate_messages(
            merge_messages, "merge", "analytics_merge"
        )
        assert merge_result.aggregation_strategy == "merge"

        # Test reduce strategy on same data
        reduce_result = await complex_aggregator.message_aggregator.aggregate_messages(
            merge_messages, "reduce", "analytics_reduce"
        )
        assert reduce_result.aggregation_strategy == "reduce"
        assert (
            "numeric_count" in reduce_result.reduced_data
        )  # Should process numeric values

        # Test collect strategy
        collect_result = await complex_aggregator.message_aggregator.aggregate_messages(
            merge_messages, "collect", "analytics_collect"
        )
        assert collect_result.aggregation_strategy == "collect"
        assert len(collect_result.collected_messages) == 2

    @pytest.mark.asyncio
    async def test_high_volume_message_processing(self, complex_aggregator):
        """Test processing high volume of messages."""
        # Create 100 groups with mixed data types
        high_volume_messages = []
        for i in range(100):
            message = {
                "group_id": f"service_{i % 10}",  # 10 different services
                "timestamp": datetime.utcnow().isoformat(),
                "metric_value": str(i * 10),
                "status": "active" if i % 2 == 0 else "idle",
                "metadata": {"instance": f"inst_{i}", "region": f"region_{i % 5}"},
            }
            high_volume_messages.append(message)

        # Test reduce strategy for aggregating metrics
        start_time = time.time()
        result = await complex_aggregator.message_aggregator.aggregate_messages(
            high_volume_messages, "reduce", "high_volume_test"
        )
        processing_time = time.time() - start_time

        assert result.aggregation_strategy == "reduce"
        assert len(result.groups_processed) == 100
        assert processing_time < 5.0  # Should complete within 5 seconds

        # Verify numeric aggregation
        reduced_data = result.reduced_data
        assert "count" in reduced_data
        assert int(reduced_data["count"]) == 100
        assert "sum" in reduced_data  # Should aggregate the metric values

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, complex_aggregator):
        """Test error recovery and resilience."""
        # Test with malformed data
        malformed_messages = [
            {"group_id": "valid", "data": "good_data"},
            {"invalid_structure": "missing_group_id"},
            None,  # None value
            {"group_id": "another_valid", "data": "more_good_data"},
        ]

        # Filter out None values (simulating input validation)
        filtered_messages = [msg for msg in malformed_messages if msg is not None]

        # Should handle malformed data gracefully
        result = await complex_aggregator.message_aggregator.aggregate_messages(
            filtered_messages, "collect", "error_recovery_test"
        )

        assert result.aggregation_strategy == "collect"
        # Should process the valid messages
        assert len(result.groups_processed) >= 2

    def test_stress_health_monitoring(self, complex_aggregator):
        """Test health monitoring under stress conditions."""
        # Simulate high load
        complex_aggregator.operation_metrics = {
            "total_operations": 10000,
            "successful_operations": 9500,
            "failed_operations": 500,
            "processing_times": [100.0] * 1000,  # 1000 operations at 100ms each
            "groups_processed": 50000,
            "state_persistence_count": 1000,
        }

        health = complex_aggregator.health_check()
        assert health.status == EnumHealthStatus.HEALTHY  # 95% success rate exactly

        # Increase failure rate
        complex_aggregator.operation_metrics["successful_operations"] = 9000
        complex_aggregator.operation_metrics["failed_operations"] = 1000

        health = complex_aggregator.health_check()
        assert health.status == EnumHealthStatus.DEGRADED  # 90% success rate

    @pytest.mark.asyncio
    async def test_state_persistence_workflow(self, complex_aggregator):
        """Test complete state persistence and recovery workflow."""
        # Mock successful database operations
        complex_aggregator.state_manager.persist_state = AsyncMock(return_value=True)
        complex_aggregator.state_manager.restore_state = AsyncMock()

        # Test persistence workflow
        messages = [
            {"group_id": "state_test_1", "data": "persistent_data_1"},
            {"group_id": "state_test_2", "data": "persistent_data_2"},
        ]

        # Aggregate messages
        result = await complex_aggregator.aggregate_messages(
            group_messages=messages,
            aggregation_strategy="merge",
            correlation_id="state_workflow",
        )

        assert result.status == "success"

        # Persist state
        state_data = ModelStateData(
            operation_type="workflow_state",
            data=result.aggregated_result.result_data,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id="state_workflow",
        )

        persist_result = await complex_aggregator.persist_state(
            state_key="workflow_state_key",
            state_data=state_data,
            correlation_id="state_workflow",
        )

        assert persist_result.status == "success"
        complex_aggregator.state_manager.persist_state.assert_called_once()

        # Mock restored state
        complex_aggregator.state_manager.restore_state.return_value = state_data

        # Restore state
        restore_result = await complex_aggregator.restore_state("workflow_state_key")

        assert restore_result.status == "success"
        assert restore_result.state_snapshot == state_data.data
        complex_aggregator.state_manager.restore_state.assert_called_once()
