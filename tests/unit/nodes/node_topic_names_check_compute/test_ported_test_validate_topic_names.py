# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Assertions ported from the deleted topic-name validator tests."""

from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.topic_names_check.model_topic_names_check_input import (
    ModelTopicNamesCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_topic_names_check_compute.handler import (
    NodeTopicNamesCheckCompute,
)
from omnibase_core.nodes.node_topic_names_check_compute.matcher_topic_names import (
    extract_topics,
)
from omnibase_core.nodes.node_topic_names_check_compute.runtime_topic_names_check import (
    main,
)

pytestmark = pytest.mark.unit


def check(value: str) -> ModelValidationReport:
    return NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(
            files=[
                ModelSourceFile(path="topics.py", source=f'TOPIC_CASE = "{value}"\n')
            ]
        )
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(
            "onex." + "evt.omnimemory.intent-stored.v1",
            id="test_valid_canonical_topic_passes",
        ),
        pytest.param(
            "onex." + "cmd.user-service.create-account.v2",
            id="test_valid_canonical_cmd_topic_passes",
        ),
        pytest.param(
            "onex." + "dlq.service-a.failed-event.v1", id="test_valid_dlq_topic_passes"
        ),
        pytest.param(
            "onex." + "snapshot.registry.state-dump.v1",
            id="test_valid_snapshot_topic_passes",
        ),
    ],
)
def test_valid_topics(value: str) -> None:
    report = check(value)
    assert report.overall_status == "PASS"
    assert report.findings == ()


def test_env_prefixed_topic_fails() -> None:
    value = "{env}." + "onex." + "evt.omnimemory.intent-stored.v1"
    report = check(value)
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert "{env}." in finding.message
    assert finding.message == f"topic uses {{env}}. prefix (legacy pattern): {value}"
    assert finding.rule_id == "env-prefix"
    assert finding.location == "topics.py:1"


def test_flat_legacy_topic_fails() -> None:
    report = check("agent-actions")
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert "flat" in finding.message.lower()
    assert (
        finding.message
        == "flat legacy topic name (must use onex.<kind>.<producer>.<event>.v<n>): agent-actions"
    )
    assert finding.rule_id == "flat-topic"
    assert finding.location == "topics.py:1"


def test_invalid_kind_fails() -> None:
    report = check("onex." + "events.omnimemory.intent-stored.v1")
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert "Kind" in finding.message or "kind" in finding.message.lower()
    assert finding.rule_id == "canonical-suffix"
    assert finding.location == "topics.py:1"


@pytest.mark.parametrize(
    ("filename", "first", "second", "source"),
    [
        pytest.param(
            "constants_topics.py",
            "onex." + "evt.omnimemory.intent-stored.v1",
            "onex." + "dlq.service.failed.v1",
            'TOPIC_INTENT_STORED = "{first}"\nSUFFIX_DLQ = "{second}"\nUNRELATED_VAR = "not-a-topic"\n',
            id="test_scan_python_file_extracts_topics",
        ),
        pytest.param(
            "topics.ts",
            "onex." + "cmd.agent.run-action.v1",
            "onex." + "snapshot.dash.state.v1",
            'export const TOPIC_AGENT_ACTION = "{first}"\nexport const SUFFIX_SNAPSHOT = "{second}"\nconst PRIVATE_VAR = "not-exported"\n',
            id="test_scan_typescript_file_extracts_topics",
        ),
    ],
)
def test_scan_file_extracts_topics(
    filename: str,
    first: str,
    second: str,
    source: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / filename
    path.write_text(source.format(first=first, second=second), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    report = NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(files=[ModelSourceFile(path=str(path), source=text)])
    )
    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert extract_topics(str(path), text) == [(1, first), (2, second)]
    assert main([str(path), "--verbose"]) == 0
    assert capsys.readouterr().out == (
        "Scanned 1 files, found 2 topic constants\n"
        "OK: 2 topic(s) validated across 1 file(s)\n"
    )


def test_scan_file_nonexistent_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "does_not_exist.py"
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(root=str(tmp_path), explicit_paths=[str(path)])
    )
    assert not path.exists()
    assert gathered.files == []
    report = NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(
            files=[
                ModelSourceFile(path=file.path, source=file.source)
                for file in gathered.files
            ]
        )
    )
    assert report.findings == ()
    assert report.overall_status == "PASS"


def test_scan_file_unsupported_extension_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "topics.txt"
    value = "onex." + "evt.svc.event.v1"
    path.write_text(f'TOPIC_FOO = "{value}"\n')
    source = path.read_text()
    report = NodeTopicNamesCheckCompute().handle(
        ModelTopicNamesCheckInput(
            files=[ModelSourceFile(path=str(path), source=source)]
        )
    )
    assert extract_topics(str(path), source) == []
    assert report.findings == ()
    assert report.overall_status == "PASS"


def test_repo_with_valid_topics_exits_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = "onex." + "evt.service-a.event-one.v1"
    second = "onex." + "cmd.service-b.do-thing.v2"
    (tmp_path / "constants_topics.py").write_text(
        f'TOPIC_A = "{first}"\nTOPIC_B = "{second}"\n', encoding="utf-8"
    )
    destination = tmp_path / "report.json"
    assert main([str(tmp_path), "--verbose", "--report-json", str(destination)]) == 0
    output = capsys.readouterr()
    assert output.out == (
        "Scanned 1 files, found 2 topic constants\n"
        "OK: 2 topic(s) validated across 1 file(s)\n"
    )
    assert output.err == ""
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "PASS"
    assert report.findings == ()


@pytest.mark.parametrize(
    ("constant", "value", "rule", "fragment"),
    [
        pytest.param(
            "TOPIC_LEGACY",
            "agent-actions",
            "flat-topic",
            "flat",
            id="test_repo_with_legacy_topic_has_violations",
        ),
        pytest.param(
            "TOPIC_OLD",
            "{env}." + "onex." + "evt.service.event.v1",
            "env-prefix",
            "{env}.",
            id="test_repo_with_env_prefix_has_violations",
        ),
    ],
)
def test_repo_has_violations(
    constant: str,
    value: str,
    rule: str,
    fragment: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "constants_topics.py").write_text(
        f'{constant} = "{value}"\n', encoding="utf-8"
    )
    destination = tmp_path / "report.json"
    assert main([str(tmp_path), "--report-json", str(destination)]) == 1
    report = ModelValidationReport.model_validate_json(destination.read_text())
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert fragment in finding.message.lower()
    assert finding.rule_id == rule
    assert finding.location == "constants_topics.py:1"
    output = capsys.readouterr()
    assert (
        output.out
        == f"FAIL: 1 violation(s) found:\n\n  {finding.location}: {finding.message}\n"
    )
    assert output.err == ""
