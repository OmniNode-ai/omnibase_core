# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Private dispatcher registration record for :mod:`mixin_node_dispatch`."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory

if TYPE_CHECKING:
    from omnibase_core.enums.enum_node_kind import EnumNodeKind

__all__ = []

_DispatcherCallable = Callable[..., object]


class _NodeDispatchEntry:
    """Selection metadata for one registered dispatcher.

    This is the core-only mirror of the engine's execution-independent dispatch
    registration data. It intentionally keeps the callable opaque because the
    selection layer never invokes it.
    """

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
        dispatcher: _DispatcherCallable,
        category: EnumMessageCategory,
        message_types: set[str] | None,
        node_kind: EnumNodeKind | None,
        payload_type_matcher: Callable[[object], bool] | None,
    ) -> None:
        self.dispatcher_id = dispatcher_id
        self.dispatcher = dispatcher
        self.category = category
        self.message_types = (
            set(message_types) if message_types is not None else None
        )  # None means "all message types"
        self.node_kind = node_kind
        # None means "not type-scoped" — legacy string-only matching applies.
        self.payload_type_matcher = payload_type_matcher
