# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RSD provenance-stamp fail-closed GATE for omnibase_core (OMN-15011).

The missing enforcement surface identified by the OMN-15011 audit: the OMN-14355
canonical-handler-shape ratchet (``scripts/ci/canonical_handler_shape.py``) proves
a node's *shape* but is authorship-agnostic by design — a brand-new node born
already shape-canonical requires proof of nothing about *how* it came to exist.
This gate closes that hole for authorship: every node under this package's node
tree must carry a machine-checkable provenance stamp, or be grandfathered into a
frozen, shrink-only exemption baseline.

Stamp (``<node_dir>/.rsd_provenance.json``, the emission-side seam contract this
gate consumes — see ``omnimarket``'s ``node_hybrid_codegen_orchestrator``
handler, ``_provenance_stamp_json``, for the producer side):

* **Machine (RSD emission)** — ``generated_by: rsd_delegation`` plus
  ``producer_node``, ``run_id``, and ``files_sha256`` (a map of generated
  filename -> ``sha256:<hex>``, MUST include ``contract.yaml``, the triggering
  artifact). The gate RECOMPUTES every listed digest from the live file on disk
  and rejects any mismatch — it never trusts the stamp's self-asserted content,
  mirroring ``canonical_handler_shape.py``'s ``verify_adequacy_receipt`` staleness
  recompute. This proves stamp/content self-consistency (anti-copy-paste,
  anti-staleness) — it is NOT a cryptographic non-repudiation / PKI proof of
  causal RSD authorship (no trusted-signer infra exists here); that is the same
  "recompute, don't trust the verdict" posture the existing OMN-14355 gate uses,
  not a stronger claim.
* **Hand-authored (OMN-14781 sanctioned exception path)** —
  ``generated_by: hand_authored`` plus a ``ticket`` matching ``OMN-\\d+`` (the
  in-ticket documented-exception citation the spec requires; never silence).

Enforcement (mirrors the OMN-14355 baseline/ratchet mechanics):

* A committed baseline (``scripts/ci/rsd_provenance_stamp_baseline.py``,
  generated) freezes the set of nodes that predate this gate and therefore
  cannot retroactively prove provenance — the GRANDFATHER exemption.
* WARN (non-blocking) on every baselined unstamped node — known debt.
* HARD-FAIL on a node missing/invalid stamp that is NOT in the baseline (this is
  exactly "a NEW node must carry a stamp" — a brand-new node has no baseline
  entry by construction, since ``--update`` only ever freezes what already
  lacked a stamp at generation time and new nodes are never added to it).
* The baseline is monotonically NON-INCREASING: any GROWTH versus the git-BASE
  (``origin/dev``) baseline is an unconditional HARD-FAIL — the exemption list is
  a bounded, shrink-only allowlist for legacy debt, never an ongoing escape
  hatch. Unlike OMN-14355's shape ratchet there is no "flip proof" needed to
  shrink this baseline: a node leaves the exemption set the moment it gets a
  valid stamp (independently, live re-derived by ``classify_node`` above), so
  no separate flip-receipt machinery exists here.

Full-scan-always (no diff-scoping): unlike the AST-heavy handler-shape
classifier, provenance classification is a JSON parse plus a handful of sha256
reads per node — cheap enough that the O(all-nodes) full scan is not a real
perf tax. This intentionally does NOT replicate OMN-14355's change-aware
``--scope changed`` / escalation machinery; the full scan is strictly stronger
(catches everything a diff-scoped run would, plus tampering issued outside the
apparent diff) and simpler to reason about. Diff-scoping is a possible future
optimization, not a correctness requirement.

Regenerate the baseline (full scan; sanctioned DOWNWARD re-freeze only — a node
leaves the baseline only by acquiring a real, gate-verified stamp)::

    uv run python scripts/ci/rsd_provenance_stamp.py --update

Run the check (CI + pre-commit)::

    uv run python scripts/ci/rsd_provenance_stamp.py

Fan-out to another package (OMN-15011 acceptance #5, follow-on, not wired as a
required check in this PR): ``--package``/``--src-root`` (or the
``ONEX_RSD_PROVENANCE_PACKAGE`` env var) repoint the scan at a sibling repo's
node tree without touching omnibase_core's own committed baseline, mirroring
``canonical_handler_shape.py``'s ``--package`` fan-out (OMN-14368).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

