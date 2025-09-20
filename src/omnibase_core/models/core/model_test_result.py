"""
Test Result Model.

Individual test result model for test execution tracking.
"""

from pydantic import BaseModel, Field


class ModelTestResult(BaseModel):
    """Individual test result."""

    test_name: str = Field(..., description="Name of the test")
    passed: bool = Field(..., description="Whether the test passed")
    duration_ms: int = Field(
        default=0,
        description="Test execution duration in milliseconds",
        ge=0,
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if test failed",
    )
    details: str | None = Field(default=None, description="Additional test details")


# Export for use
__all__ = ["ModelTestResult"]