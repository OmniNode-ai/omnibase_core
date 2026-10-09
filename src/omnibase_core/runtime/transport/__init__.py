# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Concrete transports for the unified runtime dispatch loop.

Net-new foundation (epic OMN-14717). Exposes the in-memory transport that models
Kafka's per-partition offset semantics. The parametrized conformance suite lives in
:mod:`omnibase_core.runtime.transport.runtime_transport_conformance` and is imported
directly by tests (never from this ``__init__``) so the production import graph stays
free of any test-framework dependency.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker
    from omnibase_core.runtime.transport.runtime_in_memory_transport import (
        InMemoryTransport,
    )

__all__ = ["InMemoryBroker", "InMemoryTransport"]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "InMemoryBroker": (
        "omnibase_core.runtime.transport.runtime_in_memory_broker",
        "InMemoryBroker",
    ),
    "InMemoryTransport": (
        "omnibase_core.runtime.transport.runtime_in_memory_transport",
        "InMemoryTransport",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
