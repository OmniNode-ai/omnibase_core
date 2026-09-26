# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Closed vocabularies for execution-graph replay models."""

from enum import StrEnum


class EnumExecutionGraphNodeKind(StrEnum):
    HOP = "hop"
    REROUTE_EVIDENCE = "reroute_evidence"


class EnumExecutionGraphEdgeKind(StrEnum):
    CAUSED = "caused"
    REROUTED = "rerouted"
    VERIFIED = "verified"
    ANCHORED = "anchored"


class EnumExecutionGraphEndpointKind(StrEnum):
    NODE = "node"
    VERDICT = "verdict"
    SESSION_ANCHOR = "session_anchor"


class EnumExecutionGraphCursorMode(StrEnum):
    LATEST = "latest"
    BOUNDED = "bounded"


class EnumExecutionGraphAnchorKind(StrEnum):
    SESSION = "session"
    NONE = "none"


class EnumExecutionGraphAnchorState(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class EnumExecutionGraphVerdictStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNRESOLVED = "unresolved"


class EnumExecutionGraphVerdictOutcome(StrEnum):
    DONE = "done"
    REFUSED = "refused"


class EnumExecutionGraphUnresolvedReason(StrEnum):
    MISSING_PARENT = "missing_parent"
    PARENT_OUTSIDE_CURSOR = "parent_outside_cursor"
    MISSING_ANCHOR = "missing_anchor"
    MISSING_VERDICT = "missing_verdict"


class EnumExecutionGraphRefusalReason(StrEnum):
    CORRELATION_NOT_FOUND = "correlation_not_found"
    CORRELATION_AMBIGUOUS = "correlation_ambiguous"
    MULTIPLE_CHAIN_HEADS = "multiple_chain_heads"
    ENVELOPE_ID_COLLISION = "envelope_id_collision"
    PARENT_CYCLE = "parent_cycle"
    UNSUPPORTED_VERSION = "unsupported_version"
    INVALID_EVIDENCE = "invalid_evidence"
