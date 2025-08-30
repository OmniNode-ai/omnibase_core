"""Parsed node model."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ModelParsedNode(BaseModel):
    """Result of parsing enhanced node configuration."""

    id: str = Field(..., description="Node identifier")
    tool: str = Field(..., description="Tool name")
    inputs: Optional[List[str]] = Field(default=None, description="Input dependencies")
    parameters: Optional[Union[str, List[str]]] = Field(
        default=None, description="Node parameters"
    )
    retry_config: Optional[str] = Field(
        default=None, description="Retry configuration data"
    )
    conditional_config: Optional[str] = Field(
        default=None, description="Conditional configuration data"
    )
    loop_config: Optional[str] = Field(
        default=None, description="Loop configuration data"
    )
