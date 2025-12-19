"""
Unit tests for ModelTopicNaming.

Tests comprehensive topic naming functionality including:
- Model instantiation and validation
- Model config (frozen, extra forbid, from_attributes)
- Environment validation (valid/invalid values)
- Domain validation (pattern matching)
- Version field validation
- Topic name generation (topic_name property)
- Topic suffix property
- Topic parsing (parse_topic classmethod)
- Convenience factory methods (for_events, for_commands, for_intents)
- Helper functions (validate_topic_matches_category, get_topic_category)
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_topic_naming import (
    ModelTopicNaming,
    get_topic_category,
    validate_message_topic_alignment,
    validate_topic_matches_category,
)


@pytest.mark.unit
class TestModelTopicNamingInstantiation:
    """Test cases for ModelTopicNaming instantiation."""

    def test_instantiation_minimal_required_fields(self):
        """Test model creation with only required fields (domain, category)."""
        naming = ModelTopicNaming(
            domain="user-service",
            category=EnumMessageCategory.EVENT,
        )

        assert naming.domain == "user-service"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.environment == "dev"  # Default
        assert naming.version == "v1"  # Default

    def test_instantiation_with_all_fields(self):
        """Test model creation with all fields provided."""
        naming = ModelTopicNaming(
            environment="prod",
            domain="payment-gateway",
            category=EnumMessageCategory.COMMAND,
            version="v2",
        )

        assert naming.environment == "prod"
        assert naming.domain == "payment-gateway"
        assert naming.category == EnumMessageCategory.COMMAND
        assert naming.version == "v2"

    def test_instantiation_all_message_categories(self):
        """Test model creation with all message category types."""
        # EVENT
        naming_event = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.EVENT,
        )
        assert naming_event.category == EnumMessageCategory.EVENT

        # COMMAND
        naming_command = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.COMMAND,
        )
        assert naming_command.category == EnumMessageCategory.COMMAND

        # INTENT
        naming_intent = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.INTENT,
        )
        assert naming_intent.category == EnumMessageCategory.INTENT


@pytest.mark.unit
class TestModelTopicNamingConfig:
    """Test model_config settings (frozen, extra, from_attributes)."""

    def test_model_is_frozen(self):
        """Test that model is immutable (frozen=True)."""
        naming = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.EVENT,
        )

        with pytest.raises(ValidationError):
            naming.environment = "prod"

        with pytest.raises(ValidationError):
            naming.domain = "other"

        with pytest.raises(ValidationError):
            naming.version = "v2"

    def test_model_forbids_extra_fields(self):
        """Test that extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicNaming(
                domain="user",
                category=EnumMessageCategory.EVENT,
                extra_field="not_allowed",  # type: ignore[call-arg]
            )
        assert (
            "extra_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_model_supports_from_attributes(self):
        """Test that model supports from_attributes=True."""

        # Create a simple object with attributes
        class TopicData:
            def __init__(self):
                self.environment = "staging"
                self.domain = "order"
                self.category = EnumMessageCategory.COMMAND
                self.version = "v3"

        data = TopicData()
        naming = ModelTopicNaming.model_validate(data)

        assert naming.environment == "staging"
        assert naming.domain == "order"
        assert naming.category == EnumMessageCategory.COMMAND
        assert naming.version == "v3"


@pytest.mark.unit
class TestModelTopicNamingEnvironmentValidation:
    """Test environment field validation."""

    def test_valid_environments(self):
        """Test all valid environment values."""
        valid_envs = ["dev", "staging", "prod", "test", "local"]

        for env in valid_envs:
            naming = ModelTopicNaming(
                environment=env,
                domain="user",
                category=EnumMessageCategory.EVENT,
            )
            assert naming.environment == env.lower()

    def test_environment_case_insensitive(self):
        """Test that environment validation is case-insensitive."""
        naming_upper = ModelTopicNaming(
            environment="DEV",
            domain="user",
            category=EnumMessageCategory.EVENT,
        )
        assert naming_upper.environment == "dev"

        naming_mixed = ModelTopicNaming(
            environment="Staging",
            domain="user",
            category=EnumMessageCategory.EVENT,
        )
        assert naming_mixed.environment == "staging"

        naming_all_caps = ModelTopicNaming(
            environment="PROD",
            domain="user",
            category=EnumMessageCategory.EVENT,
        )
        assert naming_all_caps.environment == "prod"

    def test_invalid_environment_raises_value_error(self):
        """Test that invalid environment raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicNaming(
                environment="invalid",
                domain="user",
                category=EnumMessageCategory.EVENT,
            )
        assert "environment" in str(exc_info.value).lower()

    def test_invalid_environment_variations(self):
        """Test various invalid environment values."""
        invalid_envs = [
            "development",  # Not in allowed set
            "production",  # Full word not allowed
            "qa",  # Not in allowed set
            "sandbox",  # Not in allowed set
            "demo",  # Not in allowed set
        ]

        for env in invalid_envs:
            with pytest.raises(ValidationError):
                ModelTopicNaming(
                    environment=env,
                    domain="user",
                    category=EnumMessageCategory.EVENT,
                )


@pytest.mark.unit
class TestModelTopicNamingDomainValidation:
    """Test domain field validation."""

    def test_valid_domains(self):
        """Test valid domain patterns."""
        valid_domains = [
            "user-service",
            "payment",
            "order-management",
            "a",  # Single letter
            "user123",  # With numbers
            "my-service-2",  # With numbers and hyphens
            "x1y2z3",  # Letters and numbers mixed
        ]

        for domain in valid_domains:
            naming = ModelTopicNaming(
                domain=domain,
                category=EnumMessageCategory.EVENT,
            )
            assert naming.domain == domain.lower()

    def test_domain_case_normalization(self):
        """Test that domain is normalized to lowercase."""
        naming = ModelTopicNaming(
            domain="UserService",
            category=EnumMessageCategory.EVENT,
        )
        assert naming.domain == "userservice"

        naming_mixed = ModelTopicNaming(
            domain="PAYMENT-GATEWAY",
            category=EnumMessageCategory.EVENT,
        )
        assert naming_mixed.domain == "payment-gateway"

    def test_invalid_domain_starts_with_number(self):
        """Test that domain starting with number raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelTopicNaming(
                domain="123service",
                category=EnumMessageCategory.EVENT,
            )
        assert "domain" in str(exc_info.value).lower()

    def test_invalid_domain_special_characters(self):
        """Test that domain with special characters raises error."""
        invalid_domains = [
            "user_service",  # Underscore not allowed
            "user.service",  # Dot not allowed
            "user@service",  # @ not allowed
            "user/service",  # Slash not allowed
            "user service",  # Space not allowed
            "user+service",  # Plus not allowed
        ]

        for domain in invalid_domains:
            with pytest.raises(ValidationError):
                ModelTopicNaming(
                    domain=domain,
                    category=EnumMessageCategory.EVENT,
                )

    def test_invalid_domain_empty_string(self):
        """Test that empty domain raises error."""
        with pytest.raises(ValidationError):
            ModelTopicNaming(
                domain="",
                category=EnumMessageCategory.EVENT,
            )


@pytest.mark.unit
class TestModelTopicNamingVersionValidation:
    """Test version field validation."""

    def test_valid_versions(self):
        """Test valid version patterns."""
        valid_versions = ["v1", "v2", "v10", "v100", "v999"]

        for version in valid_versions:
            naming = ModelTopicNaming(
                domain="user",
                category=EnumMessageCategory.EVENT,
                version=version,
            )
            assert naming.version == version

    def test_default_version(self):
        """Test that default version is v1."""
        naming = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.EVENT,
        )
        assert naming.version == "v1"

    def test_invalid_version_patterns(self):
        """Test invalid version patterns."""
        invalid_versions = [
            "1",  # Missing v prefix
            "version1",  # Wrong prefix
            "V1",  # Uppercase V
            "v",  # Missing number
            "v1.0",  # Dot notation not allowed
            "v1-beta",  # Extra suffix not allowed
            "vone",  # Non-numeric
        ]

        for version in invalid_versions:
            with pytest.raises(ValidationError):
                ModelTopicNaming(
                    domain="user",
                    category=EnumMessageCategory.EVENT,
                    version=version,
                )


