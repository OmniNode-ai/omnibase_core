"""
ModelRegistryToolInfo - Registry tool information model.
"""

from typing import Optional

from pydantic import BaseModel


class ModelRegistryToolInfo(BaseModel):
    """Registry tool information."""

    tool_type: Optional[str]
    protocol_requirements: list[str]
