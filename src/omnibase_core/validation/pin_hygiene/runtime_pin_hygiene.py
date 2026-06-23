# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Git-aware two-transport runner for the pin-hygiene COMPUTE validator (OMN-13509).

The seam that makes the SAME ``HandlerPinHygieneCompute`` run over a swappable bus
backend (identical to the private-IP / no-faked-boundary validators):

* **pre-commit** (default here): the in-memory backend (``EventBusInmemory``) —
  in-process, zero infra, deterministic, fast.
* **CI**: the same handler, a Kafka backend, fanned across the runner fleet.

Only the *backend* changes; the handler and dispatch shape are identical, so
local and CI verdicts cannot drift.

WHAT MAKES THIS RUNNER DIFFERENT from the pure-text scanners: the gate verdict
depends on GIT ANCESTRY, which is I/O. To keep the COMPUTE handler pure, the
runner — the EFFECT boundary — resolves that I/O and feeds the handler text:

1. ``_iter_pin_files`` / ``_read_text`` load the candidate ``pyproject.toml`` /
   ``uv.lock`` files (the file I/O).
2. ``_annotate_ancestry`` finds each guarded sibling git pin (rev / @rev / ?rev=
   / branch=), resolves the sibling's ``dev`` HEAD from its local canonical clone
   under ``$OMNI_HOME``, runs ``git merge-base --is-ancestor <pinned> <dev-head>``,
   and rewrites the line with a trailing ``# pin-ancestry: ancestor|orphan|unknown``
   annotation (the git I/O). ``unknown`` is the fail-closed sentinel for any pin
   whose ancestry could not be resolved (rev not found, sibling clone missing,
   git error).
3. The ANNOTATED text is published as a typed command envelope onto the bus; the
   pure COMPUTE handler scans the TEXT (reading the annotation, never running git)
   and publishes its verdict back on the result topic; the runner aggregates
   findings and exits non-zero when any pin is flagged.

This is the honest division: git resolution is an EFFECT, the verdict is COMPUTE.
The handler never runs git or reads files.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from omnibase_core.constants.constants_event_types import (
    TOPIC_VALIDATION_PIN_HYGIENE_SCAN_COMPLETED_EVENT,
    TOPIC_VALIDATION_PIN_HYGIENE_SCAN_REQUESTED_CMD,
)
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.pin_hygiene.handler import HandlerPinHygieneCompute
from omnibase_core.validation.pin_hygiene.models import (
    ModelPinHygieneScanInput,
    ModelPinHygieneScanResult,
)

__all__ = [
    "COMMAND_TOPIC",
    "RESULT_TOPIC",
    "PinHygieneBusRunner",
    "annotate_ancestry",
    "main",
]

# Contract-style topic names sourced from the canonical topic registry.
COMMAND_TOPIC: Final[str] = TOPIC_VALIDATION_PIN_HYGIENE_SCAN_REQUESTED_CMD
RESULT_TOPIC: Final[str] = TOPIC_VALIDATION_PIN_HYGIENE_SCAN_COMPLETED_EVENT

_RUNNER_GROUP: Final[str] = "validator-pin-hygiene-runner"
_HANDLER_GROUP: Final[str] = "validator-pin-hygiene-compute"

# Only dependency-pin manifests carry sibling git pins.
_PIN_FILENAMES: Final[frozenset[str]] = frozenset({"pyproject.toml", "uv.lock"})

_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        ".next",
        "dist",
        "build",
        ".onex_state",
        "omni_worktrees",
    }
)

# The three guarded sibling distributions → their local canonical-clone directory
# name under $OMNI_HOME (the repo-name underscore form).
_SIBLING_REPO: Final[dict[str, str]] = {
    "omnibase-core": "omnibase_core",
    "omnibase-spi": "omnibase_spi",
    "omnibase-compat": "omnibase_compat",
    "omnibase_core": "omnibase_core",
    "omnibase_spi": "omnibase_spi",
    "omnibase_compat": "omnibase_compat",
}

