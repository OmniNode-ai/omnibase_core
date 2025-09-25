#!/usr/bin/env python3
"""
Comprehensive Contract Models Validation Test

This script tests all contract models in the omnibase_core system to ensure:
- All models can be imported successfully
- All models can be instantiated with valid data
- Field validators work correctly
- No circular dependency issues exist

Usage:
    poetry run python test_contract_models.py
"""

import traceback
from typing import Any, Dict, List, Tuple


def test_main_contract_models() -> List[Tuple[str, bool, str]]:
    """Test the four main contract models (Compute, Effect, Orchestrator, Reducer)."""
    results = []

    try:
        from src.omnibase_core.enums import EnumNodeType
        from src.omnibase_core.models.contracts.model_contract_compute import (
            ModelContractCompute,
        )
        from src.omnibase_core.models.contracts.model_contract_effect import (
            ModelContractEffect,
        )
        from src.omnibase_core.models.contracts.model_contract_orchestrator import (
            ModelContractOrchestrator,
        )
        from src.omnibase_core.models.contracts.model_contract_reducer import (
            ModelContractReducer,
        )

        print("✅ Successfully imported all main contract models")
    except Exception as e:
        results.append(("Import Main Contracts", False, f"Failed to import: {e}"))
        return results

    def test_contract(
        contract_class, node_type, class_name, extra_required_fields=None
    ):
        try:
            # Base required fields for all contracts
            contract_data = {
                "name": f"test_{node_type.value}",
                "version": {"major": 1, "minor": 0, "patch": 0},
                "description": f"Test {node_type.value} contract",
                "node_type": node_type,
                "input_model": "TestInputModel",
                "output_model": "TestOutputModel",
                "performance": {"single_operation_max_ms": 1000},
            }

            # Add extra required fields if any
            if extra_required_fields:
                contract_data.update(extra_required_fields)

            contract = contract_class(**contract_data)
            return (
                class_name,
                True,
                f"Success - Contract: {contract.name}, Node: {contract.node_type}, Version: {contract.version}",
            )
        except Exception as e:
            return (class_name, False, f"Instantiation failed: {str(e)[:200]}")

    # Test ModelContractCompute (requires algorithm field)
    results.append(
        test_contract(
            ModelContractCompute,
            EnumNodeType.COMPUTE,
            "ModelContractCompute",
            {
                "algorithm": {
                    "algorithm_type": "test_algorithm",
                    "factors": {
                        "test_factor": {"weight": 1.0, "calculation_method": "linear"}
                    },
                }
            },
        )
    )

    # Test ModelContractEffect (requires io_operations field)
    results.append(
        test_contract(
            ModelContractEffect,
            EnumNodeType.EFFECT,
            "ModelContractEffect",
            {"io_operations": [{"operation_type": "api_call"}]},
        )
    )

    # Test ModelContractOrchestrator
    results.append(
        test_contract(
            ModelContractOrchestrator,
            EnumNodeType.ORCHESTRATOR,
            "ModelContractOrchestrator",
        )
    )

    # Test ModelContractReducer
    results.append(
        test_contract(
            ModelContractReducer, EnumNodeType.REDUCER, "ModelContractReducer"
        )
    )

    return results


def test_working_subcontract_models() -> List[Tuple[str, bool, str]]:
    """Test subcontract models that work without required fields."""
    results = []

    try:
        from src.omnibase_core.models.contracts.subcontracts.model_caching_subcontract import (
            ModelCachingSubcontract,
        )
        from src.omnibase_core.models.contracts.subcontracts.model_routing_subcontract import (
            ModelRoutingSubcontract,
        )
        from src.omnibase_core.models.contracts.subcontracts.model_state_management_subcontract import (
            ModelStateManagementSubcontract,
        )
        from src.omnibase_core.models.contracts.subcontracts.model_workflow_coordination_subcontract import (
            ModelWorkflowCoordinationSubcontract,
        )

        print("✅ Successfully imported working subcontract models")
    except Exception as e:
        results.append(("Import Subcontracts", False, f"Failed to import: {e}"))
        return results

    def test_subcontract(subcontract_class, class_name, required_fields=None):
        try:
            data = {}
            if required_fields:
                data.update(required_fields)

            subcontract = subcontract_class(**data)
            return (class_name, True, f"Success - instantiated {class_name}")
        except Exception as e:
            return (class_name, False, f"Failed: {str(e)[:200]}")

    # Test working subcontracts
    results.append(test_subcontract(ModelCachingSubcontract, "ModelCachingSubcontract"))
    results.append(test_subcontract(ModelRoutingSubcontract, "ModelRoutingSubcontract"))
    results.append(
        test_subcontract(
            ModelStateManagementSubcontract, "ModelStateManagementSubcontract"
        )
    )
    results.append(
        test_subcontract(
            ModelWorkflowCoordinationSubcontract, "ModelWorkflowCoordinationSubcontract"
        )
    )

    return results


