# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""omnibase_core's omnibase-spi dev-tag pin (OMN-9050).

The Pre-commit Suite's stale_pin check turned dev red on 2026-11-01 when the
pin dev-20261028203020-ce27d197198f trailed the newest spi dev tag by 12
merges and 78 hours. These cases hold the pin at or after the tag that cleared
it, and hold uv.lock to the same tag as pyproject.toml.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLEARING_TAG = "dev-20261101025141-38465d47118c"
DEV_TAG = re.compile(r"^dev-(\d{14})-[0-9a-f]{12}$")
LOCK_TAG = re.compile(r"omnibase_spi\.git\?tag=(dev-\d{14}-[0-9a-f]{12})")


def _pyproject_spi_tag() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tag = data["tool"]["uv"]["sources"]["omnibase-spi"]["tag"]
    assert isinstance(tag, str)
    return tag


@pytest.mark.unit
def test_spi_pin_is_at_or_after_clearing_tag() -> None:
    tag = _pyproject_spi_tag()
    match = DEV_TAG.match(tag)
    assert match is not None, f"omnibase-spi pin {tag!r} is not a dev merge tag"
    clearing = DEV_TAG.match(CLEARING_TAG)
    assert clearing is not None
    assert match.group(1) >= clearing.group(1), (
        f"omnibase-spi pin {tag} predates {CLEARING_TAG}"
    )


@pytest.mark.unit
def test_uv_lock_spi_tag_matches_pyproject() -> None:
    lock_tags = set(
        LOCK_TAG.findall((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    )
    assert lock_tags == {_pyproject_spi_tag()}
