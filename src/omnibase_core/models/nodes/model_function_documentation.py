"""
Function Documentation Model.

Documentation and example content for functions.
Part of the ModelFunctionNodeMetadata restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelFunctionDocumentation(BaseModel):
    """
    Function documentation and examples.

    Contains documentation content:
    - Docstrings and descriptions
    - Usage examples and notes
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

    def get_documentation_summary(self) -> dict[str, bool | int | float]:
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
            examples=examples or [],
        )

    @classmethod
    def create_with_examples(
        cls,
        examples: list[str],
    ) -> ModelFunctionDocumentation:
        """Create documentation with examples."""
        return cls(examples=examples)


# Export for use
__all__ = ["ModelFunctionDocumentation"]
