# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-23015: no source file reads a stream through click's deprecated getters.

``click.get_text_stream`` and ``click.get_binary_stream`` are reachable in click
8.5 only through that package's module-level ``__getattr__``, which is annotated
``-> object``. A call on the result is therefore ``"object" not callable`` under
strict mypy, whatever mypy's own version: measured 2026-11-07 on the 0.47.69
release branch, where the refresh moved click 8.3.1 to 8.5.1, strict mypy 1.19.1
reported ``src/omnibase_core/cli/cli_bootstrap.py:45: error: "object" not
callable  [operator]`` while dev at the same mypy was clean. Both names also
emit a DeprecationWarning and are slated for removal in Click 9.0, so the fix is
``sys.stdin`` and ``sys.stdin.buffer``, which ``CliRunner(input=...)`` replaces
exactly as click's own getters read.

This test fails on a tree where any source file calls either getter, which is
what the merge base looks like.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

#: Reachable only through click's ``__getattr__(name) -> object`` since 8.5.
DEPRECATED = ("get_text_stream", "get_binary_stream")


def test_no_source_file_calls_a_deprecated_click_stream_getter() -> None:
    """One such call fails strict mypy as soon as a refresh resolves click 8.5."""
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name in DEPRECATED:
            if f"click.{name}" in text or f"from click import {name}" in text:
                offenders.append(f"{path.relative_to(ROOT)}: {name}")
    assert not offenders, (
        "these files read a stream through a click getter that click 8.5 exposes "
        "only as `object`, so strict mypy fails on the call and Click 9.0 removes "
        f"the name; use sys.stdin instead: {offenders}"
    )
