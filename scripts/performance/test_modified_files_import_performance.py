#!/usr/bin/env python3
"""
Import performance tests for modified files.

Tests the import performance of files that have been modified for ONEX compliance
to ensure changes don't negatively impact module loading times.
"""

import importlib
import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean, median, stdev
from typing import Dict, List, Tuple

# Add src to Python path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class ImportPerformanceTester:
    """Test import performance of modified files."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.src_root = self.project_root / "src"

        # Files that were modified based on git status
        self.modified_files = [
            "src/omnibase_core/models/infrastructure/model_result.py",
            "src/omnibase_core/models/infrastructure/model_timeout.py",
            "src/omnibase_core/models/metadata/model_semver.py",
            "src/omnibase_core/models/utils/model_yaml_value.py",
            "src/omnibase_core/utils/safe_yaml_loader.py",
            "scripts/intelligence/intelligence_hook.py",
        ]

    def get_module_name_from_file(self, file_path: str) -> str:
        """Convert file path to Python module name."""
        file_path = file_path.replace("src/", "").replace("/", ".").replace(".py", "")
        return file_path

    def time_import(
        self, module_name: str, iterations: int = 10
    ) -> Tuple[List[float], bool]:
        """Time module import over multiple iterations."""
        import_times = []
        successful_imports = 0

        for _ in range(iterations):
            # Clear module from cache if present
            if module_name in sys.modules:
                del sys.modules[module_name]

            try:
                start_time = time.perf_counter()
                importlib.import_module(module_name)
                end_time = time.perf_counter()

                import_time = end_time - start_time
                import_times.append(import_time)
                successful_imports += 1

            except Exception as e:
                print(f"   ⚠️  Failed to import {module_name}: {e}")
                continue

        success_rate = successful_imports / iterations
        return import_times, success_rate >= 0.8

    def test_baseline_imports(self) -> Dict[str, float]:
        """Test baseline import times for common modules."""
        print("📏 Testing baseline import performance...")

        baseline_modules = ["json", "pathlib", "typing", "datetime", "dataclasses"]

        baselines = {}
        for module in baseline_modules:
            times, success = self.time_import(module, 5)
            if success and times:
                avg_time = mean(times)
                baselines[module] = avg_time
                print(f"   {module}: {avg_time:.4f}s")

        return baselines

    def test_modified_file_imports(self) -> List[Dict]:
        """Test import performance of modified files."""
        print("\n🔍 Testing modified file import performance...")

        results = []

        for file_path in self.modified_files:
            if not file_path.startswith("src/"):
                print(f"   ⏭️  Skipping {file_path} (not a Python module)")
                continue

            module_name = self.get_module_name_from_file(file_path)
            print(f"   Testing {module_name}...")

            try:
                times, success = self.time_import(module_name, 5)

                if success and times:
                    result = {
                        "file_path": file_path,
                        "module_name": module_name,
                        "times": times,
                        "avg_time": mean(times),
                        "median_time": median(times),
                        "std_dev": stdev(times) if len(times) > 1 else 0.0,
                        "min_time": min(times),
                        "max_time": max(times),
                        "success": True,
                    }
                else:
                    result = {
                        "file_path": file_path,
                        "module_name": module_name,
                        "times": [],
                        "avg_time": 0.0,
                        "median_time": 0.0,
                        "std_dev": 0.0,
                        "min_time": 0.0,
                        "max_time": 0.0,
                        "success": False,
                    }

                results.append(result)

            except Exception as e:
                print(f"   ❌ Error testing {module_name}: {e}")
                results.append(
                    {
                        "file_path": file_path,
                        "module_name": module_name,
                        "times": [],
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def analyze_import_performance(
        self, results: List[Dict], baselines: Dict[str, float]
    ):
        """Analyze import performance results."""
        print("\n📊 Import Performance Analysis:")
        print("=" * 70)
        print(f"{'Module':<40} {'Avg Time':<10} {'Status'}")
        print("-" * 70)

        # Calculate baseline average for comparison
        baseline_avg = mean(baselines.values()) if baselines else 0.01

        slow_imports = []
        fast_imports = []
        failed_imports = []

        for result in results:
            if not result["success"]:
                failed_imports.append(result)
                status = "❌ FAILED"
                avg_time_str = "N/A"
            else:
                avg_time = result["avg_time"]
                avg_time_str = f"{avg_time:.4f}s"

                if avg_time > baseline_avg * 5:  # 5x slower than baseline
                    slow_imports.append(result)
                    status = "🐌 SLOW"
                elif avg_time > baseline_avg * 2:  # 2x slower than baseline
                    status = "⚠️  MODERATE"
                else:
                    fast_imports.append(result)
                    status = "✅ FAST"

            module_short = (
                result["module_name"].split(".")[-1]
                if "." in result["module_name"]
                else result["module_name"]
            )
            print(f"{module_short:<40} {avg_time_str:<10} {status}")

        # Analysis summary
        print(f"\n🎯 Import Performance Summary:")
        print(f"   Fast imports: {len(fast_imports)}")
        print(f"   Slow imports: {len(slow_imports)}")
        print(f"   Failed imports: {len(failed_imports)}")

        if baselines:
            print(f"   Baseline average: {baseline_avg:.4f}s")

        # Recommendations
        print(f"\n💡 Recommendations:")
        if slow_imports:
            print(f"   ⚠️  {len(slow_imports)} slow imports detected:")
            for imp in slow_imports:
                print(f"      - {imp['module_name']}: {imp['avg_time']:.4f}s")
                print(f"        Consider lazy imports or reducing dependencies")

        if failed_imports:
            print(f"   ❌ {len(failed_imports)} failed imports:")
            for imp in failed_imports:
                print(f"      - {imp['module_name']}")
                if "error" in imp:
                    print(f"        Error: {imp['error']}")

        return {
            "fast_count": len(fast_imports),
            "slow_count": len(slow_imports),
            "failed_count": len(failed_imports),
            "total_avg_time": (
                mean([r["avg_time"] for r in results if r["success"]])
                if results
                else 0.0
            ),
        }

    def test_circular_import_impact(self):
        """Test the performance impact of circular imports."""
        print(f"\n🔄 Testing circular import impact...")

        # Try to import modules known to have circular imports
        circular_modules = [
            "omnibase_core.exceptions.onex_error",
            "omnibase_core.models.common.model_error_context",
            "omnibase_core.models.common.model_numeric_value",
        ]

        for module_name in circular_modules:
            print(f"   Testing {module_name}...")
            try:
                times, success = self.time_import(module_name, 3)
                if success:
                    avg_time = mean(times)
                    print(f"     Import time: {avg_time:.4f}s")
                    if avg_time > 0.1:
                        print(
                            f"     ⚠️  Slow import may be due to circular dependencies"
                        )
                else:
                    print(
                        f"     ❌ Import failed - likely due to circular dependencies"
                    )
            except Exception as e:
                print(f"     ❌ Import error: {e}")

    def test_lazy_import_opportunities(self):
        """Identify opportunities for lazy importing."""
        print(f"\n🔄 Analyzing lazy import opportunities...")

        # Check if imports can be deferred
        opportunities = []

        for file_path in self.modified_files:
            if file_path.startswith("src/"):
                full_path = self.project_root / file_path
                if full_path.exists():
                    try:
                        with open(full_path, "r") as f:
                            content = f.read()

                        # Look for imports at module level that could be moved to function level
                        lines = content.split("\n")
                        for i, line in enumerate(lines[:20]):  # Check first 20 lines
                            if line.strip().startswith("from ") and "import" in line:
                                if "Exception" in line or "Error" in line:
                                    opportunities.append(
                                        {
                                            "file": file_path,
                                            "line": i + 1,
                                            "import": line.strip(),
                                            "reason": "Exception imports can often be lazy",
                                        }
                                    )

                    except Exception as e:
                        print(f"   ⚠️  Error analyzing {file_path}: {e}")

        if opportunities:
            print(f"   Found {len(opportunities)} lazy import opportunities:")
            for opp in opportunities[:5]:  # Show first 5
                print(f"     {opp['file']}:{opp['line']} - {opp['reason']}")
        else:
            print(f"   No obvious lazy import opportunities found")

    def run_comprehensive_import_test(self):
        """Run comprehensive import performance tests."""
        print("🚀 Comprehensive Import Performance Testing")
        print("=" * 60)

        # Test baselines
        baselines = self.test_baseline_imports()

        # Test modified files
        results = self.test_modified_file_imports()

        # Analyze results
        analysis = self.analyze_import_performance(results, baselines)

        # Test circular import impact
        self.test_circular_import_impact()

        # Test lazy import opportunities
        self.test_lazy_import_opportunities()

        # Save detailed results
        results_file = Path("import_performance_results.txt")
        with open(results_file, "w") as f:
            f.write("IMPORT PERFORMANCE TEST RESULTS\n")
            f.write("=" * 40 + "\n\n")

            f.write("BASELINES:\n")
            for module, time_val in baselines.items():
                f.write(f"  {module}: {time_val:.4f}s\n")

            f.write(f"\nMODIFIED FILES:\n")
            for result in results:
                f.write(f"\n{result['module_name']}\n")
                f.write(f"  File: {result['file_path']}\n")
                if result["success"]:
                    f.write(f"  Average time: {result['avg_time']:.4f}s\n")
                    f.write(f"  Min time: {result['min_time']:.4f}s\n")
                    f.write(f"  Max time: {result['max_time']:.4f}s\n")
                else:
                    f.write(f"  FAILED TO IMPORT\n")

            f.write(f"\nSUMMARY:\n")
            f.write(f"  Fast imports: {analysis['fast_count']}\n")
            f.write(f"  Slow imports: {analysis['slow_count']}\n")
            f.write(f"  Failed imports: {analysis['failed_count']}\n")
            f.write(f"  Average import time: {analysis['total_avg_time']:.4f}s\n")

        print(f"\n💾 Detailed results saved to: {results_file}")

        return analysis


def main():
    """Main import performance testing entry point."""
    tester = ImportPerformanceTester()
    analysis = tester.run_comprehensive_import_test()

    # Overall assessment
    print(f"\n🎯 Overall Import Performance Assessment:")
    if analysis["failed_count"] > 0:
        print(
            f"   ❌ {analysis['failed_count']} imports are failing - fix circular dependencies"
        )
    if analysis["slow_count"] > 0:
        print(
            f"   ⚠️  {analysis['slow_count']} imports are slow - consider optimization"
        )
    if analysis["fast_count"] > 0:
        print(f"   ✅ {analysis['fast_count']} imports are performing well")

    return analysis


if __name__ == "__main__":
    main()
