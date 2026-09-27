# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lane-literal branching guard (OMN-19760, runtime lane overlays plan LO16).

A runtime learns which lane it is, and what that lane is for, only from a
deployment overlay supplied by whoever runs it (``runtime.lane``, OMN-19746).
Shipped code may therefore branch on a lane's ROLE (``EnumRuntimeLaneRole``),
never on a lane's NAME: a name compiled into code is one deployment's topology,
and every other deployment either inherits it or needs a code change.

The guard is structural, so it carries no list of lane names. It refuses:

``lane-literal-compare``
    ``==``/``!=`` between a lane-valued expression and a string literal, or
    ``in``/``not in`` of a lane-valued expression in a literal collection of
    strings. A bare name on the literal side resolves through module- and
    class-level ``NAME = <literal>`` bindings, so ``lane == _X_LANE`` with
    ``_X_LANE = "x"`` is the same finding. A lane-valued expression is a name or attribute called ``lane``,
    ``lane_id``, ``lane_name`` or ``<prefix>_lane[_id|_name]`` (optionally
    through ``.value``, ``.name``, ``str()`` or a case/strip method), a read of
    the ``ONEX_RUNTIME_LANE`` environment variable, or a name assigned from one.

``lane-literal-match``
    ``match`` on a lane-valued expression with a string-literal ``case``.

``lane-literal-collection``
    A module- or class-level collection (tuple, list, set, frozenset, dict
    keys, or a ``|``/``+`` of them) of lane-like string literals bound to a
    name whose last ``_`` segment is ``LANE``/``LANES`` (``X_LANES``), or a
    dict literal whose name starts with one (``LANE_PORTS``, keyed by lane).

A lane-like literal is a non-empty string that is not shaped like an
environment-variable name, so ``LANE_ENV_VAR = "ONEX_RUNTIME_LANE"`` passes.

Ratchet: a baseline file (``--baseline``) grandfathers today's findings by
content fingerprint; only new fingerprints fail, and ``--update-baseline``
refuses to let the baseline grow. There is no inline suppression marker.

Usage::

    python -m omnibase_core.validation.validator_no_lane_literal_branching \\
        --repo-root . --baseline <baseline.json> src/

