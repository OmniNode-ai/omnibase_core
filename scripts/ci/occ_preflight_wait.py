# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Bounded wait for ``occ-preflight / eligibility`` (OMN-17864).

Why this module exists
-----------------------
``occ-preflight.yml``'s "Resolve Evidence-Source" step used to be a single
bash check: if the PR body had no ``Evidence-Source:`` line yet, or the cited
onex_change_control companion PR had not merged yet, the step ``exit 1``'d in
2-8 seconds. Both conditions are TRANSIENT — the OCC autobind PATCHes the
stamp onto the body after the PR opens, and the companion merges some minutes
later — but the aggregator that reads this job's conclusion never re-runs, so
a real, would-eventually-pass PR was recorded FAILURE forever.

Measured over 188 merged product PRs in the 48h to 2026-09-16T14:47Z: 53 PRs
had their first CI run conclude BEFORE the cited companion merged, and 0 of
those 53 concluded success. Of the 135 whose first run concluded after the
companion merged, 77 (57%) succeeded. Time from CI-run start to companion
merge: median 16 min, p75 26, p90 41, p95 55, max 239 -- a 1500-second budget
covers 141/188 (75%).

The fix is the producer, not the aggregator: this job already sits inside a
CI run whose sibling job, "OCC Companion Merged Gate (OMN-15214)"
(``scripts/ci/check_occ_companion_merged.py``), polls the IDENTICAL fact
(live PR body, cited companion merged or not) for up to
``DEADLINE_SECONDS=1500`` at ``POLL_INTERVAL_SECONDS=30``, unconditionally,
on every run. Giving ``occ-preflight`` the same bounded wait costs no
additional wall clock on the critical path -- the run already pays for that
budget elsewhere. 1500/30 is that already-declared, already-paid budget for
the same fact in the same run, not a new number invented for this module.

Shape
-----
Mirrors ``occ_preflight_heal.py``: a pure ``decide_preflight_wait`` verdict
function, a :class:`GhPort` protocol for the live reads it needs, a
:class:`GhCli` implementation backed by the ``gh`` binary, and a thin
``main()`` polling driver. The pure function is exhaustively unit-tested;
the client is exercised only by the workflow itself.

Every branch fails closed. An unreadable PR body is ``FAIL_NOW``, not
``WAIT`` -- there is nothing to re-read that will fix itself. A companion
CLOSED without merging is ``FAIL_NOW`` -- that is the exact OMN-15214
incident state, and waiting cannot un-close it. A malformed evidence-source
value is ``FAIL_NOW`` -- waiting cannot repair an authoring error. A
evidence-source SHA that is not an ancestor of any onex_change_control
durable branch is ``FAIL_NOW`` -- onex_change_control is squash-only, so a
feature-branch head SHA can never become one (OMN-15216), and no amount of
elapsed time changes that. Only ``stamp_absent`` and ``companion_unmerged``
are genuinely retryable, and even those convert to ``DEADLINE`` (also a hard
failure) once ``elapsed_seconds >= deadline_seconds``.

A ``merge_group`` (or any non-``pull_request``) event always ``PROCEED``s
immediately, never waits. Invariant I2 in ``occ-preflight.yml``'s own header
requires a ``merge_group`` run to re-validate fully against the pinned
evidence and fail fast; a bounded wait on that event would blur "fast" and
would let a stale in-flight PR-open evaluation leak into the merge-queue
gate, which is the one thing I2 exists to prevent.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # fixed argv, no shell, trusted gh binary
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol

EXIT_OK: Final[int] = 0
EXIT_ERROR: Final[int] = 1

OCC_REPO_DEFAULT: Final[str] = "OmniNode-ai/onex_change_control"

# Branches on which an evidence-source commit SHA counts as durable evidence.
# Mirrors check_occ_companion_merged.OCC_DURABLE_BRANCHES.
OCC_DURABLE_BRANCHES: Final[tuple[str, ...]] = ("dev", "main")

# The already-paid OMN-15214 budget for the identical fact in the same run.
# See module docstring -- this is not a new number, it is the existing one.
DEFAULT_DEADLINE_SECONDS: Final[int] = 1500
DEFAULT_POLL_INTERVAL_SECONDS: Final[int] = 30

EVIDENCE_SOURCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^Evidence-Source:\s+(\S.*)$", re.IGNORECASE | re.MULTILINE
)
OCC_PR_REF_RE: Final[re.Pattern[str]] = re.compile(r"^OCC#(\d+)$", re.IGNORECASE)
HEX_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")

