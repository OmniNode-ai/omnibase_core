#!/usr/bin/env python3
"""
Performance tests for validation hook scripts.

Tests the execution time of validation hooks to ensure they don't slow down the development workflow.
"""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, stdev
from typing import List


@dataclass
class ValidationPerformanceResult:
    """Result of validation hook performance test."""

    script_name: str
    execution_times: list[float]
    avg_time: float
    median_time: float
    std_dev: float
    min_time: float
    max_time: float
    success_rate: float


class ValidationHookPerformanceTester:
    """Test performance of validation hooks."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.validation_scripts = [
            "scripts/validation/validate-elif-limit.py",
            "scripts/validation/validate-onex-error-compliance.py",
            "scripts/validation/validate-stubbed-functionality.py",
        ]

    def time_validation_script(
        self, script_path: str, iterations: int = 5
    ) -> ValidationPerformanceResult:
        """Time a validation script over multiple iterations."""
        print(f"⏱️  Testing {script_path} ({iterations} iterations)...")

        full_script_path = self.project_root / script_path
        if not full_script_path.exists():
            raise FileNotFoundError(f"Validation script not found: {full_script_path}")

        execution_times = []
        successful_runs = 0

        # Get some sample Python files to test with
        sample_files = list((self.project_root / "src").rglob("*.py"))[
            :10
        ]  # Use 10 sample files
        sample_file_args = [str(f) for f in sample_files]

        for i in range(iterations):
            try:
                start_time = time.perf_counter()

                # Build command based on script requirements
                if "elif-limit" in script_path:
                    # This script requires file arguments
                    cmd = ["python", str(full_script_path)] + sample_file_args
                else:
                    # These scripts can run without arguments (scan all files)
                    cmd = ["python", str(full_script_path)]

                # Run the validation script
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,  # 30 second timeout
                )

                end_time = time.perf_counter()
                execution_time = end_time - start_time
                execution_times.append(execution_time)

                if result.returncode == 0:
                    successful_runs += 1
                else:
                    print(
                        f"   ⚠️  Run {i+1} had non-zero exit code: {result.returncode}"
                    )
                    if result.stderr:
                        print(f"   Error: {result.stderr[:200]}...")

            except subprocess.TimeoutExpired:
                print(f"   ⚠️  Run {i+1} timed out after 30 seconds")
            except Exception as e:
                print(f"   ⚠️  Run {i+1} failed with exception: {e}")

        if not execution_times:
            return ValidationPerformanceResult(
                script_name=script_path,
                execution_times=[],
                avg_time=0.0,
                median_time=0.0,
                std_dev=0.0,
                min_time=0.0,
                max_time=0.0,
                success_rate=0.0,
            )

        return ValidationPerformanceResult(
            script_name=script_path,
            execution_times=execution_times,
            avg_time=mean(execution_times),
            median_time=median(execution_times),
            std_dev=stdev(execution_times) if len(execution_times) > 1 else 0.0,
            min_time=min(execution_times),
            max_time=max(execution_times),
            success_rate=successful_runs / iterations,
        )

    def test_all_validation_hooks(self) -> list[ValidationPerformanceResult]:
        """Test performance of all validation hooks."""
        print("🚀 Testing Validation Hook Performance")
        print("=" * 50)

        results = []

        for script_path in self.validation_scripts:
            try:
                result = self.time_validation_script(script_path)
                results.append(result)
            except Exception as e:
                print(f"❌ Failed to test {script_path}: {e}")

        return results

    def analyze_performance(self, results: list[ValidationPerformanceResult]):
        """Analyze validation hook performance and provide recommendations."""
        print("\n📊 Validation Hook Performance Results:")
        print("=" * 80)
        print(f"{'Script':<45} {'Avg Time':<10} {'Success':<8} {'Status'}")
        print("-" * 80)

        for result in results:
            if not result.execution_times:
                status = "❌ FAILED"
                avg_time_str = "N/A"
                success_str = "0%"
            else:
                avg_time_str = f"{result.avg_time:.3f}s"
                success_str = f"{result.success_rate*100:.0f}%"

                if result.avg_time > 10.0:
                    status = "🐌 VERY SLOW"
                elif result.avg_time > 5.0:
                    status = "⚠️  SLOW"
                elif result.avg_time > 2.0:
                    status = "⚡ MODERATE"
                else:
                    status = "✅ FAST"

            script_name = Path(result.script_name).name
            print(f"{script_name:<45} {avg_time_str:<10} {success_str:<8} {status}")

        print("\n🎯 Performance Analysis:")
        print("=" * 50)

        # Identify slow hooks
        slow_hooks = [r for r in results if r.execution_times and r.avg_time > 5.0]
        if slow_hooks:
            print("⚠️  SLOW VALIDATION HOOKS DETECTED:")
            for hook in slow_hooks:
                print(
                    f"   - {Path(hook.script_name).name}: {hook.avg_time:.3f}s average"
                )
                print("     Consider optimizing or running less frequently")

        # Check for failed hooks
        failed_hooks = [
            r for r in results if not r.execution_times or r.success_rate < 1.0
        ]
        if failed_hooks:
            print("\n❌ FAILING VALIDATION HOOKS:")
            for hook in failed_hooks:
                print(
                    f"   - {Path(hook.script_name).name}: {hook.success_rate*100:.0f}% success rate"
                )

        # Calculate total validation time
        total_time = sum(r.avg_time for r in results if r.execution_times)
        print(f"\n⏱️  Total validation time: {total_time:.3f}s")

        if total_time > 30:
            print(
                "   ⚠️  Total validation time is high - consider optimizing or parallelizing"
            )
        elif total_time > 15:
            print("   ⚡ Total validation time is moderate - monitor for growth")
        else:
            print("   ✅ Total validation time is acceptable")

        return {
            "total_time": total_time,
            "slow_hooks": len(slow_hooks),
            "failed_hooks": len(failed_hooks),
            "all_passing": len(failed_hooks) == 0,
            "performance_acceptable": total_time <= 30,
        }

    def test_validation_script_scaling(self, script_path: str):
        """Test how validation script performance scales with codebase size."""
        print(f"\n🔍 Testing scaling performance for {Path(script_path).name}")

        # Get current file counts
        src_files = list((self.project_root / "src").rglob("*.py"))
        test_files = list((self.project_root / "tests").rglob("*.py"))

        print(f"   Source files: {len(src_files)}")
        print(f"   Test files: {len(test_files)}")

        # Run single timing test
        result = self.time_validation_script(script_path, iterations=1)
        if result.execution_times:
            files_per_second = (len(src_files) + len(test_files)) / result.avg_time
            print(f"   Processing rate: {files_per_second:.0f} files/second")
            print(f"   Estimated time for 1000 files: {1000/files_per_second:.2f}s")

        return result


def main():
    """Main validation hook performance testing entry point."""
    tester = ValidationHookPerformanceTester()

    # Test all validation hooks
    results = tester.test_all_validation_hooks()

    # Analyze performance
    analysis = tester.analyze_performance(results)

    # Test scaling for key hooks
    if results:
        print("\n🚀 Testing scaling performance...")
        for result in results[:2]:  # Test first 2 hooks for scaling
            if result.execution_times:
                tester.test_validation_script_scaling(result.script_name)

    # Generate recommendations
    print("\n💡 Recommendations:")
    print("=" * 50)

    if analysis["performance_acceptable"]:
        print("✅ Validation hook performance is acceptable")
        print("✅ No immediate optimizations required")
    else:
        print("⚠️  Consider these optimizations:")
        print("   1. Implement caching for repeated file analysis")
        print("   2. Add early exit conditions for common cases")
        print("   3. Parallelize independent validation checks")
        print("   4. Consider running expensive validations only on CI")

    if not analysis["all_passing"]:
        print("❌ Fix failing validation hooks before deployment")

    # Save results to file
    results_file = Path("validation_performance_results.txt")
    with open(results_file, "w") as f:
        f.write("VALIDATION HOOK PERFORMANCE RESULTS\n")
        f.write("=" * 40 + "\n\n")

        f.write(f"Total validation time: {analysis['total_time']:.3f}s\n")
        f.write(f"Slow hooks: {analysis['slow_hooks']}\n")
        f.write(f"Failed hooks: {analysis['failed_hooks']}\n")
        f.write(f"All passing: {analysis['all_passing']}\n")
        f.write(f"Performance acceptable: {analysis['performance_acceptable']}\n\n")

        for result in results:
            f.write(f"{result.script_name}\n")
            f.write("-" * len(result.script_name) + "\n")
            if result.execution_times:
                f.write(f"Average time: {result.avg_time:.4f}s\n")
                f.write(f"Median time: {result.median_time:.4f}s\n")
                f.write(f"Std deviation: {result.std_dev:.4f}s\n")
                f.write(f"Min time: {result.min_time:.4f}s\n")
                f.write(f"Max time: {result.max_time:.4f}s\n")
                f.write(f"Success rate: {result.success_rate*100:.1f}%\n")
            else:
                f.write("FAILED TO EXECUTE\n")
            f.write("\n")

    print(f"\n💾 Detailed results saved to: {results_file}")

    return analysis


if __name__ == "__main__":
    main()
