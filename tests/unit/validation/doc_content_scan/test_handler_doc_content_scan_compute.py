# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# doc-content-file-ok OMN-13569 reason="these fixtures ARE doc-content violations the scanner-under-test must flag; the literals + OMN ids are the subject"
# onex-allow-file-internal-ip OMN-13569 reason="fixtures include intentional LAN-IP literals the scanner must flag"
"""Unit + corpus-acceptance tests for the doc-content COMPUTE validator (OMN-13569, G2).

These tests assert three things:

1. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_doc_content_scan``) is the
   acceptance authority; it lives in omnimarket (the generation producer) and
   cannot be imported here (core ↛ market layering), so its fixtures are re-pinned
   inline below. Every violation fixture must be flagged; every clean fixture must
   pass — including the boundary cases (localhost, RFC5737 doc IPs, example.com,
   env-var forms, the decimal/SemVer near-misses, the suppression marker).
2. The PATH-based exemptions the text-only corpus could not express:
   ``OMN-<digits>`` is exempt under ``onex_change_control/`` and ``contracts/`` but
   local-env rules still apply there; the line/file suppression markers work.
3. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the sibling private-IP validator.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.doc_content_scan.handler import (
    HandlerDocContentScanCompute,
    scan_source,
)
from omnibase_core.validation.doc_content_scan.models import (
    EnumDocViolationType,
    ModelDocContentScanInput,
)

# --- Acceptance corpus (re-pinned from the omnimarket corpus the generation run
# was accepted against). Each entry is the fixture's source line. ------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    "The broker runs on 192.168.86.201 in the lab.",  # v-base-lan-ip
    "Deployed to .201 over the weekend.",  # v-base-host-shorthand
    "Logs are written to /Users/jonah/Code/omni_home/run.log",  # v-base-personal-path  # local-path-ok OMN-13569 fixture is the personal-path violation the scanner must flag
    "Connect with `ssh jonah@192.168.86.201` then tail the logs.",  # v-base-ssh-line
    "Questions go to jonah.neugass@gmail.com for now.",  # v-base-personal-email
    "This was fixed in OMN-13294 last sprint.",  # v-base-omn-prose
    "Postgres listens on 10.0.0.5 inside the cluster.",  # v-mut-lan-ip-10-band
    "Valkey is reachable at 172.16.4.9 from the runners.",  # v-mut-lan-ip-172-band
    "The Mac Studio is the .200 box.",  # v-mut-host-shorthand-200
    "Drop the artifact in /home/jonah/scratch/out.json overnight.",  # v-mut-personal-path-home  # local-path-ok OMN-13569 fixture is the personal-path violation the scanner must flag
    "The renderer is the effect node (OMN-12822) on the bus.",  # v-mut-omn-parenthetical
    "## OMN-13567 doc content scan",  # v-mut-omn-heading
    "- See OMN-13568 for the corpus.",  # v-mut-omn-list-item
    "Details: [the ticket](https://linear.app/omninode/issue/OMN-13569).",  # v-mut-omn-link-target
    "Evidence lives in OMN-13294-handoff.md at the repo root.",  # v-mut-omn-filename
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    "Open http://localhost:3000 to view the dashboard.",  # c-base-localhost
    "The dev server binds 127.0.0.1 only.",  # c-base-loopback
    "Point the client at 192.0.2.10 (TEST-NET-1) in the example.",  # c-base-doc-ip-192-0-2
    "Webhooks post to https://hooks.example.com/ingest.",  # c-base-example-com
    "Artifacts go under $OMNI_HOME/omni_worktrees/out.log.",  # c-base-env-var-path
    "Try 198.51.100.42 (TEST-NET-2) for the second example.",  # c-mut-doc-ip-198-51-100
    "The third example uses 203.0.113.7 (TEST-NET-3).",  # c-mut-doc-ip-203-0-113
    "Connect to ${ONEX_HOST} resolved from the overlay.",  # c-mut-env-var-braced
    "Defaults resolve from Path.home() / '.omnibase'.",  # c-mut-path-home-call
    "The free tier prices at $0.200 per million tokens.",  # c-mut-decimal-not-host
    "Released as v1.201.0 on the changelog.",  # c-mut-semver-not-host
    "The broker runs on 192.168.86.201.  <!-- doc-content-ok approved example -->",  # c-mut-line-suppressed
    "The OMNI_HOME path and OMNINODE platform are referenced here.",  # c-mut-omn-clean-no-ticket-shape
)


# ---------------------------------------------------------------------------
# Corpus acceptance — the verdict that gated the generation run
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("source", _VIOLATION_FIXTURES)
def test_every_violation_fixture_is_flagged(source: str) -> None:
    # Default path "<input>" is not under an exempt tree, so OMN refs flag.
    result = scan_source(source)
    assert result.flagged is True, f"violation fixture not flagged: {source!r}"
    assert result.findings, "a flagged result must carry at least one finding"


@pytest.mark.unit
@pytest.mark.parametrize("source", _CLEAN_FIXTURES)
def test_every_clean_fixture_passes(source: str) -> None:
    result = scan_source(source)
    assert result.flagged is False, f"clean fixture false-flagged: {source!r}"
    assert result.findings == ()


# ---------------------------------------------------------------------------
# Per-class finding shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lan_ip_finding_shape() -> None:
    (finding,) = scan_source("host = 10.0.0.5").findings
    assert finding.violation_type is EnumDocViolationType.LAN_IP
    assert finding.matched_text == "10.0.0.5"
    assert finding.line == 1
    assert finding.column >= 1
    assert "10.0.0.5" in finding.context


@pytest.mark.unit
def test_host_shorthand_finding_shape() -> None:
    (finding,) = scan_source("deployed to .201").findings
    assert finding.violation_type is EnumDocViolationType.HOST_SHORTHAND
    assert finding.matched_text == ".201"


@pytest.mark.unit
def test_personal_path_and_ssh_and_email_classes() -> None:
    path_doc = "see /Users/jonah/x"  # local-path-ok OMN-13569 personal-path fixture
    assert (
        scan_source(path_doc).findings[0].violation_type
        is EnumDocViolationType.PERSONAL_PATH
    )
    assert (
        scan_source("run ssh bob@host.lan now").findings[0].violation_type
        is EnumDocViolationType.SSH_INVOCATION
    )
    assert (
        scan_source("mail me@gmail.com").findings[0].violation_type
        is EnumDocViolationType.PERSONAL_EMAIL
    )


@pytest.mark.unit
def test_ticket_reference_class_and_token_boundary() -> None:
    (finding,) = scan_source("fixed in OMN-42 today").findings
    assert finding.violation_type is EnumDocViolationType.TICKET_REFERENCE
    assert finding.matched_text == "OMN-42"
    # OMNI_HOME / OMNINODE are not the OMN-<digits> shape.
    assert scan_source("OMNI_HOME and OMNINODE here").flagged is False


@pytest.mark.unit
def test_decimal_and_semver_are_not_host_shorthand() -> None:
    assert scan_source("price is 0.200 per token").flagged is False
    assert scan_source("version v1.201.0 shipped").flagged is False


@pytest.mark.unit
def test_rfc5737_and_loopback_are_not_lan_ip() -> None:
    assert scan_source("use 192.0.2.1 in docs").flagged is False
    assert scan_source("use 198.51.100.1 in docs").flagged is False
    assert scan_source("use 203.0.113.1 in docs").flagged is False
    assert scan_source("binds 127.0.0.1 only").flagged is False


# ---------------------------------------------------------------------------
# PATH-based exemptions (could not be expressed in the text-only corpus)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "onex_change_control/grants/prod.md",
        "docs/contracts/OMN-1.yaml.md",
        "repo/contracts/spec.md",
    ],
)
def test_ticket_reference_exempt_under_governance_and_contract_trees(path: str) -> None:
    # OMN-<digits> is exempt under these trees.
    assert scan_source("see OMN-1234 for context", path=path).flagged is False


@pytest.mark.unit
def test_local_env_rules_still_apply_under_exempt_trees() -> None:
    # The path exemption is ONLY for ticket refs — a LAN IP still flags there.
    result = scan_source(
        "deployed to 192.168.86.201",
        path="onex_change_control/notes.md",
    )
    assert result.flagged is True
    assert result.findings[0].violation_type is EnumDocViolationType.LAN_IP


@pytest.mark.unit
def test_ticket_reference_flagged_outside_exempt_trees() -> None:
    assert scan_source("see OMN-1234", path="docs/handoffs/note.md").flagged is True


# ---------------------------------------------------------------------------
# Skill-frontmatter ticket: field exemption (OMN-13572)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "line",
    [
        "ticket: OMN-1234",
        "ticket:   OMN-1234",
        "ticket: 'OMN-1234'",
        'ticket: "OMN-1234"',
        "  ticket: OMN-1234",  # nested/indented frontmatter
    ],
)
def test_skill_frontmatter_ticket_field_is_exempt(line: str) -> None:
    # A SKILL.md ``ticket: OMN-NNNN`` frontmatter binding must NOT be flagged,
    # even outside the governance/contract trees (default <input> path).
    assert scan_source(line, path="plugins/onex/skills/foo/SKILL.md").flagged is False


@pytest.mark.unit
def test_skill_frontmatter_exemption_is_anchored_not_substring() -> None:
    # The exemption is anchored to a dedicated ``ticket:`` FIELD at line start
    # (operator rule: a line matching ^ticket:\s*OMN- must not flag). A line that
    # does NOT start with the ticket: field still flags its OMN ids.
    assert scan_source("# this references ticket: OMN-1234 inline").flagged is True
    assert scan_source("blocked_by_ticket: OMN-1234").flagged is True
    assert scan_source("description: see OMN-1234").flagged is True


# ---------------------------------------------------------------------------
# Suppression escape hatches
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_line_marker_suppresses_only_that_line() -> None:
    src = (
        "host = 10.0.0.5  <!-- doc-content-ok approved -->\n"  # suppressed
        "other = 192.168.0.1"  # still flagged
    )
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [2]


@pytest.mark.unit
def test_file_marker_suppresses_the_whole_file() -> None:
    src = (
        "<!-- doc-content-file-ok doc fixture -->\n"
        "host = 10.0.0.5\n"
        "see OMN-1234\n"
        "ssh jonah@192.168.86.201"
    )
    result = scan_source(src)
    assert result.flagged is False
    assert result.findings == ()


# ---------------------------------------------------------------------------
# Order independence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_findings_are_order_independent() -> None:
    src = "host = 10.0.0.1\nsee OMN-99"
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [1, 2]


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerDocContentScanCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-doc-content-scan-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerDocContentScanCompute()
    envelope: ModelEventEnvelope[ModelDocContentScanInput] = ModelEventEnvelope(
        payload=ModelDocContentScanInput(content="host 10.0.0.1", path="d.md")
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "d.md"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.doc_content_scan.runtime_doc_content_scan import (
        DocContentScanBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = DocContentScanBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelDocContentScanInput(content="deployed to .201", path="bad.md"),
                    ModelDocContentScanInput(
                        content="open http://localhost:3000", path="ok.md"
                    ),
                ]
            )
        finally:
            await bus.shutdown()
        by_path = {r.path: r for r in results}
        assert by_path["bad.md"].flagged is True
        assert by_path["ok.md"].flagged is False

    asyncio.run(_run())
