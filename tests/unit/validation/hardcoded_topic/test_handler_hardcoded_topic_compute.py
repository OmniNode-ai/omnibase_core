# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-topic-literal OMN-13294 reason="corpus fixtures + assertions name the onex.* topic literal the scanner-under-test must flag; the literals are the subject"
"""Unit + corpus-acceptance tests for the hardcoded-topic COMPUTE validator (OMN-13294, G2).

These tests assert two things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the G1 local-paths canary and the G2 private-IP /
   unfinished-work-marker validators.
2. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_hardcoded_topic.HARDCODED_TOPIC_CORPUS``)
   is the acceptance authority; it lives in omnimarket (the generation producer)
   and cannot be imported here (core ↛ market layering), so its fixtures are
   re-pinned inline below. Every violation fixture must be flagged; every clean
   fixture must pass. The boundary cases (two-segment ``onex.core`` below the
   topic shape, a non-``onex`` dotted ``kafka.cluster.broker.id`` string, a dotted
   python import path) are what make this a real gate, not a curated demo.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.hardcoded_topic.handler import (
    HandlerHardcodedTopicCompute,
    scan_source,
)
from omnibase_core.validation.hardcoded_topic.models import (
    ModelHardcodedTopicScanInput,
)

# --- Acceptance corpus (re-pinned VERBATIM from the omnimarket corpus the
# generation run was accepted against — corpus_hardcoded_topic.py). Each entry is
# the fixture source. -----------------------------------------------------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    # base cases
    'TOPIC = "onex.generation.benchmark.completed"',  # v-base-generation-topic
    'await bus.publish("onex.delegation.attempt.started", env)',  # v-base-publish-call
    # adversarial mutation cases (must still flag)
    "SWEEP_TOPIC = 'onex.aislop.sweep.completed'",  # v-mut-single-quote
    'RESULT_TOPIC = "onex.review.verdict.posted"',  # v-mut-other-domain
    'EVT = "onex.runtime.node.deploy.requested"',  # v-mut-deeper-segments
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    'topic = self._contract.topics["benchmark_completed"]',  # c-base-contract-topic
    "from omnimarket.nodes.node_generation_consumer.models import x",  # c-base-module-path
    'NAMESPACE = "onex.core"',  # c-mut-two-segment
    'LEGACY = "kafka.cluster.broker.id"',  # c-mut-non-onex-prefix
)


# ---------------------------------------------------------------------------
# Corpus acceptance — the verdict that gated the generation run
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("source", _VIOLATION_FIXTURES)
def test_every_violation_fixture_is_flagged(source: str) -> None:
    result = scan_source(source)
    assert result.flagged is True, f"violation fixture not flagged: {source!r}"
    assert result.findings, "a flagged result must carry at least one finding"


@pytest.mark.unit
@pytest.mark.parametrize("source", _CLEAN_FIXTURES)
def test_every_clean_fixture_passes(source: str) -> None:
    result = scan_source(source)
    assert result.flagged is False, f"clean fixture false-flagged: {source!r}"
    assert result.findings == ()


@pytest.mark.unit
def test_finding_carries_topic_line_context() -> None:
    result = scan_source('TOPIC = "onex.generation.benchmark.completed"')
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.topic == "onex.generation.benchmark.completed"
    assert finding.line == 1
    assert "onex.generation.benchmark.completed" in finding.context


@pytest.mark.unit
def test_inline_publish_call_topic_is_flagged() -> None:
    result = scan_source(
        'await bus.publish("onex.delegation.attempt.started", envelope)'
    )
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.topic == "onex.delegation.attempt.started"


@pytest.mark.unit
def test_two_segment_onex_string_is_below_topic_shape() -> None:
    # onex.core is two-segment — below the onex.<a>.<b>.<c> topic shape.
    assert scan_source('NAMESPACE = "onex.core"').flagged is False
    # onex.cmd alone (two segments) is also below the shape.
    assert scan_source('X = "onex.cmd"').flagged is False


@pytest.mark.unit
def test_non_onex_dotted_string_is_not_flagged() -> None:
    # A topic-shaped (4-segment) string NOT prefixed onex. is not an onex topic.
    assert scan_source('LEGACY = "kafka.cluster.broker.id"').flagged is False


@pytest.mark.unit
def test_unquoted_dotted_module_path_is_not_flagged() -> None:
    # A dotted python import path is not a quoted topic literal.
    assert scan_source("from omnimarket.nodes.node_x.models import y").flagged is False


@pytest.mark.unit
def test_mismatched_quote_fragment_is_not_flagged() -> None:
    # The quote backreference ties the closing quote to the opening one; a
    # fragment with mismatched/absent closing quote must not match.
    assert scan_source("X = \"onex.a.b.c'").flagged is False


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerHardcodedTopicCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-hardcoded-topic-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerHardcodedTopicCompute()
    envelope: ModelEventEnvelope[ModelHardcodedTopicScanInput] = ModelEventEnvelope(
        payload=ModelHardcodedTopicScanInput(
            content='T = "onex.generation.benchmark.completed"', path="f.py"
        )
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "f.py"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.hardcoded_topic.runtime_hardcoded_topic import (
        HardcodedTopicBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = HardcodedTopicBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelHardcodedTopicScanInput(
                        content='T = "onex.delegation.attempt.started"',
                        path="bad.py",
                    ),
                    ModelHardcodedTopicScanInput(
                        content='topic = self._contract.topics["x"]', path="ok.py"
                    ),
                ]
            )
        finally:
            await bus.shutdown()
        by_path = {r.path: r for r in results}
        assert by_path["bad.py"].flagged is True
        assert by_path["ok.py"].flagged is False

    asyncio.run(_run())


@pytest.mark.unit
def test_findings_are_order_independent() -> None:
    # Two violations on different lines: stable order by line.
    src = 'A = "onex.a.b.c"\nB = "onex.d.e.f"'
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [1, 2]
    assert [f.topic for f in findings] == ["onex.a.b.c", "onex.d.e.f"]


# ---------------------------------------------------------------------------
# Suppression escape hatches
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_line_marker_suppresses_only_that_line() -> None:
    src = (
        'A = "onex.a.b.c"  # onex-allow-topic-literal approved SOT\n'  # suppressed
        'B = "onex.d.e.f"'  # still flagged
    )
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [2]


@pytest.mark.unit
def test_file_marker_suppresses_the_whole_file() -> None:
    # A topic-registry source whose subject IS topic literals: one file-level
    # marker suppresses every finding so the declarations stay clean.
    src = (
        "# onex-allow-file-topic-literal registry SOT\n"
        'A = "onex.a.b.c"\n'
        'B = "onex.d.e.f"\n'
        'C = "onex.g.h.i.j"'
    )
    result = scan_source(src)
    assert result.flagged is False
    assert result.findings == ()


# ---------------------------------------------------------------------------
# Runner exit-code semantics: blocking (default) vs report-only (CI burn-down)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_runner_blocks_on_violation_and_passes_when_clean(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from omnibase_core.validation.hardcoded_topic.runtime_hardcoded_topic import main

    bad = tmp_path / "bad.py"
    bad.write_text('T = "onex.runtime.node.deploy.requested"\n', encoding="utf-8")
    clean = tmp_path / "clean.py"
    clean.write_text('topic = self._contract.topics["deploy"]\n', encoding="utf-8")

    # Default (blocking): a pasted topic literal fails the gate.
    assert main([str(bad), "--quiet"]) == 1
    # Clean source passes.
    assert main([str(clean), "--quiet"]) == 0


@pytest.mark.unit
def test_runner_report_only_always_exits_zero(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from omnibase_core.validation.hardcoded_topic.runtime_hardcoded_topic import main

    bad = tmp_path / "bad.py"
    bad.write_text('T = "onex.runtime.node.deploy.requested"\n', encoding="utf-8")
    # --report-only prints the finding but never fails (burn-down phase).
    assert main([str(bad), "--report-only", "--quiet"]) == 0
