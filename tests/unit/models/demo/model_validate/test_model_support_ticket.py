# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelSupportTicket."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumCustomerTier, EnumSupportChannel
from omnibase_core.models.demo.model_validate import ModelSupportTicket


class TestModelSupportTicketCreation:
    """Test ModelSupportTicket creation and validation."""

    def test_create_valid_ticket(self, valid_ticket_data: dict) -> None:
        """Test creating a valid ticket with typical data."""
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)

        assert ticket.ticket_id == "TKT-TEST-001"
        assert ticket.customer_tier == EnumCustomerTier.PRO
        assert ticket.channel == EnumSupportChannel.EMAIL
        assert ticket.language == "en"
        assert ticket.subject == "Test support ticket"
        assert "test support ticket body" in ticket.body.lower()

    def test_create_minimal_ticket(self, valid_ticket_data_minimal: dict) -> None:
        """Test creating a ticket with only required fields."""
        ticket = ModelSupportTicket.model_validate(valid_ticket_data_minimal)

        assert ticket.ticket_id == "TKT-TEST-002"
        assert ticket.customer_tier == EnumCustomerTier.FREE
        assert ticket.language == "en"  # Default value
        assert ticket.attachments is None
        assert ticket.product_area is None
        assert ticket.priority_hint is None
        assert ticket.previous_contact_count is None

    def test_create_full_ticket(self, valid_ticket_data_full: dict) -> None:
        """Test creating a ticket with all fields populated."""
        ticket = ModelSupportTicket.model_validate(valid_ticket_data_full)

        assert ticket.ticket_id == "TKT-TEST-003"
        assert ticket.customer_tier == EnumCustomerTier.ENTERPRISE
        assert ticket.channel == EnumSupportChannel.CHAT
        assert ticket.language == "es"
        assert ticket.attachments == ["file1.pdf", "file2.png"]
        assert ticket.product_area == "billing"
        assert ticket.priority_hint == "high"
        assert ticket.previous_contact_count == 3


class TestModelSupportTicketValidation:
    """Test ModelSupportTicket field validation."""

    def test_missing_required_field_ticket_id(self, valid_ticket_data: dict) -> None:
        """Test that missing ticket_id raises validation error."""
        del valid_ticket_data["ticket_id"]

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportTicket.model_validate(valid_ticket_data)

        assert "ticket_id" in str(exc_info.value)

    def test_missing_required_field_created_at(self, valid_ticket_data: dict) -> None:
        """Test that missing created_at raises validation error."""
        del valid_ticket_data["created_at"]

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportTicket.model_validate(valid_ticket_data)

        assert "created_at" in str(exc_info.value)

    def test_invalid_customer_tier(self, valid_ticket_data: dict) -> None:
        """Test that invalid customer_tier raises validation error."""
        valid_ticket_data["customer_tier"] = "invalid_tier"

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportTicket.model_validate(valid_ticket_data)

        assert "customer_tier" in str(exc_info.value)

    def test_invalid_channel(self, valid_ticket_data: dict) -> None:
        """Test that invalid channel raises validation error."""
        valid_ticket_data["channel"] = "phone"

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportTicket.model_validate(valid_ticket_data)

        assert "channel" in str(exc_info.value)

    def test_negative_previous_contact_count(self, valid_ticket_data: dict) -> None:
        """Test that negative previous_contact_count raises validation error."""
        valid_ticket_data["previous_contact_count"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportTicket.model_validate(valid_ticket_data)

        assert "previous_contact_count" in str(exc_info.value)

    def test_extra_fields_forbidden(self, valid_ticket_data: dict) -> None:
        """Test that extra fields are forbidden."""
        valid_ticket_data["extra_field"] = "not allowed"

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportTicket.model_validate(valid_ticket_data)

        assert "extra_field" in str(exc_info.value)


class TestModelSupportTicketEnumValues:
    """Test enum value handling in ModelSupportTicket."""

    def test_customer_tier_string_values(self, valid_ticket_data: dict) -> None:
        """Test that string enum values are accepted."""
        valid_ticket_data["customer_tier"] = "free"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.customer_tier == EnumCustomerTier.FREE

        valid_ticket_data["customer_tier"] = "pro"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.customer_tier == EnumCustomerTier.PRO

        valid_ticket_data["customer_tier"] = "enterprise"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.customer_tier == EnumCustomerTier.ENTERPRISE

    def test_channel_string_values(self, valid_ticket_data: dict) -> None:
        """Test that string channel values are accepted."""
        valid_ticket_data["channel"] = "email"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.channel == EnumSupportChannel.EMAIL

        valid_ticket_data["channel"] = "chat"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.channel == EnumSupportChannel.CHAT

        valid_ticket_data["channel"] = "web"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.channel == EnumSupportChannel.WEB


class TestModelSupportTicketDatetime:
    """Test datetime handling in ModelSupportTicket."""

    def test_datetime_with_timezone(self, valid_ticket_data: dict) -> None:
        """Test that datetime with timezone is accepted."""
        valid_ticket_data["created_at"] = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.created_at.tzinfo is not None

    def test_datetime_from_iso_string(self, valid_ticket_data: dict) -> None:
        """Test that ISO format datetime string is accepted."""
        valid_ticket_data["created_at"] = "2024-01-15T10:30:00Z"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.created_at.year == 2024
        assert ticket.created_at.month == 1
        assert ticket.created_at.day == 15

    def test_datetime_with_timezone_offset(self, valid_ticket_data: dict) -> None:
        """Test that datetime with timezone offset is accepted."""
        valid_ticket_data["created_at"] = "2024-01-15T10:30:00+05:30"
        ticket = ModelSupportTicket.model_validate(valid_ticket_data)
        assert ticket.created_at is not None
