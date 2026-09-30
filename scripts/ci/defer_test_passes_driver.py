# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Run the pinned OCC compliance runner with ``test_passes`` deferred (OMN-18157)
and the item loop scoped to this PR's own dod_evidence items.

The pinned runner judges a ``test_passes`` item with ``gh pr checks`` and treats
every check that is not SUCCESS, SKIPPED or NEUTRAL as a failure. Inside the
Contract Compliance Check job that set always includes the job itself, still
running, so such an item can never pass there. This driver runs the pinned
runner's own ``main()`` unchanged except for that one check type: each
``test_passes`` item is reported WARN and written to ``--deferred-record``, and
CI Summary evaluates the record once every other check has a verdict
(``scripts/ci/deferred_test_passes_gate.py``).

PR scope (OMN-20130): a ticket contract is shared by every repo's PRs for that ticket, and
the pinned runner executes every item of it in this product checkout. An item
whose generated id binds it to another PR is therefore run against a tree it
says nothing about; the change-control admissibility validator minted for an
omnibase_infra PR (``uv run pytest tests/test_evidence_admissibility.py -q``, a
file only onex_change_control has) exits 5 here and BLOCKs every omnibase_core
PR citing the same ticket. :func:`install_pr_scope` reports such an item WARN
without executing it. Items bound to this PR and items bound to no PR run
unchanged, and supersession is still decided over the whole contract.

Repo scope (OMN-19384): a check whose ``cwd`` is ``${OMNI_HOME}/<repo>``
declares the repo it runs in. The autobind producer mints the change-control
admissibility validator (``uv run pytest tests/test_evidence_admissibility.py
-q``, a file only onex_change_control has) with
``cwd: ${OMNI_HOME}/onex_change_control``, and the behaviour-proof item with its
own product repo. The pinned runner ignores ``cwd`` and would run such an item
in this checkout, where it exits 4 or 5 and BLOCKs. :func:`declared_repo_outside`
reports an item whose every check declares one other repo as not this repo's
item: it is neither run nor counted, and the log says so. An item that declares
no repo runs exactly as before, so a test file missing from this repo still
fails here.

It runs inside the pinned checker's environment (``uv run`` from that checkout),
so every other check type executes exactly as the pinned runner executes it.

Usage::

    python defer_test_passes_driver.py --deferred-record <path> -- <runner args>
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path
from types import ModuleType

_CHECKER_MODULE = "onex_change_control.scripts.contract_compliance_check"
_DEFERRED_DETAIL = (
    "DEFERRED to CI Summary (OMN-18157): judged there once every other check "
    "on the PR has a verdict, because in this job the check set includes this "
    "job itself, still running."
)


def install_deferral(checker: ModuleType, deferred: list[dict[str, object]]) -> None:
    """Replace the pinned runner's ``test_passes`` entry with a recording deferral."""
    runners = getattr(checker, "_CHECK_RUNNERS", None)
    if not isinstance(runners, dict) or "test_passes" not in runners:
        raise RuntimeError(
            "pinned checker has no _CHECK_RUNNERS['test_passes'] entry to defer"
        )
    warn = getattr(checker, "_RESULT_WARN", None)
    if not isinstance(warn, str):
        raise RuntimeError("pinned checker has no _RESULT_WARN result constant")

    def _defer_test_passes(
        check_value: object, _workspace: Path, pr_number: int, repo: str
    ) -> tuple[str, str]:
        deferred.append(
            {"pr_number": pr_number, "repo": repo, "check_value": str(check_value)}
        )
        return warn, _DEFERRED_DETAIL

    runners["test_passes"] = _defer_test_passes


# A generated evidence id binds its item to one pull request with ``-pr-<n>``:
# ``dod-<org>-<repo>-pr-<n>[-ci]`` names the repo too, while
# ``dod-occ-<check>-pr-<n>`` and ``occ-self-bind-pr-<n>`` name only the number.
_PR_BINDING = re.compile(r"-pr-(?P<number>\d+)(?=-|$)")


def pr_binding_outside(item_id: object, *, repo: str, pr_number: int) -> str | None:
    """Name the other PR an evidence id binds its item to, or None.

    None means the item is this PR's own (same repo and number, or a number
    with no repo named that equals this PR's) or is bound to no PR at all, so
    it must run. A number that differs from this PR's, or a repo in the id that
    differs from ``repo``, makes the item another PR's evidence.
    """
    if not isinstance(item_id, str):
        return None
    match = _PR_BINDING.search(item_id)
    if match is None:
        return None
    number = int(match["number"])
    org = repo.partition("/")[0]
    head = item_id[: match.start()]
    repo_prefix = f"dod-{org}-"
    if head.startswith(repo_prefix) and len(head) > len(repo_prefix):
        bound_repo = f"{org}/{head[len(repo_prefix) :]}"
        if bound_repo != repo or number != pr_number:
            return f"{bound_repo}#{number}"
        return None
    if number != pr_number:
        return f"PR #{number}"
    return None


# A check's ``cwd`` of ``${OMNI_HOME}/<repo>[/<path>]`` names the repo checkout
# it runs in (``ModelDodCheck.cwd``; the producer's ``behavior_proof_cwd`` and
# ``ADMISSIBILITY_VALIDATOR_CWD``).
_DECLARED_REPO_CWD = re.compile(r"^\$\{OMNI_HOME\}/(?P<repo>[^/$]+)(?:/|$)")


