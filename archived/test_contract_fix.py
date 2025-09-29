#!/usr/bin/env python3
"""
Test script to verify the ModelContractEffect.from_yaml() recursion fix.

This script tests the critical P0 bug fix to ensure ONEX nodes can now initialize.
"""

import tempfile
from pathlib import Path

from omnibase_core.core.contracts.model_contract_effect import ModelContractEffect


def test_minimal_contract():
    """
    Validate that a minimal effect contract YAML can be parsed without causing infinite recursion.

    Attempts to load a compact, valid effect contract YAML into ModelContractEffect. Useful to verify that parsing/loading does not raise a RecursionError when initializing basic ONEX nodes.

    Returns:
        True if the contract loads successfully, False otherwise.
    """

    minimal_yaml = """
name: test_effect_node
version: 1.0.0
description: Test effect node for recursion fix validation
node_type: EFFECT
input_model: omnibase_core.models.effect.ModelEffectInput
output_model: omnibase_core.models.effect.ModelEffectOutput
contract_version: 1.0.0
node_name: test_effect_node
input_state:
  type: object
output_state:
  type: object
io_operations:
  - operation_type: file_read
    atomic: true
    timeout_seconds: 30
"""

    print("Testing minimal contract YAML loading...")
    try:
        contract = ModelContractEffect.from_yaml(minimal_yaml)
        print(f"✅ SUCCESS: Contract loaded successfully")
        print(f"   - Node name: {contract.node_name}")
        print(f"   - Contract version: {contract.contract_version}")
        print(f"   - IO operations: {len(contract.io_operations)}")
        print(f"   - Node type: {contract.node_type}")
        return True
    except RecursionError as e:
        print(f"❌ FAILED: Infinite recursion still exists: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Other error: {e}")
        return False


def test_comprehensive_contract():
    """Test comprehensive contract with full ONEX features."""

    comprehensive_yaml = """
name: comprehensive_effect_node
version: 2.1.0
description: Comprehensive effect node with full ONEX feature set for testing
node_type: EFFECT
input_model: omnibase_core.models.effect.ModelEffectInput
output_model: omnibase_core.models.effect.ModelEffectOutput
contract_version: 1.0.0
node_name: comprehensive_effect_node

input_state:
  type: object
  properties:
    data:
      type: string
    version:
      type: integer

output_state:
  type: object
  properties:
    result:
      type: string
    processed_at:
      type: string

io_operations:
  - operation_type: file_write
    atomic: true
    backup_enabled: true
    timeout_seconds: 60
    buffer_size: 8192
  - operation_type: db_query
    atomic: false
    timeout_seconds: 30

transaction_management:
  enabled: true
  isolation_level: read_committed
  timeout_seconds: 45
  rollback_on_error: true

retry_policies:
  max_attempts: 5
  backoff_strategy: exponential
  base_delay_ms: 200
  max_delay_ms: 8000
  circuit_breaker_enabled: true

external_services:
  - service_type: rest_api
    endpoint_url: https://api.example.com
    authentication_method: bearer_token
    rate_limit_enabled: true
    max_connections: 20

backup_config:
  enabled: true
  backup_location: ./backups
  retention_days: 14
  compression_enabled: true

event_type:
  primary_events:
    - effect_processed
  event_categories:
    - system
  event_routing:
    - target: processor
  event_name: effect_processed
  event_schema:
    type: object
    properties:
      node_id:
        type: string
      result:
        type: object
"""

    print("\nTesting comprehensive contract YAML loading...")
    try:
        contract = ModelContractEffect.from_yaml(comprehensive_yaml)
        print(f"✅ SUCCESS: Comprehensive contract loaded successfully")
        print(f"   - Node name: {contract.node_name}")
        print(f"   - IO operations: {len(contract.io_operations)}")
        print(f"   - External services: {len(contract.external_services)}")
        print(f"   - Transaction management: {contract.transaction_management.enabled}")
        print(f"   - Retry max attempts: {contract.retry_policies.max_attempts}")
        print(f"   - Backup enabled: {contract.backup_config.enabled}")
        return True
    except RecursionError as e:
        print(f"❌ FAILED: Infinite recursion still exists: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Other error: {e}")
        return False


def test_file_based_loading():
    """Test loading contract from actual file (simulates real ONEX node initialization)."""

    file_yaml = """
name: file_based_effect_node
version: 1.0.0
description: File-based effect node for testing real initialization
node_type: EFFECT
input_model: omnibase_core.models.effect.ModelEffectInput
output_model: omnibase_core.models.effect.ModelEffectOutput
contract_version: 1.0.0
node_name: file_based_effect_node
input_state:
  type: object
output_state:
  type: object
io_operations:
  - operation_type: file_read
    atomic: true
"""

    print("\nTesting file-based contract loading...")
    try:
        # Create temporary contract file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(file_yaml)
            temp_path = Path(f.name)

        # Read file and load contract (simulates real node initialization)
        yaml_content = temp_path.read_text()
        contract = ModelContractEffect.from_yaml(yaml_content)

        # Cleanup
        temp_path.unlink()

        print(f"✅ SUCCESS: File-based contract loaded successfully")
        print(f"   - Node name: {contract.node_name}")
        print(f"   - Contract version: {contract.contract_version}")
        return True
    except RecursionError as e:
        print(f"❌ FAILED: Infinite recursion still exists: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Other error: {e}")
        return False


def main():
    """Run all contract loading tests to verify the recursion fix."""

    print("🚀 Testing ModelContractEffect.from_yaml() recursion fix")
    print("=" * 60)

    tests = [
        test_minimal_contract,
        test_comprehensive_contract,
        test_file_based_loading,
    ]

    passed = 0
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ CRITICAL: Test {test_func.__name__} crashed: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 SUCCESS: All tests passed - recursion bug is FIXED!")
        print("✅ ONEX nodes should now be able to initialize properly")
        return True
    else:
        print("❌ FAILURE: Some tests failed - recursion bug may still exist")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
