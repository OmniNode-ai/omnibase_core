# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelDecisionAlternative.

Tests:
- Valid construction for all three statuses
- rejection_reason invariant: REJECTED requires reason; others must be None
- label whitespace normalization and empty-label rejection
- Immutability (frozen model)
- extra fields forbidden
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.store.model_decision_alternative import (
    ModelDecisionAlternative,
)

# ============================================================================
# Valid construction
# ============================================================================


class TestModelDecisionAlternativeValid:
    """Tests for valid ModelDecisionAlternative construction."""

    def test_selected_no_rejection_reason(self) -> None:
        alt = ModelDecisionAlternative(label="PostgreSQL", status="SELECTED")
        assert alt.label == "PostgreSQL"
        assert alt.status == "SELECTED"
        assert alt.rejection_reason is None

    def test_considered_no_rejection_reason(self) -> None:
        alt = ModelDecisionAlternative(label="SQLite", status="CONSIDERED")
        assert alt.status == "CONSIDERED"
        assert alt.rejection_reason is None

    def test_rejected_with_reason(self) -> None:
        alt = ModelDecisionAlternative(
            label="MySQL",
            status="REJECTED",
            rejection_reason="Lacks native JSON indexing required by query patterns",
        )
        assert alt.status == "REJECTED"
        assert (
            alt.rejection_reason
            == "Lacks native JSON indexing required by query patterns"
        )

    def test_label_whitespace_stripped(self) -> None:
        alt = ModelDecisionAlternative(label="  Redis  ", status="CONSIDERED")
        assert alt.label == "Redis"

    def test_frozen_model_immutable(self) -> None:
        alt = ModelDecisionAlternative(label="Kafka", status="SELECTED")
        with pytest.raises(Exception):
            alt.label = "RabbitMQ"  # type: ignore[misc]


# ============================================================================
# rejection_reason invariant
# ============================================================================


class TestRejectionReasonInvariant:
    """Tests for the rejection_reason invariant enforcement."""

    def test_rejected_without_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="rejection_reason is required"):
            ModelDecisionAlternative(label="MySQL", status="REJECTED")

    def test_rejected_with_empty_reason_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelDecisionAlternative(
                label="MySQL", status="REJECTED", rejection_reason=""
            )

    def test_selected_with_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="rejection_reason must be None"):
            ModelDecisionAlternative(
                label="PostgreSQL",
                status="SELECTED",
                rejection_reason="Should not be here",
            )

    def test_considered_with_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="rejection_reason must be None"):
            ModelDecisionAlternative(
                label="SQLite",
                status="CONSIDERED",
                rejection_reason="Should not be here",
            )


# ============================================================================
# Label validation
# ============================================================================


class TestLabelValidation:
    """Tests for label field validation."""

    def test_empty_label_raises(self) -> None:
        with pytest.raises(ValidationError, match="label must not be empty"):
            ModelDecisionAlternative(label="", status="CONSIDERED")

    def test_whitespace_only_label_raises(self) -> None:
        with pytest.raises(ValidationError, match="label must not be empty"):
            ModelDecisionAlternative(label="   ", status="CONSIDERED")


# ============================================================================
# Extra fields and invalid status
# ============================================================================


class TestSchemaEnforcement:
    """Tests for schema enforcement."""

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelDecisionAlternative(  # type: ignore[call-arg]
                label="PostgreSQL", status="SELECTED", extra_field="bad"
            )

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelDecisionAlternative(label="PostgreSQL", status="APPROVED")  # type: ignore[arg-type]
