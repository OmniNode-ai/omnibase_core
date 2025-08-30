"""
CLI parsed arguments model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliParsedArgs(BaseModel):
    """Strongly typed CLI parsed arguments."""

    string_args: dict[str, str] = Field(default_factory=dict)
    integer_args: dict[str, int] = Field(default_factory=dict)
    boolean_args: dict[str, bool] = Field(default_factory=dict)
