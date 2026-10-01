# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct-model-call gate, COMPUTE half (OMN-20295).

A blocking, structural gate that refuses any model call (an HTTP request to a
model endpoint, provider host or base_url; the exec of a model CLI such as
crush, codex, ``claude -p`` or llama-cli; the import of a model SDK; or a caller
of one of those in another file) outside the sanctioned delegation node
packages. Pre-existing sites live in a per-repository baseline that may only
shrink, each naming its removal ticket. The server-side backstop for calls no
static gate can see is OMN-20299.

* ``handler``: ``HandlerDirectModelCallCompute``, the pure definition-B handler.
* ``_scan`` and the modules it imports: the AST, import and call-graph analysis.
* ``_baseline``: the shrink-only ratchet and the baseline rendering.
* ``policy.yaml``: the only place a package is sanctioned. There is no inline
  suppression marker.

Every read and write (git, files, the policy resource, the clock) lives in the
EFFECT half, ``node_direct_model_call_check_effect``, which also carries the
``check-direct-model-call`` CLI.
"""

from __future__ import annotations

from omnibase_core.nodes.node_direct_model_call_check_compute.handler import (
    HandlerDirectModelCallCompute,
)

__all__ = ["HandlerDirectModelCallCompute"]
