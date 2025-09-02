"""
Group Gateway - Message routing and response aggregation with PostgreSQL persistence.

This tool implements the Group Gateway component of ONEX Messaging Architecture v0.2,
providing intelligent message routing, response aggregation, and PostgreSQL-based caching.
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timedelta

import asyncpg

from omnibase_core.core.errors import OnexError
from omnibase_core.core.infrastructure_service_bases import NodeEffectService
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.nodes.canary.config.canary_config import get_canary_config
from omnibase_core.nodes.canary.utils.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerException,
    get_circuit_breaker,
)
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler
from omnibase_core.nodes.canary.utils.metrics_collector import get_metrics_collector

from .models import (
    ModelAggregatedResponse,
    ModelGroupGatewayInput,
    ModelGroupGatewayOutput,
    ModelMessageData,
    ModelRoutingMetrics,
)


class ResponseAggregator:
    """Handles response aggregation with PostgreSQL caching."""

    def __init__(self, db_pool: asyncpg.Pool, db_circuit_breaker):
        """Initialize with database connection pool and circuit breaker."""
        self.db_pool = db_pool
        self.db_circuit_breaker = db_circuit_breaker
        self.logger = logging.getLogger(__name__)
        self.config = get_canary_config()
        self.error_handler = get_error_handler(self.logger)

    async def aggregate_responses(
        self,
        responses: list[dict[str, str]],
        operation_type: str,
        correlation_id: str | None = None,
    ) -> ModelAggregatedResponse:
        """Aggregate multiple tool responses into a single response."""
        context = self.error_handler.create_operation_context(
            "aggregate_responses",
            {"operation_type": operation_type, "response_count": len(responses)},
            correlation_id,
        )

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
            error_details = self.error_handler.handle_error(
                e, context, correlation_id, "aggregate_responses"
            )
            msg = f"Failed to aggregate responses: {error_details['message']}"
            raise OnexError(msg) from e

    async def get_cached_response(
        self,
        cache_key: str,
    ) -> ModelAggregatedResponse | None:
        """Retrieve cached response from PostgreSQL with circuit breaker protection."""
        try:
            # Use circuit breaker for database operations
            return await self.db_circuit_breaker.call(
                lambda: self._get_cached_response_impl(cache_key),
                fallback=lambda: None,  # Return None if database is down
            )
        except Exception as e:
            self.logger.exception(f"Cache lookup failed: {e}")
            return None

    async def _get_cached_response_impl(
        self, cache_key: str
    ) -> ModelAggregatedResponse | None:
        """Internal implementation for cached response retrieval."""
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

    async def cache_response(
        self,
        cache_key: str,
        response_data: ModelAggregatedResponse,
        ttl_seconds: int = None,
    ) -> bool:
        """Store response in PostgreSQL cache with circuit breaker protection."""
        try:
            # Use circuit breaker for database operations
            return await self.db_circuit_breaker.call(
                lambda: self._cache_response_impl(
                    cache_key, response_data, ttl_seconds
                ),
                fallback=lambda: False,  # Return False if database is down
            )
        except Exception as e:
            self.logger.exception(f"Cache storage failed: {e}")
            return False

    async def _cache_response_impl(
        self,
        cache_key: str,
        response_data: ModelAggregatedResponse,
        ttl_seconds: int = None,
    ) -> bool:
        """Internal implementation for cache response storage."""
        # Use configurable cache TTL
        if ttl_seconds is None:
            ttl_seconds = self.config.performance.cache_ttl_seconds
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

    def generate_cache_key(
        self,
        operation_type: str,
        target_tools: list[str],
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


class NodeCanaryGateway(NodeEffectService):
    """
    Group Gateway tool for ONEX Messaging Architecture v0.2.

    Provides message routing, response aggregation, and PostgreSQL-based caching
    for efficient tool communication and response management.
    """

    def __init__(self, container: ONEXContainer):
        """Initialize Group Gateway with container injection."""
        super().__init__(container)
        self.db_pool: asyncpg.Pool | None = None
        self.response_aggregator: ResponseAggregator | None = None

        # Initialize configuration and utilities
        self.config = get_canary_config()
        self.error_handler = get_error_handler(self.logger)
        self.metrics_collector = get_metrics_collector("canary_gateway")

        # Setup circuit breakers for external services
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            timeout_seconds=self.config.timeouts.api_call_timeout_ms / 1000,
        )
        self.api_circuit_breaker = get_circuit_breaker("external_api", cb_config)
        self.db_circuit_breaker = get_circuit_breaker("database", cb_config)

        # Rate limiting state
        self.rate_limit_requests = {}

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
            # Initialize PostgreSQL connection pool with configuration
            db_config = self.config.database
            self.db_pool = await asyncpg.create_pool(
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.username,
                password=db_config.password,
                min_size=db_config.min_pool_size,
                max_size=db_config.max_pool_size,
            )

            # Initialize response aggregator with circuit breaker
            self.response_aggregator = ResponseAggregator(
                self.db_pool, self.db_circuit_breaker
            )

            self.logger.info("Group Gateway initialized successfully")

        except Exception as e:
            msg = f"Failed to initialize Group Gateway: {e!s}"
            raise OnexError(msg) from e

    async def cleanup(self) -> None:
        """Clean up database connections."""
        if self.db_pool:
            await self.db_pool.close()

    def _check_rate_limit(self, client_id: str = "default") -> bool:
        """Check if client is within rate limits using configuration."""
        current_time = time.time()
        window_size = 60  # 1 minute window
        max_requests = self.config.performance.max_concurrent_operations

        # Clean old entries
        if client_id in self.rate_limit_requests:
            self.rate_limit_requests[client_id] = [
                timestamp
                for timestamp in self.rate_limit_requests[client_id]
                if current_time - timestamp < window_size
            ]
        else:
            self.rate_limit_requests[client_id] = []

        # Check limit
        if len(self.rate_limit_requests[client_id]) >= max_requests:
            self.metrics_collector.increment_counter(
                "rate_limit.exceeded", {"client_id": client_id}
            )
            return False

        # Add current request
        self.rate_limit_requests[client_id].append(current_time)
        self.metrics_collector.increment_counter(
            "rate_limit.allowed", {"client_id": client_id}
        )
        return True

    async def route_message(
        self,
        target_tools: list[str],
        message_data: ModelMessageData,
        operation_type: str = "route",
        correlation_id: str | None = None,
        timeout_ms: int = None,
        cache_strategy: str = "cache_aside",
        client_id: str = "default",
    ) -> ModelGroupGatewayOutput:
        """Route message to target tools and aggregate responses."""
        # Generate operation ID for tracking
        operation_id = str(uuid.uuid4())
        start_time = time.time()

        # Check rate limits
        if not self._check_rate_limit(client_id):
            return ModelGroupGatewayOutput(
                status="error",
                aggregated_response={},
                error_message="Rate limit exceeded",
                routing_metrics=self._get_routing_metrics(),
            )

        # Start metrics collection
        await self.metrics_collector.record_operation_start(
            operation_id, operation_type
        )

        # Create error handling context
        context = self.error_handler.create_operation_context(
            "route_message",
            {
                "operation_type": operation_type,
                "target_tools": target_tools,
                "cache_strategy": cache_strategy,
            },
            correlation_id,
        )

        try:
            self.routing_metrics["total_requests"] += 1

            # Generate cache key
            cache_key = self.response_aggregator.generate_cache_key(
                operation_type,
                target_tools,
                message_data,
            )

            # Check cache first (cache-aside pattern)
            cached_response = None
            if cache_strategy == "cache_aside":
                cached_response = await self.response_aggregator.get_cached_response(
                    cache_key,
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
                target_tools,
                message_data,
                timeout_ms,
            )

            # Aggregate responses
            aggregated_response = await self.response_aggregator.aggregate_responses(
                responses,
                operation_type,
                correlation_id,
            )

            # Cache the response
            if cache_strategy in ["cache_aside", "write_through"]:
                await self.response_aggregator.cache_response(
                    cache_key,
                    aggregated_response,
                )

            # Update metrics
            response_time = (time.time() - start_time) * 1000
            self.routing_metrics["response_times"].append(response_time)
            self.routing_metrics["successful_requests"] += 1

            # Record successful operation
            await self.metrics_collector.record_operation_end(
                operation_id, operation_type, True
            )

            return ModelGroupGatewayOutput(
                status="success",
                aggregated_response=aggregated_response,
                cache_hit=False,
                routing_metrics=self._get_routing_metrics(),
            )

        except Exception as e:
            self.routing_metrics["failed_requests"] += 1

            # Handle error with secure error handler
            error_details = self.error_handler.handle_error(
                e, context, correlation_id, "route_message"
            )

            # Record failed operation
            await self.metrics_collector.record_operation_end(
                operation_id, operation_type, False, type(e).__name__
            )

            return ModelGroupGatewayOutput(
                status="error",
                aggregated_response={},
                error_message=error_details["message"],
                routing_metrics=self._get_routing_metrics(),
            )

    async def _execute_routing(
        self,
        target_tools: list[str],
        message_data: ModelMessageData,
        timeout_ms: int,
    ) -> list[dict[str, str]]:
        """Execute routing to target tools with circuit breaker protection."""
        responses = []

        # Use configured timeout if not provided
        if timeout_ms is None:
            timeout_ms = self.config.timeouts.gateway_timeout_ms

        for tool in target_tools:
            try:
                # Use circuit breaker for external API calls
                response = await self.api_circuit_breaker.call(
                    lambda: self._call_tool(tool, message_data),
                    fallback=lambda: self._get_fallback_response(tool),
                )
                responses.append(response)

                # Record successful routing
                self.metrics_collector.increment_counter(
                    "tool.routing.success", {"tool": tool}
                )

            except Exception as e:
                error_response = {
                    "tool": tool,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                responses.append(error_response)

                # Record failed routing
                self.metrics_collector.increment_counter(
                    "tool.routing.failure",
                    {"tool": tool, "error_type": type(e).__name__},
                )

        return responses

    async def _call_tool(
        self, tool: str, message_data: ModelMessageData
    ) -> dict[str, str]:
        """Simulate calling an external tool (placeholder for actual implementation)."""
        # In production, this would make actual HTTP/gRPC calls
        # Add simulation delay from config
        import asyncio

        await asyncio.sleep(self.config.business_logic.api_simulation_delay_ms / 1000)

        return {
            "tool": tool,
            "status": "success",
            "data": f"Response from {tool}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _get_fallback_response(self, tool: str) -> dict[str, str]:
        """Get fallback response when tool is unavailable."""
        return {
            "tool": tool,
            "status": "fallback",
            "data": f"Fallback response for {tool} (service unavailable)",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _get_routing_metrics(self) -> ModelRoutingMetrics:
        """Get current routing metrics."""
        avg_response_time = 0
        if self.routing_metrics["response_times"]:
            avg_response_time = sum(self.routing_metrics["response_times"]) / len(
                self.routing_metrics["response_times"],
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
        """Check health of Group Gateway and dependencies with comprehensive monitoring."""
        operation_id = str(uuid.uuid4())
        await self.metrics_collector.record_operation_start(
            operation_id, "health_check"
        )

        context = self.error_handler.create_operation_context("health_check", {}, None)

        try:
            health_status = {
                "group_gateway": "healthy",
                "postgresql": "unknown",
                "circuit_breakers": {},
                "metrics": self.metrics_collector.get_node_metrics().model_dump(),
                "config_status": "loaded",
            }

            # Check PostgreSQL connection with circuit breaker
            if self.db_pool:
                try:
                    await self.db_circuit_breaker.call(
                        lambda: self._check_db_health(), fallback=lambda: None
                    )
                    health_status["postgresql"] = "healthy"
                except Exception as e:
                    health_status["postgresql"] = f"unhealthy: {e!s}"

            # Add circuit breaker stats
            health_status["circuit_breakers"] = {
                "api": self.api_circuit_breaker.get_stats(),
                "database": self.db_circuit_breaker.get_stats(),
            }

            overall_status = (
                "healthy" if health_status["postgresql"] == "healthy" else "degraded"
            )

            await self.metrics_collector.record_operation_end(
                operation_id, "health_check", True
            )

            return ModelGroupGatewayOutput(
                status=overall_status,
                aggregated_response=health_status,
            )

        except Exception as e:
            error_details = self.error_handler.handle_error(
                e, context, None, "health_check"
            )
            await self.metrics_collector.record_operation_end(
                operation_id, "health_check", False, type(e).__name__
            )

            return ModelGroupGatewayOutput(
                status="error",
                aggregated_response={},
                error_message=error_details["message"],
            )

    async def _check_db_health(self) -> None:
        """Internal database health check."""
        async with self.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

    async def clear_cache(
        self,
        cache_pattern: str | None = None,
    ) -> ModelGroupGatewayOutput:
        """Clear response cache entries with proper error handling and metrics."""
        operation_id = str(uuid.uuid4())
        await self.metrics_collector.record_operation_start(operation_id, "clear_cache")

        context = self.error_handler.create_operation_context(
            "clear_cache", {"cache_pattern": cache_pattern}, None
        )

        try:
            if not self.db_pool:
                msg = "Database pool not initialized"
                raise OnexError(msg)

            # Use circuit breaker for database operations
            deleted_count = await self.db_circuit_breaker.call(
                lambda: self._clear_cache_impl(cache_pattern)
            )

            await self.metrics_collector.record_operation_end(
                operation_id, "clear_cache", True
            )
            self.metrics_collector.increment_counter(
                "cache.cleared", {"pattern": cache_pattern or "all"}
            )

            return ModelGroupGatewayOutput(
                status="success",
                aggregated_response={"cleared_entries": deleted_count},
            )

        except Exception as e:
            error_details = self.error_handler.handle_error(
                e, context, None, "clear_cache"
            )
            await self.metrics_collector.record_operation_end(
                operation_id, "clear_cache", False, type(e).__name__
            )

            return ModelGroupGatewayOutput(
                status="error",
                aggregated_response={},
                error_message=error_details["message"],
            )

    async def _clear_cache_impl(self, cache_pattern: str | None = None) -> int:
        """Internal cache clearing implementation."""
        async with self.db_pool.acquire() as conn:
            if cache_pattern:
                result = await conn.execute(
                    "DELETE FROM response_cache WHERE cache_key LIKE $1",
                    f"%{cache_pattern}%",
                )
            else:
                result = await conn.execute("DELETE FROM response_cache")

            # Extract number of deleted rows
            return int(result.split()[-1]) if result else 0

    # Main processing method for NodeBase
    async def process(
        self,
        input_data: ModelGroupGatewayInput,
    ) -> ModelGroupGatewayOutput:
        """Process Group Gateway requests."""
        if input_data.operation_type in ["route", "broadcast", "aggregate"]:
            return await self.route_message(
                target_tools=input_data.target_tools,
                message_data=input_data.message_data,
                operation_type=input_data.operation_type,
                correlation_id=input_data.correlation_id,
                timeout_ms=input_data.timeout_ms
                or self.config.timeouts.gateway_timeout_ms,
                cache_strategy=input_data.cache_strategy or "cache_aside",
                client_id=getattr(input_data, "client_id", "default"),
            )
        return ModelGroupGatewayOutput(
            status="error",
            aggregated_response={},
            error_message=f"Unknown operation type: {input_data.operation_type}",
        )


def main():
    """Main entry point for Group Gateway - returns node instance with infrastructure container"""
    from canary.canary_gateway.container import create_infrastructure_container

    container = create_infrastructure_container()
    return NodeCanaryGateway(container)


if __name__ == "__main__":
    main()
