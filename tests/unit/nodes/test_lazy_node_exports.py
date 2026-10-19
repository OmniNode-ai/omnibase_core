# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node package exports stay compatible without loading unrelated runtimes."""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest

import omnibase_core.nodes as nodes

pytestmark = pytest.mark.unit


def test_ledger_startup_does_not_load_base_node_implementations() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "import omnibase_core.nodes.node_work_ledger_state_compute.runtime_work_ledger; "
            "assert not {"
            "'omnibase_core.nodes.node_compute', "
            "'omnibase_core.nodes.node_effect', "
            "'omnibase_core.nodes.node_orchestrator', "
            "'omnibase_core.nodes.node_reducer'"
            "}.intersection(sys.modules)",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("name", nodes.__all__)
def test_public_export_is_the_concrete_symbol_and_is_cached(name: str) -> None:
    value = getattr(nodes, name)
    concrete_module = importlib.import_module(value.__module__)
    assert value is getattr(concrete_module, name)
    assert nodes.__dict__[name] is value


def test_unknown_export_raises_attribute_error() -> None:
    name = "missing_node_export"
    with pytest.raises(AttributeError, match=name):
        getattr(nodes, name)
