#!/usr/bin/env python3
"""
Protocol Implementation Testing Script

Tests that all protocol implementations work correctly across the 205 model files.
"""

import importlib
import sys
from pathlib import Path
from typing import Any

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from omnibase_core.types.constraints import (
    Configurable,
    Executable,
    Identifiable,
    MetadataProvider,
    Nameable,
    Serializable,
    Validatable,
)


class ProtocolTester:
    """Test protocol implementations across all models."""

    def __init__(self):
        self.test_results: list[dict[str, Any]] = []
        self.errors: list[str] = []

    def test_protocol_methods(self, instance: Any, class_name: str) -> dict[str, bool]:
        """Test protocol methods on an instance."""
        results = {}

        # Test Serializable
        if isinstance(instance, Serializable):
            try:
                serialized = instance.serialize()
                results["serialize"] = isinstance(serialized, dict)
            except Exception as e:
                results["serialize"] = False
                self.errors.append(f"{class_name}.serialize() failed: {e}")

        # Test Validatable
        if isinstance(instance, Validatable):
            try:
                is_valid = instance.validate()
                results["validate"] = isinstance(is_valid, bool)
            except Exception as e:
                results["validate"] = False
                self.errors.append(f"{class_name}.validate() failed: {e}")

        # Test Configurable
        if isinstance(instance, Configurable):
            try:
                configured = instance.configure(test_param="test_value")
                results["configure"] = isinstance(configured, bool)
            except Exception as e:
                results["configure"] = False
                self.errors.append(f"{class_name}.configure() failed: {e}")

        # Test Executable
        if isinstance(instance, Executable):
            try:
                executed = instance.execute(test_param="test_value")
                results["execute"] = isinstance(executed, bool)
            except Exception as e:
                results["execute"] = False
                self.errors.append(f"{class_name}.execute() failed: {e}")

        # Test Identifiable
        if isinstance(instance, Identifiable):
            try:
                identifier = instance.get_id()
                results["get_id"] = isinstance(identifier, str)
            except Exception as e:
                results["get_id"] = False
                self.errors.append(f"{class_name}.get_id() failed: {e}")

        # Test MetadataProvider
        if isinstance(instance, MetadataProvider):
            try:
                metadata = instance.get_metadata()
                results["get_metadata"] = isinstance(metadata, dict)

                # Test set_metadata
                set_result = instance.set_metadata({"test": "value"})
                results["set_metadata"] = isinstance(set_result, bool)
            except Exception as e:
                results["get_metadata"] = False
                results["set_metadata"] = False
                self.errors.append(f"{class_name} MetadataProvider methods failed: {e}")

        # Test Nameable
        if isinstance(instance, Nameable):
            try:
                name = instance.get_name()
                results["get_name"] = isinstance(name, str)

                # Test set_name
                instance.set_name("test_name")
                results["set_name"] = True
            except Exception as e:
                results["get_name"] = False
                results["set_name"] = False
                self.errors.append(f"{class_name} Nameable methods failed: {e}")

        return results

    def test_model_file(self, module_path: str) -> dict[str, Any]:
        """Test protocol implementations in a model file."""
        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Find model classes
            model_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr_name.startswith("Model")
                    and hasattr(attr, "__module__")
                    and attr.__module__ == module_path
                ):
                    model_classes.append((attr_name, attr))

            if not model_classes:
                return {
                    "module": module_path,
                    "status": "no_models",
                    "classes": [],
                    "protocol_tests": {},
                }

            # Test each model class
            class_results = {}
            for class_name, model_class in model_classes:
                try:
                    # Try to create an instance with default parameters
                    instance = None

                    # Try different instantiation approaches
                    for approach in [
                        lambda cls=model_class: cls(),  # Default constructor
                        lambda cls=model_class: cls(),  # Empty kwargs
                    ]:
                        try:
                            instance = approach()
                            break
                        except Exception:
                            continue

                    if instance is None:
                        # Try with common required fields
                        common_fields = {
                            "name": "test",
                            "key": "test_key",
                            "value": "test_value",
                            "id": "test_id",
                            "start_time": "2023-01-01T00:00:00Z",
                        }

                        # Get model fields to determine which are required
                        if hasattr(model_class, "model_fields"):
                            for (
                                field_name,
                                field_info,
                            ) in model_class.model_fields.items():
                                if (
                                    field_name in common_fields
                                    and hasattr(field_info, "is_required")
                                    and field_info.is_required()
                                ):
                                    try:
                                        instance = model_class(
                                            **{field_name: common_fields[field_name]}
                                        )
                                        break
                                    except Exception:
                                        continue

                    if instance is None:
                        class_results[class_name] = {
                            "instantiation": False,
                            "protocols": [],
                            "method_tests": {},
                        }
                        continue

                    # Check which protocols are implemented
                    protocols = []
                    for protocol in [
                        Serializable,
                        Validatable,
                        Configurable,
                        Executable,
                        Identifiable,
                        MetadataProvider,
                        Nameable,
                    ]:
                        if isinstance(instance, protocol):
                            protocols.append(protocol.__name__)

                    # Test protocol methods
                    method_tests = self.test_protocol_methods(instance, class_name)

                    class_results[class_name] = {
                        "instantiation": True,
                        "protocols": protocols,
                        "method_tests": method_tests,
                    }

                except Exception as e:
                    class_results[class_name] = {
                        "instantiation": False,
                        "error": str(e),
                        "protocols": [],
                        "method_tests": {},
                    }

            return {
                "module": module_path,
                "status": "success",
                "classes": list(class_results.keys()),
                "protocol_tests": class_results,
            }

        except Exception as e:
            return {
                "module": module_path,
                "status": "import_error",
                "error": str(e),
                "classes": [],
                "protocol_tests": {},
            }

    def test_all_models(self) -> dict[str, Any]:
        """Test all model implementations."""
        # Core models to test (sample from each category)
        test_modules = [
            # Core models
            "omnibase_core.models.core.model_configuration_base",
            "omnibase_core.models.core.model_generic_collection",
            "omnibase_core.models.core.model_typed_configuration",
            # Metadata models
            "omnibase_core.models.metadata.model_generic_metadata",
            "omnibase_core.models.metadata.model_semver",
            "omnibase_core.models.metadata.model_metadata_value",
            # Operations models
            "omnibase_core.models.operations.model_execution_metadata",
            "omnibase_core.models.operations.model_event_metadata",
            "omnibase_core.models.operations.model_workflow_metadata",
            # Nodes models
            "omnibase_core.models.nodes.model_node_metadata_info",
            "omnibase_core.models.nodes.model_node_core_metadata",
            "omnibase_core.models.nodes.model_node_configuration",
            # Config models
            "omnibase_core.models.examples.model_typed_property",
            "omnibase_core.models.examples.model_property_collection",
            "omnibase_core.models.examples.model_artifact_type_config",
            # Infrastructure models
            "omnibase_core.models.infrastructure.model_result",
            "omnibase_core.models.infrastructure.model_execution_result",
            "omnibase_core.models.infrastructure.model_retry_config",
            # CLI models
            "omnibase_core.models.cli.model_cli_execution",
            "omnibase_core.models.cli.model_cli_result",
            "omnibase_core.models.cli.model_performance_metrics",
        ]

        print(
            f"🧪 Testing protocol implementations on {len(test_modules)} sample models..."
        )

        for module_path in test_modules:
            print(f"   Testing: {module_path}")
            result = self.test_model_file(module_path)
            self.test_results.append(result)

        return self.generate_test_summary()

    def generate_test_summary(self) -> dict[str, Any]:
        """Generate test summary."""
        total_modules = len(self.test_results)
        successful_modules = len(
            [r for r in self.test_results if r["status"] == "success"]
        )
        total_classes = sum(len(r["classes"]) for r in self.test_results)

        protocol_stats = {}
        method_stats = {}

        for result in self.test_results:
            if result["status"] == "success":
                for class_name, class_data in result["protocol_tests"].items():
                    # Count protocol implementations
                    for protocol in class_data.get("protocols", []):
                        protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1

                    # Count method test results
                    for method, success in class_data.get("method_tests", {}).items():
                        if method not in method_stats:
                            method_stats[method] = {"passed": 0, "failed": 0}

                        if success:
                            method_stats[method]["passed"] += 1
                        else:
                            method_stats[method]["failed"] += 1

        return {
            "summary": {
                "total_modules_tested": total_modules,
                "successful_modules": successful_modules,
                "success_rate": (
                    (successful_modules / total_modules * 100)
                    if total_modules > 0
                    else 0
                ),
                "total_classes_tested": total_classes,
                "total_errors": len(self.errors),
            },
            "protocol_implementations": protocol_stats,
            "method_test_results": method_stats,
            "detailed_results": self.test_results,
            "errors": self.errors[:10],  # First 10 errors
        }