@pytest.mark.unit
class TestModelTopicNamingTopicName:
    """Test topic_name property."""

    def test_topic_name_format_event(self):
        """Test topic_name format for EVENT category."""
        naming = ModelTopicNaming(
            environment="dev",
            domain="user-service",
            category=EnumMessageCategory.EVENT,
            version="v1",
        )
        assert naming.topic_name == "dev.user-service.events.v1"

    def test_topic_name_format_command(self):
        """Test topic_name format for COMMAND category."""
        naming = ModelTopicNaming(
            environment="prod",
            domain="payment",
            category=EnumMessageCategory.COMMAND,
            version="v2",
        )
        assert naming.topic_name == "prod.payment.commands.v2"

    def test_topic_name_format_intent(self):
        """Test topic_name format for INTENT category."""
        naming = ModelTopicNaming(
            environment="staging",
            domain="order-management",
            category=EnumMessageCategory.INTENT,
            version="v3",
        )
        assert naming.topic_name == "staging.order-management.intents.v3"

    def test_topic_name_all_environments(self):
        """Test topic_name generation for all environments."""
        environments = ["dev", "staging", "prod", "test", "local"]

        for env in environments:
            naming = ModelTopicNaming(
                environment=env,
                domain="user",
                category=EnumMessageCategory.EVENT,
            )
            expected = f"{env}.user.events.v1"
            assert naming.topic_name == expected


