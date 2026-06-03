# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Topic-migration contract (OMN-12621).

Declarative, contract-native description of moving an event stream from an
``old`` canonical topic (and consumer group) to a ``new`` one across a bounded
compatibility window with an explicit drain-proof gate before cutover.

The model is **general** enough to express two migration shapes:

1. A ``.vN`` bump on the same logical stream
   (``onex.evt.<svc>.<event>.v1`` → ``...v2``), driven by an event
   ``schema_version`` major bump.
2. A namespace rename
   (``onex.evt.<old-ns>.*`` → ``<new-ns>.*``), the first concrete consumer of
   which is OMN-12407.

Modeled on :class:`ModelDbSafetyPolicy` (frozen, ``extra="forbid"``). Versions
are :class:`ModelSemVer`. The breaking-schema-change validator (OMN-12621)
requires an adjacent contract of this shape whenever it detects a breaking
topic-schema delta.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_cutover_criterion import EnumCutoverCriterion
from omnibase_core.enums.enum_migration_phase import EnumMigrationPhase
from omnibase_core.enums.enum_topic_schema_delta import EnumTopicSchemaDelta
from omnibase_core.models.contracts.model_topic_schema_binding import (
    ModelTopicSchemaBinding,
    detect_breaking_delta,
    parse_canonical_topic,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelTopicMigrationContract(BaseModel):
    """Contract governing a single topic migration.

    Captures the source and target streams, their consumer groups, the bounded
    compatibility window, the cutover criteria that must hold before the new
    topic becomes authoritative, and the drain-proof gate that proves the old
    topic is fully consumed before decommission.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_version: ModelSemVer = Field(
        ...,
        description="Version of this migration contract document",
    )
    ticket: str = Field(
        ...,
        description="Linear ticket authorizing this migration",
        pattern=r"^OMN-\d+$",
    )

    old_binding: ModelTopicSchemaBinding = Field(
        ...,
        description="Source topic ↔ schema_version binding being migrated away from",
    )
    new_binding: ModelTopicSchemaBinding = Field(
        ...,
        description="Target topic ↔ schema_version binding being migrated to",
    )

    old_consumer_group: str = Field(
        ...,
        min_length=1,
        description="Consumer group reading the old topic",
    )
    new_consumer_group: str = Field(
        ...,
        min_length=1,
        description="Consumer group reading the new topic",
    )

    compatibility_window_hours: int = Field(
        ...,
        ge=1,
        description=(
            "Bounded window (hours) during which both topics are live before "
            "cutover. Must be a positive, finite duration — no open-ended windows."
        ),
    )

    cutover_criteria: tuple[EnumCutoverCriterion, ...] = Field(
        ...,
        min_length=1,
        description="Conditions that must all hold before advancing to CUTOVER",
    )

    drain_proof_required: bool = Field(
        default=True,
        description=(
            "Whether cutover requires proof the old topic is fully drained for "
            "the old consumer group. Defaults True; opting out is explicit."
        ),
    )

    phase: EnumMigrationPhase = Field(
        default=EnumMigrationPhase.PLANNED,
        description="Current lifecycle phase of the migration",
    )

    @model_validator(mode="after")
    def _validate_migration(self) -> ModelTopicMigrationContract:
        # Old and new must be distinct streams (topic or schema major must move).
        if (
            self.old_binding.topic == self.new_binding.topic
            and self.old_binding.schema_version == self.new_binding.schema_version
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    "Topic-migration contract old_binding and new_binding are "
                    "identical; a migration must move topic or schema_version."
                ),
            )

        # The migration must describe a breaking delta — otherwise no migration
        # contract is needed and authoring one is a smell.
        delta = detect_breaking_delta(self.old_binding, self.new_binding)
        if not delta.is_breaking:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Topic-migration contract describes a non-breaking delta "
                    f"({delta.value}); migration contracts are only for breaking "
                    "deltas (major_bump or namespace_rename)."
                ),
            )

        # Drain-proof gate: if required, OLD_TOPIC_DRAINED must be a cutover criterion.
        if (
            self.drain_proof_required
            and EnumCutoverCriterion.OLD_TOPIC_DRAINED not in self.cutover_criteria
        ):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    "drain_proof_required is True but OLD_TOPIC_DRAINED is not "
                    "among cutover_criteria; the drain-proof gate would never be "
                    "enforced."
                ),
            )

        # Both topics must be canonical (parse or raise).
        parse_canonical_topic(self.old_binding.topic)
        parse_canonical_topic(self.new_binding.topic)
        return self

    @property
    def delta(self) -> EnumTopicSchemaDelta:
        """The breaking delta class this migration addresses."""
        return detect_breaking_delta(self.old_binding, self.new_binding)

    @property
    def is_namespace_rename(self) -> bool:
        """True if this migration renames the topic namespace (OMN-12407 shape)."""
        return self.delta is EnumTopicSchemaDelta.NAMESPACE_RENAME


__all__ = ["ModelTopicMigrationContract"]