def declared_repo_outside(item: object, *, repo: str) -> str | None:
    """Name the other repo an item declares it runs in, or None.

    Every check must declare ``cwd: ${OMNI_HOME}/<repo>`` and all must name the
    same repo, and that repo must differ from this one (``owner/name``). An item
    with any check that declares no repo, or that names this repo, returns None
    and runs.
    """
    if not isinstance(item, dict):
        return None
    checks = item.get("checks")
    if not isinstance(checks, list) or not checks:
        return None
    declared: set[str] = set()
    for check in checks:
        cwd = check.get("cwd") if isinstance(check, dict) else None
        match = _DECLARED_REPO_CWD.match(cwd.strip()) if isinstance(cwd, str) else None
        if match is None:
            return None
        declared.add(match["repo"])
    if len(declared) != 1:
        return None
    owner = declared.pop()
    if owner == repo.rpartition("/")[2]:
        return None
    return owner


def install_pr_scope(checker: ModuleType) -> None:
    """Wrap the pinned runner's item loop so it executes only this PR's items."""
    run_dod_checks = getattr(checker, "_run_dod_checks", None)
    superseded_ids = getattr(checker, "_superseded_dod_ids", None)
    warn = getattr(checker, "_RESULT_WARN", None)
    if not callable(run_dod_checks) or not callable(superseded_ids):
        raise RuntimeError(
            "pinned checker has no _run_dod_checks/_superseded_dod_ids to scope"
        )
    if not isinstance(warn, str):
        raise RuntimeError("pinned checker has no _RESULT_WARN result constant")

    def _scoped_run_dod_checks(
        dod_evidence: list[object], workspace: Path, context: object
    ) -> list[tuple[str, str, str, str]]:
        repo = str(getattr(context, "repo", ""))
        pr_number = int(getattr(context, "pr_number", 0))
        superseded_in_contract = superseded_ids(dod_evidence)
        results: list[tuple[str, str, str, str]] = []
        in_scope: list[object] = []
        for item in dod_evidence:
            item_id = item.get("id") if isinstance(item, dict) else None
            other = pr_binding_outside(item_id, repo=repo, pr_number=pr_number)
            owner = declared_repo_outside(item, repo=repo)
            if other is None and owner is not None:
                print(  # noqa: T201 - CI log line
                    f"\n[DoD {item_id}]\n  [~] repo_scope: NOT THIS REPO'S ITEM -- "
                    f"its checks declare cwd ${{OMNI_HOME}}/{owner}, not {repo}; "
                    f"{owner}'s own compliance run executes it. Not run and not "
                    "counted here.",
                    flush=True,
                )
                continue
            if other is None:
                in_scope.append(item)
                continue
            detail = (
                f"NOT RUN HERE -- bound to {other}, not {repo}#{pr_number}; that "
                "PR's own gate evaluates it."
            )
            print(f"\n[DoD {item_id}]\n  [~] pr_scope: {detail}", flush=True)  # noqa: T201 - CI log line
            results.append((str(item_id), "pr_scope", warn, detail))
        still_superseded = superseded_ids(in_scope)
        kept: list[object] = []
        for item in in_scope:
            item_id = item.get("id") if isinstance(item, dict) else None
            if item_id in superseded_in_contract and item_id not in still_superseded:
                detail = (
                    "SUPERSEDED -- a later append-only dod_evidence item bound to "
                    f"another PR declares evidence_artifact='supersedes_dod_evidence:"
                    f"{item_id}'; not re-executed."
                )
                print(  # noqa: T201 - CI log line
                    f"\n[DoD {item_id}]\n  [~] superseded: {detail}", flush=True
                )
                results.append((str(item_id), "superseded", warn, detail))
                continue
            kept.append(item)
        results.extend(run_dod_checks(kept, workspace, context))
        return results

    checker._run_dod_checks = _scoped_run_dod_checks  # type: ignore[attr-defined]


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if "--" not in raw:
        sys.stderr.write("::error::usage: --deferred-record <path> -- <runner args>\n")
        return 1
    split = raw.index("--")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deferred-record", required=True, type=Path)
    args = parser.parse_args(raw[:split])

    # This file lives in the product's scripts/ci; keep that directory from
    # shadowing any module the pinned checker imports.
    own_dir = str(Path(__file__).resolve().parent)
    sys.path[:] = [entry for entry in sys.path if entry != own_dir]

    deferred: list[dict[str, object]] = []
    try:
        checker = importlib.import_module(_CHECKER_MODULE)
        install_deferral(checker, deferred)
        install_pr_scope(checker)
    except (ImportError, RuntimeError) as exc:
        sys.stderr.write(f"::error::Cannot wrap the pinned compliance runner: {exc}\n")
        return 1

    sys.argv = ["run_contract_compliance_check.py", *raw[split + 1 :]]
    code = checker.main()
    args.deferred_record.parent.mkdir(parents=True, exist_ok=True)
    args.deferred_record.write_text(
        json.dumps({"schema": 1, "deferred": deferred}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(  # noqa: T201 - CI log line
        f"[INFO] {len(deferred)} test_passes item(s) deferred to CI Summary "
        f"(record: {args.deferred_record})",
        flush=True,
    )
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