@pytest.mark.unit
class TestModelTopicNamingTopicSuffix:
    """Test topic_suffix property."""

    def test_topic_suffix_event(self):
        """Test topic_suffix for EVENT category."""
        naming = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.EVENT,
        )
        assert naming.topic_suffix == "events"

    def test_topic_suffix_command(self):
        """Test topic_suffix for COMMAND category."""
        naming = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.COMMAND,
        )
        assert naming.topic_suffix == "commands"

    def test_topic_suffix_intent(self):
        """Test topic_suffix for INTENT category."""
        naming = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.INTENT,
        )
        assert naming.topic_suffix == "intents"


@pytest.mark.unit
class TestModelTopicNamingParseTopic:
    """Test parse_topic() classmethod."""

    def test_parse_standard_format_event(self):
        """Test parsing standard format: dev.user.events.v1"""
        naming = ModelTopicNaming.parse_topic("dev.user.events.v1")

        assert naming is not None
        assert naming.environment == "dev"
        assert naming.domain == "user"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.version == "v1"

    def test_parse_standard_format_command(self):
        """Test parsing standard format: prod.payment.commands.v2"""
        naming = ModelTopicNaming.parse_topic("prod.payment.commands.v2")

        assert naming is not None
        assert naming.environment == "prod"
        assert naming.domain == "payment"
        assert naming.category == EnumMessageCategory.COMMAND
        assert naming.version == "v2"

    def test_parse_standard_format_intent(self):
        """Test parsing standard format: staging.order.intents.v3"""
        naming = ModelTopicNaming.parse_topic("staging.order.intents.v3")

        assert naming is not None
        assert naming.environment == "staging"
        assert naming.domain == "order"
        assert naming.category == EnumMessageCategory.INTENT
        assert naming.version == "v3"

    def test_parse_without_version(self):
        """Test parsing topic without version: dev.user.events"""
        naming = ModelTopicNaming.parse_topic("dev.user.events")

        assert naming is not None
        assert naming.environment == "dev"
        assert naming.domain == "user"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.version == "v1"  # Default version

    def test_parse_multi_part_domain(self):
        """Test parsing topic with multi-part domain."""
        # Note: The current implementation joins domain parts with dots
        # if there are multiple parts between env and suffix
        naming = ModelTopicNaming.parse_topic("dev.user-service.events.v1")

        assert naming is not None
        assert naming.environment == "dev"
        assert naming.domain == "user-service"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.version == "v1"

    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        naming = ModelTopicNaming.parse_topic("DEV.USER.EVENTS.V1")

        assert naming is not None
        assert naming.environment == "dev"
        assert naming.domain == "user"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.version == "v1"

    def test_parse_invalid_too_few_parts(self):
        """Test parsing invalid topic with too few parts."""
        result = ModelTopicNaming.parse_topic("user.events")
        # Should return None due to too few parts (missing env)
        # or succeed if "user" is treated as env and "events" as suffix
        # Based on implementation, 2 parts returns None
        assert result is None

    def test_parse_invalid_unknown_suffix(self):
        """Test parsing topic with unknown suffix."""
        result = ModelTopicNaming.parse_topic("dev.user.notifications.v1")
        assert result is None

    def test_parse_invalid_empty_string(self):
        """Test parsing empty string."""
        result = ModelTopicNaming.parse_topic("")
        assert result is None

    def test_parse_invalid_single_part(self):
        """Test parsing single-part topic."""
        result = ModelTopicNaming.parse_topic("events")
        assert result is None

    def test_parse_invalid_environment(self):
        """Test parsing topic with invalid environment."""
        result = ModelTopicNaming.parse_topic("invalid.user.events.v1")
        assert result is None

    def test_parse_roundtrip(self):
        """Test that parsing a generated topic_name returns equivalent model."""
        original = ModelTopicNaming(
            environment="prod",
            domain="payment",
            category=EnumMessageCategory.COMMAND,
            version="v2",
        )

        parsed = ModelTopicNaming.parse_topic(original.topic_name)

        assert parsed is not None
        assert parsed.environment == original.environment
        assert parsed.domain == original.domain
        assert parsed.category == original.category
        assert parsed.version == original.version


