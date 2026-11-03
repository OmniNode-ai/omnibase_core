# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-21516: the pin-parity check has one home, the core node.

The repo-local script copy is gone and the pre-commit config runs the node
through the ``check-precommit-pin-parity`` hook id only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[3]
_NODE_MODULE = (
    "omnibase_core.nodes.node_precommit_rev_time_effect.runtime_precommit_pin_parity"
)


def _hooks() -> list[dict[str, object]]:
    config = yaml.safe_load((_ROOT / ".pre-commit-config.yaml").read_text())
    return [hook for repo in config["repos"] for hook in repo.get("hooks", [])]


@pytest.mark.unit
def test_local_script_copy_is_deleted() -> None:
    script = _ROOT / "scripts" / "validation" / "validate_precommit_pin_parity.py"
    assert not script.exists()


@pytest.mark.unit
def test_old_local_hook_id_is_gone() -> None:
    assert "precommit-pin-parity" not in {hook["id"] for hook in _hooks()}


@pytest.mark.unit
def test_pin_parity_hook_runs_the_core_node() -> None:
    [hook] = [h for h in _hooks() if h["id"] == "check-precommit-pin-parity"]
    assert _NODE_MODULE in str(hook["entry"])
    assert "validate_precommit_pin_parity.py" not in str(hook["entry"])
