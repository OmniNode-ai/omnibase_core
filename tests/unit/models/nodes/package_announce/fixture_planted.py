# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixtures of the node announcement tests, including the planted violations (OMN-21589).

A planted violation is an input built to break exactly one rule. Each rule's test
runs against its planted violation and against a control that obeys the rule, so a
check that can no longer refuse is itself a failing test.
"""

from datetime import UTC, datetime
from uuid import UUID

from omnibase_core.enums.enum_announced_node_kind import EnumAnnouncedNodeKind
from omnibase_core.enums.enum_announcement_operation import EnumAnnouncementOperation
from omnibase_core.models.events.contract_registration.model_announced_package import (
    ModelAnnouncedPackage,
)
from omnibase_core.models.events.contract_registration.model_node_announcement import (
    ModelNodeAnnouncement,
)
from omnibase_core.models.nodes.package_announce.model_node_announce_policy import (
    ModelNodeAnnouncePolicy,
)

ANNOUNCER = UUID("00000000-0000-4000-8000-0000000000a1")
INTRUDER = UUID("00000000-0000-4000-8000-0000000000ff")
TRUSTED = ("alpha_pkg.", "beta_pkg.")


def policy(
    *,
    profiles: tuple[str, ...] = ("main",),
    authoritative: dict[str, UUID] | None = None,
) -> ModelNodeAnnouncePolicy:
    """A policy that differs from another only in the values the overlay supplies."""
    return ModelNodeAnnouncePolicy(
        trusted_handler_prefixes=TRUSTED,
        active_profiles=profiles,
        authoritative_announcers=(
            authoritative
            if authoritative is not None
            else {"alpha-pkg": ANNOUNCER, "beta-pkg": ANNOUNCER}
        ),
    )


def contract_bytes(
    name: str,
    *,
    handler_module: str = "alpha_pkg.nodes.example.handler",
    profiles: tuple[str, ...] = (),
    newline: str = "\n",
    extra_topic: str | None = None,
) -> bytes:
    """The bytes of a small node contract, with the requested line endings."""
    lines = [
        f"name: {name}",
        "node_type: compute",
        "event_bus:",
        "  publish_topics:",
        f"    - onex.evt.fixture.{name.replace('_', '-')}-completed.v1",
    ]
    if extra_topic is not None:
        lines.append(f"    - {extra_topic}")
    lines += [
        "handler_routing:",
        "  handlers:",
        "    - handler:",
        f"        module: {handler_module}",
        "        name: Handler",
    ]
    if profiles:
        lines.append("runtime_profiles:")
        lines += [f"  - {profile}" for profile in profiles]
    return (newline.join(lines) + newline).encode("utf-8")


def announcement(
    raw: bytes,
    *,
    name: str = "example",
    operation: EnumAnnouncementOperation = EnumAnnouncementOperation.ANNOUNCE,
    generation: int = 1,
    announcer_id: UUID = ANNOUNCER,
    distribution: str = "alpha-pkg",
    version: str = "1.0.0",
) -> ModelNodeAnnouncement:
    """The announcement an honest announcer would publish for these contract bytes."""
    return ModelNodeAnnouncement(
        entity_id=name,
        operation=operation,
        content_hash=ModelNodeAnnouncement.canonical_content_hash(raw),
        package=ModelAnnouncedPackage(distribution=distribution, version=version),
        node_kind=EnumAnnouncedNodeKind.NODE,
        announcer_id=announcer_id,
        generation=generation,
        announced_at=datetime(2026, 10, 30, tzinfo=UTC),
    )


GOOD_FIELDS: dict[str, object] = {
    "entity_id": "node_example",
    "operation": "announce",
    "content_hash": "0123456789abcdef" * 4,
    "package": {"distribution": "example-pkg", "version": "1.2.3"},
    "node_kind": "node",
    "declared_topics": ["fixture.example.done"],
    "handler_dependencies": ["ProtocolExample"],
    "announcer_id": "00000000-0000-4000-8000-0000000000a1",
    "generation": 1,
    "announced_at": "2026-10-30T00:00:00+00:00",
}

# Each planted violation breaks one field of an otherwise valid record.
PLANTED_INVALID_FIELDS: dict[str, dict[str, object]] = {
    "uppercase_hash": {"content_hash": "A" * 64},
    "non_hex_hash": {"content_hash": "g" * 64},
    "short_hash": {"content_hash": "a" * 63},
    "long_hash": {"content_hash": "a" * 65},
    "empty_name": {"entity_id": ""},
    "unknown_operation": {"operation": "rename"},
    "unknown_kind": {"node_kind": "daemon"},
    "naive_timestamp": {"announced_at": "2026-10-30T00:00:00"},
    "generation_zero": {"generation": 0},
    "announcer_not_a_uuid": {"announcer_id": "announcer-1"},
    "empty_distribution": {"package": {"distribution": "", "version": "1"}},
    "extra_field": {"surprise": 1},
}
