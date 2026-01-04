# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelChangeProposal model (OMN-1196).

Tests the change proposal model for representing proposed system changes
for evaluation. This model captures before/after configurations, change
metadata, and provides helper methods for change analysis.

This test file follows TDD principles - tests are written before implementation.

Related:
    - OMN-1196: Create ModelChangeProposal for system change evaluation
"""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Import will work once model is created
# These imports are commented to allow the test file to be created before implementation
# Uncomment once the model is implemented
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

    def test_endpoint_change_type_accepted(
        self, sample_before_config: dict, sample_after_config: dict
    ) -> None:
        """endpoint_change is a valid change_type."""
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Change endpoint",
            rationale="Testing endpoint change type",
            before_config=sample_before_config,
            after_config=sample_after_config,
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
        assert "change_type" in error_str or "invalid" in error_str.lower()

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
        assert "description" in error_str or "min_length" in error_str.lower()

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
        assert "rationale" in error_str or "min_length" in error_str.lower()

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
        assert "description" in error_str or "whitespace" in error_str.lower()

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
        assert "rationale" in error_str or "whitespace" in error_str.lower()

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
        assert "before_config" in error_str or "empty" in error_str.lower()

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
        assert "after_config" in error_str or "empty" in error_str.lower()

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
        assert "Extra inputs" in error_str or "unknown_field" in error_str


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
        proposal = ModelChangeProposal(
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Update endpoint",
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
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Change endpoint",
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
        # Should mention changed keys
        assert "model_name" in diff or "temperature" in diff or "max_tokens" in diff

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

        # Should contain some indication of old and new values
        # Could be format like "gpt-4 -> gpt-4-turbo" or similar
        assert "gpt-4" in diff or str(sample_before_config["temperature"]) in diff

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
            change_type=EnumChangeType.ENDPOINT_CHANGE,
            description="Breaking endpoint change",
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
        """Very long descriptions are handled (or rejected if there's a limit)."""
        long_description = "A" * 10000

        # If there's a max length, this should raise
        # If not, it should work
        try:
            proposal = ModelChangeProposal(
                change_type=EnumChangeType.CONFIG_CHANGE,
                description=long_description,
                rationale="Testing long description",
                before_config=sample_before_config,
                after_config=sample_after_config,
            )
            assert len(proposal.description) == 10000
        except ValidationError:
            # Expected if there's a max length constraint
            pass

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
