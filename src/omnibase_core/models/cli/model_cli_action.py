"""
Dynamic CLI Action Model.

Replaces hardcoded EnumNodeCliAction with extensible model that
enables plugin extensibility and contract-driven action registration.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.decorators import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_cli_action_serialized import (
    TypedDictCliActionSerialized,
)


class ModelCliAction(BaseModel):  # Protocols removed temporarily for syntax validation
    """
    Dynamic CLI action model that reads from contracts.

    Replaces hardcoded EnumNodeCliAction to allow third-party nodes
    to register their own actions dynamically.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Globally unique action identifier",
    )
    action_name_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for action name",
        exclude=True,
    )
    action_display_name: str = Field(
        default=...,
        description="Action name",
        alias="action_name",
    )
    node_id: UUID = Field(default=..., description="UUID-based node reference")
    node_display_name: str = Field(
        default=..., description="Node name", alias="node_name"
    )
    description: str = Field(default=..., description="Human-readable description")
    deprecated: bool = Field(default=False, description="Whether action is deprecated")
    category: object = Field(
        default=None,
        description="Action category for grouping (enum or null)",
    )

    @field_validator("category", mode="before")
    @classmethod
    def unwrap_category(cls, v: object) -> object:
        """Unwrap ModelSchemaValue if passed and validate enum."""
        if isinstance(v, ModelSchemaValue):
            v = v.to_value()

        # If not None, validate it's a valid enum member
        if v is not None:
            from omnibase_core.enums.enum_action_category import EnumActionCategory

            # Allow enum members directly
            if isinstance(v, EnumActionCategory):
                return v

            # Try to convert string to enum
            if isinstance(v, str):
                try:
                    return EnumActionCategory(v)
                except ValueError:
                    valid_values = [e.value for e in EnumActionCategory]
                    message = (
                        f"Invalid category value: {v}. Must be one of {valid_values}"
                    )
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=message,
                        details=ModelErrorContext.with_context(
                            {
                                "error_type": ModelSchemaValue.from_value(
                                    "valueerror",
                                ),
                                "validation_context": ModelSchemaValue.from_value(
                                    "model_validation",
                                ),
                            },
                        ),
                    ) from None

            # Invalid type
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Category must be None or EnumActionCategory, got {type(v)}",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("typeerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        return v

    @field_validator("action_display_name")
    @classmethod
    def validate_action_display_name(cls, v: str) -> str:
        """Validate action display name pattern."""
        # Pattern: lowercase letter, followed by lowercase letters,
        # numbers, or underscores
        import re

        pattern = r"^[a-z][a-z0-9_]*$"
        if not re.match(pattern, v):
            message = (
                "action_display_name must match pattern: start with "
                "lowercase letter and contain only lowercase letters, "
                "numbers, and underscores"
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=message,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        return v

    @model_validator(mode="before")
    @classmethod
    def compute_action_name_id(cls, values: dict[str, object]) -> dict[str, object]:
        """Compute action_name_id from action_display_name if not provided."""
        if isinstance(values, dict):
            # Get action_name from either the direct field or the alias
            action_name = values.get("action_display_name") or values.get("action_name")

            # If action_name_id is not provided but action_name is, compute it
            if (
                "action_name_id" not in values
                and action_name
                and isinstance(action_name, str)
            ):
                import hashlib

                action_hash = hashlib.sha256(action_name.encode()).hexdigest()
                action_name_id = UUID(
                    f"{action_hash[:8]}-{action_hash[8:12]}-{action_hash[12:16]}-{action_hash[16:20]}-{action_hash[20:32]}",
                )
                values["action_name_id"] = action_name_id
        return values

    @classmethod
    def from_contract_action(
        cls,
        action_name: str,
        node_id: UUID,
        node_name: str,
        description: str | None = None,
        **kwargs: object,
    ) -> ModelCliAction:
        """Factory method for creating actions from contract data."""
        # Validate input types first using Pydantic validation
        cls.model_validate(
            {
                "action_id": "00000000-0000-0000-0000-000000000000",
                "action_name_id": "00000000-0000-0000-0000-000000000000",
                # Use alias to validate action_display_name
                "action_name": action_name,
                "node_id": node_id,  # This will trigger validation
                # Use alias to validate node_display_name
                "node_name": node_name,
                "description": description or "test",  # Trigger validation
            },
        )

        # Extract known fields with proper types from kwargs
        action_id = kwargs.get("action_id")
        deprecated = kwargs.get("deprecated", False)
        category = kwargs.get("category")

        # Type validation for extracted kwargs
        if action_id is not None and not isinstance(action_id, UUID):
            action_id = None  # Use default UUID generation
        if not isinstance(deprecated, bool):
            deprecated = False
        # category is now stored directly without ModelSchemaValue wrapping

        # Return instance with typed arguments - Pydantic will validate
        # Use default description only if None, preserve empty strings
        final_description = (
            description
            if description is not None
            else f"{action_name} action for {node_name}"
        )

        # action_name_id will be computed automatically by the model validator
        # Don't pass action_name_id manually - let the validator compute it
        # from action_name hash
        if action_id is not None:
            return cls(
                action_id=action_id,
                action_name=action_name,  # Use alias
                node_id=node_id,
                node_name=node_name,  # Use alias
                description=final_description,
                deprecated=deprecated,
                category=category,
            )
        return cls(
            action_name=action_name,  # Use alias
            node_id=node_id,
            node_name=node_name,  # Use alias
            description=final_description,
            deprecated=deprecated,
            category=category,
        )

    def get_qualified_name(self) -> str:
        """Get fully qualified action name."""
        return f"{self.node_display_name}:{self.action_display_name}"

    def get_globally_unique_id(self) -> str:
        """Get globally unique identifier combining action_id and node_id."""
        return f"{self.node_id}:{self.action_id}"

    def matches(self, action_name: str) -> bool:
        """Check if this action matches the given action name."""
        return self.action_display_name == action_name

    def matches_node_id(self, node_id: UUID) -> bool:
        """Check if this action belongs to the specified node ID."""
        return self.node_id == node_id

    def matches_action_id(self, action_id: UUID) -> bool:
        """Check if this action has the specified action ID."""
        return self.action_id == action_id

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        populate_by_name=True,  # Allow both field name and alias
    )

    @allow_dict_any
    # NOTE(OMN-1201): Override uses **kwargs to pass through to parent while setting
    # by_alias=True default. Signature is functionally compatible but mypy strict mode
    # flags the **kwargs pattern vs explicit parameters as incompatible.
    def model_dump(  # type: ignore[override]
        self, **kwargs: Any
    ) -> TypedDictCliActionSerialized:
        """Override model_dump to use aliases by default."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)  # type: ignore[return-value]

    # Protocol method implementations

    @allow_dict_any
    def serialize(self) -> TypedDictCliActionSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True
