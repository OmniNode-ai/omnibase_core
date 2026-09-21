# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Private selected-route record for :mod:`mixin_node_dispatch`."""

from __future__ import annotations

from typing import NamedTuple

from omnibase_core.runtime.dispatch_entry import _NodeDispatchEntry

__all__ = []


class _NodeDispatchMatch(NamedTuple):
    """One selected dispatcher paired with the route that selected it."""

    route_id: str
    entry: _NodeDispatchEntry
