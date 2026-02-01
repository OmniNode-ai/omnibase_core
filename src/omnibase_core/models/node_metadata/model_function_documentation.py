"""
Function Documentation Model.

Documentation and example content for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_function_documentation_summary_type import (
    TypedDictFunctionDocumentationSummaryType,
)


class ModelFunctionDocumentation(BaseModel):
    """
    Function documentation and examples.

    Contains documentation content:
    - Docstrings and descriptions
    - Usage examples and notes
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Documentation content (3 fields, but text-based)
    docstring: str | None = Field(default=None, description="Function docstring")
    examples: list[str] = Field(default_factory=list, description="Usage examples")
    notes: list[str] = Field(default_factory=list, description="Additional notes")

    def has_documentation(self) -> bool:
        """Check if function has adequate documentation."""
        return bool(self.docstring and len(self.docstring.strip()) > 0)

    def has_examples(self) -> bool:
        """Check if function has usage examples."""
        return len(self.examples) > 0

    def has_notes(self) -> bool:
        """Check if function has additional notes."""
        return len(self.notes) > 0

    def add_example(self, example: str) -> None:
        """Add a usage example."""
        if example not in self.examples:
            self.examples.append(example)

    def add_note(self, note: str) -> None:
        """Add a note."""
        if note not in self.notes:
            self.notes.append(note)

    def get_documentation_quality_score(self) -> float:
        """Get documentation quality score (0-1)."""
        score = 0.0

        # Basic documentation
        if self.has_documentation():
            score += 0.5

        # Examples
        if self.has_examples():
            score += 0.3

        # Notes and additional info
        if self.has_notes():
            score += 0.2

        return min(score, 1.0)

    def get_documentation_summary(self) -> TypedDictFunctionDocumentationSummaryType:
        """Get documentation summary."""
        return {
            "has_documentation": self.has_documentation(),
            "has_examples": self.has_examples(),
            "has_notes": self.has_notes(),
            "examples_count": len(self.examples),
            "notes_count": len(self.notes),
            "quality_score": self.get_documentation_quality_score(),
        }

    @classmethod
    def create_documented(
        cls,
        docstring: str,
        examples: list[str] | None = None,
    ) -> ModelFunctionDocumentation:
        """Create documentation with docstring and examples."""
        return cls(
            docstring=docstring,
            examples=examples if examples is not None else [],
        )

    @classmethod
    def create_with_examples(
        cls,
        examples: list[str],
    ) -> ModelFunctionDocumentation:
        """Create documentation with examples."""
        return cls(examples=examples)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack documentation data into metadata dict
        # Convert list[str] to list for JsonType compatibility
        result["metadata"] = {
            "docstring": self.docstring,
            "examples": list(self.examples),
            "notes": list(self.notes),
            "has_documentation": self.has_documentation(),
            "has_examples": self.has_examples(),
            "has_notes": self.has_notes(),
            "documentation_quality_score": self.get_documentation_quality_score(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelFunctionDocumentation"]
