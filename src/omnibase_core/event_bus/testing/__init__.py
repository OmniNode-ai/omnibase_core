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
