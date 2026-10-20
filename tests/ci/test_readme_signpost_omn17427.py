# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427 AC23: the README opens with a short knowledge-base signpost.

Release notes may follow the signpost under a level-two heading without
contributing to its line count or satisfying its knowledge-base link check.
"""

from __future__ import annotations

from itertools import takewhile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_URL = "https://github.com/OmniNode-ai/knowledge_base"
MIN_SIGNPOST_LINES = 3
MAX_SIGNPOST_LINES = 5


def _signpost(text: str) -> list[str]:
    return list(takewhile(lambda line: not line.startswith("## "), text.splitlines()))


def _signpost_ok(text: str) -> bool:
    signpost = _signpost(text)
    return MIN_SIGNPOST_LINES <= len(
        signpost
    ) <= MAX_SIGNPOST_LINES and KNOWLEDGE_BASE_URL in "\n".join(signpost)


def test_repository_readme_opens_with_signpost() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert _signpost_ok(readme), _signpost(readme)


def test_release_notes_after_signpost_are_allowed() -> None:
    readme = "\n".join(
        ["# Repository", "", "Repository description.", KNOWLEDGE_BASE_URL]
        + ["## v0.0.1 (2026-01-01)"]
        + [f"- Release note {i}" for i in range(20)]
    )
    assert _signpost_ok(readme)


def test_long_prose_readme_is_refused() -> None:
    readme = "\n".join([KNOWLEDGE_BASE_URL] + [f"Prose line {i}" for i in range(11)])
    assert not _signpost_ok(readme)


def test_signpost_without_knowledge_base_link_is_refused() -> None:
    readme = "\n".join(
        ["# Repository", "", "Repository description.", "Documentation elsewhere."]
        + ["## v0.0.1", KNOWLEDGE_BASE_URL]
    )
    assert not _signpost_ok(readme)


def test_signpost_over_five_lines_is_refused() -> None:
    readme = "\n".join(
        [KNOWLEDGE_BASE_URL] + [f"Signpost line {i}" for i in range(6)] + ["## v0.0.1"]
    )
    assert not _signpost_ok(readme)
