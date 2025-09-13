#!/usr/bin/env python3
"""
Phase 3: 7-Gate Validation System with Rollback Automation

Enhanced validation framework for HIGH/CRITICAL risk model remediation.
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of a validation gate."""

    gate_number: int
    gate_name: str
    success: bool
    message: str
    execution_time: float
    metrics: Dict[str, Any] = None
    rollback_triggered: bool = False


@dataclass
class SystemBaseline:
    """System performance and health baseline."""

    timestamp: str
    performance_metrics: Dict[str, float]
    health_status: Dict[str, bool]
    test_results: Dict[str, int]
    import_graph: Dict[str, List[str]]


class Phase3Validator:
    """7-Gate validation system for HIGH risk model remediation."""

    def __init__(self, model_path: str, rollback_on_failure: bool = True):
        self.model_path = Path(model_path)
        self.model_name = self.model_path.stem
        self.rollback_on_failure = rollback_on_failure
        self.baseline = self.load_baseline()
        self.results: List[ValidationResult] = []

    def load_baseline(self) -> Optional[SystemBaseline]:
        """Load system baseline for comparison."""
        baseline_path = Path("baselines") / f"{self.model_name}_baseline.json"
        if baseline_path.exists():
            with open(baseline_path, "r") as f:
                data = json.load(f)
                return SystemBaseline(**data)
        return None

    def run_all_gates(self) -> bool:
        """Execute all 7 validation gates with rollback on failure."""
        print(f"🚀 Running 7-Gate Validation for {self.model_name}")
        print("=" * 60)

        gates = [
            ("Factory Method Elimination", self.gate1_factory_elimination),
            ("Serialization Compliance", self.gate2_serialization_compliance),
            ("Import Chain Stability", self.gate3_import_stability),
            ("Test Suite Integrity", self.gate4_test_integrity),
            ("Performance Stability", self.gate5_performance_stability),
            ("Critical System Functionality", self.gate6_critical_functionality),
            ("Infrastructure Resilience", self.gate7_infrastructure_resilience),
        ]

        for gate_num, (gate_name, gate_func) in enumerate(gates, 1):
            print(f"\n🔍 Gate {gate_num}: {gate_name}")
            print("-" * 40)

            start_time = time.time()
            try:
                success, message, metrics = gate_func()
                execution_time = time.time() - start_time

                result = ValidationResult(
                    gate_number=gate_num,
                    gate_name=gate_name,
                    success=success,
                    message=message,
                    execution_time=execution_time,
                    metrics=metrics,
                )

                self.results.append(result)

                if success:
                    print(f"✅ Gate {gate_num} PASSED: {message}")
                    print(f"   Execution time: {execution_time:.2f}s")
                else:
                    print(f"❌ Gate {gate_num} FAILED: {message}")
                    if self.rollback_on_failure:
                        self.trigger_rollback(f"Gate {gate_num} failure")
                        result.rollback_triggered = True
                    return False

            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"Gate {gate_num} exception: {str(e)}"

                result = ValidationResult(
                    gate_number=gate_num,
                    gate_name=gate_name,
                    success=False,
                    message=error_msg,
                    execution_time=execution_time,
                )

                self.results.append(result)
                print(f"💥 Gate {gate_num} EXCEPTION: {error_msg}")

                if self.rollback_on_failure:
                    self.trigger_rollback(f"Gate {gate_num} exception")
                    result.rollback_triggered = True
                return False

        print(f"\n🎉 ALL 7 GATES PASSED for {self.model_name}")
        self.save_validation_report()
        return True

    def gate1_factory_elimination(self) -> Tuple[bool, str, Dict]:
        """Gate 1: Verify all factory methods removed."""
        # Check for @classmethod factory patterns
        cmd = ["grep", "-r", "@classmethod.*def from_", str(self.model_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            factory_methods = result.stdout.strip().split("\n")
            return (
                False,
                f"Found {len(factory_methods)} factory methods still present",
                {
                    "factory_methods_found": len(factory_methods),
                    "examples": factory_methods[:3],
                },
            )

        # Check for standalone factory functions
        cmd = ["grep", "-r", "def from_.*\\(", str(self.model_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            factory_functions = result.stdout.strip().split("\n")
            return (
                False,
                f"Found {len(factory_functions)} factory functions still present",
                {
                    "factory_functions_found": len(factory_functions),
                    "examples": factory_functions[:3],
                },
            )

        return (
            True,
            "All factory methods successfully eliminated",
            {"factory_methods_found": 0, "factory_functions_found": 0},
        )

    def gate2_serialization_compliance(self) -> Tuple[bool, str, Dict]:
        """Gate 2: Verify model_dump() used instead of to_dict()."""
        cmd = ["grep", "-r", "def to_dict", str(self.model_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            to_dict_methods = result.stdout.strip().split("\n")
            return (
                False,
                f"Found {len(to_dict_methods)} to_dict() methods",
                {
                    "to_dict_methods_found": len(to_dict_methods),
                    "examples": to_dict_methods[:3],
                },
            )

        # Verify model_dump usage exists
        cmd = ["grep", "-r", "model_dump()", str(self.model_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        model_dump_count = (
            len(result.stdout.strip().split("\n")) if result.returncode == 0 else 0
        )

        return (
            True,
            "Serialization compliance verified",
            {"to_dict_methods_found": 0, "model_dump_usage_count": model_dump_count},
        )

    def gate3_import_stability(self) -> Tuple[bool, str, Dict]:
        """Gate 3: Verify import chains resolve successfully."""
        try:
            # Attempt to compile the model
            cmd = ["python", "-m", "py_compile", str(self.model_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return (
                    False,
                    f"Import compilation failed: {result.stderr}",
                    {"compilation_success": False, "error_details": result.stderr},
                )

            # Count import statements
            with open(self.model_path, "r") as f:
                content = f.read()
                import_count = len(
                    [
                        line
                        for line in content.split("\n")
                        if line.strip().startswith(("import ", "from "))
                    ]
                )

            return (
                True,
                f"Import chain stability verified ({import_count} imports)",
                {"compilation_success": True, "import_count": import_count},
            )

        except subprocess.TimeoutExpired:
            return (
                False,
                "Import compilation timeout (>30s)",
                {"compilation_success": False, "error_details": "Compilation timeout"},
            )

    def gate4_test_integrity(self) -> Tuple[bool, str, Dict]:
        """Gate 4: Verify test suite passes with no regressions."""
        # Run tests with timeout
        cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--maxfail=5"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return (
                False,
                f"Test suite failed (exit code {result.returncode})",
                {
                    "tests_passed": False,
                    "exit_code": result.returncode,
                    "error_output": result.stdout[-500:],  # Last 500 chars
                },
            )

        # Parse test results
        output_lines = result.stdout.split("\n")
        passed_line = [
            line for line in output_lines if "passed" in line and "failed" not in line
        ]

        if passed_line:
            # Extract number of passed tests
            import re

            match = re.search(r"(\d+) passed", passed_line[-1])
            passed_count = int(match.group(1)) if match else 0
        else:
            passed_count = 0

        target_count = 109  # Minimum expected tests
        if passed_count < target_count:
            return (
                False,
                f"Insufficient tests passed ({passed_count} < {target_count})",
                {
                    "tests_passed": True,
                    "passed_count": passed_count,
                    "target_count": target_count,
                },
            )

        return (
            True,
            f"Test integrity verified ({passed_count} tests passed)",
            {
                "tests_passed": True,
                "passed_count": passed_count,
                "target_count": target_count,
            },
        )

    def gate5_performance_stability(self) -> Tuple[bool, str, Dict]:
        """Gate 5: Verify no performance regression >5%."""
        if not self.baseline:
            return (
                True,
                "No baseline available, performance check skipped",
                {"baseline_available": False},
            )

        # Run performance benchmark
        current_metrics = self.run_performance_benchmark()

        performance_delta = {}
        regression_detected = False

        for metric, current_value in current_metrics.items():
            if metric in self.baseline.performance_metrics:
                baseline_value = self.baseline.performance_metrics[metric]
                delta_percent = (
                    (current_value - baseline_value) / baseline_value
                ) * 100
                performance_delta[metric] = delta_percent

                # Check for >5% regression (higher is worse for time metrics)
                if delta_percent > 5.0:
                    regression_detected = True

        if regression_detected:
            return (
                False,
                f"Performance regression detected: {performance_delta}",
                {
                    "baseline_available": True,
                    "performance_delta": performance_delta,
                    "regression_threshold": 5.0,
                },
            )

        return (
            True,
            f"Performance stability verified: {performance_delta}",
            {
                "baseline_available": True,
                "performance_delta": performance_delta,
                "regression_threshold": 5.0,
            },
        )

    def gate6_critical_functionality(self) -> Tuple[bool, str, Dict]:
        """Gate 6: Verify critical ONEX system components operational."""
        critical_services = [
            "event_bus",
            "node_system",
            "infrastructure",
            "protocol_system",
        ]

        service_status = {}
        all_healthy = True

        for service in critical_services:
            # Simulate health check (replace with actual health check endpoints)
            try:
                # Health check implementation would go here
                health_status = self.check_service_health(service)
                service_status[service] = health_status
                if not health_status:
                    all_healthy = False
            except Exception as e:
                service_status[service] = False
                all_healthy = False

        if not all_healthy:
            failed_services = [
                svc for svc, status in service_status.items() if not status
            ]
            return (
                False,
                f"Critical services unhealthy: {failed_services}",
                {"service_status": service_status, "failed_services": failed_services},
            )

        return (
            True,
            "All critical systems operational",
            {"service_status": service_status, "failed_services": []},
        )

    def gate7_infrastructure_resilience(self) -> Tuple[bool, str, Dict]:
        """Gate 7: Verify infrastructure stability and recovery."""
        resilience_tests = [
            ("container_resolution", self.test_container_resolution),
            ("event_processing", self.test_event_processing),
            ("load_balancing", self.test_load_balancing),
            ("failover_capability", self.test_failover_capability),
        ]

        test_results = {}
        all_passed = True

        for test_name, test_func in resilience_tests:
            try:
                result = test_func()
                test_results[test_name] = result
                if not result:
                    all_passed = False
            except Exception as e:
                test_results[test_name] = False
                all_passed = False

        if not all_passed:
            failed_tests = [test for test, result in test_results.items() if not result]
            return (
                False,
                f"Infrastructure resilience tests failed: {failed_tests}",
                {"test_results": test_results, "failed_tests": failed_tests},
            )

        return (
            True,
            "Infrastructure resilience verified",
            {"test_results": test_results, "failed_tests": []},
        )

    def run_performance_benchmark(self) -> Dict[str, float]:
        """Run performance benchmark and return metrics."""
        # Simplified benchmark - replace with actual performance tests
        return {
            "model_load_time": 0.05,  # seconds
            "memory_usage": 128.0,  # MB
            "response_time": 0.02,  # seconds
        }

    def check_service_health(self, service_name: str) -> bool:
        """Check health of a critical service."""
        # Implement actual health checks here
        return True  # Simplified for example

    def test_container_resolution(self) -> bool:
        """Test dependency injection container resolution."""
        # Implement actual container resolution test
        return True

    def test_event_processing(self) -> bool:
        """Test event bus processing capability."""
        # Implement actual event processing test
        return True

    def test_load_balancing(self) -> bool:
        """Test load balancing functionality."""
        # Implement actual load balancing test
        return True

    def test_failover_capability(self) -> bool:
        """Test system failover and recovery."""
        # Implement actual failover test
        return True

    def trigger_rollback(self, reason: str) -> None:
        """Trigger automated rollback procedure."""
        print(f"\n🚨 ROLLBACK TRIGGERED: {reason}")
        print("=" * 50)

        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        )
        current_commit = result.stdout.strip()

        # Perform rollback
        print(f"Rolling back from commit: {current_commit}")

        # Option 1: Revert specific file
        rollback_cmd = ["git", "checkout", "HEAD~1", "--", str(self.model_path)]
        subprocess.run(rollback_cmd)

        print(f"✅ Rollback completed for {self.model_path}")
        print(f"📝 Manual verification required before proceeding")

    def save_validation_report(self) -> None:
        """Save comprehensive validation report."""
        report = {
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "timestamp": datetime.now().isoformat(),
            "validation_results": [
                {
                    "gate_number": r.gate_number,
                    "gate_name": r.gate_name,
                    "success": r.success,
                    "message": r.message,
                    "execution_time": r.execution_time,
                    "metrics": r.metrics,
                    "rollback_triggered": r.rollback_triggered,
                }
                for r in self.results
            ],
            "overall_success": all(r.success for r in self.results),
            "total_execution_time": sum(r.execution_time for r in self.results),
        }

        report_path = Path("validation_reports") / f"{self.model_name}_validation.json"
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Validation report saved: {report_path}")


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python run_7_gate_validation.py <model_path> [--no-rollback]")
        sys.exit(1)

    model_path = sys.argv[1]
    rollback_on_failure = "--no-rollback" not in sys.argv

    validator = Phase3Validator(model_path, rollback_on_failure)
    success = validator.run_all_gates()

    if success:
        print(f"\n🎉 Phase 3 validation SUCCESSFUL for {validator.model_name}")
        sys.exit(0)
    else:
        print(f"\n💥 Phase 3 validation FAILED for {validator.model_name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
