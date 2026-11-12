# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""JSON-safe runtime bus event: the message bytes base64-encoded so the model is JSON safe."""

from __future__ import annotations

import base64

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_event_message import ModelEventMessage


class ModelRuntimeBusEvent(BaseModel):
    """A runtime bus event with topic, key, value, and headers in JSON-safe form."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    topic: str = Field(min_length=1)
    key_b64: str | None = None
    value_b64: str
    headers: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_message(cls, message: ModelEventMessage) -> ModelRuntimeBusEvent:
        """Build a JSON-safe event from a ModelEventMessage (key/value are bytes; headers is ModelEventHeaders)."""
        key_b64: str | None = None
        if message.key is not None:
            key_b64 = base64.b64encode(message.key).decode("ascii")
        value_b64 = base64.b64encode(message.value).decode("ascii")
        headers = message.headers.model_dump(mode="json")
        headers_str: dict[str, str] = {
            k: str(v) for k, v in headers.items() if v is not None
        }
        return cls(
            topic=message.topic,
            key_b64=key_b64,
            value_b64=value_b64,
            headers=headers_str,
        )

    def value_bytes(self) -> bytes:
        """Decode the base64-encoded value back to bytes."""
        return base64.b64decode(self.value_b64)

    def key_bytes(self) -> bytes | None:
        """Decode the base64-encoded key back to bytes, or None if absent."""
        if self.key_b64 is None:
            return None
        return base64.b64decode(self.key_b64)


__all__: list[str] = ["ModelRuntimeBusEvent"]
