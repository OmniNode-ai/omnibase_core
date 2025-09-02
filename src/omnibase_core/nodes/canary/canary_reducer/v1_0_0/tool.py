"""
Canary Reducer Node - State aggregation for canary deployments.

Simple REDUCER node implementation for testing and validation purposes.
"""

import asyncio
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.core.node_base import ModelNodeBase


class ModelCanaryReducerInput(BaseModel):
    """Input model for Canary Reducer operations."""

    adapter_results: List[Dict[str, Any]] = Field(
        ..., description="Results from infrastructure adapters to aggregate"
    )
    operation_type: Optional[str] = Field(
        default="aggregate", description="Type of aggregation operation to perform"
    )


class ModelCanaryReducerOutput(BaseModel):
    """Output model for Canary Reducer operations."""

    status: str = Field(..., description="Operation status")
    aggregated_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated results from infrastructure adapters",
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )


class NodeCanaryReducer(ModelNodeBase):
    """
    Canary Reducer Node - State aggregation for canary deployments.

    Simple REDUCER node that aggregates results from multiple adapters,
    manages state transitions, and provides consolidated infrastructure status.
    """

    def __init__(self, contract_path=None, *args, **kwargs):
        from pathlib import Path

        # Use default contract path if not provided
        if contract_path is None:
            contract_path = Path(__file__).parent / "contract.yaml"

        super().__init__(contract_path=contract_path, *args, **kwargs)
        self._aggregation_count = 0
        self._cached_results: Dict[str, Dict[str, Any]] = {}
        self._infrastructure_status = "unknown"

    async def aggregate_results(
        self, input_data: ModelCanaryReducerInput
    ) -> ModelCanaryReducerOutput:
        """
        Aggregate results from infrastructure adapters.

        Args:
            input_data: Results to aggregate

        Returns:
            ModelCanaryReducerOutput with aggregated result
        """
        try:
            if input_data.operation_type == "bootstrap":
                result = await self._aggregate_bootstrap_results(
                    input_data.adapter_results
                )
            elif input_data.operation_type == "health_check":
                result = await self._aggregate_health_results(
                    input_data.adapter_results
                )
            elif input_data.operation_type == "failover":
                result = await self._aggregate_failover_results(
                    input_data.adapter_results
                )
            elif input_data.operation_type == "status_aggregation":
                result = await self._aggregate_status_results(
                    input_data.adapter_results
                )
            else:
                result = await self._aggregate_generic_results(
                    input_data.adapter_results
                )

            self._aggregation_count += 1
            self._update_infrastructure_status(result)

            return ModelCanaryReducerOutput(status="success", aggregated_result=result)

        except Exception as e:
            return ModelCanaryReducerOutput(
                status="failed",
                aggregated_result={},
                error_message=f"Reduction failed: {type(e).__name__}",
            )

    async def _aggregate_bootstrap_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate bootstrap results from adapters."""
        aggregated = {
            "bootstrap_status": "in_progress",
            "adapters": {},
            "ready_services": [],
            "failed_services": [],
            "total_services": 0,
        }

        for result in results:
            adapter_name = result.get("adapter_name", "unknown")
            status = result.get("status", "unknown")
            services = result.get("services", [])

            aggregated["adapters"][adapter_name] = {
                "status": status,
                "services": services,
                "service_count": len(services),
            }

            aggregated["total_services"] += len(services)

            # Categorize services
            for service in services:
                service_status = service.get("status", "unknown")
                service_name = service.get("name", "unnamed")

                if service_status in ["ready", "healthy"]:
                    aggregated["ready_services"].append(service_name)
                elif service_status in ["failed", "unhealthy", "error"]:
                    aggregated["failed_services"].append(service_name)

        # Determine overall bootstrap status
        total_ready = len(aggregated["ready_services"])
        total_failed = len(aggregated["failed_services"])

        if total_failed == 0 and total_ready > 0:
            aggregated["bootstrap_status"] = "completed"
        elif total_failed > 0:
            aggregated["bootstrap_status"] = "partial"

        return aggregated

    async def _aggregate_health_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate health check results from adapters."""
        aggregated = {
            "overall_health": "healthy",
            "adapters": {},
            "healthy_count": 0,
            "degraded_count": 0,
            "unhealthy_count": 0,
            "total_checks": len(results),
        }

        health_scores = []

        for result in results:
            adapter_name = result.get("adapter_name", "unknown")
            health_status = result.get("health_status", "unknown")
            health_score = result.get("health_score", 0.0)

            aggregated["adapters"][adapter_name] = {
                "status": health_status,
                "score": health_score,
                "details": result.get("details", {}),
            }

            health_scores.append(health_score)

            # Count by status
            if health_status == "healthy":
                aggregated["healthy_count"] += 1
            elif health_status == "degraded":
                aggregated["degraded_count"] += 1
            else:
                aggregated["unhealthy_count"] += 1

        # Calculate overall health
        if health_scores:
            avg_score = sum(health_scores) / len(health_scores)

            if avg_score >= 0.9:
                aggregated["overall_health"] = "healthy"
            elif avg_score >= 0.6:
                aggregated["overall_health"] = "degraded"
            else:
                aggregated["overall_health"] = "unhealthy"

            aggregated["average_health_score"] = avg_score

        return aggregated

    async def _aggregate_failover_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate failover operation results."""
        aggregated = {
            "failover_status": "in_progress",
            "adapters": {},
            "successful_failovers": 0,
            "failed_failovers": 0,
            "total_adapters": len(results),
        }

        for result in results:
            adapter_name = result.get("adapter_name", "unknown")
            failover_status = result.get("failover_status", "unknown")

            aggregated["adapters"][adapter_name] = {
                "status": failover_status,
                "primary_endpoint": result.get("primary_endpoint"),
                "backup_endpoint": result.get("backup_endpoint"),
                "switch_time_ms": result.get("switch_time_ms", 0),
            }

            if failover_status == "success":
                aggregated["successful_failovers"] += 1
            else:
                aggregated["failed_failovers"] += 1

        # Determine overall failover status
        if aggregated["failed_failovers"] == 0:
            aggregated["failover_status"] = "completed"
        elif aggregated["successful_failovers"] > aggregated["failed_failovers"]:
            aggregated["failover_status"] = "partial"
        else:
            aggregated["failover_status"] = "failed"

        return aggregated

    async def _aggregate_status_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate general status results."""
        aggregated = {
            "infrastructure_status": "unknown",
            "adapters": {},
            "service_summary": defaultdict(int),
            "last_updated": None,
        }

        all_ready = True
        any_failed = False

        for result in results:
            adapter_name = result.get("adapter_name", "unknown")
            services = result.get("services", [])

            aggregated["adapters"][adapter_name] = {
                "service_count": len(services),
                "services": services,
            }

            # Aggregate service status counts
            for service in services:
                status = service.get("status", "unknown")
                aggregated["service_summary"][status] += 1

                if status not in ["ready", "healthy"]:
                    all_ready = False
                if status in ["failed", "unhealthy", "error"]:
                    any_failed = True

        # Determine infrastructure status
        if all_ready:
            aggregated["infrastructure_status"] = "ready"
        elif any_failed:
            aggregated["infrastructure_status"] = "degraded"
        else:
            aggregated["infrastructure_status"] = "partial"

        return aggregated

    async def _aggregate_generic_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate generic results from adapters."""
        aggregated = {"result_count": len(results), "adapters": {}, "summary": {}}

        # Group results by adapter
        for result in results:
            adapter_name = result.get("adapter_name", "unknown")

            if adapter_name not in aggregated["adapters"]:
                aggregated["adapters"][adapter_name] = []

            aggregated["adapters"][adapter_name].append(result)

        # Create summary statistics
        aggregated["summary"] = {
            "total_results": len(results),
            "unique_adapters": len(aggregated["adapters"]),
            "avg_results_per_adapter": len(results)
            / max(1, len(aggregated["adapters"])),
        }

        return aggregated

    def _update_infrastructure_status(self, aggregation_result: Dict[str, Any]) -> None:
        """Update cached infrastructure status."""
        if "infrastructure_status" in aggregation_result:
            self._infrastructure_status = aggregation_result["infrastructure_status"]
        elif "overall_health" in aggregation_result:
            self._infrastructure_status = aggregation_result["overall_health"]
        elif "bootstrap_status" in aggregation_result:
            self._infrastructure_status = aggregation_result["bootstrap_status"]

    async def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get current infrastructure aggregation and readiness status."""
        return {
            "infrastructure_status": self._infrastructure_status,
            "adapter_health": "monitoring",
            "readiness_state": self._infrastructure_status,
            "aggregations_performed": self._aggregation_count,
            "cache_size": len(self._cached_results),
        }

    async def list_loaded_adapters(self) -> Dict[str, Any]:
        """List all loaded infrastructure adapters."""
        # Mock adapter list based on contract configuration
        adapters = [
            {
                "name": "consul_adapter",
                "type": "service_discovery",
                "status": "loaded",
                "version": "1.0.0",
            },
            {
                "name": "vault_adapter",
                "type": "secret_management",
                "status": "loaded",
                "version": "1.0.0",
            },
            {
                "name": "kafka_adapter",
                "type": "message_queue",
                "status": "loaded",
                "version": "1.0.0",
            },
            {
                "name": "group_gateway",
                "type": "message_routing",
                "status": "loaded",
                "version": "1.0.0",
            },
            {
                "name": "message_aggregator",
                "type": "message_processing",
                "status": "loaded",
                "version": "1.0.0",
            },
            {
                "name": "local_registry",
                "type": "service_registry",
                "status": "loaded",
                "version": "1.0.0",
            },
        ]

        return {
            "loaded_adapters": adapters,
            "adapter_count": len(adapters),
            "types": list(set(adapter["type"] for adapter in adapters)),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of infrastructure tool group."""
        return {
            "status": "healthy",
            "infrastructure_status": self._infrastructure_status,
            "aggregations_performed": self._aggregation_count,
            "node_type": "REDUCER",
            "node_name": "canary_reducer",
        }
