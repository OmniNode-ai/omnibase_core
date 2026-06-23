# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# test-literal-ok: OMN-13480 — fixtures ARE hardcoded localhost/loopback URL
# violations the scanner-under-test must flag; the literals are the subject.
# onex-allow-file OMN-13480 reason="corpus fixtures are intentional hardcoded localhost/loopback URL violations the scanner-under-test must flag"
"""Unit + corpus-acceptance tests for the localhost-URL COMPUTE validator (OMN-13480, G2).

These tests assert two things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the private-IP / local-paths canaries.
2. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_hardcoded_localhost_url``)
   is the acceptance authority; it lives in omnimarket (the generation producer)
   and cannot be imported here (core ↛ market layering), so its fixtures are
   re-pinned inline below. Every violation fixture must be flagged; every clean
   fixture must pass. The boundary cases (a public host URL, a contract-sourced
   reference, the bare ``localhost`` word, a public host whose name merely
   CONTAINS ``localhost``, and the suppression marker) are what make this a real
   gate, not a curated demo.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.localhost_url.handler import (
    HandlerLocalhostUrlCompute,
    scan_source,
)
from omnibase_core.validation.localhost_url.models import ModelLocalhostUrlScanInput

# --- Acceptance corpus (re-pinned from the omnimarket corpus the generation run
# was accepted against). Each entry is (source, must_be_flagged). ------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    'BASE_URL = "http://localhost:8000/v1/chat/completions"',  # v-base-localhost-http
    'ENDPOINT = "http://127.0.0.1:8085/health"',  # v-base-loopback-http
    'BASE_URL = "https://localhost:8443/v1/models"',  # v-mut-localhost-https
    'URL = "https://127.0.0.1/api"',  # v-mut-loopback-https
    "DSN = 'http://localhost/metrics'",  # v-mut-localhost-bare-slash
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    'DOCS = "https://docs.omninode.ai/v1"',  # c-base-public-host-url
    'endpoint = resolve_endpoint("local-coder")',  # c-base-contract-ref
    'COMMENT = "binds to localhost in the dev profile only"',  # c-mut-bare-localhost-word
    'URL = "https://localhost-mirror.omninode.ai/v1"',  # c-mut-localhost-substring-host
    'URL = "http://localhost:8000"  # onex-allow-internal-ip approved local fixture',  # c-mut-suppressed
)


# ---------------------------------------------------------------------------
# Corpus acceptance — the corpus, not the LLM, is the acceptance authority
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
def test_finding_carries_host_line_column_context() -> None:
    result = scan_source('  BASE_URL = "http://localhost:8000/v1"')
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.host == "localhost"
    assert finding.matched_url == "http://localhost"
    assert finding.line == 1
    assert finding.column >= 1
    assert "localhost" in finding.context


@pytest.mark.unit
def test_both_loopback_hosts_are_labelled() -> None:
    assert scan_source('x = "http://localhost/a"').findings[0].host == "localhost"
    assert scan_source('x = "https://127.0.0.1/a"').findings[0].host == "127.0.0.1"


@pytest.mark.unit
def test_substring_host_is_not_flagged() -> None:
    # A public host whose name merely STARTS with the loopback token must NOT flag.
    assert scan_source('x = "https://localhost-mirror.example.com/v1"').flagged is False
    assert scan_source('x = "https://127.0.0.1.evil.com/v1"').flagged is False


@pytest.mark.unit
def test_bare_word_localhost_not_in_url_is_not_flagged() -> None:
    # The word 'localhost' in prose, not inside an http(s):// URL literal, is clean.
    assert scan_source('s = "binds to localhost in dev"').flagged is False
    # A non-http scheme is out of scope for this gate.
    assert scan_source('dsn = "postgres://localhost/db"').flagged is False


@pytest.mark.unit
def test_bare_localhost_url_at_end_of_literal_is_flagged() -> None:
    # No port, no path — http://localhost at the end of the literal still flags.
    result = scan_source('x = "http://localhost"')
    assert result.flagged is True
    assert result.findings[0].matched_url == "http://localhost"


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerLocalhostUrlCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-localhost-url-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerLocalhostUrlCompute()
    envelope: ModelEventEnvelope[ModelLocalhostUrlScanInput] = ModelEventEnvelope(
        payload=ModelLocalhostUrlScanInput(
            content='H = "http://localhost:9000"', path="f.py"
        )
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "f.py"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.localhost_url.runtime_localhost_url import (
        LocalhostUrlBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = LocalhostUrlBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelLocalhostUrlScanInput(
                        content='H = "http://localhost:8000"', path="bad.py"
                    ),
                    ModelLocalhostUrlScanInput(
                        content='H = "https://docs.example.com"', path="ok.py"
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
    # Two violations on different lines: stable sort by (line, column).
    src = 'A = "http://localhost/a"\nB = "https://127.0.0.1/b"'
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [1, 2]


# ---------------------------------------------------------------------------
# Suppression escape hatches (CLAUDE.md Rule 6)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_line_marker_suppresses_only_that_line() -> None:
    src = (
        'A = "http://localhost/a"  # onex-allow-internal-ip approved\n'  # suppressed
        'B = "https://127.0.0.1/b"'  # still flagged
    )
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [2]


@pytest.mark.unit
def test_file_marker_suppresses_whole_file() -> None:
    src = (
        "# onex-allow-file-internal-ip doc whose subject is localhost URLs\n"
        'A = "http://localhost/a"\n'
        'B = "https://127.0.0.1/b"'
    )
    result = scan_source(src)
    assert result.flagged is False
    assert result.findings == ()


# ---------------------------------------------------------------------------
# Runner fail-closed behavior (a blocking gate must never silently pass an
# unreadable file)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unreadable_file_fails_closed() -> None:
    from pathlib import Path

    from omnibase_core.validation.localhost_url.runtime_localhost_url import _read_text

    # A path that cannot be read (does not exist) must RAISE, not return "" — a
    # blocking validator that treats an unreadable file as clean would let
    # violations slip through silently.
    with pytest.raises(OSError):
        _read_text(Path("/nonexistent/path/that/cannot/be/read.py"))
