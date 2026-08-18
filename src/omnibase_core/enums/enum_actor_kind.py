# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Actor-Kind Enum (OMN-16177).

Discriminator for ``ModelActor``, the work-event claimant union. A claimant is
either an LLM session or a runtime node: a merge-sweep node claiming a PR-drive
is the same lock as a session claiming a ticket, so the two are variants of one
union rather than a session model with node fields bolted on.
"""

from enum import StrEnum, unique


@unique
class EnumActorKind(StrEnum):
    """Which kind of claimant emitted a work event."""

    SESSION = "session"
    """An LLM session (Claude Code or equivalent), identified by its handle."""

    NODE = "node"
    """A runtime node invocation, identified by node id, lane, and run id."""


__all__: list[str] = ["EnumActorKind"]
