# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RSD provenance-stamp blocking check for omnibase_core (OMN-15011).

Every node under the package's node tree must carry a valid, machine-checkable
provenance stamp. Any node without a valid stamp fails; there is no exemption
list.

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

The check always scans the full node tree. Provenance classification is a JSON
parse plus a handful of sha256 reads per node, so a full scan is inexpensive
and catches invalid stamps regardless of which files changed. Positional
filenames passed by pre-commit are accepted without narrowing the scan.

Run the check (CI + pre-commit)::

    uv run python scripts/ci/rsd_provenance_stamp.py

The ``--package``/``--src-root`` options (or the
``ONEX_RSD_PROVENANCE_PACKAGE``/``ONEX_RSD_PROVENANCE_SRC_ROOT`` environment
variables) repoint the scan at another package's node tree. ``--nodes-glob``
can override the contract-file pattern.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
    """Outcome of the provenance-stamp check."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    new_unstamped: tuple[str, ...]

    @property
    def failed(self) -> bool:
        return bool(self.new_unstamped)


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
# Enforcement
# --------------------------------------------------------------------------- #


def evaluate(findings: list[ModelProvenanceFinding]) -> RatchetResult:
    """Fail every node without a valid provenance stamp."""
    return RatchetResult(new_unstamped=tuple(current_unstamped(findings)))


def _format_failure(
    result: RatchetResult, findings: list[ModelProvenanceFinding]
) -> str:
    by_id = {f.node_id: f for f in findings}
    lines = [
        "RSD provenance-stamp check FAILED (OMN-15011).",
        "",
    ]
    if result.new_unstamped:
        lines.append("  Node(s) without a valid provenance stamp — every node must")
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
    lines.append("")
    lines.append("Every node without a valid stamp fails; there is no exemption list.")
    lines.append(f"Add a valid {STAMP_FILENAME} to each listed node.")
    return "\n".join(lines)


def _report(result: RatchetResult, findings: list[ModelProvenanceFinding]) -> int:
    if result.failed:
        print(_format_failure(result, findings), file=sys.stderr)
        return 1
    print(
        f"RSD provenance-stamp check OK — checked {len(findings)} node(s); unstamped=0."
    )
    return 0


# --------------------------------------------------------------------------- #
# Package scoping (OMN-15011 acceptance #5: fan-out follow-on, not wired here)
# --------------------------------------------------------------------------- #


def _resolve_scope(
    package: str,
    src_root: Path | None,
    nodes_glob: str | None,
) -> tuple[Path, str]:
    """Compute ``(src_root, nodes_glob)`` for a scope.

    Mirrors ``canonical_handler_shape.py``'s ``_resolve_scope``: every argument
    defaults to the omnibase_core value already in effect, so
    ``package="omnibase_core"`` with all other args ``None`` reproduces today's
    constants exactly.
    """
    resolved_src_root = src_root if src_root is not None else SRC_ROOT
    resolved_glob = nodes_glob or f"{package}/**/nodes/**/contract.yaml"
    return resolved_src_root, resolved_glob


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RSD provenance-stamp blocking check (OMN-15011)."
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

    global PACKAGE, SRC_ROOT, NODES_GLOB
    PACKAGE = args.package
    SRC_ROOT, NODES_GLOB = _resolve_scope(args.package, args.src_root, args.nodes_glob)

    findings = classify_all()
    return _report(evaluate(findings), findings)


if __name__ == "__main__":
    raise SystemExit(main())
