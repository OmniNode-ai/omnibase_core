# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical registry of runtime-profile names (OMN-12957).

This module is the **single source of truth** for the set of runtime-profile
names that the ONEX runtime knows how to boot. A contract that declares a
``runtime_profiles`` value not present in :data:`REGISTERED_RUNTIME_PROFILES`
silently orphans the node: the runtime never wires its subscriptions to any
process, so it has zero consumers and zero errors. ``ValidatorRuntimeProfiles``
enforces ``contract.runtime_profiles ⊆ REGISTERED_RUNTIME_PROFILES`` so the
orphan is caught at commit/CI time instead of at runtime.

Layering note: the concrete profile *behaviour* (prefetch policy, subsystem
gating) lives in ``omnibase_infra.runtime.runtime_profile._PROFILES``. That
registry derives its key set from this constant — core owns the **names**,
infra owns the **behaviour**. ``omnibase_infra`` carries a parity test
(``test_profiles_match_core_registry``) that fails if the two drift, so the
infra ``_PROFILES`` dict can never declare a profile core does not know about
and core can never bless a name infra does not implement.

Consumer-attached subset
------------------------
:data:`CONSUMER_ATTACHED_RUNTIME_PROFILES` is the subset of profiles that run a
*standalone Kafka consumer* — i.e. a process that actually attaches a consumer
group and drains its owned topics. ``main``, ``effects``, and ``workers`` host
the orchestrator / effect / worker consumer lanes respectively. ``local-dev``,
``default``, ``staging``, and ``production`` are policy overlays (prefetch
posture), not distinct consumer lanes; ``canary`` and ``projection-api`` run
isolated lanes that do NOT consume the general command/event groups a
REDUCER/EFFECT needs.

A REDUCER or EFFECT contract that subscribes to topics but names *only*
non-consumer-attached profiles is the second, subtler class of silent
orphaning: the name is registered (passes the subset check) but no process ever
drains its subscriptions. ``ValidatorRuntimeProfiles`` flags that too.
"""

from __future__ import annotations

# Every runtime-profile name the ONEX runtime can boot. Lower-cased; the
# validator and ownership filter normalize declared profiles before comparison.
REGISTERED_RUNTIME_PROFILES: frozenset[str] = frozenset(
    {
        "local-dev",
        "default",
        "main",
        "effects",
        "workers",
        "projection-api",
        "canary",
        "staging",
        "production",
    }
)

# Profiles that run a standalone Kafka consumer (attach a consumer group and
# drain owned topics). A subscribing REDUCER/EFFECT must name at least one of
# these or its subscriptions are never consumed by any process.
CONSUMER_ATTACHED_RUNTIME_PROFILES: frozenset[str] = frozenset(
    {
        "main",
        "effects",
        "workers",
    }
)


__all__ = [
    "CONSUMER_ATTACHED_RUNTIME_PROFILES",
    "REGISTERED_RUNTIME_PROFILES",
]
