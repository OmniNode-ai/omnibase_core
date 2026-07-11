# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Effect-readback oracle canary (OMN-14358).

Proves the effect-golden readback is NON-VACUOUS on a real EFFECT node
(``NodeComplianceEvidenceEffect``): a suppressed declared side-effect is CAUGHT
by readback, while a "didn't throw" check stays blind. This is the EFFECT analog
of the compute-oracle canary — the MagicMock blind spot (OMN-14294) turned into a
defeated pattern.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.compliance_evidence.model_evidence_report_state import (
    ModelEvidenceReportState,
)
from omnibase_core.nodes.node_compliance_evidence_effect.handler import (
    NodeComplianceEvidenceEffect,
)
from scripts.ci.effect_golden import (
    ModelEffectReadback,
    RecordingEventSink,
    compare_effect_golden,
    parse_publish_topics,
    readback_effects,
    record_effect_golden,
)

pytestmark = pytest.mark.unit

TOPIC = "onex.evt.core.compliance-scan-completed.v1"
# Declared effects (contract): publish TOPIC + write the run-specific report file.
DECLARED_FILES = ["compliance/runs/*.yaml"]
VOLATILE = ["run_id", "timestamp", "correlation_id"]


def _report(run_id: str | None = "fixed-run") -> ModelEvidenceReportState:
    return ModelEvidenceReportState(
        total=3, passed=2, failed=1, results=[], run_id=run_id
    )


def test_contract_declares_the_publish_topic() -> None:
    contract = (
        Path(__file__).resolve().parents[3]
        / "src/omnibase_core/nodes/node_compliance_evidence_effect/contract.yaml"
    )
    assert TOPIC in parse_publish_topics(contract)


def test_readback_passes_when_all_declared_effects_happen(tmp_path: Path) -> None:
    sink = RecordingEventSink()
    node = NodeComplianceEvidenceEffect(tmp_path, sink, TOPIC)
    node.execute(_report())
    rb = readback_effects(
        sink=sink,
        declared_topics=[TOPIC],
        declared_file_globs=DECLARED_FILES,
        root=tmp_path,
    )
    assert rb.ok is True
    assert rb.published_ok and rb.files_ok
    assert rb.missing_effects == []


def test_readback_CATCHES_a_suppressed_effect(tmp_path: Path) -> None:
    # THE proof: event_bus=None suppresses the publish (handler logs, never emits).
    # execute() STILL returns a Path (no exception) — 'didn't throw' is blind — but
    # the declared topic never reaches a real sink, so readback FAILS.
    sink = RecordingEventSink()  # stays empty: the node was given no bus
    node = NodeComplianceEvidenceEffect(tmp_path, None, TOPIC)
    returned = node.execute(_report())  # does NOT throw
    assert isinstance(returned, Path)  # 'didn't throw' would PASS here
    rb = readback_effects(
        sink=sink,
        declared_topics=[TOPIC],
        declared_file_globs=DECLARED_FILES,
        root=tmp_path,
    )
    assert rb.ok is False  # readback DISCRIMINATES where 'didn't throw' cannot
    assert rb.published_ok is False
    assert rb.files_ok is True  # the file leg still happened
    assert f"topic:{TOPIC}" in rb.missing_effects


def test_readback_catches_a_missing_file(tmp_path: Path) -> None:
    # Event published but the declared file glob matches nothing -> conjunctive FAIL.
    sink = RecordingEventSink()
    sink.publish(TOPIC, {"run_id": "x"})
    rb = readback_effects(
        sink=sink,
        declared_topics=[TOPIC],
        declared_file_globs=DECLARED_FILES,
        root=tmp_path,
    )
    assert rb.ok is False
    assert rb.published_ok is True
    assert rb.files_ok is False
    assert any(m.startswith("file:") for m in rb.missing_effects)


def test_effect_golden_equivalence_masks_volatile_fields(tmp_path: Path) -> None:
    # Record with one run_id; replay with another. Under the volatile mask the
    # event payloads are equivalent (run_id excluded).
    sinkA = RecordingEventSink()
    NodeComplianceEvidenceEffect(tmp_path / "a", sinkA, TOPIC).execute(_report("run-A"))
    golden = record_effect_golden(
        sink=sinkA,
        declared_topics=[TOPIC],
        declared_file_globs=DECLARED_FILES,
        volatile_mask=VOLATILE,
    )
    sinkB = RecordingEventSink()
    NodeComplianceEvidenceEffect(tmp_path / "b", sinkB, TOPIC).execute(_report("run-B"))
    assert compare_effect_golden(golden, sinkB) == []


def test_effect_golden_compare_catches_payload_change() -> None:
    golden = {
        "golden_version": "effect_golden.v1",
        "events": [[TOPIC, {"passed": 2, "failed": 1}]],
        "volatile_mask": VOLATILE,
    }
    sink = RecordingEventSink()
    sink.publish(TOPIC, {"passed": 99, "failed": 1})  # a real behavior change
    diffs = compare_effect_golden(golden, sink)
    assert diffs, "compare must catch a changed effect payload"


def test_readback_model_rejects_inconsistent_verdict() -> None:
    with pytest.raises(ValueError, match="ok must equal"):
        ModelEffectReadback(
            ok=True, published_ok=False, files_ok=True, missing_effects=[]
        )
