# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""SupportRequest model for OMN-1201 Demo Support Assistant.

This module defines the input schema for the support assistant handler.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportRequest(BaseModel):  # type: ignore[explicit-any]
    """Input schema for support assistant.

    This model represents a user's support request to the AI assistant,
    including their message, optional conversation context, and urgency level.

    Attributes:
        user_identifier: External identifier for the user making the request.
        message: The user's support message or question.
        context: Optional dictionary containing previous conversation context.
        urgency: Priority level of the request (low, medium, or high).
    """

    model_config = ConfigDict(extra="forbid")

    user_identifier: str = Field(
        ...,
        description="External identifier for the user making the request",
    )
    message: str = Field(
        ...,
        description="The user's support message or question",
    )
    context: dict[str, str] | None = Field(
        default=None,
        description="Optional previous conversation context",
    )
    urgency: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Priority level of the request",
    )


__all__ = ["SupportRequest"]
