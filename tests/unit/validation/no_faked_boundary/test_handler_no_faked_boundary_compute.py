# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-faked-boundary OMN-13497 reason="corpus fixtures are intentional boundary-fake violations the scanner-under-test must flag; the patterns are the subject"
"""Unit + corpus-acceptance tests for the no-faked-boundary COMPUTE validator (OMN-13497).

These tests assert two things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the private-IP / local-paths validators.
2. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_no_faked_boundary``) is
   the acceptance authority; it lives in omnimarket (the generation producer) and
   cannot be imported here (core ↛ market layering), so its fixtures are re-pinned
   inline below. Every violation fixture must be flagged; every clean fixture must
   pass. The boundary cases (recorded-from-real replay, real adapter, real bus,
   external mock, non-boundary base) are what make this a real gate, not a demo.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.no_faked_boundary.handler import (
    HandlerNoFakedBoundaryCompute,
    scan_source,
)
from omnibase_core.validation.no_faked_boundary.models import (
    ModelNoFakedBoundaryScanInput,
)

# --- Acceptance corpus (re-pinned from the omnimarket corpus the generation run
# was accepted against). Each entry is one source line. ----------------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    "class _FakeBridge(ModelInferenceAdapter):",  # v-base-fake-bridge
    '    with patch("httpx.Client") as mock_client:',  # v-base-patch-httpx
    "    adapter = RecordedFixtureInferenceAdapter(completion=prompt)",  # v-base-echo-completion
    "    inference_bridge = MagicMock()",  # v-base-magicmock-router
    "class _StubInferenceRouter(ModelInferenceAdapter):",  # v-mut-stub-router
    '    @patch("httpx.AsyncClient")',  # v-mut-patch-async
    '    adapter = RecordedFixtureInferenceAdapter(completion=f"[recorded] {prompt}")',  # v-mut-echo-fstring
    "    self.router = AsyncMock()",  # v-mut-asyncmock-router
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    '    adapter = RecordedFixtureInferenceAdapter(completion="The capital of France is Paris.")',  # c-base-recorded-replay
    "    adapter = RoutingResolvedJudgeInferenceAdapter(routing=resolved)",  # c-base-real-adapter
    "    bus = EventBusInmemory()",  # c-base-real-bus
    '    with patch("slack_sdk.WebClient") as mock_slack:',  # c-mut-external-mock
    '    @patch("boto3.client")',  # c-mut-external-s3
    "class MockServiceHub(MixinServiceRegistry):",  # c-mut-mock-nonboundary-base
    '    adapter = RecordedFixtureInferenceAdapter(completion="Answer the prompt carefully.")',  # c-mut-recorded-mentions-prompt
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
def test_finding_carries_pattern_line_and_text() -> None:
    result = scan_source("class _FakeBridge(ModelInferenceAdapter):")
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.pattern == "class_subclassing_boundary"
    assert finding.line == 1
    assert "_FakeBridge" in finding.matched_text


@pytest.mark.unit
def test_nonboundary_registry_base_is_not_flagged() -> None:
    # A Mock class subclassing a service-registry mixin is a test harness, not a
    # fake of the inference boundary. This is the FP fixed in the OMN-13497 shadow
    # run; pinning it stops a regression that would re-broaden the class matcher.
    assert scan_source("class MockServiceHub(MixinServiceRegistry):").flagged is False


@pytest.mark.unit
def test_recorded_literal_mentioning_prompt_is_not_an_echo() -> None:
    # 'prompt' as a word inside a recorded string literal is not the prompt var.
    src = '    a = RecordedFixtureInferenceAdapter(completion="Answer the prompt carefully.")'
    assert scan_source(src).flagged is False
    # but the bare-identifier echo IS flagged
    assert scan_source("    a = X(completion=prompt)").flagged is True


@pytest.mark.unit
def test_external_egress_mock_is_not_flagged() -> None:
    assert scan_source('    with patch("slack_sdk.WebClient") as m:').flagged is False
    assert scan_source('    @patch("boto3.client")').flagged is False
    # but the platform's own httpx egress IS flagged
    assert scan_source('    with patch("httpx.Client") as m:').flagged is True


@pytest.mark.unit
def test_suppression_marker_skips_line() -> None:
    src = "class _FakeBridge(ModelInferenceAdapter):  # onex-allow-faked-boundary"
    assert scan_source(src).flagged is False


# ---------------------------------------------------------------------------
# Canonical recorded-replay seam exemption + file-level marker (OMN-13500/13502)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_canonical_replay_patch_seam_is_not_flagged() -> None:
    # The canonical golden-chain seam: patch httpx.Client with a recorded-replay
    # transport (live routing/request construction still run; only bytes replayed).
    # The binding lives on a prior line, so the scanner must be content-aware.
    src = (
        "    transport = RecordedReplayInferenceTransport([fixture])\n"
        '    with patch("httpx.Client", return_value=transport):\n'
        "        run_chain()\n"
    )
    assert scan_source(src).flagged is False


@pytest.mark.unit
def test_canonical_replay_patch_seam_inline_construction_is_not_flagged() -> None:
    src = (
        '    with patch("httpx.AsyncClient",'
        " return_value=RecordedReplayInferenceTransport([f])):\n"
        "        run_chain()\n"
    )
    assert scan_source(src).flagged is False


@pytest.mark.unit
def test_bare_patch_httpx_still_flags_even_with_replay_binding_present() -> None:
    # A bare ``patch("httpx.Client") as mock`` captures the mock to hand-set canned
    # bytes — a fake — even in a file that also builds a real replay transport.
    src = (
        "    transport = RecordedReplayInferenceTransport([fixture])\n"
        '    with patch("httpx.Client") as mock_client:\n'
        "        mock_client.return_value.post.return_value = _canned\n"
    )
    result = scan_source(src)
    assert result.flagged is True
    assert any(f.pattern == "patch_httpx_egress" for f in result.findings)


@pytest.mark.unit
def test_patch_httpx_injecting_magicmock_still_flags() -> None:
    src = '    with patch("httpx.Client", return_value=MagicMock()):'
    assert scan_source(src).flagged is True


@pytest.mark.unit
def test_file_level_marker_skips_whole_file() -> None:
    src = (
        "# onex-allow-file-faked-boundary OMN-13497 reason=corpus subject\n"
        "class _FakeBridge(ModelInferenceAdapter):\n"
        '    with patch("httpx.Client") as mock_client:\n'
        "    inference_bridge = MagicMock()\n"
    )
    result = scan_source(src)
    assert result.flagged is False
    assert result.findings == ()


@pytest.mark.unit
def test_file_level_marker_is_distinct_from_line_marker() -> None:
    # The per-line marker must NOT be a substring of the file-level marker, so a
    # file-level marker does not accidentally suppress only the line it is on.
    from omnibase_core.validation.no_faked_boundary.handler import (
        _FILE_SUPPRESSION_MARKER,
        _SUPPRESSION_MARKER,
    )

    assert _SUPPRESSION_MARKER not in _FILE_SUPPRESSION_MARKER


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerNoFakedBoundaryCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-no-faked-boundary-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerNoFakedBoundaryCompute()
    envelope: ModelEventEnvelope[ModelNoFakedBoundaryScanInput] = ModelEventEnvelope(
        payload=ModelNoFakedBoundaryScanInput(
            content="class _FakeBridge(ModelInferenceAdapter):", path="f.py"
        )
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "f.py"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.no_faked_boundary.runtime_no_faked_boundary import (
        NoFakedBoundaryBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = NoFakedBoundaryBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelNoFakedBoundaryScanInput(
                        content="    inference_bridge = MagicMock()", path="bad.py"
                    ),
                    ModelNoFakedBoundaryScanInput(
                        content="    bus = EventBusInmemory()", path="ok.py"
                    ),
                ]
            )
        finally:
            await bus.shutdown()
        by_path = {r.path: r for r in results}
        assert by_path["bad.py"].flagged is True
        assert by_path["ok.py"].flagged is False

    asyncio.run(_run())
