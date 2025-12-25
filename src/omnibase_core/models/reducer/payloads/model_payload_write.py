"""
PayloadWrite - Typed payload for file/storage write intents.

This module provides the PayloadWrite model for file and storage
write operations from Reducers. The Effect node receives the intent
and performs the write operation to the configured storage backend.

Design Pattern:
    Reducers emit this payload when data should be written to a file
    or object storage. This separation ensures Reducer purity - the
    Reducer declares the desired outcome without performing the actual
    side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import PayloadWrite
    >>>
    >>> payload = PayloadWrite(
    ...     path="s3://bucket/reports/daily-2024-01-15.json",
    ...     content='{"summary": "daily report", "items": 150}',
    ...     content_type="application/json",
    ...     metadata={"generator": "report-service", "version": "1.0"},
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_intent_payload_union: Union type
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)


class PayloadWrite(ModelIntentPayloadBase):
    """Payload for file/storage write intents.

    Emitted by Reducers when data should be written to a file or object storage.
    The Effect node executes this intent by performing the write operation to
    the configured storage backend (filesystem, S3, GCS, etc.).

    Supports various content types and optional metadata for storage systems.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "write".
            Placed first for optimal union type resolution performance.
        path: Target path for the write operation. For filesystems, this is
            the file path. For object storage, this is the object key.
        content: The content to write as a string. For text content (JSON, YAML,
            plain text), pass directly. For binary data (images, PDFs, etc.),
            encode to base64 using `base64.b64encode(data).decode('ascii')`.
        content_type: MIME type of the content (e.g., "application/json",
            "image/png", "application/pdf"). Used by Effect to determine if
            base64 decoding is needed for binary types.
        encoding: Text encoding for string content (default: "utf-8").
        create_dirs: Whether to create parent directories if they don't exist.
        overwrite: Whether to overwrite existing files (default: True).
        metadata: Optional metadata for object storage systems.

    Example:
        >>> payload = PayloadWrite(
        ...     path="s3://bucket/reports/daily-2024-01-15.json",
        ...     content='{"summary": "daily report", "items": 150}',
        ...     content_type="application/json",
        ...     metadata={"generator": "report-service", "version": "1.0"},
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["write"] = Field(
        default="write",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    path: str = Field(
        ...,
        description=(
            "Target path for the write operation. For filesystems, use absolute "
            "or relative paths. For object storage, use URI format (s3://, gs://)."
        ),
        min_length=1,
        max_length=1024,
    )

    content: str = Field(
        ...,
        description=(
            "The content to write as a string. For text content (JSON, YAML, plain text), "
            "pass the string directly. For binary data (images, PDFs, archives), encode "
            "to base64 string using `base64.b64encode(data).decode('ascii')`. The Effect "
            "handler will decode base64 content when content_type indicates binary "
            "(e.g., 'application/octet-stream', 'image/png', 'application/pdf'). "
            "Example for binary: content=base64.b64encode(image_bytes).decode('ascii'), "
            "content_type='image/png'."
        ),
    )

    content_type: str = Field(
        default="text/plain",
        description=(
            "MIME type of the content. Examples: 'application/json', 'text/plain', "
            "'application/octet-stream'."
        ),
        max_length=128,
    )

    encoding: str = Field(
        default="utf-8",
        description="Text encoding for string content. Default is UTF-8.",
        max_length=32,
    )

    create_dirs: bool = Field(
        default=True,
        description=(
            "Whether to create parent directories if they don't exist. "
            "Only applicable for filesystem writes."
        ),
    )

    overwrite: bool = Field(
        default=True,
        description=(
            "Whether to overwrite existing files. If False and file exists, "
            "the Effect should raise an error or skip."
        ),
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Optional metadata for object storage systems. Keys and values "
            "are strings. Common keys: 'Content-Disposition', 'Cache-Control'."
        ),
    )


__all__ = [
    "PayloadWrite",
]
