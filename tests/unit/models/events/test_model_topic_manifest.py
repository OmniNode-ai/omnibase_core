# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ONEX Topic Manifest models.

Tests cover:
- EnumTopicType values and behavior
- EnumCleanupPolicy values and behavior
- ModelTopicConfig factory methods and validation
- ModelTopicManifest domain operations and topic name generation
- Domain name validation patterns
- Edge cases and error conditions
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.events import (
    EnumCleanupPolicy,
    EnumTopicType,
    ModelTopicConfig,
    ModelTopicManifest,
)


@pytest.mark.unit
class TestEnumTopicType:
    """Test cases for EnumTopicType enum."""

    def test_values_exist(self):
        """Test that all expected topic type values are defined."""
        assert hasattr(EnumTopicType, "COMMANDS")
        assert hasattr(EnumTopicType, "DLQ")
        assert hasattr(EnumTopicType, "EVENTS")
        assert hasattr(EnumTopicType, "INTENTS")
        assert hasattr(EnumTopicType, "SNAPSHOTS")

    def test_values_are_correct(self):
        """Test that topic type values match expected strings."""
        assert EnumTopicType.COMMANDS.value == "commands"
        assert EnumTopicType.DLQ.value == "dlq"
        assert EnumTopicType.EVENTS.value == "events"
        assert EnumTopicType.INTENTS.value == "intents"
        assert EnumTopicType.SNAPSHOTS.value == "snapshots"

    def test_str_conversion(self):
        """Test that __str__ returns the value."""
        assert str(EnumTopicType.COMMANDS) == "commands"
        assert str(EnumTopicType.DLQ) == "dlq"
        assert str(EnumTopicType.EVENTS) == "events"
        assert str(EnumTopicType.INTENTS) == "intents"
        assert str(EnumTopicType.SNAPSHOTS) == "snapshots"

    def test_inherits_from_str(self):
        """Test that EnumTopicType inherits from str for serialization."""
        assert isinstance(EnumTopicType.COMMANDS, str)
        assert isinstance(EnumTopicType.EVENTS, str)

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [e.value for e in EnumTopicType]
        assert len(values) == len(set(values))
        assert len(values) == 5

    def test_iteration(self):
        """Test that enum can be iterated."""
        topic_types = list(EnumTopicType)
        assert len(topic_types) == 5
        assert EnumTopicType.COMMANDS in topic_types
        assert EnumTopicType.DLQ in topic_types
        assert EnumTopicType.EVENTS in topic_types
        assert EnumTopicType.INTENTS in topic_types
        assert EnumTopicType.SNAPSHOTS in topic_types

    def test_comparison_with_string(self):
        """Test that enum can be compared to strings."""
        assert EnumTopicType.COMMANDS == "commands"
        assert EnumTopicType.EVENTS == "events"

    def test_hashable(self):
        """Test that enum values are hashable (usable as dict keys)."""
        mapping = {
            EnumTopicType.COMMANDS: "cmd_handler",
            EnumTopicType.EVENTS: "evt_handler",
        }
        assert mapping[EnumTopicType.COMMANDS] == "cmd_handler"


@pytest.mark.unit
class TestEnumCleanupPolicy:
    """Test cases for EnumCleanupPolicy enum."""

    def test_values_exist(self):
        """Test that all expected cleanup policy values are defined."""
        assert hasattr(EnumCleanupPolicy, "DELETE")
        assert hasattr(EnumCleanupPolicy, "COMPACT")
        assert hasattr(EnumCleanupPolicy, "COMPACT_DELETE")

    def test_values_are_correct(self):
        """Test that cleanup policy values match expected Kafka config strings."""
        assert EnumCleanupPolicy.DELETE.value == "delete"
        assert EnumCleanupPolicy.COMPACT.value == "compact"
        assert EnumCleanupPolicy.COMPACT_DELETE.value == "compact,delete"

    def test_str_conversion(self):
        """Test that __str__ returns the value for Kafka configuration."""
        assert str(EnumCleanupPolicy.DELETE) == "delete"
        assert str(EnumCleanupPolicy.COMPACT) == "compact"
        assert str(EnumCleanupPolicy.COMPACT_DELETE) == "compact,delete"

    def test_inherits_from_str(self):
        """Test that EnumCleanupPolicy inherits from str for serialization."""
        assert isinstance(EnumCleanupPolicy.DELETE, str)
        assert isinstance(EnumCleanupPolicy.COMPACT, str)

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [e.value for e in EnumCleanupPolicy]
        assert len(values) == len(set(values))
        assert len(values) == 3

    def test_iteration(self):
        """Test that enum can be iterated."""
        policies = list(EnumCleanupPolicy)
        assert len(policies) == 3
        assert EnumCleanupPolicy.DELETE in policies
        assert EnumCleanupPolicy.COMPACT in policies
        assert EnumCleanupPolicy.COMPACT_DELETE in policies


