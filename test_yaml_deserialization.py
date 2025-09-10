#!/usr/bin/env python3
"""
Test YAML Contract Deserialization

This tests what the pre-commit hook SHOULD be testing but isn't:
Can the YAML contract files actually deserialize to their backing Pydantic models?
"""

import sys
from pathlib import Path

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
                results.append((contract["name"], False, "YAML file not found"))
                continue

            with open(yaml_path) as f:
                yaml_content = f.read()

            print("   ✅ YAML file read successfully")

            # Import the model class using static imports for security
            try:
                # Use static imports to avoid dynamic import security issues
                from omnibase_core.core.contracts.model_contract_compute import (
                    ModelContractCompute,
                )
                from omnibase_core.core.contracts.model_contract_effect import (
                    ModelContractEffect,
                )
                from omnibase_core.core.contracts.model_contract_gateway import (
                    ModelContractGateway,
                )
                from omnibase_core.core.contracts.model_contract_orchestrator import (
                    ModelContractOrchestrator,
                )
                from omnibase_core.core.contracts.model_contract_reducer import (
                    ModelContractReducer,
                )

                # Mapping of module names to actual model classes
                allowed_models = {
                    "omnibase_core.core.contracts.model_contract_compute": {
                        "ModelContractCompute": ModelContractCompute,
                    },
                    "omnibase_core.core.contracts.model_contract_effect": {
                        "ModelContractEffect": ModelContractEffect,
                    },
                    "omnibase_core.core.contracts.model_contract_gateway": {
                        "ModelContractGateway": ModelContractGateway,
                    },
                    "omnibase_core.core.contracts.model_contract_orchestrator": {
                        "ModelContractOrchestrator": ModelContractOrchestrator,
                    },
                    "omnibase_core.core.contracts.model_contract_reducer": {
                        "ModelContractReducer": ModelContractReducer,
                    },
                }

                module_name = contract["model_module"]
                model_class_name = contract["model_class"]

                if module_name not in allowed_models:
                    raise ValueError(f"Module {module_name} not in allowed list")

                if model_class_name not in allowed_models[module_name]:
                    raise ValueError(
                        f"Model class {model_class_name} not found in {module_name}",
                    )

                model_class = allowed_models[module_name][model_class_name]
                print(f"   ✅ Model class imported: {model_class_name}")
            except Exception as e:
                print(f"   ❌ Failed to import model class: {e}")
                results.append((contract["name"], False, f"Model import failed: {e}"))
                continue

            # Try to deserialize YAML to Pydantic model using from_yaml method
            try:
                if hasattr(model_class, "from_yaml"):
                    model_instance = model_class.from_yaml(yaml_content)
                else:
                    # Fallback: use ModelGenericYaml first, then model_validate
                    from omnibase_core.model.core.model_generic_yaml import (
                        ModelGenericYaml,
                    )

                    generic_model = ModelGenericYaml.from_yaml(yaml_content)
                    yaml_data = generic_model.model_dump()
                    model_instance = model_class.model_validate(yaml_data)
                print("   ✅ YAML → Model deserialization SUCCESS!")

                # Test serialization back
                serialized = model_instance.model_dump()
                print("   ✅ Model → dict serialization SUCCESS!")

                results.append((contract["name"], True, "Full round-trip successful"))

            except Exception as e:
                print(f"   ❌ YAML → Model deserialization FAILED: {e}")
                print(f"      Error type: {type(e).__name__}")
                results.append(
                    (contract["name"], False, f"Deserialization failed: {e}"),
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
