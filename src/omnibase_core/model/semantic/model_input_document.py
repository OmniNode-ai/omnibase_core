"""
Input document model for preprocessing operations.

Provides strongly-typed document structure to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelInputDocument(BaseModel):
    """
    A document to be processed by the preprocessing engine.

    Replaces Dict[str, Any] usage in documents fields.
    """

    document_id: str = Field(description="Unique identifier for the document")

    content: str = Field(description="Raw document content to be processed")

    title: str | None = Field(
        default=None,
        description="Document title if available",
    )

    source_path: str | None = Field(
        default=None,
        description="Original file path or URL",
    )

    content_type: str | None = Field(
        default=None,
        description="MIME type or content type",
    )

    language: str | None = Field(
        default=None,
        description="Document language code (e.g., 'en', 'es')",
    )

    encoding: str | None = Field(default="utf-8", description="Text encoding")

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional document metadata (string values only)",
    )

    author: str | None = Field(
        default=None,
        description="Document author if available",
    )

    created_date: str | None = Field(
        default=None,
        description="Document creation date (ISO format)",
    )

    modified_date: str | None = Field(
        default=None,
        description="Document modification date (ISO format)",
    )

    file_size_bytes: int | None = Field(
        default=None,
        description="Original file size in bytes",
    )

    processing_priority: int | None = Field(
        default=None,
        description="Processing priority (1-10, higher = more urgent)",
    )

    skip_validation: bool = Field(
        default=False,
        description="Whether to skip content validation",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
