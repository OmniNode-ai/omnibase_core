# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""
Comprehensive tests for ModelTopicParser and ModelParsedTopic.

Tests cover:
- parse() with ONEX Kafka format (onex.<domain>.<type>)
- parse() with Environment-Aware format (<env>.<domain>.<category>.<version>)
- parse() with invalid formats
- get_category() extraction
- matches_pattern() with wildcards (*, **)
- validate_topic() strict and non-strict modes

OMN-934: Message dispatch engine implementation
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_topic_taxonomy import EnumTopicType
from omnibase_core.models.dispatch.model_topic_parser import (
    EnumTopicStandard,
    ModelParsedTopic,
    ModelTopicParser,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def parser() -> ModelTopicParser:
    """Create a fresh ModelTopicParser for each test."""
    return ModelTopicParser()


# ============================================================================
# ModelParsedTopic Tests
# ============================================================================


@pytest.mark.unit
class TestModelParsedTopic:
    """Tests for ModelParsedTopic model."""

    def test_create_valid_parsed_topic(self) -> None:
        """Test creating a valid ModelParsedTopic."""
        parsed = ModelParsedTopic(
            raw_topic="onex.registration.events",
            standard=EnumTopicStandard.ONEX_KAFKA,
            domain="registration",
            category=EnumMessageCategory.EVENT,
            topic_type=EnumTopicType.EVENTS,
            is_valid=True,
        )

        assert parsed.raw_topic == "onex.registration.events"
        assert parsed.standard == EnumTopicStandard.ONEX_KAFKA
        assert parsed.domain == "registration"
        assert parsed.category == EnumMessageCategory.EVENT
        assert parsed.is_valid is True

    def test_create_invalid_parsed_topic(self) -> None:
        """Test creating an invalid ModelParsedTopic."""
        parsed = ModelParsedTopic(
            raw_topic="invalid.topic",
            standard=EnumTopicStandard.UNKNOWN,
            is_valid=False,
            validation_error="Topic does not match any known format",
        )

        assert parsed.is_valid is False
        assert parsed.validation_error is not None

    def test_is_routable_valid_topic(self) -> None:
        """Test is_routable() for valid topic with category."""
        parsed = ModelParsedTopic(
            raw_topic="onex.user.events",
            standard=EnumTopicStandard.ONEX_KAFKA,
            category=EnumMessageCategory.EVENT,
            is_valid=True,
        )

        assert parsed.is_routable() is True

    def test_is_routable_invalid_topic(self) -> None:
        """Test is_routable() for invalid topic."""
        parsed = ModelParsedTopic(
            raw_topic="invalid",
            standard=EnumTopicStandard.UNKNOWN,
            is_valid=False,
        )

        assert parsed.is_routable() is False

    def test_is_routable_no_category(self) -> None:
        """Test is_routable() when category is None."""
        parsed = ModelParsedTopic(
            raw_topic="onex.user.snapshots",  # snapshots don't map to a category
            standard=EnumTopicStandard.ONEX_KAFKA,
            category=None,  # No category for snapshots
            is_valid=True,
        )

        assert parsed.is_routable() is False

    def test_parsed_topic_immutable(self) -> None:
        """Test that ModelParsedTopic is immutable (frozen)."""
        from pydantic import ValidationError

        parsed = ModelParsedTopic(
            raw_topic="onex.user.events",
            standard=EnumTopicStandard.ONEX_KAFKA,
            is_valid=True,
        )

        with pytest.raises(ValidationError, match="frozen"):
            parsed.domain = "changed"  # type: ignore[misc]


# ============================================================================
# ONEX Kafka Format Tests
# ============================================================================


@pytest.mark.unit
class TestOnexKafkaFormat:
    """Tests for parsing ONEX Kafka format topics (onex.<domain>.<type>)."""

    def test_parse_onex_kafka_events(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX Kafka events topic."""
        result = parser.parse("onex.registration.events")

        assert result.is_valid is True
        assert result.standard == EnumTopicStandard.ONEX_KAFKA
        assert result.domain == "registration"
        assert result.category == EnumMessageCategory.EVENT
        assert result.topic_type == EnumTopicType.EVENTS

    def test_parse_onex_kafka_commands(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX Kafka commands topic."""
        result = parser.parse("onex.discovery.commands")

        assert result.is_valid is True
        assert result.standard == EnumTopicStandard.ONEX_KAFKA
        assert result.domain == "discovery"
        assert result.category == EnumMessageCategory.COMMAND
        assert result.topic_type == EnumTopicType.COMMANDS

    def test_parse_onex_kafka_intents(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX Kafka intents topic."""
        result = parser.parse("onex.workflow.intents")

        assert result.is_valid is True
        assert result.standard == EnumTopicStandard.ONEX_KAFKA
        assert result.domain == "workflow"
        assert result.category == EnumMessageCategory.INTENT
        assert result.topic_type == EnumTopicType.INTENTS

    def test_parse_onex_kafka_snapshots(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX Kafka snapshots topic (no category mapping)."""
        result = parser.parse("onex.state.snapshots")

        assert result.is_valid is True
        assert result.standard == EnumTopicStandard.ONEX_KAFKA
        assert result.domain == "state"
        assert result.category is None  # snapshots don't have a category
        assert result.topic_type == EnumTopicType.SNAPSHOTS

    def test_parse_onex_kafka_single_letter_domain(
        self, parser: ModelTopicParser
    ) -> None:
        """Test parsing ONEX Kafka with single-letter domain."""
        result = parser.parse("onex.a.events")

        assert result.is_valid is True
        assert result.domain == "a"

    def test_parse_onex_kafka_hyphenated_domain(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX Kafka with hyphenated domain."""
        result = parser.parse("onex.user-service.events")

        assert result.is_valid is True
        assert result.domain == "user-service"

    def test_parse_onex_kafka_case_insensitive(self, parser: ModelTopicParser) -> None:
        """Test that ONEX Kafka parsing is case-insensitive."""
        result = parser.parse("ONEX.REGISTRATION.EVENTS")

        assert result.is_valid is True
        assert result.standard == EnumTopicStandard.ONEX_KAFKA
        assert result.domain == "registration"  # Normalized to lowercase


# ============================================================================
# Environment-Aware Format Tests
# ============================================================================


@pytest.mark.unit
class TestEnvironmentAwareFormat:
    """Tests for parsing Environment-Aware format topics (<env>.<domain>.<category>.<version>)."""

    def test_parse_env_aware_dev(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware topic with dev environment."""
        result = parser.parse("dev.user.events.v1")

        assert result.is_valid is True
        assert result.standard == EnumTopicStandard.ENVIRONMENT_AWARE
        assert result.environment == "dev"
        assert result.domain == "user"
        assert result.category == EnumMessageCategory.EVENT
        assert result.version == "v1"

    def test_parse_env_aware_prod(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware topic with prod environment."""
        result = parser.parse("prod.order.commands.v2")

        assert result.is_valid is True
        assert result.environment == "prod"
        assert result.domain == "order"
        assert result.category == EnumMessageCategory.COMMAND
        assert result.version == "v2"

    def test_parse_env_aware_staging(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware topic with staging environment."""
        result = parser.parse("staging.payment.intents.v1")

        assert result.is_valid is True
        assert result.environment == "staging"
        assert result.domain == "payment"
        assert result.category == EnumMessageCategory.INTENT

    def test_parse_env_aware_test(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware topic with test environment."""
        result = parser.parse("test.notification.events.v3")

        assert result.is_valid is True
        assert result.environment == "test"
        assert result.version == "v3"

    def test_parse_env_aware_local(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware topic with local environment."""
        result = parser.parse("local.auth.commands.v1")

        assert result.is_valid is True
        assert result.environment == "local"

    def test_parse_env_aware_case_insensitive(self, parser: ModelTopicParser) -> None:
        """Test that Environment-Aware parsing is case-insensitive."""
        result = parser.parse("DEV.USER.EVENTS.V1")

        assert result.is_valid is True
        assert result.environment == "dev"  # Normalized to lowercase
        assert result.domain == "user"

    def test_parse_env_aware_higher_version(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware with multi-digit version."""
        result = parser.parse("prod.order.events.v123")

        assert result.is_valid is True
        assert result.version == "v123"


# ============================================================================
# Invalid Format Tests
# ============================================================================


@pytest.mark.unit
class TestInvalidFormats:
    """Tests for parsing invalid topic formats."""

    def test_parse_empty_string(self, parser: ModelTopicParser) -> None:
        """Test parsing empty string."""
        result = parser.parse("")

        assert result.is_valid is False
        assert result.standard == EnumTopicStandard.UNKNOWN
        assert result.validation_error is not None

    def test_parse_whitespace_only(self, parser: ModelTopicParser) -> None:
        """Test parsing whitespace-only string."""
        result = parser.parse("   ")

        assert result.is_valid is False
        assert (
            "empty" in result.validation_error.lower()
            or "whitespace" in result.validation_error.lower()
        )

    def test_parse_no_category(self, parser: ModelTopicParser) -> None:
        """Test parsing topic without category segment."""
        result = parser.parse("some.random.topic")

        assert result.is_valid is False
        assert result.standard == EnumTopicStandard.UNKNOWN

    def test_parse_invalid_onex_prefix(self, parser: ModelTopicParser) -> None:
        """Test parsing with wrong prefix (not 'onex')."""
        result = parser.parse("notx.user.events")

        # May fallback to category detection
        assert result.standard != EnumTopicStandard.ONEX_KAFKA

    def test_parse_onex_missing_domain(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX format with missing domain."""
        result = parser.parse("onex..events")

        assert result.standard != EnumTopicStandard.ONEX_KAFKA

    def test_parse_onex_invalid_type(self, parser: ModelTopicParser) -> None:
        """Test parsing ONEX format with invalid type."""
        result = parser.parse("onex.user.invalid")

        assert result.standard != EnumTopicStandard.ONEX_KAFKA

    def test_parse_env_aware_invalid_env(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware with invalid environment."""
        result = parser.parse("invalid.user.events.v1")

        assert result.standard != EnumTopicStandard.ENVIRONMENT_AWARE

    def test_parse_env_aware_missing_version(self, parser: ModelTopicParser) -> None:
        """Test parsing Environment-Aware without version."""
        result = parser.parse("dev.user.events")

        # Should not match ENVIRONMENT_AWARE pattern
        assert result.standard != EnumTopicStandard.ENVIRONMENT_AWARE

    def test_parse_env_aware_invalid_version_format(
        self, parser: ModelTopicParser
    ) -> None:
        """Test parsing Environment-Aware with invalid version format."""
        result = parser.parse("dev.user.events.version1")

        assert result.standard != EnumTopicStandard.ENVIRONMENT_AWARE


# ============================================================================
# Fallback Category Detection Tests
# ============================================================================


@pytest.mark.unit
class TestFallbackCategoryDetection:
    """Tests for fallback category detection from non-standard topics."""

    def test_parse_fallback_events(self, parser: ModelTopicParser) -> None:
        """Test fallback detection for topics containing .events."""
        result = parser.parse("some.custom.events.format")

        assert result.is_valid is True  # Category was detected
        assert result.category == EnumMessageCategory.EVENT
        assert result.standard == EnumTopicStandard.UNKNOWN

    def test_parse_fallback_commands(self, parser: ModelTopicParser) -> None:
        """Test fallback detection for topics containing .commands."""
        result = parser.parse("some.custom.commands.format")

        assert result.is_valid is True
        assert result.category == EnumMessageCategory.COMMAND

    def test_parse_fallback_intents(self, parser: ModelTopicParser) -> None:
        """Test fallback detection for topics containing .intents."""
        result = parser.parse("some.custom.intents.format")

        assert result.is_valid is True
        assert result.category == EnumMessageCategory.INTENT

    def test_parse_fallback_events_at_end(self, parser: ModelTopicParser) -> None:
        """Test fallback detection for topics ending with .events."""
        result = parser.parse("custom.topic.events")

        assert result.category == EnumMessageCategory.EVENT


# ============================================================================
# get_category() Tests
# ============================================================================


@pytest.mark.unit
class TestGetCategory:
    """Tests for get_category() method."""

    def test_get_category_onex_events(self, parser: ModelTopicParser) -> None:
        """Test get_category for ONEX events topic."""
        category = parser.get_category("onex.registration.events")

        assert category == EnumMessageCategory.EVENT

    def test_get_category_onex_commands(self, parser: ModelTopicParser) -> None:
        """Test get_category for ONEX commands topic."""
        category = parser.get_category("onex.discovery.commands")

        assert category == EnumMessageCategory.COMMAND

    def test_get_category_onex_intents(self, parser: ModelTopicParser) -> None:
        """Test get_category for ONEX intents topic."""
        category = parser.get_category("onex.workflow.intents")

        assert category == EnumMessageCategory.INTENT

    def test_get_category_env_aware(self, parser: ModelTopicParser) -> None:
        """Test get_category for Environment-Aware topic."""
        category = parser.get_category("dev.user.events.v1")

        assert category == EnumMessageCategory.EVENT

    def test_get_category_invalid_topic(self, parser: ModelTopicParser) -> None:
        """Test get_category for invalid topic returns None."""
        category = parser.get_category("invalid.topic")

        assert category is None


# ============================================================================
# matches_pattern() Tests
# ============================================================================


@pytest.mark.unit
class TestMatchesPattern:
    """Tests for matches_pattern() with wildcards."""

    def test_exact_match(self, parser: ModelTopicParser) -> None:
        """Test exact pattern matching."""
        assert parser.matches_pattern("onex.user.events", "onex.user.events") is True
        assert parser.matches_pattern("onex.user.events", "onex.user.commands") is False

    def test_single_wildcard(self, parser: ModelTopicParser) -> None:
        """Test single wildcard (*) matches single segment."""
        pattern = "onex.*.events"

        assert parser.matches_pattern(pattern, "onex.user.events") is True
        assert parser.matches_pattern(pattern, "onex.order.events") is True
        assert parser.matches_pattern(pattern, "onex.user.commands") is False
        assert (
            parser.matches_pattern(pattern, "onex.user.service.events") is False
        )  # * doesn't match dots

    def test_double_wildcard(self, parser: ModelTopicParser) -> None:
        """Test double wildcard (**) matches multiple segments."""
        pattern = "dev.**"

        assert parser.matches_pattern(pattern, "dev.user.events.v1") is True
        assert parser.matches_pattern(pattern, "dev.order.commands.v2") is True
        assert parser.matches_pattern(pattern, "prod.user.events.v1") is False

    def test_double_wildcard_middle(self, parser: ModelTopicParser) -> None:
        """Test double wildcard in the middle of pattern."""
        pattern = "**.events.*"

        assert parser.matches_pattern(pattern, "dev.user.events.v1") is True
        assert parser.matches_pattern(pattern, "prod.order.events.v2") is True
        assert (
            parser.matches_pattern(pattern, "dev.user.events") is False
        )  # Missing segment after events

    def test_double_wildcard_at_end(self, parser: ModelTopicParser) -> None:
        """Test double wildcard at end of pattern."""
        pattern = "dev.user.**"

        assert parser.matches_pattern(pattern, "dev.user.events.v1") is True
        assert parser.matches_pattern(pattern, "dev.user.commands.v2") is True

    def test_mixed_wildcards(self, parser: ModelTopicParser) -> None:
        """Test pattern with both * and **."""
        pattern = "*.user.**"

        assert parser.matches_pattern(pattern, "dev.user.events.v1") is True
        assert parser.matches_pattern(pattern, "prod.user.commands.v2") is True
        assert (
            parser.matches_pattern(pattern, "dev.order.events.v1") is False
        )  # Wrong domain

    def test_wildcard_case_insensitive(self, parser: ModelTopicParser) -> None:
        """Test pattern matching is case-insensitive."""
        pattern = "onex.*.events"

        assert parser.matches_pattern(pattern, "ONEX.USER.EVENTS") is True
        assert parser.matches_pattern(pattern, "onex.USER.events") is True

    def test_empty_pattern(self, parser: ModelTopicParser) -> None:
        """Test empty pattern returns False."""
        assert parser.matches_pattern("", "onex.user.events") is False

    def test_empty_topic(self, parser: ModelTopicParser) -> None:
        """Test empty topic returns False."""
        assert parser.matches_pattern("onex.*.events", "") is False


# ============================================================================
# validate_topic() Tests
# ============================================================================


@pytest.mark.unit
class TestValidateTopic:
    """Tests for validate_topic() in strict and non-strict modes."""

    def test_validate_onex_kafka_non_strict(self, parser: ModelTopicParser) -> None:
        """Test validate_topic for ONEX Kafka format in non-strict mode."""
        is_valid, error = parser.validate_topic("onex.registration.events")

        assert is_valid is True
        assert error is None

    def test_validate_onex_kafka_strict(self, parser: ModelTopicParser) -> None:
        """Test validate_topic for ONEX Kafka format in strict mode."""
        is_valid, error = parser.validate_topic("onex.registration.events", strict=True)

        assert is_valid is True
        assert error is None

    def test_validate_env_aware_non_strict(self, parser: ModelTopicParser) -> None:
        """Test validate_topic for Environment-Aware in non-strict mode."""
        is_valid, error = parser.validate_topic("dev.user.events.v1")

        assert is_valid is True
        assert error is None

    def test_validate_env_aware_strict_fails(self, parser: ModelTopicParser) -> None:
        """Test validate_topic for Environment-Aware in strict mode fails."""
        is_valid, error = parser.validate_topic("dev.user.events.v1", strict=True)

        assert is_valid is False
        assert error is not None
        assert "ONEX Kafka format" in error

    def test_validate_invalid_topic_non_strict(self, parser: ModelTopicParser) -> None:
        """Test validate_topic for invalid topic in non-strict mode."""
        is_valid, error = parser.validate_topic("completely.invalid.topic")

        assert is_valid is False
        assert error is not None

    def test_validate_invalid_topic_strict(self, parser: ModelTopicParser) -> None:
        """Test validate_topic for invalid topic in strict mode."""
        is_valid, error = parser.validate_topic("completely.invalid.topic", strict=True)

        assert is_valid is False
        assert error is not None


# ============================================================================
# Convenience Method Tests
# ============================================================================


@pytest.mark.unit
class TestConvenienceMethods:
    """Tests for convenience methods."""

    def test_is_onex_kafka_format_true(self, parser: ModelTopicParser) -> None:
        """Test is_onex_kafka_format returns True for valid ONEX topic."""
        assert parser.is_onex_kafka_format("onex.user.events") is True

    def test_is_onex_kafka_format_false(self, parser: ModelTopicParser) -> None:
        """Test is_onex_kafka_format returns False for non-ONEX topic."""
        assert parser.is_onex_kafka_format("dev.user.events.v1") is False

    def test_is_environment_aware_format_true(self, parser: ModelTopicParser) -> None:
        """Test is_environment_aware_format returns True for valid env-aware topic."""
        assert parser.is_environment_aware_format("dev.user.events.v1") is True

    def test_is_environment_aware_format_false(self, parser: ModelTopicParser) -> None:
        """Test is_environment_aware_format returns False for non-env-aware topic."""
        assert parser.is_environment_aware_format("onex.user.events") is False

    def test_extract_domain_onex(self, parser: ModelTopicParser) -> None:
        """Test extract_domain for ONEX Kafka topic."""
        domain = parser.extract_domain("onex.registration.events")

        assert domain == "registration"

    def test_extract_domain_env_aware(self, parser: ModelTopicParser) -> None:
        """Test extract_domain for Environment-Aware topic."""
        domain = parser.extract_domain("dev.user.events.v1")

        assert domain == "user"

    def test_extract_domain_invalid(self, parser: ModelTopicParser) -> None:
        """Test extract_domain for invalid topic."""
        domain = parser.extract_domain("invalid")

        assert domain is None


# ============================================================================
# Thread Safety Tests
# ============================================================================


@pytest.mark.unit
class TestThreadSafety:
    """Tests verifying thread-safety characteristics."""

    def test_parser_is_stateless(self) -> None:
        """Test that ModelTopicParser is stateless."""
        parser1 = ModelTopicParser()
        parser2 = ModelTopicParser()

        # Both parsers should produce identical results
        result1 = parser1.parse("onex.user.events")
        result2 = parser2.parse("onex.user.events")

        assert result1.raw_topic == result2.raw_topic
        assert result1.standard == result2.standard
        assert result1.domain == result2.domain
        assert result1.category == result2.category

    def test_parsed_topic_immutable(self) -> None:
        """Test that ModelParsedTopic is immutable."""
        parser = ModelTopicParser()
        result = parser.parse("onex.user.events")

        # Attempting to modify should raise
        with pytest.raises(Exception):  # ValidationError
            result.domain = "modified"  # type: ignore[misc]


# ============================================================================
# EnumTopicStandard Tests
# ============================================================================


@pytest.mark.unit
class TestEnumTopicStandard:
    """Tests for EnumTopicStandard enum."""

    def test_enum_values(self) -> None:
        """Test EnumTopicStandard enum values."""
        assert EnumTopicStandard.ONEX_KAFKA.value == "onex_kafka"
        assert EnumTopicStandard.ENVIRONMENT_AWARE.value == "environment_aware"
        assert EnumTopicStandard.UNKNOWN.value == "unknown"

    def test_enum_str(self) -> None:
        """Test EnumTopicStandard __str__ method."""
        assert str(EnumTopicStandard.ONEX_KAFKA) == "onex_kafka"
        assert str(EnumTopicStandard.ENVIRONMENT_AWARE) == "environment_aware"
        assert str(EnumTopicStandard.UNKNOWN) == "unknown"
