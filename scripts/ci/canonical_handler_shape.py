# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical handler-shape GROWTH RATCHET for omnibase_core (OMN-14355).

The missing enforcement surface for the RSD canonical rewrite. ``compliance_sweep``
checks handler *hygiene* (topic/transport/logic-in-node) but is blind to handler
*shape* — so a node whose handler is not the canonical shape passes green CI. This
ratchet classifies each node's contract-declared handler shape and forces the
non-canonical set to shrink monotonically.

Canonical definition = B (operator-locked, OMN-14355): a typed-payload handler
core ``handle(request) -> response`` bound via the contract, adapted by the shared
runtime (``omnibase_core.runtime.runtime_local_adapter``, OMN-8724). The core must
NOT reference the ``ModelEventEnvelope`` type (the envelope boundary is the shared
runtime adapter, NOT a per-node wrapper). Concretely a node is canonical when:

* the contract binds a handler (``handler.module`` / ``handler_routing`` entry /
  ``default_handler``); and
* that handler class exposes a ``handle`` method the runtime can adapt — a single
  positional parameter that is BaseModel-typed, or named
  ``request``/``payload``/``event``/``input_model``/``command``, or a zero-arg /
  ``**kwargs`` method; and
* the resolved handler module does not import/reference ``ModelEventEnvelope``
  (C-core: no envelope type in the core).

Everything else is non-canonical: no handler binding, an unresolved
(phantom) binding, a class with only operation-named methods (no ``handle``),
an empty handler class, a non-adaptable ``handle`` (raw ``dict``/multi-positional),
or a core that reaches into the envelope directly (``envelope_in_core``).

Enforcement (mirrors the import-layering ratchet, OMN-14340):

* A committed baseline (``scripts/ci/canonical_handler_shape_baseline.py``,
  generated) freezes the current non-canonical node set as a plain tuple.
* WARN (non-blocking) on every baselined non-canonical node — known debt.
* HARD-FAIL on a NEW non-canonical node (not in the baseline) or baseline-count
  growth. New nodes must be born canonical.
* A node FLIPS non-canonical -> canonical (baseline shrinks) ONLY with a 3-part
  proof: (1) shape-canonical; (2) an adequacy receipt whose verdict the gate
  RE-DERIVES from the raw numbers (it never trusts the receipt's self-asserted
  ``meets_target`` — a persisted receipt can lie; it recomputes ``pct >= target``
  and re-hashes the handler module live for staleness); (3) a GREEN
  equivalence-replay artifact bound to the SAME selected input set. Coverage is
  not equivalence: a receipt without a passing regen-vs-legacy replay never flips
  (the OMN-14208-at-scale trap). "A test file exists" is insufficient.

Scope (change-aware, O(changed) on the hot path):

* default ``--scope changed`` classifies only the nodes owning the diff's files
  (pre-commit passes staged filenames; CI diffs ``--base-ref``). A change to the
  classifier, the baseline, or a module the classifier resolves THROUGH (the
  runtime adapter / envelope mixin / a shared module) FAIL-CLOSED escalates to a
  full scan.
* ``--full`` / ``--scope full`` scans the whole repository (baseline generation,
  periodic drift audit, main-boundary verification).

Regenerate the baseline (full scan; sanctioned DOWNWARD re-freeze only — new
canonical nodes each carry an adequacy + equivalence proof)::

    uv run python scripts/ci/canonical_handler_shape.py --update

Run the check (CI + pre-commit)::

    uv run python scripts/ci/canonical_handler_shape.py            # diff-scoped
    uv run python scripts/ci/canonical_handler_shape.py --full     # whole repo

Fan-out to another package (OMN-14368): ``--package``/``--src-root`` (or the
``ONEX_CANON_SHAPE_PACKAGE`` env var) repoint the scan at a sibling repo's node
tree without touching omnibase_core's own committed baseline. Both default to
omnibase_core, so core behavior is byte-for-byte unchanged when unset::

    uv run python scripts/ci/canonical_handler_shape.py --update \\
        --package omnimarket --src-root ../omnimarket/src \\
        --baseline ../omnimarket/scripts/ci/canonical_handler_shape_baseline.py
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

PACKAGE = "omnibase_core"
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
NODES_GLOB = "omnibase_core/**/nodes/**/contract.yaml"

