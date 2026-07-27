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
        pr_data = fetcher.pr_view(repo, pr_number, "body,author")
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

        evidence_source = parse_evidence_source(str(pr_data.get("body") or ""))
    else:
        evidence_source = evidence_source_override

    if not evidence_source:
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
