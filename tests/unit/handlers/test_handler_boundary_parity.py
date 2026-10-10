# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the OCC ``check-boundary-parity`` decisions (OMN-20074).

Each case builds a fixture tree of peer repositories under ``tmp_path`` and runs
the core handler over it. The expected report text of the clean, break and
missing-file cases was recorded by running onex_change_control rev a89a6f30fabf
``check_boundary_parity.py`` on the same trees; the handler must reproduce it
byte for byte so a consumer that repoints sees the same verdict and output.
"""

from __future__ import annotations

import importlib.resources
from datetime import date
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_boundary_parity import (
    MANIFEST_RESOURCE,
    HandlerBoundaryParity,
    main,
)
from omnibase_core.models.nodes.boundary_validation.model_boundary_parity_input import (
    ModelBoundaryParityInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

pytestmark = pytest.mark.unit

# The six boundaries of onex_change_control src/onex_change_control/boundaries/kafka_boundaries.yaml,
# identical at main a89a6f30fabf and dev da751e728024: (topic, producer repo, consumer repo,
# producer file, consumer file, topic pattern, status).
OCC_BOUNDARIES = [
    (
        "onex.cmd.omniintelligence.claude-hook-event.v1",
        "omniclaude",
        "omniintelligence",
        "src/omniclaude/hooks/topics.py",
        "src/omniintelligence/nodes/node_claude_hook_event_effect/contract.yaml",
        "claude-hook-event\\.v1",
        None,
    ),
    (
        "onex.cmd.omniintelligence.tool-content.v1",
        "omniclaude",
        "omniintelligence",
        "src/omniclaude/hooks/topics.py",
        "src/omniintelligence/nodes/node_claude_hook_event_effect/contract.yaml",
        "tool-content\\.v1",
        None,
    ),
    (
        "onex.cmd.omniintelligence.session-outcome.v1",
        "omniclaude",
        "omniintelligence",
        "src/omniclaude/hooks/topics.py",
        "src/omniintelligence/nodes/node_pattern_feedback_effect/contract.yaml",
        "session-outcome\\.v1",
        None,
    ),
    (
        "onex.cmd.omniintelligence.compliance-evaluate.v1",
        "omniclaude",
        "omniintelligence",
        "src/omniclaude/hooks/topics.py",
        "src/omniintelligence/nodes/node_compliance_evaluate_effect/contract.yaml",
        "compliance-evaluate\\.v1",
        None,
    ),
    (
        "onex.evt.omniintelligence.intent-classified.v1",
        "omniintelligence",
        "omnimarket",
        "src/omniintelligence/nodes/node_claude_hook_event_effect/contract.yaml",
        "src/omnimarket/nodes/node_intent_event_consumer_effect/contract.yaml",
        "intent-classified\\.v1",
        None,
    ),
    (
        "onex.evt.onex-change-control.contract-drift-detected.v1",
        "onex_change_control",
        "omniclaude",
        "src/onex_change_control/nodes/node_contract_drift_effect/contract.yaml",
        "src/omniclaude/hooks/topics.py",
        "contract-drift-detected\\.v1",
        "active",
    ),
]

TOPIC = "onex.cmd.beta.hook-event.v1"
PRODUCER_FILE = "src/alpha/topics.py"
CONSUMER_FILE = "src/beta/nodes/node_hook_effect/contract.yaml"

MANIFEST = f"""---
version: "1"
boundaries:
  - topic_name: "{TOPIC}"
    producer_repo: alpha
    consumer_repo: beta
    producer_file: "{PRODUCER_FILE}"
    consumer_file: "{CONSUMER_FILE}"
    topic_pattern: "hook-event\\\\.v1"
    event_schema: "ModelHookEvent"
  - topic_name: "onex.evt.beta.widget-built.v1"
    producer_repo: beta
    consumer_repo: alpha
    producer_file: "{CONSUMER_FILE}"
    consumer_file: "{PRODUCER_FILE}"
    topic_pattern: "widget-built\\\\.v1"
    event_schema: "ModelWidgetBuilt"
"""

PRODUCER_CLEAN = (
    f'HOOK_EVENT = "{TOPIC}"\nWIDGET_BUILT = "onex.evt.beta.widget-built.v1"\n'
)
PRODUCER_BROKEN = (
    'HOOK_EVENT = "onex.cmd.beta.other-thing.v2"\n'
    'WIDGET_BUILT = "onex.evt.beta.widget-built.v1"\n'
)
CONSUMER = (
    "event_bus:\n"
    "  subscribe_topics:\n"
    f"    - {TOPIC}\n"
    "  publish_topics:\n"
    "    - onex.evt.beta.widget-built.v1\n"
)

# Recorded from onex_change_control rev a89a6f30fabf check_boundary_parity.py.
EXPECTED_CLEAN = """\
========================================================================
Kafka Boundary Parity Report
========================================================================

Total boundaries: 2
  OK:       2
  MISMATCH: 0

All boundaries are in parity.

"""
EXPECTED_BROKEN = """\
========================================================================
Kafka Boundary Parity Report
========================================================================

Total boundaries: 2
  OK:       1
  MISMATCH: 1

------------------------------------------------------------------------
MISMATCHES:
------------------------------------------------------------------------

  Topic: onex.cmd.beta.hook-event.v1
  Producer: alpha -> Consumer: beta
  Error: topic not found in producer: alpha/src/alpha/topics.py

------------------------------------------------------------------------
OK boundaries:
------------------------------------------------------------------------
  [OK] onex.evt.beta.widget-built.v1 (beta -> alpha)

"""
EXPECTED_MISSING = """\
========================================================================
Kafka Boundary Parity Report
========================================================================