# Sibling name as a delimited token (mirrors the handler's HARDENED
# _PATTERN_SIBLING — must include the `/` URL-path prefix and `.`/`@` suffix so the
# uv.lock `[[package]]` stanza form `.../omnibase_compat.git?branch=main#<sha>` is
# caught, where the package key is on a separate line).
_PATTERN_SIBLING: Final[re.Pattern[str]] = re.compile(
    rf'(?:^|\s|"|,|;|/)({"|".join(_SIBLING_REPO)})(?:\s|,|;|"|\[|@|\.|$)',
    re.IGNORECASE,
)
_PATTERN_REV: Final[re.Pattern[str]] = re.compile(
    r'rev\s*=\s*["\']([a-fA-F0-9]+)["\']', re.IGNORECASE
)
_PATTERN_PEP508: Final[re.Pattern[str]] = re.compile(
    r"""git\+https://.*?@([a-fA-F0-9]{7,40})(?=#|$|["'])"""
)
_PATTERN_UVLOCK: Final[re.Pattern[str]] = re.compile(r"\?rev=([a-fA-F0-9]{7,40})")
# Branch pin in both the TOML form `branch = "<name>"` and the uv.lock URL form
# `?branch=<name>` (must mirror the handler's _PATTERN_BRANCH).
_PATTERN_BRANCH: Final[re.Pattern[str]] = re.compile(
    r'branch\s*=\s*["\']([^"\']+)["\']|\?branch=([A-Za-z0-9._/\-]+)', re.IGNORECASE
)
# A line that already carries an annotation is left as-is (idempotent re-runs).
_PATTERN_ANCESTRY: Final[re.Pattern[str]] = re.compile(r"#\s*pin-ancestry:\s*\w+")

# Dev integration line every sibling pin is measured against.
_DEV_REF: Final[str] = "dev"


def _omni_home() -> Path | None:
    raw = os.environ.get("OMNI_HOME")
    return Path(raw) if raw else None


def _git(repo: Path, *args: str) -> tuple[int, str]:
    """Run a git command in ``repo``; return (returncode, stripped stdout)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def _resolve_dev_head(repo: Path) -> str | None:
    """Resolve the sibling's dev HEAD commit, preferring origin/dev then dev."""
    for ref in (f"origin/{_DEV_REF}", _DEV_REF):
        rc, sha = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if rc == 0 and sha:
            return sha
    return None


def _is_ancestor(repo: Path, pinned: str, dev_head: str) -> str:
    """Return the ancestry verdict for ``pinned`` vs ``dev_head`` in ``repo``.

    ``ancestor`` — pinned is an ancestor of (or equal to) dev_head.
    ``orphan``   — pinned is a real commit but NOT on the dev line (diverged).
    ``unknown``  — pinned could not be resolved to a commit in the clone (fail closed).
    """
    rc, _ = _git(repo, "cat-file", "-e", f"{pinned}^{{commit}}")
    if rc != 0:
        return "unknown"
    rc, _ = _git(repo, "merge-base", "--is-ancestor", pinned, dev_head)
    if rc == 0:
        return "ancestor"
    if rc == 1:
        return "orphan"
    return "unknown"


def _resolve_branch_head(repo: Path, branch: str) -> str | None:
    """Resolve a branch name to its commit, preferring the origin remote ref."""
    for ref in (f"origin/{branch}", branch):
        rc, sha = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if rc == 0 and sha:
            return sha
    return None


def _pinned_commit(line: str, repo: Path) -> str | None:
    """Extract the pinned commit for a sibling line (rev / @rev / ?rev= / branch)."""
    for pat in (_PATTERN_REV, _PATTERN_PEP508, _PATTERN_UVLOCK):
        m = pat.search(line)
        if m is not None:
            return m.group(1)
    m = _PATTERN_BRANCH.search(line)
    if m is not None:
        # A branch pin resolves to that branch's current head in the sibling clone.
        # Group 1 is the TOML `branch = "x"` form; group 2 the uv.lock `?branch=x`.
        branch = m.group(1) or m.group(2)
        return _resolve_branch_head(repo, branch)
    return None


