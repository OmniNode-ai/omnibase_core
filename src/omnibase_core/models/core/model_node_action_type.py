"""
Node Action Type Model.

Rich action type model that replaces EnumNodeActionType with full metadata support.
Self-contained action definitions with built-in categorization and validation.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelNodeActionType(BaseModel):
    """
    Rich action type model with embedded metadata.

    Replaces simple string enums with self-contained action definitions
    that include all necessary metadata for validation and execution.
    """

    name: str = Field(default=..., description="Unique action type name")
    category: ModelActionCategory = Field(default=..., description="Action category")
    display_name: str = Field(default=..., description="Human-readable display name")
    description: str = Field(default=..., description="Detailed action description")

    # Behavioral metadata
    is_destructive: bool = Field(
        default=False,
        description="Whether this action modifies data",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether this action requires user confirmation",
    )
    estimated_duration_ms: int | None = Field(
        default=None,
        description="Estimated execution time in milliseconds",
    )

    # Security and permissions
    security_level: str = Field(
        default="standard",
        description="Required security clearance level",
    )
    required_permissions: list[str] = Field(
        default_factory=list,
        description="Required permissions for execution",
    )

    # Tool-as-a-service metadata
    mcp_compatible: bool = Field(
        default=True,
        description="Whether action supports MCP protocol",
    )
    graphql_compatible: bool = Field(
        default=True,
        description="Whether action supports GraphQL",
    )
    composition_compatible: bool = Field(
        default=True,
        description="Whether action supports composition patterns",
    )

    # Class-level registry for action type management
    _registry: ClassVar[dict[str, ModelNodeActionType]] = {}

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: str) -> str:
        """Validate security level is from allowed values."""
        allowed_levels = {"public", "standard", "elevated", "restricted", "classified"}
        if v not in allowed_levels:
            msg = f"Security level must be one of: {allowed_levels}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate action name follows naming conventions.

        Action names must be:
        - Non-empty (at least one character)
        - Lowercase only
        - Alphanumeric with underscores only (no spaces or special chars)

        Args:
            v: The action name to validate.

        Returns:
            The validated action name.

        Raises:
            ModelOnexError: If the name is empty, not lowercase, or contains
                invalid characters.
        """
        # Check for empty string first with clear error message
        if not v:
            msg = "Action name cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if not v.islower():
            msg = "Action name must be lowercase"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if not v.replace("_", "").isalnum():
            msg = "Action name must contain only letters, numbers, and underscores"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def __str__(self) -> str:
        """String representation returns the action name."""
        return self.name

    def __eq__(self, other: object) -> bool:
        """Equality based on action name."""
        if isinstance(other, ModelNodeActionType):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        Returns:
            int: Hash computed from the action name.
        """
        return hash(self.name)

    @classmethod
    def register(cls, action_type: ModelNodeActionType) -> None:
        """Register an action type in the global registry."""
        cls._registry[action_type.name] = action_type

    @classmethod
    def get_by_name(cls, name: str) -> ModelNodeActionType | None:
        """Get action type by name from registry."""
        return cls._registry.get(name)

    @classmethod
    def get_by_category(
        cls,
        category: ModelActionCategory,
    ) -> list[ModelNodeActionType]:
        """Get all action types in a specific category."""
        return [
            action for action in cls._registry.values() if action.category == category
        ]

    @classmethod
    def get_all_registered(cls) -> list[ModelNodeActionType]:
        """Get all registered action types."""
        return list(cls._registry.values())

    @classmethod
    def get_destructive_actions(cls) -> list[ModelNodeActionType]:
        """Get all destructive action types."""
        return [action for action in cls._registry.values() if action.is_destructive]

    @classmethod
    def get_by_security_level(cls, security_level: str) -> list[ModelNodeActionType]:
        """Get all action types requiring specific security level."""
        return [
            action
            for action in cls._registry.values()
            if action.security_level == security_level
        ]

    def is_compatible_with_protocol(self, protocol: str) -> bool:
        """Check if action is compatible with a specific protocol."""
        protocol_map = {
            "mcp": self.mcp_compatible,
            "graphql": self.graphql_compatible,
            "composition": self.composition_compatible,
        }
        return protocol_map.get(protocol.lower(), False)

    # union-ok: service_metadata - Complex return type includes ModelActionCategory model
    def to_service_metadata(
        self,
    ) -> dict[
        str,
        str | bool | int | list[str] | ModelActionCategory | None,
    ]:
        """Generate service discovery metadata with strong typing."""
        return {
            "name": self.name,
            "category": self.category,
            "display_name": self.display_name,
            "description": self.description,
            "is_destructive": self.is_destructive,
            "requires_confirmation": self.requires_confirmation,
            "estimated_duration_ms": self.estimated_duration_ms,
            "security_level": self.security_level,
            "required_permissions": self.required_permissions,
            "mcp_compatible": self.mcp_compatible,
            "graphql_compatible": self.graphql_compatible,
            "composition_compatible": self.composition_compatible,
        }
