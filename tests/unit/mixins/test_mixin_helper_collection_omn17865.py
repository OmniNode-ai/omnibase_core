# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Collection regression for test-only mixin helper classes (OMN-17865).

Three mixin test modules define helper classes whose names begin with ``Test``
and which carry a constructor. Pytest tries to collect them and emits
``PytestCollectionWarning``, which fails collection once warnings are promoted
to errors. Each helper is a fixture for the real ``Test...`` classes in the
same module, so the helpers must opt out of collection with a class-local
``__test__ = False`` while the real tests keep running.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]

# module -> helper class that must not be collected
_HELPERS_BY_MODULE = {
    "tests/unit/mixins/test_mixin_contract_state_reducer.py": "TestNode",
    "tests/unit/mixins/test_mixin_effect_execution.py": "TestNode",
    "tests/unit/mixins/test_mixin_event_bus.py": "TestMixinNode",
}


def _collect(module: str) -> subprocess.CompletedProcess[str]:
    """Collect one module with collection warnings promoted to errors."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            module,
            "--collect-only",
            "--color=no",
            "-n",
            "0",
            "-p",
            "no:cacheprovider",
            "-W",
            "error::pytest.PytestCollectionWarning",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=50,
        check=False,
    )


@pytest.mark.parametrize(("module", "helper"), sorted(_HELPERS_BY_MODULE.items()))
def test_helper_class_collects_without_warning(module: str, helper: str) -> None:
    result = _collect(module)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PytestCollectionWarning" not in result.stdout + result.stderr
    output = result.stdout
    # The helper is not collected, but the module's real test classes still are.
    assert f"<Class {helper}>" not in output
    assert "<Class Test" in output
    assert "<Function test_" in output
