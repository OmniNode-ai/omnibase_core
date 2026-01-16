"""Validation context model for field-level validation details.

This module provides ModelValidationContext, a typed context model for
tracking validation field names, expected values, and actual values.

Thread Safety:
    ModelValidationContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

Note:
    This model is for **field-level** validation (tracking field name, expected,
    and actual values). For **contract-level** validation context (validation mode
    and flags), use :class:`omnibase_core.models.events.contract_validation.ModelContractValidationContext`.

See Also:
    - ModelResourceContext: Resource-related context
    - ModelErrorDetails: Error handling with validation context
    - :class:`omnibase_core.models.events.contract_validation.ModelContractValidationContext`:
        Contract validation context (different model, different purpose)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationContext(BaseModel):
    """Typed context for field-level validation details.

    This model provides structured fields for capturing validation
    failures, including the field name, expected value, and actual value.

    Use Cases:
        - Validation error reporting
        - Form validation feedback
        - API request validation
        - Data quality checks

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        field_name: Name of the field that failed validation.
        expected: Description or value that was expected.
        actual: The actual value that was provided.

    Example:
        Validation failure context::

            from omnibase_core.models.context import ModelValidationContext

            context = ModelValidationContext(
                field_name="email",
                expected="valid email format",
                actual="not-an-email",
            )

        Type mismatch context::

            context = ModelValidationContext(
                field_name="age",
                expected="integer >= 0",
                actual="-5",
            )

    See Also:
        - ModelResourceContext: For resource identification
        - ModelErrorDetails: Uses validation context for error handling
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    field_name: str = Field(
        description="Name of the field that failed validation",
    )
    expected: str | None = Field(
        default=None,
        description="Description or value that was expected",
    )
    actual: str | None = Field(
        default=None,
        description="The actual value that was provided",
    )
