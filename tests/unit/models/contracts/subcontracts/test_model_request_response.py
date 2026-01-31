"""
Tests for request-response models (OMN-1760).

Comprehensive tests for ModelCorrelationConfig, ModelReplyTopics,
ModelRequestResponseInstance, and ModelRequestResponseConfig.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_correlation_config import (
    ModelCorrelationConfig,
)
from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_reply_topics import (
    ModelReplyTopics,
)
from omnibase_core.models.contracts.subcontracts.model_request_response_config import (
    ModelRequestResponseConfig,
)
from omnibase_core.models.contracts.subcontracts.model_request_response_instance import (
    ModelRequestResponseInstance,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Valid topic suffixes for testing
VALID_REQUEST_TOPIC = "onex.cmd.user-service.create-account.v1"
VALID_COMPLETED_TOPIC = "onex.evt.user-service.account-created.v1"
VALID_FAILED_TOPIC = "onex.evt.user-service.account-creation-failed.v1"

# Invalid topic suffixes for testing
INVALID_TOPIC_NO_PREFIX = "invalid-topic"
INVALID_TOPIC_ENV_PREFIX = "dev.onex.evt.service.response.v1"
INVALID_TOPIC_UPPERCASE = "ONEX.EVT.SERVICE.EVENT.V1"
INVALID_TOPIC_WRONG_SEGMENTS = "onex.evt.service.v1"

# Default version for ModelEventBusSubcontract
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# ModelCorrelationConfig Tests
# =============================================================================


@pytest.mark.unit
class TestModelCorrelationConfigDefaults:
    """Test ModelCorrelationConfig default values."""

    def test_defaults_applied_correctly(self):
        """Test that defaults are applied when no values provided."""
        config = ModelCorrelationConfig()
        assert config.location == "body"
        assert config.field == "correlation_id"

    def test_default_location_is_body(self):
        """Test that default location is 'body'."""
        config = ModelCorrelationConfig()
        assert config.location == "body"

    def test_default_field_is_correlation_id(self):
        """Test that default field is 'correlation_id'."""
        config = ModelCorrelationConfig()
        assert config.field == "correlation_id"


@pytest.mark.unit
class TestModelCorrelationConfigCustomValues:
    """Test ModelCorrelationConfig with custom values."""

    def test_custom_location_body_accepted(self):
        """Test that 'body' location is accepted."""
        config = ModelCorrelationConfig(location="body")
        assert config.location == "body"

    def test_custom_location_headers_accepted(self):
        """Test that 'headers' location is accepted."""
        config = ModelCorrelationConfig(location="headers")
        assert config.location == "headers"

    def test_custom_field_accepted(self):
        """Test that custom field name is accepted."""
        config = ModelCorrelationConfig(field="request_id")
        assert config.field == "request_id"

    def test_custom_location_and_field_accepted(self):
        """Test that both custom location and field are accepted."""
        config = ModelCorrelationConfig(location="headers", field="x-correlation-id")
        assert config.location == "headers"
        assert config.field == "x-correlation-id"


@pytest.mark.unit
class TestModelCorrelationConfigValidation:
    """Test ModelCorrelationConfig validation."""

    def test_invalid_location_rejected(self):
        """Test that invalid location literal is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCorrelationConfig(location="query")  # type: ignore[arg-type]
        assert "location" in str(exc_info.value).lower()

    def test_location_literal_validation_accepts_body(self):
        """Test location literal validation accepts 'body'."""
        config = ModelCorrelationConfig(location="body")
        assert config.location == "body"

    def test_location_literal_validation_accepts_headers(self):
        """Test location literal validation accepts 'headers'."""
        config = ModelCorrelationConfig(location="headers")
        assert config.location == "headers"


