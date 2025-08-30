"""
Model for metadata properties - flexible key-value storage.
"""

from pydantic import BaseModel, Field


class ModelMetadataProperties(BaseModel):
    """Model for flexible metadata properties storage."""

    # Common properties that metadata blocks might contain
    author: str | None = Field(None, description="Author of the file or metadata")
    purpose: str | None = Field(
        None,
        description="Purpose or description of the file",
    )
    complexity: str | None = Field(
        None,
        description="Complexity level of the content",
    )
    status: str | None = Field(None, description="Status of the file or component")
    category: str | None = Field(None, description="Category or classification")
    priority: str | None = Field(None, description="Priority level")
    environment: str | None = Field(None, description="Target environment")

    # File-specific properties
    file_path: str | None = Field(None, description="Original file path")
    file_type: str | None = Field(None, description="Detected file type")
    encoding: str | None = Field(None, description="File encoding")

    # Processing properties
    test_type: str | None = Field(None, description="Type of test or processing")
    scan_batch: str | None = Field(
        None,
        description="Batch identifier for bulk operations",
    )
    test_case: str | None = Field(None, description="Test case identifier")

    # Workflow properties
    workflow_stage: str | None = Field(None, description="Current workflow stage")
    processing_flags: str | None = Field(
        None,
        description="Processing flags or options",
    )

    # Custom string values for extensibility
    custom_string_1: str | None = Field(None, description="Custom string property 1")
    custom_string_2: str | None = Field(None, description="Custom string property 2")
    custom_string_3: str | None = Field(None, description="Custom string property 3")

    # Numeric properties
    numeric_value_1: int | float | None = Field(
        None,
        description="Custom numeric value 1",
    )
    numeric_value_2: int | float | None = Field(
        None,
        description="Custom numeric value 2",
    )

    # Boolean flags
    is_test: bool | None = Field(None, description="Whether this is a test file")
    is_generated: bool | None = Field(
        None,
        description="Whether this file is generated",
    )
    requires_review: bool | None = Field(
        None,
        description="Whether this file requires review",
    )

    class Config:
        extra = "forbid"  # Don't allow arbitrary fields - use the defined optional fields instead
