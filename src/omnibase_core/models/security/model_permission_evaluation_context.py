from pydantic import Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"\nModelPermissionEvaluationContext: Context for permission evaluation.\n\nThis model provides structured context for permission evaluation without using Any types.\n"
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModelPermissionEvaluationContext(BaseModel):
    """Context for permission evaluation."""

    user_id: UUID | None = Field(default=None, description="User identifier")
    resource_path: str | None = Field(
        default=None, description="Resource being accessed"
    )
    requested_action: str | None = Field(
        default=None, description="Action being requested"
    )
    timestamp: datetime | None = Field(default=None, description="Request timestamp")
    client_ip: str | None = Field(default=None, description="Client IP address")
    user_agent: str | None = Field(default=None, description="Client user agent")
    session_id: UUID | None = Field(default=None, description="Session identifier")
    string_attributes: dict[str, str] = Field(
        default_factory=dict, description="String context attributes"
    )
    integer_attributes: dict[str, int] = Field(
        default_factory=dict, description="Integer context attributes"
    )
    boolean_attributes: dict[str, bool] = Field(
        default_factory=dict, description="Boolean context attributes"
    )

    # union-ok: permission_primitive - domain excludes float for permission attribute types
    def get(
        self, key: str, default: str | int | bool | None = None
    ) -> str | int | bool | None:
        """Get a value from context attributes (dict[str, Any]-like behavior)."""
        if hasattr(self, key) and key not in [
            "string_attributes",
            "integer_attributes",
            "boolean_attributes",
        ]:
            value = getattr(self, key)
            # Type narrowing: ensure return type matches signature
            if isinstance(value, (str, int, bool, type(None))):
                return value
            return default
        if key in self.string_attributes:
            return self.string_attributes[key]
        if key in self.integer_attributes:
            return self.integer_attributes[key]
        if key in self.boolean_attributes:
            return self.boolean_attributes[key]
        return default

    def __contains__(self, key: str) -> bool:
        """Check if key exists in context (dict[str, Any]-like behavior)."""
        if hasattr(self, key) and key not in [
            "string_attributes",
            "integer_attributes",
            "boolean_attributes",
        ]:
            return getattr(self, key) is not None
        return (
            key in self.string_attributes
            or key in self.integer_attributes
            or key in self.boolean_attributes
        )

    # union-ok: permission_primitive - domain excludes float for permission attribute types
    def __getitem__(self, key: str) -> str | int | bool:
        """Get item with indexing (dict[str, Any]-like behavior)."""
        value = self.get(key)
        if value is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                message=f"Key '{key}' not found in context",
            )
        return value
