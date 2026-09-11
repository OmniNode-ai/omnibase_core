# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Selection metadata for one node-owned dispatcher."""

from __future__ import annotations

from collections.abc import Callable

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.types.type_node_dispatch import DispatcherCallable


class DispatchEntry:
    """Core-only dispatcher metadata used during route selection."""

    __slots__ = (
        "category",
        "dispatcher",
        "dispatcher_id",
        "message_types",
        "node_kind",
        "payload_type_matcher",
    )

    def __init__(
        self,
        *,
        dispatcher_id: str,
        dispatcher: DispatcherCallable,
        category: EnumMessageCategory,
        message_types: set[str] | None,
        node_kind: EnumNodeKind | None,
        payload_type_matcher: Callable[[object], bool] | None,
    ) -> None:
        self.dispatcher_id = dispatcher_id
        self.dispatcher = dispatcher
        self.category = category
        self.message_types = set(message_types) if message_types is not None else None
        self.node_kind = node_kind
        self.payload_type_matcher = payload_type_matcher


__all__ = ["DispatchEntry"]