Total boundaries: 2
  OK:       0
  MISMATCH: 2

------------------------------------------------------------------------
MISMATCHES:
------------------------------------------------------------------------

  Topic: onex.cmd.beta.hook-event.v1
  Producer: alpha -> Consumer: beta
  Error: consumer file missing: beta/src/beta/nodes/node_hook_effect/contract.yaml

  Topic: onex.evt.beta.widget-built.v1
  Producer: beta -> Consumer: alpha
  Error: producer file missing: beta/src/beta/nodes/node_hook_effect/contract.yaml


"""


def build_repos(root: Path, *, producer: str | None, consumer: str | None) -> Path:
    """Write the two-repo fixture under *root* and return the manifest path."""
    if producer is not None:
        path = root / "alpha" / PRODUCER_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(producer, encoding="utf-8")
    if consumer is not None:
        path = root / "beta" / CONSUMER_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(consumer, encoding="utf-8")
    (root / "beta").mkdir(exist_ok=True)
    manifest = root.parent / "manifest.yaml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    return manifest


def _run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    *,
    producer: str | None,
    consumer: str | None,
) -> tuple[int, str]:
    root = tmp_path / "repos"
    root.mkdir()
    manifest = build_repos(root, producer=producer, consumer=consumer)
    code = main(["--repos-root", str(root), "--manifest", str(manifest)])
    return code, capsys.readouterr().out


def test_clean_fixture_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(tmp_path, capsys, producer=PRODUCER_CLEAN, consumer=CONSUMER)
    assert (code, out) == (0, EXPECTED_CLEAN)


def test_parity_break_fails_naming_topic_and_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(tmp_path, capsys, producer=PRODUCER_BROKEN, consumer=CONSUMER)
    assert code == 1
    assert out == EXPECTED_BROKEN


def test_missing_file_fails_naming_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(tmp_path, capsys, producer=PRODUCER_CLEAN, consumer=None)
    assert (code, out) == (1, EXPECTED_MISSING)


def _report(files: dict[str, str], manifest: str, today: date) -> ModelValidationReport:
    return HandlerBoundaryParity().handle(
        ModelBoundaryParityInput(
            manifest_yaml=manifest,
            files=[ModelSourceFile(path=p, source=s) for p, s in files.items()],
            today=today,
        )
    )


def test_handler_finding_names_topic_and_producer_file() -> None:
    report = _report(
        {f"alpha/{PRODUCER_FILE}": PRODUCER_BROKEN, f"beta/{CONSUMER_FILE}": CONSUMER},
        MANIFEST,
        date(2026, 10, 10),
    )
    assert report.overall_status == "FAIL"
    failed = [f for f in report.findings if f.severity == "FAIL"]
    assert len(failed) == 1
    assert failed[0].evidence["topic"] == TOPIC
    assert failed[0].location == f"alpha/{PRODUCER_FILE}"
    assert f"topic not found in producer: alpha/{PRODUCER_FILE}" in failed[0].message


def test_topic_found_by_name_and_event_segment_fallbacks() -> None:
    """The regex, then the literal topic name, then the event segment may match."""
    manifest = MANIFEST.replace("hook-event\\\\.v1", "no-such-pattern")
    by_name = _report(
        {f"alpha/{PRODUCER_FILE}": PRODUCER_CLEAN, f"beta/{CONSUMER_FILE}": CONSUMER},
        manifest,
        date(2026, 10, 10),
    )
    assert by_name.overall_status == "PASS"
    by_segment = _report(
        {
            f"alpha/{PRODUCER_FILE}": "SEGMENT = 'hook-event'\nwidget-built.v1\n",
            f"beta/{CONSUMER_FILE}": CONSUMER,
        },
        manifest,
        date(2026, 10, 10),
    )
    assert by_segment.overall_status == "PASS"


PENDING_MANIFEST = f"""---
boundaries:
  - topic_name: "{TOPIC}"
    producer_repo: alpha
    consumer_repo: beta
    producer_file: "{PRODUCER_FILE}"
    consumer_file: "{CONSUMER_FILE}"
    topic_pattern: "hook-event\\\\.v1"
    status: pending
    pending_since: "2026-10-01"
    pending_reason: "consumer not built yet"
"""


def test_pending_boundary_within_grace_is_skipped() -> None:
    report = _report({}, PENDING_MANIFEST, date(2026, 10, 15))
    assert report.overall_status == "PASS"
    assert [f.severity for f in report.findings] == ["SKIP"]
    assert report.findings[0].message == (
        f"  PENDING (grace): {TOPIC} (alpha -> beta) — consumer not built yet"
    )


def test_pending_boundary_past_grace_fails() -> None:
    report = _report({}, PENDING_MANIFEST, date(2026, 10, 16))
    assert report.overall_status == "FAIL"
    assert report.findings[0].evidence["error"] == (
        f"EXPIRED PENDING: {TOPIC} has been pending for 15 days (since 2026-10-01, "
        "grace period is 14 days). Reason: consumer not built yet"
    )


def test_missing_repos_root_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--repos-root", str(tmp_path / "absent")]) == 1
    assert "ERROR: Repos root not found" in capsys.readouterr().err


def test_packaged_manifest_holds_the_occ_boundaries() -> None:
    text = (
        importlib.resources.files("omnibase_core.contracts") / MANIFEST_RESOURCE
    ).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    keys = (
        "topic_name",
        "producer_repo",
        "consumer_repo",
        "producer_file",
        "consumer_file",
        "topic_pattern",
    )
    assert [
        (*(entry[k] for k in keys), entry.get("status")) for entry in data["boundaries"]
    ] == OCC_BOUNDARIES
