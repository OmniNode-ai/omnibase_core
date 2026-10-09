# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Testing utilities for the core-resident ``event_bus_substrate`` fixture.

See ``fixture_event_bus_substrate.py`` for the fixture itself and
``contract_event_bus_substrate.py`` for the shared cross-repo contract
tests. Import the specific symbols you need directly from those submodules
(e.g. in a ``conftest.py``) -- this package ``__init__`` re-exports the
fixture names for convenience but the pytest fixtures must still be
imported by name into a ``conftest.py`` or test module to be registered.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.event_bus.testing.fixture_event_bus_substrate import (
        CORE_EVENT_BUS_SUBSTRATE_PARAMS,
        CORE_FIDELITY_SUBSTRATE_PARAMS,
        build_core_event_bus_substrate,
        build_core_event_bus_substrate_instance,
        event_bus_substrate,
        fidelity_event_bus_substrate,
    )

__all__: list[str] = [
    "CORE_EVENT_BUS_SUBSTRATE_PARAMS",
    "CORE_FIDELITY_SUBSTRATE_PARAMS",
    "build_core_event_bus_substrate",
    "build_core_event_bus_substrate_instance",
    "event_bus_substrate",
    "fidelity_event_bus_substrate",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "CORE_EVENT_BUS_SUBSTRATE_PARAMS": (
        "omnibase_core.event_bus.testing.fixture_event_bus_substrate",
        "CORE_EVENT_BUS_SUBSTRATE_PARAMS",
    ),
    "CORE_FIDELITY_SUBSTRATE_PARAMS": (
        "omnibase_core.event_bus.testing.fixture_event_bus_substrate",
        "CORE_FIDELITY_SUBSTRATE_PARAMS",
    ),
    "build_core_event_bus_substrate": (
        "omnibase_core.event_bus.testing.fixture_event_bus_substrate",
        "build_core_event_bus_substrate",
    ),
    "build_core_event_bus_substrate_instance": (
        "omnibase_core.event_bus.testing.fixture_event_bus_substrate",
        "build_core_event_bus_substrate_instance",
    ),
    "event_bus_substrate": (
        "omnibase_core.event_bus.testing.fixture_event_bus_substrate",
        "event_bus_substrate",
    ),
    "fidelity_event_bus_substrate": (
        "omnibase_core.event_bus.testing.fixture_event_bus_substrate",
        "fidelity_event_bus_substrate",
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