@pytest.mark.unit
class TestModelCorrelationConfigImmutability:
    """Test ModelCorrelationConfig frozen behavior."""

    def test_model_is_frozen(self):
        """Test that the model is frozen (immutable)."""
        config = ModelCorrelationConfig()
        with pytest.raises((ValidationError, TypeError)):
            config.location = "headers"  # type: ignore[misc]

    def test_model_is_hashable(self):
        """Test that frozen model is hashable."""
        config = ModelCorrelationConfig()
        # Frozen models should be hashable
        hash_value = hash(config)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelCorrelationConfigSerialization:
    """Test ModelCorrelationConfig serialization."""

    def test_model_dump(self):
        """Test model_dump returns correct dict."""
        config = ModelCorrelationConfig(location="headers", field="x-request-id")
        data = config.model_dump()
        assert data["location"] == "headers"
        assert data["field"] == "x-request-id"

    def test_model_validate(self):
        """Test model_validate creates correct model."""
        data = {"location": "headers", "field": "trace_id"}
        config = ModelCorrelationConfig.model_validate(data)
        assert config.location == "headers"
        assert config.field == "trace_id"

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip."""
        original = ModelCorrelationConfig(location="headers", field="my_correlation")
        data = original.model_dump()
        restored = ModelCorrelationConfig.model_validate(data)
        assert restored == original


# =============================================================================
# ModelReplyTopics Tests
# =============================================================================


@pytest.mark.unit
class TestModelReplyTopicsRequiredFields:
    """Test ModelReplyTopics required fields."""

    def test_completed_is_required(self):
        """Test that 'completed' field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(failed=VALID_FAILED_TOPIC)  # type: ignore[call-arg]
        assert "completed" in str(exc_info.value).lower()

    def test_failed_is_required(self):
        """Test that 'failed' field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(completed=VALID_COMPLETED_TOPIC)  # type: ignore[call-arg]
        assert "failed" in str(exc_info.value).lower()

    def test_both_fields_required(self):
        """Test that both fields are required - empty construction fails."""
        with pytest.raises(ValidationError):
            ModelReplyTopics()  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelReplyTopicsValidTopics:
    """Test ModelReplyTopics with valid topic suffixes."""

    def test_valid_topic_suffixes_accepted(self):
        """Test that valid ONEX topic suffixes are accepted."""
        topics = ModelReplyTopics(
            completed=VALID_COMPLETED_TOPIC,
            failed=VALID_FAILED_TOPIC,
        )
        assert topics.completed == VALID_COMPLETED_TOPIC
        assert topics.failed == VALID_FAILED_TOPIC

    def test_valid_cmd_topic_suffix_accepted(self):
        """Test that valid cmd topic suffixes are accepted."""
        topics = ModelReplyTopics(
            completed="onex.cmd.service.response-completed.v1",
            failed="onex.cmd.service.response-failed.v1",
        )
        assert topics.completed == "onex.cmd.service.response-completed.v1"
        assert topics.failed == "onex.cmd.service.response-failed.v1"

    def test_valid_evt_topic_suffix_accepted(self):
        """Test that valid evt topic suffixes are accepted."""
        topics = ModelReplyTopics(
            completed="onex.evt.myservice.task-done.v2",
            failed="onex.evt.myservice.task-error.v2",
        )
        assert topics.completed == "onex.evt.myservice.task-done.v2"


@pytest.mark.unit
class TestModelReplyTopicsInvalidTopics:
    """Test ModelReplyTopics topic validation rejects invalid topics."""

    def test_invalid_completed_topic_rejected_no_prefix(self):
        """Test that invalid completed topic without prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(
                completed=INVALID_TOPIC_NO_PREFIX,
                failed=VALID_FAILED_TOPIC,
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()

    def test_invalid_failed_topic_rejected_no_prefix(self):
        """Test that invalid failed topic without prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=INVALID_TOPIC_NO_PREFIX,
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()

    def test_invalid_topic_rejected_with_env_prefix(self):
        """Test that topic with environment prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(
                completed=INVALID_TOPIC_ENV_PREFIX,
                failed=VALID_FAILED_TOPIC,
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()

    def test_invalid_topic_rejected_uppercase(self):
        """Test that uppercase topic is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(
                completed=INVALID_TOPIC_UPPERCASE,
                failed=VALID_FAILED_TOPIC,
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()

    def test_invalid_topic_rejected_wrong_segments(self):
        """Test that topic with wrong segment count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReplyTopics(
                completed=INVALID_TOPIC_WRONG_SEGMENTS,
                failed=VALID_FAILED_TOPIC,
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelReplyTopicsSerialization:
    """Test ModelReplyTopics serialization."""

    def test_model_dump(self):
        """Test model_dump returns correct dict."""
        topics = ModelReplyTopics(
            completed=VALID_COMPLETED_TOPIC,
            failed=VALID_FAILED_TOPIC,
        )
        data = topics.model_dump()
        assert data["completed"] == VALID_COMPLETED_TOPIC
        assert data["failed"] == VALID_FAILED_TOPIC

    def test_model_validate(self):
        """Test model_validate creates correct model."""
        data = {"completed": VALID_COMPLETED_TOPIC, "failed": VALID_FAILED_TOPIC}
        topics = ModelReplyTopics.model_validate(data)
        assert topics.completed == VALID_COMPLETED_TOPIC
        assert topics.failed == VALID_FAILED_TOPIC

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip."""
        original = ModelReplyTopics(
            completed=VALID_COMPLETED_TOPIC,
            failed=VALID_FAILED_TOPIC,
        )
        data = original.model_dump()
        restored = ModelReplyTopics.model_validate(data)
        assert restored.completed == original.completed
        assert restored.failed == original.failed


# =============================================================================
# ModelRequestResponseInstance Tests
# =============================================================================


@pytest.mark.unit
class TestModelRequestResponseInstanceDefaults:
    """Test ModelRequestResponseInstance default values."""

    def test_all_defaults_applied(self):
        """Test that all defaults are applied correctly."""
        instance = ModelRequestResponseInstance(
            name="test-instance",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        assert instance.correlation is None
        assert instance.timeout_seconds == 30
        assert instance.consumer_group_mode == "per_instance"
        assert instance.auto_offset_reset == "earliest"

    def test_default_correlation_is_none(self):
        """Test that default correlation is None."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        assert instance.correlation is None

    def test_default_timeout_seconds_is_30(self):
        """Test that default timeout_seconds is 30."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        assert instance.timeout_seconds == 30

    def test_default_consumer_group_mode_is_per_instance(self):
        """Test that default consumer_group_mode is 'per_instance'."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        assert instance.consumer_group_mode == "per_instance"

    def test_default_auto_offset_reset_is_earliest(self):
        """Test that default auto_offset_reset is 'earliest'."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        assert instance.auto_offset_reset == "earliest"


@pytest.mark.unit
class TestModelRequestResponseInstanceTopicValidation:
    """Test ModelRequestResponseInstance topic validation."""

    def test_valid_request_topic_accepted(self):
        """Test that valid request topic is accepted."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        assert instance.request_topic == VALID_REQUEST_TOPIC

    def test_invalid_request_topic_rejected_no_prefix(self):
        """Test that invalid request topic without prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequestResponseInstance(
                name="test",
                request_topic=INVALID_TOPIC_NO_PREFIX,
                reply_topics=ModelReplyTopics(
                    completed=VALID_COMPLETED_TOPIC,
                    failed=VALID_FAILED_TOPIC,
                ),
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()

    def test_invalid_request_topic_rejected_env_prefix(self):
        """Test that request topic with environment prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequestResponseInstance(
                name="test",
                request_topic=INVALID_TOPIC_ENV_PREFIX,
                reply_topics=ModelReplyTopics(
                    completed=VALID_COMPLETED_TOPIC,
                    failed=VALID_FAILED_TOPIC,
                ),
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()

    def test_invalid_request_topic_rejected_uppercase(self):
        """Test that uppercase request topic is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequestResponseInstance(
                name="test",
                request_topic=INVALID_TOPIC_UPPERCASE,
                reply_topics=ModelReplyTopics(
                    completed=VALID_COMPLETED_TOPIC,
                    failed=VALID_FAILED_TOPIC,
                ),
            )
        assert "invalid topic suffix" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelRequestResponseInstanceFullCreation:
    """Test ModelRequestResponseInstance full creation with all fields."""

    def test_full_instance_creation_with_all_fields(self):
        """Test creating instance with all fields specified."""
        correlation = ModelCorrelationConfig(location="headers", field="x-request-id")
        reply_topics = ModelReplyTopics(
            completed=VALID_COMPLETED_TOPIC,
            failed=VALID_FAILED_TOPIC,
        )

        instance = ModelRequestResponseInstance(
            name="my-rpc-instance",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=reply_topics,
            correlation=correlation,
            timeout_seconds=60,
            consumer_group_mode="shared",
            auto_offset_reset="latest",
        )

        assert instance.name == "my-rpc-instance"
        assert instance.request_topic == VALID_REQUEST_TOPIC
        assert instance.reply_topics == reply_topics
        assert instance.correlation == correlation
        assert instance.timeout_seconds == 60
        assert instance.consumer_group_mode == "shared"
        assert instance.auto_offset_reset == "latest"

    def test_consumer_group_mode_per_instance_accepted(self):
        """Test that consumer_group_mode 'per_instance' is accepted."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            consumer_group_mode="per_instance",
        )
        assert instance.consumer_group_mode == "per_instance"

    def test_consumer_group_mode_shared_accepted(self):
        """Test that consumer_group_mode 'shared' is accepted."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            consumer_group_mode="shared",
        )
        assert instance.consumer_group_mode == "shared"

    def test_auto_offset_reset_earliest_accepted(self):
        """Test that auto_offset_reset 'earliest' is accepted."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            auto_offset_reset="earliest",
        )
        assert instance.auto_offset_reset == "earliest"

    def test_auto_offset_reset_latest_accepted(self):
        """Test that auto_offset_reset 'latest' is accepted."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            auto_offset_reset="latest",
        )
        assert instance.auto_offset_reset == "latest"

    def test_timeout_seconds_minimum_value(self):
        """Test that timeout_seconds minimum value (1) is accepted."""
        instance = ModelRequestResponseInstance(
            name="test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            timeout_seconds=1,
        )
        assert instance.timeout_seconds == 1

    def test_timeout_seconds_below_minimum_rejected(self):
        """Test that timeout_seconds below minimum is rejected."""
        with pytest.raises(ValidationError):
            ModelRequestResponseInstance(
                name="test",
                request_topic=VALID_REQUEST_TOPIC,
                reply_topics=ModelReplyTopics(
                    completed=VALID_COMPLETED_TOPIC,
                    failed=VALID_FAILED_TOPIC,
                ),
                timeout_seconds=0,
            )


@pytest.mark.unit
class TestModelRequestResponseInstanceSerialization:
    """Test ModelRequestResponseInstance serialization."""

    def test_model_dump(self):
        """Test model_dump returns correct dict."""
        instance = ModelRequestResponseInstance(
            name="test-instance",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            timeout_seconds=45,
        )
        data = instance.model_dump()
        assert data["name"] == "test-instance"
        assert data["request_topic"] == VALID_REQUEST_TOPIC
        assert data["timeout_seconds"] == 45

    def test_model_validate(self):
        """Test model_validate creates correct model."""
        data = {
            "name": "validated-instance",
            "request_topic": VALID_REQUEST_TOPIC,
            "reply_topics": {
                "completed": VALID_COMPLETED_TOPIC,
                "failed": VALID_FAILED_TOPIC,
            },
        }
        instance = ModelRequestResponseInstance.model_validate(data)
        assert instance.name == "validated-instance"
        assert instance.request_topic == VALID_REQUEST_TOPIC

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip."""
        original = ModelRequestResponseInstance(
            name="roundtrip-test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            correlation=ModelCorrelationConfig(location="headers", field="trace-id"),
            timeout_seconds=120,
            consumer_group_mode="shared",
            auto_offset_reset="latest",
        )
        data = original.model_dump()
        restored = ModelRequestResponseInstance.model_validate(data)
        assert restored.name == original.name
        assert restored.request_topic == original.request_topic
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.consumer_group_mode == original.consumer_group_mode
        assert restored.auto_offset_reset == original.auto_offset_reset


# =============================================================================
# ModelRequestResponseConfig Tests
# =============================================================================


@pytest.mark.unit
class TestModelRequestResponseConfigValidInstances:
    """Test ModelRequestResponseConfig with valid instances."""

    def test_valid_config_with_one_instance(self):
        """Test valid config with one instance."""
        instance = ModelRequestResponseInstance(
            name="single-instance",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        config = ModelRequestResponseConfig(instances=[instance])
        assert len(config.instances) == 1
        assert config.instances[0].name == "single-instance"

    def test_valid_config_with_multiple_instances(self):
        """Test valid config with multiple instances."""
        instance1 = ModelRequestResponseInstance(
            name="instance-1",
            request_topic="onex.cmd.service-a.request.v1",
            reply_topics=ModelReplyTopics(
                completed="onex.evt.service-a.completed.v1",
                failed="onex.evt.service-a.failed.v1",
            ),
        )
        instance2 = ModelRequestResponseInstance(
            name="instance-2",
            request_topic="onex.cmd.service-b.request.v1",
            reply_topics=ModelReplyTopics(
                completed="onex.evt.service-b.completed.v1",
                failed="onex.evt.service-b.failed.v1",
            ),
        )
        config = ModelRequestResponseConfig(instances=[instance1, instance2])
        assert len(config.instances) == 2
        assert config.instances[0].name == "instance-1"
        assert config.instances[1].name == "instance-2"


@pytest.mark.unit
class TestModelRequestResponseConfigEmptyInstancesRejection:
    """Test that empty instances list is rejected - CRITICAL test."""

    def test_empty_instances_list_rejected(self):
        """Test that empty instances list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequestResponseConfig(instances=[])
        assert "must contain at least one instance" in str(exc_info.value)

    def test_empty_instances_list_rejected_via_model_validate(self):
        """Test that empty instances list is rejected via model_validate."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRequestResponseConfig.model_validate({"instances": []})
        assert "must contain at least one instance" in str(exc_info.value)


@pytest.mark.unit
class TestModelRequestResponseConfigSerialization:
    """Test ModelRequestResponseConfig serialization."""

    def test_model_dump(self):
        """Test model_dump returns correct dict."""
        instance = ModelRequestResponseInstance(
            name="dump-test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        config = ModelRequestResponseConfig(instances=[instance])
        data = config.model_dump()
        assert "instances" in data
        assert len(data["instances"]) == 1
        assert data["instances"][0]["name"] == "dump-test"

    def test_model_validate(self):
        """Test model_validate creates correct model."""
        data = {
            "instances": [
                {
                    "name": "validate-test",
                    "request_topic": VALID_REQUEST_TOPIC,
                    "reply_topics": {
                        "completed": VALID_COMPLETED_TOPIC,
                        "failed": VALID_FAILED_TOPIC,
                    },
                }
            ]
        }
        config = ModelRequestResponseConfig.model_validate(data)
        assert len(config.instances) == 1
        assert config.instances[0].name == "validate-test"

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip."""
        instance = ModelRequestResponseInstance(
            name="roundtrip",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            timeout_seconds=90,
        )
        original = ModelRequestResponseConfig(instances=[instance])
        data = original.model_dump()
        restored = ModelRequestResponseConfig.model_validate(data)
        assert len(restored.instances) == len(original.instances)
        assert restored.instances[0].name == original.instances[0].name
        assert (
            restored.instances[0].timeout_seconds
            == original.instances[0].timeout_seconds
        )


# =============================================================================
# Integration with ModelEventBusSubcontract Tests
# =============================================================================


@pytest.mark.unit
class TestModelEventBusSubcontractRequestResponseIntegration:
    """Test integration of request_response with ModelEventBusSubcontract."""

    def test_request_response_none_default(self):
        """Test that request_response defaults to None."""
        subcontract = ModelEventBusSubcontract(version=DEFAULT_VERSION)
        assert subcontract.request_response is None

    def test_request_response_with_valid_config(self):
        """Test request_response with valid config."""
        instance = ModelRequestResponseInstance(
            name="integration-test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )
        request_response_config = ModelRequestResponseConfig(instances=[instance])

        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            request_response=request_response_config,
        )
        assert subcontract.request_response is not None
        assert len(subcontract.request_response.instances) == 1
        assert subcontract.request_response.instances[0].name == "integration-test"

    def test_request_response_serialization_roundtrip(self):
        """Test serialization roundtrip with request_response config."""
        instance = ModelRequestResponseInstance(
            name="serialization-test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
            correlation=ModelCorrelationConfig(location="headers", field="x-trace-id"),
            timeout_seconds=45,
        )
        request_response_config = ModelRequestResponseConfig(instances=[instance])

        original = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            event_bus_type="distributed",
            request_response=request_response_config,
        )

        data = original.model_dump()
        restored = ModelEventBusSubcontract.model_validate(data)

        assert restored.request_response is not None
        assert len(restored.request_response.instances) == 1
        assert restored.request_response.instances[0].name == "serialization-test"
        assert restored.request_response.instances[0].timeout_seconds == 45
        assert restored.request_response.instances[0].correlation is not None
        assert restored.request_response.instances[0].correlation.location == "headers"

    def test_request_response_none_serialization_roundtrip(self):
        """Test serialization roundtrip when request_response is None."""
        original = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            event_bus_type="memory",
        )

        data = original.model_dump()
        restored = ModelEventBusSubcontract.model_validate(data)

        assert restored.request_response is None
        assert restored.event_bus_type == "memory"

    def test_request_response_with_multiple_instances(self):
        """Test request_response with multiple instances in subcontract."""
        instances = [
            ModelRequestResponseInstance(
                name=f"instance-{i}",
                request_topic=f"onex.cmd.service-{i}.request.v1",
                reply_topics=ModelReplyTopics(
                    completed=f"onex.evt.service-{i}.completed.v1",
                    failed=f"onex.evt.service-{i}.failed.v1",
                ),
            )
            for i in range(3)
        ]
        config = ModelRequestResponseConfig(instances=instances)

        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            request_response=config,
        )

        assert subcontract.request_response is not None
        assert len(subcontract.request_response.instances) == 3
        for i, inst in enumerate(subcontract.request_response.instances):
            assert inst.name == f"instance-{i}"


@pytest.mark.unit
class TestModelEventBusSubcontractRequestResponseEdgeCases:
    """Test edge cases for request_response integration."""

    def test_extra_fields_in_request_response_config_ignored(self):
        """Test that extra fields in request_response config are ignored."""
        data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "request_response": {
                "instances": [
                    {
                        "name": "test",
                        "request_topic": VALID_REQUEST_TOPIC,
                        "reply_topics": {
                            "completed": VALID_COMPLETED_TOPIC,
                            "failed": VALID_FAILED_TOPIC,
                        },
                        "extra_field_should_be_ignored": "value",
                    }
                ],
                "another_extra_field": "ignored",
            },
        }
        subcontract = ModelEventBusSubcontract.model_validate(data)
        assert subcontract.request_response is not None
        assert len(subcontract.request_response.instances) == 1

    def test_request_response_coexists_with_topic_lists(self):
        """Test that request_response works with publish/subscribe topics."""
        instance = ModelRequestResponseInstance(
            name="coexist-test",
            request_topic=VALID_REQUEST_TOPIC,
            reply_topics=ModelReplyTopics(
                completed=VALID_COMPLETED_TOPIC,
                failed=VALID_FAILED_TOPIC,
            ),
        )

        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            publish_topics=["onex.evt.my-service.data-updated.v1"],
            subscribe_topics=["onex.cmd.my-service.process-data.v1"],
            request_response=ModelRequestResponseConfig(instances=[instance]),
        )

        assert len(subcontract.publish_topics) == 1
        assert len(subcontract.subscribe_topics) == 1
        assert subcontract.request_response is not None
