# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Channel envelope model for OmniClaw normalized messaging.

The channel envelope is the core data contract that all channel adapters
produce and the orchestrator consumes. It normalizes messages from any
messaging platform into a single schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_channel_type import EnumChannelType
from omnibase_core.models.channel.model_channel_attachment import (
    ModelChannelAttachment,
)


class ModelChannelEnvelope(BaseModel):
    """Normalized channel message envelope.

    All channel adapters (Discord, Slack, Telegram, etc.) produce instances
    of this model. The channel orchestrator consumes it, processes the
    message, and emits reply events.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Channel identification
    # string-id-ok: channel_id is a platform-specific identifier (e.g. Discord channel snowflake)
    channel_id: str = Field(
        ..., min_length=1, description="Platform-specific channel/room ID"
    )
    channel_type: EnumChannelType = Field(..., description="Messaging platform type")

    # Sender
    # string-id-ok: sender_id is a platform-specific user identifier (e.g. Discord user snowflake)
    sender_id: str = Field(..., min_length=1, description="Platform-specific user ID")
    sender_display_name: str = Field(
        default="", description="Human-readable sender name"
    )

    # Message content
    message_text: str = Field(..., description="Normalized plain-text message body")
    # string-id-ok: message_id is a platform-specific message identifier
    message_id: str = Field(
        ..., min_length=1, description="Platform-specific message ID"
    )
    # string-id-ok: thread_id is a platform-specific thread/conversation identifier
    thread_id: str | None = Field(
        default=None, description="Thread/conversation ID if threaded"
    )
    attachments: tuple[ModelChannelAttachment, ...] = Field(
        default_factory=tuple, description="Message attachments"
    )

    # Routing
    timestamp: datetime = Field(
        ..., description="Message timestamp (UTC, timezone-aware)"
    )
    correlation_id: UUID = Field(default_factory=uuid4)
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Platform-specific metadata"
    )

    # Response routing
    reply_to: str | None = Field(
        default=None,
        description="Message ID to reply to (for threaded responses)",
    )
