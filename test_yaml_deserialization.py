#!/usr/bin/env python3
"""
Test YAML Contract Deserialization

This tests what the pre-commit hook SHOULD be testing but isn't:
Can the YAML contract files actually deserialize to their backing Pydantic models?
"""

import sys
from pathlib import Path

import yaml

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_canary_contract_deserialization():
    """Test if Canary YAML contracts deserialize to their backing models."""

    contracts_to_test = [
        {
            "name": "canary_compute",
            "yaml_path": "src/omnibase_core/nodes/canary/canary_compute/v1_0_0/contract.yaml",
            "model_class": "ModelContractCompute",
            "model_module": "omnibase_core.core.contracts.model_contract_compute",
        },
        {
            "name": "canary_effect",
            "yaml_path": "src/omnibase_core/nodes/canary/canary_effect/v1_0_0/contract.yaml",
            "model_class": "ModelContractEffect",
            "model_module": "omnibase_core.core.contracts.model_contract_effect",
        },
        {
            "name": "canary_gateway",
            "yaml_path": "src/omnibase_core/nodes/canary/canary_gateway/v1_0_0/contract.yaml",
            "model_class": "ModelContractGateway",
            "model_module": "omnibase_core.core.contracts.model_contract_gateway",
        },
        {
            "name": "canary_orchestrator",
            "yaml_path": "src/omnibase_core/nodes/canary/canary_orchestrator/v1_0_0/contract.yaml",
            "model_class": "ModelContractOrchestrator",
            "model_module": "omnibase_core.core.contracts.model_contract_orchestrator",
        },
        {
            "name": "canary_reducer",
            "yaml_path": "src/omnibase_core/nodes/canary/canary_reducer/v1_0_0/contract.yaml",
            "model_class": "ModelContractReducer",
            "model_module": "omnibase_core.core.contracts.model_contract_reducer",
        },
    ]

    print("🧪 Testing YAML Contract → Pydantic Model Deserialization")
    print("=" * 65)

    results = []

    for contract in contracts_to_test:
        print(f"\n📄 Testing {contract['name']}...")

        try:
            # Load YAML file
            yaml_path = Path(contract["yaml_path"])
            if not yaml_path.exists():
                print(f"   ❌ YAML file not found: {yaml_path}")
                results.append((contract["name"], False, f"YAML file not found"))
                continue

            with open(yaml_path, "r") as f:
                yaml_data = yaml.safe_load(f)

            print(f"   ✅ YAML loaded successfully")

            # Import the model class using whitelist approach for security
            try:
                # Whitelist of allowed modules for security
                allowed_modules = {
                    "omnibase_core.core.contracts.model_contract_compute": "omnibase_core.core.contracts.model_contract_compute",
                    "omnibase_core.core.contracts.model_contract_effect": "omnibase_core.core.contracts.model_contract_effect",
                    "omnibase_core.core.contracts.model_contract_gateway": "omnibase_core.core.contracts.model_contract_gateway",
                    "omnibase_core.core.contracts.model_contract_orchestrator": "omnibase_core.core.contracts.model_contract_orchestrator",
                    "omnibase_core.core.contracts.model_contract_reducer": "omnibase_core.core.contracts.model_contract_reducer",
                }

                module_name = contract["model_module"]
                if module_name not in allowed_modules:
                    raise ValueError(f"Module {module_name} not in allowed whitelist")

                import importlib

                module = importlib.import_module(allowed_modules[module_name])
                model_class = getattr(module, contract["model_class"])
                print(f"   ✅ Model class imported: {contract['model_class']}")
            except Exception as e:
                print(f"   ❌ Failed to import model class: {e}")
                results.append((contract["name"], False, f"Model import failed: {e}"))
                continue

            # Try to deserialize YAML to Pydantic model
            try:
                model_instance = model_class.model_validate(yaml_data)
                print(f"   ✅ YAML → Model deserialization SUCCESS!")

                # Test serialization back
                serialized = model_instance.model_dump()
                print(f"   ✅ Model → dict serialization SUCCESS!")

                results.append((contract["name"], True, "Full round-trip successful"))

            except Exception as e:
                print(f"   ❌ YAML → Model deserialization FAILED: {e}")
                print(f"      Error type: {type(e).__name__}")
                results.append(
                    (contract["name"], False, f"Deserialization failed: {e}")
                )

        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            results.append((contract["name"], False, f"Unexpected error: {e}"))

    # Print summary
    print("\n" + "=" * 65)
    print("📊 YAML DESERIALIZATION TEST SUMMARY")
    print("=" * 65)

    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    print(f"Total Contracts Tested: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Success Rate: {len(successful)/len(results)*100:.1f}%")

    if failed:
        print(f"\n❌ FAILED CONTRACTS ({len(failed)}):")
        for name, _, error in failed:
            print(f"   • {name}: {error}")

    if successful:
        print(f"\n✅ SUCCESSFUL CONTRACTS ({len(successful)}):")
        for name, _, message in successful:
            print(f"   • {name}: {message}")

    return len(failed) == 0


if __name__ == "__main__":
    success = test_canary_contract_deserialization()
    sys.exit(0 if success else 1)
