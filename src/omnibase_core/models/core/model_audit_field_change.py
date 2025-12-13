"""
Audit field change model for tracking individual field changes.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelAuditFieldChange(BaseModel):
    """Individual field change in an audit entry."""

    field_path: str = Field(
        default=..., description="Dot-separated path to changed field"
    )
    old_value: ModelSchemaValue = Field(default=..., description="Previous value")
    new_value: ModelSchemaValue = Field(default=..., description="New value")
    value_type: str = Field(default=..., description="Type of the value")

    def is_sensitive(self) -> bool:
        """Check if this field contains sensitive data."""
        sensitive_fields = ["password", "token", "secret", "key", "credential"]
        return any(s in self.field_path.lower() for s in sensitive_fields)
