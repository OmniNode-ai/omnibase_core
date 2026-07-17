#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed CI reason-graph emitter (OMN-14705 / OMN-14644 Phase 3, CI-01).

Root cause this module addresses
--------------------------------
When one prerequisite (`occ-preflight`) fails, dozens of `needs: occ-preflight`
product and governance jobs skip or fail, and the projection shows *N failed
checks* instead of *one root cause*. This emitter collapses a run into exactly
one dominant ``ModelCiReasonGraph`` root plus ``BLOCKED_UPSTREAM`` dependents
that all point back at the root, so a 30-check cascade projects as **one**
blocked candidate — not thirty.

It is the graph layer built *around* the deterministic, unit-tested product
classifier (`scripts/ci/product_readiness.py`); it reuses that classifier for
the product dimension rather than reimplementing it (the WS1 classifier stays
byte-identical). See design ``docs/plans/2026-07-17-product-first-ci-decouple-design.md`` §2.

Design invariants (mirror ``scripts/ci/product_readiness.py``)
--------------------------------------------------------------
- **No network I/O. Stdlib only.** Runs under a bare ``setup-python`` step; the
  workflow resolves sibling conclusions and passes them in. This module only
  classifies and hashes.
- **Single-rooted + deterministic.** When several signals are present the
  dominant root is chosen by a fixed precedence, so replay yields an identical
  graph. The root carries a content-addressed receipt id
  ``root_receipt_id = sha256(head_sha || root_kind || primary_signal)[:16]``.
- **Fail closed.** An unconfirmable product subcheck (skipped/cancelled/absent)
  never masquerades as a pass; it becomes a ``RUNNER_INFRA`` root (product
  dimension) or a ``BLOCKED_UPSTREAM`` dependent under a non-product root.
