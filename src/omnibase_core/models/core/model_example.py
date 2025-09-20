"""
Example model with strong typing and UUID support.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...core.core_uuid_service import UUIDService
from ...enums.enum_example_category import EnumExampleCategory
from ...enums.enum_example_validation_status import EnumExampleValidationStatus
from .model_example_input import ModelExampleInput
from .model_example_output import ModelExampleOutput
from .model_generic_collection import Identifiable


class ModelExample(BaseModel):
    """
    Individual example with strong typing and UUID support.

    Replaces dict[str, Any] with structured models and provides
    UUID-based identification with enum-based categorization.
    """

    # Example identification
    example_id: UUID = Field(
        default_factory=UUIDService.generate_correlation_id,
        description="Unique identifier for this example"
    )
    name: str | None = Field(None, description="Example name")
    description: str | None = Field(None, description="Example description")

    # Example data - strongly typed
    input_data: ModelExampleInput | None = Field(
        default=None,
        description="Structured input data for the example"
    )
    output_data: ModelExampleOutput | None = Field(
        default=None,
        description="Structured output data for the example"
    )

    # Categorization and context
    category: EnumExampleCategory | None = Field(
        default=None,
        description="Category of the example using enum"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for additional categorization"
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context for the example"
    )

    # Validation info - enum-based
    validation_status: EnumExampleValidationStatus = Field(
        default=EnumExampleValidationStatus.PENDING,
        description="Validation status using enum"
    )
    validation_notes: str | None = Field(
        default=None,
        description="Notes about validation"
    )

    # Author and ownership
    author_id: UUID | None = Field(
        default=None,
        description="UUID of the example author"
    )
    author_name: str | None = Field(
        default=None,
        description="Name of the example author"
    )

    # Timestamps
    created_at: datetime | None = Field(
        default=None,
        description="When the example was created"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="When the example was last updated"
    )
    validated_at: datetime | None = Field(
        default=None,
        description="When the example was last validated"
    )

    # Helper methods
    def get_id(self) -> UUID:
        """Get the unique identifier for this example (Identifiable protocol)."""
        return self.example_id

    def is_valid(self) -> bool:
        """Check if the example is valid."""
        return self.validation_status == EnumExampleValidationStatus.VALID

    def is_pending_validation(self) -> bool:
        """Check if validation is pending."""
        return self.validation_status == EnumExampleValidationStatus.PENDING

    def mark_as_valid(self, notes: str | None = None) -> None:
        """Mark the example as valid."""
        self.validation_status = EnumExampleValidationStatus.VALID
        if notes:
            self.validation_notes = notes
        self.validated_at = datetime.utcnow()

    def mark_as_invalid(self, notes: str | None = None) -> None:
        """Mark the example as invalid."""
        self.validation_status = EnumExampleValidationStatus.INVALID
        if notes:
            self.validation_notes = notes
        self.validated_at = datetime.utcnow()

    def requires_review(self, notes: str | None = None) -> None:
        """Mark the example as requiring review."""
        self.validation_status = EnumExampleValidationStatus.REQUIRES_REVIEW
        if notes:
            self.validation_notes = notes

    def has_input_data(self) -> bool:
        """Check if the example has input data."""
        return self.input_data is not None

    def has_output_data(self) -> bool:
        """Check if the example has output data."""
        return self.output_data is not None

    def is_complete(self) -> bool:
        """Check if the example has both input and output data."""
        return self.has_input_data() and self.has_output_data()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelExample":
        """Create from dictionary with validation."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data)}")

        return cls(**data)

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str | None = None,
        input_data: ModelExampleInput | None = None,
        output_data: ModelExampleOutput | None = None,
        category: EnumExampleCategory | None = None
    ) -> "ModelExample":
        """Create a simple example with basic information."""
        return cls(
            name=name,
            description=description,
            input_data=input_data,
            output_data=output_data,
            category=category
        )