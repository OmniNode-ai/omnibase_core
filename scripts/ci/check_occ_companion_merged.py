# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OCC companion-merged gate (OMN-15214, ported to omnibase_core per OMN-15222) —
a strict ``CI Summary`` gate.

Why this exists
---------------
On 2026-07-26 an automated "OCC queue hygiene" pass closed five OPEN
onex_change_control evidence companions (#5012-#5016) whose product PRs had
already MERGED, destroying three evidence chains (OMN-15199 / OMN-15200 /
OMN-15203) with no successor. The sweep's trigger state is exactly
"OPEN companion + MERGED product PR".

This gate makes that state unreachable at the merge boundary for this repo:
a product PR's ``CI Summary`` (a required branch-protection context on
omnibase_core ``main``; the 2026-07-25 reconciliation note in
``.github/required-checks.yaml`` records that ``dev`` protection was narrowed
to drop the aggregators — on ``dev`` the umbrella currently binds any
all-checks-green merge flow rather than branch protection) cannot go green
until the OCC evidence cited by the PR's
``Evidence-Source:`` line is DURABLE — i.e. the cited companion PR is MERGED,
or the cited commit SHA is an ancestor of an onex_change_control durable
branch (dev/main). Because the product PR cannot merge before its companion
does, "merged product + open companion" can no longer arise via the merge
path, and a companion-closing sweep has nothing load-bearing to destroy.

Deliberately NOT a new required status check: this job is registered in
:data:`scripts.ci.ci_summary_gate.GATE_JOBS` (completeness anchor — the
umbrella WAITS for it) and :data:`scripts.ci.ci_summary_gate.STRICT_SUCCESS_JOBS`
(a skip/cancel conclusion fails closed) and enforced through the existing
fail-closed ``CI Summary`` umbrella poller. Adding a new top-level
required context that does not report on every PR shape wedges merges
indefinitely (see CLAUDE.md, deploy-gate section); the umbrella pattern has no
such failure mode because its check-run always instantiates.

Verdict model (mirrors ci_summary_gate exit codes)
--------------------------------------------------
* ``PASS`` (0)    — evidence is durable, or the gate does not apply
  (non-PR event; trusted dependency-bot author, mirroring occ-preflight's
  OMN-13762 exemption).
* ``PENDING`` (2) — evidence may still become durable without a new commit:
  Evidence-Source not yet PATCHed onto the body by occ-autobind, companion
  still OPEN (auto-merge in flight), or a transient API error. The runner
  entrypoint polls; at the deadline PENDING converts to FAIL (fail-closed).
* ``FAIL`` (1)    — evidence can never become durable in this state:
  companion CLOSED without merging (the incident state), cited SHA not an
  ancestor of an OCC durable branch (squash-only merges guarantee a
  feature-branch head SHA never becomes one — the OMN-15216 defect), or a
  malformed Evidence-Source value.

The companion-must-merge-first ordering is safe: onex_change_control PRs have
no reverse dependency on product-PR merge state (occ-preflight validates OCC's
own PRs from their in-tree diff), and repo-level auto-merge is enabled there.
The incident's canary lane proved the ordering live: companion OCC#5008 merged
40+ minutes before its product PR.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # fixed argv, no shell, trusted gh binary
import sys
import time
from dataclasses import dataclass

OCC_REPO_DEFAULT = "OmniNode-ai/onex_change_control"

# Branches on which an OCC commit SHA counts as durable evidence.
OCC_DURABLE_BRANCHES: tuple[str, ...] = ("dev", "main")

# Mirrors occ-preflight's OMN-13762 dependency-bot exemption
# (validator_receipt_gate.DEPENDENCY_BOT_AUTHORS): bot-authored dependency
# bumps structurally cannot cite OCC evidence.
DEPENDENCY_BOT_AUTHORS: frozenset[str] = frozenset(
    {
        "dependabot[bot]",
        "app/dependabot",
        "dependabot",
        "renovate[bot]",
        "app/renovate",
        "renovate",
    }
)

# Events on which the gate enforces (mirrors occ-preflight's event scope).
ENFORCED_EVENTS: frozenset[str] = frozenset({"pull_request", "merge_group"})

EVIDENCE_SOURCE_RE = re.compile(
    r"^Evidence-Source:\s+(\S.*)$", re.IGNORECASE | re.MULTILINE
)
# OMN-18069 -- the autobind producer's terminal outcome, posted as a check-run on
# the product PR's own head SHA by
# omnimarket/.../handlers/occ_autobind_outcome.py. The name and the marker
# prefix are a cross-repo contract; changing either is a two-repo change.
AUTOBIND_OUTCOME_CHECK_NAME = "occ-autobind / outcome"
AUTOBIND_OUTCOME_MARKER_PREFIX = "occ-autobind-outcome:"
AUTOBIND_OUTCOME_ERROR = "ERROR"
OCC_PR_REF_RE = re.compile(r"^OCC#(\d+)$", re.IGNORECASE)
HEX_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
MERGE_GROUP_PR_RE = re.compile(r"/pr-(\d+)-")

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_PENDING = 2

