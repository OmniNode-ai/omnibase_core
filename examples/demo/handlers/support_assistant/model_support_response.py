# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""SupportResponse model for OMN-1201 Demo Support Assistant.

This module defines the output schema for the support assistant handler.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportResponse(BaseModel):  # type: ignore[explicit-any]
    """Output schema for support assistant.

    This model represents the AI assistant's response to a support request,
    including the response text, suggested actions, and metadata about the
    classification and confidence of the response.

    Attributes:
        response_text: The assistant's response message to the user.
        suggested_actions: List of recommended next steps for the user.
        confidence: Confidence score of the response (0.0 to 1.0).
        requires_escalation: Whether the issue needs human escalation.
        category: Classification of the support request type.
        sentiment: Detected sentiment of the user's message.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_text: str = Field(
        ...,
        description="The assistant's response message to the user",
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="List of recommended next steps for the user",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the response (0.0 to 1.0)",
    )
    requires_escalation: bool = Field(
        ...,
        description="Whether the issue needs human escalation",
    )
    category: Literal["billing", "technical", "general", "account"] = Field(
        ...,
        description="Classification of the support request type",
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        ...,
        description="Detected sentiment of the user's message",
    )


__all__ = ["SupportResponse"]
