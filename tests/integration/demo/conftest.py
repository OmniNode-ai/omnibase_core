# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Demo integration tests run with the operator switch on (OMN-26518).

The root ``onex`` group lists and resolves only customer groups by default. Most
tests here exercise internal groups by name through the root group, so they run
as an operator would.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _operator_switch_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEX_CLI_SHOW_ALL_COMMANDS", "1")
