# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for PayloadNotify.

This module tests the PayloadNotify model for notification intents, verifying:
1. Field validation (channel, recipients, subject, body, priority, etc.)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import PayloadNotify


@pytest.mark.unit
class TestPayloadNotifyInstantiation:
    """Test PayloadNotify instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
        )
        assert payload.channel == "email"
        assert payload.recipients == ["test@example.com"]
        assert payload.subject == "Test Subject"
        assert payload.body == "Test Body"
        assert payload.intent_type == "notify"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        template_id = uuid4()
        payload = PayloadNotify(
            channel="slack",
            recipients=["#engineering-alerts", "#ops"],
            subject="Build Failed",
            body="Build #1234 failed in production pipeline",
            priority="high",
            template_id=template_id,
            template_vars={"build_id": "1234", "env": "production"},
            metadata={"service": "ci-cd", "pipeline": "deploy"},
        )
        assert payload.channel == "slack"
        assert payload.recipients == ["#engineering-alerts", "#ops"]
        assert payload.subject == "Build Failed"
        assert payload.body == "Build #1234 failed in production pipeline"
        assert payload.priority == "high"
        assert payload.template_id == template_id
        assert payload.template_vars == {"build_id": "1234", "env": "production"}
        assert payload.metadata == {"service": "ci-cd", "pipeline": "deploy"}


@pytest.mark.unit
class TestPayloadNotifyDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'notify'."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        assert payload.intent_type == "notify"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        data = payload.model_dump()
        assert data["intent_type"] == "notify"


@pytest.mark.unit
class TestPayloadNotifyChannelValidation:
    """Test channel field validation."""

    def test_valid_channels(self) -> None:
        """Test all valid notification channels."""
        valid_channels = ["email", "sms", "slack", "pagerduty", "webhook", "teams"]
        for channel in valid_channels:
            payload = PayloadNotify(
                channel=channel,  # type: ignore[arg-type]
                recipients=["recipient"],
                subject="Test",
                body="Body",
            )
            assert payload.channel == channel

    def test_invalid_channel_rejected(self) -> None:
        """Test that invalid channel is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="invalid",  # type: ignore[arg-type]
                recipients=["recipient"],
                subject="Test",
                body="Body",
            )
        assert "channel" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadNotifyRecipientsValidation:
    """Test recipients field validation."""

    def test_recipients_required(self) -> None:
        """Test that recipients is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(channel="email", subject="Test", body="Body")  # type: ignore[call-arg]
        assert "recipients" in str(exc_info.value)

    def test_recipients_min_length(self) -> None:
        """Test recipients minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=[],
                subject="Test",
                body="Body",
            )
        assert "recipients" in str(exc_info.value)

    def test_recipients_accepts_multiple(self) -> None:
        """Test recipients accepts multiple entries."""
        payload = PayloadNotify(
            channel="email",
            recipients=["a@test.com", "b@test.com", "c@test.com"],
            subject="Test",
            body="Body",
        )
        assert len(payload.recipients) == 3


@pytest.mark.unit
class TestPayloadNotifySubjectValidation:
    """Test subject field validation."""

    def test_subject_required(self) -> None:
        """Test that subject is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                body="Body",
            )  # type: ignore[call-arg]
        assert "subject" in str(exc_info.value)

    def test_subject_min_length(self) -> None:
        """Test subject minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="",
                body="Body",
            )
        assert "subject" in str(exc_info.value)

    def test_subject_max_length(self) -> None:
        """Test subject maximum length validation."""
        long_subject = "a" * 257
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject=long_subject,
                body="Body",
            )
        assert "subject" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadNotifyBodyValidation:
    """Test body field validation."""

    def test_body_required(self) -> None:
        """Test that body is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
            )  # type: ignore[call-arg]
        assert "body" in str(exc_info.value)

    def test_body_min_length(self) -> None:
        """Test body minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
                body="",
            )
        assert "body" in str(exc_info.value)

    def test_body_max_length(self) -> None:
        """Test body maximum length validation."""
        long_body = "a" * 16385
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
                body=long_body,
            )
        assert "body" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadNotifyPriorityValidation:
    """Test priority field validation."""

    def test_valid_priorities(self) -> None:
        """Test all valid priority levels."""
        valid_priorities = ["low", "normal", "high", "critical"]
        for priority in valid_priorities:
            payload = PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
                body="Body",
                priority=priority,  # type: ignore[arg-type]
            )
            assert payload.priority == priority

    def test_invalid_priority_rejected(self) -> None:
        """Test that invalid priority is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
                body="Body",
                priority="urgent",  # type: ignore[arg-type]
            )
        assert "priority" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadNotifyDefaultValues:
    """Test default values."""

    def test_default_priority(self) -> None:
        """Test default priority is normal."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        assert payload.priority == "normal"

    def test_default_template_id(self) -> None:
        """Test default template_id is None."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        assert payload.template_id is None

    def test_default_template_vars(self) -> None:
        """Test default template_vars is empty dict."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        assert payload.template_vars == {}

    def test_default_metadata(self) -> None:
        """Test default metadata is empty dict."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        assert payload.metadata == {}


@pytest.mark.unit
class TestPayloadNotifyImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_channel(self) -> None:
        """Test that channel cannot be modified after creation."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        with pytest.raises(ValidationError):
            payload.channel = "slack"  # type: ignore[misc]

    def test_cannot_modify_subject(self) -> None:
        """Test that subject cannot be modified after creation."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        with pytest.raises(ValidationError):
            payload.subject = "New Subject"  # type: ignore[misc]


@pytest.mark.unit
class TestPayloadNotifySerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        template_id = uuid4()
        original = PayloadNotify(
            channel="slack",
            recipients=["#alerts"],
            subject="Alert",
            body="System alert",
            priority="high",
            template_id=template_id,
            template_vars={"key": "value"},
            metadata={"source": "monitoring"},
        )
        data = original.model_dump()
        restored = PayloadNotify.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        json_str = original.model_dump_json()
        restored = PayloadNotify.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = PayloadNotify(
            channel="email",
            recipients=["test@example.com"],
            subject="Test",
            body="Body",
        )
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "channel",
            "recipients",
            "subject",
            "body",
            "priority",
            "template_id",
            "template_vars",
            "metadata",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestPayloadNotifyExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadNotify(
                channel="email",
                recipients=["test@example.com"],
                subject="Test",
                body="Body",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
