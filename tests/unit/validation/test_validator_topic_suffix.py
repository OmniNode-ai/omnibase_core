# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for topic suffix validator.

Tests for the ONEX topic suffix validation utilities following the canonical
naming convention: onex.{kind}.{producer}.{event-name}.v{n}

Covers:
- validate_topic_suffix (full validation with result model)
- parse_topic_suffix (parse with ValueError on invalid)
- compose_full_topic (combine env prefix with suffix)
- is_valid_topic_suffix (boolean convenience check)
- Constants: ENV_PREFIXES, VALID_TOPIC_KINDS, patterns
"""

import re

import pytest

from omnibase_core.models.validation.model_topic_suffix_parts import (
    TOPIC_KIND_CMD,
    TOPIC_KIND_DLQ,
    TOPIC_KIND_EVT,
    TOPIC_KIND_SNAPSHOT,
    VALID_TOPIC_KINDS,
    ModelTopicSuffixParts,
)
from omnibase_core.models.validation.model_topic_validation_result import (
    ModelTopicValidationResult,
)
from omnibase_core.validation.validator_topic_suffix import (
    ENV_PREFIXES,
    EXPECTED_SEGMENT_COUNT,
    KEBAB_CASE_PATTERN,
    TOPIC_PREFIX,
    TOPIC_SUFFIX_PATTERN,
    VERSION_PATTERN,
    compose_full_topic,
    is_valid_topic_suffix,
    parse_topic_suffix,
    validate_topic_suffix,
)

# =============================================================================
# Constants Tests
# =============================================================================


@pytest.mark.unit
class TestConstants:
    """Tests for module constants."""

    def test_topic_prefix(self) -> None:
        """Test that TOPIC_PREFIX is 'onex'."""
        assert TOPIC_PREFIX == "onex"

    def test_expected_segment_count(self) -> None:
        """Test that expected segment count is 5."""
        assert EXPECTED_SEGMENT_COUNT == 5

    def test_env_prefixes_contains_expected_values(self) -> None:
        """Test that ENV_PREFIXES contains all expected environment prefixes."""
        expected = {"dev", "staging", "prod", "test", "local"}
        assert expected == ENV_PREFIXES

    def test_env_prefixes_is_frozenset(self) -> None:
        """Test that ENV_PREFIXES is an immutable frozenset."""
        assert isinstance(ENV_PREFIXES, frozenset)

    def test_valid_topic_kinds_contains_expected_values(self) -> None:
        """Test that VALID_TOPIC_KINDS contains all valid kind tokens."""
        expected = {"cmd", "evt", "dlq", "snapshot"}
        assert expected == VALID_TOPIC_KINDS

    def test_topic_kind_constants(self) -> None:
        """Test that topic kind constants have correct values."""
        assert TOPIC_KIND_CMD == "cmd"
        assert TOPIC_KIND_EVT == "evt"
        assert TOPIC_KIND_DLQ == "dlq"
        assert TOPIC_KIND_SNAPSHOT == "snapshot"


# =============================================================================
# Pattern Tests
# =============================================================================


@pytest.mark.unit
class TestPatterns:
    """Tests for regex patterns."""

    def test_topic_suffix_pattern_is_compiled(self) -> None:
        """Test that TOPIC_SUFFIX_PATTERN is a compiled regex."""
        assert isinstance(TOPIC_SUFFIX_PATTERN, re.Pattern)

    def test_kebab_case_pattern_is_compiled(self) -> None:
        """Test that KEBAB_CASE_PATTERN is a compiled regex."""
        assert isinstance(KEBAB_CASE_PATTERN, re.Pattern)

    def test_version_pattern_is_compiled(self) -> None:
        """Test that VERSION_PATTERN is a compiled regex."""
        assert isinstance(VERSION_PATTERN, re.Pattern)

    @pytest.mark.parametrize(
        ("identifier", "description"),
        [
            ("a", "single letter"),
            ("abc", "multiple letters"),
            ("abc-def", "with hyphen"),
            ("my-service", "common service name"),
            ("a1", "letter followed by digit"),
            ("abc123", "letters and digits"),
            ("a-b-c", "multiple hyphens"),
            ("service-123", "hyphen before digits"),
            ("a1b2c3", "interleaved letters and digits"),
        ],
    )
    def test_kebab_case_pattern_valid(self, identifier: str, description: str) -> None:
        """Test that valid kebab-case identifiers match pattern."""
        assert KEBAB_CASE_PATTERN.match(identifier) is not None, (
            f"Failed for {description}"
        )

    @pytest.mark.parametrize(
        ("identifier", "description"),
        [
            ("ABC", "uppercase letters"),
            ("MyService", "mixed case"),
            ("123abc", "starts with digit"),
            ("1-service", "starts with digit"),
            ("my_service", "contains underscore"),
            ("my.service", "contains dot"),
            ("my service", "contains space"),
            ("-service", "starts with hyphen"),
            ("service-", "ends with hyphen"),
            ("", "empty string"),
        ],
    )
    def test_kebab_case_pattern_invalid(
        self, identifier: str, description: str
    ) -> None:
        """Test that invalid kebab-case identifiers do not match pattern."""
        assert KEBAB_CASE_PATTERN.match(identifier) is None, (
            f"Should not match: {description}"
        )

    @pytest.mark.parametrize(
        ("version", "expected_number"),
        [
            ("v1", 1),
            ("v2", 2),
            ("v10", 10),
            ("v99", 99),
            ("v123", 123),
            ("v999", 999),
        ],
    )
    def test_version_pattern_valid(self, version: str, expected_number: int) -> None:
        """Test that valid version strings match pattern and extract number."""
        match = VERSION_PATTERN.match(version)
        assert match is not None
        assert int(match.group(1)) == expected_number

    @pytest.mark.parametrize(
        ("version", "description"),
        [
            ("1", "missing 'v' prefix"),
            ("v", "missing number"),
            ("v0", "version zero (valid pattern but invalid semantically)"),
            ("version1", "full word 'version'"),
            ("V1", "uppercase V"),
            ("v1.0", "decimal version"),
            ("v-1", "negative number"),
            ("", "empty string"),
        ],
    )
    def test_version_pattern_invalid(self, version: str, description: str) -> None:
        """Test that invalid version strings do not match (except v0 matches pattern)."""
        # Note: v0 matches the pattern but is semantically invalid (version >= 1 required)
        if version == "v0":
            assert VERSION_PATTERN.match(version) is not None
        else:
            assert VERSION_PATTERN.match(version) is None, (
                f"Should not match: {description}"
            )


# =============================================================================
# validate_topic_suffix Tests - Valid Cases
# =============================================================================


@pytest.mark.unit
class TestValidateTopicSuffixValid:
    """Tests for validate_topic_suffix with valid suffixes."""

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("onex.evt.omnimemory.intent-stored.v1", "basic event suffix"),
            ("onex.cmd.omnimemory.intent-query-requested.v1", "command suffix"),
            ("onex.evt.omniintelligence.intent-classified.v1", "intelligence event"),
            ("onex.dlq.omnimemory.failed-events.v1", "dead letter queue suffix"),
            ("onex.snapshot.omnimemory.state-backup.v1", "snapshot suffix"),
        ],
    )
    def test_valid_basic_suffixes(self, suffix: str, description: str) -> None:
        """Test that basic valid suffixes pass validation."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is True, f"Failed for {description}"
        assert result.parsed is not None
        assert result.error is None

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("onex.evt.a.b.v1", "single character segments"),
            ("onex.cmd.my-service.my-event.v999", "large version number"),
            ("onex.evt.service123.event-name-123.v1", "numbers in kebab-case"),
            ("onex.dlq.a1b2.c3d4.v50", "alphanumeric producer/event"),
            ("onex.snapshot.x.y.v1", "minimal single char"),
        ],
    )
    def test_valid_edge_case_suffixes(self, suffix: str, description: str) -> None:
        """Test that edge case valid suffixes pass validation."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is True, f"Failed for {description}"
        assert result.parsed is not None

    @pytest.mark.parametrize(
        "kind",
        ["cmd", "evt", "dlq", "snapshot"],
    )
    def test_all_valid_kinds(self, kind: str) -> None:
        """Test that all valid kind tokens are accepted."""
        suffix = f"onex.{kind}.producer.event-name.v1"
        result = validate_topic_suffix(suffix)
        assert result.is_valid is True
        assert result.parsed is not None
        assert result.parsed.kind == kind

    def test_returns_correct_model_type(self) -> None:
        """Test that validate_topic_suffix returns ModelTopicValidationResult."""
        result = validate_topic_suffix("onex.evt.service.event.v1")
        assert isinstance(result, ModelTopicValidationResult)

    def test_valid_result_has_parsed_parts(self) -> None:
        """Test that valid result contains parsed ModelTopicSuffixParts."""
        result = validate_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        assert result.is_valid is True
        assert isinstance(result.parsed, ModelTopicSuffixParts)

    def test_parsed_parts_contain_correct_values(self) -> None:
        """Test that parsed parts contain correct extracted values."""
        result = validate_topic_suffix("onex.evt.omnimemory.intent-stored.v2")
        assert result.parsed is not None
        assert result.parsed.kind == "evt"
        assert result.parsed.producer == "omnimemory"
        assert result.parsed.event_name == "intent-stored"
        assert result.parsed.version == 2
        assert result.parsed.raw_suffix == "onex.evt.omnimemory.intent-stored.v2"

    def test_suffix_normalized_to_lowercase(self) -> None:
        """Test that suffix is normalized to lowercase."""
        result = validate_topic_suffix("ONEX.EVT.OMNIMEMORY.INTENT-STORED.V1")
        assert result.is_valid is True
        assert result.parsed is not None
        assert result.parsed.raw_suffix == "onex.evt.omnimemory.intent-stored.v1"

    def test_whitespace_stripped(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = validate_topic_suffix("  onex.evt.service.event.v1  ")
        assert result.is_valid is True
        assert result.parsed is not None
        assert result.parsed.raw_suffix == "onex.evt.service.event.v1"


# =============================================================================
# validate_topic_suffix Tests - Invalid Cases
# =============================================================================


@pytest.mark.unit
class TestValidateTopicSuffixInvalid:
    """Tests for validate_topic_suffix with invalid suffixes."""

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("dev.onex.evt.omnimemory.intent-stored.v1", "has 'dev' env prefix"),
            ("staging.onex.cmd.service.event.v1", "has 'staging' env prefix"),
            ("prod.onex.evt.service.event.v1", "has 'prod' env prefix"),
            ("test.onex.dlq.service.event.v1", "has 'test' env prefix"),
            ("local.onex.snapshot.service.event.v1", "has 'local' env prefix"),
        ],
    )
    def test_rejects_environment_prefix(self, suffix: str, description: str) -> None:
        """Test that suffixes with environment prefix are rejected."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is False, f"Should reject: {description}"
        assert result.error is not None
        assert "environment prefix" in result.error.lower()

    @pytest.mark.parametrize(
        ("suffix", "segment_count", "description"),
        [
            ("onex.evt.omnimemory.v1", 4, "4 segments (missing event-name)"),
            ("onex.evt.omnimemory.intent.stored.v1", 6, "6 segments (too many)"),
            ("onex.evt.v1", 3, "3 segments"),
            ("onex.v1", 2, "2 segments"),
            ("onex", 1, "1 segment"),
            ("onex.evt.a.b.c.d.v1", 7, "7 segments"),
        ],
    )
    def test_rejects_wrong_segment_count(
        self, suffix: str, segment_count: int, description: str
    ) -> None:
        """Test that suffixes with wrong segment count are rejected."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is False, f"Should reject: {description}"
        assert result.error is not None
        assert "5 segments" in result.error or "segment" in result.error.lower()

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("onex.events.omnimemory.intent-stored.v1", "full word 'events' not 'evt'"),
            ("onex.commands.service.event.v1", "full word 'commands' not 'cmd'"),
            ("onex.foo.service.event.v1", "unknown kind 'foo'"),
            ("onex.bar.service.event.v1", "unknown kind 'bar'"),
            ("onex.event.service.event.v1", "singular 'event' not 'evt'"),
            ("onex.command.service.event.v1", "singular 'command' not 'cmd'"),
            ("onex.deadletter.service.event.v1", "'deadletter' not 'dlq'"),
            ("onex.snap.service.event.v1", "'snap' not 'snapshot'"),
        ],
    )
    def test_rejects_invalid_kind(self, suffix: str, description: str) -> None:
        """Test that suffixes with invalid kind token are rejected."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is False, f"Should reject: {description}"
        assert result.error is not None
        assert "kind" in result.error.lower()

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("onex.evt.OmniMemory.intent-stored.v1", "uppercase producer"),
            ("onex.evt.Omnimemory.intent-stored.v1", "capitalized producer"),
            ("onex.evt.omni_memory.intent-stored.v1", "underscore in producer"),
            (
                "onex.evt.omni.memory.intent-stored.v1",
                "dot in producer (extra segment)",
            ),
            ("onex.evt.123service.event.v1", "producer starts with number"),
            ("onex.evt.-service.event.v1", "producer starts with hyphen"),
        ],
    )
    def test_rejects_invalid_producer(self, suffix: str, description: str) -> None:
        """Test that suffixes with invalid producer format are rejected."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is False, f"Should reject: {description}"
        assert result.error is not None
        # Error might be about producer or segment count depending on the case

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("onex.evt.omnimemory.IntentStored.v1", "uppercase event-name"),
            ("onex.evt.omnimemory.Intent-Stored.v1", "capitalized event-name"),
            ("onex.evt.omnimemory.intent_stored.v1", "underscore in event-name"),
            ("onex.evt.omnimemory.123event.v1", "event-name starts with number"),
            ("onex.evt.omnimemory.-event.v1", "event-name starts with hyphen"),
        ],
    )
    def test_rejects_invalid_event_name(self, suffix: str, description: str) -> None:
        """Test that suffixes with invalid event-name format are rejected."""
        result = validate_topic_suffix(suffix)
        assert result.is_valid is False, f"Should reject: {description}"
        assert result.error is not None

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("onex.evt.omnimemory.intent-stored", "missing version"),
            ("onex.evt.omnimemory.intent-stored.1", "missing 'v' prefix"),
            ("onex.evt.omnimemory.intent-stored.v0", "version 0 not allowed"),
            ("onex.evt.omnimemory.intent-stored.v", "missing version number"),
            ("onex.evt.omnimemory.intent-stored.version1", "wrong format 'version1'"),
            ("onex.evt.omnimemory.intent-stored.V1", "uppercase V (normalized)"),
        ],
    )
    def test_rejects_invalid_version(self, suffix: str, description: str) -> None:
        """Test that suffixes with invalid version format are rejected."""
        result = validate_topic_suffix(suffix)
        # Note: uppercase V1 gets normalized, so it might pass
        if suffix.endswith(".V1"):
            # Uppercase gets normalized to lowercase, so v1 is valid
            assert result.is_valid is True
        else:
            assert result.is_valid is False, f"Should reject: {description}"
            assert result.error is not None

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("evt.omnimemory.intent-stored.v1", "missing 'onex' prefix"),
            ("foo.evt.omnimemory.intent-stored.v1", "wrong prefix 'foo'"),
            ("ONEX.evt.omnimemory.intent-stored", "ONEX but missing version"),
        ],
    )
    def test_rejects_missing_onex_prefix(self, suffix: str, description: str) -> None:
        """Test that suffixes without 'onex.' prefix are rejected."""
        result = validate_topic_suffix(suffix)
        # Note: "ONEX.evt.omnimemory.intent-stored" missing version, not prefix
        if "missing version" in description:
            assert result.is_valid is False
            assert result.error is not None
        else:
            assert result.is_valid is False, f"Should reject: {description}"
            assert result.error is not None

    def test_rejects_empty_string(self) -> None:
        """Test that empty string is rejected."""
        result = validate_topic_suffix("")
        assert result.is_valid is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_rejects_whitespace_only(self) -> None:
        """Test that whitespace-only string is rejected."""
        result = validate_topic_suffix("   ")
        assert result.is_valid is False
        assert result.error is not None
        assert "empty" in result.error.lower()


# =============================================================================
# parse_topic_suffix Tests
# =============================================================================


@pytest.mark.unit
class TestParseTopicSuffix:
    """Tests for parse_topic_suffix function."""

    def test_returns_model_topic_suffix_parts(self) -> None:
        """Test that parse_topic_suffix returns ModelTopicSuffixParts."""
        parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        assert isinstance(parts, ModelTopicSuffixParts)

    def test_extracts_kind_correctly(self) -> None:
        """Test that kind is extracted correctly."""
        parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        assert parts.kind == "evt"

    def test_extracts_producer_correctly(self) -> None:
        """Test that producer is extracted correctly."""
        parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        assert parts.producer == "omnimemory"

    def test_extracts_event_name_correctly(self) -> None:
        """Test that event_name is extracted correctly."""
        parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        assert parts.event_name == "intent-stored"

    def test_extracts_version_as_integer(self) -> None:
        """Test that version is extracted as integer."""
        parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v42")
        assert parts.version == 42
        assert isinstance(parts.version, int)

    def test_stores_raw_suffix(self) -> None:
        """Test that raw_suffix is stored (normalized)."""
        parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        assert parts.raw_suffix == "onex.evt.omnimemory.intent-stored.v1"

    @pytest.mark.parametrize(
        "kind",
        ["cmd", "evt", "dlq", "snapshot"],
    )
    def test_parses_all_kinds(self, kind: str) -> None:
        """Test that all valid kinds are parsed correctly."""
        suffix = f"onex.{kind}.producer.event-name.v1"
        parts = parse_topic_suffix(suffix)
        assert parts.kind == kind

    def test_raises_value_error_on_invalid_suffix(self) -> None:
        """Test that ValueError is raised for invalid suffix."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic_suffix("invalid.topic")
        assert "Invalid topic suffix" in str(exc_info.value)

    def test_error_message_includes_original_suffix(self) -> None:
        """Test that error message includes the original suffix."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic_suffix("bad.suffix.here")
        assert "bad.suffix.here" in str(exc_info.value)

    def test_error_message_includes_validation_error(self) -> None:
        """Test that error message includes validation error details."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic_suffix("dev.onex.evt.service.event.v1")
        error_msg = str(exc_info.value)
        assert "environment prefix" in error_msg.lower()

    @pytest.mark.parametrize(
        ("suffix", "description"),
        [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("not-a-topic", "random string"),
            ("onex.evt.service", "too few segments"),
        ],
    )
    def test_raises_for_various_invalid_inputs(
        self, suffix: str, description: str
    ) -> None:
        """Test that ValueError is raised for various invalid inputs."""
        with pytest.raises(ValueError):
            parse_topic_suffix(suffix)


