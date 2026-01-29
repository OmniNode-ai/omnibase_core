"""
Unit tests for ONEX Topic Taxonomy constants.

Tests cover:
- topic_name() function behavior
- Topic type suffix constants (including DLQ)
- Domain name constants
- Topic constants for all domains
- Cleanup policy constants
- Retention default constants
- Naming convention compliance
- Token mapping functions (get_token_to_topic_type, get_topic_type_to_token,
  get_valid_topic_suffix_kinds)
"""

import pytest

from omnibase_core.constants import (
    CLEANUP_POLICY_COMMANDS,
    CLEANUP_POLICY_EVENTS,
    CLEANUP_POLICY_INTENTS,
    CLEANUP_POLICY_SNAPSHOTS,
    DOMAIN_AUDIT,
    DOMAIN_DISCOVERY,
    DOMAIN_METRICS,
    DOMAIN_REGISTRATION,
    DOMAIN_RUNTIME,
    RETENTION_MS_AUDIT,
    RETENTION_MS_COMMANDS,
    RETENTION_MS_EVENTS,
    RETENTION_MS_INTENTS,
    RETENTION_MS_SNAPSHOTS,
    TOPIC_DISCOVERY_COMMANDS,
    TOPIC_DISCOVERY_EVENTS,
    TOPIC_DISCOVERY_INTENTS,
    TOPIC_EVENT_PUBLISH_INTENT,
    TOPIC_REGISTRATION_COMMANDS,
    TOPIC_REGISTRATION_EVENTS,
    TOPIC_REGISTRATION_INTENTS,
    TOPIC_REGISTRATION_SNAPSHOTS,
    TOPIC_RUNTIME_COMMANDS,
    TOPIC_RUNTIME_EVENTS,
    TOPIC_RUNTIME_INTENTS,
    TOPIC_TYPE_COMMANDS,
    TOPIC_TYPE_DLQ,
    TOPIC_TYPE_EVENTS,
    TOPIC_TYPE_INTENTS,
    TOPIC_TYPE_SNAPSHOTS,
    topic_name,
)
from omnibase_core.constants.constants_topic_taxonomy import (
    PLATFORM_BASELINE_TOPIC_SUFFIXES,
    get_token_to_topic_type,
    get_topic_type_to_token,
    get_valid_topic_suffix_kinds,
)
from omnibase_core.enums.enum_topic_taxonomy import EnumTopicType


@pytest.mark.unit
class TestTopicNameFunction:
    """Test cases for the topic_name() generator function."""

    def test_basic_format(self):
        """Test that topic_name generates onex.<domain>.<type> format."""
        result = topic_name("test", "events")
        assert result == "onex.test.events"

    def test_registration_domain(self):
        """Test topic_name with registration domain."""
        result = topic_name("registration", "events")
        assert result == "onex.registration.events"

    def test_all_topic_types(self):
        """Test topic_name with all topic types."""
        assert topic_name("test", "commands") == "onex.test.commands"
        assert topic_name("test", "events") == "onex.test.events"
        assert topic_name("test", "intents") == "onex.test.intents"
        assert topic_name("test", "snapshots") == "onex.test.snapshots"

    def test_custom_domain(self):
        """Test topic_name with custom domain names."""
        assert topic_name("myservice", "events") == "onex.myservice.events"
        assert topic_name("codegen", "commands") == "onex.codegen.commands"
        assert topic_name("audit", "snapshots") == "onex.audit.snapshots"

    def test_hyphenated_domain(self):
        """Test topic_name with hyphenated domain names."""
        result = topic_name("my-service", "events")
        assert result == "onex.my-service.events"

    def test_numeric_suffix_domain(self):
        """Test topic_name with numeric domain suffixes."""
        result = topic_name("service1", "events")
        assert result == "onex.service1.events"

    def test_returns_string(self):
        """Test that topic_name always returns a string."""
        result = topic_name("test", "events")
        assert isinstance(result, str)

    def test_consistent_prefix(self):
        """Test that all generated names start with 'onex.'."""
        domains = ["registration", "discovery", "runtime", "metrics", "audit"]
        types = ["commands", "events", "intents", "snapshots"]

        for domain in domains:
            for topic_type in types:
                result = topic_name(domain, topic_type)
                assert result.startswith("onex.")


