"""Tool input data model for protocol tool."""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ModelToolInputData(BaseModel):
    """Input data for tool execution."""

    operation: str = Field(..., description="Operation to perform")
    source_path: Optional[str] = Field(
        None, description="Source file or directory path"
    )
    target_path: Optional[str] = Field(
        None, description="Target file or directory path"
    )
    config: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        None, description="Configuration parameters"
    )
    metadata: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        None, description="Metadata for the operation"
    )
    options: Optional[List[str]] = Field(None, description="Additional options")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