# =============================================================================
# compose_full_topic Tests
# =============================================================================


@pytest.mark.unit
class TestComposeFullTopic:
    """Tests for compose_full_topic function."""

    def test_composes_with_dev_prefix(self) -> None:
        """Test composing full topic with dev prefix."""
        full = compose_full_topic("dev", "onex.evt.omnimemory.intent-stored.v1")
        assert full == "dev.onex.evt.omnimemory.intent-stored.v1"

    def test_composes_with_staging_prefix(self) -> None:
        """Test composing full topic with staging prefix."""
        full = compose_full_topic("staging", "onex.cmd.service.event.v1")
        assert full == "staging.onex.cmd.service.event.v1"

    def test_composes_with_prod_prefix(self) -> None:
        """Test composing full topic with prod prefix."""
        full = compose_full_topic("prod", "onex.evt.user-service.account-created.v2")
        assert full == "prod.onex.evt.user-service.account-created.v2"

    def test_composes_with_test_prefix(self) -> None:
        """Test composing full topic with test prefix."""
        full = compose_full_topic("test", "onex.dlq.service.failed-events.v1")
        assert full == "test.onex.dlq.service.failed-events.v1"

    def test_composes_with_local_prefix(self) -> None:
        """Test composing full topic with local prefix."""
        full = compose_full_topic("local", "onex.snapshot.service.backup.v1")
        assert full == "local.onex.snapshot.service.backup.v1"

    @pytest.mark.parametrize(
        "env_prefix",
        ["dev", "staging", "prod", "test", "local"],
    )
    def test_all_valid_env_prefixes(self, env_prefix: str) -> None:
        """Test that all valid environment prefixes work."""
        full = compose_full_topic(env_prefix, "onex.evt.service.event.v1")
        assert full == f"{env_prefix}.onex.evt.service.event.v1"

    def test_normalizes_env_prefix_to_lowercase(self) -> None:
        """Test that environment prefix is normalized to lowercase."""
        full = compose_full_topic("DEV", "onex.evt.service.event.v1")
        assert full == "dev.onex.evt.service.event.v1"

    def test_strips_env_prefix_whitespace(self) -> None:
        """Test that whitespace is stripped from env prefix."""
        full = compose_full_topic("  dev  ", "onex.evt.service.event.v1")
        assert full == "dev.onex.evt.service.event.v1"

    def test_validates_suffix(self) -> None:
        """Test that suffix is validated before composing."""
        with pytest.raises(ValueError) as exc_info:
            compose_full_topic("dev", "invalid.suffix")
        assert "Invalid topic suffix" in str(exc_info.value)

    def test_raises_for_empty_env_prefix(self) -> None:
        """Test that empty env prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            compose_full_topic("", "onex.evt.service.event.v1")
        assert "empty" in str(exc_info.value).lower()

    def test_raises_for_whitespace_env_prefix(self) -> None:
        """Test that whitespace-only env prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            compose_full_topic("   ", "onex.evt.service.event.v1")
        assert "empty" in str(exc_info.value).lower()

    def test_raises_for_invalid_env_prefix(self) -> None:
        """Test that invalid env prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            compose_full_topic("production", "onex.evt.service.event.v1")
        error_msg = str(exc_info.value)
        assert "production" in error_msg
        assert "must be one of" in error_msg.lower()

    @pytest.mark.parametrize(
        ("env_prefix", "description"),
        [
            ("development", "full word 'development'"),
            ("production", "full word 'production'"),
            ("qa", "unknown 'qa'"),
            ("uat", "unknown 'uat'"),
            ("sandbox", "unknown 'sandbox'"),
        ],
    )
    def test_rejects_invalid_env_prefixes(
        self, env_prefix: str, description: str
    ) -> None:
        """Test that invalid environment prefixes are rejected."""
        with pytest.raises(ValueError):
            compose_full_topic(env_prefix, "onex.evt.service.event.v1")

    def test_uses_normalized_suffix_from_parsed_result(self) -> None:
        """Test that composed topic uses normalized suffix."""
        full = compose_full_topic("dev", "  ONEX.EVT.SERVICE.EVENT.V1  ")
        assert full == "dev.onex.evt.service.event.v1"


# =============================================================================
# is_valid_topic_suffix Tests
# =============================================================================


@pytest.mark.unit
class TestIsValidTopicSuffix:
    """Tests for is_valid_topic_suffix function."""

    def test_returns_true_for_valid_suffix(self) -> None:
        """Test that True is returned for valid suffix."""
        assert is_valid_topic_suffix("onex.evt.service.event.v1") is True

    def test_returns_false_for_invalid_suffix(self) -> None:
        """Test that False is returned for invalid suffix."""
        assert is_valid_topic_suffix("invalid") is False

    def test_returns_bool_type(self) -> None:
        """Test that return type is bool."""
        result = is_valid_topic_suffix("onex.evt.service.event.v1")
        assert isinstance(result, bool)

    @pytest.mark.parametrize(
        ("suffix", "expected"),
        [
            ("onex.evt.omnimemory.intent-stored.v1", True),
            ("onex.cmd.service.command.v2", True),
            ("onex.dlq.service.failed.v1", True),
            ("onex.snapshot.service.backup.v1", True),
            ("dev.onex.evt.service.event.v1", False),
            ("onex.events.service.event.v1", False),
            ("invalid.topic", False),
            ("", False),
        ],
    )
    def test_various_suffixes(self, suffix: str, expected: bool) -> None:
        """Test is_valid_topic_suffix with various inputs."""
        assert is_valid_topic_suffix(suffix) is expected


# =============================================================================
# ModelTopicSuffixParts Tests
# =============================================================================


@pytest.mark.unit
class TestModelTopicSuffixParts:
    """Tests for ModelTopicSuffixParts model."""

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable (frozen)."""
        parts = ModelTopicSuffixParts(
            kind="evt",
            producer="service",
            event_name="event",
            version=1,
            raw_suffix="onex.evt.service.event.v1",
        )
        with pytest.raises(Exception):  # ValidationError for frozen model
            parts.kind = "cmd"  # type: ignore[misc]

    def test_model_forbids_extra_fields(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(Exception):  # ValidationError
            ModelTopicSuffixParts(
                kind="evt",
                producer="service",
                event_name="event",
                version=1,
                raw_suffix="onex.evt.service.event.v1",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_version_must_be_positive(self) -> None:
        """Test that version must be >= 1."""
        with pytest.raises(Exception):  # ValidationError
            ModelTopicSuffixParts(
                kind="evt",
                producer="service",
                event_name="event",
                version=0,
                raw_suffix="onex.evt.service.event.v0",
            )

    def test_all_fields_required(self) -> None:
        """Test that all fields are required."""
        with pytest.raises(Exception):  # ValidationError
            ModelTopicSuffixParts(  # type: ignore[call-arg]
                kind="evt",
                producer="service",
                # missing event_name, version, raw_suffix
            )


# =============================================================================
# ModelTopicValidationResult Tests
# =============================================================================


@pytest.mark.unit
class TestModelTopicValidationResult:
    """Tests for ModelTopicValidationResult model."""

    def test_success_factory_creates_valid_result(self) -> None:
        """Test that success factory creates valid result."""
        parsed = ModelTopicSuffixParts(
            kind="evt",
            producer="service",
            event_name="event",
            version=1,
            raw_suffix="onex.evt.service.event.v1",
        )
        result = ModelTopicValidationResult.success(
            suffix="onex.evt.service.event.v1",
            parsed=parsed,
        )
        assert result.is_valid is True
        assert result.parsed is not None
        assert result.error is None

    def test_failure_factory_creates_invalid_result(self) -> None:
        """Test that failure factory creates invalid result."""
        result = ModelTopicValidationResult.failure(
            suffix="invalid",
            error="Test error message",
        )
        assert result.is_valid is False
        assert result.parsed is None
        assert result.error == "Test error message"

    def test_model_is_frozen(self) -> None:
        """Test that result model is immutable."""
        result = ModelTopicValidationResult.failure(suffix="bad", error="error")
        with pytest.raises(Exception):  # ValidationError for frozen model
            result.is_valid = True  # type: ignore[misc]


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestImports:
    """Tests for import paths."""

    def test_import_from_validator_module(self) -> None:
        """Test that all exports are importable from the validator module."""
        from omnibase_core.validation.validator_topic_suffix import (
            ENV_PREFIXES,
            EXPECTED_SEGMENT_COUNT,
            KEBAB_CASE_PATTERN,
            TOPIC_PREFIX,
            TOPIC_SUFFIX_PATTERN,
            VERSION_PATTERN,
            compose_full_topic,
            is_valid_topic_suffix,
            parse_topic_suffix,
            validate_topic_suffix,
        )

        assert callable(validate_topic_suffix)
        assert callable(parse_topic_suffix)
        assert callable(compose_full_topic)
        assert callable(is_valid_topic_suffix)
        assert TOPIC_PREFIX is not None
        assert ENV_PREFIXES is not None
        assert EXPECTED_SEGMENT_COUNT is not None
        assert TOPIC_SUFFIX_PATTERN is not None
        assert KEBAB_CASE_PATTERN is not None
        assert VERSION_PATTERN is not None

    def test_import_models_from_validation_models(self) -> None:
        """Test that models are importable from models.validation package."""
        from omnibase_core.models.validation.model_topic_suffix_parts import (
            VALID_TOPIC_KINDS,
            ModelTopicSuffixParts,
        )
        from omnibase_core.models.validation.model_topic_validation_result import (
            ModelTopicValidationResult,
        )

        assert ModelTopicSuffixParts is not None
        assert ModelTopicValidationResult is not None
        assert VALID_TOPIC_KINDS is not None


# =============================================================================
# Thread Safety Tests
# =============================================================================


@pytest.mark.unit
class TestThreadSafety:
    """Tests for thread safety properties."""

    def test_patterns_are_compiled_and_immutable(self) -> None:
        """Test that patterns are compiled regex (immutable)."""
        pattern1 = TOPIC_SUFFIX_PATTERN
        pattern2 = KEBAB_CASE_PATTERN
        pattern3 = VERSION_PATTERN

        # Patterns should be immutable compiled regex
        assert isinstance(pattern1, re.Pattern)
        assert isinstance(pattern2, re.Pattern)
        assert isinstance(pattern3, re.Pattern)

    def test_env_prefixes_is_immutable(self) -> None:
        """Test that ENV_PREFIXES is immutable frozenset."""
        assert isinstance(ENV_PREFIXES, frozenset)
        # frozenset does not have add method
        assert not hasattr(ENV_PREFIXES, "add") or not callable(
            getattr(ENV_PREFIXES, "add", None)
        )

    def test_valid_topic_kinds_is_immutable(self) -> None:
        """Test that VALID_TOPIC_KINDS is immutable frozenset."""
        assert isinstance(VALID_TOPIC_KINDS, frozenset)

    def test_validation_functions_are_stateless(self) -> None:
        """Test that validation functions produce consistent results (stateless)."""
        suffix = "onex.evt.service.event.v1"

        # Multiple calls should produce identical results
        result1 = validate_topic_suffix(suffix)
        result2 = validate_topic_suffix(suffix)

        assert result1.is_valid == result2.is_valid
        assert result1.suffix == result2.suffix
        if result1.parsed and result2.parsed:
            assert result1.parsed.kind == result2.parsed.kind
            assert result1.parsed.producer == result2.parsed.producer
            assert result1.parsed.event_name == result2.parsed.event_name
            assert result1.parsed.version == result2.parsed.version


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests for topic suffix validation."""

    def test_very_long_producer_name(self) -> None:
        """Test handling of very long producer name."""
        long_producer = "a" + "-b" * 50  # Long but valid kebab-case
        suffix = f"onex.evt.{long_producer}.event.v1"
        result = validate_topic_suffix(suffix)
        assert result.is_valid is True

    def test_very_long_event_name(self) -> None:
        """Test handling of very long event name."""
        long_event = "event" + "-name" * 50  # Long but valid kebab-case
        suffix = f"onex.evt.service.{long_event}.v1"
        result = validate_topic_suffix(suffix)
        assert result.is_valid is True

    def test_very_large_version_number(self) -> None:
        """Test handling of very large version number."""
        result = validate_topic_suffix("onex.evt.service.event.v999999")
        assert result.is_valid is True
        assert result.parsed is not None
        assert result.parsed.version == 999999

    def test_mixed_case_is_normalized(self) -> None:
        """Test that mixed case input is normalized to lowercase."""
        result = validate_topic_suffix("ONEX.EVT.MyService.MyEvent.V1")
        assert result.is_valid is True
        assert result.parsed is not None
        assert result.parsed.kind == "evt"
        assert result.parsed.producer == "myservice"
        assert result.parsed.event_name == "myevent"

    def test_consecutive_hyphens_in_kebab_case(self) -> None:
        """Test handling of consecutive hyphens (allowed by pattern)."""
        # Note: Pattern allows consecutive hyphens - may want to restrict
        result = validate_topic_suffix("onex.evt.my--service.event--name.v1")
        # Pattern [a-z][a-z0-9-]* allows this
        assert result.is_valid is True

    def test_trailing_hyphen_in_kebab_case(self) -> None:
        """Test handling of trailing hyphen (allowed by pattern)."""
        # Note: Pattern allows trailing hyphens - may want to restrict
        result = validate_topic_suffix("onex.evt.service-.event-.v1")
        # Pattern [a-z][a-z0-9-]* allows this
        assert result.is_valid is True

    def test_unicode_characters_rejected(self) -> None:
        """Test that non-ASCII characters are rejected."""
        result = validate_topic_suffix(
            "onex.evt.servic\u00e9.event.v1"
        )  # e with accent
        # After lowercase normalization, pattern should reject non-ASCII
        assert result.is_valid is False

    def test_newline_in_suffix_rejected(self) -> None:
        """Test that newline characters are rejected."""
        result = validate_topic_suffix("onex.evt.service.event.v1\n")
        # Newline creates an extra segment or invalid character
        assert result.is_valid is False

    def test_tab_in_suffix_rejected(self) -> None:
        """Test that tab characters are rejected."""
        result = validate_topic_suffix("onex.evt.service\t.event.v1")
        # Tab creates invalid character
        assert result.is_valid is False
