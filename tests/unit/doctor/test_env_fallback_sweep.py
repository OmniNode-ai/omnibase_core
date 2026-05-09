# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Static analysis: no silent localhost env fallbacks in doctor or CLI source."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_FALLBACK_PATTERN = re.compile(
    r'os\.environ(?:\.get)?\([^)]*,\s*["\'].*localhost.*["\']'
)

_SRC_ROOT = Path(__file__).parent.parent.parent.parent / "src" / "omnibase_core"

_SCAN_MODULES = [
    _SRC_ROOT / "doctor" / "checks",
    _SRC_ROOT / "cli",
]


def _collect_violations() -> list[str]:
    violations: list[str] = []
    for module_dir in _SCAN_MODULES:
        if not module_dir.exists():
            continue
        for py_file in sorted(module_dir.rglob("*.py")):
            for lineno, line in enumerate(py_file.read_text().splitlines(), start=1):
                if _FALLBACK_PATTERN.search(line) and not line.strip().startswith("#"):
                    rel = py_file.relative_to(_SRC_ROOT.parent.parent)
                    violations.append(f"{rel}:{lineno}: {line.strip()}")
    return violations


def test_no_localhost_env_fallbacks() -> None:
    violations = _collect_violations()
    assert violations == [], (
        "Silent localhost env fallbacks found (OMN-10733):\n" + "\n".join(violations)
    )
