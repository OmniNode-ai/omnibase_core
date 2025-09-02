#!/usr/bin/env python3
"""
Simple Real Service Test - No Canary Nodes, Just Direct Service Validation

This directly tests the real services without the canary node framework
to prove the services are actually running and accessible.
"""

import uuid
from datetime import datetime

import consul
import psycopg2


def test_real_consul():
    """Test real Consul service directly."""
    print("🔍 Testing Real Consul Service...")

    try:
        # Connect to real Consul
        client = consul.Consul(host="localhost", port=8500)

        # Get node info
        node_info = client.agent.self()
        node_name = node_info["Config"]["NodeName"]
        datacenter = node_info["Config"]["Datacenter"]

        print(f"   ✅ Consul connected: {node_name} (DC: {datacenter})")

        # Test service registration
        service_id = f"test-{uuid.uuid4().hex[:8]}"
        client.agent.service.register(
            service_id=service_id,
            name="real_test_service",
            address="127.0.0.1",
            port=8888,
            tags=["test"],
        )
        print(f"   ✅ Service registered: {service_id}")

        # Test KV operations
        test_key = f"test/{service_id}/data"
        test_value = f"Real test at {datetime.now().isoformat()}"
        client.kv.put(test_key, test_value)

        # Retrieve and verify
        _, data = client.kv.get(test_key)
        stored_value = data["Value"].decode()

        if stored_value == test_value:
            print(f"   ✅ KV operations working: {test_key}")
            return True
        else:
            print(f"   ❌ KV verification failed")
            return False

    except Exception as e:
        print(f"   ❌ Consul test failed: {e}")
        return False


def test_real_postgresql():
    """Test real PostgreSQL service directly."""
    print("🗄️ Testing Real PostgreSQL Service...")

    try:
        # Connect to real PostgreSQL
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="canary_test",
            user="canary_user",
            password="canary_pass",
        )

        cursor = conn.cursor()

        # Get database info
        cursor.execute("SELECT current_database(), current_user, version();")
        db_info = cursor.fetchone()

        print(f"   ✅ PostgreSQL connected: {db_info[0]} as {db_info[1]}")
        print(f"   ✅ Version: {db_info[2][:50]}...")

        # Test table operations
        table_name = f"real_test_{uuid.uuid4().hex[:8]}"

        cursor.execute(
            f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                test_data VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Insert test data
        test_data = f"Real service test at {datetime.now().isoformat()}"
        cursor.execute(
            f"""
            INSERT INTO {table_name} (test_data)
            VALUES (%s) RETURNING id
        """,
            (test_data,),
        )

        inserted_id = cursor.fetchone()[0]
        conn.commit()

        print(
            f"   ✅ Table created and data inserted: {table_name} (ID: {inserted_id})"
        )

        # Verify data
        cursor.execute(
            f"""
            SELECT test_data FROM {table_name} WHERE id = %s
        """,
            (inserted_id,),
        )

        retrieved_data = cursor.fetchone()[0]

        if retrieved_data == test_data:
            print(f"   ✅ Data verification successful")
            conn.close()
            return True
        else:
            print(f"   ❌ Data verification failed")
            conn.close()
            return False

    except Exception as e:
        print(f"   ❌ PostgreSQL test failed: {e}")
        return False


def main():
    """Run simple real service validation."""
    print("🚀 REAL SERVICE VALIDATION (No Canary Framework)")
    print("=" * 60)

    # Test Consul
    consul_ok = test_real_consul()

    # Test PostgreSQL
    postgres_ok = test_real_postgresql()

    # Results
    print("\n" + "=" * 60)
    print("📊 REAL SERVICE TEST RESULTS")
    print("=" * 60)

    services_tested = 0
    services_working = 0

    if consul_ok:
        print("   Consul:     ✅ WORKING")
        services_working += 1
    else:
        print("   Consul:     ❌ FAILED")
    services_tested += 1

    if postgres_ok:
        print("   PostgreSQL: ✅ WORKING")
        services_working += 1
    else:
        print("   PostgreSQL: ❌ FAILED")
    services_tested += 1

    print(f"\n🎯 Result: {services_working}/{services_tested} real services working")

    if services_working == services_tested:
        print("🎉 ALL REAL SERVICES ARE WORKING!")
        print("   The containers ARE running and accessible.")
    elif services_working > 0:
        print("⚠️  SOME REAL SERVICES WORKING")
        print("   At least some containers are running.")
    else:
        print("❌ NO REAL SERVICES WORKING")
        print("   No containers appear to be running or accessible.")


if __name__ == "__main__":
    main()