_ENFORCED_EVENT: Final[str] = "pull_request"


class EnumPreflightWaitOutcome(StrEnum):
    """One value per terminal or poll-again branch of :func:`decide_preflight_wait`."""

    PROCEED = "proceed"
    WAIT = "wait"
    FAIL_NOW = "fail_now"
    DEADLINE = "deadline"


@dataclass(frozen=True)
class ModelPreflightWaitDecision:
    """One poll's verdict. ``reason`` is a stable machine-readable token;
    ``detail`` names the PR, the companion, and the elapsed seconds for a
    human reading the job log."""

    outcome: EnumPreflightWaitOutcome
    reason: str
    detail: str

    @property
    def should_continue_polling(self) -> bool:
        return self.outcome is EnumPreflightWaitOutcome.WAIT

    @property
    def is_terminal_failure(self) -> bool:
        return self.outcome in (
            EnumPreflightWaitOutcome.FAIL_NOW,
            EnumPreflightWaitOutcome.DEADLINE,
        )


def parse_evidence_source(pr_body: str) -> str | None:
    """First ``Evidence-Source:`` value in *pr_body*, or ``None``."""
    match = EVIDENCE_SOURCE_RE.search(pr_body)
    return match.group(1).strip() if match else None


def _wait_or_deadline(
    *, reason: str, detail: str, elapsed_seconds: int, deadline_seconds: int
) -> ModelPreflightWaitDecision:
    """Shared tail of every retryable branch (rule 8 of the design)."""
    if elapsed_seconds >= deadline_seconds:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.DEADLINE,
            reason=reason,
            detail=(
                f"{detail} -- poll deadline ({deadline_seconds}s) reached after "
                f"{elapsed_seconds}s; failing closed"
            ),
        )
    return ModelPreflightWaitDecision(
        outcome=EnumPreflightWaitOutcome.WAIT,
        reason=reason,
        detail=f"{detail} ({elapsed_seconds}s elapsed of {deadline_seconds}s budget)",
    )


def decide_preflight_wait(
    *,
    pr_body: str | None,
    companion_state: str | None,
    cited_sha_is_ancestor: bool,
    elapsed_seconds: int,
    deadline_seconds: int,
    event_name: str,
) -> ModelPreflightWaitDecision:
    """Pure verdict for one poll iteration.

    ``companion_state`` is the live onex_change_control companion PR state
    when the evidence-source stamp cites one (``"MERGED"`` / ``"OPEN"`` /
    ``"CLOSED"``), or ``None`` when the stamp cites a SHA instead, or when a
    companion was cited but its state could not be read (a retryable
    transport failure, distinct from an authoritative CLOSED).

    ``cited_sha_is_ancestor`` is only consulted when the stamp is SHA-shaped;
    it is ignored otherwise.
    """
    if event_name != _ENFORCED_EVENT:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.PROCEED,
            reason="non_pull_request_event",
            detail=(
                f"event '{event_name}' is not '{_ENFORCED_EVENT}'; invariant I2 "
                "requires a merge_group run to re-validate against pinned evidence "
                "and fail fast, so the bounded wait never applies here"
            ),
        )

    if pr_body is None:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.FAIL_NOW,
            reason="body_unreadable",
            detail=(
                "the PR body could not be read; failing closed rather than waiting "
                "on a surface that cannot be observed"
            ),
        )

    stamp = parse_evidence_source(pr_body)
    if stamp is None:
        return _wait_or_deadline(
            reason="stamp_absent",
            detail=(
                "PR body has no evidence-source stamp line yet (the occ-autobind "
                "mint may still be in flight)"
            ),
            elapsed_seconds=elapsed_seconds,
            deadline_seconds=deadline_seconds,
        )

    occ_ref = OCC_PR_REF_RE.match(stamp)
    is_hex_sha = HEX_SHA_RE.match(stamp.lower()) is not None

    if occ_ref is None and not is_hex_sha:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.FAIL_NOW,
            reason="stamp_malformed",
            detail=(
                f"evidence-source value '{stamp}' is neither 'OCC#<number>' nor a "
                "hex commit SHA; waiting cannot repair an authoring error"
            ),
        )

    if occ_ref is not None:
        companion_pr = occ_ref.group(1)
        state = (companion_state or "").upper()

        if state == "MERGED":
            return ModelPreflightWaitDecision(
                outcome=EnumPreflightWaitOutcome.PROCEED,
                reason="evidence_durable",
                detail=f"companion OCC#{companion_pr} is MERGED -- evidence is durable",
            )

        if state == "CLOSED":
            # The exact OMN-15214 incident state: an OPEN companion closed
            # without merging. Never poll; the evidence no longer exists.
            return ModelPreflightWaitDecision(
                outcome=EnumPreflightWaitOutcome.FAIL_NOW,
                reason="companion_closed_unmerged",
                detail=(
                    f"companion OCC#{companion_pr} is CLOSED without merging -- the "
                    "cited evidence no longer exists, and waiting cannot bring it back"
                ),
            )

        # "OPEN" or unresolved (a transient read failure on the companion
        # lookup itself) both retry: only an authoritative CLOSED is terminal.
        retry_reason = (
            "companion_unmerged" if state == "OPEN" else "companion_state_unresolved"
        )
        retry_detail = (
            f"companion OCC#{companion_pr} is still OPEN -- it must merge before "
            "this PR may merge"
            if state == "OPEN"
            else f"could not resolve the live state of companion OCC#{companion_pr} (retryable)"
        )
        return _wait_or_deadline(
            reason=retry_reason,
            detail=retry_detail,
            elapsed_seconds=elapsed_seconds,
            deadline_seconds=deadline_seconds,
        )

    # SHA-shaped stamp.
    if cited_sha_is_ancestor:
        return ModelPreflightWaitDecision(
            outcome=EnumPreflightWaitOutcome.PROCEED,
            reason="evidence_durable",
            detail=(
                f"evidence-source SHA {stamp} is an ancestor of an OCC durable "
                "branch -- evidence is durable"
            ),
        )
    return ModelPreflightWaitDecision(
        outcome=EnumPreflightWaitOutcome.FAIL_NOW,
        reason="sha_not_ancestor",
        detail=(
            f"evidence-source SHA {stamp} is not an ancestor of any OCC durable "
            f"branch {OCC_DURABLE_BRANCHES} -- onex_change_control is squash-only, "
            "so a feature-branch head SHA can never become one (OMN-15216); "
            "waiting cannot repair this"
        ),
    )


