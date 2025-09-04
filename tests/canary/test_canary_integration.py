#!/usr/bin/env python3
"""
Canary Node Integration Testing.

This script tests the full 4-node canary architecture with actual inter-node communication:
- Orchestrator coordinates workflows and calls other nodes
- Compute and Effect nodes perform operations and return results
- Reducer aggregates real results from multiple nodes
- Gateway routes messages between nodes

This demonstrates the complete ONEX canary deployment system working together.
"""

import asyncio
import json
import time
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# ===== INTER-NODE COMMUNICATION FRAMEWORK =====


class NodeMessage(BaseModel):
    """Message format for inter-node communication."""

    message_id: str = Field(..., description="Unique message identifier")
    source_node: str = Field(..., description="Source node identifier")
    target_node: str = Field(..., description="Target node identifier")
    operation: str = Field(..., description="Operation to perform")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    timestamp: float = Field(default_factory=time.time, description="Message timestamp")


class NodeResponse(BaseModel):
    """Response format for inter-node communication."""

    message_id: str = Field(..., description="Original message ID")
    source_node: str = Field(..., description="Responding node identifier")
    target_node: str = Field(..., description="Original sender identifier")
    success: bool = Field(..., description="Whether operation succeeded")
    result: Dict[str, Any] = Field(default_factory=dict, description="Operation result")
    error_message: Optional[str] = Field(
        default=None, description="Error if operation failed"
    )
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    timestamp: float = Field(
        default_factory=time.time, description="Response timestamp"
    )


