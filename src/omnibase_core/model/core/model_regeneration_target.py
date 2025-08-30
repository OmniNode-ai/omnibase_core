"""
Canonical model for specifying a regeneration target (artifact or directory).
"""

from pathlib import Path

from pydantic import BaseModel


class ModelRegenerationTarget(BaseModel):
    """
    Canonical model for specifying a regeneration target (artifact or directory).
    """

    path: Path
    type: str | None = None  # Optionally use an Enum for artifact type