PACKAGE = "omnibase_core"
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
NODES_GLOB = "omnibase_core/**/nodes/**/contract.yaml"

BASELINE_PATH = Path(__file__).with_name("rsd_provenance_stamp_baseline.py")

STAMP_FILENAME = ".rsd_provenance.json"
EXPECTED_STAMP_SCHEMA = "rsd_provenance_stamp.v1"
_TICKET_RE = re.compile(r"^OMN-\d+$")

CategoryT = Literal[
    "rsd_delegation",
    "hand_authored",
    "missing",
    "unparseable",
    "bad_schema",
    "incomplete_machine_stamp",
    "stamp_file_missing",
    "stamp_hash_mismatch",
    "hand_authored_bad_ticket",
    "unknown_generated_by",
]

_BASELINE_HEADER = '''# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""FROZEN RSD provenance-stamp exemption baseline — OMN-15011.

Generated by ``scripts/ci/rsd_provenance_stamp.py --update``. Do not edit by hand.

``EXEMPT_UNSTAMPED`` is the frozen set of nodes that predate the provenance-stamp
gate and therefore carry no ``.rsd_provenance.json``. It is monotonically
NON-INCREASING: it may only shrink, and only by a node acquiring a real,
gate-verified stamp (no separate flip-receipt is required — the stamp's own
recompute IS the proof). A NEW node without a stamp, or ANY growth of this set,
HARD-FAILS CI + pre-commit. Retirement mechanism = backfilling real provenance
stamps (or documented hand-authored exceptions) onto the legacy nodes below.
"""
'''


# --------------------------------------------------------------------------- #
# Typed finding model (rule #5: emit a typed finding, not prose)
# --------------------------------------------------------------------------- #


class ModelProvenanceFinding(BaseModel):
    """One node's provenance-stamp classification result."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    node_id: str
    is_stamped: bool
    category: CategoryT
    detail: str | None = None


class RatchetResult(BaseModel):
    """Outcome of a ratchet check."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    new_unstamped: tuple[str, ...]
    warn_baselined: tuple[str, ...]
    baseline_growth: tuple[str, ...] = ()

    @property
    def failed(self) -> bool:
        return bool(self.new_unstamped or self.baseline_growth)


# --------------------------------------------------------------------------- #
# Classification (recompute-not-trust, mirrors verify_adequacy_receipt)
# --------------------------------------------------------------------------- #


