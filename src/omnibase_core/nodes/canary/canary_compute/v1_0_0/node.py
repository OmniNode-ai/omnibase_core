"""
Message Aggregator - Cross-group message aggregation and state management.

This tool implements the Message Aggregator component of ONEX Messaging Architecture v0.2,
providing cross-group message coordination, intelligent aggregation strategies,
and PostgreSQL-based state persistence.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Union

import asyncpg
from pydantic import BaseModel, Field

from omnibase_core.core.errors.onex_error import OnexError
from omnibase_core.core.infrastructure_service_bases import NodeComputeService
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus

from .models import ModelMessageAggregatorInput, ModelMessageAggregatorOutput


# Internal helper models (not part of contract)
class ModelGroupMessage(BaseModel):
    """Model for group message data."""

    group_id: str = Field(..., description="Tool group identifier")
    message_content: str = Field(..., description="Message content")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Message metadata"
    )
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ModelAggregationResult(BaseModel):
    """Model for aggregation result data."""

    strategy_used: str = Field(..., description="Aggregation strategy used")
    total_messages: int = Field(..., description="Total number of messages processed")
    result_data: Dict[str, str] = Field(
        default_factory=dict, description="Aggregated result"
    )
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )


class ModelAggregationMetrics(BaseModel):
    """Model for aggregation performance metrics."""

    total_operations: int = Field(
        ..., description="Total number of aggregation operations"
    )
    successful_operations: int = Field(
        ..., description="Number of successful operations"
    )
    failed_operations: int = Field(..., description="Number of failed operations")
    average_processing_time_ms: float = Field(
        ..., description="Average processing time"
    )
    groups_processed: int = Field(..., description="Number of groups processed")
    state_persistence_count: int = Field(
        ..., description="Number of state persistence operations"
    )


class ModelStateData(BaseModel):
    """Model for state persistence data."""

    operation_type: str = Field(..., description="Type of state operation")
    data: Dict[str, str] = Field(default_factory=dict, description="State data content")
    timestamp: str = Field(..., description="State creation timestamp")
    correlation_id: Optional[str] = Field(
        default=None, description="State correlation ID"
    )


class ModelGroupMessageData(BaseModel):
    """Model for group message data with processing metadata."""

    group_id: str = Field(..., description="Tool group identifier")
    message_content: str = Field(..., description="Message content")
    data: Dict[str, str] = Field(default_factory=dict, description="Message data")
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Message metadata"
    )
    timestamp: str = Field(..., description="Message timestamp")
    message_hash: Optional[int] = Field(
        default=None, description="Message content hash"
    )


class ModelAggregatedData(BaseModel):
    """Model for aggregated message data."""

    aggregation_strategy: str = Field(..., description="Strategy used for aggregation")
    correlation_id: Optional[str] = Field(
        default=None, description="Correlation identifier"
    )
    timestamp: str = Field(..., description="Aggregation timestamp")
    groups_processed: List[str] = Field(
        default_factory=list, description="List of processed groups"
    )
    merged_data: Optional[Dict[str, str]] = Field(
        default=None, description="Merged data for merge strategy"
    )
    combined_messages: Optional[List[ModelGroupMessageData]] = Field(
        default=None, description="Combined messages for combine strategy"
    )
    reduced_data: Optional[Dict[str, str]] = Field(
        default=None, description="Reduced data for reduce strategy"
    )
    collected_messages: Optional[Dict[str, str]] = Field(
        default=None, description="Collected messages for collect strategy"
    )
    conflicts_resolved: Optional[int] = Field(
        default=None, description="Number of conflicts resolved"
    )
    total_messages: Optional[int] = Field(
        default=None, description="Total number of messages processed"
    )
    collection_metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Collection metadata"
    )


class ModelNumericStats(BaseModel):
    """Model for numeric statistics in reduce operations."""

    sum: float = Field(..., description="Sum of numeric values")
    average: float = Field(..., description="Average of numeric values")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    numeric_count: int = Field(..., description="Count of numeric values")


class StateManager:
    """Handles state persistence and recovery with PostgreSQL."""

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize with database connection pool."""
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)

    async def persist_state(
        self,
        state_key: str,
        state_data: ModelStateData,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Persist aggregation state to PostgreSQL."""
        try:
            request_id = str(uuid.uuid4())

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO aggregation_requests (
                        request_id, correlation_id, operation_type, request_data, status
                    ) VALUES ($1, $2, $3, $4, $5)
                    """,
                    request_id,
                    correlation_id or state_key,
                    "persist_state",
                    json.dumps(state_data.dict()),
                    "completed",
                )

                # Create snapshot
                await conn.execute(
                    """
                    INSERT INTO aggregation_state_snapshots (
                        snapshot_id, correlation_id, snapshot_data, snapshot_version
                    ) VALUES ($1, $2, $3, $4)
                    ON CONFLICT (correlation_id) DO UPDATE SET
                        snapshot_data = EXCLUDED.snapshot_data,
                        snapshot_version = aggregation_state_snapshots.snapshot_version + 1,
                        created_at = NOW()
                    """,
                    str(uuid.uuid4()),
                    correlation_id or state_key,
                    json.dumps(state_data.dict()),
                    1,
                )

            self.logger.info(f"State persisted successfully for key: {state_key}")
            return True

        except Exception as e:
            self.logger.error(f"State persistence failed: {e}")
            return False

    async def restore_state(self, state_key: str) -> Optional[ModelStateData]:
        """Restore aggregation state from PostgreSQL."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT snapshot_data, snapshot_version, created_at
                    FROM aggregation_state_snapshots
                    WHERE correlation_id = $1
                    ORDER BY snapshot_version DESC
                    LIMIT 1
                    """,
                    state_key,
                )

                if row:
                    snapshot_data = row["snapshot_data"]
                    self.logger.info(
                        f"State restored successfully for key: {state_key}"
                    )
                    return ModelStateData(
                        operation_type="restore",
                        data=snapshot_data if isinstance(snapshot_data, dict) else {},
                        timestamp=datetime.utcnow().isoformat(),
                        correlation_id=state_key,
                    )

                return None

        except Exception as e:
            self.logger.error(f"State restoration failed: {e}")
            return None

    async def cleanup_expired_state(self, retention_days: int = 7) -> int:
        """Clean up expired state records."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            async with self.db_pool.acquire() as conn:
                # Clean up old requests
                result1 = await conn.execute(
                    "DELETE FROM aggregation_requests WHERE created_at < $1",
                    cutoff_date,
                )

                # Clean up old snapshots (keep latest for each correlation_id)
                await conn.execute(
                    """
                    DELETE FROM aggregation_state_snapshots
                    WHERE created_at < $1
                    AND snapshot_id NOT IN (
                        SELECT DISTINCT ON (correlation_id) snapshot_id
                        FROM aggregation_state_snapshots
                        ORDER BY correlation_id, snapshot_version DESC
                    )
                    """,
                    cutoff_date,
                )

                cleaned_count = int(result1.split()[-1]) if result1 else 0
                return cleaned_count

        except Exception as e:
            self.logger.error(f"State cleanup failed: {e}")
            return 0


class MessageAggregator:
    """Handles cross-group message aggregation with multiple strategies."""

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize with database connection pool."""
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)

    async def aggregate_messages(
        self,
        group_messages: List[Dict[str, str]],
        strategy: str,
        correlation_id: Optional[str] = None,
    ) -> ModelAggregatedData:
        """Aggregate messages from multiple groups using specified strategy."""
        try:
            if strategy == "merge":
                return await self._merge_aggregation(group_messages, correlation_id)
            elif strategy == "combine":
                return await self._combine_aggregation(group_messages, correlation_id)
            elif strategy == "reduce":
                return await self._reduce_aggregation(group_messages, correlation_id)
            elif strategy == "collect":
                return await self._collect_aggregation(group_messages, correlation_id)
            else:
                raise OnexError(f"Unknown aggregation strategy: {strategy}")

        except Exception as e:
            raise OnexError(f"Message aggregation failed: {str(e)}") from e

    async def _merge_aggregation(
        self,
        group_messages: List[Dict[str, str]],
        correlation_id: Optional[str],
    ) -> ModelAggregatedData:
        """Merge messages with deep object merging and conflict resolution."""
        merged_data = {}
        conflicts_resolved = 0
        groups_processed = []

        # Deep merge with conflict resolution
        for idx, group_data in enumerate(group_messages):
            group_id = group_data.get("group_id", f"group_{idx}")
            groups_processed.append(group_id)
            merged_data = self._deep_merge(merged_data, group_data, f"group_{group_id}")

        return ModelAggregatedData(
            aggregation_strategy="merge",
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=groups_processed,
            merged_data=merged_data,
            conflicts_resolved=conflicts_resolved,
        )

    async def _combine_aggregation(
        self,
        group_messages: List[Dict[str, str]],
        correlation_id: Optional[str],
    ) -> ModelAggregatedData:
        """Combine messages into collections with metadata preservation."""
        combined_messages = []
        total_messages = 0
        groups_processed = []

        for idx, group_data in enumerate(group_messages):
            group_id = group_data.get("group_id", f"group_{idx}")
            groups_processed.append(group_id)

            message_entry = ModelGroupMessageData(
                group_id=group_id,
                message_content=group_data.get("message_content", ""),
                data=group_data,
                metadata=group_data.get("metadata", {}),
                timestamp=datetime.utcnow().isoformat(),
                message_hash=hash(str(group_data)),
            )
            combined_messages.append(message_entry)
            total_messages += 1

        return ModelAggregatedData(
            aggregation_strategy="combine",
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=groups_processed,
            combined_messages=combined_messages,
            total_messages=total_messages,
        )

    async def _reduce_aggregation(
        self,
        group_messages: List[Dict[str, str]],
        correlation_id: Optional[str],
    ) -> ModelAggregatedData:
        """Reduce messages using aggregation functions."""
        groups_processed = [
            msg.get("group_id", f"group_{i}") for i, msg in enumerate(group_messages)
        ]
        reduced_data = {
            "count": str(len(group_messages)),
            "groups": ",".join(groups_processed),
        }

        # Simple reduction - count numeric values
        numeric_values = []
        for group_data in group_messages:
            if "value" in group_data:
                try:
                    numeric_value = float(group_data["value"])
                    numeric_values.append(numeric_value)
                except (ValueError, TypeError):
                    pass

        if numeric_values:
            stats = ModelNumericStats(
                sum=sum(numeric_values),
                average=sum(numeric_values) / len(numeric_values),
                min=min(numeric_values),
                max=max(numeric_values),
                numeric_count=len(numeric_values),
            )
            reduced_data.update(
                {
                    "sum": str(stats.sum),
                    "average": str(stats.average),
                    "min": str(stats.min),
                    "max": str(stats.max),
                    "numeric_count": str(stats.numeric_count),
                }
            )

        return ModelAggregatedData(
            aggregation_strategy="reduce",
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=groups_processed,
            reduced_data=reduced_data,
        )

    async def _collect_aggregation(
        self,
        group_messages: List[Dict[str, str]],
        correlation_id: Optional[str],
    ) -> ModelAggregatedData:
        """Collect messages without processing, preserving original structure."""
        collected_messages = {}
        groups_processed = []
        collection_metadata = {
            "total_groups": str(len(group_messages)),
        }

        # Convert messages to string format for collection
        for idx, group_data in enumerate(group_messages):
            group_id = group_data.get("group_id", f"group_{idx}")
            groups_processed.append(group_id)

            message_content = group_data.get("message_content", str(group_data))
            collected_messages[group_id] = message_content
            collection_metadata[f"{group_id}_size"] = str(len(message_content))

        return ModelAggregatedData(
            aggregation_strategy="collect",
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat(),
            groups_processed=groups_processed,
            collected_messages=collected_messages,
            collection_metadata=collection_metadata,
        )

    def _deep_merge(
        self, dict1: Dict[str, str], dict2: Dict[str, str], source_prefix: str
    ) -> Dict[str, str]:
        """Deep merge two dictionaries with conflict tracking."""
        result = dict1.copy()

        for key, value in dict2.items():
            if key in result:
                # Conflict resolution - timestamp priority (keep newer)
                result[f"{key}_{source_prefix}"] = str(value)
                self.logger.debug(f"Conflict resolved for key {key}: kept both values")
            else:
                result[key] = str(value)

        return result