@pytest.mark.unit
class TestModelTopicNamingFactoryMethods:
    """Test convenience factory methods."""

    def test_for_events_basic(self):
        """Test for_events() with minimal args."""
        naming = ModelTopicNaming.for_events(domain="user")

        assert naming.domain == "user"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.environment == "dev"  # Default
        assert naming.version == "v1"  # Default
        assert naming.topic_name == "dev.user.events.v1"

    def test_for_events_all_args(self):
        """Test for_events() with all args."""
        naming = ModelTopicNaming.for_events(
            domain="payment",
            environment="prod",
            version="v2",
        )

        assert naming.domain == "payment"
        assert naming.category == EnumMessageCategory.EVENT
        assert naming.environment == "prod"
        assert naming.version == "v2"
        assert naming.topic_name == "prod.payment.events.v2"

    def test_for_commands_basic(self):
        """Test for_commands() with minimal args."""
        naming = ModelTopicNaming.for_commands(domain="order")

        assert naming.domain == "order"
        assert naming.category == EnumMessageCategory.COMMAND
        assert naming.environment == "dev"
        assert naming.version == "v1"
        assert naming.topic_name == "dev.order.commands.v1"

    def test_for_commands_all_args(self):
        """Test for_commands() with all args."""
        naming = ModelTopicNaming.for_commands(
            domain="notification",
            environment="staging",
            version="v3",
        )

        assert naming.domain == "notification"
        assert naming.category == EnumMessageCategory.COMMAND
        assert naming.environment == "staging"
        assert naming.version == "v3"
        assert naming.topic_name == "staging.notification.commands.v3"

    def test_for_intents_basic(self):
        """Test for_intents() with minimal args."""
        naming = ModelTopicNaming.for_intents(domain="workflow")

        assert naming.domain == "workflow"
        assert naming.category == EnumMessageCategory.INTENT
        assert naming.environment == "dev"
        assert naming.version == "v1"
        assert naming.topic_name == "dev.workflow.intents.v1"

    def test_for_intents_all_args(self):
        """Test for_intents() with all args."""
        naming = ModelTopicNaming.for_intents(
            domain="automation",
            environment="test",
            version="v4",
        )

        assert naming.domain == "automation"
        assert naming.category == EnumMessageCategory.INTENT
        assert naming.environment == "test"
        assert naming.version == "v4"
        assert naming.topic_name == "test.automation.intents.v4"


