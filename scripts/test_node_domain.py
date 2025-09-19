#!/usr/bin/env python3
"""
Node Domain Test Runner

Simplified test runner for node domain reorganization validation
that doesn't rely on the full dependency chain.
"""

import sys
import os
import importlib.util
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_node_domain_structure():
    """Test the basic structure of the node domain."""
    results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "errors": []
    }

    print("🔍 Testing Node Domain Reorganization")
    print("=" * 50)

    # Test 1: Check if node models directory exists
    results["tests_run"] += 1
    nodes_dir = Path(__file__).parent.parent / "src" / "omnibase_core" / "models" / "nodes"
    if nodes_dir.exists():
        print("✅ Node models directory exists")
        results["tests_passed"] += 1
    else:
        print("❌ Node models directory missing")
        results["tests_failed"] += 1
        results["errors"].append("Node models directory not found")

    # Test 2: Check if individual model files exist
    expected_files = [
        "model_cli_node_execution_input.py",
        "model_metadata_node_collection.py",
        "model_node_capability.py",
        "model_node_information.py",
        "model_node_type.py",
        "__init__.py",
    ]

    for file_name in expected_files:
        results["tests_run"] += 1
        file_path = nodes_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name} exists")
            results["tests_passed"] += 1
        else:
            print(f"❌ {file_name} missing")
            results["tests_failed"] += 1
            results["errors"].append(f"Missing file: {file_name}")

    # Test 3: Check basic import structure without dependencies
    results["tests_run"] += 1
    init_file = nodes_dir / "__init__.py"
    if init_file.exists():
        try:
            with open(init_file, 'r') as f:
                content = f.read()

            # Check for expected imports in __init__.py
            expected_imports = [
                "ModelCliNodeExecutionInput",
                "ModelMetadataNodeCollection",
                "ModelNodeCapability",
                "ModelNodeInformation",
                "ModelNodeType"
            ]

            all_imports_found = all(imp in content for imp in expected_imports)
            if all_imports_found:
                print("✅ All expected imports found in __init__.py")
                results["tests_passed"] += 1
            else:
                missing = [imp for imp in expected_imports if imp not in content]
                print(f"❌ Missing imports in __init__.py: {missing}")
                results["tests_failed"] += 1
                results["errors"].append(f"Missing imports: {missing}")

        except Exception as e:
            print(f"❌ Error reading __init__.py: {e}")
            results["tests_failed"] += 1
            results["errors"].append(f"Error reading __init__.py: {e}")
    else:
        print("❌ __init__.py not found")
        results["tests_failed"] += 1
        results["errors"].append("__init__.py not found")

    # Test 4: Check __all__ declaration
    results["tests_run"] += 1
    try:
        with open(init_file, 'r') as f:
            content = f.read()

        if "__all__" in content:
            print("✅ __all__ declaration found")
            results["tests_passed"] += 1
        else:
            print("❌ __all__ declaration missing")
            results["tests_failed"] += 1
            results["errors"].append("__all__ declaration missing")
    except:
        print("❌ Could not check __all__ declaration")
        results["tests_failed"] += 1
        results["errors"].append("Could not check __all__ declaration")

    # Test 5: Check test files exist
    test_dir = Path(__file__).parent.parent / "tests" / "unit" / "nodes" / "domain_tests"
    expected_test_files = [
        "test_node_domain_imports.py",
        "test_node_exports.py",
        "test_four_node_archetype.py",
        "test_node_capability_model.py",
        "test_node_type_model.py",
        "test_cli_node_execution.py",
        "test_metadata_node_collection.py",
        "test_node_information_model.py",
    ]

    for test_file in expected_test_files:
        results["tests_run"] += 1
        test_path = test_dir / test_file
        if test_path.exists():
            print(f"✅ Test file {test_file} exists")
            results["tests_passed"] += 1
        else:
            print(f"❌ Test file {test_file} missing")
            results["tests_failed"] += 1
            results["errors"].append(f"Missing test file: {test_file}")

    # Test 6: Check integration tests
    results["tests_run"] += 1
    integration_test = Path(__file__).parent.parent / "tests" / "integration" / "nodes" / "test_node_domain_integration.py"
    if integration_test.exists():
        print("✅ Integration test file exists")
        results["tests_passed"] += 1
    else:
        print("❌ Integration test file missing")
        results["tests_failed"] += 1
        results["errors"].append("Integration test file missing")

    return results