class GhPort(Protocol):
    """The live GitHub reads this poll needs."""

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None: ...

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]: ...

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None: ...

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> bool: ...


class GhCli:
    """:class:`GhPort` backed by the ``gh`` binary."""

    def _run(self, argv: list[str]) -> str | None:
        try:
            proc = subprocess.run(  # fixed argv, no shell
                argv, capture_output=True, text=True, timeout=60, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"::warning::gh invocation failed: {exc}", file=sys.stderr)
            return None
        if proc.returncode != 0:
            print(
                f"::warning::{' '.join(argv[:4])}... exited {proc.returncode}: "
                f"{proc.stderr.strip()[:300]}",
                file=sys.stderr,
            )
            return None
        return proc.stdout

    def read_pr_body(self, *, repo: str, pr_number: str) -> str | None:
        """The LIVE body via the REST API -- never the triggering event
        payload. occ-autobind PATCHes Evidence-Source onto the body AFTER the
        triggering event fired, which is exactly the race this module closes.
        """
        raw = self._run(
            ["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".body"]
        )
        if raw is None:
            return None
        text = raw.rstrip("\n")
        return "" if text == "null" else text

    def read_companion(
        self, *, occ_repo: str, pr_number: str
    ) -> tuple[str | None, str]:
        raw = self._run(
            [
                "gh",
                "pr",
                "view",
                pr_number,
                "--repo",
                occ_repo,
                "--json",
                "state,headRefOid,mergeCommit",
            ]
        )
        if raw is None:
            return None, ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None, ""
        if not isinstance(data, dict):
            return None, ""
        state_raw = data.get("state")
        state = (
            str(state_raw).upper() if isinstance(state_raw, str) and state_raw else None
        )
        sha = ""
        if state == "MERGED":
            merge_commit = data.get("mergeCommit")
            if isinstance(merge_commit, dict):
                sha = str(merge_commit.get("oid") or "")
        else:
            head_ref_oid = data.get("headRefOid")
            sha = str(head_ref_oid) if isinstance(head_ref_oid, str) else ""
        return state, sha

    def canonicalize_sha(self, *, occ_repo: str, sha: str) -> str | None:
        raw = self._run(
            ["gh", "api", f"repos/{occ_repo}/commits/{sha}", "--jq", ".sha"]
        )
        text = raw.strip() if raw is not None else ""
        return text or None

    def sha_is_ancestor(
        self, *, occ_repo: str, sha: str, branches: tuple[str, ...]
    ) -> bool:
        for branch in branches:
            raw = self._run(
                [
                    "gh",
                    "api",
                    f"repos/{occ_repo}/compare/{branch}...{sha}",
                    "--jq",
                    ".status",
                ]
            )
            if raw is not None and raw.strip() in ("identical", "behind"):
                return True
        return False


def _resolve_facts(
    client: GhPort, *, repo: str, pr_number: str, occ_repo: str
) -> tuple[str | None, str | None, bool, str]:
    """One round of live reads. Returns (pr_body, companion_state,
    cited_sha_is_ancestor, resolved_sha)."""
    pr_body = client.read_pr_body(repo=repo, pr_number=pr_number)
    if pr_body is None:
        return None, None, False, ""

    stamp = parse_evidence_source(pr_body)
    if stamp is None:
        return pr_body, None, False, ""

    occ_ref = OCC_PR_REF_RE.match(stamp)
    if occ_ref is not None:
        state, sha = client.read_companion(
            occ_repo=occ_repo, pr_number=occ_ref.group(1)
        )
        return pr_body, state, False, sha

    if HEX_SHA_RE.match(stamp.lower()) is not None:
        canonical = client.canonicalize_sha(occ_repo=occ_repo, sha=stamp)
        resolved_sha = canonical or stamp
        is_ancestor = client.sha_is_ancestor(
            occ_repo=occ_repo, sha=resolved_sha, branches=OCC_DURABLE_BRANCHES
        )
        return pr_body, None, is_ancestor, resolved_sha

    # Malformed; decide_preflight_wait reports this itself from pr_body.
    return pr_body, None, False, ""


def _write_github_output(name: str, value: str, *, github_output_path: str) -> None:
    # No os.environ read here by design (OMN-17744 typed-bootstrap-only
    # boundary): the caller resolves $GITHUB_OUTPUT in the workflow's bash
    # step and passes it explicitly via --github-output-path.
    if not github_output_path:
        return
    with open(github_output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _build_parser() -> argparse.ArgumentParser:
    # Every value this CLI needs is passed explicitly by the caller (see
    # occ-preflight.yml's "Resolve Evidence-Source" step) -- no os.environ
    # fallback defaults, per the OMN-17744 typed-bootstrap-only boundary.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="")
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--event-name", default="pull_request")
    parser.add_argument("--occ-repo", default=OCC_REPO_DEFAULT)
    parser.add_argument(
        "--deadline-seconds", type=int, default=DEFAULT_DEADLINE_SECONDS
    )
    parser.add_argument(
        "--poll-interval-seconds", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS
    )
    parser.add_argument(
        "--github-output-path",
        default="",
        help="Value of $GITHUB_OUTPUT, resolved by the caller and passed explicitly.",
    )
    return parser


def main(argv: list[str] | None = None, *, gh: GhPort | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.repo or not args.pr_number:
        print("--repo and --pr-number are required", file=sys.stderr)
        return EXIT_ERROR

    client: GhPort = gh if gh is not None else GhCli()
    start = time.monotonic()

    while True:
        elapsed = int(time.monotonic() - start)
        pr_body, companion_state, cited_sha_is_ancestor, resolved_sha = _resolve_facts(
            client, repo=args.repo, pr_number=args.pr_number, occ_repo=args.occ_repo
        )
        decision = decide_preflight_wait(
            pr_body=pr_body,
            companion_state=companion_state,
            cited_sha_is_ancestor=cited_sha_is_ancestor,
            elapsed_seconds=elapsed,
            deadline_seconds=args.deadline_seconds,
            event_name=args.event_name,
        )
        print(
            f"occ-preflight wait: [{decision.outcome.value}] {decision.reason} -- {decision.detail}"
        )

        if decision.outcome is EnumPreflightWaitOutcome.PROCEED:
            if resolved_sha:
                _write_github_output(
                    "sha", resolved_sha, github_output_path=args.github_output_path
                )
                print(f"::notice::Evidence-Source resolved to OCC SHA: {resolved_sha}")
            return EXIT_OK

        if decision.is_terminal_failure:
            print(f"::error::{decision.detail}", file=sys.stderr)
            return EXIT_ERROR

        time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
