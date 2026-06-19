# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Per-Topic Provisioning Config Model (contract declaration site).

Contract-loadable per-topic provisioning config carried at the
``event_bus.publish_topics`` / ``subscribe_topics`` declaration site (keyed by
topic suffix, on :class:`ModelTopicMeta`). Mirrors the four creation-relevant
fields of the infra-side ``ModelTopicSpec`` (partitions, replication_factor,
kafka_config) so the contract-driven boot provisioning loop can create a topic
to its contract-declared spec instead of broker defaults.

All fields are OPTIONAL. ``None`` means "fall back to the platform
``ModelTopicSpec`` defaults" (currently partitions=6, replication_factor=1, no
kafka_config overrides) — this model does not duplicate those default values so
the single source of truth for defaults stays on the provisioning side.

Distinct from :class:`omnibase_core.models.events.model_topic_config.ModelTopicConfig`,
which is a fully-specified taxonomy-driven topic config (mandatory
``topic_type`` / ``cleanup_policy`` enums) used by the OMN-939 topic taxonomy.
This model is the minimal, all-optional carry for the contract declaration site.

Keystone for OMN-13300: unblocks the per-repo ``ALL_PROVISIONED_TOPIC_SPECS``
migrations (OMN-13301/13302/13303/13304) by making per-topic config
contract-declared at the publish/subscribe declaration site rather than only on
``published_events``.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelTopicProvisioningConfig"]


class ModelTopicProvisioningConfig(BaseModel):
    """
    Optional per-topic provisioning config carried on a topic declaration.

    Declared per topic suffix via :class:`ModelTopicMeta.topic_config`. Every
    field is optional; an absent field (``None``) defers to the platform
    ``ModelTopicSpec`` defaults at provisioning time.
    """

    partitions: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Partition count for this topic. None defers to the platform "
            "ModelTopicSpec default."
        ),
    )

    replication_factor: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Replication factor for this topic. None defers to the platform "
            "ModelTopicSpec default."
        ),
    )

    kafka_config: dict[str, str] | None = Field(
        default=None,
        description=(
            "Optional Kafka topic config overrides (e.g. "
            '{"cleanup.policy": "compact", "retention.ms": "604800000"}). '
            "None defers to the platform ModelTopicSpec default (no overrides)."
        ),
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