@pytest.mark.unit
class TestValidateTopicMatchesCategory:
    """Test validate_topic_matches_category() helper function."""

    def test_validate_event_topic_matches_event_category(self):
        """Test that event topic matches EVENT category."""
        assert (
            validate_topic_matches_category(
                "dev.user.events.v1", EnumMessageCategory.EVENT
            )
            is True
        )

    def test_validate_command_topic_matches_command_category(self):
        """Test that command topic matches COMMAND category."""
        assert (
            validate_topic_matches_category(
                "prod.payment.commands.v1", EnumMessageCategory.COMMAND
            )
            is True
        )

    def test_validate_intent_topic_matches_intent_category(self):
        """Test that intent topic matches INTENT category."""
        assert (
            validate_topic_matches_category(
                "staging.order.intents.v1", EnumMessageCategory.INTENT
            )
            is True
        )

    def test_validate_topic_mismatch(self):
        """Test that mismatched topic/category returns False."""
        # Event topic with COMMAND category
        assert (
            validate_topic_matches_category(
                "dev.user.events.v1", EnumMessageCategory.COMMAND
            )
            is False
        )

        # Command topic with EVENT category
        assert (
            validate_topic_matches_category(
                "dev.user.commands.v1", EnumMessageCategory.EVENT
            )
            is False
        )

        # Intent topic with EVENT category
        assert (
            validate_topic_matches_category(
                "dev.user.intents.v1", EnumMessageCategory.EVENT
            )
            is False
        )

    def test_validate_invalid_topic_returns_false(self):
        """Test that invalid topic returns False (no exceptions)."""
        assert (
            validate_topic_matches_category("invalid-topic", EnumMessageCategory.EVENT)
            is False
        )

        assert validate_topic_matches_category("", EnumMessageCategory.EVENT) is False

    def test_validate_topic_without_version(self):
        """Test validation of topic without version suffix."""
        assert (
            validate_topic_matches_category(
                "dev.user.events", EnumMessageCategory.EVENT
            )
            is True
        )


@pytest.mark.unit
class TestGetTopicCategory:
    """Test get_topic_category() helper function."""

    def test_get_category_from_event_topic(self):
        """Test extracting EVENT category from topic."""
        category = get_topic_category("dev.user.events.v1")
        assert category == EnumMessageCategory.EVENT

    def test_get_category_from_command_topic(self):
        """Test extracting COMMAND category from topic."""
        category = get_topic_category("prod.payment.commands.v2")
        assert category == EnumMessageCategory.COMMAND

    def test_get_category_from_intent_topic(self):
        """Test extracting INTENT category from topic."""
        category = get_topic_category("staging.order.intents.v1")
        assert category == EnumMessageCategory.INTENT

    def test_get_category_topic_without_version(self):
        """Test extracting category from topic without version."""
        assert get_topic_category("dev.user.events") == EnumMessageCategory.EVENT
        assert get_topic_category("dev.user.commands") == EnumMessageCategory.COMMAND
        assert get_topic_category("dev.user.intents") == EnumMessageCategory.INTENT

    def test_get_category_invalid_topic_returns_none(self):
        """Test that invalid topic returns None."""
        assert get_topic_category("invalid-topic") is None
        assert get_topic_category("") is None
        assert get_topic_category("dev.user.notifications.v1") is None

    def test_get_category_case_insensitive(self):
        """Test that category extraction is case-insensitive."""
        assert get_topic_category("DEV.USER.EVENTS.V1") == EnumMessageCategory.EVENT
        assert (
            get_topic_category("PROD.PAYMENT.COMMANDS.V1")
            == EnumMessageCategory.COMMAND
        )


