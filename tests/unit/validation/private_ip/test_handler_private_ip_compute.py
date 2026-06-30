# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# test-literal-ok: OMN-13294 — fixtures ARE hardcoded private-IP violations the
# scanner-under-test must flag; the literals are the subject.
# onex-allow-file OMN-13294 reason="corpus fixtures are intentional hardcoded private-IP violations the scanner-under-test must flag"
"""Unit + corpus-acceptance tests for the private-IP COMPUTE validator (OMN-13294, G2).

These tests assert two things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the G1 local-paths canary.
2. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_hardcoded_ip``) is the
   acceptance authority; it lives in omnimarket (the generation producer) and
   cannot be imported here (core ↛ market layering), so its fixtures are re-pinned
   inline below. Every violation fixture must be flagged; every clean fixture must
   pass. The boundary cases (public IP, SemVer token, 172.15 below-band, the
   suppression marker) are what make this a real gate, not a curated demo.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.private_ip.handler import (
    HandlerPrivateIpCompute,
    scan_source,
)
from omnibase_core.validation.private_ip.models import ModelPrivateIpScanInput

# --- Acceptance corpus (re-pinned from the omnimarket corpus the generation run
# was accepted against). Each entry is (source, must_be_flagged). ------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    'HOST = "192.168.86.201"',  # v-base-192-168
    'BROKER = "10.0.0.42"',  # v-base-10
    'DB = "172.16.5.10"',  # v-base-172
    'HOST = "192.168.99.250"',  # v-mut-192-octet
    'ADDR = "172.31.255.254"',  # v-mut-172-band-edge
    'ENDPOINT = "https://192.168.86.201:8000/v1/chat/completions"',  # v-mut-url-prefixed
    "REDIS = '10.10.10.10'",  # v-mut-10-single-quote
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    'DNS = "8.8.8.8"',  # c-base-public-ip
    'endpoint_ref = resolve_endpoint("local-coder")',  # c-base-contract-ref
    'VERSION = "1.10.172.0"',  # c-mut-semver
    'HOST = "172.15.0.1"',  # c-mut-172-public (below the 172.16-31 band)
    'HOST = "192.168.86.201"  # onex-allow-internal-ip approved test fixture',  # c-mut-suppressed
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
def test_finding_carries_block_line_column_context() -> None:
    result = scan_source('  HOST = "192.168.86.201"')
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.rfc1918_block == "192.168/16"
    assert finding.matched_text == "192.168.86.201"
    assert finding.line == 1
    assert finding.column >= 1
    assert "192.168.86.201" in finding.context


@pytest.mark.unit
def test_all_three_rfc1918_blocks_are_labelled() -> None:
    assert scan_source('x = "10.1.2.3"').findings[0].rfc1918_block == "10/8"
    assert scan_source('x = "172.20.0.1"').findings[0].rfc1918_block == "172.16/12"
    assert scan_source('x = "192.168.0.1"').findings[0].rfc1918_block == "192.168/16"


@pytest.mark.unit
def test_octet_over_255_is_not_a_valid_ip() -> None:
    # 192.168.300.1 has an out-of-range octet — not a valid IPv4 literal.
    assert scan_source('x = "192.168.300.1"').flagged is False


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerPrivateIpCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-private-ip-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerPrivateIpCompute()
    envelope: ModelEventEnvelope[ModelPrivateIpScanInput] = ModelEventEnvelope(
        payload=ModelPrivateIpScanInput(content='H = "10.0.0.1"', path="f.py")
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "f.py"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.private_ip.runtime_private_ip import (
        PrivateIpBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = PrivateIpBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelPrivateIpScanInput(content='H = "192.168.0.1"', path="bad.py"),
                    ModelPrivateIpScanInput(content='H = "8.8.8.8"', path="ok.py"),
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
    # Two violations on different lines: stable sort by (line, column).
    src = 'A = "10.0.0.1"\nB = "192.168.1.1"'
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [1, 2]


# ---------------------------------------------------------------------------
# Suppression escape hatches (CLAUDE.md Rule 6)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_line_marker_suppresses_only_that_line() -> None:
    src = (
        'A = "10.0.0.1"  # onex-allow-internal-ip approved\n'  # suppressed
        'B = "192.168.1.1"'  # still flagged
    )
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [2]


@pytest.mark.unit
def test_file_marker_suppresses_the_whole_file() -> None:
    # A documentation-heavy file whose subject IS IP literals: one file-level
    # marker suppresses every finding so rendered docs stay clean.
    src = (
        "# onex-allow-file-internal-ip doc fixture\n"
        'A = "10.0.0.1"\n'
        'B = "192.168.1.1"\n'
        'C = "172.20.0.1"'
    )
    result = scan_source(src)
    assert result.flagged is False
    assert result.findings == ()
