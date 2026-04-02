# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelChannelEnvelope and ModelChannelAttachment."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_channel_type import EnumChannelType
from omnibase_core.models.channel.model_channel_attachment import (
    ModelChannelAttachment,
)
from omnibase_core.models.channel.model_channel_envelope import ModelChannelEnvelope


def _make_envelope(**overrides: object) -> ModelChannelEnvelope:
    """Build a valid envelope with sensible defaults, overriding as needed."""
    defaults: dict[str, object] = {
        "channel_id": "general",
        "channel_type": EnumChannelType.DISCORD,
        "sender_id": "user-123",
        "message_text": "Hello world",
        "message_id": "msg-456",
        "timestamp": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    return ModelChannelEnvelope(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelChannelAttachment:
    """Test cases for ModelChannelAttachment."""

    def test_minimal_attachment(self) -> None:
        att = ModelChannelAttachment(filename="doc.pdf", content_type="application/pdf")
        assert att.filename == "doc.pdf"
        assert att.content_type == "application/pdf"
        assert att.url is None
        assert att.size_bytes is None

    def test_full_attachment(self) -> None:
        att = ModelChannelAttachment(
            filename="image.png",
            content_type="image/png",
            url="https://cdn.example.com/image.png",
            size_bytes=1024,
        )
        assert att.url == "https://cdn.example.com/image.png"
        assert att.size_bytes == 1024

    def test_frozen(self) -> None:
        att = ModelChannelAttachment(filename="a.txt", content_type="text/plain")
        with pytest.raises(ValidationError):
            att.filename = "b.txt"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ModelChannelAttachment(
                filename="a.txt",
                content_type="text/plain",
                extra_field="bad",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelChannelEnvelope:
    """Test cases for ModelChannelEnvelope."""

    def test_minimal_envelope(self) -> None:
        env = _make_envelope()
        assert env.channel_id == "general"
        assert env.channel_type == EnumChannelType.DISCORD
        assert env.sender_id == "user-123"
        assert env.message_text == "Hello world"
        assert env.message_id == "msg-456"
        assert env.sender_display_name == ""
        assert env.thread_id is None
        assert env.attachments == ()
        assert env.metadata == {}
        assert env.reply_to is None
        assert isinstance(env.correlation_id, UUID)

    def test_all_fields(self) -> None:
        cid = uuid4()
        ts = datetime.now(tz=UTC)
        att = ModelChannelAttachment(filename="f.txt", content_type="text/plain")
        env = _make_envelope(
            channel_type=EnumChannelType.SLACK,
            sender_display_name="Alice",
            thread_id="thread-1",
            attachments=(att,),
            timestamp=ts,
            correlation_id=cid,
            metadata={"guild_id": "12345"},
            reply_to="msg-100",
        )
        assert env.channel_type == EnumChannelType.SLACK
        assert env.sender_display_name == "Alice"
        assert env.thread_id == "thread-1"
        assert len(env.attachments) == 1
        assert env.attachments[0].filename == "f.txt"
        assert env.correlation_id == cid
        assert env.metadata == {"guild_id": "12345"}
        assert env.reply_to == "msg-100"

    def test_frozen(self) -> None:
        env = _make_envelope()
        with pytest.raises(ValidationError):
            env.message_text = "changed"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_envelope(extra_bad="nope")

    def test_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelChannelEnvelope()  # type: ignore[call-arg]

    def test_channel_type_accepts_enum(self) -> None:
        for ct in list(EnumChannelType):
            env = _make_envelope(channel_type=ct)
            assert env.channel_type == ct

    def test_round_trip_serialization(self) -> None:
        env = _make_envelope()
        data = env.model_dump(mode="json")
        restored = ModelChannelEnvelope.model_validate(data)
        assert restored.channel_id == env.channel_id
        assert restored.channel_type == env.channel_type
        assert restored.message_text == env.message_text
        assert restored.correlation_id == env.correlation_id

    def test_empty_channel_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_envelope(channel_id="")

    def test_empty_sender_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_envelope(sender_id="")

    def test_empty_message_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_envelope(message_id="")

    def test_importable_from_package(self) -> None:
        from omnibase_core.models.channel import (
            ModelChannelAttachment as A,
        )
        from omnibase_core.models.channel import (
            ModelChannelEnvelope as E,
        )

        assert A is ModelChannelAttachment
        assert E is ModelChannelEnvelope
