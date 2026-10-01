# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A command line in one function that runs a repository file or module (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass

from omnibase_core.nodes.node_direct_model_call_check_compute._script_ref import (
    _ScriptRef,
)


@dataclass(frozen=True)
class _ExecEdge:
    caller: tuple[str, str]
    ref: _ScriptRef
    line: int