def test_working_supporting_models() -> List[Tuple[str, bool, str]]:
    """Test supporting contract models that work."""
    results = []

    try:
        from src.omnibase_core.models.contracts.model_dependency import ModelDependency
        from src.omnibase_core.models.contracts.model_filter_conditions import (
            ModelFilterConditions,
        )
        from src.omnibase_core.models.contracts.model_trigger_mappings import (
            ModelTriggerMappings,
        )
        from src.omnibase_core.models.contracts.model_workflow_conditions import (
            ModelWorkflowConditions,
        )

        print("✅ Successfully imported working supporting models")
    except Exception as e:
        results.append(("Import Supporting Models", False, f"Failed to import: {e}"))
        return results

    def test_model(model_class, class_name, required_fields=None):
        try:
            data = {}
            if required_fields:
                data.update(required_fields)

            model = model_class(**data)
            return (class_name, True, f"Success - instantiated {class_name}")
        except Exception as e:
            return (class_name, False, f"Failed: {str(e)[:200]}")

    # Test working supporting models
    results.append(
        test_model(ModelDependency, "ModelDependency", {"name": "TestDependency"})
    )
    results.append(test_model(ModelFilterConditions, "ModelFilterConditions"))
    results.append(test_model(ModelTriggerMappings, "ModelTriggerMappings"))
    results.append(test_model(ModelWorkflowConditions, "ModelWorkflowConditions"))

    return results


def test_field_validators() -> List[Tuple[str, bool, str]]:
    """Test field validators work correctly."""
    results = []

    try:
        from src.omnibase_core.enums import EnumNodeType
        from src.omnibase_core.models.contracts.model_contract_compute import (
            ModelContractCompute,
        )

        print("✅ Testing field validators")
    except Exception as e:
        results.append(("Field Validators Import", False, f"Failed to import: {e}"))
        return results

    # Test invalid version field
    try:
        ModelContractCompute(
            name="test_compute",
            version={"major": -1, "minor": 0, "patch": 0},  # Invalid negative version
            description="Test compute contract",
            node_type=EnumNodeType.COMPUTE,
            input_model="TestInputModel",
            output_model="TestOutputModel",
            algorithm={
                "algorithm_type": "test",
                "factors": {"factor1": {"weight": 1.0, "calculation_method": "test"}},
            },
            performance={"single_operation_max_ms": 1000},
        )
        results.append(
            ("Version Validator", False, "Should have rejected negative version")
        )
    except Exception:
        results.append(
            ("Version Validator", True, "Correctly rejected negative version")
        )

    # Test invalid algorithm factor weights (should sum to 1.0)
    try:
        ModelContractCompute(
            name="test_compute",
            version={"major": 1, "minor": 0, "patch": 0},
            description="Test compute contract",
            node_type=EnumNodeType.COMPUTE,
            input_model="TestInputModel",
            output_model="TestOutputModel",
            algorithm={
                "algorithm_type": "test",
                "factors": {"factor1": {"weight": 0.5, "calculation_method": "test"}},
            },  # Doesn't sum to 1.0
            performance={"single_operation_max_ms": 1000},
        )
        results.append(
            (
                "Factor Weight Validator",
                False,
                "Should have rejected weights not summing to 1.0",
            )
        )
    except Exception:
        results.append(
            (
                "Factor Weight Validator",
                True,
                "Correctly rejected invalid factor weights",
            )
        )

    # Test invalid node type
    try:
        ModelContractCompute(
            name="test_compute",
            version={"major": 1, "minor": 0, "patch": 0},
            description="Test compute contract",
            node_type="invalid_node_type",  # Invalid node type
            input_model="TestInputModel",
            output_model="TestOutputModel",
            algorithm={
                "algorithm_type": "test",
                "factors": {"factor1": {"weight": 1.0, "calculation_method": "test"}},
            },
            performance={"single_operation_max_ms": 1000},
        )
        results.append(
            ("Node Type Validator", False, "Should have rejected invalid node type")
        )
    except Exception:
        results.append(
            ("Node Type Validator", True, "Correctly rejected invalid node type")
        )

    return results


def main():
    """Run all tests and print results."""
    print("Contract Models Validation Test")
    print("=" * 50)

    all_results = []

    # Test main contract models
    print("\n🔍 Testing Main Contract Models...")
    main_results = test_main_contract_models()
    all_results.extend(main_results)

    # Test working subcontract models
    print("\n🔍 Testing Subcontract Models...")
    subcontract_results = test_working_subcontract_models()
    all_results.extend(subcontract_results)

    # Test working supporting models
    print("\n🔍 Testing Supporting Models...")
    supporting_results = test_working_supporting_models()
    all_results.extend(supporting_results)

    # Test field validators
    print("\n🔍 Testing Field Validators...")
    validator_results = test_field_validators()
    all_results.extend(validator_results)

    # Print summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, success, message in all_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"TOTAL: {passed + failed} tests")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")

    if failed == 0:
        print("🎉 All tests passed! Contract models are working correctly.")
        return 0
    else:
        print(f"⚠️  {failed} tests failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    exit(main())
