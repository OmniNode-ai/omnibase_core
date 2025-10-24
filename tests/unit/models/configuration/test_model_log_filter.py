"""Tests for ModelLogFilter."""

import pytest

from omnibase_core.models.configuration.model_log_filter import ModelLogFilter


class TestModelLogFilterBasics:
    def test_create_with_required_fields(self):
        filter = ModelLogFilter(filter_name="test_filter", filter_type="regex")
        assert filter.filter_name == "test_filter"
        assert filter.filter_type == "regex"
        assert filter.enabled is True

    def test_filter_type_validation(self):
        for ftype in ["regex", "field_match", "level_range", "keyword", "custom"]:
            filter = ModelLogFilter(filter_name="test", filter_type=ftype)
            assert filter.filter_type == ftype


class TestModelLogFilterMatching:
    def test_matches_message_disabled(self):
        filter = ModelLogFilter(filter_name="test", filter_type="regex", enabled=False)
        assert filter.matches_message(10, "test message", {}) is True

    def test_matches_regex(self):
        filter = ModelLogFilter(
            filter_name="test", filter_type="regex", regex_pattern="error.*occurred"
        )
        assert filter._matches_regex("error has occurred") is True
        assert filter._matches_regex("no match here") is False

    def test_matches_field(self):
        filter = ModelLogFilter(
            filter_name="test",
            filter_type="field_match",
            field_name="level",
            field_value="ERROR",
        )
        assert filter._matches_field({"level": "ERROR"}) is True
        assert filter._matches_field({"level": "INFO"}) is False

    def test_matches_level_range(self):
        filter = ModelLogFilter(
            filter_name="test", filter_type="level_range", min_level=10, max_level=50
        )
        assert filter._matches_level_range(30) is True
        assert filter._matches_level_range(5) is False
        assert filter._matches_level_range(60) is False

    def test_matches_keywords_case_sensitive(self):
        filter = ModelLogFilter(
            filter_name="test",
            filter_type="keyword",
            keywords=["ERROR", "WARN"],
            case_sensitive=True,
        )
        assert filter._matches_keywords("ERROR occurred") is True
        assert filter._matches_keywords("error occurred") is False

    def test_matches_keywords_case_insensitive(self):
        filter = ModelLogFilter(
            filter_name="test",
            filter_type="keyword",
            keywords=["ERROR", "WARN"],
            case_sensitive=False,
        )
        assert filter._matches_keywords("ERROR occurred") is True
        assert filter._matches_keywords("error occurred") is True

    def test_apply_filter_exclude(self, monkeypatch):
        """Test apply_filter with exclude action.

        Note: Current implementation doesn't actually use the 'action' field.
        This test verifies that matching messages are processed correctly.
        When action support is implemented, this test should be updated.
        """
        from omnibase_core.models.configuration.model_log_filter_config import (
            ModelLogFilterConfig,
        )

        # Mock random.random() to return deterministic value for should_sample()
        monkeypatch.setattr("random.random", lambda: 0.5)

        # Create filter with deterministic sampling (sample_rate=1.0)
        filter = ModelLogFilter(
            filter_name="test",
            filter_type="keyword",
            keywords=["debug"],
            action="exclude",
            configuration=ModelLogFilterConfig(sample_rate=1.0),
        )
        log_entry = {"level": 10, "message": "debug info", "user": "test"}
        result = filter.apply_filter(log_entry)

        # With sample_rate=1.0 and matching message, should return filtered entry
        assert result is not None
        assert result["message"] == "debug info"
        assert result["level"] == 10

    def test_apply_filter_include(self, monkeypatch):
        # Mock random.random() to return deterministic value for should_sample()
        monkeypatch.setattr("random.random", lambda: 0.5)

        filter = ModelLogFilter(
            filter_name="test",
            filter_type="keyword",
            keywords=["error"],
            action="include",
        )
        log_entry = {"level": 40, "message": "error occurred", "user": "test"}
        result = filter.apply_filter(log_entry)
        assert result is not None


class TestModelLogFilterSerialization:
    def test_serialization(self):
        filter = ModelLogFilter(filter_name="test", filter_type="regex")
        data = filter.model_dump()
        assert data["filter_name"] == "test"

    def test_roundtrip(self):
        original = ModelLogFilter(filter_name="test", filter_type="regex")
        data = original.model_dump()
        restored = ModelLogFilter.model_validate(data)
        assert restored.filter_name == original.filter_name
