# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDeliveryFailureEvidence.

Frozen r2 contract authority: Linear comment cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb
on OMN-15666 (2026-08-02T20:10:29Z) -- strict, frozen, extra="forbid"; exact
required field set (stage, error_type, error_message, retryable).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)


@pytest.mark.unit
class TestModelDeliveryFailureEvidence:
    """Test suite for ModelDeliveryFailureEvidence."""

    def test_construction_with_required_fields(self) -> None:
        evidence = ModelDeliveryFailureEvidence(
            stage="primary_dlq_publish",
            error_type="ConnectionError",
            error_message="mock broker refused publish",
            retryable=True,
        )
        assert evidence.stage == "primary_dlq_publish"
        assert evidence.error_type == "ConnectionError"
        assert evidence.error_message == "mock broker refused publish"
        assert evidence.retryable is True

    def test_is_frozen(self) -> None:
        evidence = ModelDeliveryFailureEvidence(
            stage="quarantine_publish",
            error_type="TimeoutError",
            error_message="broker did not ack",
            retryable=False,
        )
        with pytest.raises(ValidationError):
            evidence.stage = "primary_dlq_publish"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelDeliveryFailureEvidence(
                stage="primary_dlq_publish",
                error_type="ConnectionError",
                error_message="mock broker refused publish",
                retryable=True,
                schema_version="1.0.0",  # type: ignore[call-arg]
            )

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelDeliveryFailureEvidence(  # type: ignore[call-arg]
                stage="primary_dlq_publish",
                error_type="ConnectionError",
                retryable=True,
            )

    def test_exact_field_set(self) -> None:
        assert set(ModelDeliveryFailureEvidence.model_fields) == {
            "stage",
            "error_type",
            "error_message",
            "retryable",
        }
