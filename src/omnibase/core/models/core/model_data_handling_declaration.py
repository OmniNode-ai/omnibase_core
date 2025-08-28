"""
Data handling declaration model.
"""

from typing import Optional

from pydantic import BaseModel

from omnibase.enums import EnumDataClassification


class ModelDataHandlingDeclaration(BaseModel):
    """Data handling and classification declaration."""

    processes_sensitive_data: bool
    data_residency_required: Optional[str] = None
    data_classification: Optional[EnumDataClassification] = None
