"""
ModelDebugData: Debug data representation.

This model provides structured debug data without using Any types.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelDebugData(BaseModel):
    """Debug data representation."""

    connection_details: Dict[str, str] = Field(
        default_factory=dict, description="Connection debug details"
    )
    credential_status: Dict[str, str] = Field(
        default_factory=dict, description="Credential status information"
    )
    validation_results: Dict[str, str] = Field(
        default_factory=dict, description="Validation debug results"
    )
    performance_metrics: Dict[str, str] = Field(
        default_factory=dict, description="Performance debug metrics"
    )
    error_details: List[str] = Field(
        default_factory=list, description="Detailed error information"
    )
    debug_flags: Dict[str, bool] = Field(
        default_factory=dict, description="Debug flag settings"
    )