_VERDICT_NAMES = {EXIT_PASS: "PASS", EXIT_FAIL: "FAIL", EXIT_PENDING: "PENDING"}


@dataclass(frozen=True)
class Verdict:
    """Terminal or poll-again outcome of a single gate evaluation."""

    code: int  # EXIT_PASS | EXIT_FAIL | EXIT_PENDING
    reason: str

    @property
    def name(self) -> str:
        return _VERDICT_NAMES[self.code]


class GhFetcher:
    """Live GitHub reads via the ``gh`` CLI. Every failure returns ``None``
    so the caller decides between PENDING (retryable) and FAIL (terminal)."""

    def _run(self, argv: list[str]) -> str | None:
        try:
            result = subprocess.run(  # fixed argv, no shell
                argv, capture_output=True, text=True, timeout=60, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"::warning::gh invocation failed: {exc}", file=sys.stderr)
            return None
        if result.returncode != 0:
            print(
                f"::warning::{' '.join(argv[:4])}... exited "
                f"{result.returncode}: {result.stderr.strip()[:300]}",
                file=sys.stderr,
            )
            return None
        return result.stdout

    def pr_view(self, repo: str, number: str, fields: str) -> dict[str, object] | None:
        raw = self._run(
            ["gh", "pr", "view", str(number), "--repo", repo, "--json", fields]
        )
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def check_runs(self, repo: str, head_sha: str) -> list[dict[str, object]] | None:
        """Check-runs on *head_sha*, or ``None`` when the read itself failed.

        ``None`` is deliberately distinct from ``[]``: an empty list is
        evidence that no outcome was posted, a failed read is evidence of
        nothing at all, and this gate must never convert the second into the
        first (rule 16 -- an empty result is not evidence of absence).
        """
        raw = self._run(
            [
                "gh",
                "api",
                f"repos/{repo}/commits/{head_sha}/check-runs?per_page=100",
                "--jq",
                ".check_runs",
            ]
        )
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, list) else None

    def compare_status(self, repo: str, base: str, head_sha: str) -> str | None:
        """``identical``/``behind`` ⇒ ``head_sha`` is an ancestor of ``base``."""
        raw = self._run(
            [
                "gh",
                "api",
                f"repos/{repo}/compare/{base}...{head_sha}",
                "--jq",
                ".status",
            ]
        )
        return raw.strip() if raw is not None else None


def parse_evidence_source(body: str) -> str | None:
    """First ``Evidence-Source:`` value in the PR body, or ``None``."""
    match = EVIDENCE_SOURCE_RE.search(body or "")
    return match.group(1).strip() if match else None


def read_autobind_outcome(
    check_runs: list[dict[str, object]],
) -> tuple[str, str] | None:
    """Return ``(outcome, reason)`` from the newest autobind outcome check-run.

    OMN-18069. The producer writes a machine-readable first line into the
    check-run summary:

    ``occ-autobind-outcome: ERROR repo=... pr=... correlation_id=... reason=...``

    Returns ``None`` when no such check-run is present, which is the ordinary
    case for a PR whose autobind has not reported yet.
    """
    latest: dict[str, object] | None = None
    for run in check_runs:
        if not isinstance(run, dict):
            continue
        if str(run.get("name") or "") != AUTOBIND_OUTCOME_CHECK_NAME:
            continue
        if str(run.get("status") or "") != "completed":
            continue
        if latest is None or str(run.get("completed_at") or "") >= str(
            latest.get("completed_at") or ""
        ):
            latest = run
    if latest is None:
        return None

    output = latest.get("output")
    summary = ""
    if isinstance(output, dict):
        summary = str(output.get("summary") or "")
    for line in summary.splitlines():
        stripped = line.strip()
        if not stripped.startswith(AUTOBIND_OUTCOME_MARKER_PREFIX):
            continue
        payload = stripped[len(AUTOBIND_OUTCOME_MARKER_PREFIX) :].strip()
        if not payload:
            break
        outcome = payload.split(None, 1)[0]
        reason = ""
        marker = "reason="
        if marker in payload:
            reason = payload.split(marker, 1)[1].strip()
        return outcome, reason
    return None


