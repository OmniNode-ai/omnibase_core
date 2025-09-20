"""
Test Results Collection Model.

Strongly typed model for test execution results collection.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_test_result import ModelTestResult


class ModelTestResults(BaseModel):
    """Collection of test results with summary."""

    results: list[ModelTestResult] = Field(
        default_factory=list,
        description="Individual test results",
    )
    total_tests: int = Field(default=0, description="Total number of tests", ge=0)
    passed_tests: int = Field(default=0, description="Number of passed tests", ge=0)
    failed_tests: int = Field(default=0, description="Number of failed tests", ge=0)
    total_duration_ms: int = Field(
        default=0,
        description="Total execution time in milliseconds",
        ge=0,
    )
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When tests were executed",
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100.0

    @property
    def all_passed(self) -> bool:
        """Check if all tests passed."""
        return self.failed_tests == 0 and self.total_tests > 0

    def add_result(self, test_result: ModelTestResult) -> None:
        """Add a test result and update counters."""
        self.results.append(test_result)
        self.total_tests += 1
        if test_result.passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        self.total_duration_ms += test_result.duration_ms

    @classmethod
    def from_dict(cls, test_data: dict[str, bool]) -> "ModelTestResults":
        """Create from dictionary with strict type validation."""
        results = []
        for test_name, passed in test_data.items():
            results.append(ModelTestResult(test_name=test_name, passed=passed))

        instance = cls()
        for result in results:
            instance.add_result(result)

        return instance


# Export for use
__all__ = ["ModelTestResults"]
