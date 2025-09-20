"""
Data handling declaration model.
"""

from typing import Literal

from pydantic import BaseModel


class ModelDataHandlingDeclaration(BaseModel):
    """Data handling and classification declaration."""

    processes_sensitive_data: bool
    data_residency_required: str | None = None
    data_classification: (
        Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"] | None
    ) = None