def test_file_contents():
    """Test basic content validation of node model files."""
    results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "errors": []
    }

    print("\n📋 Testing File Contents")
    print("=" * 50)

    nodes_dir = Path(__file__).parent.parent / "src" / "omnibase_core" / "models" / "nodes"

    # Test file contents
    file_tests = [
        ("model_node_type.py", ["class ModelNodeType", "from_string", "CONTRACT_TO_MODEL"]),
        ("model_node_capability.py", ["class ModelNodeCapability", "SUPPORTS_DRY_RUN", "from_string"]),
        ("model_node_information.py", ["class ModelNodeInformation", "ModelNodeConfiguration", "from_dict"]),
        ("model_cli_node_execution_input.py", ["class ModelCliNodeExecutionInput", "to_legacy_dict", "from_legacy_dict"]),
    ]

    for file_name, expected_content in file_tests:
        results["tests_run"] += 1
        file_path = nodes_dir / file_name

        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                missing_content = [item for item in expected_content if item not in content]
                if not missing_content:
                    print(f"✅ {file_name} has expected content")
                    results["tests_passed"] += 1
                else:
                    print(f"❌ {file_name} missing content: {missing_content}")
                    results["tests_failed"] += 1
                    results["errors"].append(f"{file_name} missing: {missing_content}")

            except Exception as e:
                print(f"❌ Error reading {file_name}: {e}")
                results["tests_failed"] += 1
                results["errors"].append(f"Error reading {file_name}: {e}")
        else:
            print(f"❌ {file_name} not found")
            results["tests_failed"] += 1
            results["errors"].append(f"{file_name} not found")

    return results

def test_archetype_knowledge():
    """Test four node archetype knowledge is represented."""
    results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "errors": []
    }

    print("\n🏗️ Testing Four Node Archetype Knowledge")
    print("=" * 50)

    # Test that four node archetype tests exist
    test_file = Path(__file__).parent.parent / "tests" / "unit" / "nodes" / "domain_tests" / "test_four_node_archetype.py"

    results["tests_run"] += 1
    if test_file.exists():
        try:
            with open(test_file, 'r') as f:
                content = f.read()

            # Check for archetype patterns
            archetypes = ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]
            archetype_tests = [
                "test_compute_node_archetype",
                "test_effect_node_archetype",
                "test_reducer_node_archetype",
                "test_orchestrator_node_archetype"
            ]

            all_found = all(test in content for test in archetype_tests)
            if all_found:
                print("✅ All four node archetype tests found")
                results["tests_passed"] += 1
            else:
                missing = [test for test in archetype_tests if test not in content]
                print(f"❌ Missing archetype tests: {missing}")
                results["tests_failed"] += 1
                results["errors"].append(f"Missing archetype tests: {missing}")

        except Exception as e:
            print(f"❌ Error reading archetype test file: {e}")
            results["tests_failed"] += 1
            results["errors"].append(f"Error reading archetype test: {e}")
    else:
        print("❌ Four node archetype test file missing")
        results["tests_failed"] += 1
        results["errors"].append("Four node archetype test file missing")

    return results

def main():
    """Main test runner."""
    print("🧪 Node Domain Reorganization Test Suite")
    print("=" * 60)

    all_results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "errors": []
    }

    # Run all test suites
    test_suites = [
        ("Domain Structure", test_node_domain_structure),
        ("File Contents", test_file_contents),
        ("Archetype Knowledge", test_archetype_knowledge),
    ]

    for suite_name, test_func in test_suites:
        print(f"\n🔬 Running {suite_name} Tests...")
        results = test_func()

        # Aggregate results
        all_results["tests_run"] += results["tests_run"]
        all_results["tests_passed"] += results["tests_passed"]
        all_results["tests_failed"] += results["tests_failed"]
        all_results["errors"].extend(results["errors"])

    # Summary
    print("\n📊 Test Summary")
    print("=" * 60)
    print(f"Total Tests Run: {all_results['tests_run']}")
    print(f"Tests Passed: {all_results['tests_passed']} ✅")
    print(f"Tests Failed: {all_results['tests_failed']} ❌")

    if all_results['tests_failed'] == 0:
        print("\n🎉 All tests passed! Node domain reorganization is successful.")
        return True
    else:
        print(f"\n⚠️ {all_results['tests_failed']} tests failed.")
        if all_results['errors']:
            print("\nErrors:")
            for error in all_results['errors']:
                print(f"  - {error}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)