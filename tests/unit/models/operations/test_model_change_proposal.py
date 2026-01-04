# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelChangeProposal model (OMN-1196).

Tests the change proposal model for representing proposed system changes
for evaluation. This model captures before/after configurations, change
metadata, and provides helper methods for change analysis.

Related:
    - OMN-1196: Create ModelChangeProposal for system change evaluation
"""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_change_proposal import (
    EnumChangeType,
    ModelChangeProposal,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_before_config() -> dict:
    """Sample before configuration for testing."""
    return {
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "timeout_ms": 30000,
    }


@pytest.fixture
def sample_after_config() -> dict:
    """Sample after configuration for testing - differs from before."""
    return {
        "model_name": "gpt-4-turbo",
        "temperature": 0.5,
        "max_tokens": 2000,
        "timeout_ms": 30000,
    }


@pytest.fixture
def sample_identical_config() -> dict:
    """Sample config that is identical (for testing identical rejection)."""
    return {
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
    }


@pytest.fixture
def nested_before_config() -> dict:
    """Sample nested before configuration for testing."""
    return {
        "endpoint": {
            "url": "https://api.example.com/v1",
            "auth": {"type": "bearer", "token_env": "API_TOKEN"},
        },
        "settings": {
            "retry": {"max_retries": 3, "backoff_ms": 1000},
            "timeout_ms": 5000,
        },
    }


@pytest.fixture
def nested_after_config() -> dict:
    """Sample nested after configuration for testing."""
    return {
        "endpoint": {
            "url": "https://api.example.com/v2",
            "auth": {"type": "bearer", "token_env": "API_TOKEN"},
        },
        "settings": {
            "retry": {"max_retries": 5, "backoff_ms": 2000},
            "timeout_ms": 10000,
        },
    }


@pytest.fixture
def minimal_valid_proposal(
    sample_before_config: dict, sample_after_config: dict
) -> ModelChangeProposal:
    """Create a minimal valid proposal for testing."""
    return ModelChangeProposal(
        change_type=EnumChangeType.CONFIG_CHANGE,
        description="Update model configuration",
        rationale="Improve response quality and speed",
        before_config=sample_before_config,
        after_config=sample_after_config,
    )


@pytest.fixture
def full_proposal(
    sample_before_config: dict, sample_after_config: dict
) -> ModelChangeProposal:
    """Create a fully-populated proposal for testing."""
    correlation_id = uuid4()
    return ModelChangeProposal(
        change_type=EnumChangeType.MODEL_SWAP,
        description="Swap GPT-4 for GPT-4-Turbo",
        rationale="GPT-4-Turbo offers better performance at lower cost",
        before_config=sample_before_config,
        after_config=sample_after_config,
        correlation_id=correlation_id,
        proposed_by="system-optimizer",
        tags=["performance", "cost-reduction"],
    )


# =============================================================================
# Phase 1: Model Validation Tests
# =============================================================================


@pytest.mark.unit
class TestChangeProposalValidation:
    """Phase 1: Model validation tests."""

    def test_change_id_auto_generated_as_uuid(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """change_id should be auto-generated as valid UUID."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test proposal",
            rationale="Testing auto-generated ID",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert proposal.change_id is not None
        assert isinstance(proposal.change_id, UUID)

    def test_change_id_can_be_provided(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """change_id can be explicitly provided."""
        explicit_id = uuid4()
        proposal = ModelChangeProposal(
            change_id=explicit_id,
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test proposal",
            rationale="Testing explicit ID",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert proposal.change_id == explicit_id

    def test_before_after_must_differ(self, sample_identical_config: dict) -> None:
        """before_config and after_config cannot be identical - should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Invalid proposal",
                rationale="Testing identical configs",
                before_config=sample_identical_config,
                after_config=sample_identical_config.copy(),
            )

        assert "identical" in str(exc_info.value).lower()

    def test_model_swap_type_accepted(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """model_swap is a valid change_type."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.MODEL_SWAP,
            description="Swap model",
            rationale="Testing model swap type",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert proposal.change_type == EnumChangeType.MODEL_SWAP

    def test_config_change_type_accepted(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """config_change is a valid change_type."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Change config",
            rationale="Testing config change type",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert proposal.change_type == EnumChangeType.CONFIG_CHANGE

    def test_endpoint_change_type_accepted(self) -> None:
        """endpoint_change is a valid change_type."""
        # Use configs with valid URL strings for endpoint_change validation
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Change endpoint",
            rationale="Testing endpoint change type",
            before_config={"url": "https://api.old.example.com/v1", "timeout": 30},
            after_config={"url": "https://api.new.example.com/v2", "timeout": 60},
        )

        assert proposal.change_type == EnumChangeType.ENDPOINT_CHANGE

    def test_invalid_change_type_rejected(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Invalid change_type should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type="invalid_type",  # type: ignore[arg-type]
                description="Invalid proposal",
                rationale="Testing invalid type",
                before_config=sample_before_config,
                after_config=sample_after_config,
            )

        error_str = str(exc_info.value)
        # Pydantic enum error includes field name and valid options
        assert "change_type" in error_str
        assert "Input should be" in error_str
        assert "model_swap" in error_str  # One of the valid enum values

    def test_empty_description_rejected(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Empty description should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="",
                rationale="Valid rationale",
                before_config=sample_before_config,
                after_config=sample_after_config,
            )

        error_str = str(exc_info.value)
        # Pydantic min_length error includes field name and constraint message
        assert "description" in error_str
        assert "at least 1 character" in error_str

    def test_empty_rationale_rejected(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Empty rationale should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Valid description",
                rationale="",
                before_config=sample_before_config,
                after_config=sample_after_config,
            )

        error_str = str(exc_info.value)
        # Pydantic min_length error includes field name and constraint message
        assert "rationale" in error_str
        assert "at least 1 character" in error_str

    def test_frozen_model_is_immutable(
        self, minimal_valid_proposal: ModelChangeProposal
    ) -> None:
        """Model should be frozen/immutable after creation."""
        with pytest.raises(ValidationError):
            minimal_valid_proposal.description = "Modified description"  # type: ignore[misc]

    def test_whitespace_only_description_rejected(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Whitespace-only description should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="   ",
                rationale="Valid rationale",
                before_config=sample_before_config,
                after_config=sample_after_config,
            )

        error_str = str(exc_info.value)
        # Custom validator error includes field name and whitespace message
        assert "description" in error_str
        assert "whitespace-only" in error_str

    def test_whitespace_only_rationale_rejected(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Whitespace-only rationale should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Valid description",
                rationale="   \t\n  ",
                before_config=sample_before_config,
                after_config=sample_after_config,
            )

        error_str = str(exc_info.value)
        # Custom validator error includes field name and whitespace message
        assert "rationale" in error_str
        assert "whitespace-only" in error_str

    def test_timestamp_auto_generated(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Timestamp should be auto-generated if not provided."""
        before_time = datetime.now(UTC)

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test proposal",
            rationale="Testing auto timestamp",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        after_time = datetime.now(UTC)

        assert proposal.created_at is not None
        assert isinstance(proposal.created_at, datetime)
        assert before_time <= proposal.created_at <= after_time

    def test_empty_before_config_rejected(self, sample_after_config: dict) -> None:
        """Empty before_config should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Test proposal",
                rationale="Testing empty before",
                before_config={},
                after_config=sample_after_config,
            )

        error_str = str(exc_info.value)
        # Custom validator error includes field name and empty constraint
        assert "before_config" in error_str
        assert "cannot be empty" in error_str

    def test_empty_after_config_rejected(self, sample_before_config: dict) -> None:
        """Empty after_config should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Test proposal",
                rationale="Testing empty after",
                before_config=sample_before_config,
                after_config={},
            )

        error_str = str(exc_info.value)
        # Custom validator error includes field name and empty constraint
        assert "after_config" in error_str
        assert "cannot be empty" in error_str

    def test_extra_fields_forbidden(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Extra fields should be forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Test proposal",
                rationale="Testing extra fields",
                before_config=sample_before_config,
                after_config=sample_after_config,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value)
        # Pydantic extra='forbid' error includes field name and standard message
        assert "unknown_field" in error_str
        assert "Extra inputs are not permitted" in error_str


# =============================================================================
# Phase 2: Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestChangeProposalSerialization:
    """Phase 2: Serialization tests."""

    def test_roundtrip_json_serialization(
        self, full_proposal: ModelChangeProposal
    ) -> None:
        """Model survives JSON roundtrip."""
        json_str = full_proposal.model_dump_json()
        restored = ModelChangeProposal.model_validate_json(json_str)

        assert restored.change_id == full_proposal.change_id
        assert restored.change_type == full_proposal.change_type
        assert restored.description == full_proposal.description
        assert restored.rationale == full_proposal.rationale
        assert restored.before_config == full_proposal.before_config
        assert restored.after_config == full_proposal.after_config
        assert restored.correlation_id == full_proposal.correlation_id
        assert restored.proposed_by == full_proposal.proposed_by
        assert restored.tags == full_proposal.tags

    def test_roundtrip_dict_serialization(
        self, full_proposal: ModelChangeProposal
    ) -> None:
        """Model survives dict roundtrip."""
        dumped = full_proposal.model_dump()
        restored = ModelChangeProposal.model_validate(dumped)

        assert restored.change_id == full_proposal.change_id
        assert restored.change_type == full_proposal.change_type
        assert restored.before_config == full_proposal.before_config
        assert restored.after_config == full_proposal.after_config

    def test_datetime_serialization_iso_format(
        self, minimal_valid_proposal: ModelChangeProposal
    ) -> None:
        """Dates serialize to ISO format."""
        json_str = minimal_valid_proposal.model_dump_json()
        data = json.loads(json_str)

        # Verify created_at is in ISO format string
        assert "created_at" in data
        created_at_str = data["created_at"]
        assert isinstance(created_at_str, str)

        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_nested_config_serialization(
        self, nested_before_config: dict, nested_after_config: dict
    ) -> None:
        """Nested dicts in config serialize correctly."""
        # Use CONFIG_CHANGE to test serialization without endpoint URL validation
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Update config",
            rationale="Testing nested serialization",
            before_config=nested_before_config,
            after_config=nested_after_config,
        )

        json_str = proposal.model_dump_json()
        restored = ModelChangeProposal.model_validate_json(json_str)

        # Verify nested structure is preserved
        assert (
            restored.before_config["endpoint"]["url"]
            == nested_before_config["endpoint"]["url"]
        )
        assert (
            restored.after_config["settings"]["retry"]["max_retries"]
            == nested_after_config["settings"]["retry"]["max_retries"]
        )

    def test_uuid_serialization(self, full_proposal: ModelChangeProposal) -> None:
        """UUIDs serialize to string format."""
        json_str = full_proposal.model_dump_json()
        data = json.loads(json_str)

        # change_id should serialize to string
        assert "change_id" in data
        assert isinstance(data["change_id"], str)

        # Should be parseable as UUID
        parsed_id = UUID(data["change_id"])
        assert parsed_id == full_proposal.change_id

        # correlation_id should also serialize to string
        if full_proposal.correlation_id:
            assert "correlation_id" in data
            assert isinstance(data["correlation_id"], str)
            parsed_corr = UUID(data["correlation_id"])
            assert parsed_corr == full_proposal.correlation_id

    def test_enum_serialization(
        self, minimal_valid_proposal: ModelChangeProposal
    ) -> None:
        """EnumChangeType serializes to string value."""
        json_str = minimal_valid_proposal.model_dump_json()
        data = json.loads(json_str)

        assert "change_type" in data
        assert data["change_type"] == EnumChangeType.CONFIG_CHANGE.value

    def test_model_dump_mode_json(self, full_proposal: ModelChangeProposal) -> None:
        """model_dump with mode='json' produces JSON-serializable output."""
        dumped = full_proposal.model_dump(mode="json")

        # All UUIDs should be strings
        assert isinstance(dumped["change_id"], str)

        # datetime should be string
        assert isinstance(dumped["created_at"], str)

        # Should be directly JSON serializable
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)


