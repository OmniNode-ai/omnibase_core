#!/usr/bin/env python3
"""
Test script to verify all canary nodes function properly.

Tests all 5 canary node implementations:
- NodeCanaryCompute (COMPUTE)
- NodeCanaryEffect (EFFECT)
- NodeCanaryOrchestrator (ORCHESTRATOR)
- NodeCanaryReducer (REDUCER)
- NodeCanaryGateway (EFFECT/Gateway)
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import all canary nodes
from omnibase_core.nodes.canary.canary_compute.v1_0_0.tool import (
    ModelCanaryComputeInput,
    NodeCanaryCompute,
)
from omnibase_core.nodes.canary.canary_effect.v1_0_0.tool import (
    ModelCanaryEffectInput,
    NodeCanaryEffect,
)
from omnibase_core.nodes.canary.canary_gateway.v1_0_0.tool import (
    ModelGroupGatewayInput,
    NodeCanaryGateway,
)
from omnibase_core.nodes.canary.canary_orchestrator.v1_0_0.tool import (
    ModelCanaryOrchestratorInput,
    NodeCanaryOrchestrator,
)
from omnibase_core.nodes.canary.canary_reducer.v1_0_0.tool import (
    ModelCanaryReducerInput,
    NodeCanaryReducer,
)


class CanaryNodeTester:
    """Test runner for all canary nodes."""

    def __init__(self):
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "node_results": {},
        }

    async def run_all_tests(self):
        """Run tests for all canary nodes."""
        print("🧪 Testing Canary Nodes Functionality")
        print("=" * 50)

        # Test each node type
        await self.test_compute_node()
        await self.test_effect_node()
        await self.test_orchestrator_node()
        await self.test_reducer_node()
        await self.test_gateway_node()

        # Print summary
        self.print_summary()

    async def test_compute_node(self):
        """Test NodeCanaryCompute functionality."""
        print("\n🧮 Testing COMPUTE Node (NodeCanaryCompute)")
        print("-" * 40)

        try:
            node = NodeCanaryCompute()
            node_results = []

            # Test 1: Addition computation
            input_data = ModelCanaryComputeInput(
                operation_type="add",
                data={"numbers": [1, 2, 3, 4, 5]},
                correlation_id="test-compute-1",
            )

            result = await node.process_computation(input_data)
            success = result.success and result.result.get("sum") == 15
            self.record_test("Compute - Addition", success, result)
            node_results.append(("Addition", success, result.result))

            # Test 2: Multiplication computation
            input_data = ModelCanaryComputeInput(
                operation_type="multiply",
                data={"numbers": [2, 3, 4]},
                correlation_id="test-compute-2",
            )

            result = await node.process_computation(input_data)
            success = result.success and result.result.get("product") == 24
            self.record_test("Compute - Multiplication", success, result)
            node_results.append(("Multiplication", success, result.result))

            # Test 3: Aggregation computation
            input_data = ModelCanaryComputeInput(
                operation_type="aggregate",
                data={"items": ["hello", 123, True, 45.6]},
                correlation_id="test-compute-3",
            )

            result = await node.process_computation(input_data)
            success = result.success and "aggregated" in result.result
            self.record_test("Compute - Aggregation", success, result)
            node_results.append(("Aggregation", success, result.result))

            # Test 4: Health check
            health = await node.health_check()
            success = health.get("status") == "healthy"
            self.record_test("Compute - Health Check", success, health)
            node_results.append(("Health Check", success, health))

            self.results["node_results"]["compute"] = node_results
            print(f"✅ COMPUTE node tests completed")

        except Exception as e:
            print(f"❌ COMPUTE node test failed: {e}")
            traceback.print_exc()
            self.record_test("Compute - Exception", False, {"error": str(e)})

    async def test_effect_node(self):
        """Test NodeCanaryEffect functionality."""
        print("\n🎯 Testing EFFECT Node (NodeCanaryEffect)")
        print("-" * 40)

        try:
            node = NodeCanaryEffect()
            node_results = []

            # Test 1: Health check operation
            input_data = ModelCanaryEffectInput(
                operation_type="health_check",
                parameters={},
                correlation_id="test-effect-1",
            )

            result = await node.perform_effect(input_data)
            success = result.success and "status" in result.operation_result
            self.record_test("Effect - Health Check", success, result)
            node_results.append(("Health Check", success, result.operation_result))

            # Test 2: API call simulation
            input_data = ModelCanaryEffectInput(
                operation_type="external_api_call",
                parameters={"endpoint": "/api/users", "method": "GET"},
                correlation_id="test-effect-2",
            )

            result = await node.perform_effect(input_data)
            success = (
                result.success and result.operation_result.get("status_code") == 200
            )
            self.record_test("Effect - API Call", success, result)
            node_results.append(("API Call", success, result.operation_result))

            # Test 3: File system operation
            input_data = ModelCanaryEffectInput(
                operation_type="file_system_operation",
                parameters={
                    "operation": "write",
                    "file_path": "/tmp/test.txt",
                    "content": "test data",
                },
                correlation_id="test-effect-3",
            )

            result = await node.perform_effect(input_data)
            success = (
                result.success and result.operation_result.get("status") == "success"
            )
            self.record_test("Effect - File System", success, result)
            node_results.append(("File System", success, result.operation_result))

            # Test 4: Node health check
            health = await node.health_check()
            success = health.get("status") == "healthy"
            self.record_test("Effect - Health Check", success, health)
            node_results.append(("Node Health", success, health))

            self.results["node_results"]["effect"] = node_results
            print(f"✅ EFFECT node tests completed")

        except Exception as e:
            print(f"❌ EFFECT node test failed: {e}")
            traceback.print_exc()
            self.record_test("Effect - Exception", False, {"error": str(e)})

    async def test_orchestrator_node(self):
        """Test NodeCanaryOrchestrator functionality."""
        print("\n🎼 Testing ORCHESTRATOR Node (NodeCanaryOrchestrator)")
        print("-" * 40)

        try:
            node = NodeCanaryOrchestrator()
            node_results = []

            # Test 1: Infrastructure startup workflow
            input_data = ModelCanaryOrchestratorInput(
                operation_type="infrastructure_startup",
                workflow_id="test-startup-1",
                correlation_id="test-orch-1",
            )

            result = await node.start_workflow(input_data)
            success = result.status == "completed"
            self.record_test("Orchestrator - Infrastructure Startup", success, result)
            node_results.append(
                ("Infrastructure Startup", success, result.workflow_result)
            )

            # Test 2: Canary deployment workflow
            input_data = ModelCanaryOrchestratorInput(
                operation_type="canary_deployment",
                workflow_id="test-canary-1",
                parameters={"service": "test-service", "traffic_percentage": 20},
                correlation_id="test-orch-2",
            )

            result = await node.start_workflow(input_data)
            success = (
                result.status == "completed" and "promotion" in result.workflow_result
            )
            self.record_test("Orchestrator - Canary Deployment", success, result)
            node_results.append(("Canary Deployment", success, result.workflow_result))

            # Test 3: List workflows
            workflows = await node.list_workflows()
            success = (
                "active_workflows" in workflows and workflows["total_executed"] >= 2
            )
            self.record_test("Orchestrator - List Workflows", success, workflows)
            node_results.append(("List Workflows", success, workflows))

            # Test 4: Health check
            health = await node.health_check()
            success = health.get("status") == "healthy"
            self.record_test("Orchestrator - Health Check", success, health)
            node_results.append(("Health Check", success, health))

            self.results["node_results"]["orchestrator"] = node_results
            print(f"✅ ORCHESTRATOR node tests completed")

        except Exception as e:
            print(f"❌ ORCHESTRATOR node test failed: {e}")
            traceback.print_exc()
            self.record_test("Orchestrator - Exception", False, {"error": str(e)})

    async def test_reducer_node(self):
        """Test NodeCanaryReducer functionality."""
        print("\n🔄 Testing REDUCER Node (NodeCanaryReducer)")
        print("-" * 40)

        try:
            node = NodeCanaryReducer()
            node_results = []

            # Test 1: Health check aggregation
            mock_results = [
                {
                    "adapter_name": "consul",
                    "health_status": "healthy",
                    "health_score": 0.95,
                },
                {
                    "adapter_name": "vault",
                    "health_status": "healthy",
                    "health_score": 0.90,
                },
                {
                    "adapter_name": "kafka",
                    "health_status": "degraded",
                    "health_score": 0.75,
                },
            ]

            input_data = ModelCanaryReducerInput(
                adapter_results=mock_results, operation_type="health_check"
            )

            result = await node.aggregate_results(input_data)
            success = (
                result.status == "success"
                and "overall_health" in result.aggregated_result
            )
            self.record_test("Reducer - Health Aggregation", success, result)
            node_results.append(
                ("Health Aggregation", success, result.aggregated_result)
            )

            # Test 2: Bootstrap aggregation
            bootstrap_results = [
                {
                    "adapter_name": "consul",
                    "status": "ready",
                    "services": [{"name": "consul", "status": "ready"}],
                },
                {
                    "adapter_name": "vault",
                    "status": "ready",
                    "services": [{"name": "vault", "status": "ready"}],
                },
            ]

            input_data = ModelCanaryReducerInput(
                adapter_results=bootstrap_results, operation_type="bootstrap"
            )

            result = await node.aggregate_results(input_data)
            success = (
                result.status == "success"
                and "bootstrap_status" in result.aggregated_result
            )
            self.record_test("Reducer - Bootstrap Aggregation", success, result)
            node_results.append(
                ("Bootstrap Aggregation", success, result.aggregated_result)
            )

            # Test 3: List loaded adapters
            adapters = await node.list_loaded_adapters()
            success = (
                "loaded_adapters" in adapters and len(adapters["loaded_adapters"]) > 0
            )
            self.record_test("Reducer - List Adapters", success, adapters)
            node_results.append(("List Adapters", success, adapters))

            # Test 4: Health check
            health = await node.health_check()
            success = health.get("status") == "healthy"
            self.record_test("Reducer - Health Check", success, health)
            node_results.append(("Health Check", success, health))

            self.results["node_results"]["reducer"] = node_results
            print(f"✅ REDUCER node tests completed")

        except Exception as e:
            print(f"❌ REDUCER node test failed: {e}")
            traceback.print_exc()
            self.record_test("Reducer - Exception", False, {"error": str(e)})

    async def test_gateway_node(self):
        """Test NodeCanaryGateway functionality."""
        print("\n🚪 Testing GATEWAY Node (NodeCanaryGateway)")
        print("-" * 40)

        try:
            node = NodeCanaryGateway()
            node_results = []

            # Test 1: Route message
            input_data = ModelGroupGatewayInput(
                operation_type="route",
                target_tools=["compute-node-1", "compute-node-2"],
                message_data={"action": "process", "data": [1, 2, 3]},
                correlation_id="test-gateway-1",
            )

            result = await node.route_message(input_data)
            success = (
                result.status == "success"
                and "selected_target" in result.aggregated_response
            )
            self.record_test("Gateway - Route Message", success, result)
            node_results.append(("Route Message", success, result.aggregated_response))

            # Test 2: Broadcast message
            input_data = ModelGroupGatewayInput(
                operation_type="broadcast",
                target_tools=["effect-node-1", "effect-node-2", "effect-node-3"],
                message_data={"broadcast": "test message"},
                correlation_id="test-gateway-2",
            )

            result = await node.route_message(input_data)
            success = (
                result.status == "success"
                and "broadcast_results" in result.aggregated_response
            )
            self.record_test("Gateway - Broadcast Message", success, result)
            node_results.append(
                ("Broadcast Message", success, result.aggregated_response)
            )

            # Test 3: Aggregate from targets
            input_data = ModelGroupGatewayInput(
                operation_type="aggregate",
                target_tools=["reducer-node-1", "reducer-node-2"],
                message_data={"items": ["data1", "data2", "data3"]},
                correlation_id="test-gateway-3",
            )

            result = await node.route_message(input_data)
            success = (
                result.status == "success"
                and "aggregation" in result.aggregated_response
            )
            self.record_test("Gateway - Aggregate Messages", success, result)
            node_results.append(
                ("Aggregate Messages", success, result.aggregated_response)
            )

            # Test 4: Get routing metrics
            metrics = await node.get_routing_metrics()
            success = "total_routes" in metrics and metrics["total_routes"] >= 3
            self.record_test("Gateway - Routing Metrics", success, metrics)
            node_results.append(("Routing Metrics", success, metrics))

            # Test 5: Health check
            health = await node.health_check()
            success = health.get("status") == "healthy"
            self.record_test("Gateway - Health Check", success, health)
            node_results.append(("Health Check", success, health))

            self.results["node_results"]["gateway"] = node_results
            print(f"✅ GATEWAY node tests completed")

        except Exception as e:
            print(f"❌ GATEWAY node test failed: {e}")
            traceback.print_exc()
            self.record_test("Gateway - Exception", False, {"error": str(e)})

    def record_test(self, test_name: str, passed: bool, result_data):
        """Record test result."""
        self.results["tests_run"] += 1
        if passed:
            self.results["tests_passed"] += 1
            print(f"  ✅ {test_name}")
        else:
            self.results["tests_failed"] += 1
            print(f"  ❌ {test_name}")
            if hasattr(result_data, "error_message") and result_data.error_message:
                print(f"     Error: {result_data.error_message}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("🧪 CANARY NODES TEST SUMMARY")
        print("=" * 50)

        print(f"Tests Run: {self.results['tests_run']}")
        print(f"Tests Passed: {self.results['tests_passed']}")
        print(f"Tests Failed: {self.results['tests_failed']}")

        success_rate = (self.results["tests_passed"] / self.results["tests_run"]) * 100
        print(f"Success Rate: {success_rate:.1f}%")

        if self.results["tests_failed"] == 0:
            print("\n🎉 ALL CANARY NODES ARE FUNCTIONING CORRECTLY!")
            print("✅ The canary deployment system is ready for use.")
        else:
            print(f"\n⚠️  {self.results['tests_failed']} tests failed.")
            print("❌ Please review the failed tests before deploying.")

        # Print node-by-node summary
        print("\n📊 NODE-BY-NODE RESULTS:")
        for node_name, node_results in self.results["node_results"].items():
            passed_tests = sum(1 for _, success, _ in node_results if success)
            total_tests = len(node_results)
            print(f"  {node_name.upper()}: {passed_tests}/{total_tests} tests passed")


async def main():
    """Run all canary node tests."""
    tester = CanaryNodeTester()
    await tester.run_all_tests()

    # Return exit code based on test results
    return 0 if tester.results["tests_failed"] == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        traceback.print_exc()
        sys.exit(1)