BASELINE_PATH = Path(__file__).with_name("canonical_handler_shape_baseline.py")
# Committed adequacy receipts, one per flipped node: ``<node_id>.json``.
RECEIPTS_DIR = Path(__file__).with_name("adequacy_receipts")

# Single-positional parameter names the shared runtime adapter pass-through
# recognizes (``runtime_local_adapter._parameter_expects_model`` + the coercion
# path). A ``handle`` with one of these (or a BaseModel-typed) param is adapted.
MAGIC_PARAM_NAMES = frozenset(
    {"request", "payload", "event", "input_model", "command", "input", "cmd", "msg"}
)

CategoryT = Literal[
    "canonical",
    "no_binding",
    "phantom",
    "op_method",
    "empty",
    "nonadaptable",
    "envelope_in_core",
]

_BASELINE_HEADER = '''# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""FROZEN canonical handler-shape ratchet baseline — OMN-14355.

Generated by ``scripts/ci/canonical_handler_shape.py --update``. Do not edit by hand.

``NON_CANONICAL`` is the frozen set of nodes whose contract-declared handler is not
the canonical typed-payload shape (definition B). It is monotonically
NON-INCREASING: it may only shrink. A node leaves this set (flips canonical) ONLY
with a committed adequacy receipt under ``scripts/ci/adequacy_receipts/`` — a shape
flip alone is not proof of equivalence (the OMN-14208 trap). A NEW non-canonical
node, or growth of this set, HARD-FAILS CI + pre-commit. Retirement mechanism = the
RSD canonical rewrite regenerating these handlers, each with an adequacy receipt.
"""
'''


# --------------------------------------------------------------------------- #
# Typed finding model (rule #5: emit a typed finding, not prose)
# --------------------------------------------------------------------------- #


class ModelHandlerShapeFinding(BaseModel):
    """A single node's handler-shape classification result."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    node_id: str
    category: CategoryT
    is_canonical: bool
    handler_module: str | None = None
    detail: str | None = None


# --------------------------------------------------------------------------- #
# AST classification
# --------------------------------------------------------------------------- #


def _module_to_files(module: str) -> list[Path]:
    """Candidate source files for a dotted handler module (module or package)."""
    rel = module.replace(".", "/")
    files: list[Path] = []
    exact = SRC_ROOT / f"{rel}.py"
    if exact.exists():
        files.append(exact)
    pdir = SRC_ROOT / rel
    if pdir.is_dir():
        files.extend(sorted(pdir.glob("*.py")))
        files.extend(sorted(pdir.glob("handlers/*.py")))
    # de-dupe, push __init__ last so a real handler module wins
    uniq: list[Path] = []
    for f in files:
        if f not in uniq:
            uniq.append(f)
    uniq.sort(key=lambda f: (f.name == "__init__.py", str(f)))
    return uniq


def _node_package(contract_path: Path) -> str:
    """Dotted package for the node dir holding ``contract.yaml``."""
    rel = contract_path.parent.relative_to(SRC_ROOT)
    return ".".join(rel.parts)


def _contract_bindings(data: dict[str, object]) -> list[tuple[str, str | None]]:
    """Return declared (module, class_or_None) handler bindings, primary first."""
    out: list[tuple[str, str | None]] = []
    handler = data.get("handler")
    if isinstance(handler, dict) and handler.get("module"):
        out.append((str(handler["module"]), handler.get("class")))
    routing = data.get("handler_routing")
    if isinstance(routing, dict):
        default = routing.get("default_handler")
        if isinstance(default, str) and default:
            # form "handler:ClassName" | "module.path:ClassName" | "ClassName"
            left, _, right = default.partition(":")
            cls = right or left
            module = left if ("." in left and right) else None
            out.append((module or "", cls or None))
        for entry in routing.get("handlers", []) or []:
            if isinstance(entry, dict):
                h = entry.get("handler")
                if isinstance(h, dict) and h.get("module"):
                    out.append((str(h["module"]), h.get("class")))
    seen: set[tuple[str, str | None]] = set()
    ded: list[tuple[str, str | None]] = []
    for m, c in out:
        if (m, c) not in seen:
            seen.add((m, c))
            ded.append((m, c))
    return ded


def _classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [n for n in tree.body if isinstance(n, ast.ClassDef)]


def _handle_method(cls: ast.ClassDef) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for m in cls.body:
        if (
            isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
            and m.name == "handle"
        ):
            return m
    return None


def _operation_methods(cls: ast.ClassDef) -> list[str]:
    out: list[str] = []
    for m in cls.body:
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if m.name.startswith("_") or m.name in (
                "handle",
                "initialize",
                "is_initialized",
            ):
                continue
            pos = [a for a in m.args.args if a.arg != "self"]
            if pos or m.args.kwarg:
                out.append(m.name)
    return out


def _ann_str(node: ast.expr | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - defensive
        return ""


def _handle_is_adaptable(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[bool, str]:
    """Definition-B adaptability of a ``handle`` method's signature."""
    args = fn.args
    if args.kwarg is not None:
        return True, "kwargs"
    pos = [a for a in args.args if a.arg != "self"]
    pos = [
        a
        for a in pos
        if a.arg  # positional-or-keyword names
    ]
    if len(pos) == 0:
        return True, "zeroarg"
    if len(pos) == 1:
        name = pos[0].arg
        ann = _ann_str(pos[0].annotation)
        if name in MAGIC_PARAM_NAMES:
            return True, f"magic:{name}"
        looks_model = (
            ann
            and ann not in ("dict", "object", "Any", "None")
            and "dict" not in ann
            and "list" not in ann
            and (
                ann.startswith("Model")
                or "Model" in ann
                or ann.endswith(("Command", "Request", "Event", "Input"))
            )
        )
        if looks_model:
            return True, f"model:{ann}"
        return False, f"nonadaptable-single:{name}:{ann or '<untyped>'}"
    return False, f"multi-positional:{[a.arg for a in pos]}"