def annotate_ancestry(content: str, omni_home: Path | None) -> str:
    """Annotate every guarded sibling git pin line with its resolved ancestry.

    This is the EFFECT: for each sibling git pin, resolve the sibling's dev HEAD
    from its canonical clone under ``omni_home`` and decide ancestor/orphan via
    git, appending ``# pin-ancestry: <verdict>``. ``unknown`` is appended (fail
    closed) when the clone is missing or the commit cannot be resolved. Lines that
    already carry an annotation, non-sibling lines, and version-range (no-git)
    sibling lines are returned unchanged.
    """
    out: list[str] = []
    for line in content.splitlines():
        if _PATTERN_ANCESTRY.search(line):
            out.append(line)
            continue
        sib = _PATTERN_SIBLING.search(line)
        is_git_pin = any(
            p.search(line) for p in (_PATTERN_REV, _PATTERN_PEP508, _PATTERN_UVLOCK)
        ) or (_PATTERN_BRANCH.search(line) is not None)
        if sib is None or not is_git_pin:
            out.append(line)
            continue

        repo_name = _SIBLING_REPO[sib.group(1).lower()]
        repo = (omni_home / repo_name) if omni_home is not None else None
        verdict = "unknown"
        if repo is not None and (repo / ".git").exists():
            dev_head = _resolve_dev_head(repo)
            pinned = _pinned_commit(line, repo)
            if dev_head is not None and pinned:
                verdict = _is_ancestor(repo, pinned, dev_head)
        out.append(f"{line}  # pin-ancestry: {verdict}")
    return "\n".join(out)


class PinHygieneBusRunner:
    """Dispatch annotated pin text to the COMPUTE handler over a swappable bus."""

    def __init__(self, bus: EventBusInmemory) -> None:
        self._bus = bus
        self._handler = HandlerPinHygieneCompute()
        self._results: dict[str, ModelPinHygieneScanResult] = {}

    async def _on_command(self, message: ModelEventMessage) -> None:
        raw = json.loads(message.value.decode("utf-8"))
        scan_input = ModelPinHygieneScanInput.model_validate(raw)
        envelope: ModelEventEnvelope[ModelPinHygieneScanInput] = ModelEventEnvelope(
            payload=scan_input
        )
        output = await self._handler.handle(envelope)
        result = output.result
        assert result is not None  # COMPUTE always returns a result
        await self._bus.publish(
            RESULT_TOPIC, None, result.model_dump_json().encode("utf-8")
        )

    async def _on_result(self, message: ModelEventMessage) -> None:
        raw = json.loads(message.value.decode("utf-8"))
        result = ModelPinHygieneScanResult.model_validate(raw)
        self._results[result.path] = result

    async def scan_inputs(
        self, inputs: list[ModelPinHygieneScanInput]
    ) -> list[ModelPinHygieneScanResult]:
        await self._bus.subscribe(
            COMMAND_TOPIC, on_message=self._on_command, group_id=_HANDLER_GROUP
        )
        await self._bus.subscribe(
            RESULT_TOPIC, on_message=self._on_result, group_id=_RUNNER_GROUP
        )
        for scan_input in inputs:
            await self._bus.publish(
                COMMAND_TOPIC, None, scan_input.model_dump_json().encode("utf-8")
            )
        await asyncio.sleep(0)
        return [
            self._results[scan_input.path]
            for scan_input in inputs
            if scan_input.path in self._results
        ]


def _iter_pin_files(paths: list[Path]) -> Iterator[Path]:
    """EFFECT boundary: yield pyproject.toml / uv.lock files, pruning skip-dirs."""
    for p in paths:
        if p.is_file():
            if p.name in _PIN_FILENAMES and not any(
                part in _SKIP_DIRS for part in p.parts
            ):
                yield p
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if any(part in _SKIP_DIRS for part in child.parts):
                    continue
                if child.is_file() and child.name in _PIN_FILENAMES:
                    yield child


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


