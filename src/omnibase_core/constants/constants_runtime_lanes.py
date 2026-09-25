# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical registry of runtime-lane names (OMN-19408).

A runtime lane is a DEPLOYMENT fact: which lane a running process belongs to.
The deployment states it in the ``ONEX_RUNTIME_LANE`` environment variable
(OMN-18769, OMN-19144) and the runtime reads it back. A node contract may
declare ``runtime_lanes`` -- the lanes it is allowed to attach on -- and the
infra loader refuses to attach it on a runtime whose declared lane is outside
that set.

Core owns the NAMES, infra owns the behaviour: the same split as
``constants_runtime_profiles`` (OMN-12957). A lane is a different axis from a
profile. A profile is a process ROLE inside a lane (``main``, ``effects``,
``workers``); a lane is WHICH deployment the process is part of. The .201
stability-test lane's main runtime is ``main`` exactly as the dev lane's is, so
a role-scoped declaration cannot keep a lab-only node off it.

The set is closed. A contract naming a lane that is not here is refused at
parse time, and a runtime declaring one is treated as having declared none:
a typo would otherwise scope a node to a lane no runtime can ever claim, which
silently detaches it everywhere.

The spelling of the .201 dev lane is ``compose-dev``, not the lane manifest's
``dev``: it is the value the dev lane's runtime already declares
(omnibase_infra ``docker-compose.dev-lane.yml``) and the value the lab-pass
receipt emitter and the lab lane-health projection key on. One word, chosen
once, across every surface that joins on it.
"""

from __future__ import annotations

#: The lab lanes. A lab-scoped node (the lab lane-health projection, OMN-18769)
#: holds state for these and for nothing else.
LAB_RUNTIME_LANES: frozenset[str] = frozenset(
    {
        # The .201 dev lane, compose project ``omnibase-infra``, ports 8085/8086.
        "compose-dev",
        # The ``k8s/onex-lab`` overlay applied to a per-candidate cluster.
        "onex-lab",
        # The persistent k3s lab lane (OMN-18200).
        "onex-lab-k3s",
    }
)

#: Every lane a runtime deployment may declare itself to be.
REGISTERED_RUNTIME_LANES: frozenset[str] = LAB_RUNTIME_LANES | frozenset(
    {
        # .201 compose lanes (omnibase_infra deploy/lane-census/lane-manifest.yaml).
        "stability-test",
        "judge",
        "lakshman",
        "dogfood",
        "sim-202",
        "prepr-1",
        "prepr-2",
        # Cloud namespaces. Registered so a deployment there can name itself
        # without a core release; nothing here makes any node attach there.
        "onex-dev",
        "onex-prod",
    }
)


__all__ = [
    "LAB_RUNTIME_LANES",
    "REGISTERED_RUNTIME_LANES",
]
