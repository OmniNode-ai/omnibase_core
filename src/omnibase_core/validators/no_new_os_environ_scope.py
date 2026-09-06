# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Lexical scope state for the raw environment access validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

_BindingKind = Literal[  # enum-ok: internal AST binding state, not a domain value
    "os-module",
    "environment-mapping",
    "environment-function",
]


@dataclass
class _Scope:
    """Sequential binding state with Python local-shadowing semantics."""

    parent: _Scope | None
    local_names: set[str] = field(default_factory=set)
    bindings: dict[str, _BindingKind] = field(default_factory=dict)
    global_names: set[str] = field(default_factory=set)
    nonlocal_names: set[str] = field(default_factory=set)

    def resolve(self, name: str) -> _BindingKind | None:
        """Resolve a known raw-environment alias without crossing a shadow."""
        if name in self.global_names:
            return self._module_scope().resolve_local(name)
        if name in self.nonlocal_names:
            return self._nearest_enclosing_scope().resolve(name)
        return self.resolve_local(name)

    def resolve_local(self, name: str) -> _BindingKind | None:
        if name in self.bindings:
            return self.bindings[name]
        if name in self.local_names:
            return None
        if self.parent is None:
            return None
        return self.parent.resolve(name)

    def bind(self, name: str, kind: _BindingKind | None) -> None:
        """Bind or invalidate a name in the scope Python assigns to it."""
        target = self._assignment_scope(name)
        target.local_names.add(name)
        if kind is None:
            target.bindings.pop(name, None)
        else:
            target.bindings[name] = kind

    def _assignment_scope(self, name: str) -> _Scope:
        if name in self.global_names:
            return self._module_scope()
        if name in self.nonlocal_names:
            return self._nearest_enclosing_scope()
        return self

    def _module_scope(self) -> _Scope:
        scope = self
        while scope.parent is not None:
            scope = scope.parent
        return scope

    def _nearest_enclosing_scope(self) -> _Scope:
        if self.parent is None:
            return self
        return self.parent
