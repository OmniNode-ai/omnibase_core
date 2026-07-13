# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Event Bus Topic Entry Model.

The model for a single topic entry in the event bus
configuration, containing the realm-agnostic topic string and
optional tooling metadata.

Key Design Decisions:
    1. Topics stored as realm-agnostic strings (e.g., "onex.evt.intent-classified.v1")  # onex-topic-allow: pending contract auto-wiring
    2. Metadata fields (event_type, message_category, description) are tooling-only
    3. Routing uses ONLY the topic string - never metadata fields
    4. Model is frozen (immutable) with extra="forbid" for safety
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEventBusTopicEntry(BaseModel):
    """Single topic entry with optional metadata.

    IMPORTANT: Routing depends ONLY on the `topic` string.
    Metadata fields (event_type, message_category, description) are
    tooling-facing only and are never used for routing decisions.

    Attributes:
        topic: Realm-agnostic topic string (e.g., "onex.evt.intent-classified.v1").  # onex-topic-allow: pending contract auto-wiring
            This is the ONLY field used for routing.
        event_type: Optional event model name. Tooling metadata only.
        message_category: Message category (EVENT, COMMAND, INTENT).
            Tooling metadata only. Defaults to "EVENT".
        description: Optional human-readable description. Tooling metadata only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(
        ...,
        description="Realm-agnostic topic string (e.g., 'onex.evt.intent-classified.v1'). "  # onex-topic-allow: pending contract auto-wiring
        "This is the ONLY field used for routing.",
    )
    event_type: str | None = Field(
        default=None,
        description="Optional event model name. Tooling metadata only - never used for routing.",
    )
    message_category: str = Field(
        default="EVENT",
        description="Message category (EVENT, COMMAND, INTENT). "
        "Tooling metadata only - never used for routing.",
    )
    description: str | None = Field(
        default=None,
        description="Optional human-readable description. Tooling metadata only.",
    )


__all__ = ["ModelEventBusTopicEntry"]
