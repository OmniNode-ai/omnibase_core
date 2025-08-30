"""Base model for tool parameters with strong typing."""

from pydantic import BaseModel


class ModelToolParameterBase(BaseModel):
    """Base model for all tool parameters."""

    class Config:
        """Pydantic config."""

        extra = "allow"  # Allow tool-specific fields
        validate_assignment = True
