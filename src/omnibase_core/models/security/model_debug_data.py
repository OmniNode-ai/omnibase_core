"""
ModelDebugData: Debug data representation.

This model provides structured debug data without using Any types.
"""

from pydantic import BaseModel, Field


class ModelDebugData(BaseModel):
    """Debug data representation."""

    connection_details: dict[str, str] = Field(
        default_factory=dict,
        description="Connection debug details",
    )
    credential_status: dict[str, str] = Field(
        default_factory=dict,
        description="Credential status information",
    )
    validation_results: dict[str, str] = Field(
        default_factory=dict,
        description="Validation debug results",
    )
    performance_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Performance debug metrics",
    )
    error_details: list[str] = Field(
        default_factory=list,
        description="Detailed error information",
    )
    debug_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Debug flag settings",
    )
