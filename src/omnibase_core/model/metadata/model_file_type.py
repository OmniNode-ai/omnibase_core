"""
Model for file type information used by metadata tools.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, validator

from .model_metadata_properties import ModelMetadataProperties


class ModelFileType(BaseModel):
    """Model representing a file type with metadata and configuration."""

    name: str = Field(
        ...,
        description="Canonical name of the file type (e.g., PYTHON, YAML)",
        pattern="^[A-Z][A-Z_]*$",
    )

    display_name: str = Field(..., description="Human-readable name for the file type")

    extensions: List[str] = Field(
        ..., description="File extensions associated with this type", min_items=1
    )

    mime_types: List[str] = Field(
        default_factory=list, description="MIME types for this file type"
    )

    single_line_comment: str = Field(..., description="Single line comment delimiter")

    multi_line_comment_start: Optional[str] = Field(
        None, description="Multi-line comment start delimiter"
    )

    multi_line_comment_end: Optional[str] = Field(
        None, description="Multi-line comment end delimiter"
    )

    metadata_placement: str = Field(
        "top",
        description="Where metadata blocks should be placed in the file",
        pattern="^(top|bottom|after_imports|before_class)$",
    )

    supports_function_discovery: bool = Field(
        False, description="Whether this file type supports function/method discovery"
    )

    language_id: Optional[str] = Field(
        None, description="Language identifier for syntax highlighting and parsing"
    )

    metadata: Optional[ModelMetadataProperties] = Field(
        None, description="Additional metadata and configuration"
    )

    @validator("extensions")
    def validate_extensions(cls, v):
        """Ensure all extensions start with a dot."""
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(f"Extension '{ext}' must start with a dot")
        return v

    @validator("multi_line_comment_end")
    def validate_multi_line_comments(cls, v, values):
        """Ensure both multi-line delimiters are set if one is set."""
        if v and not values.get("multi_line_comment_start"):
            raise ValueError(
                "multi_line_comment_start must be set if multi_line_comment_end is set"
            )
        if not v and values.get("multi_line_comment_start"):
            raise ValueError(
                "multi_line_comment_end must be set if multi_line_comment_start is set"
            )
        return v


# Pre-defined file type instances for common types
PYTHON_FILE_TYPE = ModelFileType(
    name="PYTHON",
    display_name="Python",
    extensions=[".py"],
    mime_types=["text/x-python", "application/x-python"],
    single_line_comment="#",
    multi_line_comment_start='"""',
    multi_line_comment_end='"""',
    supports_function_discovery=True,
    language_id="python",
)

YAML_FILE_TYPE = ModelFileType(
    name="YAML",
    display_name="YAML",
    extensions=[".yaml", ".yml"],
    mime_types=["text/yaml", "application/x-yaml"],
    single_line_comment="#",
    language_id="yaml",
)

MARKDOWN_FILE_TYPE = ModelFileType(
    name="MARKDOWN",
    display_name="Markdown",
    extensions=[".md", ".markdown"],
    mime_types=["text/markdown"],
    single_line_comment="<!--",
    multi_line_comment_start="<!--",
    multi_line_comment_end="-->",
    language_id="markdown",
)

JSON_FILE_TYPE = ModelFileType(
    name="JSON",
    display_name="JSON",
    extensions=[".json"],
    mime_types=["application/json"],
    single_line_comment="//",  # Note: JSON technically doesn't support comments
    language_id="json",
    metadata=ModelMetadataProperties(
        custom_string_1="JSON does not officially support comments"
    ),
)
