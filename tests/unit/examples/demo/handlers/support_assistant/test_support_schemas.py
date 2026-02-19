# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for SupportRequest and SupportResponse Pydantic models.

This module tests the input/output schemas for the OMN-1201 Demo Support Assistant.
Following TDD approach - these tests are written before the implementation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from examples.demo.handlers.support_assistant.model_support_request import (
    SupportRequest,
)
from examples.demo.handlers.support_assistant.model_support_response import (
    SupportResponse,
)


@pytest.mark.unit
class TestSupportRequest:
    """Tests for SupportRequest input schema."""

    def test_request_requires_user_identifier(self) -> None:
        """user_identifier is required."""
        with pytest.raises(ValidationError) as exc_info:
            SupportRequest(message="Help me please")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("user_identifier",) for e in errors)

    def test_request_requires_message(self) -> None:
        """message is required."""
        with pytest.raises(ValidationError) as exc_info:
            SupportRequest(user_identifier="user123")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message",) for e in errors)

    def test_request_with_required_fields_only(self) -> None:
        """Request can be created with only required fields."""
        request = SupportRequest(user_identifier="user123", message="I need help")

        assert request.user_identifier == "user123"
        assert request.message == "I need help"

    def test_request_urgency_defaults_to_medium(self) -> None:
        """urgency defaults to 'medium' when not specified."""
        request = SupportRequest(user_identifier="user123", message="Help")

        assert request.urgency == "medium"

    def test_request_context_is_optional(self) -> None:
        """context field is optional and defaults to None."""
        request = SupportRequest(user_identifier="user123", message="Help")

        assert request.context is None

    def test_request_with_context(self) -> None:
        """context can be provided as a dict."""
        context = {"previous_message": "Hello", "ticket_id": "T123"}
        request = SupportRequest(
            user_identifier="user123",
            message="Follow up",
            context=context,
        )

        assert request.context == context

    def test_request_urgency_low(self) -> None:
        """urgency can be set to 'low'."""
        request = SupportRequest(
            user_identifier="user123",
            message="Question",
            urgency="low",
        )

        assert request.urgency == "low"

    def test_request_urgency_high(self) -> None:
        """urgency can be set to 'high'."""
        request = SupportRequest(
            user_identifier="user123",
            message="Urgent issue",
            urgency="high",
        )

        assert request.urgency == "high"

    def test_request_invalid_urgency_rejected(self) -> None:
        """Invalid urgency values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SupportRequest(
                user_identifier="user123",
                message="Help",
                urgency="critical",  # Invalid value
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("urgency",) for e in errors)

    def test_request_with_all_fields(self) -> None:
        """Request can be created with all fields specified."""
        request = SupportRequest(
            user_identifier="user456",
            message="I have an issue",
            context={"session": "abc123"},
            urgency="high",
        )

        assert request.user_identifier == "user456"
        assert request.message == "I have an issue"
        assert request.context == {"session": "abc123"}
        assert request.urgency == "high"


@pytest.mark.unit
class TestSupportResponse:
    """Tests for SupportResponse output schema."""

    def test_response_has_all_fields(self) -> None:
        """Response includes all required fields."""
        response = SupportResponse(
            response_text="Here is your answer",
            suggested_actions=["Check FAQ", "Contact billing"],
            confidence=0.85,
            requires_escalation=False,
            category="billing",
            sentiment="neutral",
        )

        assert response.response_text == "Here is your answer"
        assert response.suggested_actions == ["Check FAQ", "Contact billing"]
        assert response.confidence == 0.85
        assert response.requires_escalation is False
        assert response.category == "billing"
        assert response.sentiment == "neutral"

    def test_response_requires_response_text(self) -> None:
        """response_text is required."""
        with pytest.raises(ValidationError) as exc_info:
            SupportResponse(
                suggested_actions=[],
                confidence=0.5,
                requires_escalation=False,
                category="general",
                sentiment="neutral",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("response_text",) for e in errors)

    def test_response_suggested_actions_defaults_to_empty_list(self) -> None:
        """suggested_actions defaults to empty list when not provided."""
        response = SupportResponse(
            response_text="Answer",
            confidence=0.5,
            requires_escalation=False,
            category="general",
            sentiment="neutral",
        )

        assert response.suggested_actions == []

    def test_confidence_in_valid_range(self) -> None:
        """Confidence is between 0 and 1."""
        response = SupportResponse(
            response_text="Answer",
            suggested_actions=[],
            confidence=0.75,
            requires_escalation=False,
            category="general",
            sentiment="neutral",
        )

        assert 0.0 <= response.confidence <= 1.0

    def test_confidence_boundary_zero(self) -> None:
        """Confidence of 0.0 is valid."""
        response = SupportResponse(
            response_text="Answer",
            suggested_actions=[],
            confidence=0.0,
            requires_escalation=False,
            category="general",
            sentiment="neutral",
        )

        assert response.confidence == 0.0

    def test_confidence_boundary_one(self) -> None:
        """Confidence of 1.0 is valid."""
        response = SupportResponse(
            response_text="Answer",
            suggested_actions=[],
            confidence=1.0,
            requires_escalation=False,
            category="general",
            sentiment="positive",
        )

        assert response.confidence == 1.0

    def test_confidence_negative_rejected(self) -> None:
        """Negative confidence is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SupportResponse(
                response_text="Answer",
                suggested_actions=[],
                confidence=-0.1,
                requires_escalation=False,
                category="general",
                sentiment="neutral",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_confidence_greater_than_one_rejected(self) -> None:
        """Confidence greater than 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SupportResponse(
                response_text="Answer",
                suggested_actions=[],
                confidence=1.5,
                requires_escalation=False,
                category="general",
                sentiment="neutral",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_category_is_valid_enum(self) -> None:
        """Category is one of the allowed values."""
        for category in ["billing", "technical", "general", "account"]:
            response = SupportResponse(
                response_text="Answer",
                suggested_actions=[],
                confidence=0.5,
                requires_escalation=False,
                category=category,
                sentiment="neutral",
            )
            assert response.category == category

    def test_category_invalid_rejected(self) -> None:
        """Invalid category values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SupportResponse(
                response_text="Answer",
                suggested_actions=[],
                confidence=0.5,
                requires_escalation=False,
                category="sales",  # Invalid
                sentiment="neutral",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("category",) for e in errors)

    def test_sentiment_valid_values(self) -> None:
        """Sentiment is one of the allowed values."""
        for sentiment in ["positive", "neutral", "negative"]:
            response = SupportResponse(
                response_text="Answer",
                suggested_actions=[],
                confidence=0.5,
                requires_escalation=False,
                category="general",
                sentiment=sentiment,
            )
            assert response.sentiment == sentiment

    def test_sentiment_invalid_rejected(self) -> None:
        """Invalid sentiment values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SupportResponse(
                response_text="Answer",
                suggested_actions=[],
                confidence=0.5,
                requires_escalation=False,
                category="general",
                sentiment="angry",  # Invalid
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sentiment",) for e in errors)

    def test_requires_escalation_true(self) -> None:
        """requires_escalation can be True."""
        response = SupportResponse(
            response_text="I need to escalate this",
            suggested_actions=["Contact manager"],
            confidence=0.3,
            requires_escalation=True,
            category="technical",
            sentiment="negative",
        )

        assert response.requires_escalation is True

    def test_suggested_actions_empty_list(self) -> None:
        """suggested_actions can be an empty list."""
        response = SupportResponse(
            response_text="No actions needed",
            suggested_actions=[],
            confidence=0.9,
            requires_escalation=False,
            category="general",
            sentiment="positive",
        )

        assert response.suggested_actions == []

    def test_suggested_actions_multiple_items(self) -> None:
        """suggested_actions can have multiple items."""
        actions = ["Step 1", "Step 2", "Step 3"]
        response = SupportResponse(
            response_text="Follow these steps",
            suggested_actions=actions,
            confidence=0.8,
            requires_escalation=False,
            category="technical",
            sentiment="neutral",
        )

        assert response.suggested_actions == actions
        assert len(response.suggested_actions) == 3
