# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelDecisionStoreEntry.

Tests:
- Valid construction with all required fields
- scope_domain vocabulary enforcement (ALLOWED_DOMAINS)
- scope_services normalization (sorted, lowercase)
- created_at timezone-awareness and future-timestamp rejection
- SUPERSEDED status requires superseded_by
- Non-SUPERSEDED status requires superseded_by=None
- from_attributes=True for ORM compatibility
- Immutability (frozen model)
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_decision_type import EnumDecisionType
from omnibase_core.models.store.model_decision_alternative import (
    ModelDecisionAlternative,
)
from omnibase_core.models.store.model_decision_store_entry import (
    ALLOWED_DOMAINS,
    ModelDecisionStoreEntry,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_entry_data() -> dict:
    """Minimal valid data for ModelDecisionStoreEntry."""
    return {
        "decision_type": EnumDecisionType.TECH_STACK_CHOICE,
        "correlation_id": uuid4(),
        "scope_domain": "data-model",
        "scope_services": ("omnibase_core",),
        "scope_layer": "architecture",
        "status": "ACTIVE",
        "rationale": "PostgreSQL selected for JSON indexing and ACID guarantees.",
        "alternatives": (
            ModelDecisionAlternative(label="PostgreSQL", status="SELECTED"),
            ModelDecisionAlternative(
                label="MySQL",
                status="REJECTED",
                rejection_reason="Lacks JSON indexing support",
            ),
        ),
        "tags": ("database",),
        "source": "planning",
        "created_at": datetime.now(UTC),
    }


# ============================================================================
# Valid construction
# ============================================================================


class TestModelDecisionStoreEntryValid:
    """Tests for valid ModelDecisionStoreEntry construction."""

    def test_minimal_valid_entry(self, base_entry_data: dict) -> None:
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.scope_domain == "data-model"
        assert entry.status == "ACTIVE"
        assert isinstance(entry.decision_id, UUID)

    def test_default_decision_id_generated(self, base_entry_data: dict) -> None:
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.decision_id is not None

    def test_custom_decision_id_accepted(self, base_entry_data: dict) -> None:
        custom_id = uuid4()
        entry = ModelDecisionStoreEntry(**base_entry_data, decision_id=custom_id)
        assert entry.decision_id == custom_id

    def test_empty_scope_services_means_platform_wide(
        self, base_entry_data: dict
    ) -> None:
        base_entry_data["scope_services"] = ()
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.scope_services == ()

    def test_frozen_immutable(self, base_entry_data: dict) -> None:
        entry = ModelDecisionStoreEntry(**base_entry_data)
        with pytest.raises(Exception):
            entry.status = "DEPRECATED"  # type: ignore[misc]

    def test_from_attributes_true(self, base_entry_data: dict) -> None:
        """Verify from_attributes=True is set for ORM compatibility."""
        config = ModelDecisionStoreEntry.model_config
        assert config.get("from_attributes") is True

    def test_proposed_status(self, base_entry_data: dict) -> None:
        base_entry_data["status"] = "PROPOSED"
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.status == "PROPOSED"

    def test_deprecated_status(self, base_entry_data: dict) -> None:
        base_entry_data["status"] = "DEPRECATED"
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.status == "DEPRECATED"

    def test_superseded_status_with_superseded_by(self, base_entry_data: dict) -> None:
        base_entry_data["status"] = "SUPERSEDED"
        base_entry_data["superseded_by"] = uuid4()
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.status == "SUPERSEDED"
        assert entry.superseded_by is not None

    def test_all_allowed_domains_accepted(self, base_entry_data: dict) -> None:
        for domain in ALLOWED_DOMAINS:
            base_entry_data["scope_domain"] = domain
            entry = ModelDecisionStoreEntry(**base_entry_data)
            assert entry.scope_domain == domain

    def test_all_scope_layers_accepted(self, base_entry_data: dict) -> None:
        for layer in ("architecture", "design", "planning", "implementation"):
            base_entry_data["scope_layer"] = layer
            entry = ModelDecisionStoreEntry(**base_entry_data)
            assert entry.scope_layer == layer

    def test_all_sources_accepted(self, base_entry_data: dict) -> None:
        for source in ("planning", "interview", "pr_review", "manual"):
            base_entry_data["source"] = source
            entry = ModelDecisionStoreEntry(**base_entry_data)
            assert entry.source == source


# ============================================================================
# scope_domain validation
# ============================================================================


class TestScopeDomainValidation:
    """Tests for scope_domain vocabulary enforcement."""

    def test_invalid_domain_raises(self, base_entry_data: dict) -> None:
        base_entry_data["scope_domain"] = "not-a-valid-domain"
        with pytest.raises(ValidationError, match="not in the allowed vocabulary"):
            ModelDecisionStoreEntry(**base_entry_data)

    def test_empty_domain_raises(self, base_entry_data: dict) -> None:
        base_entry_data["scope_domain"] = ""
        with pytest.raises(ValidationError):
            ModelDecisionStoreEntry(**base_entry_data)

    def test_domain_case_sensitive(self, base_entry_data: dict) -> None:
        base_entry_data["scope_domain"] = "Data-Model"  # wrong case
        with pytest.raises(ValidationError):
            ModelDecisionStoreEntry(**base_entry_data)


# ============================================================================
# scope_services normalization
# ============================================================================


class TestScopeServicesNormalization:
    """Tests for scope_services normalization (sorted lowercase)."""

    def test_services_sorted_and_lowercased(self, base_entry_data: dict) -> None:
        base_entry_data["scope_services"] = ["Omnibase_Infra", "OMNIBASE_CORE"]
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.scope_services == ("omnibase_core", "omnibase_infra")

    def test_services_already_normalized(self, base_entry_data: dict) -> None:
        base_entry_data["scope_services"] = ("omnibase_core", "omnibase_infra")
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.scope_services == ("omnibase_core", "omnibase_infra")

    def test_services_as_list_accepted(self, base_entry_data: dict) -> None:
        base_entry_data["scope_services"] = ["omnibase_core"]
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.scope_services == ("omnibase_core",)


# ============================================================================
# created_at validation
# ============================================================================


class TestCreatedAtValidation:
    """Tests for created_at field validation."""

    def test_naive_datetime_raises(self, base_entry_data: dict) -> None:
        base_entry_data["created_at"] = datetime.now()  # naive
        with pytest.raises(ValidationError, match="timezone-aware"):
            ModelDecisionStoreEntry(**base_entry_data)

    def test_far_future_datetime_raises(self, base_entry_data: dict) -> None:
        # More than 5 minutes in the future
        base_entry_data["created_at"] = datetime.now(UTC) + timedelta(minutes=10)
        with pytest.raises(ValidationError, match="in the future"):
            ModelDecisionStoreEntry(**base_entry_data)

    def test_slightly_future_datetime_accepted(self, base_entry_data: dict) -> None:
        # Within 5 minutes should be accepted
        base_entry_data["created_at"] = datetime.now(UTC) + timedelta(minutes=4)
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.created_at is not None

    def test_past_datetime_accepted(self, base_entry_data: dict) -> None:
        base_entry_data["created_at"] = datetime.now(UTC) - timedelta(days=30)
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.created_at is not None


# ============================================================================
# Supersession consistency
# ============================================================================


class TestSupersessionConsistency:
    """Tests for superseded_by consistency with status."""

    def test_superseded_without_superseded_by_raises(
        self, base_entry_data: dict
    ) -> None:
        base_entry_data["status"] = "SUPERSEDED"
        with pytest.raises(ValidationError, match="superseded_by must be set"):
            ModelDecisionStoreEntry(**base_entry_data)

    def test_active_with_superseded_by_raises(self, base_entry_data: dict) -> None:
        base_entry_data["superseded_by"] = uuid4()
        with pytest.raises(ValidationError, match="superseded_by must be None"):
            ModelDecisionStoreEntry(**base_entry_data)

    def test_supersedes_field_can_be_populated(self, base_entry_data: dict) -> None:
        old_id = uuid4()
        base_entry_data["supersedes"] = (old_id,)
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert old_id in entry.supersedes


# ============================================================================
# New EnumDecisionType values integration
# ============================================================================


class TestNewDecisionTypes:
    """Tests verifying the new EnumDecisionType values work with ModelDecisionStoreEntry."""

    @pytest.mark.parametrize(
        "decision_type",
        [
            EnumDecisionType.TECH_STACK_CHOICE,
            EnumDecisionType.DESIGN_PATTERN,
            EnumDecisionType.API_CONTRACT,
            EnumDecisionType.SCOPE_BOUNDARY,
            EnumDecisionType.REQUIREMENT_CHOICE,
        ],
    )
    def test_new_decision_types_accepted(
        self, base_entry_data: dict, decision_type: EnumDecisionType
    ) -> None:
        base_entry_data["decision_type"] = decision_type
        entry = ModelDecisionStoreEntry(**base_entry_data)
        assert entry.decision_type == decision_type

    @pytest.mark.parametrize(
        "decision_type",
        [
            EnumDecisionType.TECH_STACK_CHOICE,
            EnumDecisionType.DESIGN_PATTERN,
            EnumDecisionType.API_CONTRACT,
            EnumDecisionType.SCOPE_BOUNDARY,
            EnumDecisionType.REQUIREMENT_CHOICE,
        ],
    )
    def test_new_decision_types_are_selection_decisions(
        self, decision_type: EnumDecisionType
    ) -> None:
        assert decision_type.is_selection_decision() is True