def _node_package(contract_path: Path) -> str:
    """Dotted package for the node dir holding ``contract.yaml``."""
    rel = contract_path.parent.relative_to(SRC_ROOT)
    return ".".join(rel.parts)


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def classify_node(contract_path: Path) -> ModelProvenanceFinding:
    """Classify one node's provenance stamp (recomputing, never trusting it)."""
    node_id = _node_package(contract_path)
    node_dir = contract_path.parent
    stamp_path = node_dir / STAMP_FILENAME

    if not stamp_path.exists():
        return ModelProvenanceFinding(
            node_id=node_id,
            is_stamped=False,
            category="missing",
            detail=f"no {STAMP_FILENAME}",
        )
    raw = _load_json(stamp_path)
    if raw is None:
        return ModelProvenanceFinding(
            node_id=node_id,
            is_stamped=False,
            category="unparseable",
            detail=f"{STAMP_FILENAME} is not valid JSON / not an object",
        )
    schema = raw.get("receipt_schema")
    if schema != EXPECTED_STAMP_SCHEMA:
        return ModelProvenanceFinding(
            node_id=node_id,
            is_stamped=False,
            category="bad_schema",
            detail=f"receipt_schema={schema!r} != {EXPECTED_STAMP_SCHEMA!r}",
        )

    generated_by = raw.get("generated_by")

    if generated_by == "hand_authored":
        ticket = raw.get("ticket")
        if not isinstance(ticket, str) or not _TICKET_RE.match(ticket):
            return ModelProvenanceFinding(
                node_id=node_id,
                is_stamped=False,
                category="hand_authored_bad_ticket",
                detail=f"ticket={ticket!r} does not match OMN-<digits>",
            )
        return ModelProvenanceFinding(
            node_id=node_id,
            is_stamped=True,
            category="hand_authored",
            detail=f"ticket={ticket}",
        )

    if generated_by == "rsd_delegation":
        producer_node = raw.get("producer_node")
        run_id = raw.get("run_id")
        files_sha256 = raw.get("files_sha256")
        if not isinstance(producer_node, str) or not producer_node:
            return ModelProvenanceFinding(
                node_id=node_id,
                is_stamped=False,
                category="incomplete_machine_stamp",
                detail="missing/empty producer_node",
            )
        if not isinstance(run_id, str) or not run_id:
            return ModelProvenanceFinding(
                node_id=node_id,
                is_stamped=False,
                category="incomplete_machine_stamp",
                detail="missing/empty run_id",
            )
        if not isinstance(files_sha256, dict) or not files_sha256:
            return ModelProvenanceFinding(
                node_id=node_id,
                is_stamped=False,
                category="incomplete_machine_stamp",
                detail="missing/empty files_sha256",
            )
        if "contract.yaml" not in files_sha256:
            return ModelProvenanceFinding(
                node_id=node_id,
                is_stamped=False,
                category="incomplete_machine_stamp",
                detail=(
                    "files_sha256 does not cover contract.yaml "
                    "(the triggering artifact)"
                ),
            )
        # RECOMPUTE every claimed digest from the live file — do not trust it.
        for rel, recorded in sorted(files_sha256.items()):
            target = node_dir / str(rel)
            if not target.exists():
                return ModelProvenanceFinding(
                    node_id=node_id,
                    is_stamped=False,
                    category="stamp_file_missing",
                    detail=f"{rel} referenced by stamp but absent on disk",
                )
            live = _sha256_file(target)
            if live != recorded:
                return ModelProvenanceFinding(
                    node_id=node_id,
                    is_stamped=False,
                    category="stamp_hash_mismatch",
                    detail=(
                        f"{rel}: live {live} != stamp-recorded {recorded!r} "
                        "(stale or forged stamp)"
                    ),
                )
        return ModelProvenanceFinding(
            node_id=node_id,
            is_stamped=True,
            category="rsd_delegation",
            detail=f"producer={producer_node} run={run_id}",
        )

    return ModelProvenanceFinding(
        node_id=node_id,
        is_stamped=False,
        category="unknown_generated_by",
        detail=f"generated_by={generated_by!r}",
    )


def classify_all() -> list[ModelProvenanceFinding]:
    findings = [classify_node(cy) for cy in sorted(SRC_ROOT.glob(NODES_GLOB))]
    return sorted(findings, key=lambda f: f.node_id)


def current_unstamped(findings: list[ModelProvenanceFinding]) -> list[str]:
    return sorted(f.node_id for f in findings if not f.is_stamped)


# --------------------------------------------------------------------------- #
# Baseline load / write
# --------------------------------------------------------------------------- #


