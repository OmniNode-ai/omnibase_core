#!/usr/bin/env python3
"""
Focused Performance Test for PR #36 - Corrected Import Paths

This script validates the specific performance improvements from PR #36:
1. Lazy loading effectiveness
2. Memory usage optimization
3. Contract model validation performance
4. Import chain analysis

Using correct import paths based on actual project structure.
"""

import gc
import json
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List


class PR36PerformanceValidator:
    """Focused performance validation for PR #36 improvements"""

    def __init__(self):
        self.results = {}
        self.baseline_import_time = 1856.0  # ms - mentioned baseline

        # Performance targets
        self.targets = {
            "import_time_ms": 5.0,
            "memory_overhead_mb": 10.0,
            "validation_time_ms": 100.0,
        }

    def measure_time_ms(self, func):
        """Measure execution time in milliseconds"""
        start = time.perf_counter()
        result = func()
        end = time.perf_counter()
        return (end - start) * 1000, result

    def measure_memory_mb(self, func):
        """Measure memory usage in MB"""
        tracemalloc.start()
        gc.collect()
        start_memory = tracemalloc.get_traced_memory()[0]

        result = func()

        current, peak = tracemalloc.get_traced_memory()
        memory_used = (current - start_memory) / (1024 * 1024)
        tracemalloc.stop()

        return memory_used, result

    def test_1_lazy_loading_effectiveness(self):
        """Test 1: Validate lazy loading import performance"""
        print("🔍 Test 1: Lazy Loading Import Performance")

        # Clear any existing imports
        modules_to_clear = [
            k for k in sys.modules.keys() if k.startswith("omnibase_core")
        ]
        for module in modules_to_clear:
            del sys.modules[module]

        # Test cold import (without accessing validation functions)
        cold_import_time, _ = self.measure_time_ms(lambda: __import__("omnibase_core"))

        print(f"   Cold import time: {cold_import_time:.2f}ms")

        # Test accessing validation functions (should trigger lazy loading)
        def access_validation():
            from omnibase_core import validate_architecture

            return validate_architecture

        lazy_load_time, _ = self.measure_time_ms(access_validation)
        print(f"   Lazy load time: {lazy_load_time:.2f}ms")

        # Test subsequent access (should be cached)
        cached_access_time, _ = self.measure_time_ms(access_validation)
        print(f"   Cached access time: {cached_access_time:.2f}ms")

        # Calculate improvement
        improvement = (
            (self.baseline_import_time - cold_import_time) / self.baseline_import_time
        ) * 100

        self.results["lazy_loading"] = {
            "cold_import_ms": cold_import_time,
            "lazy_load_ms": lazy_load_time,
            "cached_access_ms": cached_access_time,
            "baseline_ms": self.baseline_import_time,
            "improvement_percent": improvement,
            "meets_target": cold_import_time < self.targets["import_time_ms"],
        }

        print(f"   ✅ Improvement: {improvement:.1f}% vs baseline")
        print(
            f"   {'✅' if cold_import_time < self.targets['import_time_ms'] else '❌'} Target: <{self.targets['import_time_ms']}ms"
        )
        print()

    def test_2_memory_optimization(self):
        """Test 2: Memory usage optimization"""
        print("🧠 Test 2: Memory Usage Optimization")

        # Measure baseline memory
        gc.collect()
        import psutil

        process = psutil.Process()
        baseline_memory = process.memory_info().rss / (1024 * 1024)

        # Test memory of basic import
        def basic_import():
            if "omnibase_core" in sys.modules:
                del sys.modules["omnibase_core"]
            import omnibase_core

            return omnibase_core

        basic_memory, _ = self.measure_memory_mb(basic_import)
        print(f"   Basic import memory: {basic_memory:.2f}MB")

        # Test memory with validation functions loaded
        def load_validation():
            from omnibase_core import validate_architecture, validate_union_usage

            return validate_architecture, validate_union_usage

        validation_memory, _ = self.measure_memory_mb(load_validation)
        print(f"   Validation functions memory: {validation_memory:.2f}MB")

        self.results["memory_usage"] = {
            "baseline_mb": baseline_memory,
            "basic_import_mb": basic_memory,
            "validation_functions_mb": validation_memory,
            "meets_basic_target": basic_memory < self.targets["memory_overhead_mb"],
            "meets_validation_target": validation_memory
            < 20.0,  # Allow more for validation
        }

        print(
            f"   {'✅' if basic_memory < self.targets['memory_overhead_mb'] else '❌'} Basic import target: <{self.targets['memory_overhead_mb']}MB"
        )
        print(
            f"   {'✅' if validation_memory < 20.0 else '❌'} Validation target: <20MB"
        )
        print()

    def test_3_contract_model_performance(self):
        """Test 3: Contract model validation performance"""
        print("⚡ Test 3: Contract Model Validation Performance")

        try:
            # Test different import paths to find the correct ones
            model_imports = [
                (
                    "omnibase_core.models.contracts.model_algorithm_config",
                    "ModelAlgorithmConfig",
                ),
                (
                    "omnibase_core.models.contracts.model_parallel_config",
                    "ModelParallelConfig",
                ),
                (
                    "omnibase_core.models.contracts.subcontracts.model_configuration_subcontract",
                    "ModelConfigurationSubcontract",
                ),
            ]

            successful_imports = []
            validation_results = []

            for module_path, class_name in model_imports:
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    model_class = getattr(module, class_name)
                    successful_imports.append((module_path, class_name, model_class))
                    print(f"   ✅ Successfully imported {class_name}")
                except (ImportError, AttributeError) as e:
                    print(f"   ❌ Failed to import {class_name}: {e}")
                    continue

            # Test validation performance on successfully imported models
            if successful_imports:
                for module_path, class_name, model_class in successful_imports[
                    :2
                ]:  # Test first 2 to keep it reasonable
                    try:
                        # Create test data based on model requirements
                        if "AlgorithmConfig" in class_name:
                            test_data = {
                                "name": "performance_test_algorithm",
                                "description": "Testing validation performance",
                            }
                        elif "ParallelConfig" in class_name:
                            test_data = {"max_workers": 4, "strategy": "default"}
                        else:
                            test_data = {}

                        # Measure single validation
                        def single_validation():
                            return model_class(**test_data)

                        single_time, _ = self.measure_time_ms(single_validation)

                        # Measure batch validation
                        def batch_validation():
                            return [model_class(**test_data) for _ in range(10)]

                        batch_time, _ = self.measure_time_ms(batch_validation)

                        validation_results.append(
                            {
                                "model": class_name,
                                "single_validation_ms": single_time,
                                "batch_10_validation_ms": batch_time,
                                "avg_validation_ms": batch_time / 10,
                            }
                        )

                        print(f"   📊 {class_name}:")
                        print(f"      Single: {single_time:.2f}ms")
                        print(f"      Batch (10): {batch_time:.2f}ms")
                        print(f"      Average: {batch_time/10:.2f}ms")

                    except Exception as e:
                        print(f"   ❌ Validation test failed for {class_name}: {e}")
                        continue

            self.results["contract_validation"] = {
                "successful_imports": len(successful_imports),
                "total_attempted": len(model_imports),
                "validation_results": validation_results,
                "meets_performance_target": (
                    all(
                        r["avg_validation_ms"] < self.targets["validation_time_ms"]
                        for r in validation_results
                    )
                    if validation_results
                    else False
                ),
            }

            if validation_results:
                avg_validation = sum(
                    r["avg_validation_ms"] for r in validation_results
                ) / len(validation_results)
                print(f"   📈 Average validation time: {avg_validation:.2f}ms")
                print(
                    f"   {'✅' if avg_validation < self.targets['validation_time_ms'] else '❌'} Target: <{self.targets['validation_time_ms']}ms"
                )
            else:
                print(f"   ⚠️ No models could be validated")

        except Exception as e:
            print(f"   ❌ Contract model test failed: {e}")
            self.results["contract_validation"] = {"error": str(e)}

        print()

    def test_4_import_chain_analysis(self):
        """Test 4: Import chain and dependency analysis"""
        print("📊 Test 4: Import Chain Analysis")

        # Test import times of various modules
        test_modules = [
            "omnibase_core",
            "omnibase_core.models",
            "omnibase_core.models.contracts",
            "omnibase_core.enums",
            "omnibase_core.types",
            "omnibase_core.utils",
        ]

        import_times = {}

        for module_name in test_modules:
            # Clear module if already imported
            if module_name in sys.modules:
                del sys.modules[module_name]

            try:
                import_time, _ = self.measure_time_ms(lambda: __import__(module_name))
                import_times[module_name] = import_time
                print(f"   📦 {module_name}: {import_time:.2f}ms")
            except ImportError as e:
                print(f"   ❌ {module_name}: Failed to import - {e}")
                import_times[module_name] = None

        # Analyze import depth using module count
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; import omnibase_core; print(len([m for m in sys.modules if m.startswith('omnibase_core')]))",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            module_count = (
                int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            )
            print(f"   📚 Total omnibase_core modules loaded: {module_count}")
        except:
            module_count = 0

        successful_imports = sum(1 for t in import_times.values() if t is not None)
        avg_import_time = (
            sum(t for t in import_times.values() if t is not None) / successful_imports
            if successful_imports > 0
            else 0
        )

        self.results["import_chain"] = {
            "import_times": import_times,
            "module_count": module_count,
            "successful_imports": successful_imports,
            "average_import_time": avg_import_time,
            "meets_target": avg_import_time < 10.0,  # 10ms average target
        }

        print(f"   📈 Average import time: {avg_import_time:.2f}ms")
        print(f"   {'✅' if avg_import_time < 10.0 else '❌'} Target: <10ms average")
        print()

    def run_all_tests(self):
        """Run all performance tests"""
        print("🚀 PR #36 Performance Validation - Focused Test Suite")
        print("=" * 60)

        self.test_1_lazy_loading_effectiveness()
        self.test_2_memory_optimization()
        self.test_3_contract_model_performance()
        self.test_4_import_chain_analysis()

        return self.results

    def generate_summary(self):
        """Generate a summary of all test results"""
        print("📊 PERFORMANCE VALIDATION SUMMARY")
        print("=" * 60)

        # Overall assessment
        tests_passed = 0
        total_tests = 0

        # Lazy loading assessment
        if "lazy_loading" in self.results:
            total_tests += 1
            if self.results["lazy_loading"]["meets_target"]:
                tests_passed += 1
                print(
                    f"✅ Lazy Loading: PASSED ({self.results['lazy_loading']['improvement_percent']:.1f}% improvement)"
                )
            else:
                print(f"❌ Lazy Loading: FAILED")

        # Memory assessment
        if "memory_usage" in self.results:
            total_tests += 1
            if self.results["memory_usage"]["meets_basic_target"]:
                tests_passed += 1
                print(f"✅ Memory Usage: PASSED")
            else:
                print(f"❌ Memory Usage: FAILED")

        # Contract validation assessment
        if "contract_validation" in self.results:
            total_tests += 1
            if self.results["contract_validation"].get(
                "meets_performance_target", False
            ):
                tests_passed += 1
                print(f"✅ Contract Validation: PASSED")
            else:
                print(f"⚠️ Contract Validation: PARTIAL (some imports failed)")

        # Import chain assessment
        if "import_chain" in self.results:
            total_tests += 1
            if self.results["import_chain"]["meets_target"]:
                tests_passed += 1
                print(f"✅ Import Chain: PASSED")
            else:
                print(f"❌ Import Chain: FAILED")

        pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0
        overall_status = (
            "PASSED"
            if tests_passed == total_tests
            else "PARTIAL" if tests_passed > 0 else "FAILED"
        )

        print(f"\n🎯 OVERALL STATUS: {overall_status}")
        print(f"📈 Pass Rate: {pass_rate:.1f}% ({tests_passed}/{total_tests})")

        # Key improvements
        if "lazy_loading" in self.results:
            print(f"\n🔥 KEY IMPROVEMENT:")
            print(
                f"   Import time: {self.baseline_import_time}ms → {self.results['lazy_loading']['cold_import_ms']:.2f}ms"
            )
            print(
                f"   Performance gain: {self.results['lazy_loading']['improvement_percent']:.1f}%"
            )

        return overall_status, pass_rate

    def save_detailed_report(self, filename="pr36_focused_performance_report.json"):
        """Save detailed results to JSON file"""
        report = {
            "pr36_performance_validation": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "baseline_import_ms": self.baseline_import_time,
                "targets": self.targets,
                "results": self.results,
                "summary": {
                    "overall_status": self.generate_summary()[0],
                    "pass_rate": self.generate_summary()[1],
                },
            }
        }

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Detailed report saved: {filename}")
        return filename


def main():
    """Run the focused performance validation"""
    validator = PR36PerformanceValidator()

    # Run all tests
    results = validator.run_all_tests()

    # Generate summary
    overall_status, pass_rate = validator.generate_summary()

    # Save detailed report
    validator.save_detailed_report()

    # Return appropriate exit code
    return 0 if overall_status == "PASSED" else 1 if overall_status == "PARTIAL" else 2


if __name__ == "__main__":
    sys.exit(main())
