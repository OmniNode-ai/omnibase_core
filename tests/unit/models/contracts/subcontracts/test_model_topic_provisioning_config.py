# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelTopicProvisioningConfig and per-topic config carry on ModelTopicMeta.

Covers OMN-13300: per-topic ``topic_config`` (partitions, replication_factor,
kafka_config) is OPTIONAL, contract-loadable at the
``event_bus.publish_topics`` / ``subscribe_topics`` declaration site (via
``ModelEventBusSubcontract.publish_topic_metadata`` keyed by suffix), frozen,
``extra="forbid"``, PEP 604 unions, and defaults to None (defer to platform
``ModelTopicSpec`` defaults) when absent.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_topic_meta import ModelTopicMeta
from omnibase_core.models.contracts.subcontracts.model_topic_provisioning_config import (
    ModelTopicProvisioningConfig,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)
VALID_SUFFIX = "onex.evt.platform.node-registration.v1"


@pytest.mark.unit
class TestModelTopicProvisioningConfigDefaults:
    """All fields optional; absent => None => defer to platform defaults."""

    def test_all_fields_default_to_none(self):
        config = ModelTopicProvisioningConfig()
        assert config.partitions is None
        assert config.replication_factor is None
        assert config.kafka_config is None

    def test_explicit_values(self):
        config = ModelTopicProvisioningConfig(
            partitions=1,
            replication_factor=3,
            kafka_config={
                "cleanup.policy": "compact",
                "retention.ms": "604800000",
            },
        )
        assert config.partitions == 1
        assert config.replication_factor == 3
        assert config.kafka_config == {
            "cleanup.policy": "compact",
            "retention.ms": "604800000",
        }

    def test_partial_values_leave_rest_none(self):
        config = ModelTopicProvisioningConfig(partitions=12)
        assert config.partitions == 12
        assert config.replication_factor is None
        assert config.kafka_config is None


@pytest.mark.unit
class TestModelTopicProvisioningConfigConstraints:
    """Strict validation: frozen, extra=forbid, ge=1 bounds, typed kafka_config."""

    def test_frozen(self):
        config = ModelTopicProvisioningConfig(partitions=6)
        with pytest.raises(ValidationError):
            config.partitions = 12  # type: ignore[misc]

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            ModelTopicProvisioningConfig.model_validate(
                {"partitions": 6, "unknown_field": "nope"}
            )

    def test_partitions_must_be_positive(self):
        with pytest.raises(ValidationError):
            ModelTopicProvisioningConfig(partitions=0)

    def test_replication_factor_must_be_positive(self):
        with pytest.raises(ValidationError):
            ModelTopicProvisioningConfig(replication_factor=0)

    def test_kafka_config_values_must_be_str(self):
        with pytest.raises(ValidationError):
            ModelTopicProvisioningConfig.model_validate(
                {"kafka_config": {"retention.ms": 604800000}}
            )


@pytest.mark.unit
class TestModelTopicMetaTopicConfigCarry:
    """topic_config carry on ModelTopicMeta; backward-compatible default."""

    def test_topic_config_defaults_to_none(self):
        meta = ModelTopicMeta()
        assert meta.topic_config is None

    def test_existing_fields_unchanged(self):
        meta = ModelTopicMeta(schema_ref="ModelFoo", description="a topic")
        assert meta.schema_ref == "ModelFoo"
        assert meta.description == "a topic"
        assert meta.topic_config is None

    def test_topic_config_carry(self):
        meta = ModelTopicMeta(
            description="snapshot topic",
            topic_config=ModelTopicProvisioningConfig(
                partitions=1,
                kafka_config={"cleanup.policy": "compact"},
            ),
        )
        assert meta.topic_config is not None
        assert meta.topic_config.partitions == 1
        assert meta.topic_config.kafka_config == {"cleanup.policy": "compact"}

    def test_meta_extra_forbid_preserved(self):
        with pytest.raises(ValidationError):
            ModelTopicMeta.model_validate({"unexpected": "field"})

    def test_topic_config_loadable_from_nested_dict(self):
        meta = ModelTopicMeta.model_validate(
            {
                "description": "from contract yaml",
                "topic_config": {
                    "partitions": 3,
                    "replication_factor": 2,
                    "kafka_config": {"retention.ms": "86400000"},
                },
            }
        )
        assert isinstance(meta.topic_config, ModelTopicProvisioningConfig)
        assert meta.topic_config.partitions == 3
        assert meta.topic_config.replication_factor == 2
        assert meta.topic_config.kafka_config == {"retention.ms": "86400000"}


@pytest.mark.unit
class TestEventBusSubcontractTopicConfigDeclarationSite:
    """topic_config reachable at the publish/subscribe declaration site."""

    def test_publish_topic_metadata_carries_topic_config(self):
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            publish_topics=[VALID_SUFFIX],
            publish_topic_metadata={
                VALID_SUFFIX: ModelTopicMeta(
                    topic_config=ModelTopicProvisioningConfig(
                        partitions=1,
                        replication_factor=1,
                        kafka_config={"cleanup.policy": "compact"},
                    )
                )
            },
        )
        assert subcontract.publish_topic_metadata is not None
        meta = subcontract.publish_topic_metadata[VALID_SUFFIX]
        assert meta.topic_config is not None
        assert meta.topic_config.partitions == 1

    def test_subscribe_topic_metadata_loadable_from_contract_dict(self):
        subcontract = ModelEventBusSubcontract.model_validate(
            {
                "version": {"major": 1, "minor": 0, "patch": 0},
                "subscribe_topics": [VALID_SUFFIX],
                "subscribe_topic_metadata": {
                    VALID_SUFFIX: {
                        "topic_config": {"partitions": 12},
                    }
                },
            }
        )
        assert subcontract.subscribe_topic_metadata is not None
        meta = subcontract.subscribe_topic_metadata[VALID_SUFFIX]
        assert meta.topic_config is not None
        assert meta.topic_config.partitions == 12

    def test_no_topic_config_means_default_none(self):
        subcontract = ModelEventBusSubcontract(
            version=DEFAULT_VERSION,
            publish_topics=[VALID_SUFFIX],
            publish_topic_metadata={VALID_SUFFIX: ModelTopicMeta()},
        )
        assert subcontract.publish_topic_metadata is not None
        assert subcontract.publish_topic_metadata[VALID_SUFFIX].topic_config is None
