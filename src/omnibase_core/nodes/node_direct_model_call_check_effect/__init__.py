# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct-model-call gate, EFFECT half (OMN-20295).

``HandlerDirectModelCallCheckEffect`` reads the repository's tracked files, the
policy packaged with ``node_direct_model_call_check_compute``, the committed
baseline, the baseline at a base ref and today's date, and hands them to the
pure COMPUTE handler. ``runtime_direct_model_call`` is the
``check-direct-model-call`` pre-commit hook and CI command.
"""

from __future__ import annotations

from omnibase_core.nodes.node_direct_model_call_check_effect.handler import (
    HandlerDirectModelCallCheckEffect,
)

__all__ = ["HandlerDirectModelCallCheckEffect"]
