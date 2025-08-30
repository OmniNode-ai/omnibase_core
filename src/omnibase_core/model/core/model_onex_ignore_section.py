"""
OnexIgnoreSection model.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelOnexIgnoreSection(BaseModel):
    patterns: List[str] = Field(
        default_factory=list, description="Glob patterns to ignore for this tool/type."
    )
