"""
Audit value model to replace Dict[str, Any] usage in audit entries.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_audit_field_change import ModelAuditFieldChange
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import SerializedDict, TypedDictAuditChange

AuditFieldChange = ModelAuditFieldChange


class ModelAuditValue(BaseModel):
    """
    Audit value with typed fields and change tracking.
    Replaces Dict[str, Any] for previous_value and new_value fields.
    """

    object_type: str = Field(default=..., description="Type of audited object")
    object_id: UUID = Field(default=..., description="ID of audited object")
    object_name: str | None = Field(default=None, description="Name of audited object")
    field_changes: list[ModelAuditFieldChange] = Field(
        default_factory=list, description="List of field changes"
    )
    version_before: ModelSemVer | None = Field(
        default=None, description="Version before change"
    )
    version_after: ModelSemVer | None = Field(
        default=None, description="Version after change"
    )
    serialized_before: str | None = Field(
        default=None, description="JSON serialized state before"
    )
    serialized_after: str | None = Field(
        default=None, description="JSON serialized state after"
    )
    change_summary: str | None = Field(
        default=None, description="Human-readable change summary"
    )
    change_count: int = Field(default=0, description="Number of fields changed")

    def to_dict(self) -> dict[str, TypedDictAuditChange]:
        """Convert to dictionary for current standards."""
        result: dict[str, TypedDictAuditChange] = {}
        for change in self.field_changes:
            if not change.is_sensitive():
                result[change.field_path] = TypedDictAuditChange(
                    old=change.old_value,
                    new=change.new_value,
                )
        return result

    @classmethod
    def from_dict(
        cls, data: SerializedDict | None, is_new: bool = False
    ) -> "ModelAuditValue | None":
        """Create from dictionary for easy migration."""
        if data is None:
            return None
        if "field_changes" not in data and isinstance(data, dict):
            field_changes = []
            for key, value in data.items():
                if isinstance(value, dict) and "old" in value and ("new" in value):
                    field_changes.append(
                        ModelAuditFieldChange(
                            field_path=key,
                            old_value=ModelSchemaValue.from_value(value["old"]),
                            new_value=ModelSchemaValue.from_value(value["new"]),
                            value_type=type(value["new"]).__name__,
                        )
                    )
                else:
                    field_changes.append(
                        ModelAuditFieldChange(
                            field_path=key,
                            old_value=ModelSchemaValue.from_value(
                                None if is_new else value
                            ),
                            new_value=ModelSchemaValue.from_value(
                                value if is_new else None
                            ),
                            value_type=type(value).__name__,
                        )
                    )
            return cls(
                object_type="unknown",
                object_id=uuid4(),
                field_changes=field_changes,
                change_count=len(field_changes),
            )
        # Pydantic validates the data at runtime - type safety is enforced by Pydantic
        return cls.model_validate(data)

    def get_changed_fields(self) -> list[str]:
        """Get list of changed field names."""
        return [change.field_path for change in self.field_changes]

    def has_sensitive_changes(self) -> bool:
        """Check if any changes involve sensitive fields."""
        return any(change.is_sensitive() for change in self.field_changes)