def _follow_reexport(
    parsed: list[tuple[Path, ast.Module]], cls_name: str
) -> tuple[
    ast.FunctionDef | ast.AsyncFunctionDef | None, ast.ClassDef | None, Path | None
]:
    """Resolve a class re-exported via ``from <mod> import <Real> as <cls_name>``.

    Core nodes commonly re-export the concrete handler under the contract's class
    name (e.g. ``handler.py`` re-exports ``HandlerBackendSecretDisciplineCompute``
    as ``NodeBackendSecretDisciplineCompute``). Follow that import to the defining
    module so the shape is classified on the real class, not marked phantom.
    """
    # Resolve a module-level assignment alias first
    # (``NodeX = HandlerX``), so the import-follow targets the real class name.
    effective = cls_name
    for _f, tree in parsed:
        for stmt in tree.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == cls_name
                and isinstance(stmt.value, ast.Name)
            ):
                effective = stmt.value.id
    for _f, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            for alias in node.names:
                if (alias.asname or alias.name) == effective:
                    for target in _module_to_files(node.module):
                        try:
                            t2 = ast.parse(target.read_text(encoding="utf-8"))
                        except (OSError, SyntaxError):
                            continue
                        for c in _classes(t2):
                            if c.name == alias.name:
                                return _handle_method(c), c, target
    return None, None, None


def _resolve_handler(
    files: list[Path], cls_name: str | None
) -> tuple[
    ast.FunctionDef | ast.AsyncFunctionDef | None, ast.ClassDef | None, Path | None
]:
    """Find (handle_fn, class, file) for a binding, preferring the named class."""
    parsed: list[tuple[Path, ast.Module]] = []
    for f in files:
        try:
            parsed.append((f, ast.parse(f.read_text(encoding="utf-8"))))
        except (OSError, SyntaxError):
            continue
    # named class with a handle
    if cls_name:
        for f, tree in parsed:
            for c in _classes(tree):
                if c.name == cls_name:
                    fn = _handle_method(c)
                    if fn or _operation_methods(c):
                        return fn, c, f
    # any class with a handle
    for f, tree in parsed:
        for c in _classes(tree):
            fn = _handle_method(c)
            if fn is not None:
                return fn, c, f
    # named class re-exported from another module (follow the import)
    if cls_name:
        rfn, rc, rf = _follow_reexport(parsed, cls_name)
        if rc is not None:
            return rfn, rc, rf
        # named class defined locally but without a handle (report op/empty)
        for f, tree in parsed:
            for c in _classes(tree):
                if c.name == cls_name:
                    return None, c, f
    # any Handler*/Node* class
    for f, tree in parsed:
        for c in _classes(tree):
            if c.name.startswith(("Handler", "Node")):
                return None, c, f
    return None, None, None


