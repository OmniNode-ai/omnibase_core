# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One deterministic planted layout for the unit runtime and both overlay runs."""

from __future__ import annotations

import shutil
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/contract_chain_coverage"


def stage_planted(root: Path) -> list[str]:
    """Stage contracts under src/pkg and bindings under the cwd-relative tests root."""
    paths = []
    for source in sorted((_FIXTURES / "planted").glob("*/contract.yaml")):
        relative = Path("src/pkg") / source.parent.name / source.name
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
        paths.append(relative.as_posix())
    tests = root / "tests/test_planted_chains.py.txt"
    tests.parent.mkdir(parents=True, exist_ok=True)
    source_text = (_FIXTURES / "planted/tests/test_planted_chains.py.txt").read_text()
    for owner in ("orchestrator", "reducer"):
        source_text = source_text.replace(
            f'"{owner}/contract.yaml', f'"src/pkg/{owner}/contract.yaml'
        )
    tests.write_text(source_text)
    return paths
