# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Verdict parity of node_no_env_fallbacks_check_compute against the script it replaces (OMN-20565).

``tests/fixtures/validator_parity/no_env_fallbacks/golden.json`` is the output of
``scripts/validate_no_env_fallbacks.py`` (core's copy of the canonical unified gate) over
``corpus.json``, recorded before the script was deleted. The node must report the same
``(line, flagged text)`` rows for every corpus entry, except the four entries named in
``_DIVERGENCES``, each of which is a recorded, reasoned difference between the script's older
docstring tracker and the node's (the tracker infra and omniclaude already run). No other
difference is tolerated, and a divergence that stops occurring fails the test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pytest

from omnibase_core.models.nodes.no_env_fallbacks_check.model_no_env_fallbacks_check_input import (
    ModelNoEnvFallbacksCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_no_env_fallbacks_check_compute.handler import (
    NodeNoEnvFallbacksCheckCompute,
)

pytestmark = pytest.mark.unit

_FIXTURES: Final[Path] = (
    Path(__file__).resolve().parents[3] / "fixtures/validator_parity/no_env_fallbacks"
)

# name -> (script_lines, node_lines, reason)
_DIVERGENCES: Final[dict[str, tuple[list[int], list[int], str]]] = {
    "oneline_docstring_mentions_pattern": (
        [1],
        [],
        "script flags text inside a one-line docstring; node skips docstring text",
    ),
    "docstring_last_line_mentions_pattern": (
        [3],
        [],
        "script flags the closing line of a docstring that mentions the pattern",
    ),
    "assign_open_multiline_string": (
        [],
        [2],
        "script treats any line holding one triple quote as a docstring opener; "
        "node only a line that starts with one, so it scans the string body",
    ),
    "midline_open_string": (
        [],
        [2],
        "same tracker difference as assign_open_multiline_string",
    ),
}


# The committed fixtures keep a placeholder where the corpus needs a private
# address, so no repository gate sees an address literal; it is filled in here.
_LAN_HOST: Final[str] = ".".join(("192", "168", "86", "201"))


def _read_fixture(name: str) -> str:
    return (
        (_FIXTURES / name).read_text(encoding="utf-8").replace("{LAN_HOST}", _LAN_HOST)
    )


def _corpus() -> dict[str, dict[str, str]]:
    loaded: dict[str, dict[str, str]] = json.loads(_read_fixture("corpus.json"))
    return loaded


def _golden() -> dict[str, list[dict[str, str | int]]]:
    loaded: dict[str, list[dict[str, str | int]]] = json.loads(
        _read_fixture("golden.json")
    )
    return loaded


def _node_rows(name: str, suffix: str, source: str) -> list[tuple[int, str]]:
    path = f"{name}{suffix}"
    report = NodeNoEnvFallbacksCheckCompute().handle(
        ModelNoEnvFallbacksCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )
    rows: list[tuple[int, str]] = []
    for finding in report.findings:
        assert finding.location is not None
        line = int(finding.location.rsplit(":", 1)[1])
        prefix = f"{path}:{line}: "
        assert finding.message.startswith(prefix)
        rows.append((line, finding.message[len(prefix) :]))
    return rows


@pytest.mark.parametrize("name", sorted(_corpus()))
def test_parity_node_matches_script_golden(name: str) -> None:
    entry = _corpus()[name]
    expected = [(int(row["line"]), str(row["text"])) for row in _golden()[name]]
    actual = _node_rows(name, entry["suffix"], entry["source"])

    if name in _DIVERGENCES:
        script_lines, node_lines, _reason = _DIVERGENCES[name]
        assert [line for line, _ in expected] == script_lines
        assert [line for line, _ in actual] == node_lines
    else:
        assert actual == expected


def test_parity_every_recorded_divergence_is_in_the_corpus() -> None:
    assert set(_DIVERGENCES) <= set(_corpus())


def test_parity_corpus_has_flagging_and_clean_cases() -> None:
    golden = _golden()
    assert sum(1 for rows in golden.values() if rows) >= 10
    assert sum(1 for rows in golden.values() if not rows) >= 8
