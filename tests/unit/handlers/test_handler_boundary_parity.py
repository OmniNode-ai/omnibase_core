# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Decisions of the OCC ``check-boundary-parity`` script, ported (OMN-20074).

The handler must reach the verdict of onex_change_control rev a89a6f30fa
(``src/onex_change_control/scripts/check_boundary_parity.py``) over fixture
repositories: a producer that no longer references its topic fails and names
the topic and the file, a clean pair passes, a pending entry inside its grace
period is skipped and one past it fails.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_boundary_parity import (
    HandlerBoundaryParity,
    load_boundary_manifest,
    load_manifest_yaml,
    main,
)
from omnibase_core.models.nodes.boundary_parity.model_boundary_parity_input import (
    ModelBoundaryParityInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_boundaries"
TOPIC = "onex.cmd.omniintelligence.claude-hook-event.v1"
PRODUCER_FILE = "src/omniclaude/hooks/topics.py"
CONSUMER_FILE = "src/omniintelligence/nodes/node_claude_hook_event_effect/contract.yaml"

MANIFEST = f"""---
version: "1"
boundaries:
  - topic_name: "{TOPIC}"
    producer_repo: omniclaude
    consumer_repo: omniintelligence
    producer_file: "{PRODUCER_FILE}"
    consumer_file: "{CONSUMER_FILE}"
    topic_pattern: "claude-hook-event\\\\.v1"
    event_schema: "ModelClaudeCodeHookEvent"
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(tmp_path: Path, *, producer: str | None, consumer: str) -> Path:
    repos = tmp_path / "repos"
    if producer is not None:
        _write(repos / "omniclaude", PRODUCER_FILE, producer)
    _write(repos / "omniintelligence", CONSUMER_FILE, consumer)
    _write(tmp_path, "manifest.yaml", MANIFEST)
    return repos


def _run(
    tmp_path: Path, repos: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    code = main(
        ["--repos-root", str(repos), "--manifest", str(tmp_path / "manifest.yaml")]
    )
    return code, capsys.readouterr().out


CLEAN_PRODUCER = (
    'CLAUDE_HOOK_EVENT = "onex.cmd.omniintelligence.claude-hook-event.v1"\n'
)
CLEAN_CONSUMER = (
    "subscribe_topics:\n  - onex.cmd.omniintelligence.claude-hook-event.v1\n"
)


def test_clean_fixture_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = _fixture(tmp_path, producer=CLEAN_PRODUCER, consumer=CLEAN_CONSUMER)
    code, out = _run(tmp_path, repos, capsys)
    assert code == 0
    assert "Total boundaries: 1" in out
    assert "  OK:       1" in out
    assert "  MISMATCH: 0" in out
    assert "All boundaries are in parity." in out


def test_producer_pattern_missing_fails_naming_topic_and_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = _fixture(
        tmp_path, producer="UNRELATED = 'nothing here'\n", consumer=CLEAN_CONSUMER
    )
    code, out = _run(tmp_path, repos, capsys)
    assert code == 1
    assert "  MISMATCH: 1" in out
    assert f"  Topic: {TOPIC}" in out
    assert "  Producer: omniclaude -> Consumer: omniintelligence" in out
    assert f"  Error: topic not found in producer: omniclaude/{PRODUCER_FILE}" in out


def test_event_name_segment_alone_satisfies_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The source's third fallback: segment 4 of the topic name ("claude-hook-event").
    repos = _fixture(
        tmp_path, producer="NAME = 'claude-hook-event'\n", consumer=CLEAN_CONSUMER
    )
    code, _ = _run(tmp_path, repos, capsys)
    assert code == 0


def test_missing_producer_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = _fixture(tmp_path, producer=None, consumer=CLEAN_CONSUMER)
    code, out = _run(tmp_path, repos, capsys)
    assert code == 1
    assert f"  Error: producer file missing: omniclaude/{PRODUCER_FILE}" in out


def test_missing_repos_root_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_path, "manifest.yaml", MANIFEST)
    code = main(
        [
            "--repos-root",
            str(tmp_path / "absent"),
            "--manifest",
            str(tmp_path / "manifest.yaml"),
        ]
    )
    assert code == 1
    assert "ERROR: Repos root not found" in capsys.readouterr().err


def _pending_request(since: str, now: datetime) -> ModelBoundaryParityInput:
    entry = load_boundary_manifest(MANIFEST)[0].model_copy(
        update={
            "status": "pending",
            "pending_since": since,
            "pending_reason": "consumer lands next",
        }
    )
    return ModelBoundaryParityInput(boundaries=[entry], files=[], now=now)


def test_pending_inside_grace_is_skipped() -> None:
    now = datetime(2026, 10, 10, 12, tzinfo=UTC)
    since = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    report = HandlerBoundaryParity().handle(_pending_request(since, now))
    assert report.results == []
    assert [e.topic_name for e in report.pending_in_grace] == [TOPIC]
    assert not report.has_mismatches


def test_pending_past_grace_fails() -> None:
    now = datetime(2026, 10, 10, 12, tzinfo=UTC)
    since = (now - timedelta(days=15)).strftime("%Y-%m-%d")
    report = HandlerBoundaryParity().handle(_pending_request(since, now))
    assert report.mismatch_count == 1
    assert report.results[0].error == (
        f"EXPIRED PENDING: {TOPIC} has been pending for 15 days (since {since}, "
        "grace period is 14 days). Reason: consumer lands next"
    )


def test_handler_reports_per_side_verdicts() -> None:
    entries = load_boundary_manifest(MANIFEST)
    report = HandlerBoundaryParity().handle(
        ModelBoundaryParityInput(
            boundaries=entries,
            files=[
                ModelSourceFile(path=f"omniclaude/{PRODUCER_FILE}", source="x = 1\n"),
                ModelSourceFile(
                    path=f"omniintelligence/{CONSUMER_FILE}", source=CLEAN_CONSUMER
                ),
            ],
            now=datetime(2026, 10, 10, tzinfo=UTC),
        )
    )
    (result,) = report.results
    assert result.producer_file_exists
    assert not result.producer_ok
    assert result.consumer_ok


def test_packaged_manifest_is_the_occ_manifest() -> None:
    expected = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    text = load_manifest_yaml()
    parsed = json.dumps(yaml.safe_load(text), sort_keys=True).encode("utf-8")
    assert (
        hashlib.sha256(parsed).hexdigest() == expected["kafka_boundaries_parsed_sha256"]
    )
    assert len(load_boundary_manifest(text)) == 6
