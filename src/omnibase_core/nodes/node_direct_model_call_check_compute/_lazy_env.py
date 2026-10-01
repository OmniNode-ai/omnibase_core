# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A unit's local names, evaluated on first use and memoised (OMN-20295)."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping

from omnibase_core.nodes.node_direct_model_call_check_compute._constants import _Event
from omnibase_core.nodes.node_direct_model_call_check_compute._module import (
    _Module,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._value import _EMPTY, _Val


class _LazyEnv(Mapping[str, _Val]):
    """A unit's local names, each evaluated on first use and then memoised.

    A name's value is the join of all its assignments (flow-insensitive), so
    a gate cannot be passed by reassigning a name after the sink.
    """

    def __init__(
        self,
        apply: Callable[[_LazyEnv, _Val, _Event], _Val],
        module: _Module,
        qual: str,
        preset: dict[str, _Val],
        events: dict[str, list[_Event]],
        depth: int,
    ) -> None:
        self._apply = apply
        self.module = module
        self.qual = qual
        self.depth = depth
        self._preset = preset
        self._events = events
        self._memo: dict[str, _Val] = {}
        self._busy: set[str] = set()

    def __contains__(self, name: object) -> bool:
        return name in self._preset or name in self._events

    def __getitem__(self, name: str) -> _Val:
        if name in self._memo:
            return self._memo[name]
        if name not in self:
            return _EMPTY
        current = self._preset.get(name, _EMPTY)
        if name in self._busy:
            return current
        self._busy.add(name)
        try:
            for event in self._events.get(name, ()):
                current = self._apply(self, current, event)
        finally:
            self._busy.discard(name)
        self._memo[name] = current
        return current

    def __iter__(self) -> Iterator[str]:
        return iter({*self._preset, *self._events})

    def __len__(self) -> int:
        return len({*self._preset, *self._events})
