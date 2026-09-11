# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Resolve the immutable OCC evidence data checkout for contract compliance."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_OCC_REPO = "OmniNode-ai/onex_change_control"
_OCC_PR_RE = re.compile(r"^OCC#(\d+)$", re.IGNORECASE)
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
_EVIDENCE_SOURCE_RE = re.compile(
    r"^Evidence-Source: ([^\r\n]+)$", re.IGNORECASE | re.MULTILINE
)
_MERGE_GROUP_PR_RE = re.compile(r"/pr-(\d+)-")


def _gh(*args: str) -> str:
    """Run a fixed ``gh`` argv and fail with its diagnostic."""
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False, timeout=60
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise RuntimeError(f"gh {' '.join(args[:4])} failed: {detail}")
    return result.stdout


def _json_gh(*args: str) -> dict[str, object]:
    raw = _gh(*args)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("gh returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("gh returned a non-object JSON response")
    return payload


def _resolve_pr_number(
    *,
    event_name: str,
    pr_number: str,
    merge_group_head_ref: str,
    repo: str,
    commit_sha: str,
) -> str:
    if pr_number:
        return pr_number
    if event_name == "push":
        resolved = _gh(
            "api",
            f"repos/{repo}/commits/{commit_sha}/pulls",
            "--jq",
            "[.[] | select(.merged_at != null)] | sort_by(.merged_at) | last | .number // empty",
        ).strip()
        if resolved:
            return resolved
    elif event_name == "merge_group":
        match = _MERGE_GROUP_PR_RE.search(merge_group_head_ref)
        if match:
            return match.group(1)
    raise RuntimeError(f"No PR number could be resolved for event={event_name}")


def _evidence_source(body: str) -> str:
    match = _EVIDENCE_SOURCE_RE.search(body)
    if match is None:
        raise RuntimeError("PR body is missing required 'Evidence-Source:' line")
    source = match.group(1).strip()
    if not source:
        raise RuntimeError("PR body has an empty Evidence-Source value")
    return source


def _resolve_occ_sha(source: str) -> str:
    if pr_match := _OCC_PR_RE.fullmatch(source):
        occ_pr = pr_match.group(1)
        payload = _json_gh(
            "pr",
            "view",
            occ_pr,
            "--repo",
            _OCC_REPO,
            "--json",
            "state,headRefOid,mergeCommit",
        )
        state = payload.get("state")
        if state == "MERGED":
            merge_commit = payload.get("mergeCommit")
            if isinstance(merge_commit, dict):
                sha = merge_commit.get("oid")
            else:
                sha = None
        elif state == "OPEN":
            sha = payload.get("headRefOid")
        else:
            raise RuntimeError(
                f"OCC PR #{occ_pr} is {state!r}; Evidence-Source OCC# references require OPEN or MERGED"
            )
        if not isinstance(sha, str) or not sha:
            raise RuntimeError(
                f"OCC PR #{occ_pr} did not resolve to an immutable commit SHA"
            )
        return sha

    if not _SHA_RE.fullmatch(source):
        raise RuntimeError(
            f"Evidence-Source value {source!r} is not OCC#<number> or a hexadecimal SHA"
        )

    status = _gh(
        "api", f"repos/{_OCC_REPO}/compare/HEAD...{source}", "--jq", ".status"
    ).strip()
    if status in {"behind", "identical"}:
        sha = _gh("api", f"repos/{_OCC_REPO}/commits/{source}", "--jq", ".sha").strip()
        if sha:
            return sha
        raise RuntimeError("Evidence-Source SHA could not be canonicalized")

    matched_head = _gh(
        "pr",
        "list",
        "--repo",
        _OCC_REPO,
        "--state",
        "open",
        "--json",
        "headRefOid",
        "--jq",
        f'.[] | select(.headRefOid | startswith("{source}")) | .headRefOid',
    ).splitlines()
    if matched_head and matched_head[0].strip():
        return matched_head[0].strip()
    raise RuntimeError(
        "Evidence-Source SHA is neither an OCC durable-branch ancestor nor an open OCC PR head"
    )


def resolve(args: argparse.Namespace) -> tuple[str, str]:
    """Return the PR number and immutable OCC evidence SHA, or raise."""
    pr_number = _resolve_pr_number(
        event_name=args.event_name,
        pr_number=args.pr_number,
        merge_group_head_ref=args.merge_group_head_ref,
        repo=args.repo,
        commit_sha=args.commit_sha,
    )
    pr = _json_gh("pr", "view", pr_number, "--repo", args.repo, "--json", "body")
    body = pr.get("body")
    if not isinstance(body, str):
        raise RuntimeError(f"PR #{pr_number} did not return a string body")
    return pr_number, _resolve_occ_sha(_evidence_source(body))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--merge-group-head-ref", default="")
    args = parser.parse_args()
    try:
        pr_number, occ_sha = resolve(args)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        sys.stderr.write(
            f"::error::Contract Compliance evidence resolution failed: {exc}\n"
        )
        return 1

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write(f"pr_number={pr_number}\nocc_sha={occ_sha}\n")
    else:
        sys.stdout.write(f"pr_number={pr_number}\nocc_sha={occ_sha}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