- **Product defects are OCC-independent (the #1450/#1451 fix).**
  ``EVIDENCE_MISSING`` fires ONLY when OCC eligibility is observed red/absent
  *and* no product check independently failed. A real product defect therefore
  surfaces as ``PRODUCT_FAILED`` regardless of OCC state — the two dimensions no
  longer collapse into one another.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any

# Import the WS1 product classifier without reimplementing it. Works both when
# run as a bare script (`python scripts/ci/product_reason_graph.py`, where the
# script's own directory is on sys.path[0]) and when imported as a package
# (`scripts.ci.product_reason_graph`, as the pytest suite does).
try:  # pragma: no cover - import shim, both branches exercised across contexts
    from scripts.ci.product_readiness import (
        CHANGE_DETECTION_FAILED,
        COVERAGE_FAILED,
        LINT_FAILED,
        PRODUCT_GREEN,
        PRODUCT_INFRA,
        TEST_FAILED,
        TYPE_FAILED,
        EnumSubcheckOutcome,
        ProductFacts,
        categorize_conclusion,
        classify,
    )
except ImportError:  # pragma: no cover - script-run fallback
    from product_readiness import (  # type: ignore[no-redef, import-not-found]
        CHANGE_DETECTION_FAILED,
        COVERAGE_FAILED,
        LINT_FAILED,
        PRODUCT_GREEN,
        PRODUCT_INFRA,
        TEST_FAILED,
        TYPE_FAILED,
        EnumSubcheckOutcome,
        ProductFacts,
        categorize_conclusion,
        classify,
    )

SCHEMA_VERSION = "ci-reason-graph/v1"

# --- Root kinds (the six typed causes) -------------------------------------
GITHUB_API_OUTAGE = "GITHUB_API_OUTAGE"
RUNNER_INFRA = "RUNNER_INFRA"
POLICY_HELD = "POLICY_HELD"
EVIDENCE_MISSING = "EVIDENCE_MISSING"
PRODUCT_FAILED = "PRODUCT_FAILED"
DEPLOY_TRIGGER_FAILED = "DEPLOY_TRIGGER_FAILED"

# Fixed precedence (highest wins). Infra/API failures invalidate the
# observability of everything below them; an intentional hold outranks absent
# evidence; a product defect precedes any deploy attempt.
ROOT_PRECEDENCE: tuple[str, ...] = (
    GITHUB_API_OUTAGE,
    RUNNER_INFRA,
    POLICY_HELD,
    EVIDENCE_MISSING,
    PRODUCT_FAILED,
    DEPLOY_TRIGGER_FAILED,
)

# --- Node statuses ---------------------------------------------------------
STATUS_PASS = "PASS"
STATUS_FAILED = "FAILED"
STATUS_BLOCKED_UPSTREAM = "BLOCKED_UPSTREAM"
STATUS_INFRA = "INFRA"
STATUS_ABSENT = "ABSENT"

# Product-outcome code -> the subcheck name that reported the defect.
_OUTCOME_TO_CHECK: dict[str, str] = {
    CHANGE_DETECTION_FAILED: "change_detection",
    LINT_FAILED: "lint",
    TYPE_FAILED: "typecheck",
    TEST_FAILED: "tests",
    COVERAGE_FAILED: "coverage",
}

_PRODUCT_SUBCHECKS: tuple[str, ...] = (
    "change_detection",
    "lint",
    "typecheck",
    "tests",
    "coverage",
)

# Raw GitHub-API signals that count as an outage.
_API_OUTAGE_SIGNALS = frozenset(
    {"5xx", "ratelimit", "rate_limit", "graphql_down", "503", "502", "500"}
)
# OCC eligibility conclusions that count as observed red/absent evidence.
# NOTE: an *empty* string means "not part of this graph's inputs" (the product
# shadow deliberately does not consume OCC) and never fires EVIDENCE_MISSING.
_OCC_RED_SIGNALS = frozenset(
    {"failure", "action_required", "absent", "missing", "none", "null"}
)
_DEPLOY_FAIL_SIGNALS = frozenset({"failure", "action_required", "error"})


def root_receipt_id(head_sha: str, root_kind: str, primary_signal: str) -> str:
    """Content-addressed, deterministic root receipt id.

    ``sha256(head_sha || root_kind || primary_signal)[:16]`` (first 16 hex
    chars). Fields are joined with an unambiguous separator so distinct triples
    cannot collide by concatenation. Replay against the identical head + facts
    yields an identical id (fixture ``replay-determinism``).
    """
    payload = f"{head_sha}||{root_kind}||{primary_signal}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _norm(value: Any) -> str:
    return (str(value) if value is not None else "").strip().lower()


def build_reason_graph(facts: dict[str, Any]) -> dict[str, Any]:
    """Collapse a run's facts into exactly one typed root + dependents.

    ``facts`` keys:
      - ``head_sha``: exact head SHA the graph is content-addressed to.
      - ``subchecks``: dict of product subcheck conclusions (change_detection,
        lint, typecheck, tests, coverage) — the product dimension.
      - ``occ_eligibility`` (optional): observed ``occ-preflight / eligibility``
        conclusion. Empty => not consumed (never fires EVIDENCE_MISSING).
      - ``runner_signal`` / ``gh_api`` / ``policy`` / ``deploy_trigger``
        (optional): non-product signals for full-fleet reuse.
    """
    head_sha = str(facts.get("head_sha", "") or "")
    subchecks_raw: dict[str, Any] = dict(facts.get("subchecks", {}) or {})

    # Product dimension via the canonical WS1 classifier (not reimplemented).
    product = classify(ProductFacts.from_dict(subchecks_raw))
    product_outcome = product.outcome
    freeze_eligible = product.freeze_eligible
    affirmative_product_fail = product_outcome in _OUTCOME_TO_CHECK

    # Coarse per-subcheck categories for node rendering.
    subcheck_cat: dict[str, EnumSubcheckOutcome] = {
        name: categorize_conclusion(subchecks_raw.get(name))
        for name in _PRODUCT_SUBCHECKS
    }

    occ = _norm(facts.get("occ_eligibility"))
    runner = _norm(facts.get("runner_signal"))
    gh_api = _norm(facts.get("gh_api"))
    policy = _norm(facts.get("policy"))
    deploy = _norm(facts.get("deploy_trigger"))

    # --- Candidate roots (only those whose firing condition holds) ---------
    candidates: dict[str, str] = {}

    if gh_api in _API_OUTAGE_SIGNALS:
        candidates[GITHUB_API_OUTAGE] = f"gh_api={gh_api}"

    occ_red = occ in _OCC_RED_SIGNALS
    if runner:
        candidates[RUNNER_INFRA] = f"runner={runner}"
    elif product_outcome == PRODUCT_INFRA and not occ_red:
        # An unconfirmable product subcheck (skipped/cancelled/absent) with NO
        # observed OCC-red explanation is a product-dimension infra fault, not a
        # pass. When OCC *is* observed red, those same skips are downstream of
        # the OCC root and are attributed to EVIDENCE_MISSING instead (below),
        # so a needs:occ-preflight cascade collapses to ONE root — not N.
        infra_names = ",".join(
            name
            for name in _PRODUCT_SUBCHECKS
            if subcheck_cat[name]
            in (EnumSubcheckOutcome.INFRA, EnumSubcheckOutcome.ABSENT)
        )
        candidates[RUNNER_INFRA] = f"product_infra:{infra_names}"

    if policy:
        candidates[POLICY_HELD] = f"policy={policy}"

    # EVIDENCE_MISSING fires ONLY when OCC is observed red/absent AND no product
    # check independently failed (the OCC-independence property).
    if occ_red and not affirmative_product_fail:
        candidates[EVIDENCE_MISSING] = f"occ_eligibility={occ or 'absent'}"

    if affirmative_product_fail:
        check = _OUTCOME_TO_CHECK[product_outcome]
        candidates[PRODUCT_FAILED] = f"{check}=failure"

    if deploy in _DEPLOY_FAIL_SIGNALS:
        candidates[DEPLOY_TRIGGER_FAILED] = f"deploy_trigger={deploy}"

    # --- Single-rooting by fixed precedence --------------------------------
    root_kind: str | None = None
    primary_signal = ""
    for kind in ROOT_PRECEDENCE:
        if kind in candidates:
            root_kind = kind
            primary_signal = candidates[kind]
            break

    root: dict[str, Any] | None = None
    receipt_digest: str | None = None
    if root_kind is not None:
        receipt_digest = root_receipt_id(head_sha, root_kind, primary_signal)
        root = {
            "kind": root_kind,
            "primary_signal": primary_signal,
            "root_receipt_id": receipt_digest,
        }

    # --- Nodes -------------------------------------------------------------
    reporter_check = (
        _OUTCOME_TO_CHECK.get(product_outcome) if root_kind == PRODUCT_FAILED else None
    )
    nodes: list[dict[str, Any]] = []

    for name in _PRODUCT_SUBCHECKS:
        cat = subcheck_cat[name]
        node: dict[str, Any] = {"name": name}
        if name == reporter_check:
            # This subcheck IS the root cause (independent defect).
            node["status"] = STATUS_FAILED
            node["is_root"] = True
            node["root_receipt_id"] = receipt_digest
        elif cat is EnumSubcheckOutcome.PASS:
            # Reported independently — not blocked, not counted as a failure.
            node["status"] = STATUS_PASS
            node["is_root"] = False
            node["root_receipt_id"] = None
        elif cat is EnumSubcheckOutcome.FAIL:
            # A product FAIL that is NOT the elected root only happens under a
            # higher-precedence non-product root (infra/API/policy invalidated
            # its observability): it is a dependent, never independently counted.
            node["status"] = STATUS_BLOCKED_UPSTREAM
            node["is_root"] = False
            node["root_receipt_id"] = receipt_digest
        # INFRA / ABSENT: prevented from producing an independent result.
        elif root_kind is None:
            node["status"] = (
                STATUS_INFRA if cat is EnumSubcheckOutcome.INFRA else STATUS_ABSENT
            )
            node["is_root"] = False
            node["root_receipt_id"] = None
        else:
            node["status"] = STATUS_BLOCKED_UPSTREAM
            node["is_root"] = False
            node["root_receipt_id"] = receipt_digest
        nodes.append(node)

    # For a non-product root, add a synthetic reporter node naming the cause.
    if root_kind is not None and root_kind != PRODUCT_FAILED:
        nodes.insert(
            0,
            {
                "name": _SYNTHETIC_REPORTER[root_kind],
                "status": STATUS_FAILED,
                "is_root": True,
                "root_receipt_id": receipt_digest,
            },
        )

    dependents = [n for n in nodes if n["status"] == STATUS_BLOCKED_UPSTREAM]
    ready = root_kind is None and product_outcome == PRODUCT_GREEN

    return {
        "schema_version": SCHEMA_VERSION,
        "head_sha": head_sha,
        "root": root,
        "nodes": nodes,
        # count of distinct roots — the projection contract number (typically 1).
        "blocked_candidate_count": 1 if root_kind is not None else 0,
        "blocked_upstream_count": len(dependents),
        "product_outcome": product_outcome,
        "freeze_eligible": freeze_eligible,
        "ready": ready,
    }


_SYNTHETIC_REPORTER: dict[str, str] = {
    GITHUB_API_OUTAGE: "github-api",
    RUNNER_INFRA: "runner",
    POLICY_HELD: "policy",
    EVIDENCE_MISSING: "occ-preflight",
    DEPLOY_TRIGGER_FAILED: "deploy-trigger",
}


def _render_summary(graph: dict[str, Any]) -> str:
    root = graph["root"]
    lines = ["## CI Reason Graph (report-only)", ""]
    if root is None:
        lines.append(
            f"> READY — product dimension `{graph['product_outcome']}`, "
            f"freeze_eligible=`{str(graph['freeze_eligible']).lower()}`. "
            "Single-node graph, no BLOCKED_UPSTREAM dependents."
        )
    else:
        lines += [
            f"> ROOT `{root['kind']}` — signal `{root['primary_signal']}` — "
            f"receipt `{root['root_receipt_id']}`",
            "",
            f"blocked_candidate_count = **{graph['blocked_candidate_count']}** "
            f"(BLOCKED_UPSTREAM dependents: {graph['blocked_upstream_count']})",
        ]
    lines += ["", "| node | status | root_receipt_id |", "| --- | --- | --- |"]
    for node in graph["nodes"]:
        rid = node.get("root_receipt_id") or "-"
        lines.append(f"| `{node['name']}` | `{node['status']}` | `{rid}` |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Typed CI reason-graph emitter (OMN-14705 / OMN-14644 Phase 3)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("graph", help="Emit the reason graph as JSON")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--facts-json", help="JSON object of run facts")
    src.add_argument("--facts-file", help="Path to a file containing the facts JSON")
    p.add_argument(
        "--summary",
        action="store_true",
        help="Also print a Markdown summary block to stderr.",
    )

    args = parser.parse_args(argv)

    if args.command == "graph":
        if args.facts_file:
            with open(args.facts_file, encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = json.loads(args.facts_json)
        if not isinstance(data, dict):
            print("facts JSON must be an object", file=sys.stderr)
            return 2
        graph = build_reason_graph(data)
        print(json.dumps(graph, sort_keys=True))
        if args.summary:
            print(_render_summary(graph), file=sys.stderr)
        # Report-only: this surface never fails the check.
        return 0

    parser.error(f"unknown command: {args.command}")  # NoReturn — exits


if __name__ == "__main__":
    raise SystemExit(main())
