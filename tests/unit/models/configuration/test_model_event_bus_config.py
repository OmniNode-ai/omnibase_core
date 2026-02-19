# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelEventBusConfig.

Comprehensive tests for event bus configuration.
"""

import os
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from omnibase_core.models.configuration.model_event_bus_config import (
    ModelEventBusConfig,
)


@pytest.mark.unit
class TestModelEventBusConfigInitialization:
    """Test ModelEventBusConfig initialization."""

    def test_create_event_bus_config(self):
        """Test creating event bus config."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        assert config is not None
        assert isinstance(config, ModelEventBusConfig)
        assert config.bootstrap_servers == ["localhost:9092"]
        assert config.topics == ["test-topic"]

    def test_event_bus_config_with_security(self):
        """Test creating event bus config with security settings."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
            security_protocol="SASL_SSL",
            sasl_mechanism="SCRAM-SHA-256",
            sasl_username="user",
            sasl_password=SecretStr("password"),
        )
        assert config.security_protocol == "SASL_SSL"
        assert config.sasl_mechanism == "SCRAM-SHA-256"
        assert config.sasl_username == "user"
        assert config.sasl_password is not None

    def test_event_bus_config_inheritance(self):
        """Test that ModelEventBusConfig inherits from BaseModel."""
        from pydantic import BaseModel

        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        assert isinstance(config, BaseModel)


@pytest.mark.unit
class TestModelEventBusConfigValidation:
    """Test ModelEventBusConfig field validation."""

    def test_bootstrap_servers_required(self):
        """Test bootstrap_servers is required."""
        with pytest.raises(ValueError):
            ModelEventBusConfig(topics=["test-topic"])

    def test_topics_required(self):
        """Test topics is required."""
        with pytest.raises(ValueError):
            ModelEventBusConfig(bootstrap_servers=["localhost:9092"])

    def test_acks_default_value(self):
        """Test acks default value."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        assert config.acks == "all"

    def test_enable_auto_commit_default(self):
        """Test enable_auto_commit default value."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        assert config.enable_auto_commit is True

    def test_auto_offset_reset_default(self):
        """Test auto_offset_reset default value."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        assert config.auto_offset_reset == "earliest"


@pytest.mark.unit
class TestModelEventBusConfigSerialization:
    """Test ModelEventBusConfig serialization."""

    def test_event_bus_config_serialization(self):
        """Test event bus config model_dump."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
            security_protocol="PLAINTEXT",
        )
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["bootstrap_servers"] == ["localhost:9092"]
        assert data["topics"] == ["test-topic"]
        assert data["security_protocol"] == "PLAINTEXT"

    def test_event_bus_config_deserialization(self):
        """Test event bus config model_validate."""
        data = {
            "bootstrap_servers": ["localhost:9092"],
            "topics": ["test-topic"],
        }
        config = ModelEventBusConfig.model_validate(data)
        assert config.bootstrap_servers == ["localhost:9092"]
        assert config.topics == ["test-topic"]

    def test_event_bus_config_json_serialization(self):
        """Test event bus config JSON serialization."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        json_data = config.model_dump_json()
        assert isinstance(json_data, str)
        assert "bootstrap_servers" in json_data
        assert "topics" in json_data

    def test_event_bus_config_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092", "localhost:9093"],
            topics=["topic1", "topic2"],
            security_protocol="PLAINTEXT",
        )
        data = original.model_dump()
        restored = ModelEventBusConfig.model_validate(data)
        assert restored.bootstrap_servers == original.bootstrap_servers
        assert restored.topics == original.topics
        assert restored.security_protocol == original.security_protocol


