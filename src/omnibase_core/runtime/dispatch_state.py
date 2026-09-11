# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Mutable selection state owned by one node-dispatch mixin instance."""

from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.runtime.dispatch_entry import DispatchEntry
from omnibase_core.types.type_node_dispatch import DlqTopicDeriver


class DispatchState:
    """Lazily materialized route and dispatcher selection table."""

    __slots__ = ("dispatchers", "dlq_topic_deriver", "frozen", "routes")

    def __init__(self) -> None:
        self.routes: dict[str, ModelDispatchRoute] = {}
        self.dispatchers: dict[str, DispatchEntry] = {}
        self.frozen = False
        self.dlq_topic_deriver: DlqTopicDeriver | None = None


__all__ = ["DispatchState"]
