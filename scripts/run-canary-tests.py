#!/usr/bin/env python3
"""
Canary Node Unit Test Runner

Runs comprehensive unit tests for all canary nodes to ensure they meet
ONEX architecture requirements and functional specifications.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_canary_unit_tests():
    """Run all canary node unit tests."""
    print("🧪 Running Canary Node Unit Tests")
    print("=" * 50)

    # Set PYTHONPATH to include src directory
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"

    env = {"PYTHONPATH": str(src_path)}

    # Run the unit tests with pytest
    test_file = project_root / "tests" / "unit" / "test_canary_nodes.py"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    try:
        # Run pytest with verbose output and coverage
        cmd = [
            "poetry",
            "run",
            "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "--no-header",
            "--disable-warnings",
        ]

        print(f"🚀 Running: {' '.join(cmd)}")
        print()

        result = subprocess.run(
            cmd, env={**env, **dict(os.environ)}, cwd=project_root, capture_output=False
        )

        if result.returncode == 0:
            print("\n✅ All canary node unit tests passed!")
            return True
        else:
            print(f"\n❌ Some tests failed (exit code: {result.returncode})")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Test execution failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ Poetry not found. Please ensure poetry is installed and in PATH.")
        return False


def run_canary_test_validation():
    """Validate canary test coverage and completeness."""
    print("\n🔍 Validating Canary Test Coverage")
    print("-" * 50)

    # Expected test classes
    expected_tests = [
        "TestCanaryEffect",
        "TestCanaryCompute",
        "TestCanaryReducer",
        "TestCanaryOrchestrator",
        "TestCanaryGateway",
        "TestCanaryNodeIntegration",
    ]

    test_file = Path(__file__).parent.parent / "tests" / "unit" / "test_canary_nodes.py"

    if not test_file.exists():
        print("❌ Canary test file not found")
        return False

    # Read test file content
    test_content = test_file.read_text()

    missing_tests = []
    for test_class in expected_tests:
        if f"class {test_class}" not in test_content:
            missing_tests.append(test_class)

    if missing_tests:
        print(f"❌ Missing test classes: {', '.join(missing_tests)}")
        return False

    # Check for critical test methods
    critical_methods = [
        "test_health_check",
        "test_error_handling",
        "test_metrics_collection",
    ]

    missing_methods = []
    for method in critical_methods:
        if method not in test_content:
            missing_methods.append(method)

    if missing_methods:
        print(f"⚠️  Missing critical test methods: {', '.join(missing_methods)}")
        # Don't fail for missing methods, just warn

    print("✅ Test coverage validation passed")
    return True


def main():
    """Main entry point."""
    import os

    success = True

    # Validate test coverage first
    success &= run_canary_test_validation()

    # Run the actual tests
    success &= run_canary_unit_tests()

    if success:
        print("\n🎉 Canary node testing completed successfully!")
        sys.exit(0)
    else:
        print("\n🚫 Canary node testing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
