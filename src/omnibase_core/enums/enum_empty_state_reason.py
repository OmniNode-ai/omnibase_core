# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Empty-state reason vocabulary for contract-driven UI rendering.

Platform-neutral reason codes a renderer surfaces when a component cannot
display data. The client renders truth; it never silently blanks or
substitutes a fallback literal. Every empty render carries one of these
typed reasons.

Source of truth for the value set is the TS union ``EmptyStateReason`` in
``omnidash/shared/types/chart-config.ts`` (OMN-13130, epic OMN-13129). These
four values must stay in lockstep with that union; the Pydantic -> TS codegen
gate regenerates the TS mirror from this enum.

``UPSTREAM_BLOCKED`` is the capability-gating signal: when a renderer's
capability row is stale/absent the projection service withholds the contract
and the client surfaces ``upstream-blocked`` rather than rendering blind.
"""

from enum import StrEnum

__all__ = ["EnumEmptyStateReason"]


class EnumEmptyStateReason(StrEnum):
    """Typed reason a UI component renders an empty/error state.

    Mirrors the ``EmptyStateReason`` TS union exactly (four values, no more).
    A renderer MUST NOT collapse ``SCHEMA_INVALID`` into ``NO_DATA`` — each
    reason maps to a distinct operator diagnostic.
    """

    NO_DATA = "no-data"
    """The projection returned zero rows — the query is valid but empty."""

    MISSING_FIELD = "missing-field"
    """A declared display field is not emitted by the upstream projection."""

    UPSTREAM_BLOCKED = "upstream-blocked"
    """Upstream is blocked (e.g. renderer capability stale/absent); drives
    capability gating rather than a blind render."""

    SCHEMA_INVALID = "schema-invalid"
    """The projection payload failed schema validation; never folded into
    ``NO_DATA``."""
