# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""What a repository function means to its callers (OMN-20295)."""

from __future__ import annotations

from dataclasses import dataclass, field

from omnibase_core.nodes.node_direct_model_call_check_compute._value import _EMPTY, _Val


@dataclass
class _Summary:
    """What a repository function means to its callers."""

    params: tuple[str, ...]
    is_method: bool
    returns: _Val = _EMPTY
    param_sinks: dict[str, frozenset[str]] = field(default_factory=dict)
