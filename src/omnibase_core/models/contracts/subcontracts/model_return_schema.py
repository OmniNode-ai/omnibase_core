# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Return Schema Model for Context Integrity.

Schema constraints for return payloads from sub-agents. Defines which fields
are allowed in return payloads and the maximum token budget for return data.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelReturnSchema(BaseModel):
    """
    Schema constraints for return payloads from sub-agents.

    Defines which fields are allowed in return payloads and the maximum
    token budget for return data.
    """

    allowed_fields: list[str] = Field(
        default_factory=list,
        description="List of field names allowed in return payloads (empty = all allowed)",
    )

    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum token budget for return payload (None = no limit)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
    )


__all__ = [
    "ModelReturnSchema",
]
