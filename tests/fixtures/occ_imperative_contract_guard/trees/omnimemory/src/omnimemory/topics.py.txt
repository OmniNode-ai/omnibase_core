# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Canonical Kafka topic registry for omnimemory events and commands.

Defines all omnimemory Kafka topics as StrEnums. All topic names follow
ONEX canonical format: ``onex.{kind}.{producer}.{event-name}.v{n}``

This module is the single source of truth for omnimemory topic names.
No hardcoded topic strings should appear in producer or consumer code; use
these enum values instead.

ONEX Compliance:
    - Topic names are immutable StrEnum values (no hardcoded strings elsewhere).
    - All `emitted_at` fields in envelope models must be injected by callers.
    - No datetime.now() defaults permitted.

Reference: OMN-8605, OMN-8633
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumMemoryCommandTopic(UtilStrValueHelper, str, Enum):
    """Canonical Kafka topic names for omnimemory input commands.

    All topics use ``onex.cmd.omnimemory.*`` as the consumer namespace
    (producer/consumer: ``omnimemory``, kind: ``cmd``).
    """

    INTENT_QUERY_REQUESTED = "onex.cmd.omnimemory.intent-query-requested.v1"
    """Intent query requested command."""

    RUNTIME_TICK = "onex.cmd.omnimemory.runtime-tick.v1"
    """Lifecycle runtime-tick command."""

    ARCHIVE_MEMORY = "onex.cmd.omnimemory.archive-memory.v1"
    """Archive memory lifecycle command."""

    EXPIRE_MEMORY = "onex.cmd.omnimemory.expire-memory.v1"
    """Expire memory lifecycle command."""

    MEMORY_RETRIEVAL_REQUESTED = "onex.cmd.omnimemory.memory-retrieval-requested.v1"
    """Memory retrieval requested command."""

    GRAPH_MEMORY_QUERY = "onex.cmd.omnimemory.graph-memory-query.v1"
    """Graph memory query/mutation command (OMN-6578)."""

    INTENT_GRAPH_QUERY = "onex.cmd.omnimemory.intent-graph-query.v1"
    """Intent graph query/mutation command (OMN-6579)."""

    NAVIGATION_HISTORY_SESSION = "onex.cmd.omnimemory.navigation-history-session.v1"
    """Navigation history session command (OMN-6583)."""

    SEMANTIC_ANALYSIS = "onex.cmd.omnimemory.semantic-analysis.v1"
    """Semantic analysis request command (OMN-6585)."""


@unique
class EnumMemoryEventTopic(UtilStrValueHelper, str, Enum):
    """Canonical Kafka topic names for omnimemory events.

    Includes both events produced by omnimemory (crawl pipeline, intent storage)
    and cross-domain events consumed by omnimemory from other services.
    """

    # --- Cross-domain events consumed by omnimemory ---

    INTENT_CLASSIFIED = "onex.evt.omniintelligence.intent-classified.v1"
    """Intent classified event produced by omniintelligence."""

    INTENT_CLASSIFIED_DLQ = "onex.evt.omniintelligence.intent-classified-dlq.v1"
    """Dead-letter queue for intent-classified events."""

    # --- Crawl pipeline events produced by omnimemory ---

    DOCUMENT_DISCOVERED = "onex.evt.omnimemory.document-discovered.v1"
    """Document discovered by filesystem or other crawlers."""

    DOCUMENT_CHANGED = "onex.evt.omnimemory.document-changed.v1"
    """Document content changed, triggers re-parse."""

    DOCUMENT_REMOVED = "onex.evt.omnimemory.document-removed.v1"
    """Document removed from crawl scope."""

    DOCUMENT_INDEXED = "onex.evt.omnimemory.document-indexed.v1"
    """Document successfully indexed (kreuzberg variant or standard)."""

    DOCUMENT_PARSE_FAILED = "onex.evt.omnimemory.document-parse-failed.v1"
    """Document parse failed (too large, timeout, or parse error)."""

    # --- Memory pipeline events produced by omnimemory ---

    INTENT_STORED = "onex.evt.omnimemory.intent-stored.v1"
    """Intent stored event after processing intent-classified input."""

    MEMORY_RETRIEVAL_RESPONSE = "onex.evt.omnimemory.memory-retrieval-response.v1"
    """Memory retrieval response event."""


__all__ = ["EnumMemoryCommandTopic", "EnumMemoryEventTopic"]
