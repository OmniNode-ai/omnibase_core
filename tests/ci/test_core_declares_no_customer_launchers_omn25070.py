# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-25070 AC3: only the customer package omninode-onex declares onex and omni-agent.

omnibase_core stops declaring both in the release that publishes omninode-onex, so an
install never has two owners of one launcher. Developers and CI run the same CLI as
python -m omnibase_core.cli.cli_commands.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOMER_LAUNCHERS = frozenset({"onex", "omni-agent"})


def _declared_customer_launchers(pyproject_text: str) -> frozenset[str]:
    """Return the customer launcher names declared in the given pyproject text."""
    data = tomllib.loads(pyproject_text)
    scripts: dict[str, str] = data.get("project", {}).get("scripts", {})
    return frozenset(name for name in scripts if name in CUSTOMER_LAUNCHERS)


@pytest.mark.unit
def test_core_declares_no_customer_launcher() -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert _declared_customer_launchers(text) == frozenset(), (
        "onex and omni-agent are declared by omninode-onex only (OMN-25070 AC3, "
        "one owner per launcher); omnibase_core must not declare them"
    )


@pytest.mark.unit
def test_the_reader_sees_a_declared_launcher() -> None:
    text = (
        '[project]\n'
        'name = "x"\n'
        "[project.scripts]\n"
        'onex = "omnibase_core.cli.cli_commands:cli"\n'
        'other = "x:y"\n'
    )
    assert _declared_customer_launchers(text) == frozenset({"onex"})
    assert _declared_customer_launchers('[project]\nname = "x"\n') == frozenset()


@pytest.mark.unit
def test_the_cli_still_runs_as_a_module() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "omnibase_core.cli.cli_commands", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"python -m omnibase_core.cli.cli_commands --help failed "
        f"(returncode={result.returncode}); stdout={result.stdout!r} stderr={result.stderr!r}"
    )