def classify_node(contract_path: Path) -> ModelHandlerShapeFinding:
    """Classify one node's contract-declared handler shape (definition B)."""
    node_id = _node_package(contract_path)
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category="phantom",
            is_canonical=False,
            detail=f"unparseable contract: {exc}",
        )
    if not isinstance(data, dict):
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category="phantom",
            is_canonical=False,
            detail="contract is not a mapping",
        )
    bindings = _contract_bindings(data)
    node_pkg = _node_package(contract_path)
    if bindings:
        module, cls = bindings[0]
        module = module or node_pkg  # default_handler w/o an explicit module
    else:
        # No explicit binding (e.g. a ``handler_id``-only contract). The runtime
        # resolves the handler class from the node package by convention, so fall
        # back to the node package's own ``handler.py`` before declaring no_binding.
        module, cls = node_pkg, None
    files = _module_to_files(module)
    fn, cdef, path = _resolve_handler(files, cls)
    if cdef is None:
        # Nothing resolvable in the declared module nor the node package.
        cat_missing: CategoryT = "no_binding" if not bindings else "phantom"
        detail = (
            "contract declares no handler"
            if not bindings
            else f"class {cls or '<any>'} not found"
        )
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category=cat_missing,
            is_canonical=False,
            handler_module=module,
            detail=detail,
        )
    if fn is None:
        opm = _operation_methods(cdef)
        cat_nohandle: CategoryT = "op_method" if opm else "empty"
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category=cat_nohandle,
            is_canonical=False,
            handler_module=module,
            detail=(
                f"no handle(); op-methods={opm[:4]}"
                if opm
                else "no handle() and no methods"
            ),
        )
    adaptable, reason = _handle_is_adaptable(fn)
    if not adaptable:
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category="nonadaptable",
            is_canonical=False,
            handler_module=module,
            detail=reason,
        )
    # C-core: the resolved handler module must not reference the envelope type.
    mod_text = path.read_text(encoding="utf-8") if path and path.exists() else ""
    if "ModelEventEnvelope" in mod_text:
        return ModelHandlerShapeFinding(
            node_id=node_id,
            category="envelope_in_core",
            is_canonical=False,
            handler_module=module,
            detail="core references ModelEventEnvelope (fails C-core)",
        )
    return ModelHandlerShapeFinding(
        node_id=node_id,
        category="canonical",
        is_canonical=True,
        handler_module=module,
        detail=reason,
    )


def classify_all() -> list[ModelHandlerShapeFinding]:
    findings = [classify_node(cy) for cy in sorted(SRC_ROOT.glob(NODES_GLOB))]
    return sorted(findings, key=lambda f: f.node_id)


def current_non_canonical(findings: list[ModelHandlerShapeFinding]) -> list[str]:
    return sorted(f.node_id for f in findings if not f.is_canonical)


# --------------------------------------------------------------------------- #
# Baseline load / write
# --------------------------------------------------------------------------- #


