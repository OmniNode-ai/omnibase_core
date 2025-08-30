"""
Metadata model for operational windows.

Provides strongly typed metadata structure for windows.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelWindowMetadata(BaseModel):
    """Metadata for operational windows."""

    creation_source: str = Field(
        default="automation_controller", description="System that created the window"
    )
    last_modified_by: str = Field(
        default="system", description="Last modifier of window configuration"
    )
    version: str = Field(default="1.0.0", description="Window configuration version")
    tags: list[str] = Field(
        default_factory=list, description="Window categorization tags"
    )
    notes: Optional[str] = Field(None, description="Additional notes about the window")
    custom_quota_rules: Optional[str] = Field(
        None, description="Custom quota allocation rules"
    )
    notification_settings: Optional[str] = Field(
        None, description="Window-specific notification preferences"
    )
    optimization_hints: Optional[str] = Field(
        None, description="Hints for quota optimization"
    )
