"""
Canary Gateway Node - Message routing and response aggregation.

Simple GATEWAY (EFFECT) node implementation for testing and validation purposes.
"""

import asyncio
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.core.node_base import ModelNodeBase


class ModelGroupGatewayInput(BaseModel):
    """Input model for Group Gateway operations."""

    operation_type: str = Field(..., description="Type of gateway operation to perform")
    target_tools: List[str] = Field(
        ..., description="List of target tools for message routing"
    )
    message_data: Dict[str, Any] = Field(..., description="Message payload data")
    correlation_id: Optional[str] = Field(
        default=None, description="Request correlation ID"
    )
    timeout_ms: Optional[int] = Field(
        default=10000, description="Request timeout in milliseconds"
    )
    cache_strategy: Optional[str] = Field(
        default="default", description="Caching strategy to use"
    )


class ModelGroupGatewayOutput(BaseModel):
    """Output model for Group Gateway operations."""

    status: str = Field(..., description="Operation status")
    aggregated_response: Dict[str, Any] = Field(
        default_factory=dict, description="Aggregated response from target tools"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )
    cache_hit: Optional[bool] = Field(
        default=None, description="Whether response was served from cache"
    )
    routing_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Routing performance metrics"
    )


class NodeCanaryGateway(ModelNodeBase):
    """
    Canary Gateway Node - Message routing and response aggregation.

    Simple GATEWAY node that routes messages to target tools, aggregates responses,
    and provides caching and load balancing for the canary deployment system.
    """

    def __init__(self, contract_path=None, *args, **kwargs):
        from pathlib import Path

        # Use default contract path if not provided
        if contract_path is None:
            contract_path = Path(__file__).parent / "contract.yaml"

        super().__init__(contract_path=contract_path, *args, **kwargs)
        self._routing_count = 0
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._routing_metrics = {
            "total_routes": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "cache_hits": 0,
            "avg_response_time_ms": 0,
        }
        self._response_times: List[float] = []

    async def route_message(
        self, input_data: ModelGroupGatewayInput
    ) -> ModelGroupGatewayOutput:
        """
        Route message to target tools and aggregate responses.

        Args:
            input_data: Message routing request

        Returns:
            ModelGroupGatewayOutput with aggregated response
        """
        start_time = time.time()

        try:
            # Check cache first
            cache_key = self._generate_cache_key(input_data)
            cached_response = await self._check_cache(cache_key)

            if cached_response:
                self._routing_metrics["cache_hits"] += 1
                response_time = int((time.time() - start_time) * 1000)

                return ModelGroupGatewayOutput(
                    status="success",
                    aggregated_response=cached_response,
                    cache_hit=True,
                    routing_metrics={"response_time_ms": response_time},
                )

            # Route to target tools
            if input_data.operation_type == "route":
                aggregated_response = await self._route_to_targets(
                    input_data.target_tools,
                    input_data.message_data,
                    input_data.timeout_ms or 10000,
                )
            elif input_data.operation_type == "broadcast":
                aggregated_response = await self._broadcast_to_targets(
                    input_data.target_tools,
                    input_data.message_data,
                    input_data.timeout_ms or 10000,
                )
            elif input_data.operation_type == "aggregate":
                aggregated_response = await self._aggregate_from_targets(
                    input_data.target_tools,
                    input_data.message_data,
                    input_data.timeout_ms or 10000,
                )
            else:
                aggregated_response = await self._generic_routing(
                    input_data.target_tools,
                    input_data.message_data,
                    input_data.operation_type,
                )

            # Cache the response
            await self._cache_response(cache_key, aggregated_response)

            # Update metrics
            response_time = int((time.time() - start_time) * 1000)
            self._update_routing_metrics(response_time, success=True)

            return ModelGroupGatewayOutput(
                status="success",
                aggregated_response=aggregated_response,
                cache_hit=False,
                routing_metrics={"response_time_ms": response_time},
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            self._update_routing_metrics(response_time, success=False)

            return ModelGroupGatewayOutput(
                status="failed",
                aggregated_response={},
                error_message=str(e),
                cache_hit=False,
                routing_metrics={"response_time_ms": response_time},
            )

    async def _route_to_targets(
        self, targets: List[str], message: Dict[str, Any], timeout_ms: int
    ) -> Dict[str, Any]:
        """Route message to targets using round-robin."""
        if not targets:
            return {"error": "No targets specified"}

        # Simple round-robin selection
        selected_target = targets[self._routing_count % len(targets)]

        # Simulate routing to target
        await asyncio.sleep(0.1)  # Simulate network delay

        response = await self._simulate_target_response(selected_target, message)

        return {
            "selected_target": selected_target,
            "response": response,
            "routing_strategy": "round_robin",
            "total_targets": len(targets),
        }

    async def _broadcast_to_targets(
        self, targets: List[str], message: Dict[str, Any], timeout_ms: int
    ) -> Dict[str, Any]:
        """Broadcast message to all targets."""
        if not targets:
            return {"error": "No targets specified"}

        # Simulate broadcasting to all targets
        tasks = [self._simulate_target_response(target, message) for target in targets]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate responses
        aggregated = {
            "broadcast_results": {},
            "successful_targets": 0,
            "failed_targets": 0,
            "total_targets": len(targets),
        }

        for i, response in enumerate(responses):
            target = targets[i]
            if isinstance(response, Exception):
                aggregated["broadcast_results"][target] = {"error": str(response)}
                aggregated["failed_targets"] += 1
            else:
                aggregated["broadcast_results"][target] = response
                aggregated["successful_targets"] += 1

        return aggregated

    async def _aggregate_from_targets(
        self, targets: List[str], message: Dict[str, Any], timeout_ms: int
    ) -> Dict[str, Any]:
        """Aggregate data from multiple targets."""
        if not targets:
            return {"error": "No targets specified"}

        # Get responses from all targets
        tasks = [self._simulate_target_response(target, message) for target in targets]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate the data
        aggregated_data = defaultdict(list)
        successful_responses = []

        for i, response in enumerate(responses):
            if not isinstance(response, Exception):
                successful_responses.append(response)

                # Aggregate by data type
                for key, value in response.items():
                    if isinstance(value, (int, float)):
                        aggregated_data[f"{key}_sum"] += [value]
                    elif isinstance(value, str):
                        aggregated_data[f"{key}_values"] += [value]

        # Calculate aggregations
        final_aggregation = {}
        for key, values in aggregated_data.items():
            if "_sum" in key:
                final_aggregation[key.replace("_sum", "_total")] = sum(values)
                final_aggregation[key.replace("_sum", "_avg")] = sum(values) / len(
                    values
                )
            elif "_values" in key:
                final_aggregation[key.replace("_values", "_unique")] = len(set(values))
                final_aggregation[key.replace("_values", "_count")] = len(values)

        return {
            "aggregation": final_aggregation,
            "successful_responses": len(successful_responses),
            "total_targets": len(targets),
            "response_count": len(successful_responses),
        }

    async def _generic_routing(
        self, targets: List[str], message: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """Perform generic routing operation."""
        # Select first target for generic operations
        if not targets:
            return {"error": "No targets specified"}

        target = targets[0]
        response = await self._simulate_target_response(target, message)

        return {
            "operation": operation,
            "target": target,
            "response": response,
            "message": message,
        }

    async def _simulate_target_response(
        self, target: str, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate response from a target tool."""
        # Simulate processing delay
        await asyncio.sleep(0.05 + (hash(target) % 10) / 100)  # 50-150ms

        # Generate mock response based on target type
        if "compute" in target.lower():
            return {
                "result": f"Computed data for {target}",
                "computation_time": 120 + (hash(target) % 50),
                "data_processed": len(str(message)),
            }
        elif "effect" in target.lower():
            return {
                "effect_applied": True,
                "target_system": target,
                "operation_status": "completed",
                "effects_count": 1 + (hash(target) % 3),
            }
        elif "reducer" in target.lower():
            return {
                "aggregated": True,
                "items_processed": len(message.get("items", [])),
                "reduction_factor": 0.8,
                "summary": f"Reduced data from {target}",
            }
        else:
            return {
                "target": target,
                "message_received": True,
                "response_data": message,
                "status": "ok",
            }

    def _generate_cache_key(self, input_data: ModelGroupGatewayInput) -> str:
        """Generate cache key for request."""
        key_components = [
            input_data.operation_type,
            "-".join(sorted(input_data.target_tools)),
            str(hash(str(sorted(input_data.message_data.items())))),
        ]
        return ":".join(key_components)

    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check cache for existing response."""
        # Simple cache check - in production this would check TTL
        if cache_key in self._response_cache:
            cached_entry = self._response_cache[cache_key]
            cache_time = cached_entry.get("cached_at", 0)

            # Simple TTL check (5 minutes)
            if time.time() - cache_time < 300:
                return cached_entry.get("response")

        return None

    async def _cache_response(self, cache_key: str, response: Dict[str, Any]) -> None:
        """Cache response for future requests."""
        # Simple cache implementation
        if len(self._response_cache) > 1000:  # Max cache size
            # Remove oldest entry
            oldest_key = min(
                self._response_cache.keys(),
                key=lambda k: self._response_cache[k].get("cached_at", 0),
            )
            del self._response_cache[oldest_key]

        self._response_cache[cache_key] = {
            "response": response,
            "cached_at": time.time(),
        }

    def _update_routing_metrics(self, response_time_ms: int, success: bool) -> None:
        """Update routing performance metrics."""
        self._routing_count += 1
        self._routing_metrics["total_routes"] += 1

        if success:
            self._routing_metrics["successful_routes"] += 1
        else:
            self._routing_metrics["failed_routes"] += 1

        # Update response time tracking
        self._response_times.append(response_time_ms)
        if len(self._response_times) > 1000:  # Keep last 1000 measurements
            self._response_times = self._response_times[-1000:]

        # Calculate average response time
        if self._response_times:
            self._routing_metrics["avg_response_time_ms"] = sum(
                self._response_times
            ) / len(self._response_times)

    async def clear_cache(self, cache_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Clear response cache entries."""
        if cache_pattern:
            # Clear entries matching pattern
            cleared = 0
            keys_to_remove = [
                key for key in self._response_cache.keys() if cache_pattern in key
            ]
            for key in keys_to_remove:
                del self._response_cache[key]
                cleared += 1
        else:
            # Clear all entries
            cleared = len(self._response_cache)
            self._response_cache.clear()

        return {"cleared_entries": cleared}

    async def get_routing_metrics(self) -> Dict[str, Any]:
        """Get current routing performance metrics."""
        current_metrics = self._routing_metrics.copy()
        current_metrics.update(
            {
                "cache_size": len(self._response_cache),
                "success_rate": (
                    self._routing_metrics["successful_routes"]
                    / max(1, self._routing_metrics["total_routes"])
                )
                * 100,
            }
        )
        return current_metrics

    async def health_check(self) -> Dict[str, Any]:
        """Check health of group gateway and dependencies."""
        return {
            "status": "healthy",
            "routes_processed": self._routing_count,
            "cache_entries": len(self._response_cache),
            "success_rate": (
                self._routing_metrics["successful_routes"]
                / max(1, self._routing_metrics["total_routes"])
            )
            * 100,
            "node_type": "EFFECT",
            "node_name": "canary_gateway",
        }