@pytest.mark.unit
class TestModelEventBusConfigMethods:
    """Test ModelEventBusConfig methods."""

    def test_get_sasl_password_value_with_password(self):
        """Test getting SASL password value."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
            sasl_password=SecretStr("secret123"),
        )
        password = config.get_sasl_password_value()
        assert password == "secret123"

    def test_get_sasl_password_value_without_password(self):
        """Test getting SASL password value when None."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        password = config.get_sasl_password_value()
        assert password is None

    def test_apply_environment_overrides_bootstrap_servers(self):
        """Test applying environment overrides for bootstrap servers."""
        os.environ["ONEX_EVENT_BUS_BOOTSTRAP_SERVERS"] = "server1:9092,server2:9092"
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        updated = config.apply_environment_overrides()
        assert updated.bootstrap_servers == ["server1:9092", "server2:9092"]
        del os.environ["ONEX_EVENT_BUS_BOOTSTRAP_SERVERS"]

    def test_apply_environment_overrides_topics(self):
        """Test applying environment overrides for topics."""
        os.environ["ONEX_EVENT_BUS_TOPICS"] = "topic1,topic2,topic3"
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        updated = config.apply_environment_overrides()
        assert updated.topics == ["topic1", "topic2", "topic3"]
        del os.environ["ONEX_EVENT_BUS_TOPICS"]

    def test_apply_environment_overrides_security(self):
        """Test applying environment overrides for security settings."""
        os.environ["ONEX_EVENT_BUS_SECURITY_PROTOCOL"] = "SASL_SSL"
        os.environ["ONEX_EVENT_BUS_SASL_MECHANISM"] = "SCRAM-SHA-256"
        os.environ["ONEX_EVENT_BUS_SASL_USERNAME"] = "testuser"
        os.environ["ONEX_EVENT_BUS_SASL_PASSWORD"] = "testpass"

        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        updated = config.apply_environment_overrides()
        assert updated.security_protocol == "SASL_SSL"
        assert updated.sasl_mechanism == "SCRAM-SHA-256"
        assert updated.sasl_username == "testuser"
        assert updated.get_sasl_password_value() == "testpass"

        del os.environ["ONEX_EVENT_BUS_SECURITY_PROTOCOL"]
        del os.environ["ONEX_EVENT_BUS_SASL_MECHANISM"]
        del os.environ["ONEX_EVENT_BUS_SASL_USERNAME"]
        del os.environ["ONEX_EVENT_BUS_SASL_PASSWORD"]

    def test_apply_environment_overrides_integers(self):
        """Test applying environment overrides for integer fields."""
        os.environ["ONEX_EVENT_BUS_PARTITIONS"] = "5"
        os.environ["ONEX_EVENT_BUS_REPLICATION_FACTOR"] = "3"

        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        updated = config.apply_environment_overrides()
        assert updated.partitions == 5
        assert updated.replication_factor == 3

        del os.environ["ONEX_EVENT_BUS_PARTITIONS"]
        del os.environ["ONEX_EVENT_BUS_REPLICATION_FACTOR"]

    def test_apply_environment_overrides_boolean(self):
        """Test applying environment overrides for boolean fields."""
        os.environ["ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT"] = "false"

        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        updated = config.apply_environment_overrides()
        assert updated.enable_auto_commit is False

        del os.environ["ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT"]

    def test_apply_environment_overrides_no_changes(self):
        """Test applying environment overrides with no env vars set."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        updated = config.apply_environment_overrides()
        assert updated.bootstrap_servers == config.bootstrap_servers
        assert updated.topics == config.topics


@pytest.mark.unit
class TestModelEventBusConfigFactoryMethods:
    """Test ModelEventBusConfig factory methods."""

    def test_default_factory_method(self):
        """Test default factory method."""
        config = ModelEventBusConfig.default()
        assert config.bootstrap_servers == ["localhost:9092"]
        assert config.topics == ["onex-default"]
        assert config.security_protocol == "PLAINTEXT"
        assert config.group_id is not None
        assert isinstance(config.group_id, UUID)


@pytest.mark.unit
class TestModelEventBusConfigEdgeCases:
    """Test event bus config edge cases."""

    def test_multiple_bootstrap_servers(self):
        """Test configuration with multiple bootstrap servers."""
        config = ModelEventBusConfig(
            bootstrap_servers=["server1:9092", "server2:9092", "server3:9092"],
            topics=["test-topic"],
        )
        assert len(config.bootstrap_servers) == 3

    def test_multiple_topics(self):
        """Test configuration with multiple topics."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["topic1", "topic2", "topic3"],
        )
        assert len(config.topics) == 3

    def test_ssl_file_paths(self):
        """Test SSL file path configuration."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
            ssl_cafile="/path/to/ca.pem",
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
        )
        assert config.ssl_cafile == "/path/to/ca.pem"
        assert config.ssl_certfile == "/path/to/cert.pem"
        assert config.ssl_keyfile == "/path/to/key.pem"

    def test_custom_client_and_group_ids(self):
        """Test custom client and group IDs."""
        client_id = uuid4()
        group_id = uuid4()
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
            client_id=client_id,
            group_id=group_id,
        )
        assert config.client_id == client_id
        assert config.group_id == group_id


@pytest.mark.unit
class TestModelEventBusConfigAttributes:
    """Test event bus config attributes and metadata."""

    def test_event_bus_config_attributes(self):
        """Test that event bus config has expected attributes."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        assert hasattr(config, "model_dump")
        assert callable(config.model_dump)
        assert hasattr(ModelEventBusConfig, "model_validate")
        assert callable(ModelEventBusConfig.model_validate)

    def test_event_bus_config_docstring(self):
        """Test event bus config docstring."""
        assert ModelEventBusConfig.__doc__ is not None
        assert "event bus" in ModelEventBusConfig.__doc__.lower()

    def test_event_bus_config_class_name(self):
        """Test event bus config class name."""
        assert ModelEventBusConfig.__name__ == "ModelEventBusConfig"

    def test_event_bus_config_module(self):
        """Test event bus config module."""
        assert (
            ModelEventBusConfig.__module__
            == "omnibase_core.models.configuration.model_event_bus_config"
        )

    def test_event_bus_config_copy(self):
        """Test event bus config copying."""
        config = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        copied = config.model_copy()
        assert copied is not None
        assert copied.bootstrap_servers == config.bootstrap_servers
        assert copied is not config

    def test_event_bus_config_equality(self):
        """Test event bus config equality."""
        config1 = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        config2 = ModelEventBusConfig(
            bootstrap_servers=["localhost:9092"],
            topics=["test-topic"],
        )
        # Note: equality may differ due to UUID fields, so just test structure
        assert config1.bootstrap_servers == config2.bootstrap_servers
        assert config1.topics == config2.topics
