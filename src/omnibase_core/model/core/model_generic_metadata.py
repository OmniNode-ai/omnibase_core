"""
Generic metadata model to replace Dict[str, Any] usage for metadata fields.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ModelGenericMetadata(BaseModel):
    """
    Generic metadata container with flexible but typed fields.
    Replaces Dict[str, Any] for metadata fields across the codebase.
    """

    # Common metadata fields
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    updated_by: Optional[str] = Field(None, description="Last updater identifier")
    version: Optional[str] = Field(None, description="Version information")

    # Flexible fields for various use cases
    tags: Optional[List[str]] = Field(
        default_factory=list, description="Associated tags"
    )
    labels: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Key-value labels"
    )
    annotations: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Key-value annotations"
    )

    # Additional flexible storage
    custom_fields: Optional[Dict[str, Union[str, int, float, bool, List[str]]]] = Field(
        default_factory=dict, description="Custom fields with basic types"
    )

    # For complex nested data (last resort)
    extended_data: Optional[Dict[str, BaseModel]] = Field(
        None, description="Extended data with nested models"
    )

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional fields for backward compatibility

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["ModelGenericMetadata"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        return cls(**data)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
