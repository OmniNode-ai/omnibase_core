# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Port the retired topic handler's acceptance, suppression and CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.hardcoded_topic_check.model_hardcoded_topic_check_input import (
    ModelHardcodedTopicCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.handler import (
    NodeHardcodedTopicCheckCompute,
)
from omnibase_core.nodes.node_hardcoded_topic_check_compute.runtime_hardcoded_topic_check import (
    main,
)

pytestmark = pytest.mark.unit

_VIOLATION_FIXTURES: tuple[str, ...] = (
    'TOPIC = "onex' + '.generation.benchmark.completed"',
    'await bus.publish("onex' + '.delegation.attempt.started", env)',
    "SWEEP_TOPIC = 'onex" + ".aislop.sweep.completed'",
    'RESULT_TOPIC = "onex' + '.review.verdict.posted"',
    'EVT = "onex' + '.runtime.node.deploy.requested"',
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    'topic = self._contract.topics["benchmark_completed"]',
    "from omnimarket.nodes.node_generation_consumer.models import x",
    'NAMESPACE = "onex' + '.core"',
    'LEGACY = "kafka' + '.cluster.broker.id"',
)


def _scan(source: str, path: str = "<input>") -> ModelValidationReport:
    return NodeHardcodedTopicCheckCompute().handle(
        ModelHardcodedTopicCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


@pytest.mark.parametrize("source", _VIOLATION_FIXTURES)
def test_every_violation_fixture_is_flagged(source: str) -> None:
    report = _scan(source)
    assert report.overall_status == "FAIL", f"violation fixture not flagged: {source!r}"
    assert report.findings, "a flagged result must carry at least one finding"


@pytest.mark.parametrize("source", _CLEAN_FIXTURES)
def test_every_clean_fixture_passes(source: str) -> None:
    report = _scan(source)
    assert report.overall_status == "PASS", f"clean fixture false-flagged: {source!r}"
    assert report.findings == ()


def test_finding_carries_topic_line_context() -> None:
    topic = "onex" + ".generation.benchmark.completed"
    source = f'TOPIC = "{topic}"'
    report = _scan(source)
    assert report.overall_status == "FAIL"
    (finding,) = report.findings
    assert finding.evidence["topic"] == topic
    assert finding.location == "<input>:1"
    assert topic in str(finding.evidence["context"])
    assert finding.rule_id == "hardcoded-topic-literal"
    assert finding.message == f"<input>:1: [{topic}] {source}"


def test_inline_publish_call_topic_is_flagged() -> None:
    topic = "onex" + ".delegation.attempt.started"
    report = _scan(f'await bus.publish("{topic}", envelope)')
    assert report.overall_status == "FAIL"
    (finding,) = report.findings
    assert finding.evidence["topic"] == topic


def test_two_segment_onex_string_is_below_topic_shape() -> None:
    assert _scan('NAMESPACE = "onex' + '.core"').overall_status == "PASS"
    assert _scan('X = "onex' + '.cmd"').overall_status == "PASS"


def test_non_onex_dotted_string_is_not_flagged() -> None:
    assert _scan('LEGACY = "kafka' + '.cluster.broker.id"').overall_status == "PASS"


def test_unquoted_dotted_module_path_is_not_flagged() -> None:
    assert (
        _scan("from omnimarket.nodes.node_x.models import y").overall_status == "PASS"
    )


def test_mismatched_quote_fragment_is_not_flagged() -> None:
    assert _scan('X = "onex' + ".a.b.c'").overall_status == "PASS"


def test_handler_returns_compute_result() -> None:
    report = _scan('T = "onex' + '.generation.benchmark.completed"', path="f.py")
    assert report is not None
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "f.py:1"


def test_findings_are_order_independent() -> None:
    first = "onex" + ".a.b.c"
    second = "onex" + ".d.e.f"
    findings = _scan(f'A = "{first}"\nB = "{second}"').findings
    assert [finding.location for finding in findings] == ["<input>:1", "<input>:2"]
    assert [finding.evidence["topic"] for finding in findings] == [first, second]


def test_line_marker_suppresses_only_that_line() -> None:
    first = "onex" + ".a.b.c"
    second = "onex" + ".d.e.f"
    marker = "onex" + "-allow-topic-literal"
    source = f'A = "{first}"  # {marker} approved SOT\nB = "{second}"'
    findings = _scan(source).findings
    assert [finding.location for finding in findings] == ["<input>:2"]


def test_file_marker_suppresses_the_whole_file() -> None:
    first = "onex" + ".a.b.c"
    second = "onex" + ".d.e.f"
    third = "onex" + ".g.h.i.j"
    marker = "onex" + "-allow-file-topic-literal"
    source = f'# {marker} registry SOT\nA = "{first}"\nB = "{second}"\nC = "{third}"'
    report = _scan(source)
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_runner_blocks_on_violation_and_passes_when_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    topic = "onex" + ".runtime.node.deploy.requested"
    source = f'T = "{topic}"\n'
    bad = tmp_path / "bad.py"
    bad.write_text(source, encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text('topic = self._contract.topics["deploy"]\n', encoding="utf-8")
    assert main([str(bad), "--quiet"]) == 1
    assert capsys.readouterr().out == f"{bad}:1: [{topic}] {source}"
    assert main([str(clean), "--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_runner_report_only_always_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    topic = "onex" + ".runtime.node.deploy.requested"
    source = f'T = "{topic}"\n'
    bad = tmp_path / "bad.py"
    bad.write_text(source, encoding="utf-8")
    assert main([str(bad), "--report-only", "--quiet"]) == 0
    assert capsys.readouterr().out == f"{bad}:1: [{topic}] {source}"
