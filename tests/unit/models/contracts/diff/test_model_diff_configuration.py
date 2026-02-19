# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDiffConfiguration."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.diff.model_diff_configuration import (
    ModelDiffConfiguration,
)


@pytest.mark.unit
class TestModelDiffConfiguration:
    """Test suite for ModelDiffConfiguration model."""

    def test_default_exclude_fields(self) -> None:
        """Test default exclusions include transient fields."""
        config = ModelDiffConfiguration()
        assert "correlation_id" in config.exclude_fields
        assert "execution_id" in config.exclude_fields
        assert "computed_at" in config.exclude_fields
        assert "fingerprint" in config.exclude_fields

    def test_default_identity_keys(self) -> None:
        """Test default identity keys for common list fields."""
        config = ModelDiffConfiguration()
        assert config.identity_keys["transitions"] == "name"
        assert config.identity_keys["states"] == "name"
        assert config.identity_keys["steps"] == "step_id"
        assert config.identity_keys["actions"] == "name"
        assert config.identity_keys["events"] == "event_type"
        assert config.identity_keys["handlers"] == "handler_id"
        assert config.identity_keys["dependencies"] == "name"

    def test_get_identity_key_exact_match(self) -> None:
        """Test exact field path lookup."""
        config = ModelDiffConfiguration()
        assert config.get_identity_key("transitions") == "name"
        assert config.get_identity_key("steps") == "step_id"

    def test_get_identity_key_last_segment(self) -> None:
        """Test lookup by last path segment."""
        config = ModelDiffConfiguration()
        assert config.get_identity_key("meta.transitions") == "name"
        assert config.get_identity_key("workflow.steps") == "step_id"
        assert config.get_identity_key("nested.path.handlers") == "handler_id"

    def test_get_identity_key_not_found(self) -> None:
        """Test returns None for unknown fields."""
        config = ModelDiffConfiguration()
        assert config.get_identity_key("unknown_field") is None
        assert config.get_identity_key("meta.unknown") is None

    def test_should_exclude_exact_match(self) -> None:
        """Test exclusion by exact field path."""
        config = ModelDiffConfiguration()
        assert config.should_exclude("correlation_id") is True
        assert config.should_exclude("computed_at") is True
        assert config.should_exclude("fingerprint") is True

    def test_should_exclude_last_segment(self) -> None:
        """Test exclusion by field name in nested path."""
        config = ModelDiffConfiguration()
        assert config.should_exclude("meta.computed_at") is True
        assert config.should_exclude("workflow.correlation_id") is True
        assert config.should_exclude("nested.path.fingerprint") is True

    def test_should_not_exclude_valid_fields(self) -> None:
        """Test that non-excluded fields are not excluded."""
        config = ModelDiffConfiguration()
        assert config.should_exclude("name") is False
        assert config.should_exclude("version") is False
        assert config.should_exclude("meta.name") is False

    def test_frozen_model(self) -> None:
        """Test model is immutable."""
        config = ModelDiffConfiguration()
        with pytest.raises(ValidationError):
            config.include_unchanged = True  # type: ignore[misc]

    def test_custom_exclude_fields(self) -> None:
        """Test custom exclusion set."""
        config = ModelDiffConfiguration(
            exclude_fields=frozenset({"custom_field", "another_field"})
        )
        assert config.should_exclude("custom_field") is True
        assert config.should_exclude("another_field") is True
        assert config.should_exclude("correlation_id") is False

    def test_custom_identity_keys(self) -> None:
        """Test custom identity key mapping."""
        config = ModelDiffConfiguration(
            identity_keys={"my_list": "my_id", "other_list": "key"}
        )
        assert config.get_identity_key("my_list") == "my_id"
        assert config.get_identity_key("other_list") == "key"
        assert config.get_identity_key("transitions") is None

    def test_include_unchanged_default(self) -> None:
        """Test include_unchanged defaults to False."""
        config = ModelDiffConfiguration()
        assert config.include_unchanged is False

    def test_include_unchanged_true(self) -> None:
        """Test include_unchanged can be set to True."""
        config = ModelDiffConfiguration(include_unchanged=True)
        assert config.include_unchanged is True

    def test_normalize_before_diff_default(self) -> None:
        """Test normalize_before_diff defaults to True."""
        config = ModelDiffConfiguration()
        assert config.normalize_before_diff is True

    def test_normalize_before_diff_false(self) -> None:
        """Test normalize_before_diff can be set to False."""
        config = ModelDiffConfiguration(normalize_before_diff=False)
        assert config.normalize_before_diff is False

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelDiffConfiguration(
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_from_attributes_true(self) -> None:
        """Test model has from_attributes=True for pytest-xdist compatibility."""
        assert ModelDiffConfiguration.model_config.get("from_attributes") is True

    def test_empty_exclude_fields(self) -> None:
        """Test with empty exclude_fields set."""
        config = ModelDiffConfiguration(exclude_fields=frozenset())
        assert config.should_exclude("correlation_id") is False
        assert config.should_exclude("computed_at") is False

    def test_empty_identity_keys(self) -> None:
        """Test with empty identity_keys dict."""
        config = ModelDiffConfiguration(identity_keys={})
        assert config.get_identity_key("transitions") is None
        assert config.get_identity_key("steps") is None