@pytest.mark.unit
class TestTopicNameValidation:
    """Test cases for topic_name() input validation."""

    def test_empty_domain_raises_error(self):
        """Test that empty domain raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("", "events")
        assert "empty" in str(exc_info.value).lower()

    def test_uppercase_domain_raises_error(self):
        """Test that uppercase domain raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("Registration", "events")
        assert "Invalid domain" in str(exc_info.value)

    def test_domain_starting_with_number_raises_error(self):
        """Test that domain starting with number raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("1service", "events")
        assert "Invalid domain" in str(exc_info.value)

    def test_domain_with_underscore_raises_error(self):
        """Test that domain with underscore raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("my_service", "events")
        assert "Invalid domain" in str(exc_info.value)

    def test_domain_with_dot_raises_error(self):
        """Test that domain with dot raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("my.service", "events")
        assert "Invalid domain" in str(exc_info.value)

    def test_domain_with_space_raises_error(self):
        """Test that domain with space raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("my service", "events")
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_topic_type_raises_error(self):
        """Test that invalid topic type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("test", "logs")
        assert "Invalid topic_type" in str(exc_info.value)
        assert "logs" in str(exc_info.value)

    def test_empty_topic_type_raises_error(self):
        """Test that empty topic type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("test", "")
        assert "Invalid topic_type" in str(exc_info.value)

    def test_uppercase_topic_type_raises_error(self):
        """Test that uppercase topic type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            topic_name("test", "Events")
        assert "Invalid topic_type" in str(exc_info.value)

    def test_valid_domain_patterns(self):
        """Test various valid domain patterns pass validation."""
        # Single letter
        assert topic_name("a", "events") == "onex.a.events"
        # Alphanumeric
        assert topic_name("service1", "events") == "onex.service1.events"
        # Hyphenated
        assert topic_name("my-service", "events") == "onex.my-service.events"
        # Complex
        assert topic_name("my-service-v2", "events") == "onex.my-service-v2.events"


@pytest.mark.unit
class TestTopicTypeSuffixConstants:
    """Test cases for topic type suffix constants."""

    def test_topic_type_commands_value(self):
        """Test TOPIC_TYPE_COMMANDS constant value."""
        assert TOPIC_TYPE_COMMANDS == "commands"

    def test_topic_type_dlq_value(self):
        """Test TOPIC_TYPE_DLQ constant value."""
        assert TOPIC_TYPE_DLQ == "dlq"

    def test_topic_type_events_value(self):
        """Test TOPIC_TYPE_EVENTS constant value."""
        assert TOPIC_TYPE_EVENTS == "events"

    def test_topic_type_intents_value(self):
        """Test TOPIC_TYPE_INTENTS constant value."""
        assert TOPIC_TYPE_INTENTS == "intents"

    def test_topic_type_snapshots_value(self):
        """Test TOPIC_TYPE_SNAPSHOTS constant value."""
        assert TOPIC_TYPE_SNAPSHOTS == "snapshots"

    def test_topic_types_are_strings(self):
        """Test that all topic type constants are strings."""
        assert isinstance(TOPIC_TYPE_COMMANDS, str)
        assert isinstance(TOPIC_TYPE_DLQ, str)
        assert isinstance(TOPIC_TYPE_EVENTS, str)
        assert isinstance(TOPIC_TYPE_INTENTS, str)
        assert isinstance(TOPIC_TYPE_SNAPSHOTS, str)

    def test_topic_types_are_lowercase(self):
        """Test that all topic type constants are lowercase."""
        assert TOPIC_TYPE_COMMANDS.islower()
        assert TOPIC_TYPE_DLQ.islower()
        assert TOPIC_TYPE_EVENTS.islower()
        assert TOPIC_TYPE_INTENTS.islower()
        assert TOPIC_TYPE_SNAPSHOTS.islower()

    def test_topic_types_unique(self):
        """Test that all topic type constants have unique values."""
        types = [
            TOPIC_TYPE_COMMANDS,
            TOPIC_TYPE_DLQ,
            TOPIC_TYPE_EVENTS,
            TOPIC_TYPE_INTENTS,
            TOPIC_TYPE_SNAPSHOTS,
        ]
        assert len(types) == len(set(types))


@pytest.mark.unit
class TestDomainNameConstants:
    """Test cases for domain name constants."""

    def test_domain_registration_value(self):
        """Test DOMAIN_REGISTRATION constant value."""
        assert DOMAIN_REGISTRATION == "registration"

    def test_domain_discovery_value(self):
        """Test DOMAIN_DISCOVERY constant value."""
        assert DOMAIN_DISCOVERY == "discovery"

    def test_domain_runtime_value(self):
        """Test DOMAIN_RUNTIME constant value."""
        assert DOMAIN_RUNTIME == "runtime"

    def test_domain_metrics_value(self):
        """Test DOMAIN_METRICS constant value."""
        assert DOMAIN_METRICS == "metrics"

    def test_domain_audit_value(self):
        """Test DOMAIN_AUDIT constant value."""
        assert DOMAIN_AUDIT == "audit"

    def test_domains_are_strings(self):
        """Test that all domain constants are strings."""
        assert isinstance(DOMAIN_REGISTRATION, str)
        assert isinstance(DOMAIN_DISCOVERY, str)
        assert isinstance(DOMAIN_RUNTIME, str)
        assert isinstance(DOMAIN_METRICS, str)
        assert isinstance(DOMAIN_AUDIT, str)

    def test_domains_are_lowercase(self):
        """Test that all domain constants are lowercase."""
        assert DOMAIN_REGISTRATION.islower()
        assert DOMAIN_DISCOVERY.islower()
        assert DOMAIN_RUNTIME.islower()
        assert DOMAIN_METRICS.islower()
        assert DOMAIN_AUDIT.islower()

    def test_domains_unique(self):
        """Test that all domain constants have unique values."""
        domains = [
            DOMAIN_REGISTRATION,
            DOMAIN_DISCOVERY,
            DOMAIN_RUNTIME,
            DOMAIN_METRICS,
            DOMAIN_AUDIT,
        ]
        assert len(domains) == len(set(domains))


@pytest.mark.unit
class TestRegistrationDomainTopics:
    """Test cases for registration domain topic constants."""

    def test_registration_commands(self):
        """Test TOPIC_REGISTRATION_COMMANDS constant value."""
        assert TOPIC_REGISTRATION_COMMANDS == "onex.registration.commands"

    def test_registration_events(self):
        """Test TOPIC_REGISTRATION_EVENTS constant value."""
        assert TOPIC_REGISTRATION_EVENTS == "onex.registration.events"

    def test_registration_intents(self):
        """Test TOPIC_REGISTRATION_INTENTS constant value."""
        assert TOPIC_REGISTRATION_INTENTS == "onex.registration.intents"

    def test_registration_snapshots(self):
        """Test TOPIC_REGISTRATION_SNAPSHOTS constant value."""
        assert TOPIC_REGISTRATION_SNAPSHOTS == "onex.registration.snapshots"

    def test_registration_topics_use_topic_name(self):
        """Test that registration topics are equivalent to topic_name() output."""
        assert (
            topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_COMMANDS)
            == TOPIC_REGISTRATION_COMMANDS
        )
        assert (
            topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_EVENTS)
            == TOPIC_REGISTRATION_EVENTS
        )
        assert (
            topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_INTENTS)
            == TOPIC_REGISTRATION_INTENTS
        )
        assert (
            topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_SNAPSHOTS)
            == TOPIC_REGISTRATION_SNAPSHOTS
        )


@pytest.mark.unit
class TestDiscoveryDomainTopics:
    """Test cases for discovery domain topic constants."""

    def test_discovery_commands(self):
        """Test TOPIC_DISCOVERY_COMMANDS constant value."""
        assert TOPIC_DISCOVERY_COMMANDS == "onex.discovery.commands"

    def test_discovery_events(self):
        """Test TOPIC_DISCOVERY_EVENTS constant value."""
        assert TOPIC_DISCOVERY_EVENTS == "onex.discovery.events"

    def test_discovery_intents(self):
        """Test TOPIC_DISCOVERY_INTENTS constant value."""
        assert TOPIC_DISCOVERY_INTENTS == "onex.discovery.intents"

    def test_discovery_topics_use_topic_name(self):
        """Test that discovery topics are equivalent to topic_name() output."""
        assert (
            topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_COMMANDS)
            == TOPIC_DISCOVERY_COMMANDS
        )
        assert topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_EVENTS) == TOPIC_DISCOVERY_EVENTS
        assert (
            topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_INTENTS) == TOPIC_DISCOVERY_INTENTS
        )


@pytest.mark.unit
class TestRuntimeDomainTopics:
    """Test cases for runtime domain topic constants."""

    def test_runtime_commands(self):
        """Test TOPIC_RUNTIME_COMMANDS constant value."""
        assert TOPIC_RUNTIME_COMMANDS == "onex.runtime.commands"

    def test_runtime_events(self):
        """Test TOPIC_RUNTIME_EVENTS constant value."""
        assert TOPIC_RUNTIME_EVENTS == "onex.runtime.events"

    def test_runtime_intents(self):
        """Test TOPIC_RUNTIME_INTENTS constant value."""
        assert TOPIC_RUNTIME_INTENTS == "onex.runtime.intents"

    def test_runtime_topics_use_topic_name(self):
        """Test that runtime topics are equivalent to topic_name() output."""
        assert topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_COMMANDS) == TOPIC_RUNTIME_COMMANDS
        assert topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_EVENTS) == TOPIC_RUNTIME_EVENTS
        assert topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_INTENTS) == TOPIC_RUNTIME_INTENTS


@pytest.mark.unit
class TestSpecialTopicConstants:
    """Test cases for special topic constants."""

    def test_event_publish_intent(self):
        """Test TOPIC_EVENT_PUBLISH_INTENT constant value."""
        assert TOPIC_EVENT_PUBLISH_INTENT == "onex.runtime.intents"

    def test_event_publish_intent_equals_runtime_intents(self):
        """Test that TOPIC_EVENT_PUBLISH_INTENT equals TOPIC_RUNTIME_INTENTS."""
        assert TOPIC_EVENT_PUBLISH_INTENT == TOPIC_RUNTIME_INTENTS


@pytest.mark.unit
class TestCleanupPolicyConstants:
    """Test cases for cleanup policy constants."""

    def test_cleanup_policy_events(self):
        """Test CLEANUP_POLICY_EVENTS constant value."""
        assert CLEANUP_POLICY_EVENTS == "delete"

    def test_cleanup_policy_snapshots(self):
        """Test CLEANUP_POLICY_SNAPSHOTS constant value."""
        assert CLEANUP_POLICY_SNAPSHOTS == "compact,delete"

    def test_cleanup_policy_commands(self):
        """Test CLEANUP_POLICY_COMMANDS constant value."""
        assert CLEANUP_POLICY_COMMANDS == "delete"

    def test_cleanup_policy_intents(self):
        """Test CLEANUP_POLICY_INTENTS constant value."""
        assert CLEANUP_POLICY_INTENTS == "delete"

    def test_cleanup_policies_are_strings(self):
        """Test that all cleanup policy constants are strings."""
        assert isinstance(CLEANUP_POLICY_EVENTS, str)
        assert isinstance(CLEANUP_POLICY_SNAPSHOTS, str)
        assert isinstance(CLEANUP_POLICY_COMMANDS, str)
        assert isinstance(CLEANUP_POLICY_INTENTS, str)

    def test_cleanup_policy_values_are_valid_kafka_policies(self):
        """Test that cleanup policy values are valid Kafka cleanup.policy values."""
        valid_policies = ["delete", "compact", "compact,delete"]
        assert CLEANUP_POLICY_EVENTS in valid_policies
        assert CLEANUP_POLICY_SNAPSHOTS in valid_policies
        assert CLEANUP_POLICY_COMMANDS in valid_policies
        assert CLEANUP_POLICY_INTENTS in valid_policies

    def test_snapshots_use_compaction(self):
        """Test that snapshots use compaction (key-based retention)."""
        assert "compact" in CLEANUP_POLICY_SNAPSHOTS

    def test_events_commands_intents_use_delete(self):
        """Test that events, commands, and intents use delete (time-based)."""
        assert CLEANUP_POLICY_EVENTS == "delete"
        assert CLEANUP_POLICY_COMMANDS == "delete"
        assert CLEANUP_POLICY_INTENTS == "delete"


@pytest.mark.unit
class TestRetentionConstants:
    """Test cases for retention constants by topic type."""

    def test_retention_ms_commands_value(self):
        """Test RETENTION_MS_COMMANDS constant value."""
        assert RETENTION_MS_COMMANDS == 604800000  # 7 days in milliseconds

    def test_retention_ms_events_value(self):
        """Test RETENTION_MS_EVENTS constant value."""
        assert RETENTION_MS_EVENTS == 2592000000  # 30 days in milliseconds

    def test_retention_ms_intents_value(self):
        """Test RETENTION_MS_INTENTS constant value."""
        assert RETENTION_MS_INTENTS == 86400000  # 1 day in milliseconds

    def test_retention_ms_snapshots_value(self):
        """Test RETENTION_MS_SNAPSHOTS constant value."""
        assert RETENTION_MS_SNAPSHOTS == 604800000  # 7 days in milliseconds

    def test_retention_ms_audit_value(self):
        """Test RETENTION_MS_AUDIT constant value."""
        assert RETENTION_MS_AUDIT == 2592000000  # 30 days in milliseconds

    def test_retention_values_are_integers(self):
        """Test that retention values are integers."""
        assert isinstance(RETENTION_MS_COMMANDS, int)
        assert isinstance(RETENTION_MS_EVENTS, int)
        assert isinstance(RETENTION_MS_INTENTS, int)
        assert isinstance(RETENTION_MS_SNAPSHOTS, int)
        assert isinstance(RETENTION_MS_AUDIT, int)

    def test_retention_values_are_positive(self):
        """Test that retention values are positive."""
        assert RETENTION_MS_COMMANDS > 0
        assert RETENTION_MS_EVENTS > 0
        assert RETENTION_MS_INTENTS > 0
        assert RETENTION_MS_SNAPSHOTS > 0
        assert RETENTION_MS_AUDIT > 0

    def test_retention_commands_is_7_days(self):
        """Test that RETENTION_MS_COMMANDS equals 7 days."""
        seven_days_ms = 7 * 24 * 60 * 60 * 1000
        assert seven_days_ms == RETENTION_MS_COMMANDS

    def test_retention_events_is_30_days(self):
        """Test that RETENTION_MS_EVENTS equals 30 days."""
        thirty_days_ms = 30 * 24 * 60 * 60 * 1000
        assert thirty_days_ms == RETENTION_MS_EVENTS

    def test_retention_intents_is_1_day(self):
        """Test that RETENTION_MS_INTENTS equals 1 day."""
        one_day_ms = 1 * 24 * 60 * 60 * 1000
        assert one_day_ms == RETENTION_MS_INTENTS

    def test_retention_snapshots_is_7_days(self):
        """Test that RETENTION_MS_SNAPSHOTS equals 7 days."""
        seven_days_ms = 7 * 24 * 60 * 60 * 1000
        assert seven_days_ms == RETENTION_MS_SNAPSHOTS

    def test_retention_audit_is_30_days(self):
        """Test that RETENTION_MS_AUDIT equals 30 days."""
        thirty_days_ms = 30 * 24 * 60 * 60 * 1000
        assert thirty_days_ms == RETENTION_MS_AUDIT

    def test_events_and_audit_have_same_retention(self):
        """Test that events and audit have the same retention (30 days)."""
        assert RETENTION_MS_EVENTS == RETENTION_MS_AUDIT

    def test_commands_and_snapshots_have_same_retention(self):
        """Test that commands and snapshots have the same retention (7 days)."""
        assert RETENTION_MS_COMMANDS == RETENTION_MS_SNAPSHOTS

    def test_intents_have_shortest_retention(self):
        """Test that intents have the shortest retention (1 day)."""
        assert RETENTION_MS_INTENTS < RETENTION_MS_COMMANDS
        assert RETENTION_MS_INTENTS < RETENTION_MS_EVENTS
        assert RETENTION_MS_INTENTS < RETENTION_MS_SNAPSHOTS
        assert RETENTION_MS_INTENTS < RETENTION_MS_AUDIT


@pytest.mark.unit
class TestTopicNamingConvention:
    """Test cases for topic naming convention compliance."""

    def test_all_topics_start_with_onex(self):
        """Test that all topic constants start with 'onex.'."""
        topics = [
            TOPIC_REGISTRATION_COMMANDS,
            TOPIC_REGISTRATION_EVENTS,
            TOPIC_REGISTRATION_INTENTS,
            TOPIC_REGISTRATION_SNAPSHOTS,
            TOPIC_DISCOVERY_COMMANDS,
            TOPIC_DISCOVERY_EVENTS,
            TOPIC_DISCOVERY_INTENTS,
            TOPIC_RUNTIME_COMMANDS,
            TOPIC_RUNTIME_EVENTS,
            TOPIC_RUNTIME_INTENTS,
            TOPIC_EVENT_PUBLISH_INTENT,
        ]

        for topic in topics:
            assert topic.startswith("onex."), f"Topic {topic} should start with 'onex.'"

    def test_all_topics_have_three_parts(self):
        """Test that all topic constants have exactly three dot-separated parts."""
        topics = [
            TOPIC_REGISTRATION_COMMANDS,
            TOPIC_REGISTRATION_EVENTS,
            TOPIC_REGISTRATION_INTENTS,
            TOPIC_REGISTRATION_SNAPSHOTS,
            TOPIC_DISCOVERY_COMMANDS,
            TOPIC_DISCOVERY_EVENTS,
            TOPIC_DISCOVERY_INTENTS,
            TOPIC_RUNTIME_COMMANDS,
            TOPIC_RUNTIME_EVENTS,
            TOPIC_RUNTIME_INTENTS,
        ]

        for topic in topics:
            parts = topic.split(".")
            assert len(parts) == 3, (
                f"Topic {topic} should have 3 parts, has {len(parts)}"
            )

    def test_all_topics_are_lowercase(self):
        """Test that all topic constants are lowercase."""
        topics = [
            TOPIC_REGISTRATION_COMMANDS,
            TOPIC_REGISTRATION_EVENTS,
            TOPIC_REGISTRATION_INTENTS,
            TOPIC_REGISTRATION_SNAPSHOTS,
            TOPIC_DISCOVERY_COMMANDS,
            TOPIC_DISCOVERY_EVENTS,
            TOPIC_DISCOVERY_INTENTS,
            TOPIC_RUNTIME_COMMANDS,
            TOPIC_RUNTIME_EVENTS,
            TOPIC_RUNTIME_INTENTS,
        ]

        for topic in topics:
            assert topic == topic.lower(), f"Topic {topic} should be lowercase"

    def test_topic_parts_match_constants(self):
        """Test that topic parts correspond to domain and type constants."""
        # Check registration domain topics
        parts = TOPIC_REGISTRATION_EVENTS.split(".")
        assert parts[0] == "onex"
        assert parts[1] == DOMAIN_REGISTRATION
        assert parts[2] == TOPIC_TYPE_EVENTS

        # Check discovery domain topics
        parts = TOPIC_DISCOVERY_COMMANDS.split(".")
        assert parts[0] == "onex"
        assert parts[1] == DOMAIN_DISCOVERY
        assert parts[2] == TOPIC_TYPE_COMMANDS

        # Check runtime domain topics
        parts = TOPIC_RUNTIME_INTENTS.split(".")
        assert parts[0] == "onex"
        assert parts[1] == DOMAIN_RUNTIME
        assert parts[2] == TOPIC_TYPE_INTENTS


@pytest.mark.unit
class TestTopicConstantsUniqueness:
    """Test cases for topic constant uniqueness."""

    def test_all_topic_constants_unique(self):
        """Test that all topic constants have unique values."""
        topics = [
            TOPIC_REGISTRATION_COMMANDS,
            TOPIC_REGISTRATION_EVENTS,
            TOPIC_REGISTRATION_INTENTS,
            TOPIC_REGISTRATION_SNAPSHOTS,
            TOPIC_DISCOVERY_COMMANDS,
            TOPIC_DISCOVERY_EVENTS,
            TOPIC_DISCOVERY_INTENTS,
            TOPIC_RUNTIME_COMMANDS,
            TOPIC_RUNTIME_EVENTS,
            TOPIC_RUNTIME_INTENTS,
        ]

        # Note: TOPIC_EVENT_PUBLISH_INTENT == TOPIC_RUNTIME_INTENTS, so not included
        assert len(topics) == len(set(topics))


@pytest.mark.unit
class TestTopicConstantsUsability:
    """Test cases for topic constant usability patterns."""

    def test_topics_can_be_used_as_dict_keys(self):
        """Test that topic constants work as dictionary keys."""
        handlers = {
            TOPIC_REGISTRATION_EVENTS: "handle_registration_event",
            TOPIC_RUNTIME_COMMANDS: "handle_runtime_command",
        }

        assert handlers[TOPIC_REGISTRATION_EVENTS] == "handle_registration_event"
        assert handlers[TOPIC_RUNTIME_COMMANDS] == "handle_runtime_command"

    def test_topics_can_be_compared(self):
        """Test that topic constants support string comparison."""
        assert TOPIC_REGISTRATION_EVENTS == "onex.registration.events"
        assert TOPIC_RUNTIME_COMMANDS == "onex.runtime.commands"

    def test_topics_can_be_used_in_sets(self):
        """Test that topic constants work in sets."""
        topic_set = {
            TOPIC_REGISTRATION_EVENTS,
            TOPIC_RUNTIME_EVENTS,
            TOPIC_DISCOVERY_EVENTS,
        }

        assert len(topic_set) == 3
        assert TOPIC_REGISTRATION_EVENTS in topic_set

    def test_topics_can_be_serialized(self):
        """Test that topic constants can be JSON serialized."""
        import json

        data = {
            "topic": TOPIC_REGISTRATION_EVENTS,
            "domain": DOMAIN_REGISTRATION,
        }

        serialized = json.dumps(data)
        deserialized = json.loads(serialized)

        assert deserialized["topic"] == TOPIC_REGISTRATION_EVENTS
        assert deserialized["domain"] == DOMAIN_REGISTRATION


@pytest.mark.unit
class TestTopicNameFunctionWithConstants:
    """Test topic_name() function integration with constants."""

    def test_topic_name_with_domain_constants(self):
        """Test topic_name() using domain constants."""
        assert topic_name(DOMAIN_REGISTRATION, "events") == "onex.registration.events"
        assert topic_name(DOMAIN_DISCOVERY, "commands") == "onex.discovery.commands"
        assert topic_name(DOMAIN_RUNTIME, "intents") == "onex.runtime.intents"

    def test_topic_name_with_type_constants(self):
        """Test topic_name() using type constants."""
        assert topic_name("test", TOPIC_TYPE_EVENTS) == "onex.test.events"
        assert topic_name("test", TOPIC_TYPE_COMMANDS) == "onex.test.commands"
        assert topic_name("test", TOPIC_TYPE_INTENTS) == "onex.test.intents"
        assert topic_name("test", TOPIC_TYPE_SNAPSHOTS) == "onex.test.snapshots"

    def test_topic_name_with_both_constants(self):
        """Test topic_name() using both domain and type constants."""
        assert (
            topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_EVENTS)
            == TOPIC_REGISTRATION_EVENTS
        )
        assert (
            topic_name(DOMAIN_REGISTRATION, TOPIC_TYPE_COMMANDS)
            == TOPIC_REGISTRATION_COMMANDS
        )
        assert topic_name(DOMAIN_DISCOVERY, TOPIC_TYPE_EVENTS) == TOPIC_DISCOVERY_EVENTS
        assert topic_name(DOMAIN_RUNTIME, TOPIC_TYPE_INTENTS) == TOPIC_RUNTIME_INTENTS


@pytest.mark.unit
class TestModuleDocumentation:
    """Test cases for module documentation."""

    def test_module_has_docstring(self):
        """Test that the topic taxonomy module has a docstring."""
        from omnibase_core.constants import constants_topic_taxonomy

        assert constants_topic_taxonomy.__doc__ is not None
        assert len(constants_topic_taxonomy.__doc__) > 0

    def test_module_docstring_describes_purpose(self):
        """Test that module docstring describes topic taxonomy."""
        from omnibase_core.constants import constants_topic_taxonomy

        docstring = constants_topic_taxonomy.__doc__.lower()
        assert "topic" in docstring


@pytest.mark.unit
class TestModuleExports:
    """Test cases for module __all__ exports."""

    def test_all_topic_types_exported(self):
        """Test that all topic type constants are exported."""
        from omnibase_core.constants import constants_topic_taxonomy

        all_exports = constants_topic_taxonomy.__all__

        assert "TOPIC_TYPE_COMMANDS" in all_exports
        assert "TOPIC_TYPE_DLQ" in all_exports
        assert "TOPIC_TYPE_EVENTS" in all_exports
        assert "TOPIC_TYPE_INTENTS" in all_exports
        assert "TOPIC_TYPE_SNAPSHOTS" in all_exports

    def test_all_domains_exported(self):
        """Test that all domain constants are exported."""
        from omnibase_core.constants import constants_topic_taxonomy

        all_exports = constants_topic_taxonomy.__all__

        assert "DOMAIN_REGISTRATION" in all_exports
        assert "DOMAIN_DISCOVERY" in all_exports
        assert "DOMAIN_RUNTIME" in all_exports
        assert "DOMAIN_METRICS" in all_exports
        assert "DOMAIN_AUDIT" in all_exports

    def test_topic_name_function_exported(self):
        """Test that topic_name function is exported."""
        from omnibase_core.constants import constants_topic_taxonomy

        all_exports = constants_topic_taxonomy.__all__

        assert "topic_name" in all_exports

    def test_cleanup_policies_exported(self):
        """Test that cleanup policy constants are exported."""
        from omnibase_core.constants import constants_topic_taxonomy

        all_exports = constants_topic_taxonomy.__all__

        assert "CLEANUP_POLICY_EVENTS" in all_exports
        assert "CLEANUP_POLICY_SNAPSHOTS" in all_exports
        assert "CLEANUP_POLICY_COMMANDS" in all_exports
        assert "CLEANUP_POLICY_INTENTS" in all_exports

    def test_retention_constants_exported(self):
        """Test that retention constants are exported."""
        from omnibase_core.constants import constants_topic_taxonomy

        all_exports = constants_topic_taxonomy.__all__

        assert "RETENTION_MS_COMMANDS" in all_exports
        assert "RETENTION_MS_EVENTS" in all_exports
        assert "RETENTION_MS_INTENTS" in all_exports
        assert "RETENTION_MS_SNAPSHOTS" in all_exports
        assert "RETENTION_MS_AUDIT" in all_exports


@pytest.mark.unit
class TestTokenMappingFunctions:
    """Tests for token mapping accessor functions."""

    def test_get_token_to_topic_type_returns_dict(self) -> None:
        """Test that get_token_to_topic_type returns a dictionary."""
        mapping = get_token_to_topic_type()
        assert isinstance(mapping, dict)

    def test_get_token_to_topic_type_contains_all_tokens(self) -> None:
        """Test that mapping contains all expected tokens."""
        mapping = get_token_to_topic_type()
        expected_tokens = {"cmd", "dlq", "evt", "intent", "snapshot"}
        assert set(mapping.keys()) == expected_tokens

    def test_get_token_to_topic_type_maps_correctly(self) -> None:
        """Test that tokens map to correct enum values."""
        mapping = get_token_to_topic_type()
        assert mapping["cmd"] == EnumTopicType.COMMANDS
        assert mapping["evt"] == EnumTopicType.EVENTS
        assert mapping["dlq"] == EnumTopicType.DLQ
        assert mapping["intent"] == EnumTopicType.INTENTS
        assert mapping["snapshot"] == EnumTopicType.SNAPSHOTS

    def test_get_topic_type_to_token_returns_dict(self) -> None:
        """Test that get_topic_type_to_token returns a dictionary."""
        mapping = get_topic_type_to_token()
        assert isinstance(mapping, dict)

    def test_get_topic_type_to_token_is_reverse_of_token_to_type(self) -> None:
        """Test that reverse mapping is inverse of forward mapping."""
        forward = get_token_to_topic_type()
        reverse = get_topic_type_to_token()
        for token, enum_val in forward.items():
            assert reverse[enum_val] == token

    def test_get_topic_type_to_token_maps_correctly(self) -> None:
        """Test that enum values map to correct tokens."""
        mapping = get_topic_type_to_token()
        assert mapping[EnumTopicType.COMMANDS] == "cmd"
        assert mapping[EnumTopicType.EVENTS] == "evt"
        assert mapping[EnumTopicType.DLQ] == "dlq"
        assert mapping[EnumTopicType.INTENTS] == "intent"
        assert mapping[EnumTopicType.SNAPSHOTS] == "snapshot"

    def test_get_valid_topic_suffix_kinds_returns_frozenset(self) -> None:
        """Test that get_valid_topic_suffix_kinds returns a frozenset."""
        kinds = get_valid_topic_suffix_kinds()
        assert isinstance(kinds, frozenset)

    def test_get_valid_topic_suffix_kinds_contains_all_tokens(self) -> None:
        """Test that frozenset contains all valid tokens."""
        kinds = get_valid_topic_suffix_kinds()
        expected = {"cmd", "dlq", "evt", "intent", "snapshot"}
        assert kinds == expected

    def test_mappings_return_defensive_copies(self) -> None:
        """Test that dict accessors return defensive copies to prevent mutation."""
        # Dict accessors should return different objects (defensive copies)
        mapping1 = get_token_to_topic_type()
        mapping2 = get_token_to_topic_type()
        assert mapping1 is not mapping2  # Different objects
        assert mapping1 == mapping2  # Same content

        reverse1 = get_topic_type_to_token()
        reverse2 = get_topic_type_to_token()
        assert reverse1 is not reverse2  # Different objects
        assert reverse1 == reverse2  # Same content

        # Frozenset accessor can return same object (immutable, safe to share)
        kinds1 = get_valid_topic_suffix_kinds()
        kinds2 = get_valid_topic_suffix_kinds()
        assert kinds1 is kinds2  # Same object (frozenset is immutable)

    def test_valid_kinds_matches_token_keys(self) -> None:
        """Test that valid kinds equals token mapping keys."""
        tokens = get_token_to_topic_type()
        kinds = get_valid_topic_suffix_kinds()
        assert kinds == frozenset(tokens.keys())

    def test_token_to_type_values_are_enum_topic_type(self) -> None:
        """Test that all values in token_to_type are EnumTopicType instances."""
        mapping = get_token_to_topic_type()
        for value in mapping.values():
            assert isinstance(value, EnumTopicType)

    def test_type_to_token_keys_are_enum_topic_type(self) -> None:
        """Test that all keys in type_to_token are EnumTopicType instances."""
        mapping = get_topic_type_to_token()
        for key in mapping:
            assert isinstance(key, EnumTopicType)

    def test_mappings_cover_all_enum_values(self) -> None:
        """Test that mappings cover all EnumTopicType values."""
        type_to_token = get_topic_type_to_token()
        # All EnumTopicType values should be mapped
        expected_types = {
            EnumTopicType.COMMANDS,
            EnumTopicType.DLQ,
            EnumTopicType.EVENTS,
            EnumTopicType.INTENTS,
            EnumTopicType.SNAPSHOTS,
        }
        assert set(type_to_token.keys()) == expected_types


@pytest.mark.unit
class TestTokenMappingExports:
    """Test that token mapping functions are properly exported."""

    def test_token_mapping_functions_in_module_all(self) -> None:
        """Test that token mapping functions are in __all__."""
        from omnibase_core.constants import constants_topic_taxonomy

        all_exports = constants_topic_taxonomy.__all__

        assert "get_token_to_topic_type" in all_exports
        assert "get_topic_type_to_token" in all_exports
        assert "get_valid_topic_suffix_kinds" in all_exports


@pytest.mark.unit
class TestPlatformBaselineTopicSuffixes:
    """Test cases for PLATFORM_BASELINE_TOPIC_SUFFIXES constant (OMN-1652)."""

    def test_platform_baseline_topic_suffixes_is_tuple(self) -> None:
        """Test that PLATFORM_BASELINE_TOPIC_SUFFIXES is a tuple."""
        assert isinstance(PLATFORM_BASELINE_TOPIC_SUFFIXES, tuple)

    def test_platform_baseline_topic_suffixes_contains_expected_values(self) -> None:
        """Test that all expected platform baseline topics are present."""
        expected = {
            "onex.evt.contract-registered.v1",
            "onex.evt.contract-deregistered.v1",
            "onex.evt.node-heartbeat.v1",
        }
        assert set(PLATFORM_BASELINE_TOPIC_SUFFIXES) == expected

    def test_platform_baseline_topic_suffixes_count(self) -> None:
        """Test that there are exactly 3 baseline topic suffixes."""
        assert len(PLATFORM_BASELINE_TOPIC_SUFFIXES) == 3

    def test_platform_baseline_topic_suffixes_follow_naming_convention(self) -> None:
        """Test that all suffixes follow onex.evt.*.v1 convention."""
        for suffix in PLATFORM_BASELINE_TOPIC_SUFFIXES:
            assert suffix.startswith("onex.evt."), (
                f"Suffix {suffix} should start with 'onex.evt.'"
            )
            assert suffix.endswith(".v1"), f"Suffix {suffix} should end with '.v1'"

    def test_platform_baseline_topic_suffixes_are_strings(self) -> None:
        """Test that all suffixes are strings."""
        for suffix in PLATFORM_BASELINE_TOPIC_SUFFIXES:
            assert isinstance(suffix, str)

    def test_platform_baseline_topic_suffixes_are_lowercase(self) -> None:
        """Test that all suffixes are lowercase."""
        for suffix in PLATFORM_BASELINE_TOPIC_SUFFIXES:
            assert suffix == suffix.lower(), f"Suffix {suffix} should be lowercase"

    def test_platform_baseline_topic_suffixes_unique(self) -> None:
        """Test that all suffixes are unique."""
        assert len(PLATFORM_BASELINE_TOPIC_SUFFIXES) == len(
            set(PLATFORM_BASELINE_TOPIC_SUFFIXES)
        )

    def test_platform_baseline_topic_suffixes_have_four_parts(self) -> None:
        """Test that all suffixes have exactly four dot-separated parts."""
        for suffix in PLATFORM_BASELINE_TOPIC_SUFFIXES:
            parts = suffix.split(".")
            assert len(parts) == 4, (
                f"Suffix {suffix} should have 4 parts, has {len(parts)}"
            )

    def test_platform_baseline_topic_suffixes_exported(self) -> None:
        """Test that PLATFORM_BASELINE_TOPIC_SUFFIXES is in __all__."""
        from omnibase_core.constants import constants_topic_taxonomy

        assert "PLATFORM_BASELINE_TOPIC_SUFFIXES" in constants_topic_taxonomy.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
