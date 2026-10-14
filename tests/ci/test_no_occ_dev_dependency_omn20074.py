# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: omnibase_core's dev environment no longer installs onex_change_control.

The governance hooks that the dev dependency once supplied were ported into
omnibase_core, so nothing imports the package or runs its console scripts. The
dependency, its git source pin and its lock entry go together, otherwise every
``uv sync`` keeps cloning the retiring repository.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
OCC_NAME = "onex-change-control"


def _normalize(requirement: str) -> str:
    name = re.split(r"[\s<>=!~;\[@]", requirement.strip(), maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def _pyproject() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_no_dependency_group_names_onex_change_control() -> None:
    groups = _pyproject().get("dependency-groups", {})
    offenders = [
        (group, req)
        for group, reqs in groups.items()
        for req in reqs
        if isinstance(req, str) and _normalize(req) == OCC_NAME
    ]
    assert offenders == []


def test_no_uv_source_pins_onex_change_control() -> None:
    sources = _pyproject().get("tool", {}).get("uv", {}).get("sources", {})
    assert OCC_NAME not in {_normalize(name) for name in sources}


def test_lock_carries_no_onex_change_control_package() -> None:
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    names = {_normalize(pkg["name"]) for pkg in lock.get("package", [])}
    assert "omnibase-core" in names  # positive control: the lock was parsed
    assert OCC_NAME not in names
    assert "onex_change_control.git" not in (REPO_ROOT / "uv.lock").read_text(
        encoding="utf-8"
    )
