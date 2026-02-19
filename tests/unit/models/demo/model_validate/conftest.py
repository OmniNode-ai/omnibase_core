# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixtures for model-validate demo tests."""

from datetime import UTC, datetime

import pytest

from omnibase_core.enums import (
    EnumCustomerTier,
    EnumSentiment,
    EnumSupportCategory,
    EnumSupportChannel,
)


@pytest.fixture
def valid_ticket_data() -> dict:
    """Valid support ticket data for testing."""
    return {
        "ticket_id": "TKT-TEST-001",
        "created_at": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        "customer_tier": EnumCustomerTier.PRO,
        "channel": EnumSupportChannel.EMAIL,
        "language": "en",
        "subject": "Test support ticket",
        "body": "This is a test support ticket body.",
    }


@pytest.fixture
def valid_ticket_data_minimal() -> dict:
    """Minimal valid support ticket data (required fields only)."""
    return {
        "ticket_id": "TKT-TEST-002",
        "created_at": datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        "customer_tier": EnumCustomerTier.FREE,
        "channel": EnumSupportChannel.WEB,
        "subject": "Minimal ticket",
        "body": "Test body",
    }


@pytest.fixture
def valid_ticket_data_full() -> dict:
    """Full support ticket data with all optional fields."""
    return {
        "ticket_id": "TKT-TEST-003",
        "created_at": datetime(2024, 1, 15, 14, 15, 0, tzinfo=UTC),
        "customer_tier": EnumCustomerTier.ENTERPRISE,
        "channel": EnumSupportChannel.CHAT,
        "language": "es",
        "subject": "Full ticket with all fields",
        "body": "This ticket has all optional fields populated.",
        "attachments": ["file1.pdf", "file2.png"],
        "product_area": "billing",
        "priority_hint": "high",
        "previous_contact_count": 3,
    }


@pytest.fixture
def valid_classification_data() -> dict:
    """Valid classification result data for testing."""
    return {
        "ticket_id": "TKT-TEST-001",
        "category": EnumSupportCategory.BILLING_REFUND,
        "confidence": 0.95,
        "sentiment": EnumSentiment.NEUTRAL,
        "summary": "Customer requesting refund for subscription charge",
        "suggested_reply": "Thank you for contacting us. I'll process your refund.",
        "latency_ms": 1250,
        "model_id": "gpt-4-turbo-2024-04-09",
    }


@pytest.fixture
def valid_classification_data_full() -> dict:
    """Full classification result data with optional fields."""
    return {
        "ticket_id": "TKT-TEST-001",
        "category": EnumSupportCategory.TECHNICAL_BUG,
        "confidence": 0.92,
        "sentiment": EnumSentiment.NEGATIVE,
        "summary": "App crash on login for iOS user",
        "suggested_reply": "I apologize for the issue. Please try reinstalling.",
        "latency_ms": 980,
        "model_id": "gpt-4o-mini-2024-07-18",
        "reason_codes": ["app_crash", "ios_specific"],
        "invariant_tags": ["technical_domain", "mobile_platform"],
    }
