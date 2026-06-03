# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Topic ``.vN`` ↔ event ``schema_version`` linkage (OMN-12621).

Background
----------
A canonical ONEX topic carries a free-text version segment ``.vN``
(``onex.evt.<service>.<event>.v<N>``). The payload that flows on that topic is
described by a :class:`ModelEventType` whose ``schema_version`` is a full
:class:`ModelSemVer`. Before this module there was **no link** between the two:
the topic's ``.vN`` and the event's ``schema_version`` could drift apart, so
"detect a breaking schema change" had nothing to diff against.

``ModelTopicSchemaBinding`` is that link. It binds one canonical topic name to
the SemVer schema_version of the event it carries, and asserts the topic's
``.vN`` matches the event's **major** version (the wire-compat boundary, mirror
of :meth:`ModelEventType.is_compatible_with` which compares major).

Breaking-delta detection
-------------------------
:func:`detect_breaking_delta` compares two bindings (old vs new) and reports the
:class:`EnumTopicSchemaDelta`:

- ``NONE`` — same topic, same major.
- ``COMPATIBLE`` — same topic+major, minor/patch forward bump only.
- ``MAJOR_BUMP`` — same namespace+service+event, the ``.vN`` / schema major rose.
- ``NAMESPACE_RENAME`` — the namespace/service/event identity changed
  (``onex.evt.<old-ns>.*`` → ``<new-ns>.*``; first consumer is OMN-12407).

``MAJOR_BUMP`` and ``NAMESPACE_RENAME`` are **breaking** — they require a
:class:`ModelTopicMigrationContract`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_topic_schema_delta import EnumTopicSchemaDelta
from omnibase_core.models.contracts.model_canonical_topic import ModelCanonicalTopic
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# onex.<kind>.<service>.<event>[.<event>...].v<N>
_CANONICAL_TOPIC_RE = re.compile(
    r"^(?P<namespace>onex)"
    r"\.(?P<kind>cmd|evt|dlq|snapshot|intent)"
    r"\.(?P<service>[a-zA-Z0-9_-]+)"
    r"\.(?P<event>[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*)"
    r"\.v(?P<version>\d+)$"
)


def parse_canonical_topic(topic: str) -> ModelCanonicalTopic:
    """Parse a canonical ONEX topic into its structured parts.

    Raises:
        ModelOnexError: if ``topic`` does not match the canonical format
            ``onex.<kind>.<service>.<event>[.<event>...].v<N>``.
    """
    match = _CANONICAL_TOPIC_RE.match(topic)
    if match is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=(
                f"Topic {topic!r} does not match canonical ONEX format "
                "onex.<kind>.<service>.<event>[.<event>...].v<N>"
            ),
        )
    return ModelCanonicalTopic(
        namespace=match.group("namespace"),
        kind=match.group("kind"),
        service=match.group("service"),
        event=match.group("event"),
        topic_major=int(match.group("version")),
    )


def build_versioned_topic(
    service: str,
    event: str,
    version: int,
    *,
    kind: str = "evt",
) -> str:
    """Build a canonical versioned topic ``onex.<kind>.<service>.<event>.v<N>``.

    General builder addressing the gap that only ``build_dlq_topic`` existed.

    Raises:
        ModelOnexError: on invalid kind, version, or segment characters.
    """
    if kind not in ("cmd", "evt", "dlq", "snapshot", "intent"):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"Invalid topic kind {kind!r}; expected cmd|evt|dlq|snapshot|intent",
        )
    if version < 1:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            message=f"Topic version must be >= 1, got {version}",
        )
    topic = f"onex.{kind}.{service}.{event}.v{version}"
    # Validate by round-tripping through the canonical parser.
    parse_canonical_topic(topic)
    return topic


class ModelTopicSchemaBinding(BaseModel):
    """Binds a canonical topic to the SemVer schema_version it carries.

    The binding asserts the topic's ``.vN`` equals the event's
    ``schema_version.major`` — the wire-compatibility boundary. This is the
    linkage that makes a breaking schema delta detectable: a topic ``.vN`` bump
    must correspond to a schema major bump, and vice versa.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(
        ..., description="Canonical topic name (onex.<kind>.<service>.<event>.v<N>)"
    )
    event_name: str = Field(
        ...,
        description="Event identifier carried on the topic",
        pattern="^[A-Z][A-Z0-9_]*$",
    )
    schema_version: ModelSemVer = Field(
        ..., description="SemVer schema_version of the event payload on this topic"
    )

    @model_validator(mode="after")
    def _assert_major_matches_topic_version(self) -> ModelTopicSchemaBinding:
        parsed = parse_canonical_topic(self.topic)
        if parsed.topic_major != self.schema_version.major:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"Topic version segment .v{parsed.topic_major} does not match "
                    f"schema_version major {self.schema_version.major} for topic "
                    f"{self.topic!r}. The topic .vN MUST equal the event "
                    "schema_version major (wire-compatibility boundary)."
                ),
            )
        return self

    @property
    def parsed(self) -> ModelCanonicalTopic:
        """Structured view of the bound topic."""
        return parse_canonical_topic(self.topic)


def detect_breaking_delta(
    old: ModelTopicSchemaBinding,
    new: ModelTopicSchemaBinding,
) -> EnumTopicSchemaDelta:
    """Classify the delta between an old and a new topic-schema binding.

    Returns:
        - ``NAMESPACE_RENAME`` if the namespace/kind/service/event identity
          changed (breaking — e.g. OMN-12407 ``onex.evt.<old-ns>.*`` rename).
        - ``MAJOR_BUMP`` if same identity but the schema major rose (breaking).
        - ``COMPATIBLE`` if same identity+major with a forward minor/patch bump.
        - ``NONE`` if the bindings are schema-equivalent.
    """
    if old.parsed.identity != new.parsed.identity:
        return EnumTopicSchemaDelta.NAMESPACE_RENAME
    if new.schema_version.major > old.schema_version.major:
        return EnumTopicSchemaDelta.MAJOR_BUMP
    if new.schema_version.major < old.schema_version.major:
        # A major regression is also a breaking, migration-requiring change.
        return EnumTopicSchemaDelta.MAJOR_BUMP
    if new.schema_version > old.schema_version:
        return EnumTopicSchemaDelta.COMPATIBLE
    return EnumTopicSchemaDelta.NONE


__all__ = [
    "ModelTopicSchemaBinding",
    "build_versioned_topic",
    "detect_breaking_delta",
    "parse_canonical_topic",
]