def load_baseline(path: Path = BASELINE_PATH) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Baseline missing at {path}. Generate it with "
            f"`uv run python scripts/ci/canonical_handler_shape.py --update`."
        )
    spec = importlib.util.spec_from_file_location(
        "canonical_handler_shape_baseline", path
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load baseline module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [str(n) for n in getattr(module, "NON_CANONICAL", ())]


def _render_tuple(items: list[str]) -> str:
    if not items:
        return "()"
    return "(\n" + "".join(f'    "{i}",\n' for i in items) + ")"


def write_baseline(non_canonical: list[str], path: Path = BASELINE_PATH) -> None:
    body = (
        _BASELINE_HEADER
        + "\nNON_CANONICAL: tuple[str, ...] = "
        + _render_tuple(sorted(non_canonical))
        + "\n"
    )
    path.write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Package scoping (OMN-14368 mechanical-wave fan-out)
# --------------------------------------------------------------------------- #
#
# The classifier and its baseline were hardcoded to omnibase_core (OMN-14355's
# canary scope was intentionally core-only). The mechanical-wave rewrite needs
# to observe a canonical-shape flip in omnimarket/omnibase_infra too, so the
# scan target is parameterized. ``_resolve_scope`` is a pure function (no
# global mutation) so it is directly unit-testable; only ``main()`` applies
# the result to the module globals that ``classify_node`` et al. read.


def _resolve_scope(
    package: str,
    src_root: Path | None,
    nodes_glob: str | None,
    baseline: Path | None,
    receipts_dir: Path | None,
) -> tuple[Path, str, Path, Path]:
    """Compute ``(src_root, nodes_glob, baseline_path, receipts_dir)`` for a scope.

    Every argument defaults to the omnibase_core value already in effect on the
    module (``SRC_ROOT``/``BASELINE_PATH``/``RECEIPTS_DIR``), so calling this
    with ``package="omnibase_core"`` and all other args ``None`` reproduces
    today's constants exactly. A non-default ``package`` with no explicit
    ``--baseline``/``--receipts-dir`` gets a package-suffixed path beside this
    script rather than silently clobbering omnibase_core's own committed
    baseline/receipts.
    """
    resolved_src_root = src_root if src_root is not None else SRC_ROOT
    resolved_glob = nodes_glob or f"{package}/**/nodes/**/contract.yaml"
    if baseline is not None:
        resolved_baseline = baseline
    elif package == "omnibase_core":
        resolved_baseline = BASELINE_PATH
    else:
        resolved_baseline = Path(__file__).with_name(
            f"canonical_handler_shape_baseline_{package}.py"
        )
    if receipts_dir is not None:
        resolved_receipts = receipts_dir
    elif package == "omnibase_core":
        resolved_receipts = RECEIPTS_DIR
    else:
        resolved_receipts = Path(__file__).with_name(f"adequacy_receipts_{package}")
    return resolved_src_root, resolved_glob, resolved_baseline, resolved_receipts


# --------------------------------------------------------------------------- #
# Adequacy + equivalence gated flip verification (RECOMPUTE, do not trust)
# --------------------------------------------------------------------------- #
#
# A baselined node may flip non-canonical -> canonical ONLY with all three proofs:
#   1. shape-canonical (the classifier says so);
#   2. an adequacy receipt whose verdict the gate RE-DERIVES from raw numbers
#      (a persisted receipt can lie about its self-asserted booleans — verify-1705
#      forged pct=10/target=80/meets_target=True; the gate must not trust the flag);
#   3. a GREEN equivalence-replay artifact bound to the SAME selected input set
#      (coverage != equivalence; a receipt without a passing regen-vs-legacy replay
#      never flips — the OMN-14208-at-scale trap).
# The receipt is untrusted input carrying raw measurements; the gate derives the
# verdict. This decouples the gate from the (currently unmerged) adequacy_receipt
# module — it reads the raw JSON directly.

EXPECTED_RECEIPT_SCHEMA = "adequacy_receipt.v1"
EQUIVALENCE_SUFFIX = ".equivalence.json"


def _resolve_module_file(module: str) -> Path | None:
    candidate = SRC_ROOT / (module.replace(".", "/") + ".py")
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


def verify_adequacy_receipt(
    node_id: str, handler_module: str | None
) -> tuple[bool, str, list[str]]:
    """Re-derive the adequacy verdict from the receipt's RAW numbers.

    Returns ``(ok, reason, selected_input_hashes)``. Ignores the receipt's
    self-asserted ``meets_target``; recomputes ``pct >= target``; recomputes the
    handler-module sha256 live and rejects a stale receipt.
    """
    receipt_path = RECEIPTS_DIR / f"{node_id}.json"
    if not receipt_path.exists():
        return (
            False,
            f"no adequacy receipt at {receipt_path.relative_to(REPO_ROOT)}",
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
        pct = float(raw["branch_coverage_pct"])  # type: ignore[arg-type]
        target = float(raw.get("coverage_target", 80.0))  # type: ignore[arg-type]
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
    art_path = RECEIPTS_DIR / f"{node_id}{EQUIVALENCE_SUFFIX}"
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


def verify_flip_receipt(node_id: str, handler_module: str | None) -> tuple[bool, str]:
    """Return (ok, reason) for a non-canonical -> canonical baseline flip.

    Requires BOTH an adequacy receipt (re-derived verdict) AND a green
    equivalence replay bound to the SAME selected input set. Fail-closed.
    """
    ok_a, reason_a, sel_receipt = verify_adequacy_receipt(node_id, handler_module)
    if not ok_a:
        return False, f"adequacy: {reason_a}"
    ok_e, reason_e, sel_equiv = verify_equivalence_replay(node_id)
    if not ok_e:
        return False, f"equivalence: {reason_e}"
    # Bind coverage to equivalence: both must reference the same input set, else a
    # coverage-adequate golden could be replayed against a different (easier) set.
    if set(sel_receipt) != set(sel_equiv):
        return (
            False,
            "PAIR_INCOMPATIBLE: receipt/equivalence selected_input_hashes differ",
        )
    return True, f"{reason_a}+{reason_e}"


# --------------------------------------------------------------------------- #
# Enforcement
# --------------------------------------------------------------------------- #


class RatchetResult(BaseModel):
    """Outcome of a ratchet check."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    new_non_canonical: tuple[str, ...]
    unproven_flips: tuple[str, ...]
    warn_baselined: tuple[str, ...]
    proven_flips: tuple[str, ...]

    @property
    def failed(self) -> bool:
        return bool(self.new_non_canonical or self.unproven_flips)


def evaluate(
    findings: list[ModelHandlerShapeFinding], baseline: list[str]
) -> RatchetResult:
    baseline_set = set(baseline)
    by_id = {f.node_id: f for f in findings}
    current_nc = set(current_non_canonical(findings))

    # NEW non-canonical node not in the baseline -> HARD-FAIL.
    new_nc = sorted(current_nc - baseline_set)

    # Baselined nodes still non-canonical -> WARN (known debt).
    warn = sorted(current_nc & baseline_set)

    # Baselined nodes that are now canonical -> a flip; require an adequacy receipt.
    proven: list[str] = []
    unproven: list[str] = []
    for node_id in sorted(baseline_set - current_nc):
        finding = by_id.get(node_id)
        if finding is None:
            continue  # node deleted; --update will drop it
        ok, _ = verify_flip_receipt(node_id, finding.handler_module)
        (proven if ok else unproven).append(node_id)

    return RatchetResult(
        new_non_canonical=tuple(new_nc),
        unproven_flips=tuple(unproven),
        warn_baselined=tuple(warn),
        proven_flips=tuple(proven),
    )


def _format_failure(
    result: RatchetResult, findings: list[ModelHandlerShapeFinding]
) -> str:
    by_id = {f.node_id: f for f in findings}
    lines = [
        "Canonical handler-shape ratchet FAILED (OMN-14355).",
        "",
    ]
    if result.new_non_canonical:
        lines.append("  NEW non-canonical node(s) — new nodes must be born canonical")
        lines.append(
            "  (definition B: typed-payload handle(request)->response, no envelope in core):"
        )
        for node_id in result.new_non_canonical:
            f = by_id.get(node_id)
            lines.append(
                f"    + {node_id}  [{f.category if f else '?'}] {f.detail if f else ''}"
            )
    if result.unproven_flips:
        lines.append("")
        lines.append(
            "  Baselined node(s) flipped to canonical shape WITHOUT an adequacy receipt"
        )
        lines.append(
            "  — a shape flip is not proof of equivalence (OMN-14208 trap). Provide a"
        )
        lines.append(
            "  ModelAdequacyReceipt under scripts/ci/adequacy_receipts/<node_id>.json:"
        )
        for node_id in result.unproven_flips:
            f = by_id.get(node_id)
            _, reason = verify_flip_receipt(node_id, f.handler_module if f else None)
            lines.append(f"    + {node_id}  ({reason})")
    lines.append("")
    lines.append(
        "Fix the node, or regenerate the baseline only for receipt-proven flips:"
    )
    lines.append("  uv run python scripts/ci/canonical_handler_shape.py --update")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Change-aware scoping (default hot path = O(changed nodes), not O(554))
# --------------------------------------------------------------------------- #
#
# The full 554-node scan is a tax on every PR/pre-commit. The ratchet holds on a
# diff-scoped run entirely from the diff + committed baseline: a NEW non-canonical
# node in the diff hard-fails; a baselined node modified-to-canonical must flip
# (receipt); a baselined node modified-but-still-non-canonical warns. Untouched
# nodes cannot have changed classification unless a module the classifier resolves
# THROUGH changed — that triggers a FAIL-CLOSED escalation to a full scan.

ADJACENCY_PATH = Path(__file__).with_name("test_selection_adjacency.yaml")

# Modules the classifier resolves handlers THROUGH (envelope adapter / mixin / the
# gate + baseline itself). A change to any of these can flip untouched nodes'
# classification, so the gate escalates to a full scan (fail-closed).
GATE_RESOLUTION_MODULES: tuple[str, ...] = (
    "runtime/runtime_local_adapter",
    "runtime/runtime_local",
    "mixins/mixin_envelope_extraction",
)
GATE_SELF_PATHS: tuple[str, ...] = (
    "scripts/ci/canonical_handler_shape.py",
    "scripts/ci/canonical_handler_shape_baseline.py",
)


def _load_shared_modules() -> frozenset[str]:
    """Reuse the smart-test selector's shared-module list (single source of truth)."""
    if not ADJACENCY_PATH.exists():
        return frozenset()
    try:
        data = yaml.safe_load(ADJACENCY_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return frozenset()
    mods = data.get("shared_modules", []) if isinstance(data, dict) else []
    return frozenset(str(m) for m in mods)


def _git_changed_files(base_ref: str) -> list[str] | None:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _touched_node_ids(changed_files: list[str]) -> set[str]:
    """Map changed repo-relative paths to the node packages that own them."""
    nodes: set[str] = set()
    for rel in changed_files:
        if "/nodes/" not in rel or not rel.startswith("src/"):
            continue
        before, _, after = rel.partition("/nodes/")
        node_dir = after.split("/", 1)[0]
        if not node_dir.startswith("node_"):
            continue
        pkg_root = before[len("src/") :].replace("/", ".")
        nodes.add(f"{pkg_root}.nodes.{node_dir}")
    return nodes


def _escalation_reason(changed_files: list[str]) -> str | None:
    """Return a full-scan escalation reason, or None to stay diff-scoped."""
    shared = _load_shared_modules()
    prefix = f"src/{PACKAGE}/"
    for rel in changed_files:
        if rel in GATE_SELF_PATHS or rel.startswith("scripts/ci/adequacy_receipts/"):
            return f"gate/baseline/receipt changed ({rel})"
        if not rel.startswith(prefix) or not rel.endswith(".py"):
            continue
        module_path = rel[len(prefix) : -len(".py")]
        if any(
            module_path == m or module_path.startswith(m)
            for m in GATE_RESOLUTION_MODULES
        ):
            return f"classifier-resolution module changed ({module_path})"
        top = module_path.split("/", 1)[0]
        if top in shared:
            return f"shared module changed ({top})"
    return None


def classify_node_ids(node_ids: set[str]) -> list[ModelHandlerShapeFinding]:
    """Classify only the given node packages (diff-scoped hot path)."""
    findings: list[ModelHandlerShapeFinding] = []
    for node_id in sorted(node_ids):
        contract = SRC_ROOT / (node_id.replace(".", "/")) / "contract.yaml"
        if contract.exists():
            findings.append(classify_node(contract))
    return findings


def _report(
    result: RatchetResult,
    findings: list[ModelHandlerShapeFinding],
    scope_label: str,
) -> int:
    if result.warn_baselined:
        print(
            f"Canonical handler-shape ratchet WARNING (OMN-14355, {scope_label}) — "
            f"non-blocking: {len(result.warn_baselined)} baselined non-canonical "
            f"node(s) (known debt; retire via the RSD rewrite + adequacy receipt).",
            file=sys.stderr,
        )
    if result.proven_flips:
        print(
            f"  {len(result.proven_flips)} node(s) flipped canonical WITH a valid "
            f"adequacy + equivalence proof — regenerate the baseline to record: "
            f"uv run python scripts/ci/canonical_handler_shape.py --update",
            file=sys.stderr,
        )
    if result.failed:
        print(_format_failure(result, findings), file=sys.stderr)
        return 1
    print(
        f"Canonical handler-shape ratchet OK ({scope_label}) — "
        f"checked {len(findings)} node(s); "
        f"new=0 unproven_flips=0 warn={len(result.warn_baselined)}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Canonical handler-shape ratchet (OMN-14355)."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Regenerate the frozen baseline from a FULL scan (DOWNWARD re-freeze; "
        "new canonical nodes must carry an adequacy + equivalence proof).",
    )
    parser.add_argument(
        "--scope",
        choices=("changed", "full"),
        default="changed",
        help="changed (default): only nodes in the diff, O(changed). "
        "full: whole repository (baseline gen, periodic audit, main boundary).",
    )
    parser.add_argument("--full", action="store_true", help="Alias for --scope full.")
    parser.add_argument(
        "--base-ref",
        default="origin/dev",
        help="Diff base for --scope changed when no files are passed (CI path).",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Baseline module path. Defaults to omnibase_core's committed "
        "baseline, or canonical_handler_shape_baseline_<package>.py beside "
        "this script when --package overrides the target (OMN-14368).",
    )
    parser.add_argument(
        "--package",
        default=os.environ.get("ONEX_CANON_SHAPE_PACKAGE", "omnibase_core"),
        help="Target package to classify (OMN-14368 fan-out). Defaults to "
        "omnibase_core so core CI/pre-commit behavior is unchanged; pass e.g. "
        "'omnimarket' with --src-root to scan a sibling repo.",
    )
    parser.add_argument(
        "--src-root",
        type=Path,
        default=(
            Path(os.environ["ONEX_CANON_SHAPE_SRC_ROOT"])
            if "ONEX_CANON_SHAPE_SRC_ROOT" in os.environ
            else None
        ),
        help="Source root containing --package's node tree (defaults to this "
        "repo's own src/). Pass a sibling repo's src/ dir, e.g. "
        "../omnimarket/src, to scan a different package.",
    )
    parser.add_argument(
        "--nodes-glob",
        default=None,
        help="Override the contract.yaml glob (default: "
        "'<package>/**/nodes/**/contract.yaml', relative to --src-root).",
    )
    parser.add_argument(
        "--receipts-dir",
        type=Path,
        default=None,
        help="Override the adequacy-receipts directory for --package.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a FULL-scan classification as JSON and exit 0.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit changed files (pre-commit passes staged filenames here).",
    )
    args = parser.parse_args(argv)

    # Apply the resolved scope to the module globals every other function in
    # this file reads (classify_node, _escalation_reason, verify_*, ...).
    # Pure computation happens in _resolve_scope; only main() mutates state,
    # once per process, so unit tests calling these functions directly never
    # observe a scope left over from a prior test.
    global PACKAGE, SRC_ROOT, NODES_GLOB, BASELINE_PATH, RECEIPTS_DIR
    PACKAGE = args.package
    SRC_ROOT, NODES_GLOB, BASELINE_PATH, RECEIPTS_DIR = _resolve_scope(
        args.package, args.src_root, args.nodes_glob, args.baseline, args.receipts_dir
    )

    if args.json:
        import json

        print(json.dumps([f.model_dump() for f in classify_all()], indent=2))
        return 0

    if args.update:
        findings = classify_all()
        non_canonical = current_non_canonical(findings)
        write_baseline(non_canonical, BASELINE_PATH)
        print(
            f"Regenerated {BASELINE_PATH.name} (full scan, package={PACKAGE}) — "
            f"{len(findings)} nodes, "
            f"canonical={len(findings) - len(non_canonical)}, "
            f"non_canonical={len(non_canonical)}"
        )
        return 0

    baseline = load_baseline(BASELINE_PATH)

    full = args.full or args.scope == "full"
    scope_label = "full"
    if not full:
        # Derive the changed-file set: explicit args (pre-commit) else git diff (CI).
        changed = args.files if args.files else _git_changed_files(args.base_ref)
        if changed is None:
            # fail-closed: cannot compute the diff -> full scan (fallthrough below)
            scope_label = "full (diff unavailable — fail-closed)"
        else:
            reason = _escalation_reason(changed)
            if reason is not None:
                scope_label = f"full (escalated: {reason})"
            else:
                node_ids = _touched_node_ids(changed)
                if not node_ids:
                    print(
                        "Canonical handler-shape ratchet OK (changed) — "
                        "no node files in the diff."
                    )
                    return 0
                findings = classify_node_ids(node_ids)
                return _report(evaluate(findings, baseline), findings, "changed")

    findings = classify_all()
    return _report(evaluate(findings, baseline), findings, scope_label)


if __name__ == "__main__":
    raise SystemExit(main())
