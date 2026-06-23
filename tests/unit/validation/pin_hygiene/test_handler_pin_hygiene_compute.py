# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-pin-hygiene OMN-13509 reason="corpus fixtures are intentional diverged-pin violations the scanner-under-test must flag; the pin literals are the subject"
"""Unit + corpus-acceptance tests for the sibling-pin-hygiene COMPUTE validator (OMN-13509).

These tests assert four things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the private-IP / no-faked-boundary validators.
2. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_pin_hygiene``) is the
   acceptance authority; it lives in omnimarket (the generation producer) and
   cannot be imported here (core ↛ market layering), so its fixtures are
   re-pinned inline below. Every violation fixture must be flagged; every clean
   fixture must pass.
3. The HARDENING beyond the corpus holds: a sibling git pin with NO ancestry
   annotation fails CLOSED (the generated seed skipped it — fail open).
4. The EFFECT runner's git resolution (``annotate_ancestry``) produces the
   correct annotation against a REAL temp git repo, and the end-to-end gate FAILS
   the #2071 shape (a branch that diverged from dev) and PASSES a clean ancestor
   pin — the real recurrence proof.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.pin_hygiene.handler import (
    HandlerPinHygieneCompute,
    scan_source,
)
from omnibase_core.validation.pin_hygiene.models import ModelPinHygieneScanInput

# --- Acceptance corpus (re-pinned from the omnimarket corpus the generation run
# was accepted against). Each entry is one annotated pin line. -----------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    'omnibase-core = { git = "https://github.com/OmniNode-ai/omnibase_core.git", rev = "def4560000000000000000000000000000000000" }  # pin-ancestry: orphan',  # v-base-pyproject-rev
    'omnibase-spi = { git = "https://github.com/OmniNode-ai/omnibase_spi.git", rev = "0123456789abcdef0123456789abcdef01234567" }  # pin-ancestry: orphan',  # v-base-spi-rev
    'omnibase-compat = { git = "https://github.com/OmniNode-ai/omnibase_compat.git", rev = "fedcba9876543210fedcba9876543210fedcba98" }  # pin-ancestry: orphan',  # v-base-compat-rev
    '    "omnibase-core @ git+https://github.com/OmniNode-ai/omnibase_core.git@def4560000000000000000000000000000000000",  # pin-ancestry: orphan',  # v-mut-pep508-at-rev
    '    { name = "omnibase-core", git = "https://github.com/OmniNode-ai/omnibase_core.git?rev=def4560000000000000000000000000000000000" },  # pin-ancestry: orphan',  # v-mut-uvlock-qrev
    'omnibase-spi = { git = "https://github.com/OmniNode-ai/omnibase_spi.git", branch = "main" }  # pin-ancestry: orphan',  # v-mut-branch-main-diverged
    'omnibase-core = { git = "https://github.com/OmniNode-ai/omnibase_core.git", rev = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }  # pin-ancestry: unknown',  # v-mut-unknown-fail-closed
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    'omnibase-core = { git = "https://github.com/OmniNode-ai/omnibase_core.git", rev = "8ecb7efc17721dda2ce468b2e5051816ff8e89bc" }  # pin-ancestry: ancestor',  # c-base-pyproject-rev-ancestor
    '    "omnibase-core @ git+https://github.com/OmniNode-ai/omnibase_core.git@8ecb7efc17721dda2ce468b2e5051816ff8e89bc",  # pin-ancestry: ancestor',  # c-mut-pep508-at-rev-ancestor
    '    { name = "omnibase-core", git = "https://github.com/OmniNode-ai/omnibase_core.git?rev=8ecb7efc17721dda2ce468b2e5051816ff8e89bc" },  # pin-ancestry: ancestor',  # c-mut-uvlock-qrev-ancestor
    'some-thirdparty-lib = { git = "https://github.com/acme/thirdparty.git", rev = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef" }  # pin-ancestry: orphan',  # c-mut-non-sibling-git-pin
    '    "omnibase-core>=0.44.0,<0.47.0",',  # c-mut-version-range-pin
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
def test_finding_carries_sibling_pin_type_and_verdict() -> None:
    src = 'omnibase-core = { git = "x", rev = "def456" }  # pin-ancestry: orphan'
    result = scan_source(src)
    (finding,) = result.findings
    assert finding.sibling == "omnibase-core"
    assert finding.pin_type == "rev"
    assert finding.verdict == "orphan"
    assert finding.line == 1


# ---------------------------------------------------------------------------
# Hardening beyond the corpus — fail CLOSED on a missing annotation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sibling_git_pin_without_annotation_fails_closed() -> None:
    # The generated SEED skipped an unannotated sibling git pin (fail OPEN). The
    # hardened handler treats a missing annotation as 'unknown' and FLAGS it.
    src = 'omnibase-core = { git = "https://x/omnibase_core.git", rev = "def456" }'
    result = scan_source(src)
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.verdict == "unknown"


@pytest.mark.unit
def test_uvlock_branch_url_form_is_flagged() -> None:
    # HARDENING: uv.lock expresses a branch pin as `...omnibase_compat.git?branch=main`
    # (URL form), not the TOML `branch = "main"` form. The seed missed it.
    src = '    { name = "omnibase-compat", git = "https://github.com/OmniNode-ai/omnibase_compat.git?branch=main" },  # pin-ancestry: orphan'
    result = scan_source(src)
    assert result.flagged is True
    assert result.findings[0].pin_type == "branch"


@pytest.mark.unit
def test_uvlock_package_stanza_url_embedded_name_is_flagged() -> None:
    # HARDENING: the uv.lock `[[package]]` stanza puts the git source on a line that
    # carries the repo name only INSIDE the URL path (the package key `name = "..."`
    # is on a separate line). This is the literal #2071 / OMN-13507 form. The seed's
    # delimiter set missed the `/<repo>.git` URL-embedded name.
    src = 'source = { git = "https://github.com/OmniNode-ai/omnibase_core.git?rev=def4560000000000000000000000000000000000" }  # pin-ancestry: orphan'
    result = scan_source(src)
    assert result.flagged is True
    assert result.findings[0].sibling == "omnibase_core"
    assert result.findings[0].pin_type == "uv-lock-rev"


@pytest.mark.unit
def test_uvlock_stanza_ancestor_is_not_flagged() -> None:
    # The same URL-embedded-name stanza form, annotated ancestor, stays clean.
    src = 'source = { git = "https://github.com/OmniNode-ai/omnibase_core.git?rev=8ecb7efc17721dda2ce468b2e5051816ff8e89bc" }  # pin-ancestry: ancestor'
    assert scan_source(src).flagged is False


@pytest.mark.unit
def test_suppression_marker_skips_line() -> None:
    src = (
        'omnibase-core = { git = "x", rev = "def456" }  '
        "# pin-ancestry: orphan  # onex-allow-pin-hygiene"
    )
    assert scan_source(src).flagged is False


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerPinHygieneCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-pin-hygiene-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerPinHygieneCompute()
    envelope: ModelEventEnvelope[ModelPinHygieneScanInput] = ModelEventEnvelope(
        payload=ModelPinHygieneScanInput(
            content='omnibase-core = { git = "x", rev = "def456" }  # pin-ancestry: orphan',
            path="pyproject.toml",
        )
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "pyproject.toml"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.pin_hygiene.runtime_pin_hygiene import (
        PinHygieneBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = PinHygieneBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelPinHygieneScanInput(
                        content='omnibase-core = { git = "x", rev = "def456" }  # pin-ancestry: orphan',
                        path="bad.toml",
                    ),
                    ModelPinHygieneScanInput(
                        content='omnibase-core = { git = "x", rev = "abc123" }  # pin-ancestry: ancestor',
                        path="ok.toml",
                    ),
                ]
            )
        finally:
            await bus.shutdown()
        by_path = {r.path: r for r in results}
        assert by_path["bad.toml"].flagged is True
        assert by_path["ok.toml"].flagged is False

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# EFFECT runner git resolution + the #2071 recurrence proof
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _make_sibling_repo(omni_home: Path) -> tuple[str, str]:
    """Build a real omnibase_core clone with a dev line and a DIVERGED main.

    Returns (ancestor_sha, orphan_sha):
    * ancestor_sha is a commit ON the dev line (ancestor of dev HEAD) — clean.
    * orphan_sha is a commit on a 'main' branch that DIVERGED from dev (the #2071
      shape) — must flag.
    """
    repo = omni_home / "omnibase_core"
    return _build_diverged_repo(repo)


@pytest.mark.unit
def test_annotate_ancestry_resolves_real_git_state(tmp_path: Path) -> None:
    from omnibase_core.validation.pin_hygiene.runtime_pin_hygiene import (
        annotate_ancestry,
    )

    ancestor_sha, orphan_sha = _make_sibling_repo(tmp_path)
    # A rev pin to an ancestor commit → annotated 'ancestor'.
    ann = annotate_ancestry(
        f'omnibase-core = {{ git = "x", rev = "{ancestor_sha}" }}', tmp_path
    )
    assert "# pin-ancestry: ancestor" in ann
    # A rev pin to a diverged (off-dev) commit → 'orphan'.
    ann = annotate_ancestry(
        f'omnibase-core = {{ git = "x", rev = "{orphan_sha}" }}', tmp_path
    )
    assert "# pin-ancestry: orphan" in ann
    # A rev that does not exist in the clone → 'unknown' (fail closed).
    ann = annotate_ancestry(
        'omnibase-core = { git = "x", rev = "0000000000000000000000000000000000000000" }',
        tmp_path,
    )
    assert "# pin-ancestry: unknown" in ann


@pytest.mark.unit
def test_branch_main_diverged_is_flagged_end_to_end(tmp_path: Path) -> None:
    # THE #2071 SHAPE: a branch=main sibling pin whose main has diverged from dev.
    from omnibase_core.validation.pin_hygiene.runtime_pin_hygiene import (
        annotate_ancestry,
    )

    _make_sibling_repo(tmp_path)
    pin = 'omnibase-spi = { git = "x", branch = "main" }'
    # build a spi repo with the same diverged-main shape so the branch resolves
    _make_sibling_repo_named(tmp_path, "omnibase_spi")
    annotated = annotate_ancestry(pin, tmp_path)
    assert "# pin-ancestry: orphan" in annotated, annotated
    assert scan_source(annotated).flagged is True


def _make_sibling_repo_named(omni_home: Path, repo_name: str) -> None:
    _build_diverged_repo(omni_home / repo_name)


def _build_diverged_repo(repo: Path) -> tuple[str, str]:
    """Create a git repo with a 'dev' line and a 'main' that diverged from base.

    Returns (ancestor_sha on dev line, orphan_sha on diverged main). The default
    branch from ``git init`` is explicitly named ``dev`` (``-b dev``) so creating
    ``main`` from the base commit does not collide with it.
    """
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base_sha = _git(repo, "rev-parse", "HEAD")
    # dev line continues from base.
    (repo / "f.txt").write_text("dev work\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "dev work")
    # main diverges from base (a commit that is NOT on the dev line).
    _git(repo, "checkout", "-q", "-b", "main", base_sha)
    (repo / "g.txt").write_text("diverged main work\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "diverged main")
    orphan_sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "dev")
    return base_sha, orphan_sha


@pytest.mark.unit
def test_pyproject_suppression_propagates_to_uvlock() -> None:
    # A sibling suppressed in pyproject.toml (the source of truth) propagates the
    # suppression to its derived uv.lock entries — uv.lock comments do not survive
    # `uv lock`, so the durable suppression lives in pyproject.
    from omnibase_core.validation.pin_hygiene.runtime_pin_hygiene import (
        _propagate_suppression,
        _suppressed_siblings,
    )

    pyproject = (
        'omnibase-compat = { git = "x", branch = "main" }  '
        "# onex-allow-pin-hygiene OMN-13522"
    )
    suppressed = _suppressed_siblings(pyproject)
    assert suppressed == {"omnibase_compat"}

    uvlock = 'source = { git = "https://github.com/OmniNode-ai/omnibase_compat.git?branch=main#abc" }'
    propagated = _propagate_suppression(uvlock, suppressed)
    assert "onex-allow-pin-hygiene" in propagated
    assert scan_source(propagated).flagged is False
    # an UNSUPPRESSED sibling in the same lock is NOT propagated
    other = 'source = { git = "https://github.com/OmniNode-ai/omnibase_core.git?rev=def4560000000000000000000000000000000000" }  # pin-ancestry: orphan'
    assert "onex-allow-pin-hygiene" not in _propagate_suppression(other, suppressed)
    assert scan_source(_propagate_suppression(other, suppressed)).flagged is True


@pytest.mark.unit
def test_ancestor_pin_passes_end_to_end(tmp_path: Path) -> None:
    from omnibase_core.validation.pin_hygiene.runtime_pin_hygiene import (
        annotate_ancestry,
    )

    ancestor_sha, _ = _make_sibling_repo(tmp_path)
    pin = f'omnibase-core = {{ git = "x", rev = "{ancestor_sha}" }}'
    annotated = annotate_ancestry(pin, tmp_path)
    assert "# pin-ancestry: ancestor" in annotated
    assert scan_source(annotated).flagged is False
