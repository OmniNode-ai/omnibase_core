# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Private dispatch-table state for :mod:`mixin_node_dispatch`."""

from __future__ import annotations

from collections.abc import Callable

from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.runtime.dispatch_entry import _NodeDispatchEntry

__all__ = []

# ``(event_type | None, original_topic) -> dlq_topic | None``.
DlqTopicDeriver = Callable[[str | None, str], str | None]


class _NodeDispatchState:
    """Per-instance dispatch-selection table, materialized lazily by the mixin."""

    __slots__ = ("dispatchers", "dlq_topic_deriver", "frozen", "routes")

    def __init__(self) -> None:
        self.routes: dict[str, ModelDispatchRoute] = {}
        self.dispatchers: dict[str, _NodeDispatchEntry] = {}
        self.frozen: bool = False
        self.dlq_topic_deriver: DlqTopicDeriver | None = None
