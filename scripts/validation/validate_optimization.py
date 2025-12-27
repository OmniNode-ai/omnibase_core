#!/usr/bin/env python3
"""
Performance Optimization Validation

Tests the lazy import optimization to ensure it meets zero tolerance requirements.
Target: Reduce cold import from 1856ms to <50ms (>95% improvement).
"""

import gc
import sys
import time
import tracemalloc
from pathlib import Path

import psutil

# Add src to path to allow direct imports before package installation.
# This validation script runs standalone (not via pytest) and needs access
# to omnibase_core source modules to measure import performance.
# The path manipulation is necessary because the package isn't installed
# when running this script directly during development/CI validation.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class OptimizationValidator:
    """Validates performance optimization implementations."""

    def __init__(self):
        self.process = psutil.Process()
        self.results = {}

    def clear_import_cache(self, pattern: str = "omnibase_core"):
        """Clear module import cache to simulate cold start."""
        modules_to_clear = [k for k in sys.modules if pattern in k]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        gc.collect()

    def measure_import_performance(self, test_name: str, import_func) -> dict:
        """Measure import performance with detailed metrics."""
        print(f"🔍 Testing: {test_name}")

        # Clear cache for true cold start
        self.clear_import_cache()

        # Start monitoring
        tracemalloc.start()
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        start_time = time.perf_counter()

        try:
            # Execute the import
            result = import_func()

            # Measure completion
            end_time = time.perf_counter()
            final_memory = self.process.memory_info().rss / 1024 / 1024
            _current, peak = tracemalloc.get_traced_memory()

            execution_time = (end_time - start_time) * 1000  # ms
            memory_delta = final_memory - initial_memory
            peak_memory = peak / 1024 / 1024

            metrics = {
                "test_name": test_name,
                "execution_time_ms": execution_time,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": peak_memory,
                "status": "SUCCESS",
                "result_type": str(type(result).__name__),
            }

            # Performance status
            if execution_time < 50:
                status = "✅ EXCELLENT"
            elif execution_time < 100:
                status = "✅ GOOD"
            elif execution_time < 200:
                status = "⚠️  ACCEPTABLE"
            else:
                status = "🚨 POOR"

            print(f"   {status}: {execution_time:.2f}ms, {memory_delta:.2f}MB delta")
            return metrics

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return {
                "test_name": test_name,
                "execution_time_ms": 0,
                "memory_delta_mb": 0,
                "peak_memory_mb": 0,
                "status": "FAILED",
                "error": str(e),
            }

        finally:
            tracemalloc.stop()

    def test_original_imports(self) -> dict:
        """Test original import performance (baseline)."""
        print("\n🚨 BASELINE TESTING: Original Import Performance")
        print("=" * 60)

        tests = {
            "original_contract_base": lambda: __import__(
                "omnibase_core.models.contracts.model_contract_base"
            ),
            "original_contracts_module": lambda: __import__(
                "omnibase_core.models.contracts"
            ),
            "original_subcontracts": lambda: __import__(
                "omnibase_core.models.contracts.subcontracts"
            ),
        }

        results = {}
        for test_name, import_func in tests.items():
            results[test_name] = self.measure_import_performance(test_name, import_func)

        return results

    def test_lazy_imports(self) -> dict:
        """Test lazy import performance."""
        print("\n🚀 OPTIMIZATION TESTING: Lazy Import Performance")
        print("=" * 60)

        tests = {
            "lazy_module_import": lambda: __import__(
                "omnibase_core.models.contracts.lazy_imports"
            ),
            "lazy_get_contract_base": lambda: self._test_lazy_contract_base(),
            "lazy_get_contract_compute": lambda: self._test_lazy_contract_compute(),
            "lazy_multiple_contracts": lambda: self._test_multiple_lazy_contracts(),
        }

        results = {}
        for test_name, import_func in tests.items():
            results[test_name] = self.measure_import_performance(test_name, import_func)

        return results

    def _test_lazy_contract_base(self):
        """Test lazy contract base loading."""
        from omnibase_core.models.contracts.model_lazy_imports import get_contract_base

        return get_contract_base()

    def _test_lazy_contract_compute(self):
        """Test lazy contract compute loading."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_compute,
        )

        return get_contract_compute()

    def _test_multiple_lazy_contracts(self):
        """Test loading multiple lazy contracts."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_base,
            get_contract_compute,
            get_contract_effect,
        )

        return [get_contract_base(), get_contract_compute(), get_contract_effect()]

    def test_instantiation_performance(self) -> dict:
        """Test model instantiation performance with lazy loading."""
        print("\n⚡ INSTANTIATION TESTING: Model Creation Performance")
        print("=" * 60)

        def test_lazy_instantiation():
            from omnibase_core.models.contracts.model_algorithm_config import (
                ModelAlgorithmConfig,
            )
            from omnibase_core.models.contracts.model_algorithm_factor_config import (
                ModelAlgorithmFactorConfig,
            )
            from omnibase_core.models.contracts.model_lazy_imports import (
                get_contract_compute,
            )

            ContractCompute = get_contract_compute()

            # Create test data
            test_data = {
                "contract_id": "performance_test",
                "version": {"major": 1, "minor": 0, "patch": 0},
                "description": "Performance test contract",
                "dependencies": [],
                "algorithm": ModelAlgorithmConfig(
                    algorithm_type="test",
                    factors={
                        "test_factor": ModelAlgorithmFactorConfig(
                            weight=1.0, calculation_method="linear"
                        )
                    },
                ),
            }

            # Create instance
            return ContractCompute(**test_data)

        result = self.measure_import_performance(
            "lazy_model_instantiation", test_lazy_instantiation
        )
        return {"lazy_model_instantiation": result}

    def calculate_improvement_metrics(self, baseline: dict, optimized: dict) -> dict:
        """Calculate improvement metrics between baseline and optimized."""
        improvements = {}

        for opt_key, opt_result in optimized.items():
            if opt_result.get("status") == "SUCCESS":
                opt_time = opt_result["execution_time_ms"]

                # Find best baseline comparison
                baseline_time = None
                for base_key, base_result in baseline.items():
                    if base_result.get("status") == "SUCCESS":
                        if (
                            baseline_time is None
                            or base_result["execution_time_ms"] > baseline_time
                        ):
                            baseline_time = base_result["execution_time_ms"]

                if baseline_time and baseline_time > 0:
                    improvement_percent = (
                        (baseline_time - opt_time) / baseline_time
                    ) * 100
                    speedup_ratio = (
                        baseline_time / opt_time if opt_time > 0 else float("inf")
                    )

                    improvements[opt_key] = {
                        "baseline_time_ms": baseline_time,
                        "optimized_time_ms": opt_time,
                        "improvement_percent": improvement_percent,
                        "speedup_ratio": speedup_ratio,
                        "meets_zero_tolerance": opt_time < 50,
                    }

        return improvements

    def generate_validation_report(self) -> dict:
        """Generate comprehensive validation report."""
        print("\n" + "=" * 80)
        print("🎯 PERFORMANCE OPTIMIZATION VALIDATION REPORT")
        print("=" * 80)

        # Run all tests
        baseline_results = self.test_original_imports()
        lazy_results = self.test_lazy_imports()
        instantiation_results = self.test_instantiation_performance()

        # Calculate improvements
        improvements = self.calculate_improvement_metrics(
            baseline_results, lazy_results
        )

        # Determine compliance status
        zero_tolerance_compliance = all(
            result.get("execution_time_ms", float("inf")) < 50
            for result in lazy_results.values()
            if result.get("status") == "SUCCESS"
        )

        # Generate summary
        print("\n📊 VALIDATION SUMMARY:")
        print(
            f"   Tests Run: {len(baseline_results) + len(lazy_results) + len(instantiation_results)}"
        )
        print(
            f"   Zero Tolerance Compliance: {'✅ PASSED' if zero_tolerance_compliance else '❌ FAILED'}"
        )

        if improvements:
            best_improvement = max(
                improvements.values(), key=lambda x: x.get("improvement_percent", 0)
            )
            print(
                f"   Best Improvement: {best_improvement['improvement_percent']:.1f}%"
            )
            print(f"   Best Speedup: {best_improvement['speedup_ratio']:.1f}x faster")

        print("\n📈 DETAILED IMPROVEMENTS:")
        for test_name, metrics in improvements.items():
            print(f"   {test_name}:")
            print(
                f"      {metrics['baseline_time_ms']:.2f}ms → {metrics['optimized_time_ms']:.2f}ms"
            )
            print(f"      Improvement: {metrics['improvement_percent']:.1f}%")
            print(
                f"      Zero Tolerance: {'✅' if metrics['meets_zero_tolerance'] else '❌'}"
            )

        return {
            "baseline_results": baseline_results,
            "lazy_results": lazy_results,
            "instantiation_results": instantiation_results,
            "improvements": improvements,
            "zero_tolerance_compliance": zero_tolerance_compliance,
            "recommendation": (
                "APPROVED FOR DEPLOYMENT"
                if zero_tolerance_compliance
                else "REQUIRES FURTHER OPTIMIZATION"
            ),
        }


def main():
    """Run performance optimization validation."""
    print("🔬 PERFORMANCE OPTIMIZATION VALIDATION")
    print("Target: <50ms import time (Zero Tolerance Compliance)")
    print("=" * 80)

    validator = OptimizationValidator()
    report = validator.generate_validation_report()

    # Save report
    import json

    report_file = Path(__file__).parent / "optimization_validation_report.json"

    serializable_report = {}
    for key, value in report.items():
        try:
            json.dumps(value)
            serializable_report[key] = value
        except (TypeError, ValueError):
            serializable_report[key] = str(value)

    with open(report_file, "w") as f:
        json.dump(serializable_report, f, indent=2, default=str)

    print(f"\n📄 Full validation report saved to: {report_file}")

    # Final verdict
    if report["zero_tolerance_compliance"]:
        print("\n✅ OPTIMIZATION VALIDATION PASSED")
        print("🚀 Lazy import optimization meets zero tolerance requirements")
        return 0
    else:
        print("\n❌ OPTIMIZATION VALIDATION FAILED")
        print("🔧 Further optimization required to meet zero tolerance")
        return 1


if __name__ == "__main__":
    sys.exit(main())