def resolve_pr_number(
    event_name: str, pr_number: str, merge_group_head_ref: str
) -> str:
    """PR number for pull_request or merge_group events ('' if unresolvable)."""
    if pr_number:
        return pr_number
    if event_name == "merge_group" and merge_group_head_ref:
        match = MERGE_GROUP_PR_RE.search(merge_group_head_ref)
        if match:
            return match.group(1)
    return ""


def _terminal_autobind_error(
    fetcher: GhFetcher, repo: str, pr_number: str, head_sha: str
) -> str | None:
    """The producer's ERROR reason for *head_sha*, or ``None``.

    Fail-OPEN by design, and only here: an unreadable check-run list, a missing
    head SHA, or any non-ERROR outcome all return ``None`` and leave the caller
    on its existing PENDING path. This short-circuit may only ever turn a
    would-be timeout into a fast, reasoned failure -- it must never be able to
    fail a PR on its own, because the evidence it reads is written by a
    different repo's runtime and an outage there would otherwise become an
    outage here.
    """
    if not head_sha:
        return None
    check_runs = fetcher.check_runs(repo, head_sha)
    if check_runs is None:
        return None
    parsed = read_autobind_outcome(check_runs)
    if parsed is None:
        return None
    outcome, reason = parsed
    if outcome.upper() != AUTOBIND_OUTCOME_ERROR:
        return None
    return reason or "(no reason recorded)"