@pytest.mark.unit
class TestModelTopicConfigInstantiation:
    """Test cases for ModelTopicConfig instantiation."""

    def test_instantiation_minimal(self):
        """Test config creation with minimal required fields."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
        )

        assert config.topic_type == EnumTopicType.EVENTS
        assert config.cleanup_policy == EnumCleanupPolicy.DELETE
        assert config.retention_ms is None
        assert config.retention_bytes is None
        assert config.partitions == 3  # default
        assert config.replication_factor == 1  # default

    def test_instantiation_all_fields(self):
        """Test config creation with all fields specified."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.SNAPSHOTS,
            cleanup_policy=EnumCleanupPolicy.COMPACT_DELETE,
            retention_ms=86400000,
            retention_bytes=1073741824,  # 1 GB
            partitions=6,
            replication_factor=3,
        )

        assert config.topic_type == EnumTopicType.SNAPSHOTS
        assert config.cleanup_policy == EnumCleanupPolicy.COMPACT_DELETE
        assert config.retention_ms == 86400000
        assert config.retention_bytes == 1073741824
        assert config.partitions == 6
        assert config.replication_factor == 3

    def test_frozen_config(self):
        """Test that config is immutable (frozen)."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
        )

        with pytest.raises(ValidationError):
            config.partitions = 10  # type: ignore[misc]

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                extra_field="not_allowed",  # type: ignore[call-arg]
            )
        assert (
            "extra_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )


@pytest.mark.unit
class TestModelTopicConfigValidation:
    """Test cases for ModelTopicConfig field validation."""

    def test_retention_ms_valid_zero(self):
        """Test that retention_ms accepts zero (immediate deletion)."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.COMMANDS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=0,
        )
        assert config.retention_ms == 0

    def test_retention_ms_valid_positive(self):
        """Test that retention_ms accepts positive values."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=604800000,  # 7 days
        )
        assert config.retention_ms == 604800000

    def test_retention_ms_invalid_negative(self):
        """Test that retention_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                retention_ms=-1,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_retention_bytes_valid_none(self):
        """Test that retention_bytes accepts None (broker default)."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_bytes=None,
        )
        assert config.retention_bytes is None

    def test_retention_bytes_valid_unlimited(self):
        """Test that retention_bytes accepts -1 (unlimited)."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_bytes=-1,
        )
        assert config.retention_bytes == -1

    def test_retention_bytes_valid_positive(self):
        """Test that retention_bytes accepts positive values."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_bytes=1073741824,  # 1 GB
        )
        assert config.retention_bytes == 1073741824

    def test_retention_bytes_invalid_less_than_minus_one(self):
        """Test that retention_bytes rejects values less than -1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                retention_bytes=-2,
            )
        assert "greater than or equal to -1" in str(exc_info.value)

    def test_partitions_valid_minimum(self):
        """Test that partitions accepts minimum value of 1."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            partitions=1,
        )
        assert config.partitions == 1

    def test_partitions_valid_maximum(self):
        """Test that partitions accepts maximum value of 1000."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            partitions=1000,
        )
        assert config.partitions == 1000

    def test_partitions_invalid_zero(self):
        """Test that partitions rejects zero."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                partitions=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_partitions_invalid_exceeds_max(self):
        """Test that partitions rejects values over 1000."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                partitions=1001,
            )
        assert "less than or equal to 1000" in str(exc_info.value)

    def test_replication_factor_valid_minimum(self):
        """Test that replication_factor accepts minimum value of 1."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            replication_factor=1,
        )
        assert config.replication_factor == 1

    def test_replication_factor_valid_maximum(self):
        """Test that replication_factor accepts maximum value of 10."""
        config = ModelTopicConfig(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            replication_factor=10,
        )
        assert config.replication_factor == 10

    def test_replication_factor_invalid_zero(self):
        """Test that replication_factor rejects zero."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                replication_factor=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_replication_factor_invalid_exceeds_max(self):
        """Test that replication_factor rejects values over 10."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicConfig(
                topic_type=EnumTopicType.EVENTS,
                cleanup_policy=EnumCleanupPolicy.DELETE,
                replication_factor=11,
            )
        assert "less than or equal to 10" in str(exc_info.value)


@pytest.mark.unit
class TestModelTopicConfigFactoryMethods:
    """Test cases for ModelTopicConfig factory methods."""

    def test_commands_default(self):
        """Test commands_default() factory method."""
        config = ModelTopicConfig.commands_default()

        assert config.topic_type == EnumTopicType.COMMANDS
        assert config.cleanup_policy == EnumCleanupPolicy.DELETE
        assert config.retention_ms == 604800000  # 7 days per ONEX standard
        assert config.partitions == 3
        assert config.replication_factor == 1

    def test_events_default(self):
        """Test events_default() factory method."""
        config = ModelTopicConfig.events_default()

        assert config.topic_type == EnumTopicType.EVENTS
        assert config.cleanup_policy == EnumCleanupPolicy.DELETE
        assert config.retention_ms == 2592000000  # 30 days per ONEX standard
        assert config.partitions == 3
        assert config.replication_factor == 1

    def test_intents_default(self):
        """Test intents_default() factory method."""
        config = ModelTopicConfig.intents_default()

        assert config.topic_type == EnumTopicType.INTENTS
        assert config.cleanup_policy == EnumCleanupPolicy.DELETE
        assert config.retention_ms == 86400000  # 1 day per ONEX standard
        assert config.partitions == 3
        assert config.replication_factor == 1

    def test_snapshots_default(self):
        """Test snapshots_default() factory method."""
        config = ModelTopicConfig.snapshots_default()

        assert config.topic_type == EnumTopicType.SNAPSHOTS
        assert config.cleanup_policy == EnumCleanupPolicy.COMPACT_DELETE
        assert config.retention_ms == 604800000  # 7 days per ONEX standard
        assert config.partitions == 3
        assert config.replication_factor == 1

    def test_dlq_default(self):
        """Test dlq_default() factory method."""
        config = ModelTopicConfig.dlq_default()

        assert config.topic_type == EnumTopicType.DLQ
        assert config.cleanup_policy == EnumCleanupPolicy.DELETE
        assert config.retention_ms == 2592000000  # 30 days per ONEX standard
        assert config.partitions == 3
        assert config.replication_factor == 1

    def test_factory_methods_return_frozen_instances(self):
        """Test that factory methods return frozen (immutable) instances."""
        configs = [
            ModelTopicConfig.commands_default(),
            ModelTopicConfig.dlq_default(),
            ModelTopicConfig.events_default(),
            ModelTopicConfig.intents_default(),
            ModelTopicConfig.snapshots_default(),
        ]

        for config in configs:
            with pytest.raises(ValidationError):
                config.partitions = 10  # type: ignore[misc]

    def test_factory_retention_ordering(self):
        """Test that retention follows logical ordering: intents < commands/snapshots < events."""
        commands = ModelTopicConfig.commands_default()
        intents = ModelTopicConfig.intents_default()
        events = ModelTopicConfig.events_default()
        snapshots = ModelTopicConfig.snapshots_default()

        # Per ONEX standard:
        # Intents have shortest retention (1 day)
        # Commands and Snapshots have same retention (7 days)
        # Events have longest retention (30 days)
        assert intents.retention_ms is not None
        assert commands.retention_ms is not None
        assert snapshots.retention_ms is not None
        assert events.retention_ms is not None
        assert intents.retention_ms < commands.retention_ms < events.retention_ms
        assert commands.retention_ms == snapshots.retention_ms


@pytest.mark.unit
class TestModelTopicManifestInstantiation:
    """Test cases for ModelTopicManifest instantiation."""

    def test_instantiation_minimal(self):
        """Test manifest creation with minimal valid data."""
        config = ModelTopicConfig.events_default()
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: config},
        )

        assert manifest.domain == "test"
        assert len(manifest.topics) == 1
        assert EnumTopicType.EVENTS in manifest.topics

    def test_instantiation_all_topics(self):
        """Test manifest creation with all five topic types."""
        manifest = ModelTopicManifest(
            domain="myservice",
            topics={
                EnumTopicType.COMMANDS: ModelTopicConfig.commands_default(),
                EnumTopicType.DLQ: ModelTopicConfig.dlq_default(),
                EnumTopicType.EVENTS: ModelTopicConfig.events_default(),
                EnumTopicType.INTENTS: ModelTopicConfig.intents_default(),
                EnumTopicType.SNAPSHOTS: ModelTopicConfig.snapshots_default(),
            },
        )

        assert manifest.domain == "myservice"
        assert len(manifest.topics) == 5
        for topic_type in EnumTopicType:
            assert topic_type in manifest.topics

    def test_frozen_manifest(self):
        """Test that manifest is immutable (frozen)."""
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )

        with pytest.raises(ValidationError):
            manifest.domain = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            ModelTopicManifest(
                domain="test",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
                extra_field="not_allowed",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelTopicManifestDomainValidation:
    """Test cases for domain name validation in ModelTopicManifest."""

    def test_valid_single_letter_domain(self):
        """Test that single letter domain is valid."""
        manifest = ModelTopicManifest(
            domain="a",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )
        assert manifest.domain == "a"

    def test_valid_lowercase_domain(self):
        """Test that lowercase alphabetic domain is valid."""
        manifest = ModelTopicManifest(
            domain="registration",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )
        assert manifest.domain == "registration"

    def test_valid_alphanumeric_domain(self):
        """Test that alphanumeric domain is valid."""
        manifest = ModelTopicManifest(
            domain="service1",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )
        assert manifest.domain == "service1"

    def test_valid_hyphenated_domain(self):
        """Test that domain with hyphens is valid."""
        manifest = ModelTopicManifest(
            domain="my-service",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )
        assert manifest.domain == "my-service"

    def test_valid_complex_domain(self):
        """Test that complex domain with letters, numbers, and hyphens is valid."""
        manifest = ModelTopicManifest(
            domain="service-v2-prod",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )
        assert manifest.domain == "service-v2-prod"

    def test_invalid_empty_domain(self):
        """Test that empty domain is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        # Should fail either min_length or pattern validation
        assert (
            "String should have at least 1 character" in str(exc_info.value)
            or "string_pattern_mismatch" in str(exc_info.value).lower()
        )

    def test_invalid_uppercase_domain(self):
        """Test that uppercase domain is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="Registration",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_starts_with_number(self):
        """Test that domain starting with number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="1service",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_starts_with_hyphen(self):
        """Test that domain starting with hyphen is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="-service",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_ends_with_hyphen(self):
        """Test that domain ending with hyphen is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="service-",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_contains_underscore(self):
        """Test that domain with underscore is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="my_service",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_contains_dot(self):
        """Test that domain with dot is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="my.service",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_contains_space(self):
        """Test that domain with space is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain="my service",
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "string_pattern_mismatch" in str(exc_info.value).lower()

    def test_invalid_too_long_domain(self):
        """Test that domain exceeding max length is rejected."""
        long_domain = "a" * 65  # max_length is 64
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicManifest(
                domain=long_domain,
                topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
            )
        assert "64" in str(exc_info.value) or "String should have at most" in str(
            exc_info.value
        )

    def test_valid_max_length_domain(self):
        """Test that domain at max length is valid."""
        max_domain = "a" * 64
        manifest = ModelTopicManifest(
            domain=max_domain,
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )
        assert manifest.domain == max_domain


@pytest.mark.unit
class TestModelTopicManifestGetTopicName:
    """Test cases for ModelTopicManifest.get_topic_name() method."""

    def test_get_topic_name_events(self):
        """Test topic name generation for events."""
        manifest = ModelTopicManifest(
            domain="registration",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )

        assert (
            manifest.get_topic_name(EnumTopicType.EVENTS) == "onex.registration.events"
        )

    def test_get_topic_name_commands(self):
        """Test topic name generation for commands."""
        manifest = ModelTopicManifest(
            domain="discovery",
            topics={EnumTopicType.COMMANDS: ModelTopicConfig.commands_default()},
        )

        assert (
            manifest.get_topic_name(EnumTopicType.COMMANDS) == "onex.discovery.commands"
        )

    def test_get_topic_name_intents(self):
        """Test topic name generation for intents."""
        manifest = ModelTopicManifest(
            domain="runtime",
            topics={EnumTopicType.INTENTS: ModelTopicConfig.intents_default()},
        )

        assert manifest.get_topic_name(EnumTopicType.INTENTS) == "onex.runtime.intents"

    def test_get_topic_name_snapshots(self):
        """Test topic name generation for snapshots."""
        manifest = ModelTopicManifest(
            domain="metrics",
            topics={EnumTopicType.SNAPSHOTS: ModelTopicConfig.snapshots_default()},
        )

        assert (
            manifest.get_topic_name(EnumTopicType.SNAPSHOTS) == "onex.metrics.snapshots"
        )

    def test_get_topic_name_missing_type_raises_key_error(self):
        """Test that requesting missing topic type raises KeyError."""
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )

        with pytest.raises(KeyError) as exc_info:
            manifest.get_topic_name(EnumTopicType.COMMANDS)

        # Error message contains lowercase value 'commands' and domain 'test'
        assert "commands" in str(exc_info.value)
        assert "test" in str(exc_info.value)


@pytest.mark.unit
class TestModelTopicManifestGetAllTopicNames:
    """Test cases for ModelTopicManifest.get_all_topic_names() method."""

    def test_get_all_topic_names_single_topic(self):
        """Test getting all topic names with single topic."""
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )

        names = manifest.get_all_topic_names()

        assert len(names) == 1
        assert names[EnumTopicType.EVENTS] == "onex.test.events"

    def test_get_all_topic_names_all_topics(self):
        """Test getting all topic names with all five topics."""
        manifest = ModelTopicManifest(
            domain="registration",
            topics={
                EnumTopicType.COMMANDS: ModelTopicConfig.commands_default(),
                EnumTopicType.DLQ: ModelTopicConfig.dlq_default(),
                EnumTopicType.EVENTS: ModelTopicConfig.events_default(),
                EnumTopicType.INTENTS: ModelTopicConfig.intents_default(),
                EnumTopicType.SNAPSHOTS: ModelTopicConfig.snapshots_default(),
            },
        )

        names = manifest.get_all_topic_names()

        assert len(names) == 5
        assert names[EnumTopicType.COMMANDS] == "onex.registration.commands"
        assert names[EnumTopicType.DLQ] == "onex.registration.dlq"
        assert names[EnumTopicType.EVENTS] == "onex.registration.events"
        assert names[EnumTopicType.INTENTS] == "onex.registration.intents"
        assert names[EnumTopicType.SNAPSHOTS] == "onex.registration.snapshots"

    def test_get_all_topic_names_returns_new_dict(self):
        """Test that get_all_topic_names returns a new dictionary each call."""
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )

        names1 = manifest.get_all_topic_names()
        names2 = manifest.get_all_topic_names()

        assert names1 == names2
        assert names1 is not names2  # Different objects


@pytest.mark.unit
class TestModelTopicManifestGetConfig:
    """Test cases for ModelTopicManifest.get_config() method."""

    def test_get_config_exists(self):
        """Test getting config for existing topic type."""
        events_config = ModelTopicConfig.events_default()
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: events_config},
        )

        retrieved = manifest.get_config(EnumTopicType.EVENTS)
        assert retrieved == events_config

    def test_get_config_missing_raises_key_error(self):
        """Test that getting missing config raises KeyError."""
        manifest = ModelTopicManifest(
            domain="test",
            topics={EnumTopicType.EVENTS: ModelTopicConfig.events_default()},
        )

        with pytest.raises(KeyError) as exc_info:
            manifest.get_config(EnumTopicType.SNAPSHOTS)

        # Error message contains lowercase value 'snapshots' and domain 'test'
        assert "snapshots" in str(exc_info.value)
        assert "test" in str(exc_info.value)


@pytest.mark.unit
class TestModelTopicManifestRegistrationDomain:
    """Test cases for ModelTopicManifest.registration_domain() factory method."""

    def test_registration_domain_returns_manifest(self):
        """Test that registration_domain() returns a valid manifest."""
        manifest = ModelTopicManifest.registration_domain()

        assert isinstance(manifest, ModelTopicManifest)
        assert manifest.domain == "registration"

    def test_registration_domain_has_all_topics(self):
        """Test that registration domain has all five topic types."""
        manifest = ModelTopicManifest.registration_domain()

        assert len(manifest.topics) == 5
        assert EnumTopicType.COMMANDS in manifest.topics
        assert EnumTopicType.DLQ in manifest.topics
        assert EnumTopicType.EVENTS in manifest.topics
        assert EnumTopicType.INTENTS in manifest.topics
        assert EnumTopicType.SNAPSHOTS in manifest.topics

    def test_registration_domain_topic_names(self):
        """Test that registration domain generates correct topic names."""
        manifest = ModelTopicManifest.registration_domain()

        assert (
            manifest.get_topic_name(EnumTopicType.COMMANDS)
            == "onex.registration.commands"
        )
        assert manifest.get_topic_name(EnumTopicType.DLQ) == "onex.registration.dlq"
        assert (
            manifest.get_topic_name(EnumTopicType.EVENTS) == "onex.registration.events"
        )
        assert (
            manifest.get_topic_name(EnumTopicType.INTENTS)
            == "onex.registration.intents"
        )
        assert (
            manifest.get_topic_name(EnumTopicType.SNAPSHOTS)
            == "onex.registration.snapshots"
        )

    def test_registration_domain_configs_match_defaults(self):
        """Test that registration domain uses default configs for each type."""
        manifest = ModelTopicManifest.registration_domain()

        assert (
            manifest.get_config(EnumTopicType.COMMANDS)
            == ModelTopicConfig.commands_default()
        )
        assert manifest.get_config(EnumTopicType.DLQ) == ModelTopicConfig.dlq_default()
        assert (
            manifest.get_config(EnumTopicType.EVENTS)
            == ModelTopicConfig.events_default()
        )
        assert (
            manifest.get_config(EnumTopicType.INTENTS)
            == ModelTopicConfig.intents_default()
        )
        assert (
            manifest.get_config(EnumTopicType.SNAPSHOTS)
            == ModelTopicConfig.snapshots_default()
        )


@pytest.mark.unit
class TestModelTopicManifestCreateStandardManifest:
    """Test cases for ModelTopicManifest.create_standard_manifest() factory method."""

    def test_create_standard_manifest_custom_domain(self):
        """Test creating standard manifest with custom domain."""
        manifest = ModelTopicManifest.create_standard_manifest("codegen")

        assert manifest.domain == "codegen"
        assert len(manifest.topics) == 5

    def test_create_standard_manifest_has_all_topics(self):
        """Test that standard manifest has all five topic types."""
        manifest = ModelTopicManifest.create_standard_manifest("metrics")

        assert EnumTopicType.COMMANDS in manifest.topics
        assert EnumTopicType.DLQ in manifest.topics
        assert EnumTopicType.EVENTS in manifest.topics
        assert EnumTopicType.INTENTS in manifest.topics
        assert EnumTopicType.SNAPSHOTS in manifest.topics

    def test_create_standard_manifest_topic_names(self):
        """Test that standard manifest generates correct topic names."""
        manifest = ModelTopicManifest.create_standard_manifest("audit")

        assert manifest.get_topic_name(EnumTopicType.COMMANDS) == "onex.audit.commands"
        assert manifest.get_topic_name(EnumTopicType.DLQ) == "onex.audit.dlq"
        assert manifest.get_topic_name(EnumTopicType.EVENTS) == "onex.audit.events"
        assert manifest.get_topic_name(EnumTopicType.INTENTS) == "onex.audit.intents"
        assert (
            manifest.get_topic_name(EnumTopicType.SNAPSHOTS) == "onex.audit.snapshots"
        )

    def test_create_standard_manifest_uses_default_configs(self):
        """Test that standard manifest uses default configs for each type."""
        manifest = ModelTopicManifest.create_standard_manifest("test")

        assert (
            manifest.get_config(EnumTopicType.COMMANDS)
            == ModelTopicConfig.commands_default()
        )
        assert manifest.get_config(EnumTopicType.DLQ) == ModelTopicConfig.dlq_default()
        assert (
            manifest.get_config(EnumTopicType.EVENTS)
            == ModelTopicConfig.events_default()
        )
        assert (
            manifest.get_config(EnumTopicType.INTENTS)
            == ModelTopicConfig.intents_default()
        )
        assert (
            manifest.get_config(EnumTopicType.SNAPSHOTS)
            == ModelTopicConfig.snapshots_default()
        )

    def test_create_standard_manifest_invalid_domain(self):
        """Test that invalid domain raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelTopicManifest.create_standard_manifest("Invalid-Domain")

    def test_create_standard_manifest_equivalent_to_registration(self):
        """Test that create_standard_manifest('registration') equals registration_domain()."""
        standard = ModelTopicManifest.create_standard_manifest("registration")
        registration = ModelTopicManifest.registration_domain()

        assert standard.domain == registration.domain
        assert standard.topics == registration.topics


