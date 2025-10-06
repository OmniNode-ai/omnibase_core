from __future__ import annotations

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Test result model.

Individual test result model.
Follows ONEX one-model-per-file naming conventions.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelTestResult(BaseModel):
    """Individual test result.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Entity reference with UUID
    test_id: UUID = Field(default=..., description="Unique identifier of the test")
    test_display_name: str = Field(
        default=..., description="Human-readable name of the test"
    )
    passed: bool = Field(default=..., description="Whether the test passed")
    duration_ms: int = Field(
        default=0,
        description="Test execution duration in milliseconds",
        ge=0,
    )
    error_message: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Error message if test failed",
    )
    details: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Additional test details",
    )

    @classmethod
    def create_from_name(
        cls,
        test_name: str,
        passed: bool,
        duration_ms: int = 0,
        error_message: str | None = None,
        details: str | None = None,
    ) -> ModelTestResult:
        """
        Create test result from test name.

        Args:
            test_name: Test name (will be used as display_name)
            passed: Whether the test passed
            duration_ms: Test execution duration in milliseconds
            error_message: Error message if test failed
            details: Additional test details

        Returns:
            Test result with generated UUID and display_name set
        """
        from uuid import uuid4

        return cls(
            test_id=uuid4(),
            test_display_name=test_name,
            passed=passed,
            duration_ms=duration_ms,
            error_message=ModelSchemaValue.from_value(
                error_message if error_message else "",
            ),
            details=ModelSchemaValue.from_value(details if details else ""),
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelTestResult"]
