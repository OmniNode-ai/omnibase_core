# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test that demo models can be imported correctly."""

from __future__ import annotations


class TestDemoImports:
    """Test demo model imports."""

    def test_import_model_support_ticket(self) -> None:
        """Test that ModelSupportTicket can be imported."""
        from omnibase_core.models.demo.model_validate import ModelSupportTicket

        assert ModelSupportTicket is not None

    def test_import_model_support_classification(self) -> None:
        """Test that ModelSupportClassificationResult can be imported."""
        from omnibase_core.models.demo.model_validate import (
            ModelSupportClassificationResult,
        )

        assert ModelSupportClassificationResult is not None

    def test_import_demo_enums(self) -> None:
        """Test that demo-related enums can be imported."""
        from omnibase_core.enums import (
            EnumCustomerTier,
            EnumSentiment,
            EnumSupportCategory,
            EnumSupportChannel,
        )

        assert EnumCustomerTier.FREE.value == "free"
        assert EnumSupportChannel.EMAIL.value == "email"
        assert EnumSupportCategory.BILLING_REFUND.value == "billing_refund"
        assert EnumSentiment.POSITIVE.value == "positive"
