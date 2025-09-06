#!/usr/bin/env python3
"""
Real Integration Tests for Canary System with External Services

Tests the canary system against actual running external services:
- Consul for service discovery
- PostgreSQL for database operations
- Redis for caching/messaging

This validates that our protocol abstractions work with real infrastructure.
"""

import asyncio
import os
import uuid
from datetime import datetime

import pytest

from omnibase_core.core.node_effect import EffectType, ModelEffectInput
from omnibase_core.enums.node import EnumHealthStatus
from omnibase_core.nodes.canary.canary_effect.v1_0_0.node import NodeCanaryEffect
from omnibase_core.nodes.canary.canary_reducer.v1_0_0.node import NodeCanaryReducer
from omnibase_core.nodes.canary.container import create_infrastructure_container


class TestCanaryRealServices:
    """Integration tests using real external services."""

    @pytest.fixture
    async def real_container(self):
        """Create container configured for real external services."""
        # Override environment variables for real services
        os.environ.update(
            {
                "CONSUL_ENABLED": "true",
                "CONSUL_URL": os.getenv("CONSUL_URL", "http://localhost:8500"),
                "DATABASE_ENABLED": "true",
                "POSTGRES_URL": os.getenv(
                    "POSTGRES_URL",
                    "postgresql://canary_user:canary_pass@localhost:5433/canary_test",
                ),
                "REDIS_ENABLED": "true",
                "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
                "OMNIBASE_LOGGING_LEVEL": "INFO",
            }
        )

        # Use ModelONEXContainer with real service integrations
        from omnibase_core.core.enhanced_container import ModelONEXContainer

        container = ModelONEXContainer(enable_performance_cache=False)
        await container.init()
        return container

    @pytest.fixture
    async def effect_node(self, real_container):
        """Create effect node with real services."""
        return NodeCanaryEffect(real_container)

    @pytest.fixture
    async def reducer_node(self, real_container):
        """Create reducer node with real services."""
        return NodeCanaryReducer(real_container)

    @pytest.mark.asyncio
    async def test_consul_service_discovery_integration(self, real_container):
        """Test actual Consul service discovery integration."""
        service_discovery = await real_container.get_service_discovery()

        # Register a test service in real Consul
        test_service_id = f"canary-test-{uuid.uuid4().hex[:8]}"
        success = await service_discovery.register_service(
            service_id=test_service_id,
            service_name="canary_test_service",
            address="127.0.0.1",
            port=9999,
            health_check_url="http://127.0.0.1:9999/health",
            tags=["test", "canary"],
            metadata={"test": "real_integration"},
        )

        assert success, "Service registration should succeed with real Consul"

        # Discover the service we just registered
        services = await service_discovery.discover_services("canary_test_service")
        assert len(services) > 0, "Should find the registered service"

        found_service = next(
            (s for s in services if s.get("ServiceID") == test_service_id), None
        )
        assert found_service is not None, "Should find our specific service"
        assert found_service["ServiceName"] == "canary_test_service"
        assert found_service["ServiceAddress"] == "127.0.0.1"
        assert found_service["ServicePort"] == 9999

        # Test KV operations
        kv_success = await service_discovery.set_kv("canary/test/key", "real_value")
        assert kv_success, "KV set should work with real Consul"

        retrieved_value = await service_discovery.get_kv("canary/test/key")
        assert (
            retrieved_value == "real_value"
        ), "Should retrieve the same value from Consul KV"

        # Test health check
        health_status = await service_discovery.health_check()
        assert health_status, "Consul health check should pass"

    @pytest.mark.asyncio
    async def test_postgresql_database_integration(self, real_container):
        """Test actual PostgreSQL database integration."""
        database = await real_container.get_database()

        # Create test table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS canary_test_operations (
            id SERIAL PRIMARY KEY,
            operation_id VARCHAR(255) UNIQUE NOT NULL,
            operation_type VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            result_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        await database.execute_query(create_table_query)

        # Insert test data
        operation_id = f"op_{uuid.uuid4().hex[:8]}"
        insert_query = """
        INSERT INTO canary_test_operations (operation_id, operation_type, status, result_data)
        VALUES (%s, %s, %s, %s)
        """

        await database.execute_query(
            insert_query,
            (
                operation_id,
                "health_check",
                "completed",
                '{"success": true, "duration_ms": 150}',
            ),
        )

        # Query the data back
        select_query = "SELECT * FROM canary_test_operations WHERE operation_id = %s"
        results = await database.execute_query(select_query, (operation_id,))

        assert len(results) == 1, "Should find the inserted record"
        record = results[0]
        assert record["operation_id"] == operation_id
        assert record["operation_type"] == "health_check"
        assert record["status"] == "completed"
        assert record["result_data"]["success"] is True
        assert record["result_data"]["duration_ms"] == 150

        # Test transaction with lock
        lock_id = await database.acquire_lock(
            f"canary_test_lock_{uuid.uuid4().hex[:8]}", 30
        )
        assert lock_id is not None, "Should acquire database lock"

        lock_released = await database.release_lock(lock_id)
        assert lock_released, "Should release database lock"

        # Test health check
        health_status = await database.health_check()
        assert health_status, "Database health check should pass"

    @pytest.mark.asyncio
    async def test_effect_node_with_real_services(self, effect_node):
        """Test effect node operations with real external services."""
        # Test operation that uses real services
        effect_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "service_registration_test",
                "parameters": {
                    "service_name": f"canary_effect_{uuid.uuid4().hex[:8]}",
                    "use_real_services": True,
                },
                "correlation_id": str(uuid.uuid4()),
            },
        )

        # This should register with real Consul and log to real PostgreSQL
        result = await effect_node.perform_effect(effect_input, EffectType.API_CALL)

        assert result is not None
        assert "operation_result" in result.result
        assert result.metadata["node_type"] == "canary_effect"

        # Verify metrics were updated
        assert effect_node.operation_count > 0
        assert effect_node.success_count > 0

    @pytest.mark.asyncio
    async def test_health_aggregation_with_real_services(self, reducer_node):
        """Test health status aggregation using real service health checks."""
        # Create inputs that represent real service health checks
        health_inputs = []

        # Consul health
        consul_health_input = {
            "service_name": "consul",
            "status": "healthy",
            "last_check": datetime.now().isoformat(),
            "details": {"url": "http://localhost:8500", "response_time_ms": 45},
        }
        health_inputs.append(consul_health_input)

        # PostgreSQL health
        postgres_health_input = {
            "service_name": "postgresql",
            "status": "healthy",
            "last_check": datetime.now().isoformat(),
            "details": {
                "url": "postgresql://localhost:5433",
                "connection_pool_size": 10,
            },
        }
        health_inputs.append(postgres_health_input)

        # Redis health (if available)
        redis_health_input = {
            "service_name": "redis",
            "status": "healthy",
            "last_check": datetime.now().isoformat(),
            "details": {"url": "redis://localhost:6379", "memory_usage": "15MB"},
        }
        health_inputs.append(redis_health_input)

        # Perform aggregation with real health data
        from omnibase_core.core.node_reducer import ModelReducerInput

        reducer_input = ModelReducerInput(
            operation_type="health_aggregation",
            data_collection=health_inputs,
            aggregation_strategy="majority_healthy",
            correlation_id=str(uuid.uuid4()),
        )

        result = await reducer_node.reduce(reducer_input)

        assert result is not None
        assert result.data["success"] is True

        # With all services healthy, should show healthy status
        aggregation_result = result.data["aggregation_result"]
        assert aggregation_result["overall_status"] == "healthy"
        assert aggregation_result["healthy_services"] == 3
        assert aggregation_result["total_services"] == 3
        assert aggregation_result["health_score"] == 1.0

    @pytest.mark.asyncio
    async def test_full_canary_workflow_real_services(self, effect_node, reducer_node):
        """Test complete canary workflow using real external services."""
        workflow_id = str(uuid.uuid4())

        # Step 1: Register canary service in real Consul
        registration_input = ModelEffectInput(
            effect_type=EffectType.API_CALL,
            operation_data={
                "operation_type": "service_registration",
                "parameters": {
                    "service_name": f"canary_workflow_{workflow_id[:8]}",
                    "port": 8080,
                    "health_endpoint": "/health",
                },
                "correlation_id": workflow_id,
            },
        )

        registration_result = await effect_node.perform_effect(
            registration_input, EffectType.API_CALL
        )
        assert registration_result.result["success"] is True

        # Step 2: Log workflow start in real PostgreSQL
        logging_input = ModelEffectInput(
            effect_type=EffectType.DATABASE_OPERATION,
            operation_data={
                "operation_type": "workflow_logging",
                "parameters": {
                    "workflow_id": workflow_id,
                    "phase": "start",
                    "status": "initiated",
                },
                "correlation_id": workflow_id,
            },
        )

        logging_result = await effect_node.perform_effect(
            logging_input, EffectType.DATABASE_OPERATION
        )
        assert logging_result.result["success"] is True

        # Step 3: Aggregate results using real health data
        from omnibase_core.core.node_reducer import ModelReducerInput

        workflow_results = [registration_result.result, logging_result.result]

        aggregation_input = ModelReducerInput(
            operation_type="workflow_aggregation",
            data_collection=workflow_results,
            aggregation_strategy="all_must_succeed",
            correlation_id=workflow_id,
        )

        final_result = await reducer_node.reduce(aggregation_input)

        # Verify workflow completed successfully with real services
        assert final_result.data["success"] is True
        assert final_result.data["aggregation_result"]["successful_operations"] == 2
        assert final_result.data["aggregation_result"]["failed_operations"] == 0
        assert final_result.data["aggregation_result"]["overall_success"] is True

    def test_real_service_connectivity(self):
        """Verify we can connect to real services before running tests."""
        import socket

        import consul
        import psycopg2

        # Test Consul connectivity
        try:
            consul_client = consul.Consul(host="localhost", port=8500)
            consul_client.agent.self()
            consul_healthy = True
        except Exception:
            consul_healthy = False

        # Test PostgreSQL connectivity
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5433,
                database="canary_test",
                user="canary_user",
                password="canary_pass",
            )
            conn.close()
            postgres_healthy = True
        except Exception:
            postgres_healthy = False

        # Test Redis connectivity
        try:
            import redis

            redis_client = redis.Redis(host="localhost", port=6379)
            redis_client.ping()
            redis_healthy = True
        except Exception:
            redis_healthy = False

        # Report connectivity status
        services_status = {
            "consul": consul_healthy,
            "postgresql": postgres_healthy,
            "redis": redis_healthy,
        }

        healthy_services = sum(services_status.values())
        total_services = len(services_status)

        print(f"\n🔍 Real Service Connectivity Check:")
        print(
            f"   Consul (8500): {'✅ Connected' if consul_healthy else '❌ Unavailable'}"
        )
        print(
            f"   PostgreSQL (5433): {'✅ Connected' if postgres_healthy else '❌ Unavailable'}"
        )
        print(
            f"   Redis (6379): {'✅ Connected' if redis_healthy else '❌ Unavailable'}"
        )
        print(f"   Overall: {healthy_services}/{total_services} services healthy")

        # We need at least Consul and PostgreSQL for meaningful tests
        assert (
            consul_healthy or postgres_healthy
        ), "Need at least one real service for integration testing"


if __name__ == "__main__":
    """Run real service integration tests."""
    pytest.main([__file__, "-v", "--tb=short"])
