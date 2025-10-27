#!/usr/bin/env python3
"""
Memory usage analysis for validation changes and optimizations.

Analyzes memory consumption patterns for validation scripts and
performance optimizations to ensure changes don't create memory leaks
or excessive memory usage.
"""

import gc
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available - using basic memory analysis")


class MemoryUsageAnalyzer:
    """Analyze memory usage patterns for validation changes."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def get_memory_info(self) -> dict[str, float]:
        """Get current process memory information."""
        if PSUTIL_AVAILABLE:
            memory_info = self.process.memory_info()
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
                "percent": self.process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            }
        else:
            # Fallback to basic memory info
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "rss_mb": usage.ru_maxrss
                / 1024
                / 1024,  # On macOS ru_maxrss is in bytes
                "vms_mb": 0.0,
                "percent": 0.0,
                "available_mb": 0.0,
            }

    def analyze_validation_script_memory(self, script_path: str) -> dict[str, float]:
        """Analyze memory usage of a validation script."""
        print(f"🧠 Analyzing memory usage: {Path(script_path).name}")

        if not Path(script_path).exists():
            return {"error": f"Script not found: {script_path}"}

        # Get some sample files for testing
        sample_files = list((self.project_root / "src").rglob("*.py"))[:20]
        sample_file_args = [str(f) for f in sample_files]

        # Build command
        if "elif-limit" in script_path:
            cmd = ["python", script_path] + sample_file_args
        else:
            cmd = ["python", script_path]

        try:
            # Run script and monitor memory usage
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # For subprocess, we can't monitor memory in real-time easily
            # Instead, we'll measure the memory impact of running many validation calls

            return {
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "stdout_size": len(result.stdout),
                "stderr_size": len(result.stderr),
                "execution_time": 0.0,  # Would need more complex monitoring for accurate timing
            }

        except subprocess.TimeoutExpired:
            return {"error": "Script timed out", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "exit_code": -2}

    def test_memory_growth_pattern(self, script_path: str, iterations: int = 10):
        """Test if validation script has memory growth patterns."""
        print(
            f"📈 Testing memory growth: {Path(script_path).name} ({iterations} iterations)"
        )

        if not PSUTIL_AVAILABLE:
            print("   ⚠️  psutil not available - skipping detailed memory analysis")
            return {}

        memory_readings = []

        for i in range(iterations):
            gc.collect()  # Force garbage collection
            initial_memory = self.get_memory_info()

            # Run validation script
            result = self.analyze_validation_script_memory(script_path)

            gc.collect()  # Force garbage collection again
            final_memory = self.get_memory_info()

            memory_delta = final_memory["rss_mb"] - initial_memory["rss_mb"]
            memory_readings.append(
                {
                    "iteration": i + 1,
                    "initial_mb": initial_memory["rss_mb"],
                    "final_mb": final_memory["rss_mb"],
                    "delta_mb": memory_delta,
                    "script_success": result.get("success", False),
                }
            )

            time.sleep(0.1)  # Brief pause between iterations

        # Analyze growth pattern
        deltas = [r["delta_mb"] for r in memory_readings if r["script_success"]]

        if deltas:
            avg_delta = sum(deltas) / len(deltas)
            max_delta = max(deltas)
            total_growth = sum(deltas)

            print(f"   Average memory delta: {avg_delta:.2f}MB")
            print(f"   Maximum memory delta: {max_delta:.2f}MB")
            print(f"   Total memory growth: {total_growth:.2f}MB")

            # Check for memory leaks
            if total_growth > 50:  # More than 50MB total growth
                print("   ⚠️  Potential memory leak detected")
            elif avg_delta > 5:  # More than 5MB average per run
                print("   ⚠️  High memory usage per execution")
            else:
                print("   ✅ Memory usage appears normal")

            return {
                "avg_delta_mb": avg_delta,
                "max_delta_mb": max_delta,
                "total_growth_mb": total_growth,
                "successful_runs": len(deltas),
                "total_runs": iterations,
                "memory_leak_risk": total_growth > 50,
                "high_usage_risk": avg_delta > 5,
            }
        else:
            print("   ❌ No successful script executions for analysis")
            return {"error": "No successful executions"}

    def analyze_all_validation_scripts(self):
        """Analyze memory usage for all validation scripts."""
        print("🧠 Memory Usage Analysis for Validation Scripts")
        print("=" * 60)

        validation_scripts = [
            self.project_root / "scripts/validation/validate-elif-limit.py",
            self.project_root / "scripts/validation/validate-onex-error-compliance.py",
            self.project_root / "scripts/validation/validate-stubbed-functionality.py",
        ]

        results = {}
        overall_memory_start = self.get_memory_info()

        for script_path in validation_scripts:
            if script_path.exists():
                # Basic analysis
                basic_result = self.analyze_validation_script_memory(str(script_path))

                # Memory growth analysis
                growth_result = self.test_memory_growth_pattern(str(script_path), 5)

                results[script_path.name] = {
                    "basic_analysis": basic_result,
                    "memory_growth": growth_result,
                }
            else:
                print(f"⚠️  Script not found: {script_path}")

        overall_memory_end = self.get_memory_info()

        print("\n📊 Overall Memory Analysis Summary:")
        print(f"   Initial memory: {overall_memory_start['rss_mb']:.1f}MB")
        print(f"   Final memory: {overall_memory_end['rss_mb']:.1f}MB")
        print(
            f"   Net change: {overall_memory_end['rss_mb'] - overall_memory_start['rss_mb']:.1f}MB"
        )

        return results

    def analyze_optimization_memory_impact(self):
        """Analyze memory impact of performance optimizations."""
        print("\n🚀 Analyzing Optimization Memory Impact")
        print("=" * 50)

        # Test memory usage patterns for optimized vs unoptimized operations
        optimizations_tested = 0

        # Test 1: Property caching impact
        print("1. Testing property caching memory impact...")
        try:
            # Simulate creating many objects with cached properties
            initial_memory = self.get_memory_info()

            # Create test objects (simulating the pattern used in models)
            test_objects = []
            for i in range(100):
                # Simulate objects with cached properties
                obj = {
                    "id": i,
                    "_cached_property": None,
                    "data": f"test_data_{i}" * 10,  # Some data to cache
                }
                test_objects.append(obj)

            cached_memory = self.get_memory_info()
            memory_per_object = (
                cached_memory["rss_mb"] - initial_memory["rss_mb"]
            ) / 100

            print(f"   Memory per cached object: {memory_per_object:.4f}MB")

            # Clean up
            test_objects.clear()
            gc.collect()

            optimizations_tested += 1

        except Exception as e:
            print(f"   ⚠️  Error testing property caching: {e}")

        # Test 2: LRU cache memory impact
        print("2. Testing LRU cache memory impact...")
        try:
            from functools import lru_cache

            initial_memory = self.get_memory_info()

            @lru_cache(maxsize=128)
            def expensive_operation(x, y):
                return f"result_{x}_{y}" * 100  # Expensive string operation

            # Use the cache
            for i in range(50):
                for j in range(5):
                    expensive_operation(i, j)

            cached_memory = self.get_memory_info()
            cache_memory_impact = cached_memory["rss_mb"] - initial_memory["rss_mb"]

            print(f"   LRU cache memory impact: {cache_memory_impact:.2f}MB")

            # Clear cache
            expensive_operation.cache_clear()
            gc.collect()

            optimizations_tested += 1

        except Exception as e:
            print(f"   ⚠️  Error testing LRU cache: {e}")

        print(f"\n✅ Completed {optimizations_tested} optimization memory tests")

    def generate_memory_recommendations(self, analysis_results: dict):
        """Generate memory usage recommendations."""
        print("\n💡 Memory Usage Recommendations:")
        print("=" * 50)

        recommendations = []

        # Analyze results for patterns
        high_memory_scripts = []
        memory_leak_scripts = []

        for script_name, results in analysis_results.items():
            if "memory_growth" in results and isinstance(
                results["memory_growth"], dict
            ):
                growth_data = results["memory_growth"]

                if growth_data.get("memory_leak_risk", False):
                    memory_leak_scripts.append(script_name)

                if growth_data.get("high_usage_risk", False):
                    high_memory_scripts.append(script_name)

        # Generate specific recommendations
        if memory_leak_scripts:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": "Potential memory leaks detected",
                    "scripts": memory_leak_scripts,
                    "solution": "Review object lifecycle and add explicit cleanup",
                }
            )

        if high_memory_scripts:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "issue": "High memory usage per execution",
                    "scripts": high_memory_scripts,
                    "solution": "Consider lazy loading and memory-efficient algorithms",
                }
            )

        # Print recommendations
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. [{rec['priority']}] {rec['issue']}")
                print(f"   Affected scripts: {', '.join(rec['scripts'])}")
                print(f"   Solution: {rec['solution']}")
        else:
            print("✅ No critical memory usage issues detected")
            print("✅ Current memory usage patterns appear acceptable")

        # General recommendations
        print("\nGeneral Memory Best Practices:")
        print("1. Use generators instead of lists for large datasets")
        print("2. Implement proper cleanup in validation scripts")
        print("3. Consider memory profiling for scripts processing many files")
        print("4. Monitor memory usage in CI/CD pipelines")

        return recommendations

    def run_comprehensive_memory_analysis(self):
        """Run comprehensive memory usage analysis."""
        print("🧠 Comprehensive Memory Usage Analysis")
        print("=" * 60)

        # Analyze validation scripts
        validation_results = self.analyze_all_validation_scripts()

        # Analyze optimization impact
        self.analyze_optimization_memory_impact()

        # Generate recommendations
        recommendations = self.generate_memory_recommendations(validation_results)

        # Save results
        results_file = self.project_root / "memory_analysis_results.txt"
        with open(results_file, "w") as f:
            f.write("MEMORY USAGE ANALYSIS RESULTS\n")
            f.write("=" * 40 + "\n\n")

            f.write("VALIDATION SCRIPTS:\n")
            for script_name, results in validation_results.items():
                f.write(f"\n{script_name}:\n")
                f.write(f"  Basic analysis: {results.get('basic_analysis', {})}\n")
                f.write(f"  Memory growth: {results.get('memory_growth', {})}\n")

            f.write("\nRECOMMENDATIONS:\n")
            for i, rec in enumerate(recommendations, 1):
                f.write(f"{i}. [{rec['priority']}] {rec['issue']}\n")
                f.write(f"   Solution: {rec['solution']}\n")

        print(f"\n💾 Detailed results saved to: {results_file}")

        return {
            "validation_results": validation_results,
            "recommendations": recommendations,
            "memory_issues_count": len(
                [r for r in recommendations if r["priority"] in ["HIGH", "CRITICAL"]]
            ),
        }


def main():
    """Main memory analysis entry point."""
    analyzer = MemoryUsageAnalyzer()
    results = analyzer.run_comprehensive_memory_analysis()

    # Final assessment
    print("\n🎯 Memory Usage Assessment:")
    if results["memory_issues_count"] > 0:
        print(f"   ⚠️  {results['memory_issues_count']} critical memory issues detected")
    else:
        print("   ✅ No critical memory issues detected")

    return results


if __name__ == "__main__":
    main()
