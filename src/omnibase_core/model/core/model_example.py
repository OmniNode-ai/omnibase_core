"""
Example model.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelExample(BaseModel):
    """
    Individual example with typed fields.
    """

    # Example identification
    name: Optional[str] = Field(None, description="Example name")
    description: Optional[str] = Field(None, description="Example description")

    # Example data - using a more structured approach
    input_data: Optional[Dict[str, Any]] = Field(None, description="Example input data")
    output_data: Optional[Dict[str, Any]] = Field(
        None, description="Example output data"
    )

    # Additional context
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context for the example"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Validation info
    is_valid: bool = Field(True, description="Whether this example is valid")
    validation_notes: Optional[str] = Field(None, description="Notes about validation")

    # Timestamps
    created_at: Optional[datetime] = Field(
        None, description="When the example was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When the example was last updated"
    )
