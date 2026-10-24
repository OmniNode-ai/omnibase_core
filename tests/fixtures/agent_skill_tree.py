# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Agent Skills fixture tree for the OMN-21373 suite.

The fixtures are SKILL.md files, and this repository tracks no Markdown file
but its root README, so they are kept as one JSON map from relative path to
file text and written out to a temporary skill tree when a test first asks
for it. The reference validator reads skill directories, so the tree keeps
each fixture's directory name.
"""

from __future__ import annotations

import functools
import json
import tempfile
from pathlib import Path

FIXTURE_DATA = (
    Path(__file__).resolve().parent / "agent_skills" / "agent_skill_fixtures.json"
)


@functools.cache
def agent_skill_fixture_root() -> Path:
    """Write the fixture tree once per process and return its root."""
    files: dict[str, str] = json.loads(FIXTURE_DATA.read_text(encoding="utf-8"))
    root = Path(tempfile.mkdtemp(prefix="agent-skill-fixtures-"))
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    return root