# A sibling pin suppressed in pyproject.toml (the source of truth) propagates its
# suppression to the derived uv.lock entries for that same sibling. uv.lock is a
# machine-generated artifact: an inline `# onex-allow-pin-hygiene` comment there
# does NOT survive `uv lock`, so the durable suppression lives in pyproject and is
# carried forward here. This is the honest division: ONE declared, ticket-tracked
# suppression in the source manifest; the lock entries inherit it.
_SUPPRESSION_MARKER: Final[str] = "onex-allow-pin-hygiene"


def _suppressed_siblings(pyproject_text: str) -> set[str]:
    """Repo-name siblings whose pyproject pin line carries the suppression marker."""
    suppressed: set[str] = set()
    for line in pyproject_text.splitlines():
        if _SUPPRESSION_MARKER not in line:
            continue
        sib = _PATTERN_SIBLING.search(line)
        if sib is not None:
            suppressed.add(_SIBLING_REPO[sib.group(1).lower()])
    return suppressed


def _propagate_suppression(uvlock_text: str, suppressed: set[str]) -> str:
    """Inject the suppression marker into uv.lock lines for already-suppressed siblings."""
    if not suppressed:
        return uvlock_text
    out: list[str] = []
    for line in uvlock_text.splitlines():
        sib = _PATTERN_SIBLING.search(line)
        if (
            sib is not None
            and _SIBLING_REPO[sib.group(1).lower()] in suppressed
            and _SUPPRESSION_MARKER not in line
        ):
            out.append(
                f"{line}  # {_SUPPRESSION_MARKER} (inherited from pyproject.toml)"
            )
        else:
            out.append(line)
    return "\n".join(out)


async def _run(paths: list[Path], *, quiet: bool) -> int:
    omni_home = _omni_home()
    pin_files = list(_iter_pin_files(paths))
    # Collect siblings suppressed in any in-scope pyproject.toml (source of truth)
    # so their derived uv.lock entries inherit the (ticket-tracked) suppression.
    suppressed: set[str] = set()
    for fp in pin_files:
        if fp.name == "pyproject.toml":
            suppressed |= _suppressed_siblings(_read_text(fp))

    inputs: list[ModelPinHygieneScanInput] = []
    for fp in pin_files:
        text = _read_text(fp)
        if fp.name == "uv.lock":
            text = _propagate_suppression(text, suppressed)
        inputs.append(
            ModelPinHygieneScanInput(
                content=annotate_ancestry(text, omni_home), path=str(fp)
            )
        )
    bus = EventBusInmemory()
    await bus.start()
    try:
        runner = PinHygieneBusRunner(bus)
        results = await runner.scan_inputs(inputs)
    finally:
        await bus.shutdown()

    flagged = [r for r in results if r.flagged]
    total_findings = 0
    for result in flagged:
        for finding in result.findings:
            total_findings += 1
            print(
                f"{finding.path}:{finding.line}: [{finding.sibling} "
                f"{finding.pin_type} -> {finding.verdict}] {finding.matched_text!r}"
            )

    if not quiet:
        if total_findings:
            print(
                f"\n{total_findings} non-ancestor sibling-pin finding(s). A sibling "
                f"(omnibase-core/spi/compat) git pin must point at a commit that is "
                f"an ANCESTOR of that sibling's dev HEAD. Re-pin to a dev-line commit "
                f"(or merge the sibling first), or add `# onex-allow-pin-hygiene` to "
                f"suppress an approved exception."
            )
        else:
            print("No sibling pin-hygiene violations found.")
    return 1 if total_findings else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: scan staged pin files (pre-commit) or directories over the bus.

    Exit codes: 0 — no violations; 1 — violations found.
    """
    parser = argparse.ArgumentParser(
        prog="check-pin-hygiene",
        description=(
            "Block sibling dependency pins (omnibase-core/spi/compat git rev or "
            "branch=) whose pinned commit is NOT an ancestor of that sibling's dev "
            "HEAD, executed as a COMPUTE node over the in-memory event bus. Git "
            "ancestry is resolved at the EFFECT boundary (OMN-13509)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress the trailing summary"
    )
    parsed = parser.parse_args(argv)
    return asyncio.run(_run(parsed.paths, quiet=parsed.quiet))


if __name__ == "__main__":
    sys.exit(main())
