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
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from omnibase_spi import ProtocolCacheService

from omnibase_core.core.errors import OnexError
from omnibase_core.core.infrastructure_service_bases import NodeEffectService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.nodes.canary.utils.circuit_breaker import (
    CircuitBreakerException,
    ModelCircuitBreakerConfig,
    get_circuit_breaker,
)
from omnibase_core.nodes.canary.utils.error_handler import get_error_handler
from omnibase_core.nodes.canary.utils.metrics_collector import get_metrics_collector
from omnibase_core.services.cache_service import InMemoryCacheServiceProvider
from omnibase_core.utils.node_configuration_utils import UtilsNodeConfiguration

from .models import (
    ModelAggregatedResponse,
    ModelGroupGatewayInput,
    ModelGroupGatewayOutput,
    ModelMessageData,
    ModelRoutingMetrics,
)


class ResponseAggregator:
    """Handles response aggregation with protocol-based cache service."""

    def __init__(
        self, container: ModelONEXContainer, cache_service: ProtocolCacheService
    ):
        """Initialize with container dependency injection and cache service."""
        self.container = container
        self.cache_service = cache_service
        self.logger = logging.getLogger(__name__)
        self.config_utils = UtilsNodeConfiguration(container)
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
        correlation_id: str | None = None,
    ) -> ModelAggregatedResponse | None:
        """Retrieve cached response using protocol-based cache service."""
        try:
            # Use protocol-based cache service
            cached_data = await self.cache_service.get(cache_key)
            if cached_data is None:
                return None

            # Convert cached data back to ModelAggregatedResponse
            return ModelAggregatedResponse(**cached_data)
        except Exception as e:
            # Use secure error handler for cache lookup failures
            error_details = self.error_handler.handle_error(
                e, {"cache_key": cache_key}, correlation_id, "cache_lookup"
            )
            correlation_context = (
                f" [correlation_id={correlation_id}]" if correlation_id else ""
            )
            self.logger.exception(
                f"Cache lookup failed: {error_details['message']} [cache_key={cache_key}]{correlation_context}"
            )
            return None

    async def cache_response(
        self,
        cache_key: str,
        response_data: ModelAggregatedResponse,
        ttl_seconds: int = None,
        correlation_id: str | None = None,
    ) -> bool:
        """Store response using protocol-based cache service."""
        try:
            # Use configurable cache TTL
            if ttl_seconds is None:
                ttl_seconds = int(
                    self.config_utils.get_performance_config("cache_ttl_seconds", 300)
                )

            # Convert ModelAggregatedResponse to dictionary for caching
            cache_data = response_data.model_dump()

            # Use protocol-based cache service
            return await self.cache_service.set(cache_key, cache_data, ttl_seconds)
        except Exception as e:
            # Use secure error handler for cache storage failures
            error_details = self.error_handler.handle_error(
                e, {"cache_key": cache_key}, correlation_id, "cache_storage"
            )
            correlation_context = (
                f" [correlation_id={correlation_id}]" if correlation_id else ""
            )
            self.logger.exception(
                f"Cache storage failed: {error_details['message']} [cache_key={cache_key}]{correlation_context}"
            )
            return False

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
            "data": message_data.model_dump(),
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

    def __init__(self, container: ModelONEXContainer):
        """Initialize Group Gateway with container injection."""
        super().__init__(container)
        self.response_aggregator: ResponseAggregator | None = None

        # Initialize configuration and utilities with container-based DI
        self.config_utils = UtilsNodeConfiguration(container)
        self.error_handler = get_error_handler(self.logger)
        self.metrics_collector = get_metrics_collector("canary_gateway")

        # Setup circuit breakers for external services with default timeouts
        api_timeout_ms = self.config_utils.get_timeout_ms("api_call", 10000)
        cb_config = ModelCircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            timeout_seconds=api_timeout_ms / 1000,
        )
        self.api_circuit_breaker = get_circuit_breaker("external_api", cb_config)

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
        """Initialize components with protocol-based cache service."""
        try:
            # Create cache service provider and get cache service
            cache_provider = InMemoryCacheServiceProvider()
            cache_service = cache_provider.create_cache_service()

            # Initialize response aggregator with protocol-based cache service
            self.response_aggregator = ResponseAggregator(self.container, cache_service)

            self.logger.info(
                "Group Gateway initialized successfully with protocol-based cache service"
            )

        except Exception as e:
            # Handle initialization error with secure error handler
            error_details = self.error_handler.handle_error(
                e,
                {"operation": "initialize"},
                None,
                "initialize",
            )
            msg = f"Failed to initialize Group Gateway: {error_details['message']}"
            raise OnexError(msg) from e

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Clean up cache service resources if needed
        if hasattr(self.response_aggregator, "cache_service"):
            # Clear all cache entries on shutdown
            await self.response_aggregator.cache_service.clear()
        self.logger.info("Gateway cleanup completed")

    def _check_rate_limit(self, client_id: str = "default") -> bool:
        """Check if client is within rate limits using configuration."""
        current_time = time.time()
        window_size = 60  # 1 minute window
        max_requests = int(
            self.config_utils.get_performance_config("max_concurrent_operations", 100)
        )

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
                    correlation_id,
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
                    None,  # ttl_seconds - use default
                    correlation_id,
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
            timeout_ms = self.config_utils.get_timeout_ms("gateway", 10000)

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
                # Use secure error handler for tool routing errors
                error_details = self.error_handler.handle_error(
                    e, {"tool": tool}, None, "tool_routing"
                )
                error_response = {
                    "tool": tool,
                    "status": "error",
                    "error": f"Tool routing failed: {error_details['message']}",
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
        # Simulate delay only in debug mode
        debug_mode = bool(self.config_utils.get_security_config("debug_mode", False))
        if debug_mode:
            import asyncio

            delay_ms = float(
                self.config_utils.get_business_logic_config(
                    "api_simulation_delay_ms", 100
                )
            )
            await asyncio.sleep(delay_ms / 1000)

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
                "cache_service": "active",
                "circuit_breakers": {},
                "metrics": self.metrics_collector.get_node_metrics().model_dump(),
                "config_status": "loaded",
            }

            # Check cache service health
            cache_healthy = self.response_aggregator is not None and hasattr(
                self.response_aggregator, "cache_service"
            )
            if cache_healthy:
                # Get cache statistics
                cache_stats = self.response_aggregator.cache_service.get_stats()
                health_status["cache_service"] = "healthy"
                health_status["cache_stats"] = cache_stats
            else:
                health_status["cache_service"] = "unavailable"

            # Add circuit breaker stats
            health_status["circuit_breakers"] = {
                "api": self.api_circuit_breaker.get_stats(),
            }

            overall_status = "healthy" if cache_healthy else "degraded"

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
            # Use protocol-based cache service for clearing
            deleted_count = await self.response_aggregator.cache_service.clear(
                cache_pattern
            )

            await self.metrics_collector.record_operation_end(
                operation_id, "clear_cache", True
            )
            self.metrics_collector.increment_counter(
                "cache.cleared", {"pattern": cache_pattern or "all"}
            )

            return ModelGroupGatewayOutput(
                status="success",
                aggregated_response=ModelAggregatedResponse(
                    operation_type="clear_cache",
                    correlation_id=getattr(context, "correlation_id", None),
                    timestamp=datetime.now().isoformat(),
                    total_responses=1,
                    successful_responses=1,
                    failed_responses=0,
                    responses=[{"cleared_entries": str(deleted_count)}],
                    errors=[],
                ),
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
                aggregated_response=ModelAggregatedResponse(
                    operation_type="clear_cache",
                    correlation_id=getattr(context, "correlation_id", None),
                    timestamp=datetime.now().isoformat(),
                    total_responses=0,
                    successful_responses=0,
                    failed_responses=1,
                    responses=[],
                    errors=[{"error": error_details["message"]}],
                ),
                error_message=error_details["message"],
            )

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
                or self.config_utils.get_timeout_ms("gateway", 10000),
                cache_strategy=input_data.cache_strategy or "cache_aside",
                client_id=getattr(input_data, "client_id", "default"),
            )
        return ModelGroupGatewayOutput(
            status="error",
            aggregated_response=ModelAggregatedResponse(
                operation_type=input_data.operation_type,
                correlation_id=input_data.correlation_id,
                timestamp=datetime.now().isoformat(),
                total_responses=0,
                successful_responses=0,
                failed_responses=1,
                responses=[],
                errors=[
                    {"error": f"Unknown operation type: {input_data.operation_type}"}
                ],
            ),
            error_message=f"Unknown operation type: {input_data.operation_type}",
        )

    async def route(
        self, input_data: ModelGroupGatewayInput
    ) -> ModelGroupGatewayOutput:
        """Route message - alias for process method to satisfy contract validator."""
        return await self.process(input_data)

    async def get_health_status(self) -> dict[str, str | int | bool]:
        """Get gateway health status."""
        cache_healthy = self.response_aggregator is not None and hasattr(
            self.response_aggregator, "cache_service"
        )
        return {
            "status": "healthy" if cache_healthy else "degraded",
            "node_type": "gateway",
            "cache_service_connected": cache_healthy,
            "total_requests": self.routing_metrics["total_requests"],
            "successful_requests": self.routing_metrics["successful_requests"],
            "timestamp": datetime.now().isoformat(),
        }

    async def get_metrics(self) -> dict[str, str | int | float]:
        """Get gateway performance metrics."""
        avg_response_time = 0.0
        response_times = self.routing_metrics["response_times"]
        if response_times and isinstance(response_times, list):
            avg_response_time = sum(response_times) / len(response_times)

        total_requests = self.routing_metrics["total_requests"]
        cache_hits = self.routing_metrics["cache_hits"]
        cache_hit_rate = (
            cache_hits / max(1, total_requests)
            if isinstance(total_requests, (int, float))
            and isinstance(cache_hits, (int, float))
            else 0.0
        )

        return {
            "total_requests": total_requests,
            "successful_requests": self.routing_metrics["successful_requests"],
            "failed_requests": self.routing_metrics["failed_requests"],
            "average_response_time_ms": avg_response_time,
            "cache_hit_rate": cache_hit_rate,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Main entry point for Group Gateway - returns node instance with infrastructure container"""
    from omnibase_core.nodes.canary.container import create_infrastructure_container

    container = create_infrastructure_container()
    return NodeCanaryGateway(container)


if __name__ == "__main__":
    main()
