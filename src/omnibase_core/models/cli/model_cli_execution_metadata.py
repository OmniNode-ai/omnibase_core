"""
CLI Execution Metadata Model.

Metadata and custom context for CLI command execution.
Part of the ModelCliExecution restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators import allow_dict_any
from omnibase_core.enums.enum_context_source import EnumContextSource
from omnibase_core.enums.enum_context_type import EnumContextType
from omnibase_core.types.typed_dict_cli_execution_metadata_serialized import (
    TypedDictCliExecutionMetadataSerialized,
)

from .model_cli_execution_context import ModelCliExecutionContext


class ModelCliExecutionMetadata(BaseModel):
    """
    CLI execution metadata and custom context.

    Contains tags, categories, and custom context data
    for CLI command execution without cluttering core execution info.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Custom metadata for extensibility
    custom_context: dict[str, ModelCliExecutionContext] = Field(
        default_factory=dict,
        description="Custom execution context",
    )
    execution_tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing execution",
    )

    def add_tag(self, tag: str) -> None:
        """Add an execution tag."""
        if tag not in self.execution_tags:
            self.execution_tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove an execution tag."""
        if tag in self.execution_tags:
            self.execution_tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if tag exists."""
        return tag in self.execution_tags

    def clear_tags(self) -> None:
        """Clear all tags."""
        self.execution_tags.clear()

    def add_context(self, key: str, context: ModelCliExecutionContext) -> None:
        """Add custom context data."""
        self.custom_context[key] = context

    def get_context(
        self,
        key: str,
        default: ModelCliExecutionContext | None = None,
    ) -> ModelCliExecutionContext | None:
        """Get custom context data."""
        return self.custom_context.get(key, default)

    def remove_context(self, key: str) -> None:
        """Remove custom context data."""
        if key in self.custom_context:
            del self.custom_context[key]

    def has_context(self, key: str) -> bool:
        """Check if context key exists."""
        return key in self.custom_context

    def clear_context(self) -> None:
        """Clear all custom context."""
        self.custom_context.clear()

    def add_failure_reason(self, reason: str) -> None:
        """Add failure reason to context."""
        failure_context = ModelCliExecutionContext(
            key="failure_reason",
            value=reason,
            context_type=EnumContextType.SYSTEM,
            source=EnumContextSource.SYSTEM,
            description="Execution failure reason",
        )
        self.custom_context["failure_reason"] = failure_context

    def get_failure_reason(self) -> str | None:
        """Get failure reason from context."""
        failure_context = self.get_context("failure_reason")
        return str(failure_context.value) if failure_context else None

    @classmethod
    def create_tagged(cls, tags: list[str]) -> ModelCliExecutionMetadata:
        """Create metadata with specified tags."""
        return cls(execution_tags=tags)

    @classmethod
    def create_with_context(
        cls,
        context: dict[str, ModelCliExecutionContext],
    ) -> ModelCliExecutionMetadata:
        """Create metadata with custom context."""
        return cls(custom_context=context)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    @allow_dict_any
    def serialize(self) -> TypedDictCliExecutionMetadataSerialized:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)  # type: ignore[return-value]

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


# Export for use
__all__ = ["ModelCliExecutionMetadata"]
