# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read and re-derive adequacy and equivalence artifact evidence."""

from __future__ import annotations

import ast
import os
from pathlib import Path

from omnibase_core.validation.validator_flip_git import _git_repo_root
from omnibase_core.validation.validator_flip_scope import SCOPE

EXPECTED_RECEIPT_SCHEMA = "adequacy_receipt.v1"

EQUIVALENCE_SUFFIX = ".equivalence.json"

HANDFLIP_SUFFIX = ".handflip.json"

EXPECTED_HANDFLIP_SCHEMA = "handflip_proof.v1"

EXPECTED_NO_LEGACY_SCHEMA = "adequacy_receipt.no_legacy.v1"

LEGACY_HANDLER_NONE = "none"


def _resolve_module_file(module: str) -> Path | None:
    candidate = SCOPE.src_root / (module.replace(".", "/") + ".py")
    return candidate if candidate.exists() else None


def _sha256_file(path: Path) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object] | None:
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _display_path(path: Path) -> str:
    """Best-effort repo-relative display for a receipt/artifact path.

    OMN-14781: under fan-out (``--package``/``--receipts-dir`` pointing at a
    SIBLING repo, e.g. omnimarket), ``SCOPE.receipts_dir`` lives outside this
    classifier's own ``SCOPE.repo_root`` (which always resolves to omnibase_core). A
    naive ``path.relative_to(SCOPE.repo_root)`` then raises ``ValueError`` and crashes
    the whole gate mid-classification. Fall back to the absolute/original path
    rather than raising — the message is cosmetic, the verdict is not.
    """
    try:
        return str(path.resolve().relative_to(SCOPE.repo_root))
    except ValueError:
        return str(path)


def verify_adequacy_receipt(
    node_id: str, handler_module: str | None
) -> tuple[bool, str, list[str]]:
    """Re-derive the adequacy verdict from the receipt's RAW numbers.

    Returns ``(ok, reason, selected_input_hashes)``. Ignores the receipt's
    self-asserted ``meets_target``; recomputes ``pct >= target``; recomputes the
    handler-module sha256 live and rejects a stale receipt.
    """
    receipt_path = SCOPE.receipts_dir / f"{node_id}.json"
    if not receipt_path.exists():
        return (
            False,
            f"no adequacy receipt at {_display_path(receipt_path)}",
            [],
        )
    raw = _load_json(receipt_path)
    if raw is None:
        return False, "receipt unparseable / not an object", []
    if raw.get("node_id") != node_id:
        return False, f"receipt node_id {raw.get('node_id')!r} != {node_id!r}", []
    schema = raw.get("receipt_schema")
    if schema is not None and schema != EXPECTED_RECEIPT_SCHEMA:
        return False, f"unexpected receipt_schema {schema!r}", []
    try:
        pct_raw = raw["branch_coverage_pct"]
        target_raw = raw.get("coverage_target", 80.0)
        if not isinstance(pct_raw, (str, int, float)) or not isinstance(
            target_raw, (str, int, float)
        ):
            return False, "receipt missing/invalid coverage numbers", []
        pct = float(pct_raw)
        target = float(target_raw)
    except (KeyError, TypeError, ValueError):
        return False, "receipt missing/invalid coverage numbers", []
    waiver = raw.get("uncovered_waiver")
    has_waiver = isinstance(waiver, dict) and bool(waiver.get("reason"))
    if pct < target and not has_waiver:
        return False, f"recomputed below target ({pct} < {target}) and no waiver", []
    recorded_sha = raw.get("handler_module_sha256")
    module = raw.get("handler_module") or handler_module
    if not isinstance(module, str) or not module:
        return False, "receipt has no handler_module to freshness-check", []
    module_file = _resolve_module_file(module)
    if module_file is None:
        return False, f"handler_module {module} not resolvable for freshness check", []
    if _sha256_file(module_file) != recorded_sha:
        return False, "stale receipt: live handler_module_sha256 != recorded", []
    hashes = raw.get("selected_input_hashes")
    selected = [str(h) for h in hashes] if isinstance(hashes, list) else []
    verdict = "recomputed-meets-target" if pct >= target else "reviewed-waiver"
    return True, verdict, selected


def verify_equivalence_replay(node_id: str) -> tuple[bool, str, list[str]]:
    """Require a GREEN regen-vs-legacy equivalence-replay artifact for the node."""
    art_path = SCOPE.receipts_dir / f"{node_id}{EQUIVALENCE_SUFFIX}"
    if not art_path.exists():
        return False, "no green equivalence-replay artifact", []
    raw = _load_json(art_path)
    if raw is None:
        return False, "equivalence artifact unparseable", []
    if raw.get("node_id") != node_id:
        return False, "equivalence artifact node_id mismatch", []
    if raw.get("status") != "pass":
        return False, f"equivalence replay status={raw.get('status')!r}", []
    hashes = raw.get("selected_input_hashes")
    return (
        True,
        "equivalence-pass",
        [str(h) for h in hashes] if isinstance(hashes, list) else [],
    )


def _extract_symbol_sources(
    source_text: str, symbols: list[str]
) -> dict[str, str] | None:
    """Normalized (``ast.unparse``) source for each named symbol, or None if any missing.

    A bare ``name`` matches a function/method with that name anywhere in the module
    (module-level def or a method on any class). A qualified ``Class.method`` matches
    only that method on that class. Normalization via ``ast.unparse`` strips comments
    and whitespace but preserves structure and identifiers, so two verbatim-identical
    bodies hash equal while any real logic change diverges (fail-closed).
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return None
    wanted = set(symbols)
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for m in node.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qual = f"{node.name}.{m.name}"
                    if qual in wanted and qual not in found:
                        found[qual] = ast.unparse(m)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in wanted and node.name not in found:
                found[node.name] = ast.unparse(node)
    if wanted - set(found):
        return None
    return found


def _module_repo_rel(module: str) -> tuple[Path, str] | None:
    """(repo_root, path-relative-to-repo-root) for a dotted module under SCOPE.src_root."""
    file_path = SCOPE.src_root / (module.replace(".", "/") + ".py")
    repo_root = _git_repo_root(SCOPE.src_root if SCOPE.src_root.exists() else file_path)
    if repo_root is None:
        return None
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    return repo_root, str(rel).replace(os.sep, "/")