Exit codes: ``0`` clean, ``1`` new findings, ``2`` usage or baseline error.
"""

from __future__ import annotations

__all__ = [
    "RULE_LANE_LITERAL_COLLECTION",
    "RULE_LANE_LITERAL_COMPARE",
    "RULE_LANE_LITERAL_MATCH",
    "load_baseline",
    "main",
    "make_fingerprint",
    "partition_against_baseline",
    "scan_paths",
    "scan_source",
]

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

from omnibase_core.models.validation.model_lane_literal_branching_violation import (
    ModelLaneLiteralBranchingViolation,
)

RULE_LANE_LITERAL_COMPARE = "lane-literal-compare"
RULE_LANE_LITERAL_MATCH = "lane-literal-match"
RULE_LANE_LITERAL_COLLECTION = "lane-literal-collection"

_LANE_ENV_VAR = "ONEX_RUNTIME_LANE"
_LANE_NAME_RE = re.compile(r"^(?:[a-z0-9]+_)*lane(?:_id|_name)?$", re.IGNORECASE)
_ENV_NAME_SHAPE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_LANE_SEGMENTS = frozenset({"LANE", "LANES"})
_UNWRAP_ATTRS = frozenset({"value", "name"})
_UNWRAP_METHODS = frozenset({"lower", "upper", "casefold", "strip", "lstrip", "rstrip"})
_COLLECTION_CALLS = frozenset({"frozenset", "set", "tuple", "list"})
_SKIP_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache"}
)
_BASELINE_SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Pure scanner
# ---------------------------------------------------------------------------


def make_fingerprint(path: str, rule: str, snippet: str) -> str:
    """``sha256:<hex>`` of path, rule and the whitespace-normalized snippet.

    The ``sha256:`` prefix types the value as a digest, the same notation as an
    image digest, so it reads as a fingerprint rather than an opaque token.
    """
    normalized = " ".join(snippet.split())
    digest = hashlib.sha256(f"{path}\0{rule}\0{normalized}".encode()).hexdigest()
    return f"sha256:{digest}"


def _is_lane_like(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.strip() != ""
        and not _ENV_NAME_SHAPE_RE.match(value)
    )


def _is_lane_env_read(node: ast.AST) -> bool:
    """``os.environ["ONEX_RUNTIME_LANE"]``, ``os.environ.get(...)``, ``os.getenv(...)``."""
    if isinstance(node, ast.Subscript):
        key = node.slice
        return (
            isinstance(key, ast.Constant)
            and key.value == _LANE_ENV_VAR
            and "environ" in ast.unparse(node.value)
        )
    if isinstance(node, ast.Call) and node.args:
        first = node.args[0]
        func_text = ast.unparse(node.func)
        return (
            isinstance(first, ast.Constant)
            and first.value == _LANE_ENV_VAR
            and ("getenv" in func_text or "environ" in func_text)
        )
    return False


def _contains_lane_env_read(node: ast.AST) -> bool:
    return any(_is_lane_env_read(sub) for sub in ast.walk(node))


def _is_lane_valued(node: ast.expr, tainted: frozenset[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in tainted or bool(_LANE_NAME_RE.match(node.id))
    if isinstance(node, ast.Attribute):
        if node.attr in _UNWRAP_ATTRS and _is_lane_valued(node.value, tainted):
            return True
        return bool(_LANE_NAME_RE.match(node.attr))
    if isinstance(node, ast.Call):
        if _is_lane_env_read(node):
            return True
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _UNWRAP_METHODS:
            return _is_lane_valued(func.value, tainted)
        if isinstance(func, ast.Name) and func.id == "str" and len(node.args) == 1:
            return _is_lane_valued(node.args[0], tainted)
        # a call whose own name says it yields a lane: claimed_lane(...)
        func_name = func.id if isinstance(func, ast.Name) else None
        if isinstance(func, ast.Attribute):
            func_name = func.attr
        return func_name is not None and bool(_LANE_NAME_RE.match(func_name))
    if isinstance(node, ast.Subscript):
        return _is_lane_env_read(node)
    if isinstance(node, ast.BoolOp):
        return any(_is_lane_valued(v, tainted) for v in node.values)
    return False


def _collection_strings(node: ast.expr) -> list[object] | None:
    """Values of a literal string collection, or ``None`` when not a literal one."""
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        if all(isinstance(e, ast.Constant) for e in node.elts):
            return [e.value for e in node.elts if isinstance(e, ast.Constant)]
        return None
    if isinstance(node, ast.Dict):
        if all(isinstance(k, ast.Constant) for k in node.keys):
            return [k.value for k in node.keys if isinstance(k, ast.Constant)]
        return None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _COLLECTION_CALLS
        and not node.keywords
    ):
        if not node.args:
            return []
        if len(node.args) == 1:
            return _collection_strings(node.args[0])
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.Add)):
        left = _collection_strings(node.left)
        right = _collection_strings(node.right)
        if left is None and right is None:
            return None
        return [*(left or []), *(right or [])]
    return None


def _has_lane_like(values: list[object] | None) -> bool:
    return values is not None and any(_is_lane_like(v) for v in values)


def _tainted_names(tree: ast.AST) -> frozenset[str]:
    """Names assigned from a lane-valued expression, to a fixpoint.

    ``current = os.getenv("ONEX_RUNTIME_LANE")`` and ``claimed =
    claimed_lane(...)`` make ``current`` and ``claimed`` lane-valued, and so
    does any name assigned from one of those.
    """
    bindings: list[tuple[list[str], ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value:
            targets, value = [node.target], node.value
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if names:
            bindings.append((names, value))

    tainted: set[str] = set()
    changed = True
    while changed:
        changed = False
        frozen = frozenset(tainted)
        for names, value in bindings:
            if set(names) <= tainted:
                continue
            if _contains_lane_env_read(value) or _is_lane_valued(value, frozen):
                tainted.update(names)
                changed = True
    return frozenset(tainted)


def _module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    """Module- and class-level ``NAME = <literal>`` bindings, by name.

    A lane literal moved into a constant (``_X_LANE: Final = "x"``) and then
    compared (``lane == _X_LANE``) is the same branch on a lane name, so a
    comparison resolves a bare name through these bindings.
    """
    constants: dict[str, ast.expr] = {}
    for stmt in _binding_statements(tree.body):
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            constants[stmt.targets[0].id] = stmt.value
        elif (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.value is not None
        ):
            constants[stmt.target.id] = stmt.value
    return constants


def _resolve(node: ast.expr, constants: dict[str, ast.expr]) -> ast.expr:
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    return node


def _compare_flags(
    node: ast.Compare, tainted: frozenset[str], constants: dict[str, ast.expr]
) -> bool:
    operands = [node.left, *node.comparators]
    for i, op in enumerate(node.ops):
        left, right = operands[i], operands[i + 1]
        if isinstance(op, (ast.Eq, ast.NotEq)):
            for a, b in ((left, right), (right, left)):
                literal = _resolve(b, constants)
                if (
                    _is_lane_valued(a, tainted)
                    and isinstance(literal, ast.Constant)
                    and _is_lane_like(literal.value)
                ):
                    return True
        elif isinstance(op, (ast.In, ast.NotIn)):
            if _is_lane_valued(left, tainted) and _has_lane_like(
                _collection_strings(_resolve(right, constants))
            ):
                return True
    return False


def _pattern_has_lane_literal(pattern: ast.pattern) -> bool:
    for sub in ast.walk(pattern):
        if (
            isinstance(sub, ast.MatchValue)
            and isinstance(sub.value, ast.Constant)
            and _is_lane_like(sub.value.value)
        ):
            return True
    return False


def _binding_statements(body: list[ast.stmt]) -> list[ast.stmt]:
    """Module- and class-level statements, not function bodies."""
    out: list[ast.stmt] = []
    for stmt in body:
        if isinstance(stmt, ast.ClassDef):
            out.extend(_binding_statements(stmt.body))
        else:
            out.append(stmt)
    return out


def _name_segments(name: str) -> list[str]:
    return [seg for seg in name.upper().split("_") if seg]


def _names_a_lane_collection(name: str, value: ast.expr) -> bool:
    """``X_LANES = (...)`` holds lanes; ``LANE_PORTS = {...}`` is keyed by lane.

    Whole ``_``-separated segments only, so ``CONTROL_PLANE_TOPICS`` is not a
    lane name and ``LANES_SUBDIR`` (a path) is not a lane collection.
    """
    segments = _name_segments(name)
    if not segments:
        return False
    if segments[-1] in _LANE_SEGMENTS:
        return True
    return isinstance(value, ast.Dict) and segments[0] in _LANE_SEGMENTS


def _collection_flags(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Assign):
        names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        value: ast.expr | None = stmt.value
    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        names, value = [stmt.target.id], stmt.value
    else:
        return False
    if value is None or not any(_names_a_lane_collection(n, value) for n in names):
        return False
    return _has_lane_like(_collection_strings(value))


def scan_source(source: str, path: str) -> list[ModelLaneLiteralBranchingViolation]:
    """Scan Python *source* and return its findings; a syntax error yields none."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    tainted = _tainted_names(tree)
    constants = _module_constants(tree)
    found: list[tuple[ast.AST, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and _compare_flags(node, tainted, constants):
            found.append((node, RULE_LANE_LITERAL_COMPARE))
        elif (
            isinstance(node, ast.Match)
            and _is_lane_valued(node.subject, tainted)
            and any(_pattern_has_lane_literal(c.pattern) for c in node.cases)
        ):
            found.append((node, RULE_LANE_LITERAL_MATCH))
    found.extend(
        (stmt, RULE_LANE_LITERAL_COLLECTION)
        for stmt in _binding_statements(tree.body)
        if _collection_flags(stmt)
    )

    violations: list[ModelLaneLiteralBranchingViolation] = []
    for node, rule in found:
        # ast.unparse, not the raw segment: comments and layout inside a
        # multi-line literal do not change a finding's identity.
        if isinstance(node, ast.Match):
            snippet = f"match {ast.unparse(node.subject)}"
        else:
            snippet = ast.unparse(node)
        violations.append(
            ModelLaneLiteralBranchingViolation(
                path=path,
                line=getattr(node, "lineno", 0),
                rule=rule,
                snippet=" ".join(snippet.split()),
                fingerprint=make_fingerprint(path, rule, snippet),
            )
        )
    violations.sort(key=lambda v: (v.path, v.line, v.rule))
    return violations


# ---------------------------------------------------------------------------
# Baseline (pure)
# ---------------------------------------------------------------------------


def partition_against_baseline(
    violations: list[ModelLaneLiteralBranchingViolation],
    baseline_fingerprints: set[str],
) -> tuple[
    list[ModelLaneLiteralBranchingViolation], list[ModelLaneLiteralBranchingViolation]
]:
    """Split findings into (new, grandfathered) by baseline membership."""
    new = [v for v in violations if v.fingerprint not in baseline_fingerprints]
    old = [v for v in violations if v.fingerprint in baseline_fingerprints]
    return new, old


def _baseline_entries(data: object) -> list[dict[str, str]]:
    if not isinstance(data, dict):
        return []
    entries = data.get("violations", [])
    if not isinstance(entries, list):
        return []
    return [
        {str(k): str(v) for k, v in e.items()}
        for e in entries
        if isinstance(e, dict) and "fingerprint" in e
    ]


def load_baseline(baseline_path: Path) -> list[dict[str, str]]:
    """Read the baseline document's entries (``path``, ``rule``, ``fingerprint``)."""
    return _baseline_entries(json.loads(baseline_path.read_text(encoding="utf-8")))


def _serialize_baseline(entries: list[dict[str, str]]) -> str:
    ordered = sorted(entries, key=lambda e: (e["path"], e["rule"], e["fingerprint"]))
    doc = {
        "schema_version": _BASELINE_SCHEMA_VERSION,
        "ticket": "OMN-19760",
        "note": "burn-down only: remove entries as lane-name branching is replaced by role checks",
        "count": len(ordered),
        "violations": ordered,
    }
    return json.dumps(doc, indent=2, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------
# Filesystem boundary and CLI
# ---------------------------------------------------------------------------


def _python_files(targets: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for target in targets:
        if target.is_dir():
            files.update(
                p for p in target.rglob("*.py") if not _SKIP_DIRS.intersection(p.parts)
            )
        elif target.suffix == ".py":
            files.add(target)
    return sorted(files)


def _relative(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def scan_paths(
    targets: list[Path], repo_root: Path
) -> tuple[list[ModelLaneLiteralBranchingViolation], list[str]]:
    """Scan every ``.py`` file under *targets*; returns (findings, scanned paths)."""
    violations: list[ModelLaneLiteralBranchingViolation] = []
    scanned: list[str] = []
    for file in _python_files(targets):
        rel = _relative(file, repo_root)
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned.append(rel)
        violations.extend(scan_source(source, path=rel))
    return violations, scanned


def _out(message: str) -> None:
    sys.stdout.write(message + "\n")


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _update_baseline(
    violations: list[ModelLaneLiteralBranchingViolation],
    scanned: list[str],
    baseline_path: Path,
) -> int:
    prior = load_baseline(baseline_path) if baseline_path.exists() else None
    scanned_set = set(scanned)
    fresh = [
        {"path": v.path, "rule": v.rule, "fingerprint": v.fingerprint}
        for v in violations
    ]
    if prior is not None:
        prior_fps = {e["fingerprint"] for e in prior}
        grown = [e for e in fresh if e["fingerprint"] not in prior_fps]
        if grown:
            _err(
                f"[lane-literal-gate] refused: the baseline would grow by {len(grown)} "
                "finding(s). The baseline only shrinks; branch on a lane role "
                "(EnumRuntimeLaneRole) instead:"
            )
            for e in grown:
                _err(f"  {e['path']}: {e['rule']}")
            return 2
        kept = [e for e in prior if e["path"] not in scanned_set]
        fresh = kept + fresh
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(_serialize_baseline(fresh), encoding="utf-8")
    _out(
        f"[lane-literal-gate] baseline written: {len(fresh)} entr(y/ies) -> {baseline_path}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for pre-commit and standalone use."""
    parser = argparse.ArgumentParser(
        description=(
            "Refuse branching on a runtime lane NAME (OMN-19760). Branch on the "
            "lane's role from its runtime.lane overlay document instead."
        )
    )
    parser.add_argument("targets", nargs="*", type=Path, help="files or directories")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(),
        help="root that finding paths and fingerprints are relative to",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="ratchet baseline JSON; without it every finding fails",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite the baseline from the scanned targets (shrink only)",
    )
    args = parser.parse_args(argv)

    if not args.targets:
        return 0

    violations, scanned = scan_paths(args.targets, args.repo_root)

    if args.update_baseline:
        if args.baseline is None:
            _err("[lane-literal-gate] --update-baseline needs --baseline")
            return 2
        return _update_baseline(violations, scanned, args.baseline)

    baseline_fps: set[str] = set()
    if args.baseline is not None:
        if not args.baseline.exists():
            _err(f"[lane-literal-gate] baseline not found: {args.baseline}")
            return 2
        baseline_fps = {e["fingerprint"] for e in load_baseline(args.baseline)}

    new, _old = partition_against_baseline(violations, baseline_fps)
    if not new:
        return 0
    _out(f"[lane-literal-gate] [FAIL] {len(new)} branch(es) on a runtime lane name:")
    for v in new:
        shown = v.snippet if len(v.snippet) <= 160 else v.snippet[:157] + "..."
        _out(f"  {v.path}:{v.line}: {v.rule}: {shown}")
    _out(
        "\nA lane's name belongs to one deployment. Declare what the lane is for "
        "as a role in its runtime.lane overlay document and branch on "
        "EnumRuntimeLaneRole; per-lane data belongs in that deployment's overlay "
        "(OMN-19760)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
