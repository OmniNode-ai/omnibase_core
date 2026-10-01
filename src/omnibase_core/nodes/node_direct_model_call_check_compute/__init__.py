# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct-model-call validator (OMN-20295).

Task N4.1 of knowledge-base-internal ``beta/plans/2026-09-24-delegation-work-plan.md``
section 3.9: a blocking, structural gate that refuses any model call (an HTTP
request to a model endpoint, provider host or base_url; the exec of a model
CLI such as crush, codex, ``claude -p`` or llama-cli; the import of a model SDK;
or a caller of one of those in another file) outside the sanctioned delegation
node packages. Pre-existing sites live in a per-repository baseline that may
only shrink, each naming its removal ticket. The server-side backstop for calls
no static gate can see is OMN-20299.

* ``models``: the policy, scan input, finding and baseline.
* ``handler``: ``HandlerDirectModelCallCompute`` and the pure ``scan``.
* ``runtime_direct_model_call``: the EFFECT boundary and CLI (the
  ``check-direct-model-call`` pre-commit hook and CI command).
* ``policy.yaml``: the only place a package is sanctioned. There is no inline
  suppression marker.
"""

from __future__ import annotations

from omnibase_core.nodes.node_direct_model_call_check_compute.handler import (
    HandlerDirectModelCallCompute,
    scan,
)
from omnibase_core.nodes.node_direct_model_call_check_compute.models import (
    ModelDirectModelCallBaseline,
    ModelDirectModelCallBaselineEntry,
    ModelDirectModelCallFinding,
    ModelDirectModelCallPolicy,
    ModelDirectModelCallScanInput,
    ModelDirectModelCallSourceFile,
)

__all__ = [
    "HandlerDirectModelCallCompute",
    "ModelDirectModelCallBaseline",
    "ModelDirectModelCallBaselineEntry",
    "ModelDirectModelCallFinding",
    "ModelDirectModelCallPolicy",
    "ModelDirectModelCallScanInput",
    "ModelDirectModelCallSourceFile",
    "scan",
]
