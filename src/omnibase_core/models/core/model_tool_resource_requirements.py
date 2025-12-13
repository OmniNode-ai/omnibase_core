"""
Tool Resource Requirements Model.

Resource requirements configuration for tools.
"""

from pydantic import BaseModel, Field


class ModelToolResourceRequirements(BaseModel):
    """Resource requirements for a tool."""

    requires_separate_port: bool = Field(
        description="Whether tool requires separate HTTP port"
    )
    health_check_via_service: bool = Field(
        description="Whether health checked by parent service"
    )
    loaded_as_module: bool = Field(description="Whether loaded as module by service")