@pytest.mark.unit
class TestModelTopicManifestSerialization:
    """Test cases for ModelTopicManifest serialization."""

    def test_model_dump(self):
        """Test Pydantic model_dump() serialization."""
        manifest = ModelTopicManifest.registration_domain()
        data = manifest.model_dump()

        assert data["domain"] == "registration"
        assert "topics" in data
        assert len(data["topics"]) == 5

    def test_model_dump_json(self):
        """Test JSON serialization."""
        manifest = ModelTopicManifest.registration_domain()
        json_str = manifest.model_dump_json()

        assert isinstance(json_str, str)
        assert "registration" in json_str
        assert "events" in json_str
        assert "commands" in json_str

    def test_model_validate_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelTopicManifest.registration_domain()
        json_str = original.model_dump_json()
        restored = ModelTopicManifest.model_validate_json(json_str)

        assert restored.domain == original.domain
        assert len(restored.topics) == len(original.topics)


@pytest.mark.unit
class TestModelTopicManifestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_hyphenated_domain_topic_names(self):
        """Test topic names with hyphenated domain."""
        manifest = ModelTopicManifest.create_standard_manifest("my-service-v2")

        assert (
            manifest.get_topic_name(EnumTopicType.EVENTS) == "onex.my-service-v2.events"
        )

    def test_manifest_iteration_over_topics(self):
        """Test iterating over manifest topics."""
        manifest = ModelTopicManifest.registration_domain()

        topic_types = list(manifest.topics.keys())
        assert len(topic_types) == 5

    def test_manifest_topics_values(self):
        """Test accessing all topic configs via values()."""
        manifest = ModelTopicManifest.registration_domain()

        configs = list(manifest.topics.values())
        assert len(configs) == 5
        assert all(isinstance(c, ModelTopicConfig) for c in configs)

    def test_manifest_topics_items(self):
        """Test accessing all topic type/config pairs via items()."""
        manifest = ModelTopicManifest.registration_domain()

        for topic_type, config in manifest.topics.items():
            assert isinstance(topic_type, EnumTopicType)
            assert isinstance(config, ModelTopicConfig)
            assert config.topic_type == topic_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