@pytest.mark.unit
class TestModelTopicNamingEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_length_domain(self):
        """Test domain at maximum length boundary."""
        # Domain max_length is 100
        long_domain = "a" * 100
        naming = ModelTopicNaming(
            domain=long_domain,
            category=EnumMessageCategory.EVENT,
        )
        assert len(naming.domain) == 100

    def test_domain_exceeds_max_length(self):
        """Test that domain exceeding max length raises error."""
        long_domain = "a" * 101
        with pytest.raises(ValidationError):
            ModelTopicNaming(
                domain=long_domain,
                category=EnumMessageCategory.EVENT,
            )

    def test_max_length_environment(self):
        """Test environment at maximum length boundary."""
        # Environment max_length is 20, but only specific values are allowed
        # So this test is more about the validator rejecting invalid values
        # even if they're within length limit
        # Valid environments are all well under 20 chars

    def test_single_char_domain(self):
        """Test single character domain."""
        naming = ModelTopicNaming(
            domain="a",
            category=EnumMessageCategory.EVENT,
        )
        assert naming.domain == "a"
        assert naming.topic_name == "dev.a.events.v1"

    def test_domain_with_multiple_hyphens(self):
        """Test domain with multiple consecutive hyphens."""
        naming = ModelTopicNaming(
            domain="user--service",  # Two hyphens
            category=EnumMessageCategory.EVENT,
        )
        assert naming.domain == "user--service"

    def test_domain_ending_with_hyphen(self):
        """Test domain ending with hyphen."""
        naming = ModelTopicNaming(
            domain="user-",
            category=EnumMessageCategory.EVENT,
        )
        assert naming.domain == "user-"

    def test_topic_name_is_deterministic(self):
        """Test that topic_name property returns same value on multiple calls."""
        naming = ModelTopicNaming(
            environment="dev",
            domain="user",
            category=EnumMessageCategory.EVENT,
            version="v1",
        )

        assert naming.topic_name == naming.topic_name == naming.topic_name

    def test_high_version_number(self):
        """Test with high version number."""
        naming = ModelTopicNaming(
            domain="user",
            category=EnumMessageCategory.EVENT,
            version="v999",
        )
        assert naming.version == "v999"
        assert naming.topic_name == "dev.user.events.v999"


@pytest.mark.unit
class TestModelTopicNamingClassVars:
    """Test ClassVar patterns and constants."""

    def test_domain_pattern_exists(self):
        """Test that DOMAIN_PATTERN ClassVar exists and is a regex."""
        assert hasattr(ModelTopicNaming, "DOMAIN_PATTERN")
        import re

        assert isinstance(ModelTopicNaming.DOMAIN_PATTERN, re.Pattern)

    def test_version_pattern_in_field(self):
        """Test that version field has pattern constraint defined."""
        # Version pattern is defined as a Field pattern, not a ClassVar
        # Verify the model schema includes version pattern
        schema = ModelTopicNaming.model_json_schema()
        assert "version" in schema.get("properties", {})
        version_props = schema["properties"]["version"]
        assert "pattern" in version_props
        assert version_props["pattern"] == "^v\\d+$"

    def test_environment_values_exists(self):
        """Test that ENVIRONMENT_VALUES ClassVar exists and contains expected values."""
        assert hasattr(ModelTopicNaming, "ENVIRONMENT_VALUES")
        expected = {"dev", "staging", "prod", "test", "local"}
        assert frozenset(expected) == ModelTopicNaming.ENVIRONMENT_VALUES