def load_baseline(path: Path = BASELINE_PATH) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Baseline missing at {path}. Generate it with "
            f"`uv run python scripts/ci/rsd_provenance_stamp.py --update`."
        )
    spec = importlib.util.spec_from_file_location("rsd_provenance_stamp_baseline", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load baseline module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [str(n) for n in getattr(module, "EXEMPT_UNSTAMPED", ())]


def _render_tuple(items: list[str]) -> str:
    if not items:
        return "()"
    return "(\n" + "".join(f'    "{i}",\n' for i in items) + ")"


def write_baseline(unstamped: list[str], path: Path = BASELINE_PATH) -> None:
    body = (
        _BASELINE_HEADER
        + "\nEXEMPT_UNSTAMPED: tuple[str, ...] = "
        + _render_tuple(sorted(unstamped))
        + "\n"
    )
    path.write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------- #
# git-BASE baseline resolution (mirrors OMN-14781's in-PR-edit closure)
# --------------------------------------------------------------------------- #


def _git_repo_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.strip()
    return Path(root) if root else None


def _git_show(repo_root: Path, ref: str, rel_path: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{ref}:{rel_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _git_ref_exists(repo_root: Path, ref: str) -> bool:
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _parse_exempt_unstamped(source: str) -> list[str]:
    """Extract the ``EXEMPT_UNSTAMPED`` string tuple from baseline source, no exec()."""
    import ast

    tree = ast.parse(source)
    for node in tree.body:
        target_names: list[str] = []
        value: object = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_names = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        if "EXEMPT_UNSTAMPED" in target_names and value is not None:
            evaluated = ast.literal_eval(value)  # type: ignore[arg-type]
            return [str(n) for n in evaluated]
    return []


def load_base_baseline(baseline_path: Path, base_ref: str) -> list[str] | None:
    """Load ``EXEMPT_UNSTAMPED`` as it existed at ``base_ref`` (the git BASE).

    Returns the base entries when resolvable, or ``None`` when the base cannot
    be determined (no git, unknown ref) OR when the baseline file did NOT exist
    at ``base_ref`` yet. Either way ``None`` disables the growth check for this
    run WITHOUT hard-failing.

    NOTE this deliberately diverges from ``canonical_handler_shape.py``'s
    ``load_base_baseline``, which returns ``[]`` (not ``None``) for "file absent
    at base" because ITS growth check is entangled with a removal/flip-proof
    adjudication where ``[]`` correctly means "nothing to protect from removal."
    This gate has no such removal branch (shrinking needs no flip-proof — the
    live stamp recompute IS the proof), so treating "file absent at base" as
    ``[]`` here would make this gate's OWN first-ever landing PR compute its
    entire freshly-generated baseline as 100% "growth" against an empty base
    and hard-fail on itself. Returning ``None`` instead correctly skips the
    growth check on that one bootstrap PR; from the next PR onward the baseline
    exists at base and growth is checked normally.
    """
    repo_root = _git_repo_root(baseline_path)
    if repo_root is None:
        return None
    if not _git_ref_exists(repo_root, base_ref):
        return None
    try:
        rel = baseline_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    source = _git_show(repo_root, base_ref, str(rel).replace(os.sep, "/"))
    if source is None:
        return None
    try:
        return _parse_exempt_unstamped(source)
    except (SyntaxError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Enforcement
# --------------------------------------------------------------------------- #


def evaluate(
    findings: list[ModelProvenanceFinding],
    baseline: list[str],
    base_baseline: list[str] | None = None,
) -> RatchetResult:
    """Ratchet verdict.

    ``baseline`` is the working-tree (post-edit) committed exemption list.
    ``base_baseline`` is that list as it existed at the git BASE (origin/dev).
    Unlike OMN-14355's shape ratchet, shrinking the baseline needs NO separate
    flip-receipt: a node leaves ``EXEMPT_UNSTAMPED`` the moment ``classify_node``
    verifies it has a valid stamp, and that verification IS the proof. Growth is
    unconditionally illegal — the exemption is a bounded, legacy-only allowlist.
    """
    baseline_set = set(baseline)
    current = set(current_unstamped(findings))

    new_unstamped = sorted(current - baseline_set)
    warn = sorted(current & baseline_set)

    baseline_growth: tuple[str, ...] = ()
    if base_baseline is not None:
        base_set = set(base_baseline)
        baseline_growth = tuple(sorted(baseline_set - base_set))

    return RatchetResult(
        new_unstamped=tuple(new_unstamped),
        warn_baselined=tuple(warn),
        baseline_growth=baseline_growth,
    )


def _format_failure(
    result: RatchetResult, findings: list[ModelProvenanceFinding]
) -> str:
    by_id = {f.node_id: f for f in findings}
    lines = [
        "RSD provenance-stamp gate FAILED (OMN-15011).",
        "",
    ]
    if result.new_unstamped:
        lines.append(
            "  Node(s) without a valid provenance stamp — new/modified nodes must"
        )
        lines.append(
            f"  carry {STAMP_FILENAME} (machine rsd_delegation stamp, re-derivable"
        )
        lines.append(
            "  via files_sha256, OR hand_authored + a documented ticket exception):"
        )
        for node_id in result.new_unstamped:
            f = by_id.get(node_id)
            lines.append(
                f"    + {node_id}  [{f.category if f else '?'}] {f.detail if f else ''}"
            )
    if result.baseline_growth:
        lines.append("")
        lines.append(
            "  Baseline GROWTH — EXEMPT_UNSTAMPED is monotonically non-increasing;"
        )
        lines.append(
            "  it may only shrink (a node acquiring a real stamp), never grow:"
        )
        for node_id in result.baseline_growth:
            lines.append(f"    + {node_id}")
    lines.append("")
    lines.append("Add a valid .rsd_provenance.json, or regenerate the baseline:")
    lines.append("  uv run python scripts/ci/rsd_provenance_stamp.py --update")
    return "\n".join(lines)


def _report(result: RatchetResult, findings: list[ModelProvenanceFinding]) -> int:
    if result.warn_baselined:
        print(
            f"RSD provenance-stamp gate WARNING (OMN-15011) — non-blocking: "
            f"{len(result.warn_baselined)} baselined (grandfathered) unstamped "
            f"node(s); known legacy debt.",
            file=sys.stderr,
        )
    if result.failed:
        print(_format_failure(result, findings), file=sys.stderr)
        return 1
    print(
        f"RSD provenance-stamp gate OK — checked {len(findings)} node(s); "
        f"new_unstamped=0 baseline_growth=0 warn={len(result.warn_baselined)}."
    )
    return 0


# --------------------------------------------------------------------------- #
# Package scoping (OMN-15011 acceptance #5: fan-out follow-on, not wired here)
# --------------------------------------------------------------------------- #


def _resolve_scope(
    package: str,
    src_root: Path | None,
    nodes_glob: str | None,
    baseline: Path | None,
) -> tuple[Path, str, Path]:
    """Compute ``(src_root, nodes_glob, baseline_path)`` for a scope.

    Mirrors ``canonical_handler_shape.py``'s ``_resolve_scope``: every argument
    defaults to the omnibase_core value already in effect, so
    ``package="omnibase_core"`` with all other args ``None`` reproduces today's
    constants exactly.
    """
    resolved_src_root = src_root if src_root is not None else SRC_ROOT
    resolved_glob = nodes_glob or f"{package}/**/nodes/**/contract.yaml"
    if baseline is not None:
        resolved_baseline = baseline
    elif package == "omnibase_core":
        resolved_baseline = BASELINE_PATH
    else:
        resolved_baseline = Path(__file__).with_name(
            f"rsd_provenance_stamp_baseline_{package}.py"
        )
    return resolved_src_root, resolved_glob, resolved_baseline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RSD provenance-stamp fail-closed gate (OMN-15011)."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Regenerate the frozen exemption baseline from a FULL scan "
        "(DOWNWARD re-freeze only).",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/dev",
        help="Diff base for the baseline-growth check.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Baseline module path. Defaults to omnibase_core's committed "
        "baseline, or rsd_provenance_stamp_baseline_<package>.py beside this "
        "script when --package overrides the target.",
    )
    parser.add_argument(
        "--package",
        default=os.environ.get("ONEX_RSD_PROVENANCE_PACKAGE", "omnibase_core"),
        help="Target package to classify (fan-out follow-on). Defaults to "
        "omnibase_core so core CI/pre-commit behavior is unchanged.",
    )
    parser.add_argument(
        "--src-root",
        type=Path,
        default=(
            Path(os.environ["ONEX_RSD_PROVENANCE_SRC_ROOT"])
            if "ONEX_RSD_PROVENANCE_SRC_ROOT" in os.environ
            else None
        ),
        help="Source root containing --package's node tree (defaults to this "
        "repo's own src/).",
    )
    parser.add_argument(
        "--nodes-glob",
        default=None,
        help="Override the contract.yaml glob (default: "
        "'<package>/**/nodes/**/contract.yaml', relative to --src-root).",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit changed files (pre-commit passes staged filenames here; "
        "unused — this gate always full-scans, see module docstring).",
    )
    args = parser.parse_args(argv)

    global PACKAGE, SRC_ROOT, NODES_GLOB, BASELINE_PATH
    PACKAGE = args.package
    SRC_ROOT, NODES_GLOB, BASELINE_PATH = _resolve_scope(
        args.package, args.src_root, args.nodes_glob, args.baseline
    )

    if args.update:
        findings = classify_all()
        unstamped = current_unstamped(findings)
        write_baseline(unstamped, BASELINE_PATH)
        print(
            f"Regenerated {BASELINE_PATH.name} (full scan, package={PACKAGE}) — "
            f"{len(findings)} nodes, stamped={len(findings) - len(unstamped)}, "
            f"unstamped={len(unstamped)}"
        )
        return 0

    baseline = load_baseline(BASELINE_PATH)
    base_baseline = load_base_baseline(BASELINE_PATH, args.base_ref)
    if base_baseline is None:
        print(
            "RSD provenance-stamp gate NOTE — git BASE baseline unavailable; "
            "baseline-growth check skipped for this run (it is active in CI "
            "where the PR base is present).",
            file=sys.stderr,
        )

    findings = classify_all()
    return _report(evaluate(findings, baseline, base_baseline), findings)


if __name__ == "__main__":
    raise SystemExit(main())
