"""
Test result model.

Individual test result model.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelTestResult(BaseModel):
    """Individual test result."""

    # Entity reference with UUID
    test_id: UUID = Field(..., description="Unique identifier of the test")
    test_display_name: str = Field(..., description="Human-readable name of the test")
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

    @classmethod
    def create_from_name(
        cls,
        test_name: str,
        **kwargs: Any,
    ) -> ModelTestResult:
        """
        Create test result from test name.

        Args:
            test_name: Test name (will be used as display_name)
            **kwargs: Other test parameters

        Returns:
            Test result with generated UUID and display_name set
        """
        from uuid import uuid4

        return cls(
            test_id=uuid4(),
            test_display_name=test_name,
            **kwargs,
        )


# Export for use
__all__ = ["ModelTestResult"]
