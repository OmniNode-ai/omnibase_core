"""
Test Results Model.

Strongly typed model for test execution results.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_test_result import ModelTestResult


class ModelTestResults(BaseModel):
    """Collection of test results with summary.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelTestResults"]
