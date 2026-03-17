# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Retrieval Source Model for Context Integrity.

Defines where an agent is allowed to retrieve context from, including
the source type, namespace, optional key filters, and result limit.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_retrieval_source_type import EnumRetrievalSourceType


class ModelRetrievalSource(BaseModel):
    """
    Configuration for a single retrieval source in context integrity.

    Defines where an agent is allowed to retrieve context from, including
    the source type, namespace, optional key filters, and result limit.
    """

    source_type: EnumRetrievalSourceType = Field(
        ...,
        description="Type of retrieval source: VECTOR, STRUCTURED, or FILE",
    )

    namespace: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Namespace or collection name for the retrieval source",
    )

    keys: list[str] = Field(
        default_factory=list,
        description="Optional key filters to restrict retrieval scope",
    )

    k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results to retrieve from this source",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        use_enum_values=False,
    )


__all__ = [
    "ModelRetrievalSource",
]
