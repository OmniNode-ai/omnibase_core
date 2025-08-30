"""
Audit value model to replace Dict[str, Any] usage in audit entries.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_audit_field_change import ModelAuditFieldChange

# Backward compatibility alias
AuditFieldChange = ModelAuditFieldChange


class ModelAuditValue(BaseModel):
    """
    Audit value with typed fields and change tracking.
    Replaces Dict[str, Any] for previous_value and new_value fields.
    """

    # Object identification
    object_type: str = Field(..., description="Type of audited object")
    object_id: str = Field(..., description="ID of audited object")
    object_name: str | None = Field(None, description="Name of audited object")

    # Change details
    field_changes: list[ModelAuditFieldChange] = Field(
        default_factory=list,
        description="List of field changes",
    )

    # Metadata
    version_before: str | None = Field(None, description="Version before change")
    version_after: str | None = Field(None, description="Version after change")

    # Serialized representations (for complex objects)
    serialized_before: str | None = Field(
        None,
        description="JSON serialized state before",
    )
    serialized_after: str | None = Field(
        None,
        description="JSON serialized state after",
    )

    # Summary
    change_summary: str | None = Field(
        None,
        description="Human-readable change summary",
    )
    change_count: int = Field(0, description="Number of fields changed")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # For backward compatibility, return a simple dict of changes
        result = {}
        for change in self.field_changes:
            if not change.is_sensitive():
                result[change.field_path] = {
                    "old": change.old_value,
                    "new": change.new_value,
                }
        return result

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        is_new: bool = False,
    ) -> Optional["ModelAuditValue"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Handle legacy format - flat dict of values
        if "field_changes" not in data and isinstance(data, dict):
            field_changes = []
            for key, value in data.items():
                if isinstance(value, dict) and "old" in value and "new" in value:
                    # Already in change format
                    field_changes.append(
                        ModelAuditFieldChange(
                            field_path=key,
                            old_value=value["old"],
                            new_value=value["new"],
                            value_type=type(value["new"]).__name__,
                        ),
                    )
                else:
                    # Simple value - determine if old or new
                    field_changes.append(
                        ModelAuditFieldChange(
                            field_path=key,
                            old_value=None if is_new else value,
                            new_value=value if is_new else None,
                            value_type=type(value).__name__,
                        ),
                    )

            return cls(
                object_type="unknown",
                object_id="unknown",
                field_changes=field_changes,
                change_count=len(field_changes),
            )

        return cls(**data)

    def get_changed_fields(self) -> list[str]:
        """Get list of changed field names."""
        return [change.field_path for change in self.field_changes]

    def has_sensitive_changes(self) -> bool:
        """Check if any changes involve sensitive fields."""
        return any(change.is_sensitive() for change in self.field_changes)