# =============================================================================
# Phase 3: Factory Method Tests
# =============================================================================


@pytest.mark.unit
class TestChangeProposalFactory:
    """Phase 3: Factory method tests."""

    def test_create_factory_method(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Factory method creates valid instance."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.MODEL_SWAP,
            description="Swap models",
            rationale="Improved performance",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert isinstance(proposal, ModelChangeProposal)
        assert proposal.change_type == EnumChangeType.MODEL_SWAP
        assert proposal.description == "Swap models"
        assert proposal.rationale == "Improved performance"
        assert proposal.before_config == sample_before_config
        assert proposal.after_config == sample_after_config
        assert isinstance(proposal.change_id, UUID)

    def test_create_with_optional_fields(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Factory method works with optional fields."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Update config",
            rationale="Testing factory with options",
            before_config=sample_before_config,
            after_config=sample_after_config,
            proposed_by="agent-optimizer",
            tags=["test", "factory"],
        )

        assert proposal.proposed_by == "agent-optimizer"
        assert proposal.tags == ["test", "factory"]

    def test_create_with_correlation_id(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Factory method accepts correlation_id."""
        correlation_id = uuid4()

        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Change config",
            rationale="Testing correlation ID",
            before_config=sample_before_config,
            after_config=sample_after_config,
            correlation_id=correlation_id,
        )

        assert proposal.correlation_id == correlation_id

    def test_create_with_explicit_change_id(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Factory method accepts explicit change_id."""
        explicit_id = uuid4()

        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test explicit ID",
            rationale="Testing explicit change_id in factory",
            before_config=sample_before_config,
            after_config=sample_after_config,
            change_id=explicit_id,
        )

        assert proposal.change_id == explicit_id

    def test_create_for_model_swap(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Factory method for model_swap specific creation."""
        proposal = ModelChangeProposal.create_model_swap(
            old_model="gpt-4",
            new_model="gpt-4-turbo",
            description="Upgrade to GPT-4-Turbo",
            rationale="Better performance",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert proposal.change_type == EnumChangeType.MODEL_SWAP
        assert isinstance(proposal, ModelChangeProposal)


# =============================================================================
# Phase 4: Helper Method Tests
# =============================================================================


@pytest.mark.unit
class TestChangeProposalHelpers:
    """Phase 4: Helper method tests."""

    def test_get_changed_keys_identifies_differences(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """get_changed_keys() returns keys that differ between before/after."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test changed keys",
            rationale="Testing helper method",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        changed_keys = proposal.get_changed_keys()

        # These keys have different values
        assert "model_name" in changed_keys
        assert "temperature" in changed_keys
        assert "max_tokens" in changed_keys
        # This key has the same value
        assert "timeout_ms" not in changed_keys

    def test_get_changed_keys_includes_added_keys(self) -> None:
        """get_changed_keys() includes keys added in after_config."""
        before = {"key1": "value1"}
        after = {"key1": "value1", "key2": "value2"}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test added keys",
            rationale="Testing key addition detection",
            before_config=before,
            after_config=after,
        )

        changed_keys = proposal.get_changed_keys()

        assert "key2" in changed_keys  # Added key
        assert "key1" not in changed_keys  # Unchanged key

    def test_get_changed_keys_includes_removed_keys(self) -> None:
        """get_changed_keys() includes keys removed in after_config."""
        before = {"key1": "value1", "key2": "value2"}
        after = {"key1": "value1"}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test removed keys",
            rationale="Testing key removal detection",
            before_config=before,
            after_config=after,
        )

        changed_keys = proposal.get_changed_keys()

        assert "key2" in changed_keys  # Removed key
        assert "key1" not in changed_keys  # Unchanged key

    def test_get_changed_keys_empty_when_same_keys_different_values(self) -> None:
        """get_changed_keys() identifies value changes."""
        before = {"setting": "old_value"}
        after = {"setting": "new_value"}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test value changes",
            rationale="Testing value change detection",
            before_config=before,
            after_config=after,
        )

        changed_keys = proposal.get_changed_keys()

        assert "setting" in changed_keys

    def test_get_diff_summary_returns_readable_string(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """get_diff_summary() returns human-readable diff."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test diff summary",
            rationale="Testing diff summary helper",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        diff = proposal.get_diff_summary()

        assert isinstance(diff, str)
        assert len(diff) > 0
        # All changed keys should appear in the diff (not just any one of them)
        assert "model_name" in diff
        assert "temperature" in diff
        assert "max_tokens" in diff
        # Unchanged key should NOT appear
        assert "timeout_ms" not in diff

    def test_get_diff_summary_shows_before_after_values(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """get_diff_summary() shows before and after values."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test diff values",
            rationale="Testing value display in diff",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        diff = proposal.get_diff_summary()

        # Should contain old and new values for all changed keys
        # Check model_name change: gpt-4 -> gpt-4-turbo
        assert "gpt-4" in diff
        assert "gpt-4-turbo" in diff
        # Check temperature change: 0.7 -> 0.5
        assert "0.7" in diff
        assert "0.5" in diff

    def test_model_swap_get_model_names(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """For model_swap, can extract old/new model names."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.MODEL_SWAP,
            description="Swap model",
            rationale="Testing model name extraction",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        model_names = proposal.get_model_names()

        assert model_names is not None
        assert "old_model" in model_names
        assert "new_model" in model_names
        assert model_names["old_model"] == "gpt-4"
        assert model_names["new_model"] == "gpt-4-turbo"

    def test_get_model_names_returns_none_for_non_model_swap(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """get_model_names() returns None for non-model_swap change types."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Config change",
            rationale="Testing model names for non-swap",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        model_names = proposal.get_model_names()

        assert model_names is None

    def test_is_breaking_change_default_false(
        self, minimal_valid_proposal: ModelChangeProposal
    ) -> None:
        """is_breaking_change should default to False."""
        assert minimal_valid_proposal.is_breaking_change is False

    def test_is_breaking_change_can_be_set(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """is_breaking_change can be explicitly set."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Breaking config change",
            rationale="API version bump",
            before_config=sample_before_config,
            after_config=sample_after_config,
            is_breaking_change=True,
        )

        assert proposal.is_breaking_change is True


# =============================================================================
# Phase 5: Edge Cases and Error Handling Tests
# =============================================================================


@pytest.mark.unit
class TestChangeProposalEdgeCases:
    """Phase 5: Edge cases and error handling tests."""

    def test_deeply_nested_config_comparison(self) -> None:
        """Deeply nested configs are compared correctly."""
        before = {
            "level1": {
                "level2": {
                    "level3": {"value": "old"},
                },
            },
        }
        after = {
            "level1": {
                "level2": {
                    "level3": {"value": "new"},
                },
            },
        }

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Deep change",
            rationale="Testing deep nesting",
            before_config=before,
            after_config=after,
        )

        # Should detect the change
        changed_keys = proposal.get_changed_keys()
        assert len(changed_keys) > 0

    def test_config_with_list_values(self) -> None:
        """Configs with list values are handled correctly."""
        before = {"items": [1, 2, 3], "name": "test"}
        after = {"items": [1, 2, 3, 4], "name": "test"}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="List change",
            rationale="Testing list handling",
            before_config=before,
            after_config=after,
        )

        changed_keys = proposal.get_changed_keys()
        assert "items" in changed_keys
        assert "name" not in changed_keys

    def test_config_with_none_values(self) -> None:
        """Configs with None values are handled correctly."""
        before = {"setting": None, "other": "value"}
        after = {"setting": "now_set", "other": "value"}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="None to value",
            rationale="Testing None handling",
            before_config=before,
            after_config=after,
        )

        changed_keys = proposal.get_changed_keys()
        assert "setting" in changed_keys

    def test_config_value_to_none(self) -> None:
        """Value changing to None is detected."""
        before = {"setting": "has_value", "other": "value"}
        after = {"setting": None, "other": "value"}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Value to None",
            rationale="Testing value to None",
            before_config=before,
            after_config=after,
        )

        changed_keys = proposal.get_changed_keys()
        assert "setting" in changed_keys

    def test_unicode_in_description_and_rationale(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Unicode characters in description and rationale are handled."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Change with unicode: ",
            rationale="Rationale with special chars: ",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert "" in proposal.description
        assert "" in proposal.rationale

        # Should survive serialization
        json_str = proposal.model_dump_json()
        restored = ModelChangeProposal.model_validate_json(json_str)
        assert "" in restored.description

    def test_very_long_description_handled(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Very long descriptions are accepted (no max length constraint)."""
        long_description = "A" * 10000

        # Model has no max_length constraint on description, so this should succeed
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description=long_description,
            rationale="Testing long description",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert len(proposal.description) == 10000
        assert proposal.description == long_description

    def test_tags_empty_list_allowed(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Empty tags list is allowed."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="No tags",
            rationale="Testing empty tags",
            before_config=sample_before_config,
            after_config=sample_after_config,
            tags=[],
        )

        assert proposal.tags == []

    def test_tags_none_defaults_to_empty(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Tags default to empty list when not provided."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Default tags",
            rationale="Testing default tags",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        assert proposal.tags == []


# =============================================================================
# Phase 6: Model Configuration Tests
# =============================================================================


@pytest.mark.unit
class TestChangeProposalModelConfig:
    """Phase 6: Model configuration tests."""

    def test_model_is_frozen(self, minimal_valid_proposal: ModelChangeProposal) -> None:
        """Model config has frozen=True."""
        assert minimal_valid_proposal.model_config.get("frozen") is True

    def test_model_forbids_extra(
        self, minimal_valid_proposal: ModelChangeProposal
    ) -> None:
        """Model config has extra='forbid'."""
        assert minimal_valid_proposal.model_config.get("extra") == "forbid"

    def test_model_has_from_attributes(
        self, minimal_valid_proposal: ModelChangeProposal
    ) -> None:
        """Model config has from_attributes=True for pytest-xdist compatibility."""
        assert minimal_valid_proposal.model_config.get("from_attributes") is True


# =============================================================================
# Phase 7: Enum Tests
# =============================================================================


@pytest.mark.unit
class TestEnumChangeType:
    """Tests for EnumChangeType enum."""

    def test_model_swap_value(self) -> None:
        """MODEL_SWAP has expected string value."""
        assert EnumChangeType.MODEL_SWAP.value == "model_swap"

    def test_config_change_value(self) -> None:
        """CONFIG_CHANGE has expected string value."""
        assert EnumChangeType.CONFIG_CHANGE.value == "config_change"

    def test_endpoint_change_value(self) -> None:
        """ENDPOINT_CHANGE has expected string value."""
        assert EnumChangeType.ENDPOINT_CHANGE.value == "endpoint_change"

    def test_all_values_unique(self) -> None:
        """All enum values are unique."""
        values = [e.value for e in EnumChangeType]
        assert len(values) == len(set(values))

    def test_enum_members_count(self) -> None:
        """Enum has expected number of members (at least 3)."""
        assert len(EnumChangeType) >= 3


# =============================================================================
# Phase 8: Deep Nested Config Comparison Tests
# =============================================================================


@pytest.mark.unit
class TestDeepNestedConfigComparison:
    """Phase 8: Tests for deep nested configuration comparison (v0.4.0+)."""

    def test_get_changed_keys_deep_simple_nested(self) -> None:
        """Deep mode detects simple nested changes with dot-separated paths."""
        before = {"config": {"timeout": 10, "retries": 3}}
        after = {"config": {"timeout": 20, "retries": 3}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Update nested config",
            rationale="Testing deep comparison",
            before_config=before,
            after_config=after,
        )

        # Shallow should return 'config'
        shallow_keys = proposal.get_changed_keys(deep=False)
        assert shallow_keys == {"config"}

        # Deep should return 'config.timeout'
        deep_keys = proposal.get_changed_keys(deep=True)
        assert deep_keys == {"config.timeout"}

    def test_get_changed_keys_deep_multiple_nested(self) -> None:
        """Deep mode detects multiple nested changes."""
        before = {"settings": {"a": 1, "b": 2, "c": 3}}
        after = {"settings": {"a": 10, "b": 2, "c": 30}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Multiple nested changes",
            rationale="Testing multi-change deep comparison",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        assert deep_keys == {"settings.a", "settings.c"}

    def test_get_changed_keys_deep_three_levels(
        self, nested_before_config: dict, nested_after_config: dict
    ) -> None:
        """Deep mode handles three levels of nesting."""
        # Use CONFIG_CHANGE to test deep key comparison without endpoint URL validation
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Deep nested config change",
            rationale="Testing three-level nesting",
            before_config=nested_before_config,
            after_config=nested_after_config,
        )

        deep_keys = proposal.get_changed_keys(deep=True)

        # Should detect: endpoint.url, settings.retry.max_retries,
        # settings.retry.backoff_ms, settings.timeout_ms
        assert "endpoint.url" in deep_keys
        assert "settings.retry.max_retries" in deep_keys
        assert "settings.retry.backoff_ms" in deep_keys
        assert "settings.timeout_ms" in deep_keys
        # Should NOT include unchanged nested values
        assert "endpoint.auth.type" not in deep_keys
        assert "endpoint.auth.token_env" not in deep_keys

    def test_get_changed_keys_deep_added_nested_key(self) -> None:
        """Deep mode detects added nested keys."""
        before = {"config": {"existing": "value"}}
        after = {"config": {"existing": "value", "new_key": "new_value"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Add nested key",
            rationale="Testing nested key addition",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        assert deep_keys == {"config.new_key"}

    def test_get_changed_keys_deep_removed_nested_key(self) -> None:
        """Deep mode detects removed nested keys."""
        before = {"config": {"keep": "value", "remove": "old"}}
        after = {"config": {"keep": "value"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Remove nested key",
            rationale="Testing nested key removal",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        assert deep_keys == {"config.remove"}

    def test_get_changed_keys_deep_type_change_dict_to_value(self) -> None:
        """Deep mode handles type change from dict to scalar."""
        before = {"config": {"nested": {"a": 1}}}
        after = {"config": {"nested": "now_a_string"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Type change",
            rationale="Testing dict to scalar change",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        # The nested key changed type, should report it as changed
        assert "config.nested" in deep_keys

    def test_get_changed_keys_deep_type_change_value_to_dict(self) -> None:
        """Deep mode handles type change from scalar to dict."""
        before = {"config": {"setting": "a_string"}}
        after = {"config": {"setting": {"nested": "value"}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Type change",
            rationale="Testing scalar to dict change",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        assert "config.setting" in deep_keys

    def test_get_changed_keys_deep_top_level_and_nested(self) -> None:
        """Deep mode handles both top-level and nested changes."""
        before = {"top": "old", "nested": {"inner": "old_inner"}}
        after = {"top": "new", "nested": {"inner": "new_inner"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Mixed changes",
            rationale="Testing top-level and nested changes",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        assert deep_keys == {"top", "nested.inner"}

    def test_get_changed_keys_backwards_compatible(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """Default behavior (deep=False) is backwards compatible."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Backwards compatibility test",
            rationale="Ensure default behavior unchanged",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        # Calling without argument should work exactly as before
        changed_keys = proposal.get_changed_keys()
        assert "model_name" in changed_keys
        assert "temperature" in changed_keys
        assert "max_tokens" in changed_keys
        assert "timeout_ms" not in changed_keys

    def test_get_diff_summary_deep_mode(self) -> None:
        """get_diff_summary with deep=True shows nested paths."""
        before = {"settings": {"timeout": 10, "retries": 3}}
        after = {"settings": {"timeout": 20, "retries": 3}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Update nested settings",
            rationale="Test deep diff summary",
            before_config=before,
            after_config=after,
        )

        summary = proposal.get_diff_summary(deep=True)

        assert "settings.timeout" in summary
        assert "10" in summary
        assert "20" in summary
        assert "[~]" in summary  # Modified marker

    def test_get_diff_summary_deep_added_nested(self) -> None:
        """get_diff_summary with deep=True shows added nested keys."""
        before = {"config": {"a": 1}}
        after = {"config": {"a": 1, "b": 2}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Add nested key",
            rationale="Test deep diff summary added",
            before_config=before,
            after_config=after,
        )

        summary = proposal.get_diff_summary(deep=True)

        assert "config.b" in summary
        assert "(added)" in summary
        assert "[+]" in summary

    def test_get_diff_summary_deep_removed_nested(self) -> None:
        """get_diff_summary with deep=True shows removed nested keys."""
        before = {"config": {"a": 1, "b": 2}}
        after = {"config": {"a": 1}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Remove nested key",
            rationale="Test deep diff summary removed",
            before_config=before,
            after_config=after,
        )

        summary = proposal.get_diff_summary(deep=True)

        assert "config.b" in summary
        assert "(removed)" in summary
        assert "[-]" in summary

    def test_get_diff_summary_backwards_compatible(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """get_diff_summary without deep parameter works as before."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Backwards compat test",
            rationale="Ensure default summary unchanged",
            before_config=sample_before_config,
            after_config=sample_after_config,
        )

        summary = proposal.get_diff_summary()

        # Should show top-level keys
        assert "model_name" in summary
        assert "temperature" in summary

    def test_deep_diff_empty_nested_dict(self) -> None:
        """Deep diff handles empty nested dicts."""
        before = {"config": {}}
        after = {"config": {"new": "value"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Empty to populated",
            rationale="Test empty dict handling",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        assert "config.new" in deep_keys

    def test_deep_diff_with_list_in_nested(self) -> None:
        """Deep diff handles lists inside nested dicts."""
        before = {"config": {"items": [1, 2, 3]}}
        after = {"config": {"items": [1, 2, 3, 4]}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Nested list change",
            rationale="Test list in nested dict",
            before_config=before,
            after_config=after,
        )

        deep_keys = proposal.get_changed_keys(deep=True)
        # Lists are not recursed into, so the path stops at the list key
        assert "config.items" in deep_keys


# =============================================================================
# Phase 9: Type-Specific Validation Tests
# =============================================================================


@pytest.mark.unit
class TestTypeSpecificValidation:
    """Phase 9: Tests for type-specific validation methods (v0.4.0+).

    Tests the validation methods:
    - _validate_model_swap(): requires 'model' or 'model_name' key in both configs
    - _validate_config_change(): requires at least one overlapping key between configs
    - _validate_endpoint_change(): requires 'url' or 'endpoint' key with valid URL format
    """

    # =========================================================================
    # MODEL_SWAP Validation Tests
    # =========================================================================

    def test_model_swap_requires_model_key(self) -> None:
        """MODEL_SWAP fails without 'model' or 'model_name' key in configs."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.MODEL_SWAP,
                description="Swap to new model",
                rationale="Testing model swap validation",
                before_config={"temperature": 0.7, "max_tokens": 1000},
                after_config={"temperature": 0.5, "max_tokens": 2000},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT
        assert "model" in str(exc_info.value).lower()

    def test_model_swap_accepts_model_key(self) -> None:
        """MODEL_SWAP passes with 'model' key in both configs."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.MODEL_SWAP,
            description="Swap to new model",
            rationale="Testing model swap with 'model' key",
            before_config={"model": "gpt-4", "temperature": 0.7},
            after_config={"model": "gpt-4-turbo", "temperature": 0.5},
        )

        assert proposal.change_type == EnumChangeType.MODEL_SWAP
        assert proposal.before_config["model"] == "gpt-4"
        assert proposal.after_config["model"] == "gpt-4-turbo"

    def test_model_swap_accepts_model_name_key(self) -> None:
        """MODEL_SWAP passes with 'model_name' key in both configs."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.MODEL_SWAP,
            description="Swap to new model",
            rationale="Testing model swap with 'model_name' key",
            before_config={"model_name": "claude-3", "temperature": 0.7},
            after_config={"model_name": "claude-3.5", "temperature": 0.5},
        )

        assert proposal.change_type == EnumChangeType.MODEL_SWAP
        assert proposal.before_config["model_name"] == "claude-3"
        assert proposal.after_config["model_name"] == "claude-3.5"

    def test_model_swap_requires_model_in_both_configs(self) -> None:
        """MODEL_SWAP fails if 'model' or 'model_name' only in one config."""
        # Test: model key only in before_config
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.MODEL_SWAP,
                description="Swap to new model",
                rationale="Testing partial model key",
                before_config={"model_name": "gpt-4", "temperature": 0.7},
                after_config={"temperature": 0.5, "max_tokens": 2000},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT
        assert "after_config" in str(exc_info.value)

        # Test: model key only in after_config
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.MODEL_SWAP,
                description="Swap to new model",
                rationale="Testing partial model key",
                before_config={"temperature": 0.7, "max_tokens": 1000},
                after_config={"model": "gpt-4-turbo", "temperature": 0.5},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT
        assert "before_config" in str(exc_info.value)

    def test_model_swap_accepts_mixed_model_keys(self) -> None:
        """MODEL_SWAP passes with 'model' in one config and 'model_name' in other."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.MODEL_SWAP,
            description="Swap to new model",
            rationale="Testing mixed model keys",
            before_config={"model": "gpt-4", "temperature": 0.7},
            after_config={"model_name": "claude-3.5", "temperature": 0.5},
        )

        assert proposal.change_type == EnumChangeType.MODEL_SWAP

    # =========================================================================
    # CONFIG_CHANGE Validation Tests
    # =========================================================================

    def test_config_change_requires_overlapping_keys(self) -> None:
        """CONFIG_CHANGE fails with no overlapping keys between configs."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description="Change configuration",
                rationale="Testing config change validation",
                before_config={"old_key": "old_value", "another_old": 123},
                after_config={"new_key": "new_value", "another_new": 456},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT
        assert "common key" in str(exc_info.value).lower()

    def test_config_change_accepts_overlapping_keys(self) -> None:
        """CONFIG_CHANGE passes with at least one overlapping key."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Change configuration",
            rationale="Testing config change with overlapping keys",
            before_config={"shared_key": "old_value", "only_before": 123},
            after_config={"shared_key": "new_value", "only_after": 456},
        )

        assert proposal.change_type == EnumChangeType.CONFIG_CHANGE
        assert "shared_key" in proposal.before_config
        assert "shared_key" in proposal.after_config

    def test_config_change_accepts_multiple_overlapping_keys(self) -> None:
        """CONFIG_CHANGE passes with multiple overlapping keys."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Change multiple configs",
            rationale="Testing config change with multiple overlapping keys",
            before_config={"key1": "old1", "key2": "old2", "key3": "old3"},
            after_config={"key1": "new1", "key2": "new2", "key3": "new3"},
        )

        assert proposal.change_type == EnumChangeType.CONFIG_CHANGE
        changed_keys = proposal.get_changed_keys()
        assert len(changed_keys) == 3

    # =========================================================================
    # ENDPOINT_CHANGE Validation Tests
    # =========================================================================

    def test_endpoint_change_requires_url_or_endpoint_key(self) -> None:
        """ENDPOINT_CHANGE fails without 'url' or 'endpoint' key in configs."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing endpoint change validation",
                before_config={"host": "old.example.com", "port": 8080},
                after_config={"host": "new.example.com", "port": 9090},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT
        assert (
            "url" in str(exc_info.value).lower()
            or "endpoint" in str(exc_info.value).lower()
        )

    def test_endpoint_change_accepts_url_key(self) -> None:
        """ENDPOINT_CHANGE passes with valid 'url' key."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Change URL endpoint",
            rationale="Testing endpoint change with 'url' key",
            before_config={"url": "https://api.old.example.com/v1", "timeout": 30},
            after_config={"url": "https://api.new.example.com/v2", "timeout": 60},
        )

        assert proposal.change_type == EnumChangeType.ENDPOINT_CHANGE
        assert "url" in proposal.before_config
        assert "url" in proposal.after_config

    def test_endpoint_change_accepts_endpoint_key(self) -> None:
        """ENDPOINT_CHANGE passes with valid 'endpoint' key."""
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Change endpoint",
            rationale="Testing endpoint change with 'endpoint' key",
            before_config={"endpoint": "https://old.api.com/service", "retries": 3},
            after_config={"endpoint": "https://new.api.com/service", "retries": 5},
        )

        assert proposal.change_type == EnumChangeType.ENDPOINT_CHANGE
        assert "endpoint" in proposal.before_config
        assert "endpoint" in proposal.after_config

    def test_endpoint_change_validates_url_format(self) -> None:
        """ENDPOINT_CHANGE fails with invalid URL format."""
        # Test invalid URL in before_config
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing URL format validation",
                before_config={"url": "not-a-valid-url", "timeout": 30},
                after_config={"url": "https://api.example.com/v1", "timeout": 60},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "invalid url" in str(exc_info.value).lower()

        # Test invalid URL in after_config
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing URL format validation",
                before_config={"url": "https://api.example.com/v1", "timeout": 30},
                after_config={"url": "ftp://not-http-url.com", "timeout": 60},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "invalid url" in str(exc_info.value).lower()

    def test_endpoint_change_accepts_valid_url_formats(self) -> None:
        """ENDPOINT_CHANGE accepts various valid URL formats."""
        valid_url_pairs = [
            # HTTP and HTTPS
            ("http://example.com", "https://example.com"),
            # With ports
            ("https://api.example.com:8080", "https://api.example.com:9090"),
            # With paths
            ("https://api.example.com/v1/users", "https://api.example.com/v2/users"),
            # With query parameters
            (
                "https://api.example.com/search?q=test",
                "https://api.example.com/search?q=new",
            ),
            # IP addresses
            ("http://192.168.1.1:8080", "http://192.168.1.2:8080"),
            # Localhost
            ("http://localhost:3000", "http://localhost:4000"),
            # With subdomain
            ("https://api.staging.example.com", "https://api.prod.example.com"),
        ]

        for before_url, after_url in valid_url_pairs:
            proposal = ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description=f"Change from {before_url}",
                rationale="Testing various valid URL formats",
                before_config={"url": before_url},
                after_config={"url": after_url},
            )

            assert proposal.change_type == EnumChangeType.ENDPOINT_CHANGE
            assert proposal.before_config["url"] == before_url
            assert proposal.after_config["url"] == after_url

    def test_endpoint_change_accepts_url_in_only_one_config(self) -> None:
        """ENDPOINT_CHANGE passes with 'url' in only one config."""
        # URL only in after_config (adding an endpoint)
        proposal = ModelChangeProposal.create(
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Add endpoint URL",
            rationale="Testing URL in only after_config",
            before_config={"enabled": False},
            after_config={"enabled": True, "url": "https://api.example.com/v1"},
        )

        assert proposal.change_type == EnumChangeType.ENDPOINT_CHANGE
        assert "url" not in proposal.before_config
        assert "url" in proposal.after_config

    def test_endpoint_change_with_nested_endpoint_structure_raises_error(
        self, nested_before_config: dict, nested_after_config: dict
    ) -> None:
        """ENDPOINT_CHANGE fails with nested 'endpoint' structure (dict, not string URL)."""
        # The nested configs have 'endpoint' as a nested dict with 'url' inside,
        # which should now raise an error since 'endpoint' must be a string URL
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change nested endpoint",
                rationale="Testing nested endpoint structure",
                before_config=nested_before_config,
                after_config=nested_after_config,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be a string" in str(exc_info.value)
        assert "dict" in str(exc_info.value)

    def test_endpoint_change_non_string_url_raises_error(self) -> None:
        """ENDPOINT_CHANGE fails with non-string URL values (dict)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint with dict value",
                rationale="Testing non-string URL value",
                before_config={"endpoint": {"host": "old.example.com", "port": 8080}},
                after_config={"endpoint": {"host": "new.example.com", "port": 9090}},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be a string" in str(exc_info.value)
        assert "dict" in str(exc_info.value)

    def test_endpoint_change_non_string_url_in_before_config_only(self) -> None:
        """ENDPOINT_CHANGE fails with non-string URL in before_config only."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing non-string URL in before_config",
                before_config={"url": 12345},  # Integer instead of string
                after_config={"url": "https://api.example.com/v1"},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "before_config" in str(exc_info.value)
        assert "must be a string" in str(exc_info.value)
        assert "int" in str(exc_info.value)

    def test_endpoint_change_non_string_url_in_after_config_only(self) -> None:
        """ENDPOINT_CHANGE fails with non-string URL in after_config only."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing non-string URL in after_config",
                before_config={"url": "https://api.example.com/v1"},
                after_config={
                    "url": ["https://api.example.com/v2"]
                },  # List instead of string
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "after_config" in str(exc_info.value)
        assert "must be a string" in str(exc_info.value)
        assert "list" in str(exc_info.value)

    def test_endpoint_change_non_string_endpoint_key(self) -> None:
        """ENDPOINT_CHANGE fails with non-string 'endpoint' key value."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing non-string endpoint value",
                before_config={"endpoint": None},  # None instead of string
                after_config={"endpoint": "https://api.example.com/v1"},
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be a string" in str(exc_info.value)
        assert "NoneType" in str(exc_info.value)

    def test_endpoint_change_non_string_url_error_includes_key_name(self) -> None:
        """ENDPOINT_CHANGE error message includes the offending key name."""
        # Test with 'url' key
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing error message content",
                before_config={"url": {"nested": "value"}},
                after_config={"url": "https://api.example.com/v1"},
            )

        assert "'url'" in str(exc_info.value)

        # Test with 'endpoint' key
        with pytest.raises(ModelOnexError) as exc_info:
            ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description="Change endpoint",
                rationale="Testing error message content",
                before_config={"endpoint": 999.99},  # Float instead of string
                after_config={"endpoint": "https://api.example.com/v1"},
            )

        assert "'endpoint'" in str(exc_info.value)
        assert "float" in str(exc_info.value)

    def test_endpoint_change_invalid_ip_rejected(self) -> None:
        """Invalid IP addresses should be rejected for endpoint changes.

        Tests that IP addresses with octets outside the valid 0-255 range
        are correctly rejected by the URL validation pattern.
        """
        invalid_ips = ["999.999.999.999", "256.1.1.1", "300.200.100.50", "1.2.3.256"]
        for ip in invalid_ips:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelChangeProposal.create(
                    change_type=EnumChangeType.ENDPOINT_CHANGE,
                    description="Test endpoint change",
                    before_config={"url": f"http://{ip}:8000"},
                    after_config={"url": "http://localhost:8000"},
                    rationale="Testing invalid IP validation",
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "Invalid URL format" in str(exc_info.value.message)

    def test_endpoint_change_valid_ip_edge_cases(self) -> None:
        """Valid edge case IP addresses should be accepted for endpoint changes.

        Tests boundary values for IP address octets (0 and 255) as well as
        typical IP addresses to ensure they pass validation.
        """
        valid_ip_pairs = [
            # Boundary values
            ("http://0.0.0.0:8000", "http://0.0.0.1:8000"),
            ("http://255.255.255.255:8000", "http://255.255.255.254:8000"),
            # Typical IP addresses
            ("http://1.2.3.4:8000", "http://5.6.7.8:8000"),
            ("http://10.0.0.1:8000", "http://10.0.0.2:8000"),
            ("http://172.16.0.1:8000", "http://172.16.0.2:8000"),
            ("http://192.168.1.1:8000", "http://192.168.1.2:8000"),
            # Single octet edge cases
            ("http://0.1.1.1:8000", "http://1.1.1.1:8000"),
            ("http://255.1.1.1:8000", "http://254.1.1.1:8000"),
            ("http://1.0.1.1:8000", "http://1.1.1.1:8000"),
            ("http://1.255.1.1:8000", "http://1.254.1.1:8000"),
        ]

        for before_url, after_url in valid_ip_pairs:
            proposal = ModelChangeProposal.create(
                change_type=EnumChangeType.ENDPOINT_CHANGE,
                description=f"Change from {before_url}",
                rationale="Testing valid IP edge cases",
                before_config={"url": before_url},
                after_config={"url": after_url},
            )

            assert proposal.change_type == EnumChangeType.ENDPOINT_CHANGE
            assert proposal.before_config["url"] == before_url
            assert proposal.after_config["url"] == after_url


# =============================================================================
# Phase 10: Max Depth Recursion Limit Tests
# =============================================================================


@pytest.mark.unit
class TestMaxDepthRecursionLimit:
    """Phase 10: Tests for max_depth parameter in deep diff operations (v0.4.0+).

    Tests the defensive recursion limit feature that prevents stack overflow
    or poor performance with very deeply nested configurations.
    """

    def test_max_depth_zero_no_recursion(self) -> None:
        """max_depth=0 should not recurse into nested dicts at all."""
        before = {"config": {"a": 1}}
        after = {"config": {"a": 2}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test max_depth=0",
            rationale="Testing zero depth",
            before_config=before,
            after_config=after,
        )

        # With max_depth=0, should report 'config' as changed, not 'config.a'
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=0)
        assert deep_keys == {"config"}

    def test_max_depth_one_single_level_recursion(self) -> None:
        """max_depth=1 should recurse one level only."""
        before = {"level1": {"level2": {"level3": "old"}}}
        after = {"level1": {"level2": {"level3": "new"}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test max_depth=1",
            rationale="Testing single level depth",
            before_config=before,
            after_config=after,
        )

        # With max_depth=1, should recurse into level1, but stop at level2
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=1)
        assert deep_keys == {"level1.level2"}

    def test_max_depth_two_two_level_recursion(self) -> None:
        """max_depth=2 should recurse two levels."""
        before = {"l1": {"l2": {"l3": {"l4": "old"}}}}
        after = {"l1": {"l2": {"l3": {"l4": "new"}}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test max_depth=2",
            rationale="Testing two level depth",
            before_config=before,
            after_config=after,
        )

        # With max_depth=2, should recurse into l1.l2, but stop at l3
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=2)
        assert deep_keys == {"l1.l2.l3"}

    def test_max_depth_default_is_ten(self) -> None:
        """Default max_depth should be 10 (allowing 10 levels of recursion)."""
        # Create a structure 12 levels deep
        before: dict = {"value": "old"}
        after: dict = {"value": "new"}
        for i in range(11):  # 11 wrapping levels
            before = {f"l{11 - i}": before}
            after = {f"l{11 - i}": after}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test default max_depth",
            rationale="Testing default depth of 10",
            before_config=before,
            after_config=after,
        )

        # With default max_depth=10, should stop at l11 (10 levels of recursion)
        # l1 -> l2 -> ... -> l10 -> l11 (stops here, doesn't recurse into value)
        deep_keys = proposal.get_changed_keys(deep=True)
        # After 10 levels of recursion (l1 through l10), we hit l11 which contains
        # the nested dict, but we're at depth 10 so we report l1.l2...l11 as changed
        expected_path = ".".join([f"l{i}" for i in range(1, 12)])
        assert deep_keys == {expected_path}

    def test_max_depth_within_limit_recurses_fully(self) -> None:
        """When nesting is within max_depth, should recurse to the leaf."""
        before = {"a": {"b": {"c": "old"}}}
        after = {"a": {"b": {"c": "new"}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test within limit",
            rationale="Testing full recursion within limit",
            before_config=before,
            after_config=after,
        )

        # With max_depth=10 (default), 3 levels should fully recurse
        deep_keys = proposal.get_changed_keys(deep=True)
        assert deep_keys == {"a.b.c"}

    def test_max_depth_with_mixed_depths(self) -> None:
        """max_depth should correctly handle configs with varying nesting depths."""
        before = {
            "shallow": "old1",
            "medium": {"nested": "old2"},
            "deep": {"l1": {"l2": {"l3": "old3"}}},
        }
        after = {
            "shallow": "new1",
            "medium": {"nested": "new2"},
            "deep": {"l1": {"l2": {"l3": "new3"}}},
        }

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test mixed depths",
            rationale="Testing mixed depth nesting",
            before_config=before,
            after_config=after,
        )

        # With max_depth=1, should stop at first nested level
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=1)
        assert "shallow" in deep_keys
        assert "medium.nested" in deep_keys
        assert "deep.l1" in deep_keys  # Stops here, doesn't go to l2

        # With max_depth=2
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=2)
        assert "shallow" in deep_keys
        assert "medium.nested" in deep_keys
        assert "deep.l1.l2" in deep_keys  # Stops here, doesn't go to l3

    def test_max_depth_get_diff_summary(self) -> None:
        """get_diff_summary should also respect max_depth."""
        before = {"config": {"nested": {"value": 1}}}
        after = {"config": {"nested": {"value": 2}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test diff summary max_depth",
            rationale="Testing diff summary with depth limit",
            before_config=before,
            after_config=after,
        )

        # With max_depth=1, should report config.nested as changed
        summary = proposal.get_diff_summary(deep=True, max_depth=1)
        assert "config.nested" in summary
        assert "config.nested.value" not in summary

        # With default depth, should report config.nested.value
        summary = proposal.get_diff_summary(deep=True)
        assert "config.nested.value" in summary

    def test_max_depth_none_uses_default(self) -> None:
        """max_depth=None should use the default value of 10."""
        before = {"a": {"b": "old"}}
        after = {"a": {"b": "new"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test max_depth=None",
            rationale="Testing None uses default",
            before_config=before,
            after_config=after,
        )

        # Explicitly passing None should behave same as not passing
        keys_with_none = proposal.get_changed_keys(deep=True, max_depth=None)
        keys_without = proposal.get_changed_keys(deep=True)
        assert keys_with_none == keys_without == {"a.b"}

    def test_max_depth_ignored_when_deep_false(self) -> None:
        """max_depth should be ignored when deep=False."""
        before = {"config": {"nested": "old"}}
        after = {"config": {"nested": "new"}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test max_depth ignored",
            rationale="Testing max_depth ignored for shallow compare",
            before_config=before,
            after_config=after,
        )

        # max_depth should have no effect when deep=False
        shallow_keys_no_depth = proposal.get_changed_keys(deep=False)
        shallow_keys_with_depth = proposal.get_changed_keys(deep=False, max_depth=0)
        assert shallow_keys_no_depth == shallow_keys_with_depth == {"config"}

    def test_max_depth_at_exact_limit(self) -> None:
        """Test behavior exactly at the max_depth boundary."""
        # Create exactly 3 levels of nesting
        before = {"l1": {"l2": {"l3": "old"}}}
        after = {"l1": {"l2": {"l3": "new"}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test exact limit",
            rationale="Testing behavior at exact depth limit",
            before_config=before,
            after_config=after,
        )

        # max_depth=2 means we can recurse twice (l1 -> l2), then l3 is the limit
        # At l2, we see l3 is a nested dict, but we're at depth 2, so we report l2.l3
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=2)
        assert deep_keys == {"l1.l2.l3"}

        # max_depth=3 allows full recursion
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=3)
        assert deep_keys == {"l1.l2.l3"}

    def test_max_depth_with_added_nested_key(self) -> None:
        """max_depth should work correctly with added nested keys."""
        before: dict[str, object] = {"config": {}}
        after: dict[str, object] = {"config": {"nested": {"deep": "value"}}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test added nested key",
            rationale="Testing max_depth with added nested structure",
            before_config=before,
            after_config=after,
        )

        # With max_depth=0, should report 'config' as changed
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=0)
        assert deep_keys == {"config"}

        # With max_depth=1, should report 'config.nested'
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=1)
        assert deep_keys == {"config.nested"}

    def test_max_depth_with_removed_nested_key(self) -> None:
        """max_depth should work correctly with removed nested keys."""
        before: dict[str, object] = {"config": {"nested": {"deep": "value"}}}
        after: dict[str, object] = {"config": {}}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test removed nested key",
            rationale="Testing max_depth with removed nested structure",
            before_config=before,
            after_config=after,
        )

        # With max_depth=0, should report 'config' as changed
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=0)
        assert deep_keys == {"config"}

        # With max_depth=1, should report 'config.nested'
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=1)
        assert deep_keys == {"config.nested"}

    def test_max_depth_large_value_no_impact(self) -> None:
        """Large max_depth should have no impact on shallow structures."""
        before = {"a": 1, "b": 2}
        after = {"a": 10, "b": 20}

        proposal = ModelChangeProposal(
            change_type=EnumChangeType.CONFIG_CHANGE,
            description="Test large max_depth",
            rationale="Testing large max_depth on shallow structure",
            before_config=before,
            after_config=after,
        )

        # Large max_depth should work fine with shallow structures
        deep_keys = proposal.get_changed_keys(deep=True, max_depth=1000)
        assert deep_keys == {"a", "b"}
