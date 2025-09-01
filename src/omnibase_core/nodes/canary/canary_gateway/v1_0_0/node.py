"""
Group Gateway - Message routing and response aggregation with PostgreSQL persistence.

This tool implements the Group Gateway component of ONEX Messaging Architecture v0.2,
providing intelligent message routing, response aggregation, and PostgreSQL-based caching.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import asyncpg
from omnibase.core.errors import OnexError
from omnibase.core.infrastructure_service_bases import NodeEffectService
from omnibase.core.onex_container import ONEXContainer
from pydantic import BaseModel, Field

from .models import (
    ModelAggregatedResponse,
    ModelGroupGatewayInput,
    ModelGroupGatewayOutput,
    ModelMessageData,
    ModelRoutingMetrics,
)


class ResponseAggregator:
    """Handles response aggregation with PostgreSQL caching."""

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize with database connection pool."""
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)

    async def aggregate_responses(
        self,
        responses: List[Dict[str, str]],
        operation_type: str,
        correlation_id: Optional[str] = None,
    ) -> ModelAggregatedResponse:
        """Aggregate multiple tool responses into a single response."""
        try:
            successful_responses = []
            failed_responses = []

            for response in responses:
                if response.get("status") == "success":
                    successful_responses.append(response)
                else:
                    failed_responses.append(response)

            return ModelAggregatedResponse(
                operation_type=operation_type,
                correlation_id=correlation_id,
                timestamp=datetime.utcnow().isoformat(),
                total_responses=len(responses),
                successful_responses=len(successful_responses),
                failed_responses=len(failed_responses),
                responses=successful_responses,
                errors=failed_responses,
            )

        except Exception as e:
            raise OnexError(f"Failed to aggregate responses: {str(e)}") from e

    async def get_cached_response(
        self, cache_key: str
    ) -> Optional[ModelAggregatedResponse]:
        """Retrieve cached response from PostgreSQL."""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT response_data, expires_at
                    FROM response_cache
                    WHERE cache_key = $1 AND expires_at > NOW()
                """
                row = await conn.fetchrow(query, cache_key)

                if row:
                    # Update access metrics
                    await conn.execute(
                        "UPDATE response_cache SET access_count = access_count + 1, last_accessed = NOW() WHERE cache_key = $1",
                        cache_key,
                    )
                    # Parse JSON data back to model
                    response_data = row["response_data"]
                    if isinstance(response_data, str):
                        import json

                        response_data = json.loads(response_data)
                    return ModelAggregatedResponse(**response_data)

                return None

        except Exception as e:
            self.logger.error(f"Cache lookup failed: {e}")
            return None

    async def cache_response(
        self,
        cache_key: str,
        response_data: ModelAggregatedResponse,
        ttl_seconds: int = 300,
    ) -> bool:
        """Store response in PostgreSQL cache."""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO response_cache (cache_key, response_data, created_at, expires_at, access_count, last_accessed)
                    VALUES ($1, $2, NOW(), $3, 0, NOW())
                    ON CONFLICT (cache_key) DO UPDATE SET
                        response_data = EXCLUDED.response_data,
                        expires_at = EXCLUDED.expires_at,
                        last_accessed = NOW()
                    """,
                    cache_key,
                    json.dumps(response_data.dict()),
                    expires_at,
                )

            return True

        except Exception as e:
            self.logger.error(f"Cache storage failed: {e}")
            return False

    def generate_cache_key(
        self,
        operation_type: str,
        target_tools: List[str],
        message_data: ModelMessageData,
    ) -> str:
        """Generate cache key for request."""
        # Create deterministic hash from request components
        key_components = {
            "operation": operation_type,
            "tools": sorted(target_tools),
            "data": message_data.dict(),
        }

        key_string = json.dumps(key_components, sort_keys=True)
        hash_digest = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"gw_{operation_type}_{hash_digest}"