class NodeCanaryCompute(NodeComputeService):
    """
    Message Aggregator tool for ONEX Messaging Architecture v0.2.

    Provides cross-group message aggregation, intelligent coordination strategies,
    and PostgreSQL-based state management for distributed message processing.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize Message Aggregator with container injection."""
        super().__init__(container)
        self.domain = "infrastructure"
        self.db_pool: Optional[asyncpg.Pool] = None
        self.state_manager: Optional[StateManager] = None
        self.message_aggregator: Optional[MessageAggregator] = None
        self.operation_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "processing_times": [],
            "groups_processed": 0,
            "state_persistence_count": 0,
        }

    async def initialize(self) -> None:
        """Initialize database connections and components."""
        try:
            # Initialize PostgreSQL connection pool
            self.db_pool = await asyncpg.create_pool(
                host="localhost",
                port=5432,
                database="omnibase",
                user="postgres",
                password="",
                min_size=10,
                max_size=25,
            )

            # Initialize components
            self.state_manager = StateManager(self.db_pool)
            self.message_aggregator = MessageAggregator(self.db_pool)

            self.logger.info("Message Aggregator initialized successfully")

        except Exception as e:
            raise OnexError(f"Failed to initialize Message Aggregator: {str(e)}") from e

    async def cleanup(self) -> None:
        """Clean up database connections."""
        if self.db_pool:
            await self.db_pool.close()

    def health_check(self) -> ModelHealthStatus:
        """Single comprehensive health check for message aggregator."""
        try:
            issues = []

            # Check PostgreSQL connectivity
            if not self.db_pool:
                issues.append("PostgreSQL connection pool not initialized")
            elif hasattr(self.db_pool, "_closed") and self.db_pool._closed:
                issues.append("PostgreSQL connection pool is closed")

            # Check aggregation components
            if not self.state_manager:
                issues.append("State manager not initialized")
            if not self.message_aggregator:
                issues.append("Message aggregator not initialized")

            # Check state manager database connectivity
            if self.state_manager and not getattr(self.state_manager, "db_pool", None):
                issues.append("State manager database pool not available")

            # Check operation metrics
            metrics = self.operation_metrics
            total_ops = metrics.get("total_operations", 0)
            successful_ops = metrics.get("successful_operations", 0)
            failed_ops = metrics.get("failed_operations", 0)
            processing_times = metrics.get("processing_times", [])

            success_rate = (successful_ops / total_ops * 100) if total_ops > 0 else 100
            avg_processing_time = (
                sum(processing_times) / len(processing_times) if processing_times else 0
            )

            # Determine overall health status
            if issues:
                return ModelHealthStatus(
                    status=(
                        EnumHealthStatus.CRITICAL
                        if "not initialized" in str(issues)
                        else EnumHealthStatus.DEGRADED
                    ),
                    message=f"Critical components failed: {', '.join(issues)}",
                )
            elif failed_ops > 0 and success_rate < 95:
                return ModelHealthStatus(
                    status=EnumHealthStatus.DEGRADED,
                    message=f"High error rate: {success_rate:.1f}% success, {failed_ops} failures, avg time: {avg_processing_time:.1f}ms",
                )
            elif avg_processing_time > 10000:  # 10 seconds
                return ModelHealthStatus(
                    status=EnumHealthStatus.WARNING,
                    message=f"Slow processing detected: avg {avg_processing_time:.1f}ms, success rate: {success_rate:.1f}%",
                )
            else:
                # Get pool info if available
                pool_info = ""
                if self.db_pool and hasattr(self.db_pool, "get_size"):
                    try:
                        pool_size = self.db_pool.get_size()
                        min_size = self.db_pool.get_min_size()
                        max_size = self.db_pool.get_max_size()
                        pool_info = f", DB pool: {pool_size}/{min_size}-{max_size}"
                    except:
                        pool_info = ", DB pool: active"

                return ModelHealthStatus(
                    status=EnumHealthStatus.HEALTHY,
                    message=f"Message aggregator healthy: {total_ops} ops, {success_rate:.1f}% success, avg: {avg_processing_time:.1f}ms{pool_info}",
                )

        except Exception as e:
            self.logger.error(f"Message aggregator health check failed: {e}")
            return ModelHealthStatus(
                status=EnumHealthStatus.ERROR,
                message=f"Health check failed: {str(e)}",
            )

    async def aggregate_messages(
        self,
        group_messages: List[Dict[str, str]],
        aggregation_strategy: str,
        correlation_id: Optional[str] = None,
        timeout_ms: int = 60000,
    ) -> ModelMessageAggregatorOutput:
        """Aggregate messages from multiple tool groups."""
        start_time = time.time()

        try:
            self.operation_metrics["total_operations"] += 1
            self.operation_metrics["groups_processed"] += len(group_messages)

            # Execute aggregation
            aggregated_result = await self.message_aggregator.aggregate_messages(
                group_messages, aggregation_strategy, correlation_id
            )

            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self.operation_metrics["processing_times"].append(processing_time)
            self.operation_metrics["successful_operations"] += 1

            return ModelMessageAggregatorOutput(
                status="success",
                aggregated_result=ModelAggregationResult(
                    strategy_used=aggregation_strategy,
                    total_messages=len(group_messages),
                    result_data=(
                        aggregated_result.dict()
                        if hasattr(aggregated_result, "dict")
                        else {}
                    ),
                    processing_time_ms=processing_time,
                ),
                aggregation_metrics=self._get_aggregation_metrics(),
            )

        except Exception as e:
            self.operation_metrics["failed_operations"] += 1
            self.logger.error(f"Message aggregation failed: {e}")

            return ModelMessageAggregatorOutput(
                status="error",
                aggregated_result=ModelAggregationResult(
                    strategy_used=aggregation_strategy,
                    total_messages=0,
                    result_data={},
                    processing_time_ms=0.0,
                ),
                error_message=str(e),
                aggregation_metrics=self._get_aggregation_metrics(),
            )

    async def persist_state(
        self,
        state_key: str,
        state_data: ModelStateData,
        correlation_id: Optional[str] = None,
    ) -> ModelMessageAggregatorOutput:
        """Persist aggregation state to PostgreSQL."""
        try:
            success = await self.state_manager.persist_state(
                state_key, state_data, correlation_id
            )

            if success:
                self.operation_metrics["state_persistence_count"] += 1
                return ModelMessageAggregatorOutput(
                    status="success",
                    aggregated_result=ModelAggregationResult(
                        strategy_used="persist",
                        total_messages=1,
                        result_data={
                            "persistence_status": "completed",
                            "state_key": state_key,
                        },
                        processing_time_ms=0.0,
                    ),
                )
            else:
                return ModelMessageAggregatorOutput(
                    status="error",
                    aggregated_result=ModelAggregationResult(
                        strategy_used="persist",
                        total_messages=0,
                        result_data={},
                        processing_time_ms=0.0,
                    ),
                    error_message="State persistence failed",
                )

        except Exception as e:
            return ModelMessageAggregatorOutput(
                status="error",
                aggregated_result=ModelAggregationResult(
                    strategy_used="persist",
                    total_messages=0,
                    result_data={},
                    processing_time_ms=0.0,
                ),
                error_message=str(e),
            )

    async def restore_state(self, state_key: str) -> ModelMessageAggregatorOutput:
        """Restore aggregation state from PostgreSQL."""
        try:
            state_data = await self.state_manager.restore_state(state_key)

            if state_data:
                return ModelMessageAggregatorOutput(
                    status="success",
                    aggregated_result=ModelAggregationResult(
                        strategy_used="restore",
                        total_messages=1,
                        result_data={"restoration_status": "completed"},
                        processing_time_ms=0.0,
                    ),
                    state_snapshot=state_data.data,
                )
            else:
                return ModelMessageAggregatorOutput(
                    status="error",
                    aggregated_result=ModelAggregationResult(
                        strategy_used="restore",
                        total_messages=0,
                        result_data={},
                        processing_time_ms=0.0,
                    ),
                    error_message=f"No state found for key: {state_key}",
                )

        except Exception as e:
            return ModelMessageAggregatorOutput(
                status="error",
                aggregated_result=ModelAggregationResult(
                    strategy_used="restore",
                    total_messages=0,
                    result_data={},
                    processing_time_ms=0.0,
                ),
                error_message=str(e),
            )

    def _get_aggregation_metrics(self) -> ModelAggregationMetrics:
        """Get current aggregation metrics."""
        avg_processing_time = 0
        if self.operation_metrics["processing_times"]:
            avg_processing_time = sum(self.operation_metrics["processing_times"]) / len(
                self.operation_metrics["processing_times"]
            )

        return ModelAggregationMetrics(
            total_operations=self.operation_metrics["total_operations"],
            successful_operations=self.operation_metrics["successful_operations"],
            failed_operations=self.operation_metrics["failed_operations"],
            average_processing_time_ms=avg_processing_time,
            groups_processed=self.operation_metrics["groups_processed"],
            state_persistence_count=self.operation_metrics["state_persistence_count"],
        )

    # Main processing method for NodeBase
    async def process(
        self, input_data: ModelMessageAggregatorInput
    ) -> ModelMessageAggregatorOutput:
        """Process Message Aggregator requests."""
        if input_data.operation_type == "aggregate":
            return await self.aggregate_messages(
                group_messages=input_data.group_messages,
                aggregation_strategy=input_data.aggregation_strategy,
                correlation_id=input_data.correlation_id,
                timeout_ms=input_data.timeout_ms or 60000,
            )
        elif input_data.operation_type == "persist":
            if not input_data.state_key:
                return ModelMessageAggregatorOutput(
                    status="error",
                    aggregated_result={},
                    error_message="state_key required for persist operation",
                )
            # Convert group_messages to state data format
            state_data = ModelStateData(
                operation_type="persist",
                data={
                    f"message_{i}": str(msg)
                    for i, msg in enumerate(input_data.group_messages)
                },
                timestamp=datetime.utcnow().isoformat(),
                correlation_id=input_data.correlation_id,
            )
            return await self.persist_state(
                state_key=input_data.state_key,
                state_data=state_data,
                correlation_id=input_data.correlation_id,
            )
        elif input_data.operation_type == "restore":
            if not input_data.state_key:
                return ModelMessageAggregatorOutput(
                    status="error",
                    aggregated_result={},
                    error_message="state_key required for restore operation",
                )
            return await self.restore_state(input_data.state_key)
        else:
            return ModelMessageAggregatorOutput(
                status="error",
                aggregated_result={},
                error_message=f"Unknown operation type: {input_data.operation_type}",
            )


def main():
    """Main entry point for Message Aggregator - returns node instance with infrastructure container"""
    from ..container import create_infrastructure_container

    container = create_infrastructure_container()
    return NodeCanaryCompute(container)


if __name__ == "__main__":
    main()
