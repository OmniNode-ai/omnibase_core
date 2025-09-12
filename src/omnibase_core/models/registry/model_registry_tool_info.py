"""
ModelRegistryToolInfo - Registry tool information model.
"""

from pydantic import BaseModel


class ModelRegistryToolInfo(BaseModel):
    """Registry tool information."""

    tool_type: str | None
    protocol_requirements: list[str]
