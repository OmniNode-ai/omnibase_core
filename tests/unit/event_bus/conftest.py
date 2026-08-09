# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Registers the ``event_bus_substrate`` / ``fidelity_event_bus_substrate``
fixtures (OMN-15789) for this test package.

Importing a fixture function by name into a ``conftest.py`` is what
registers it with pytest -- the fixtures themselves live in
``omnibase_core.event_bus.testing`` so ``omnibase_infra`` can import and
extend the same names (see that package's module docstring).
"""

from __future__ import annotations

from omnibase_core.event_bus.testing.fixture_event_bus_substrate import (
    event_bus_substrate,
    fidelity_event_bus_substrate,
)

__all__: list[str] = ["event_bus_substrate", "fidelity_event_bus_substrate"]
