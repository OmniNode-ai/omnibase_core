# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the decisions of the OCC ``check-hardcoded-topics`` hook (OMN-20074).

The fixtures are verbatim fleet files; ``manifest.yaml`` records, per file, the
violation lines produced by onex_change_control rev 8d7e85bc00e7 for that path.
The handler must reproduce them, and the byte-exact output lines, so consumers
that change only ``repo:`` and ``rev:`` see no difference in what is flagged.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.handlers.handler_no_hardcoded_topics import (
    APPROVED_BASENAMES,
    HandlerNoHardcodedTopics,
    main,
)
from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_hardcoded_topics"
LITERAL = re.compile(r"""["']onex\.(evt|cmd)\.""")
MESSAGE = "hardcoded topic string -- use a constant from the canonical topic registry"


class _Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    repo: str
    source_path: str
    source_rev: str
    expected_violation_lines: list[int]


def _cases() -> list[_Case]:
    raw = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    return [_Case(**item) for item in raw]


def _scan(path: str, source: str) -> list[str]:
    report = HandlerNoHardcodedTopics().handle(
        ModelHardcodedTopicCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )
    return [finding.message for finding in report.findings]


def _fixture_text(case: _Case) -> str:
    return (FIXTURES / f"{case.id}.txt").read_text(encoding="utf-8", errors="replace")


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.id)
def test_fleet_file_decision_matches_the_occ_hook(case: _Case) -> None:
    messages = _scan(case.source_path, _fixture_text(case))
    assert messages == [
        f"{case.source_path}:{line}: {MESSAGE}"
        for line in case.expected_violation_lines
    ]


def test_positive_control_flags_a_real_fleet_file() -> None:
    case = next(c for c in _cases() if c.id == "positive-control-py")
    assert case.expected_violation_lines
    assert _scan(case.source_path, _fixture_text(case))


@pytest.mark.parametrize(
    "case_id",
    [
        "skip-docstring",
        "skip-comment-line",
        "skip-template-docstring-state",
        "skip-test-file",
        "skip-approved-basename-py",
        "skip-approved-basename-yaml",
    ],
)
def test_each_skip_class_is_a_skip_of_a_file_that_holds_a_literal(case_id: str) -> None:
    case = next(c for c in _cases() if c.id == case_id)
    text = _fixture_text(case)
    assert LITERAL.search(text), "a skip fixture must contain a quoted topic literal"
    assert _scan(case.source_path, text) == []


@pytest.mark.parametrize("case_id", ["skip-test-file", "skip-approved-basename-py"])
def test_path_skips_are_what_clears_the_file(case_id: str) -> None:
    case = next(c for c in _cases() if c.id == case_id)
    assert _scan("src/service.py", _fixture_text(case))


@pytest.mark.parametrize("basename", sorted(APPROVED_BASENAMES))
def test_every_approved_basename_is_skipped(basename: str) -> None:
    assert _scan(f"src/pkg/{basename}", 'T = "onex.evt.a.b.v1"\n') == []


def test_the_approved_basenames_are_the_twelve_of_the_occ_hook() -> None:
    assert (
        frozenset(
            {
                "platform_topic_suffixes.py",
                "topics.py",
                "topics.ts",
                "contract.yaml",
                "handler_contract.yaml",
                "topics.yaml",
                "contract_topic_extractor.py",
                "check_topic_drift.py",
                "topic_constants.py",
                "constants_topic_taxonomy.py",
                "topic_naming_baseline.txt",
                "governance_emitter.py",
            }
        )
        == APPROVED_BASENAMES
    )


@pytest.mark.parametrize(
    ("path", "flagged"),
    [
        ("src/a/test_service.py", False),
        ("src/a/service_test.py", False),
        ("web/a.test.ts", False),
        ("web/a.test.js", False),
        ("/repo/tests/helpers.py", False),
        # pre-commit passes repo-relative paths, and the OCC rule needs a
        # leading slash before ``tests``: a relative tests/ helper is flagged.
        ("tests/helpers.py", True),
        ("src/a/service.py", True),
    ],
)
def test_test_file_rule(path: str, flagged: bool) -> None:
    assert bool(_scan(path, 'T = "onex.cmd.a.b.v1"\n')) is flagged


@pytest.mark.parametrize(
    ("path", "flagged"),
    [
        ("src/pkg/wire_schemas/event_v1.yaml", False),
        ("src/pkg/wire_schemas/event_v12.yml", False),
        ("src/pkg/wire_schemas/event.yaml", True),
        ("src/pkg/other/event_v1.yaml", True),
        ("wire_schemas/event_v1.yaml", True),
    ],
)
def test_wire_schema_contract_skip(path: str, flagged: bool) -> None:
    assert bool(_scan(path, "topic: 'onex.evt.a.b.v1'\n")) is flagged


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ('T = "onex.evt.a.b.v1"\n', 1),
        ("T = 'onex.cmd.a.b.v1'\n", 1),
        ('T = "onex.evt.a.b.v1", "onex.cmd.a.b.v1"\n', 1),
        ('T = "onex.dlq.a.b.v1"\n', 0),
        ("T = onex.evt.a.b.v1\n", 0),
        ('T = "x.onex.evt.a.b.v1"\n', 0),
        ('# T = "onex.evt.a.b.v1"\n', 0),
        ('    // T = "onex.evt.a.b.v1"\n', 0),
        ('"""\nT = "onex.evt.a.b.v1"\n"""\n', 0),
        ("'''\nT = 'onex.evt.a.b.v1'\n'''\n", 0),
        ('"""doc"""\nT = "onex.evt.a.b.v1"\n', 1),
        ('/*\n T = "onex.evt.a.b.v1"\n*/\n', 0),
        ('/* T = "onex.evt.a.b.v1" */\nX = 1\n', 0),
        ('/* a */ T = "onex.evt.a.b.v1"\n', 0),
        ('/*\n * c\n */\nT = "onex.evt.a.b.v1"\n', 1),
        ('T = "onex.evt.a.b.v1"\nU = "onex.cmd.a.b.v1"\n', 2),
    ],
)
def test_line_rules(source: str, count: int) -> None:
    assert len(_scan("src/service.py", source)) == count


def test_non_utf8_bytes_are_replaced_not_fatal(tmp_path: Path) -> None:
    target = tmp_path / "service.py"
    target.write_bytes(b'T = "onex.evt.a.b.v1"  # \xff\xfe\n')
    assert main([str(target)]) == 1


def test_main_prints_the_occ_lines_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "service.py"
    target.write_text('T = "onex.evt.a.b.v1"\n', encoding="utf-8")
    assert main([str(target)]) == 1
    assert capsys.readouterr().out == (
        f"{target}:1: {MESSAGE}\n\n"
        "1 violation(s). Move topic strings to an approved constant file.\n"
    )


def test_main_is_silent_and_zero_on_a_clean_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "service.py"
    target.write_text("X = 1\n", encoding="utf-8")
    assert main([str(target)]) == 0
    assert capsys.readouterr().out == ""


def test_main_with_no_files_is_zero() -> None:
    assert main([]) == 0


def test_an_unreadable_named_file_is_an_error_not_a_pass(tmp_path: Path) -> None:
    assert main([str(tmp_path / "missing.py")]) == 1
