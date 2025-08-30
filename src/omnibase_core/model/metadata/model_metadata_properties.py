"""
Model for metadata properties - flexible key-value storage.
"""

from typing import Optional, Union

from pydantic import BaseModel, Field


class ModelMetadataProperties(BaseModel):
    """Model for flexible metadata properties storage."""

    # Common properties that metadata blocks might contain
    author: Optional[str] = Field(None, description="Author of the file or metadata")
    purpose: Optional[str] = Field(
        None, description="Purpose or description of the file"
    )
    complexity: Optional[str] = Field(
        None, description="Complexity level of the content"
    )
    status: Optional[str] = Field(None, description="Status of the file or component")
    category: Optional[str] = Field(None, description="Category or classification")
    priority: Optional[str] = Field(None, description="Priority level")
    environment: Optional[str] = Field(None, description="Target environment")

    # File-specific properties
    file_path: Optional[str] = Field(None, description="Original file path")
    file_type: Optional[str] = Field(None, description="Detected file type")
    encoding: Optional[str] = Field(None, description="File encoding")

    # Processing properties
    test_type: Optional[str] = Field(None, description="Type of test or processing")
    scan_batch: Optional[str] = Field(
        None, description="Batch identifier for bulk operations"
    )
    test_case: Optional[str] = Field(None, description="Test case identifier")

    # Workflow properties
    workflow_stage: Optional[str] = Field(None, description="Current workflow stage")
    processing_flags: Optional[str] = Field(
        None, description="Processing flags or options"
    )

    # Custom string values for extensibility
    custom_string_1: Optional[str] = Field(None, description="Custom string property 1")
    custom_string_2: Optional[str] = Field(None, description="Custom string property 2")
    custom_string_3: Optional[str] = Field(None, description="Custom string property 3")

    # Numeric properties
    numeric_value_1: Optional[Union[int, float]] = Field(
        None, description="Custom numeric value 1"
    )
    numeric_value_2: Optional[Union[int, float]] = Field(
        None, description="Custom numeric value 2"
    )

    # Boolean flags
    is_test: Optional[bool] = Field(None, description="Whether this is a test file")
    is_generated: Optional[bool] = Field(
        None, description="Whether this file is generated"
    )
    requires_review: Optional[bool] = Field(
        None, description="Whether this file requires review"
    )

    class Config:
        extra = "forbid"  # Don't allow arbitrary fields - use the defined optional fields instead