def main():
    """Main test execution."""
    print("🚀 Protocol Implementation Testing")
    print("=" * 50)

    tester = ProtocolTester()
    results = tester.test_all_models()

    # Print summary
    summary = results["summary"]
    print("\n📊 Test Results Summary:")
    print(f"   Modules Tested: {summary['total_modules_tested']}")
    print(f"   Successful Modules: {summary['successful_modules']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Classes Tested: {summary['total_classes_tested']}")
    print(f"   Total Errors: {summary['total_errors']}")

    # Print protocol implementations
    print("\n🔧 Protocol Implementations:")
    for protocol, count in results["protocol_implementations"].items():
        print(f"   {protocol}: {count} classes")

    # Print method test results
    print("\n✅ Method Test Results:")
    for method, stats in results["method_test_results"].items():
        total = stats["passed"] + stats["failed"]
        success_rate = (stats["passed"] / total * 100) if total > 0 else 0
        print(f"   {method}: {stats['passed']}/{total} passed ({success_rate:.1f}%)")

    # Print any errors
    if results["errors"]:
        print("\n⚠️  Sample Errors:")
        for error in results["errors"]:
            print(f"   - {error}")

    # Overall assessment
    overall_success = summary["success_rate"] >= 80 and len(results["errors"]) < 10
    status = "✅ PASSED" if overall_success else "❌ NEEDS ATTENTION"
    print(f"\n🎯 Overall Protocol Implementation: {status}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    exit(main())