def evaluate_once(
    fetcher: GhFetcher,
    *,
    event_name: str,
    repo: str,
    pr_number: str,
    occ_repo: str = OCC_REPO_DEFAULT,
    evidence_source_override: str | None = None,
) -> Verdict:
    """One poll iteration. PENDING means the state may still resolve itself
    (poll again); FAIL means it never can (terminal)."""

    if event_name not in ENFORCED_EVENTS:
        return Verdict(
            EXIT_PASS,
            f"event '{event_name}' is not a merge-gating event; gate not applicable",
        )

    if not pr_number:
        return Verdict(
            EXIT_FAIL,
            "could not resolve a PR number for this run — failing closed",
        )

    if evidence_source_override is None:
        # Live body, never the event payload: occ-autobind PATCHes
        # Evidence-Source onto the body AFTER the triggering event fired.
        pr_data = fetcher.pr_view(repo, pr_number, "body,author,headRefOid")
        if pr_data is None:
            return Verdict(
                EXIT_PENDING, f"could not fetch {repo}#{pr_number} (retryable)"
            )

        author_raw = pr_data.get("author")
        author = ""
        if isinstance(author_raw, dict):
            author = str(author_raw.get("login") or "")
        if author in DEPENDENCY_BOT_AUTHORS:
            return Verdict(
                EXIT_PASS,
                f"trusted dependency-bot author '{author}' — occ-preflight OMN-13762 "
                "exemption mirrored; no OCC evidence applicable",
            )

        head_sha = str(pr_data.get("headRefOid") or "")

        evidence_source = parse_evidence_source(str(pr_data.get("body") or ""))
    else:
        evidence_source = evidence_source_override
        head_sha = ""

    if not evidence_source:
        # OMN-18069: before deciding this is "still in flight", ask the producer.
        # On 2026-09-09 the autobind effect consumed 37 commands and minted
        # nothing; this gate spent its full 1500-second deadline on each of them
        # and then reported only that a deadline had passed -- never the reason,
        # which the runtime already knew and had already typed. A terminal ERROR
        # outcome on the head SHA means the companion is not coming, so waiting
        # is not merely wasteful, it is wrong.
        outcome = _terminal_autobind_error(fetcher, repo, pr_number, head_sha)
        if outcome is not None:
            return Verdict(
                EXIT_FAIL,
                f"{repo}#{pr_number} has no 'Evidence-Source:' line and the "
                f"occ-autobind producer reported {AUTOBIND_OUTCOME_ERROR} for this "
                f"head: {outcome}. The OCC companion will NOT appear on its own -- "
                "repair the reported fault and re-run the publisher, or hand-author "
                "the companion (OMN-18069).",
            )
        return Verdict(
            EXIT_PENDING,
            f"{repo}#{pr_number} body has no 'Evidence-Source:' line yet "
            "(occ-autobind mint may still be in flight)",
        )

    occ_ref = OCC_PR_REF_RE.match(evidence_source)
    if occ_ref:
        occ_pr = occ_ref.group(1)
        occ_data = fetcher.pr_view(occ_repo, occ_pr, "state,mergeCommit")
        if occ_data is None:
            return Verdict(
                EXIT_PENDING,
                f"could not fetch companion {occ_repo}#{occ_pr} (retryable)",
            )
        state = str(occ_data.get("state") or "").upper()
        if state == "MERGED":
            merge_commit = occ_data.get("mergeCommit")
            merge_oid = ""
            if isinstance(merge_commit, dict):
                merge_oid = str(merge_commit.get("oid") or "")
            return Verdict(
                EXIT_PASS,
                f"companion OCC#{occ_pr} is MERGED (merge commit {merge_oid or 'unknown'}) "
                "— evidence is durable",
            )
        if state == "OPEN":
            return Verdict(
                EXIT_PENDING,
                f"companion OCC#{occ_pr} is still OPEN — the companion must MERGE "
                "before this product PR may merge (OMN-15214). Land the companion "
                "on onex_change_control, then re-run this job.",
            )
        # CLOSED without merging: the exact state the 2026-07-26 hygiene sweep
        # minted — the evidence was destroyed. Never poll; fail loudly.
        return Verdict(
            EXIT_FAIL,
            f"companion OCC#{occ_pr} is {state or 'UNRESOLVED'} without merging — "
            "the cited evidence no longer exists. Re-cut the companion (bind it to "
            "this PR) and update Evidence-Source before merging.",
        )

    if HEX_SHA_RE.match(evidence_source.lower()):
        sha = evidence_source.lower()
        saw_api_error = False
        for branch in OCC_DURABLE_BRANCHES:
            status = fetcher.compare_status(occ_repo, branch, sha)
            if status is None:
                saw_api_error = True
                continue
            if status in ("identical", "behind"):
                return Verdict(
                    EXIT_PASS,
                    f"Evidence-Source SHA {sha} is an ancestor of {occ_repo}@{branch} "
                    "— evidence is durable",
                )
        if saw_api_error:
            return Verdict(
                EXIT_PENDING,
                f"could not resolve Evidence-Source SHA {sha} against "
                f"{occ_repo} durable branches (retryable)",
            )
        # onex_change_control is squash-only: a feature-branch head SHA can
        # NEVER become an ancestor of dev/main, so this is terminal — it is the
        # strandable pre-merge pin OMN-15216 describes.
        return Verdict(
            EXIT_FAIL,
            f"Evidence-Source SHA {sha} is not an ancestor of any durable "
            f"{occ_repo} branch {OCC_DURABLE_BRANCHES} — cite 'OCC#<pr>' (which "
            "must be MERGED) or a merged OCC commit SHA, never a feature-branch head.",
        )

    return Verdict(
        EXIT_FAIL,
        f"Evidence-Source value '{evidence_source}' is neither 'OCC#<number>' nor a "
        "hex commit SHA — fix the PR body.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GH_REPO", ""))
    parser.add_argument("--pr-number", default=os.environ.get("PR_NUMBER", ""))
    parser.add_argument(
        "--event-name", default=os.environ.get("GITHUB_EVENT_NAME", "pull_request")
    )
    parser.add_argument(
        "--merge-group-head-ref", default=os.environ.get("MERGE_GROUP_HEAD_REF", "")
    )
    parser.add_argument(
        "--occ-repo", default=os.environ.get("OCC_REPO", OCC_REPO_DEFAULT)
    )
    parser.add_argument(
        "--evidence-source",
        default=None,
        help="Override: evaluate this Evidence-Source value directly instead of "
        "reading the PR body (diagnostics / dry-run).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single evaluation, no polling; exits 0/1/2 (PASS/FAIL/PENDING).",
    )
    parser.add_argument(
        "--deadline-seconds",
        type=int,
        default=int(os.environ.get("DEADLINE_SECONDS", "1500")),
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=int(os.environ.get("POLL_INTERVAL_SECONDS", "30")),
    )
    args = parser.parse_args(argv)

    pr_number = resolve_pr_number(
        args.event_name, args.pr_number, args.merge_group_head_ref
    )
    fetcher = GhFetcher()
    deadline = time.monotonic() + args.deadline_seconds

    while True:
        verdict = evaluate_once(
            fetcher,
            event_name=args.event_name,
            repo=args.repo,
            pr_number=pr_number,
            occ_repo=args.occ_repo,
            evidence_source_override=args.evidence_source,
        )
        print(f"occ-companion-merged gate: {verdict.name} — {verdict.reason}")

        if verdict.code != EXIT_PENDING or args.once:
            if verdict.code == EXIT_FAIL:
                print(f"::error::{verdict.reason}")
            return verdict.code

        if time.monotonic() >= deadline:
            print(
                f"::error::occ-companion-merged gate: poll deadline "
                f"({args.deadline_seconds}s) reached while still PENDING — failing "
                f"closed. Last state: {verdict.reason}"
            )
            return EXIT_FAIL

        time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
