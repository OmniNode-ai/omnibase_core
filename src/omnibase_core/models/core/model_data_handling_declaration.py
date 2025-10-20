"""
Data handling declaration model.
"""

from pydantic import BaseModel

from omnibase_core.enums.enum_data_classification import EnumDataClassification


class ModelDataHandlingDeclaration(BaseModel):
    """Data handling and classification declaration."""

    processes_sensitive_data: bool
    data_residency_required: str | None = None
    data_classification: EnumDataClassification | None = None
