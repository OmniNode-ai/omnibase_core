#!/usr/bin/env python3
"""
Standalone test script to validate service discovery implementations.

This script tests the actual implementations without pytest dependencies
to verify the strong typing changes work correctly.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_memory_service_discovery():
    """Test InMemoryServiceDiscovery with strong typing."""
    print("🧪 Testing InMemoryServiceDiscovery...")

    try:
        from omnibase_core.core.common_types import ModelScalarValue
        from omnibase_core.services.memory_service_discovery import (
            InMemoryServiceDiscovery,
        )

        service_discovery = InMemoryServiceDiscovery()

        # Test metadata with different types
        metadata = {
            "environment": ModelScalarValue.create_string("production"),
            "replicas": ModelScalarValue.create_int(3),
            "load_factor": ModelScalarValue.create_float(0.75),
            "is_active": ModelScalarValue.create_bool(True),
        }

        # Register service
        print("  ✅ Registering service with typed metadata...")
        result = await service_discovery.register_service(
            service_name="test-service",
            service_id="test-001",
            host="localhost",
            port=8080,
            metadata=metadata,
        )
        assert result is True
        print("  ✅ Service registered successfully")

        # Discover services
        print("  ✅ Discovering services...")
        services = await service_discovery.discover_services("test-service")

        assert len(services) == 1
        service = services[0]

        # Verify return types
        print("  ✅ Verifying return types...")
        required_fields = [
            "service_name",
            "service_id",
            "host",
            "port",
            "health_status",
        ]

        for field in required_fields:
            assert field in service, f"Missing field: {field}"
            assert isinstance(
                service[field],
                ModelScalarValue,
            ), f"Field {field} is not ModelScalarValue: {type(service[field])}"
            print(
                f"    ✅ {field}: {service[field].type_hint} = {getattr(service[field], f'{service[field].type_hint}_value')}",
            )

        # Verify metadata preservation
        print("  ✅ Verifying metadata preservation...")
        metadata_fields = ["environment", "replicas", "load_factor", "is_active"]

        for field in metadata_fields:
            assert field in service, f"Missing metadata field: {field}"
            assert isinstance(
                service[field],
                ModelScalarValue,
            ), f"Metadata field {field} is not ModelScalarValue"
            print(
                f"    ✅ {field}: {service[field].type_hint} = {getattr(service[field], f'{service[field].type_hint}_value')}",
            )

        # Test specific values
        assert service["environment"].to_string_primitive() == "production"
        assert service["replicas"].to_int_primitive() == 3
        assert abs(service["load_factor"].to_float_primitive() - 0.75) < 0.001
        assert service["is_active"].to_bool_primitive() is True

        print("  ✅ All metadata values correct")

        # Test health functionality
        print("  ✅ Testing health functionality...")
        health = await service_discovery.get_service_health("test-001")
        assert health.service_id == "test-001"
        assert health.status == "healthy"
        print(f"    ✅ Health status: {health.status}")

        # Test deregistration
        print("  ✅ Testing deregistration...")
        result = await service_discovery.deregister_service("test-001")
        assert result is True

        services = await service_discovery.discover_services("test-service")
        assert len(services) == 0
        print("    ✅ Service deregistered successfully")

        await service_discovery.close()
        print("✅ InMemoryServiceDiscovery tests passed!\n")
        return True

    except Exception as e:
        print(f"❌ InMemoryServiceDiscovery test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_consul_service_discovery():
    """Test ConsulServiceDiscovery with fallback."""
    print("🧪 Testing ConsulServiceDiscovery...")

    try:
        from omnibase_core.core.common_types import ModelScalarValue
        from omnibase_core.services.consul_service_discovery import (
            ConsulServiceDiscovery,
        )

        # Test with fallback (consul module not available)
        service_discovery = ConsulServiceDiscovery(enable_fallback=True)

        # This should automatically use fallback
        metadata = {
            "datacenter": ModelScalarValue.create_string("us-west-2"),
            "tier": ModelScalarValue.create_string("production"),
            "weight": ModelScalarValue.create_int(100),
        }

        print("  ✅ Registering service (should use fallback)...")
        result = await service_discovery.register_service(
            service_name="consul-test-service",
            service_id="consul-001",
            host="192.168.1.10",
            port=9000,
            metadata=metadata,
        )
        assert result is True
        print("  ✅ Service registered via fallback")

        # Discover services
        print("  ✅ Discovering services via fallback...")
        services = await service_discovery.discover_services("consul-test-service")

        assert len(services) == 1
        service = services[0]

        # Verify types
        print("  ✅ Verifying return types from fallback...")
        assert isinstance(service["service_name"], ModelScalarValue)
        assert isinstance(service["service_id"], ModelScalarValue)
        assert isinstance(service["host"], ModelScalarValue)
        assert isinstance(service["port"], ModelScalarValue)

        # Verify values
        assert service["service_name"].to_string_primitive() == "consul-test-service"
        assert service["service_id"].to_string_primitive() == "consul-001"
        assert service["host"].to_string_primitive() == "192.168.1.10"
        assert service["port"].to_int_primitive() == 9000

        # Verify metadata
        assert "datacenter" in service
        assert service["datacenter"].to_string_primitive() == "us-west-2"
        assert service["weight"].to_int_primitive() == 100

        print("  ✅ All values correct via fallback")

        await service_discovery.close()
        print("✅ ConsulServiceDiscovery tests passed!\n")
        return True

    except Exception as e:
        print(f"❌ ConsulServiceDiscovery test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_model_scalar_value_standalone():
    """Test ModelScalarValue independently."""
    print("🧪 Testing ModelScalarValue...")

    try:
        from omnibase_core.core.common_types import ModelScalarValue

        # Test all type creations
        print("  ✅ Testing type creation...")
        string_val = ModelScalarValue.create_string("test_string")
        int_val = ModelScalarValue.create_int(42)
        float_val = ModelScalarValue.create_float(3.14159)
        bool_val = ModelScalarValue.create_bool(True)

        # Test type hints
        assert string_val.type_hint == "str"
        assert int_val.type_hint == "int"
        assert float_val.type_hint == "float"
        assert bool_val.type_hint == "bool"
        print("    ✅ Type hints correct")

        # Test primitive extraction
        assert string_val.to_string_primitive() == "test_string"
        assert int_val.to_int_primitive() == 42
        assert abs(float_val.to_float_primitive() - 3.14159) < 0.00001
        assert bool_val.to_bool_primitive() is True
        print("    ✅ Primitive extraction correct")

        # Test validation
        try:
            ModelScalarValue(string_value="test", int_value=42)
            assert False, "Should have failed validation"
        except ValueError as e:
            assert "exactly one value" in str(e)
            print("    ✅ Validation working correctly")

        # Test edge cases
        print("  ✅ Testing edge cases...")
        empty_str = ModelScalarValue.create_string("")
        zero_int = ModelScalarValue.create_int(0)
        zero_float = ModelScalarValue.create_float(0.0)
        false_bool = ModelScalarValue.create_bool(False)

        assert empty_str.to_string_primitive() == ""
        assert zero_int.to_int_primitive() == 0
        assert zero_float.to_float_primitive() == 0.0
        assert false_bool.to_bool_primitive() is False
        print("    ✅ Edge cases handled correctly")

        print("✅ ModelScalarValue tests passed!\n")
        return True

    except Exception as e:
        print(f"❌ ModelScalarValue test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all standalone tests."""
    print("🚀 Running Service Discovery Standalone Tests\n")

    results = []

    # Test ModelScalarValue first
    results.append(await test_model_scalar_value_standalone())

    # Test InMemoryServiceDiscovery
    results.append(await test_memory_service_discovery())

    # Test ConsulServiceDiscovery
    results.append(await test_consul_service_discovery())

    # Summary
    print("📊 Test Results Summary:")
    print("=" * 50)

    test_names = [
        "ModelScalarValue Standalone",
        "InMemoryServiceDiscovery",
        "ConsulServiceDiscovery",
    ]

    for i, (name, result) in enumerate(zip(test_names, results, strict=False)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")

    all_passed = all(results)
    print("=" * 50)

    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Service Discovery Strong Typing Implementation Verified:")
        print("   • ModelScalarValue creation and validation working")
        print("   • InMemoryServiceDiscovery returns properly typed values")
        print("   • ConsulServiceDiscovery fallback maintains typing")
        print("   • Metadata preservation with correct types")
        print("   • Type conversion and primitive extraction working")
        print("   • Edge cases handled correctly")
        return 0
    print("💥 SOME TESTS FAILED!")
    failed_count = len([r for r in results if not r])
    print(f"   {failed_count}/{len(results)} tests failed")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
