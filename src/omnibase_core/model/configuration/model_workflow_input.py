"""
Workflow input model.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ModelWorkflowInput(BaseModel):
    """Individual workflow input definition."""

    description: str = Field(..., description="Input description")
    required: bool = Field(False, description="Whether input is required")
    default: Optional[Union[str, int, bool]] = Field(None, description="Default value")
    type: str = Field("string", description="Input type (string/choice/boolean)")
    options: Optional[List[str]] = Field(None, description="Options for choice type")
