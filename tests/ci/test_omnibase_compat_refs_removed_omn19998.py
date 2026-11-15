# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-19998: configuration and live code that named the retired compat package are gone.

RULING 2026-11-15T17:59:49Z removed the compat repository. The downstream
manifest, the bypass-token blocklist repo list and the parity-gate comments no
longer point at it, and the shim and base-class modules no longer describe it
as a home. The retired-repo guard in ``repo_layers.yaml`` keeps naming it on
purpose, so that file is not listed here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
_RETIRED = re.compile(r"omnibase[_-]compat", re.IGNORECASE)

_CLEARED_FILES = (
    ".github/workflows/validator-bypass-token-blocklist.yml",
    ".github/workflows/precommit-parity-gate.yml",
    ".pre-commit-hooks.yaml",
    "docs/downstream-repos.yaml",
    "src/omnibase_core/decorators/decorator_shim.py",
    "src/omnibase_core/enums/enum_str_enum_base.py",
    "src/omnibase_core/types/type_json.py",
    "src/omnibase_core/utils/util_str_enum_base.py",
)


@pytest.mark.parametrize("rel", _CLEARED_FILES)
def test_cleared_file_does_not_name_the_retired_package(rel: str) -> None:
    hits = [
        f"{number}: {line.strip()}"
        for number, line in enumerate(
            (REPO_ROOT / rel).read_text(encoding="utf-8").splitlines(), start=1
        )
        if _RETIRED.search(line)
    ]
    assert not hits, f"{rel} still names the retired package: {hits}"


def test_retired_layer_guard_still_names_the_package() -> None:
    """Positive control: the pattern matches where the retirement is declared."""
    text = (REPO_ROOT / "src/omnibase_core/contracts/repo_layers.yaml").read_text(
        encoding="utf-8"
    )
    assert _RETIRED.search(text), "the retired-layer declaration must keep naming it"
