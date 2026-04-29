# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Document reference model for doc freshness scanning."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_doc_reference_type import EnumDocReferenceType

_MAX_STRING_LENGTH = 10000


class ModelDocReference(BaseModel):
    """A single reference extracted from a documentation file.

    Represents a code reference (file path, class name, function name,
    command, URL, or env var) found in a .md file, along with resolution
    status indicating whether the referenced target still exists.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_path: str = Field(
        ...,
        description="Path to the .md file containing the reference",
        max_length=_MAX_STRING_LENGTH,
    )
    line_number: int = Field(
        ...,
        description="Line where reference appears",
        ge=1,
    )
    reference_type: EnumDocReferenceType = Field(
        ...,
        description="What kind of reference this is",
    )
    raw_text: str = Field(
        ...,
        description="The raw text of the reference as it appears in the doc",
        max_length=_MAX_STRING_LENGTH,
    )
    resolved_target: str | None = Field(
        default=None,
        description="The absolute path or identifier the reference resolves to",
        max_length=_MAX_STRING_LENGTH,
    )
    exists: bool | None = Field(
        default=None,
        description="Whether the target exists (None = could not check)",
    )