@pytest.mark.unit
class TestValidateMessageTopicAlignment:
    """Tests for validate_message_topic_alignment() function."""

    def test_event_topic_with_event_category_passes(self):
        """Event messages to event topics should pass without error."""
        # Should not raise
        validate_message_topic_alignment(
            "dev.user.events.v1",
            EnumMessageCategory.EVENT,
        )

    def test_command_topic_with_command_category_passes(self):
        """Command messages to command topics should pass without error."""
        # Should not raise
        validate_message_topic_alignment(
            "prod.payment.commands.v1",
            EnumMessageCategory.COMMAND,
        )

    def test_intent_topic_with_intent_category_passes(self):
        """Intent messages to intent topics should pass without error."""
        # Should not raise
        validate_message_topic_alignment(
            "staging.order.intents.v1",
            EnumMessageCategory.INTENT,
        )

    def test_topic_without_version_passes(self):
        """Topics without version suffix should pass."""
        # Should not raise
        validate_message_topic_alignment(
            "dev.user.events",
            EnumMessageCategory.EVENT,
        )
        validate_message_topic_alignment(
            "dev.user.commands",
            EnumMessageCategory.COMMAND,
        )

    def test_event_topic_with_command_category_fails(self):
        """Command messages to event topics should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.events.v1",
                EnumMessageCategory.COMMAND,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "mismatch" in str(exc_info.value.message).lower()
        # Context is stored in additional_context["context"]
        context = exc_info.value.context
        assert context is not None
        additional = context.get("additional_context", {})
        nested_context = additional.get("context", {})
        assert nested_context.get("topic") == "dev.user.events.v1"

    def test_event_topic_with_intent_category_fails(self):
        """Intent messages to event topics should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.events.v1",
                EnumMessageCategory.INTENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_command_topic_with_event_category_fails(self):
        """Event messages to command topics should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.commands.v1",
                EnumMessageCategory.EVENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "expected command" in str(exc_info.value.message).lower()

    def test_command_topic_with_intent_category_fails(self):
        """Intent messages to command topics should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "prod.payment.commands.v1",
                EnumMessageCategory.INTENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_intent_topic_with_event_category_fails(self):
        """Event messages to intent topics should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "staging.order.intents.v1",
                EnumMessageCategory.EVENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_intent_topic_with_command_category_fails(self):
        """Command messages to intent topics should raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "test.workflow.intents.v1",
                EnumMessageCategory.COMMAND,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_invalid_topic_fails(self):
        """Topics without valid category suffix should raise error."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "invalid-topic",
                EnumMessageCategory.EVENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "cannot determine" in str(exc_info.value.message).lower()

    def test_empty_topic_fails(self):
        """Empty topic should raise error."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "",
                EnumMessageCategory.EVENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_topic_with_unknown_suffix_fails(self):
        """Topics with unknown suffix should raise error."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.notifications.v1",
                EnumMessageCategory.EVENT,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_context_includes_message_type(self):
        """Error context should include message_type when provided."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.events.v1",
                EnumMessageCategory.COMMAND,
                message_type_name="ProcessOrderCommand",
            )
        context = exc_info.value.context
        assert context is not None
        additional = context.get("additional_context", {})
        nested_context = additional.get("context", {})
        assert nested_context.get("message_type") == "ProcessOrderCommand"

    def test_error_context_without_message_type(self):
        """Error context should handle None message_type."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.events.v1",
                EnumMessageCategory.COMMAND,
            )
        context = exc_info.value.context
        assert context is not None
        additional = context.get("additional_context", {})
        nested_context = additional.get("context", {})
        assert nested_context.get("message_type") is None

    def test_case_insensitive_topic_matching(self):
        """Topic category detection should be case-insensitive."""
        # Should not raise - uppercase should still match
        validate_message_topic_alignment(
            "DEV.USER.EVENTS.V1",
            EnumMessageCategory.EVENT,
        )
        validate_message_topic_alignment(
            "PROD.PAYMENT.COMMANDS.V1",
            EnumMessageCategory.COMMAND,
        )

    def test_all_valid_environments(self):
        """Test validation passes for all valid environment prefixes."""
        environments = ["dev", "staging", "prod", "test", "local"]
        for env in environments:
            validate_message_topic_alignment(
                f"{env}.user.events.v1",
                EnumMessageCategory.EVENT,
            )
            validate_message_topic_alignment(
                f"{env}.user.commands.v1",
                EnumMessageCategory.COMMAND,
            )
            validate_message_topic_alignment(
                f"{env}.user.intents.v1",
                EnumMessageCategory.INTENT,
            )

    def test_error_message_contains_expected_and_actual(self):
        """Error message should contain both expected and actual category."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_message_topic_alignment(
                "dev.user.events.v1",
                EnumMessageCategory.COMMAND,
            )
        error_msg = str(exc_info.value.message)
        assert "event" in error_msg.lower()
        assert "command" in error_msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