class ToolGroupGateway(NodeEffectService):
    """
    Group Gateway tool for ONEX Messaging Architecture v0.2.

    Provides message routing, response aggregation, and PostgreSQL-based caching
    for efficient tool communication and response management.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize Group Gateway with container injection."""
        super().__init__(container)
        self.db_pool: Optional[asyncpg.Pool] = None
        self.response_aggregator: Optional[ResponseAggregator] = None
        self.routing_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }

    async def initialize(self) -> None:
        """Initialize database connections and components."""
        try:
            # Initialize PostgreSQL connection pool with environment configuration
            import os

            self.db_pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "omnibase"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                min_size=5,
                max_size=20,
            )

            # Initialize response aggregator
            self.response_aggregator = ResponseAggregator(self.db_pool)

            self.logger.info("Group Gateway initialized successfully")

        except Exception as e:
            raise OnexError(f"Failed to initialize Group Gateway: {str(e)}") from e

    async def cleanup(self) -> None:
        """Clean up database connections."""
        if self.db_pool:
            await self.db_pool.close()

    async def route_message(
        self,
        target_tools: List[str],
        message_data: ModelMessageData,
        operation_type: str = "route",
        correlation_id: Optional[str] = None,
        timeout_ms: int = 30000,
        cache_strategy: str = "cache_aside",
    ) -> ModelGroupGatewayOutput:
        """Route message to target tools and aggregate responses."""
        start_time = time.time()

        try:
            self.routing_metrics["total_requests"] += 1

            # Generate cache key
            cache_key = self.response_aggregator.generate_cache_key(
                operation_type, target_tools, message_data
            )

            # Check cache first (cache-aside pattern)
            cached_response = None
            if cache_strategy == "cache_aside":
                cached_response = await self.response_aggregator.get_cached_response(
                    cache_key
                )

                if cached_response:
                    self.routing_metrics["cache_hits"] += 1
                    self.routing_metrics["successful_requests"] += 1

                    return ModelGroupGatewayOutput(
                        status="success",
                        aggregated_response=cached_response,
                        cache_hit=True,
                        routing_metrics=self._get_routing_metrics(),
                    )

            # Cache miss - execute routing
            self.routing_metrics["cache_misses"] += 1

            # Route to target tools (simplified implementation)
            responses = await self._execute_routing(
                target_tools, message_data, timeout_ms
            )

            # Aggregate responses
            aggregated_response = await self.response_aggregator.aggregate_responses(
                responses, operation_type, correlation_id
            )

            # Cache the response
            if cache_strategy in ["cache_aside", "write_through"]:
                await self.response_aggregator.cache_response(
                    cache_key, aggregated_response
                )

            # Update metrics
            response_time = (time.time() - start_time) * 1000
            self.routing_metrics["response_times"].append(response_time)
            self.routing_metrics["successful_requests"] += 1

            return ModelGroupGatewayOutput(
                status="success",
                aggregated_response=aggregated_response,
                cache_hit=False,
                routing_metrics=self._get_routing_metrics(),
            )

        except Exception as e:
            self.routing_metrics["failed_requests"] += 1
            self.logger.error(f"Message routing failed: {e}")

            return ModelGroupGatewayOutput(
                status="error",
                aggregated_response={},
                error_message=str(e),
                routing_metrics=self._get_routing_metrics(),
            )

    async def _execute_routing(
        self, target_tools: List[str], message_data: ModelMessageData, timeout_ms: int
    ) -> List[Dict[str, str]]:
        """Execute routing to target tools (simplified implementation)."""
        # This is a simplified implementation - in production, this would
        # make actual HTTP/gRPC calls to target tools
        responses = []

        for tool in target_tools:
            try:
                # Simulate tool response
                response = {
                    "tool": tool,
                    "status": "success",
                    "data": f"Response from {tool}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                responses.append(response)

            except Exception as e:
                responses.append(
                    {
                        "tool": tool,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        return responses

    def _get_routing_metrics(self) -> ModelRoutingMetrics:
        """Get current routing metrics."""
        avg_response_time = 0
        if self.routing_metrics["response_times"]:
            avg_response_time = sum(self.routing_metrics["response_times"]) / len(
                self.routing_metrics["response_times"]
            )

        total_cache_requests = (
            self.routing_metrics["cache_hits"] + self.routing_metrics["cache_misses"]
        )
        cache_hit_ratio = 0
        if total_cache_requests > 0:
            cache_hit_ratio = self.routing_metrics["cache_hits"] / total_cache_requests

        return ModelRoutingMetrics(
            total_requests=self.routing_metrics["total_requests"],
            successful_requests=self.routing_metrics["successful_requests"],
            failed_requests=self.routing_metrics["failed_requests"],
            average_response_time_ms=avg_response_time,
            cache_hit_ratio=cache_hit_ratio,
        )

    async def health_check(self) -> ModelGroupGatewayOutput:
        """Check health of Group Gateway and dependencies."""
        try:
            health_status = {
                "group_gateway": "healthy",
                "postgresql": "unknown",
                "dependencies": [],
            }

            # Check PostgreSQL connection
            if self.db_pool:
                try:
                    async with self.db_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                    health_status["postgresql"] = "healthy"
                except Exception as e:
                    health_status["postgresql"] = f"unhealthy: {str(e)}"

            overall_status = (
                "healthy" if health_status["postgresql"] == "healthy" else "degraded"
            )

            return ModelGroupGatewayOutput(
                status=overall_status, aggregated_response=health_status
            )

        except Exception as e:
            return ModelGroupGatewayOutput(
                status="error", aggregated_response={}, error_message=str(e)
            )

    async def clear_cache(
        self, cache_pattern: Optional[str] = None
    ) -> ModelGroupGatewayOutput:
        """Clear response cache entries."""
        try:
            if not self.db_pool:
                raise OnexError("Database pool not initialized")

            async with self.db_pool.acquire() as conn:
                if cache_pattern:
                    result = await conn.execute(
                        "DELETE FROM response_cache WHERE cache_key LIKE $1",
                        f"%{cache_pattern}%",
                    )
                else:
                    result = await conn.execute("DELETE FROM response_cache")

                # Extract number of deleted rows
                deleted_count = int(result.split()[-1]) if result else 0

                return ModelGroupGatewayOutput(
                    status="success",
                    aggregated_response={"cleared_entries": deleted_count},
                )

        except Exception as e:
            return ModelGroupGatewayOutput(
                status="error", aggregated_response={}, error_message=str(e)
            )

    # Main processing method for NodeBase
    async def process(
        self, input_data: ModelGroupGatewayInput
    ) -> ModelGroupGatewayOutput:
        """Process Group Gateway requests."""
        if input_data.operation_type in ["route", "broadcast", "aggregate"]:
            return await self.route_message(
                target_tools=input_data.target_tools,
                message_data=input_data.message_data,
                operation_type=input_data.operation_type,
                correlation_id=input_data.correlation_id,
                timeout_ms=input_data.timeout_ms or 30000,
                cache_strategy=input_data.cache_strategy or "cache_aside",
            )
        else:
            return ModelGroupGatewayOutput(
                status="error",
                aggregated_response={},
                error_message=f"Unknown operation type: {input_data.operation_type}",
            )


def main():
    """Main entry point for Group Gateway - returns node instance with infrastructure container"""
    from omnibase.tools.infrastructure.container import create_infrastructure_container

    container = create_infrastructure_container()
    return ToolGroupGateway(container)


if __name__ == "__main__":
    main()