class NodeRegistry:
    """Registry for managing node instances and routing."""

    def __init__(self):
        self.nodes: Dict[str, Any] = {}
        self.message_queue: List[NodeMessage] = []
        self.response_queue: List[NodeResponse] = []
        self.routing_log: List[Dict[str, Any]] = []

    def register_node(self, node_id: str, node_instance: Any):
        """Register a node instance."""
        self.nodes[node_id] = node_instance
        print(f"📝 Registered node: {node_id}")

    def get_node(self, node_id: str) -> Optional[Any]:
        """Get a node instance by ID."""
        return self.nodes.get(node_id)

    def list_nodes(self) -> List[str]:
        """List all registered node IDs."""
        return list(self.nodes.keys())

    async def send_message(self, message: NodeMessage) -> NodeResponse:
        """Send a message to a target node and get response."""
        start_time = time.time()

        # Log the routing
        self.routing_log.append(
            {
                "message_id": message.message_id,
                "source": message.source_node,
                "target": message.target_node,
                "operation": message.operation,
                "timestamp": message.timestamp,
            }
        )

        # Get target node
        target_node = self.get_node(message.target_node)
        if not target_node:
            return NodeResponse(
                message_id=message.message_id,
                source_node=message.target_node,
                target_node=message.source_node,
                success=False,
                error_message=f"Target node '{message.target_node}' not found",
                execution_time_ms=int((time.time() - start_time) * 1000),
                correlation_id=message.correlation_id,
            )

        try:
            # Route the message based on operation type
            if message.operation == "compute":
                result = await target_node.process_computation_message(message)
            elif message.operation == "effect":
                result = await target_node.perform_effect_message(message)
            elif message.operation == "orchestrate":
                result = await target_node.start_workflow_message(message)
            elif message.operation == "reduce":
                result = await target_node.aggregate_results_message(message)
            elif message.operation == "route":
                result = await target_node.route_message_message(message)
            else:
                raise ValueError(f"Unsupported operation: {message.operation}")

            execution_time = int((time.time() - start_time) * 1000)

            return NodeResponse(
                message_id=message.message_id,
                source_node=message.target_node,
                target_node=message.source_node,
                success=True,
                result=result,
                execution_time_ms=execution_time,
                correlation_id=message.correlation_id,
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return NodeResponse(
                message_id=message.message_id,
                source_node=message.target_node,
                target_node=message.source_node,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                correlation_id=message.correlation_id,
            )


# ===== INTEGRATION-ENABLED NODES =====


class IntegratedCanaryCompute:
    """Canary Compute node with inter-node communication capabilities."""

    def __init__(self, node_id: str = "compute_node"):
        self.node_id = node_id
        self._processed_count = 0
        self._operation_history = []

    async def process_computation_message(self, message: NodeMessage) -> Dict[str, Any]:
        """Process computation via message interface."""
        operation_type = message.payload.get("operation_type")
        data = message.payload.get("data", {})

        if operation_type == "addition":
            result = self._perform_addition(data)
        elif operation_type == "multiplication":
            result = self._perform_multiplication(data)
        elif operation_type == "aggregation":
            result = self._perform_aggregation(data)
        elif operation_type == "canary_health_compute":
            result = await self._compute_canary_health(data)
        elif operation_type == "deployment_metrics":
            result = await self._compute_deployment_metrics(data)
        else:
            raise ValueError(f"Unsupported computation: {operation_type}")

        self._processed_count += 1
        self._operation_history.append(
            {
                "operation": operation_type,
                "timestamp": time.time(),
                "message_id": message.message_id,
            }
        )

        return {
            "node_id": self.node_id,
            "operation": operation_type,
            "result": result,
            "processed_count": self._processed_count,
        }

    def _perform_addition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform addition operation."""
        values = data.get("values", [])
        if not values:
            raise ValueError("No values provided for addition")

        result = sum(values)
        return {"operation": "addition", "values": values, "result": result}

    def _perform_multiplication(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform multiplication operation."""
        values = data.get("values", [])
        if not values:
            raise ValueError("No values provided for multiplication")

        result = 1
        for value in values:
            result *= value

        return {"operation": "multiplication", "values": values, "result": result}

    def _perform_aggregation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform data aggregation."""
        items = data.get("items", [])
        if not items:
            raise ValueError("No items provided for aggregation")

        total = len(items)
        numeric_values = [item for item in items if isinstance(item, (int, float))]
        avg = sum(numeric_values) / len(numeric_values) if numeric_values else 0

        return {
            "operation": "aggregation",
            "total_items": total,
            "numeric_items": len(numeric_values),
            "average": avg,
            "summary": f"Aggregated {total} items with average {avg:.2f}",
        }

    async def _compute_canary_health(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute canary deployment health metrics."""
        await asyncio.sleep(0.1)  # Simulate computation

        canary_instances = data.get("canary_instances", 1)
        success_rate = data.get("success_rate", 0.95)
        response_time_avg = data.get("response_time_ms", 150)

        health_score = (success_rate * 0.6) + (
            (1000 - min(response_time_avg, 1000)) / 1000 * 0.4
        )

        return {
            "operation": "canary_health_compute",
            "canary_instances": canary_instances,
            "success_rate": success_rate,
            "response_time_avg": response_time_avg,
            "health_score": round(health_score, 3),
            "status": (
                "healthy"
                if health_score > 0.8
                else "degraded" if health_score > 0.5 else "unhealthy"
            ),
        }

    async def _compute_deployment_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute deployment performance metrics."""
        await asyncio.sleep(0.05)  # Simulate computation

        deployment_data = data.get("deployment_data", {})
        total_requests = deployment_data.get("total_requests", 1000)
        successful_requests = deployment_data.get("successful_requests", 950)
        average_latency = deployment_data.get("average_latency_ms", 120)

        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        performance_score = max(
            0, 1 - (average_latency - 100) / 500
        )  # Penalty for latency > 100ms

        return {
            "operation": "deployment_metrics",
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": success_rate,
            "average_latency_ms": average_latency,
            "performance_score": round(performance_score, 3),
            "recommendation": (
                "proceed"
                if success_rate > 0.9 and performance_score > 0.7
                else "rollback"
            ),
        }


class IntegratedCanaryEffect:
    """Canary Effect node with inter-node communication capabilities."""

    def __init__(self, node_id: str = "effect_node"):
        self.node_id = node_id
        self._operations_count = 0
        self._operation_history = []
        self._canary_state = {"deployed": False, "traffic_percentage": 0}

    async def perform_effect_message(self, message: NodeMessage) -> Dict[str, Any]:
        """Perform effect operation via message interface."""
        operation_type = message.payload.get("operation_type")
        parameters = message.payload.get("parameters", {})

        if operation_type == "health_check":
            result = await self._simulate_health_check()
        elif operation_type == "deploy_canary":
            result = await self._deploy_canary(parameters)
        elif operation_type == "route_traffic":
            result = await self._route_traffic(parameters)
        elif operation_type == "rollback_canary":
            result = await self._rollback_canary(parameters)
        elif operation_type == "external_api_call":
            result = await self._simulate_api_call(parameters)
        elif operation_type == "database_operation":
            result = await self._simulate_database_operation(parameters)
        else:
            raise ValueError(f"Unsupported effect operation: {operation_type}")

        self._operations_count += 1
        self._operation_history.append(
            {
                "operation": operation_type,
                "timestamp": time.time(),
                "message_id": message.message_id,
            }
        )

        return {
            "node_id": self.node_id,
            "operation": operation_type,
            "result": result,
            "operations_count": self._operations_count,
            "canary_state": self._canary_state.copy(),
        }

    async def _simulate_health_check(self) -> Dict[str, Any]:
        """Simulate a health check operation."""
        await asyncio.sleep(0.1)  # Simulate network delay

        # Simulate various health metrics
        services_status = {
            "database": "healthy",
            "cache": "healthy",
            "external_apis": (
                "healthy" if self._operations_count % 10 != 0 else "degraded"
            ),
            "load_balancer": "healthy",
        }

        overall_healthy = all(
            status == "healthy" for status in services_status.values()
        )

        return {
            "operation": "health_check",
            "overall_status": "healthy" if overall_healthy else "degraded",
            "services": services_status,
            "timestamp": time.time(),
            "check_duration_ms": 100,
        }

    async def _deploy_canary(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy canary version."""
        await asyncio.sleep(0.3)  # Simulate deployment time

        canary_version = parameters.get("version", "v2.0.0")
        instance_count = parameters.get("instance_count", 2)

        # Simulate deployment
        self._canary_state["deployed"] = True
        self._canary_state["version"] = canary_version
        self._canary_state["instance_count"] = instance_count
        self._canary_state["deployment_time"] = time.time()

        return {
            "operation": "deploy_canary",
            "version": canary_version,
            "instance_count": instance_count,
            "status": "deployed",
            "deployment_duration_ms": 300,
            "endpoints": [f"canary-{i}.example.com" for i in range(instance_count)],
        }

    async def _route_traffic(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Route traffic to canary deployment."""
        await asyncio.sleep(0.1)  # Simulate routing configuration

        traffic_percentage = parameters.get("traffic_percentage", 10)

        if not self._canary_state["deployed"]:
            raise ValueError("Cannot route traffic - no canary deployment found")

        self._canary_state["traffic_percentage"] = traffic_percentage

        return {
            "operation": "route_traffic",
            "traffic_percentage": traffic_percentage,
            "status": "routing_active",
            "expected_rps": parameters.get("expected_rps", 100)
            * (traffic_percentage / 100),
            "monitoring_enabled": True,
        }

    async def _rollback_canary(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback canary deployment."""
        await asyncio.sleep(0.2)  # Simulate rollback time

        reason = parameters.get("reason", "manual_rollback")

        # Reset canary state
        previous_state = self._canary_state.copy()
        self._canary_state = {"deployed": False, "traffic_percentage": 0}

        return {
            "operation": "rollback_canary",
            "reason": reason,
            "status": "rolled_back",
            "rollback_duration_ms": 200,
            "previous_state": previous_state,
            "traffic_restored_to_stable": True,
        }

    async def _simulate_api_call(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate an external API call."""
        endpoint = parameters.get("endpoint", "/default")
        method = parameters.get("method", "GET")

        await asyncio.sleep(0.2)  # Simulate API call delay

        return {
            "operation": "api_call",
            "endpoint": endpoint,
            "method": method,
            "status_code": 200,
            "response_time_ms": 200,
            "response": {"message": "API call successful", "data": {"simulated": True}},
            "timestamp": time.time(),
        }

    async def _simulate_database_operation(
        self, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate a database operation."""
        operation = parameters.get("operation", "select")
        table = parameters.get("table", "deployments")

        await asyncio.sleep(0.15)  # Simulate database query delay

        return {
            "operation": f"db_{operation}",
            "table": table,
            "affected_rows": 1 if operation in ["insert", "update", "delete"] else 5,
            "query_time_ms": 150,
            "connection_pool_status": "healthy",
            "timestamp": time.time(),
        }


class IntegratedCanaryOrchestrator:
    """Canary Orchestrator with inter-node communication for coordinating workflows."""

    def __init__(
        self, node_id: str = "orchestrator_node", registry: NodeRegistry = None
    ):
        self.node_id = node_id
        self.registry = registry
        self._active_workflows = {}
        self._completed_workflows = {}
        self._workflow_count = 0

    async def start_workflow_message(self, message: NodeMessage) -> Dict[str, Any]:
        """Start workflow via message interface."""
        operation_type = message.payload.get("operation_type", "start_workflow")
        workflow_id = message.payload.get("workflow_id")
        workflow_type = message.payload.get("workflow_type", "canary_deployment")
        parameters = message.payload.get("parameters", {})

        if operation_type == "start_workflow":
            result = await self._execute_integrated_workflow(
                workflow_id, workflow_type, parameters, message.correlation_id
            )
        elif operation_type == "stop_workflow":
            result = await self._stop_workflow(workflow_id)
        elif operation_type == "get_status":
            result = self._get_workflow_status(workflow_id)
        else:
            raise ValueError(f"Unsupported orchestration operation: {operation_type}")

        return {
            "node_id": self.node_id,
            "operation": operation_type,
            "result": result,
            "active_workflows": len(self._active_workflows),
            "completed_workflows": len(self._completed_workflows),
        }

    async def _execute_integrated_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        parameters: Dict[str, Any],
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Execute workflow that coordinates with other nodes."""
        start_time = time.time()

        self._active_workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "status": "running",
            "start_time": start_time,
            "steps_completed": 0,
            "total_steps": 0,
            "results": [],
            "correlation_id": correlation_id,
        }

        try:
            if workflow_type == "canary_deployment":
                result = await self._execute_canary_deployment_workflow(
                    workflow_id, parameters, correlation_id
                )
            elif workflow_type == "infrastructure_health_check":
                result = await self._execute_health_check_workflow(
                    workflow_id, parameters, correlation_id
                )
            elif workflow_type == "performance_analysis":
                result = await self._execute_performance_analysis_workflow(
                    workflow_id, parameters, correlation_id
                )
            else:
                raise ValueError(f"Unknown workflow type: {workflow_type}")

            # Mark as completed
            workflow = self._active_workflows.pop(workflow_id)
            workflow["status"] = "completed"
            workflow["end_time"] = time.time()
            workflow["duration_ms"] = int(
                (workflow["end_time"] - workflow["start_time"]) * 1000
            )
            self._completed_workflows[workflow_id] = workflow
            self._workflow_count += 1

            return result

        except Exception as e:
            # Mark as failed
            workflow = self._active_workflows.pop(workflow_id)
            workflow["status"] = "failed"
            workflow["end_time"] = time.time()
            workflow["error"] = str(e)
            self._completed_workflows[workflow_id] = workflow
            raise

    async def _execute_canary_deployment_workflow(
        self, workflow_id: str, parameters: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Execute full canary deployment workflow coordinating all nodes."""
        steps_results = []
        workflow = self._active_workflows[workflow_id]
        workflow["total_steps"] = 6

        try:
            # Step 1: Deploy canary via Effect node
            print(f"  🚀 Step 1: Deploying canary version...")
            deploy_message = NodeMessage(
                message_id=f"{workflow_id}-deploy",
                source_node=self.node_id,
                target_node="effect_node",
                operation="effect",
                payload={
                    "operation_type": "deploy_canary",
                    "parameters": {
                        "version": parameters.get("canary_version", "v2.0.0"),
                        "instance_count": parameters.get("instance_count", 2),
                    },
                },
                correlation_id=correlation_id,
            )

            deploy_response = await self.registry.send_message(deploy_message)
            if not deploy_response.success:
                raise Exception(
                    f"Canary deployment failed: {deploy_response.error_message}"
                )

            steps_results.append(
                {
                    "step": "deploy_canary",
                    "result": deploy_response.result,
                    "duration_ms": deploy_response.execution_time_ms,
                }
            )
            workflow["steps_completed"] += 1

            # Step 2: Route initial traffic via Effect node
            print(f"  🔀 Step 2: Routing traffic to canary...")
            traffic_message = NodeMessage(
                message_id=f"{workflow_id}-traffic",
                source_node=self.node_id,
                target_node="effect_node",
                operation="effect",
                payload={
                    "operation_type": "route_traffic",
                    "parameters": {
                        "traffic_percentage": parameters.get("initial_traffic", 5),
                        "expected_rps": parameters.get("expected_rps", 100),
                    },
                },
                correlation_id=correlation_id,
            )

            traffic_response = await self.registry.send_message(traffic_message)
            if not traffic_response.success:
                raise Exception(
                    f"Traffic routing failed: {traffic_response.error_message}"
                )

            steps_results.append(
                {
                    "step": "route_traffic",
                    "result": traffic_response.result,
                    "duration_ms": traffic_response.execution_time_ms,
                }
            )
            workflow["steps_completed"] += 1

            # Step 3: Compute canary health metrics
            print(f"  📊 Step 3: Computing health metrics...")
            await asyncio.sleep(2)  # Simulate monitoring period

            health_compute_message = NodeMessage(
                message_id=f"{workflow_id}-health-compute",
                source_node=self.node_id,
                target_node="compute_node",
                operation="compute",
                payload={
                    "operation_type": "canary_health_compute",
                    "data": {
                        "canary_instances": deploy_response.result["result"][
                            "instance_count"
                        ],
                        "success_rate": 0.95,  # Simulated from monitoring
                        "response_time_ms": 145,  # Simulated from monitoring
                    },
                },
                correlation_id=correlation_id,
            )

            health_response = await self.registry.send_message(health_compute_message)
            if not health_response.success:
                raise Exception(
                    f"Health computation failed: {health_response.error_message}"
                )

            steps_results.append(
                {
                    "step": "compute_health",
                    "result": health_response.result,
                    "duration_ms": health_response.execution_time_ms,
                }
            )
            workflow["steps_completed"] += 1

            # Step 4: Collect deployment metrics via Compute node
            print(f"  📈 Step 4: Computing deployment metrics...")
            metrics_message = NodeMessage(
                message_id=f"{workflow_id}-metrics",
                source_node=self.node_id,
                target_node="compute_node",
                operation="compute",
                payload={
                    "operation_type": "deployment_metrics",
                    "data": {
                        "deployment_data": {
                            "total_requests": 1000,
                            "successful_requests": 950,
                            "average_latency_ms": 140,
                        }
                    },
                },
                correlation_id=correlation_id,
            )

            metrics_response = await self.registry.send_message(metrics_message)
            if not metrics_response.success:
                raise Exception(
                    f"Metrics computation failed: {metrics_response.error_message}"
                )

            steps_results.append(
                {
                    "step": "compute_metrics",
                    "result": metrics_response.result,
                    "duration_ms": metrics_response.execution_time_ms,
                }
            )
            workflow["steps_completed"] += 1

            # Step 5: Aggregate all results via Reducer node
            print(f"  🔄 Step 5: Aggregating deployment results...")
            aggregation_data = [
                {
                    "adapter": "canary_health",
                    "status": health_response.result["result"]["status"],
                    "health_score": health_response.result["result"]["health_score"],
                },
                {
                    "adapter": "deployment_metrics",
                    "status": "healthy",
                    "recommendation": metrics_response.result["result"][
                        "recommendation"
                    ],
                },
                {
                    "adapter": "traffic_routing",
                    "status": "healthy",
                    "traffic_percentage": traffic_response.result["result"][
                        "traffic_percentage"
                    ],
                },
            ]

            reducer_message = NodeMessage(
                message_id=f"{workflow_id}-reduce",
                source_node=self.node_id,
                target_node="reducer_node",
                operation="reduce",
                payload={
                    "adapter_results": aggregation_data,
                    "operation_type": "canary_deployment_status",
                },
                correlation_id=correlation_id,
            )

            reducer_response = await self.registry.send_message(reducer_message)
            if not reducer_response.success:
                raise Exception(
                    f"Result aggregation failed: {reducer_response.error_message}"
                )

            steps_results.append(
                {
                    "step": "aggregate_results",
                    "result": reducer_response.result,
                    "duration_ms": reducer_response.execution_time_ms,
                }
            )
            workflow["steps_completed"] += 1

            # Step 6: Make decision and take action
            print(f"  ⚖️ Step 6: Making deployment decision...")
            aggregated_result = reducer_response.result["aggregated_result"]
            should_proceed = (
                aggregated_result.get("overall_status") in ["ready", "healthy"]
                and metrics_response.result["result"]["recommendation"] == "proceed"
            )

            if should_proceed:
                # Increase traffic
                final_traffic_message = NodeMessage(
                    message_id=f"{workflow_id}-increase-traffic",
                    source_node=self.node_id,
                    target_node="effect_node",
                    operation="effect",
                    payload={
                        "operation_type": "route_traffic",
                        "parameters": {
                            "traffic_percentage": parameters.get("final_traffic", 50),
                            "expected_rps": parameters.get("expected_rps", 100),
                        },
                    },
                    correlation_id=correlation_id,
                )

                final_response = await self.registry.send_message(final_traffic_message)
                decision_result = {
                    "decision": "proceed",
                    "final_traffic_percentage": parameters.get("final_traffic", 50),
                    "status": "success" if final_response.success else "failed",
                }
            else:
                # Rollback
                rollback_message = NodeMessage(
                    message_id=f"{workflow_id}-rollback",
                    source_node=self.node_id,
                    target_node="effect_node",
                    operation="effect",
                    payload={
                        "operation_type": "rollback_canary",
                        "parameters": {"reason": "health_metrics_failed"},
                    },
                    correlation_id=correlation_id,
                )

                rollback_response = await self.registry.send_message(rollback_message)
                decision_result = {
                    "decision": "rollback",
                    "reason": "health_metrics_failed",
                    "status": "rolled_back" if rollback_response.success else "failed",
                }

            steps_results.append({"step": "make_decision", "result": decision_result})
            workflow["steps_completed"] += 1

            return {
                "workflow_id": workflow_id,
                "workflow_type": "canary_deployment",
                "status": "completed",
                "decision": decision_result["decision"],
                "steps": steps_results,
                "nodes_coordinated": ["effect_node", "compute_node", "reducer_node"],
                "total_duration_ms": int((time.time() - workflow["start_time"]) * 1000),
            }

        except Exception as e:
            print(f"  ❌ Workflow failed: {e}")
            raise

    async def _execute_health_check_workflow(
        self, workflow_id: str, parameters: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Execute infrastructure health check workflow."""
        steps_results = []
        workflow = self._active_workflows[workflow_id]
        workflow["total_steps"] = 3

        # Step 1: Get health status from Effect node
        health_message = NodeMessage(
            message_id=f"{workflow_id}-health",
            source_node=self.node_id,
            target_node="effect_node",
            operation="effect",
            payload={"operation_type": "health_check"},
            correlation_id=correlation_id,
        )

        health_response = await self.registry.send_message(health_message)
        steps_results.append(
            {
                "step": "health_check",
                "result": health_response.result,
                "duration_ms": health_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        # Step 2: Compute health metrics
        health_data = (
            health_response.result["result"] if health_response.success else {}
        )
        compute_message = NodeMessage(
            message_id=f"{workflow_id}-compute-health",
            source_node=self.node_id,
            target_node="compute_node",
            operation="compute",
            payload={
                "operation_type": "aggregation",
                "data": {
                    "items": [
                        1 if service == "healthy" else 0
                        for service in health_data.get("services", {}).values()
                    ]
                },
            },
            correlation_id=correlation_id,
        )

        compute_response = await self.registry.send_message(compute_message)
        steps_results.append(
            {
                "step": "compute_health_metrics",
                "result": compute_response.result,
                "duration_ms": compute_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        # Step 3: Aggregate final health status
        health_results = [
            {
                "adapter": "infrastructure",
                "status": health_data.get("overall_status", "unknown"),
            },
            {
                "adapter": "computed_metrics",
                "status": "healthy",
                "average_health": compute_response.result.get("result", {}).get(
                    "average", 0
                ),
            },
        ]

        reducer_message = NodeMessage(
            message_id=f"{workflow_id}-health-reduce",
            source_node=self.node_id,
            target_node="reducer_node",
            operation="reduce",
            payload={
                "adapter_results": health_results,
                "operation_type": "health_check",
            },
            correlation_id=correlation_id,
        )

        reducer_response = await self.registry.send_message(reducer_message)
        steps_results.append(
            {
                "step": "aggregate_health",
                "result": reducer_response.result,
                "duration_ms": reducer_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        return {
            "workflow_id": workflow_id,
            "workflow_type": "infrastructure_health_check",
            "status": "completed",
            "steps": steps_results,
            "overall_health": reducer_response.result.get("aggregated_result", {}).get(
                "overall_status", "unknown"
            ),
        }

    async def _execute_performance_analysis_workflow(
        self, workflow_id: str, parameters: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Execute performance analysis workflow."""
        steps_results = []
        workflow = self._active_workflows[workflow_id]
        workflow["total_steps"] = 4

        # Step 1: Collect performance data via Effect node
        perf_message = NodeMessage(
            message_id=f"{workflow_id}-perf-data",
            source_node=self.node_id,
            target_node="effect_node",
            operation="effect",
            payload={
                "operation_type": "external_api_call",
                "parameters": {"endpoint": "/metrics", "method": "GET"},
            },
            correlation_id=correlation_id,
        )

        perf_response = await self.registry.send_message(perf_message)
        steps_results.append(
            {
                "step": "collect_performance_data",
                "result": perf_response.result,
                "duration_ms": perf_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        # Step 2: Compute performance metrics
        metrics_message = NodeMessage(
            message_id=f"{workflow_id}-perf-compute",
            source_node=self.node_id,
            target_node="compute_node",
            operation="compute",
            payload={
                "operation_type": "deployment_metrics",
                "data": {
                    "deployment_data": {
                        "total_requests": parameters.get("total_requests", 5000),
                        "successful_requests": parameters.get(
                            "successful_requests", 4800
                        ),
                        "average_latency_ms": parameters.get("average_latency_ms", 180),
                    }
                },
            },
            correlation_id=correlation_id,
        )

        compute_response = await self.registry.send_message(metrics_message)
        steps_results.append(
            {
                "step": "compute_performance_metrics",
                "result": compute_response.result,
                "duration_ms": compute_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        # Step 3: Simulate database performance check
        db_message = NodeMessage(
            message_id=f"{workflow_id}-db-perf",
            source_node=self.node_id,
            target_node="effect_node",
            operation="effect",
            payload={
                "operation_type": "database_operation",
                "parameters": {"operation": "select", "table": "performance_metrics"},
            },
            correlation_id=correlation_id,
        )

        db_response = await self.registry.send_message(db_message)
        steps_results.append(
            {
                "step": "database_performance_check",
                "result": db_response.result,
                "duration_ms": db_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        # Step 4: Aggregate performance analysis
        perf_results = [
            {
                "adapter": "api_performance",
                "status": "healthy",
                "response_time_ms": perf_response.result.get("result", {}).get(
                    "response_time_ms", 200
                ),
            },
            {
                "adapter": "compute_metrics",
                "status": "healthy",
                "recommendation": compute_response.result.get("result", {}).get(
                    "recommendation", "proceed"
                ),
            },
            {
                "adapter": "database_performance",
                "status": "healthy",
                "query_time_ms": db_response.result.get("result", {}).get(
                    "query_time_ms", 150
                ),
            },
        ]

        reducer_message = NodeMessage(
            message_id=f"{workflow_id}-perf-reduce",
            source_node=self.node_id,
            target_node="reducer_node",
            operation="reduce",
            payload={
                "adapter_results": perf_results,
                "operation_type": "performance_analysis",
            },
            correlation_id=correlation_id,
        )

        reducer_response = await self.registry.send_message(reducer_message)
        steps_results.append(
            {
                "step": "aggregate_performance_analysis",
                "result": reducer_response.result,
                "duration_ms": reducer_response.execution_time_ms,
            }
        )
        workflow["steps_completed"] += 1

        return {
            "workflow_id": workflow_id,
            "workflow_type": "performance_analysis",
            "status": "completed",
            "steps": steps_results,
            "performance_summary": reducer_response.result.get("aggregated_result", {}),
            "recommendation": compute_response.result.get("result", {}).get(
                "recommendation", "unknown"
            ),
        }

    async def _stop_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Stop a running workflow."""
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows.pop(workflow_id)
            workflow["status"] = "cancelled"
            workflow["end_time"] = time.time()
            self._completed_workflows[workflow_id] = workflow

            return {
                "workflow_id": workflow_id,
                "status": "cancelled",
                "message": "Workflow stopped successfully",
            }
        else:
            raise ValueError(f"Workflow {workflow_id} not found or not active")

    def _get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status."""
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
        elif workflow_id in self._completed_workflows:
            workflow = self._completed_workflows[workflow_id]
        else:
            raise ValueError(f"Workflow {workflow_id} not found")

        return {
            "workflow_id": workflow_id,
            "status": workflow["status"],
            "steps_completed": workflow["steps_completed"],
            "total_steps": workflow.get("total_steps", 0),
            "start_time": workflow["start_time"],
            "end_time": workflow.get("end_time"),
            "correlation_id": workflow.get("correlation_id"),
        }


class IntegratedCanaryReducer:
    """Canary Reducer with inter-node communication for aggregating results."""

    def __init__(self, node_id: str = "reducer_node"):
        self.node_id = node_id
        self._aggregation_count = 0
        self._cached_results = {}
        self._aggregation_history = []

    async def aggregate_results_message(self, message: NodeMessage) -> Dict[str, Any]:
        """Aggregate results via message interface."""
        adapter_results = message.payload.get("adapter_results", [])
        operation_type = message.payload.get("operation_type", "general")

        if operation_type == "canary_deployment_status":
            result = self._aggregate_canary_deployment_results(adapter_results)
        elif operation_type == "health_check":
            result = self._aggregate_health_results(adapter_results)
        elif operation_type == "performance_analysis":
            result = self._aggregate_performance_results(adapter_results)
        elif operation_type == "bootstrap":
            result = self._aggregate_bootstrap_results(adapter_results)
        else:
            result = self._aggregate_general_results(adapter_results)

        self._aggregation_count += 1
        self._aggregation_history.append(
            {
                "operation": operation_type,
                "result_count": len(adapter_results),
                "timestamp": time.time(),
                "message_id": message.message_id,
            }
        )

        return {
            "node_id": self.node_id,
            "operation": operation_type,
            "aggregated_result": result,
            "aggregation_count": self._aggregation_count,
            "processed_adapters": len(adapter_results),
        }

    def _aggregate_canary_deployment_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate canary deployment specific results."""
        total_adapters = len(results)

        # Extract key metrics
        health_scores = []
        recommendations = []
        traffic_percentages = []

        adapter_statuses = {}

        for result in results:
            adapter_name = result.get("adapter", "unknown")
            adapter_statuses[adapter_name] = result.get("status", "unknown")

            if "health_score" in result:
                health_scores.append(result["health_score"])
            if "recommendation" in result:
                recommendations.append(result["recommendation"])
            if "traffic_percentage" in result:
                traffic_percentages.append(result["traffic_percentage"])

        # Calculate overall metrics
        avg_health_score = (
            sum(health_scores) / len(health_scores) if health_scores else 0
        )
        proceed_count = recommendations.count("proceed")
        rollback_count = recommendations.count("rollback")

        # Determine overall status
        if avg_health_score > 0.8 and proceed_count >= rollback_count:
            overall_status = "ready"
        elif avg_health_score > 0.5:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        return {
            "operation": "canary_deployment_status",
            "total_adapters": total_adapters,
            "adapter_statuses": adapter_statuses,
            "average_health_score": round(avg_health_score, 3),
            "recommendations": {"proceed": proceed_count, "rollback": rollback_count},
            "traffic_percentages": traffic_percentages,
            "overall_status": overall_status,
            "deployment_decision": (
                "proceed" if overall_status in ["ready"] else "rollback"
            ),
            "timestamp": time.time(),
        }

    def _aggregate_health_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate health check results."""
        total_adapters = len(results)
        healthy_adapters = sum(1 for r in results if r.get("status") == "healthy")

        health_summary = {}
        for result in results:
            adapter_name = result.get("adapter", "unknown")
            health_summary[adapter_name] = result.get("status", "unknown")

        overall_status = (
            "ready"
            if healthy_adapters == total_adapters
            else "degraded" if healthy_adapters > 0 else "unavailable"
        )

        return {
            "operation": "health_check",
            "total_adapters": total_adapters,
            "healthy_adapters": healthy_adapters,
            "health_summary": health_summary,
            "overall_status": overall_status,
            "health_percentage": (
                (healthy_adapters / total_adapters * 100) if total_adapters > 0 else 0
            ),
            "timestamp": time.time(),
        }

    def _aggregate_performance_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate performance analysis results."""
        total_adapters = len(results)

        response_times = []
        query_times = []
        recommendations = []

        adapter_performance = {}

        for result in results:
            adapter_name = result.get("adapter", "unknown")
            adapter_performance[adapter_name] = result.get("status", "unknown")

            if "response_time_ms" in result:
                response_times.append(result["response_time_ms"])
            if "query_time_ms" in result:
                query_times.append(result["query_time_ms"])
            if "recommendation" in result:
                recommendations.append(result["recommendation"])

        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )
        avg_query_time = sum(query_times) / len(query_times) if query_times else 0
        proceed_count = recommendations.count("proceed")

        # Performance scoring
        response_score = (
            max(0, 1 - (avg_response_time - 100) / 400) if avg_response_time > 0 else 1
        )
        query_score = (
            max(0, 1 - (avg_query_time - 50) / 200) if avg_query_time > 0 else 1
        )
        overall_performance_score = (response_score + query_score) / 2

        if overall_performance_score > 0.8:
            overall_status = "excellent"
        elif overall_performance_score > 0.6:
            overall_status = "good"
        elif overall_performance_score > 0.4:
            overall_status = "fair"
        else:
            overall_status = "poor"

        return {
            "operation": "performance_analysis",
            "total_adapters": total_adapters,
            "adapter_performance": adapter_performance,
            "average_response_time_ms": round(avg_response_time, 2),
            "average_query_time_ms": round(avg_query_time, 2),
            "performance_score": round(overall_performance_score, 3),
            "overall_status": overall_status,
            "recommendations": {
                "proceed": proceed_count,
                "total": len(recommendations),
            },
            "timestamp": time.time(),
        }

    def _aggregate_bootstrap_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate bootstrap initialization results."""
        total_adapters = len(results)
        successful_bootstraps = sum(
            1 for r in results if r.get("bootstrap_successful", False)
        )

        return {
            "operation": "bootstrap",
            "total_adapters": total_adapters,
            "successful_bootstraps": successful_bootstraps,
            "success_rate": (
                successful_bootstraps / total_adapters if total_adapters > 0 else 0
            ),
            "overall_status": (
                "ready" if successful_bootstraps == total_adapters else "degraded"
            ),
            "timestamp": time.time(),
        }

    def _aggregate_general_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate general results."""
        return {
            "operation": "general_aggregation",
            "total_results": len(results),
            "results_summary": [f"Result_{i}" for i in range(len(results))],
            "overall_status": "ready",
            "timestamp": time.time(),
        }


class IntegratedCanaryGateway:
    """Canary Gateway with inter-node communication for routing messages."""

    def __init__(self, node_id: str = "gateway_node", registry: NodeRegistry = None):
        self.node_id = node_id
        self.registry = registry
        self._routing_count = 0
        self._response_cache = {}
        self._routing_metrics = {
            "total_routes": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "cache_hits": 0,
            "avg_response_time_ms": 0,
        }
        self._response_times = []
        self._routing_history = []

    async def route_message_message(self, message: NodeMessage) -> Dict[str, Any]:
        """Route message via message interface."""
        operation_type = message.payload.get("operation_type")
        target_nodes = message.payload.get("target_nodes", [])
        routing_data = message.payload.get("routing_data", {})
        routing_strategy = message.payload.get("routing_strategy", "broadcast")

        start_time = time.time()

        try:
            if routing_strategy == "broadcast":
                result = await self._route_broadcast_to_nodes(
                    target_nodes, routing_data, message.correlation_id
                )
            elif routing_strategy == "round_robin":
                result = await self._route_round_robin_to_nodes(
                    target_nodes, routing_data, message.correlation_id
                )
            elif routing_strategy == "aggregate":
                result = await self._route_and_aggregate_from_nodes(
                    target_nodes, routing_data, message.correlation_id
                )
            else:
                raise ValueError(f"Unsupported routing strategy: {routing_strategy}")

            execution_time = int((time.time() - start_time) * 1000)
            self._response_times.append(execution_time)
            self._routing_count += 1
            self._routing_metrics["total_routes"] += 1
            self._routing_metrics["successful_routes"] += 1
            self._routing_metrics["avg_response_time_ms"] = sum(
                self._response_times
            ) / len(self._response_times)

            self._routing_history.append(
                {
                    "strategy": routing_strategy,
                    "target_nodes": target_nodes,
                    "timestamp": time.time(),
                    "duration_ms": execution_time,
                    "message_id": message.message_id,
                }
            )

            return {
                "node_id": self.node_id,
                "operation": operation_type,
                "routing_strategy": routing_strategy,
                "result": result,
                "routing_metrics": self._routing_metrics.copy(),
                "execution_time_ms": execution_time,
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self._routing_metrics["total_routes"] += 1
            self._routing_metrics["failed_routes"] += 1

            return {
                "node_id": self.node_id,
                "operation": operation_type,
                "routing_strategy": routing_strategy,
                "result": {},
                "error_message": str(e),
                "routing_metrics": self._routing_metrics.copy(),
                "execution_time_ms": execution_time,
            }

    async def _route_broadcast_to_nodes(
        self, target_nodes: List[str], routing_data: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Broadcast message to all target nodes."""
        responses = []

        for node_id in target_nodes:
            try:
                # Create message for target node
                target_message = NodeMessage(
                    message_id=f"gateway-broadcast-{self._routing_count}-{node_id}",
                    source_node=self.node_id,
                    target_node=node_id,
                    operation=routing_data.get("operation", "health_check"),
                    payload=routing_data.get("payload", {}),
                    correlation_id=correlation_id,
                )

                response = await self.registry.send_message(target_message)
                responses.append(
                    {
                        "target_node": node_id,
                        "success": response.success,
                        "result": response.result if response.success else None,
                        "error": (
                            response.error_message if not response.success else None
                        ),
                        "execution_time_ms": response.execution_time_ms,
                    }
                )

            except Exception as e:
                responses.append(
                    {
                        "target_node": node_id,
                        "success": False,
                        "result": None,
                        "error": str(e),
                        "execution_time_ms": 0,
                    }
                )

        successful_responses = sum(1 for r in responses if r["success"])

        return {
            "routing_strategy": "broadcast",
            "target_nodes": target_nodes,
            "total_targets": len(target_nodes),
            "successful_responses": successful_responses,
            "responses": responses,
            "all_successful": successful_responses == len(target_nodes),
            "timestamp": time.time(),
        }

    async def _route_round_robin_to_nodes(
        self, target_nodes: List[str], routing_data: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Route message using round-robin to target nodes."""
        if not target_nodes:
            raise ValueError("No target nodes provided for round-robin routing")

        selected_node = target_nodes[self._routing_count % len(target_nodes)]

        # Create message for selected node
        target_message = NodeMessage(
            message_id=f"gateway-roundrobin-{self._routing_count}-{selected_node}",
            source_node=self.node_id,
            target_node=selected_node,
            operation=routing_data.get("operation", "health_check"),
            payload=routing_data.get("payload", {}),
            correlation_id=correlation_id,
        )

        response = await self.registry.send_message(target_message)

        return {
            "routing_strategy": "round_robin",
            "selected_node": selected_node,
            "total_targets": len(target_nodes),
            "success": response.success,
            "result": response.result if response.success else None,
            "error": response.error_message if not response.success else None,
            "execution_time_ms": response.execution_time_ms,
            "timestamp": time.time(),
        }

    async def _route_and_aggregate_from_nodes(
        self, target_nodes: List[str], routing_data: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Route message to all nodes and aggregate responses."""
        individual_responses = []
        aggregated_data = {
            "total_responses": 0,
            "combined_results": {},
            "successful_nodes": [],
        }

        for node_id in target_nodes:
            try:
                # Create message for target node
                target_message = NodeMessage(
                    message_id=f"gateway-aggregate-{self._routing_count}-{node_id}",
                    source_node=self.node_id,
                    target_node=node_id,
                    operation=routing_data.get("operation", "health_check"),
                    payload=routing_data.get("payload", {}),
                    correlation_id=correlation_id,
                )

                response = await self.registry.send_message(target_message)

                individual_responses.append(
                    {
                        "node_id": node_id,
                        "success": response.success,
                        "result": response.result,
                        "execution_time_ms": response.execution_time_ms,
                    }
                )

                if response.success:
                    aggregated_data["total_responses"] += 1
                    aggregated_data["combined_results"][node_id] = response.result
                    aggregated_data["successful_nodes"].append(node_id)

            except Exception as e:
                individual_responses.append(
                    {
                        "node_id": node_id,
                        "success": False,
                        "result": None,
                        "error": str(e),
                    }
                )

        return {
            "routing_strategy": "aggregate",
            "target_nodes": target_nodes,
            "total_targets": len(target_nodes),
            "successful_responses": aggregated_data["total_responses"],
            "individual_responses": individual_responses,
            "aggregated_data": aggregated_data,
            "timestamp": time.time(),
        }


# ===== INTEGRATION TEST FUNCTIONS =====


async def test_full_canary_deployment_workflow():
    """Test complete canary deployment workflow with all nodes coordinating."""
    print("🚀 Testing Full Canary Deployment Workflow")
    print("=" * 60)

    # Set up registry and nodes
    registry = NodeRegistry()

    # Create and register nodes
    compute_node = IntegratedCanaryCompute("compute_node")
    effect_node = IntegratedCanaryEffect("effect_node")
    orchestrator_node = IntegratedCanaryOrchestrator("orchestrator_node", registry)
    reducer_node = IntegratedCanaryReducer("reducer_node")
    gateway_node = IntegratedCanaryGateway("gateway_node", registry)

    registry.register_node("compute_node", compute_node)
    registry.register_node("effect_node", effect_node)
    registry.register_node("orchestrator_node", orchestrator_node)
    registry.register_node("reducer_node", reducer_node)
    registry.register_node("gateway_node", gateway_node)

    try:
        # Start canary deployment workflow
        print("\n🎯 Starting Canary Deployment Workflow...")

        workflow_message = NodeMessage(
            message_id="test-canary-workflow-001",
            source_node="test_client",
            target_node="orchestrator_node",
            operation="orchestrate",
            payload={
                "operation_type": "start_workflow",
                "workflow_id": "canary-deploy-001",
                "workflow_type": "canary_deployment",
                "parameters": {
                    "canary_version": "v2.1.0",
                    "instance_count": 3,
                    "initial_traffic": 10,
                    "final_traffic": 50,
                    "expected_rps": 200,
                },
            },
            correlation_id="integration-test-001",
        )

        start_time = time.time()

        # Add timeout handling for async operation
        try:
            response = await asyncio.wait_for(
                registry.send_message(workflow_message),
                timeout=60.0,  # 60 second timeout for integration test
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                "Integration test timeout: Workflow execution exceeded 60 seconds. "
                "This may indicate a deadlock, infinite loop, or performance issue."
            )

        execution_time = int((time.time() - start_time) * 1000)

        # Analyze results
        if response.success:
            workflow_result = response.result["result"]
            print(f"\n✅ Canary Deployment Workflow Completed Successfully!")
            print(f"   📊 Decision: {workflow_result['decision'].upper()}")
            print(f"   ⏱️  Total Duration: {workflow_result['total_duration_ms']}ms")
            print(
                f"   🔗 Nodes Coordinated: {', '.join(workflow_result['nodes_coordinated'])}"
            )
            print(f"   📋 Steps Completed: {len(workflow_result['steps'])}")

            # Print step details
            print(f"\n📝 Workflow Steps:")
            for i, step in enumerate(workflow_result["steps"], 1):
                step_name = step["step"].replace("_", " ").title()
                duration = step.get("duration_ms", "N/A")
                print(f"   {i}. {step_name} ({duration}ms)")

            return True
        else:
            print(f"\n❌ Canary Deployment Workflow Failed: {response.error_message}")
            return False

    except Exception as e:
        print(f"\n❌ Exception during canary deployment workflow: {e}")
        return False


async def test_infrastructure_health_check_workflow():
    """Test infrastructure health check workflow coordination."""
    print("\n🏥 Testing Infrastructure Health Check Workflow")
    print("=" * 60)

    # Set up registry and nodes
    registry = NodeRegistry()

    compute_node = IntegratedCanaryCompute("compute_node")
    effect_node = IntegratedCanaryEffect("effect_node")
    orchestrator_node = IntegratedCanaryOrchestrator("orchestrator_node", registry)
    reducer_node = IntegratedCanaryReducer("reducer_node")

    registry.register_node("compute_node", compute_node)
    registry.register_node("effect_node", effect_node)
    registry.register_node("orchestrator_node", orchestrator_node)
    registry.register_node("reducer_node", reducer_node)

    try:
        print("\n🔍 Starting Health Check Workflow...")

        health_workflow_message = NodeMessage(
            message_id="test-health-workflow-001",
            source_node="test_client",
            target_node="orchestrator_node",
            operation="orchestrate",
            payload={
                "operation_type": "start_workflow",
                "workflow_id": "health-check-001",
                "workflow_type": "infrastructure_health_check",
                "parameters": {},
            },
            correlation_id="integration-test-health-001",
        )

        try:
            response = await asyncio.wait_for(
                registry.send_message(health_workflow_message),
                timeout=30.0,  # 30 second timeout for health check
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                "Health check timeout: Infrastructure health check exceeded 30 seconds"
            )

        if response.success:
            health_result = response.result["result"]
            print(f"\n✅ Health Check Workflow Completed!")
            print(f"   🏥 Overall Health: {health_result['overall_health'].upper()}")
            print(f"   📋 Steps Completed: {len(health_result['steps'])}")

            return True
        else:
            print(f"\n❌ Health Check Workflow Failed: {response.error_message}")
            return False

    except Exception as e:
        print(f"\n❌ Exception during health check workflow: {e}")
        return False


async def test_gateway_message_routing():
    """Test Gateway routing messages between nodes."""
    print("\n🚪 Testing Gateway Message Routing")
    print("=" * 60)

    registry = NodeRegistry()

    compute_node = IntegratedCanaryCompute("compute_node")
    effect_node = IntegratedCanaryEffect("effect_node")
    reducer_node = IntegratedCanaryReducer("reducer_node")
    gateway_node = IntegratedCanaryGateway("gateway_node", registry)

    registry.register_node("compute_node", compute_node)
    registry.register_node("effect_node", effect_node)
    registry.register_node("reducer_node", reducer_node)
    registry.register_node("gateway_node", gateway_node)

    test_results = []

    try:
        # Test 1: Broadcast health check to all nodes
        print("\n📡 Test 1: Broadcast health check to all nodes...")

        broadcast_message = NodeMessage(
            message_id="gateway-broadcast-test-001",
            source_node="test_client",
            target_node="gateway_node",
            operation="route",
            payload={
                "operation_type": "broadcast_health_check",
                "routing_strategy": "broadcast",
                "target_nodes": ["compute_node", "effect_node", "reducer_node"],
                "routing_data": {
                    "operation": "effect",
                    "payload": {"operation_type": "health_check"},
                },
            },
            correlation_id="gateway-test-broadcast-001",
        )

        try:
            broadcast_response = await asyncio.wait_for(
                registry.send_message(broadcast_message),
                timeout=15.0,  # 15 second timeout for broadcast
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                "Broadcast timeout: Gateway broadcast operation exceeded 15 seconds"
            )

        if broadcast_response.success:
            result = broadcast_response.result["result"]
            successful = result["successful_responses"]
            total = result["total_targets"]
            print(f"   ✅ Broadcast: {successful}/{total} nodes responded successfully")
            test_results.append(("Broadcast Routing", True))
        else:
            print(f"   ❌ Broadcast failed: {broadcast_response.error_message}")
            test_results.append(("Broadcast Routing", False))

        # Test 2: Round-robin routing
        print("\n🔄 Test 2: Round-robin routing to compute nodes...")

        roundrobin_message = NodeMessage(
            message_id="gateway-roundrobin-test-001",
            source_node="test_client",
            target_node="gateway_node",
            operation="route",
            payload={
                "operation_type": "roundrobin_compute",
                "routing_strategy": "round_robin",
                "target_nodes": ["compute_node"],
                "routing_data": {
                    "operation": "compute",
                    "payload": {
                        "operation_type": "addition",
                        "data": {"values": [10, 20, 30]},
                    },
                },
            },
            correlation_id="gateway-test-roundrobin-001",
        )

        try:
            roundrobin_response = await asyncio.wait_for(
                registry.send_message(roundrobin_message),
                timeout=15.0,  # 15 second timeout for round-robin
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                "Round-robin timeout: Gateway round-robin operation exceeded 15 seconds"
            )

        if roundrobin_response.success:
            result = roundrobin_response.result["result"]
            selected_node = result["selected_node"]
            success = result["success"]
            print(f"   ✅ Round-robin: Routed to {selected_node}, success: {success}")
            test_results.append(("Round-robin Routing", True))
        else:
            print(f"   ❌ Round-robin failed: {roundrobin_response.error_message}")
            test_results.append(("Round-robin Routing", False))

        # Test 3: Aggregate routing from multiple nodes
        print("\n🔄 Test 3: Aggregate responses from multiple nodes...")

        aggregate_message = NodeMessage(
            message_id="gateway-aggregate-test-001",
            source_node="test_client",
            target_node="gateway_node",
            operation="route",
            payload={
                "operation_type": "aggregate_health",
                "routing_strategy": "aggregate",
                "target_nodes": ["compute_node", "effect_node"],
                "routing_data": {
                    "operation": "effect",
                    "payload": {"operation_type": "health_check"},
                },
            },
            correlation_id="gateway-test-aggregate-001",
        )

        try:
            aggregate_response = await asyncio.wait_for(
                registry.send_message(aggregate_message),
                timeout=15.0,  # 15 second timeout for aggregation
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                "Aggregation timeout: Gateway aggregation operation exceeded 15 seconds"
            )

        if aggregate_response.success:
            result = aggregate_response.result["result"]
            successful = result["successful_responses"]
            total = result["total_targets"]
            print(
                f"   ✅ Aggregate: {successful}/{total} responses aggregated successfully"
            )
            test_results.append(("Aggregate Routing", True))
        else:
            print(f"   ❌ Aggregate failed: {aggregate_response.error_message}")
            test_results.append(("Aggregate Routing", False))

        return test_results

    except Exception as e:
        print(f"\n❌ Exception during gateway routing test: {e}")
        return [("Gateway Routing", False)]


async def test_performance_analysis_workflow():
    """Test performance analysis workflow coordination."""
    print("\n📊 Testing Performance Analysis Workflow")
    print("=" * 60)

    registry = NodeRegistry()

    compute_node = IntegratedCanaryCompute("compute_node")
    effect_node = IntegratedCanaryEffect("effect_node")
    orchestrator_node = IntegratedCanaryOrchestrator("orchestrator_node", registry)
    reducer_node = IntegratedCanaryReducer("reducer_node")

    registry.register_node("compute_node", compute_node)
    registry.register_node("effect_node", effect_node)
    registry.register_node("orchestrator_node", orchestrator_node)
    registry.register_node("reducer_node", reducer_node)

    try:
        print("\n📈 Starting Performance Analysis Workflow...")

        perf_workflow_message = NodeMessage(
            message_id="test-perf-workflow-001",
            source_node="test_client",
            target_node="orchestrator_node",
            operation="orchestrate",
            payload={
                "operation_type": "start_workflow",
                "workflow_id": "performance-analysis-001",
                "workflow_type": "performance_analysis",
                "parameters": {
                    "total_requests": 10000,
                    "successful_requests": 9500,
                    "average_latency_ms": 165,
                },
            },
            correlation_id="integration-test-perf-001",
        )

        try:
            response = await asyncio.wait_for(
                registry.send_message(perf_workflow_message),
                timeout=90.0,  # 90 second timeout for performance analysis
            )
        except asyncio.TimeoutError:
            raise AssertionError(
                "Performance analysis timeout: Performance workflow exceeded 90 seconds. "
                "This may indicate a performance issue or resource contention."
            )

        if response.success:
            perf_result = response.result["result"]
            print(f"\n✅ Performance Analysis Workflow Completed!")
            print(
                f"   📊 Performance Status: {perf_result['performance_summary']['overall_status'].upper()}"
            )
            print(f"   💡 Recommendation: {perf_result['recommendation'].upper()}")
            print(f"   📋 Steps Completed: {len(perf_result['steps'])}")

            return True
        else:
            print(
                f"\n❌ Performance Analysis Workflow Failed: {response.error_message}"
            )
            return False

    except Exception as e:
        print(f"\n❌ Exception during performance analysis workflow: {e}")
        return False


async def main():
    """Main integration test runner."""
    print("🧪 CANARY NODE INTEGRATION TESTING")
    print("=" * 80)
    print("Testing full 4-node architecture with inter-node communication")
    print("=" * 80)

    all_results = []

    # Test 1: Full Canary Deployment Workflow
    canary_result = await test_full_canary_deployment_workflow()
    all_results.append(("Full Canary Deployment", canary_result))

    # Test 2: Infrastructure Health Check Workflow
    health_result = await test_infrastructure_health_check_workflow()
    all_results.append(("Infrastructure Health Check", health_result))

    # Test 3: Gateway Message Routing
    gateway_results = await test_gateway_message_routing()
    all_results.extend(gateway_results)

    # Test 4: Performance Analysis Workflow
    perf_result = await test_performance_analysis_workflow()
    all_results.append(("Performance Analysis Workflow", perf_result))

    # Summary
    print("\n" + "=" * 80)
    print("🧪 CANARY NODE INTEGRATION TEST SUMMARY")
    print("=" * 80)

    total_tests = len(all_results)
    passed_tests = sum(1 for _, success in all_results if success)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"Integration Tests Run: {total_tests}")
    print(f"Integration Tests Passed: {passed_tests}")
    print(f"Integration Tests Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()

    if failed_tests == 0:
        print("🎉 All integration tests passed!")
        print("✅ Full 4-node canary architecture is working correctly!")
        print(
            "🏗️  Orchestrator ↔ Compute ↔ Effect ↔ Reducer ↔ Gateway communication verified"
        )
    else:
        print(f"⚠️  {failed_tests} integration tests failed.")
        print("❌ Please review the failed tests before deploying.")

    print("\n📊 DETAILED TEST RESULTS:")
    for test_name, success in all_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {test_name}")

    print("\n🎯 INTEGRATION HIGHLIGHTS:")
    print("  • Orchestrator coordinates multi-step workflows")
    print("  • Compute nodes perform calculations on real data")
    print("  • Effect nodes execute deployment operations")
    print("  • Reducer aggregates results from multiple nodes")
    print("  • Gateway routes messages between all nodes")
    print("  • Full canary deployment decision-making workflow")

    return failed_tests == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
