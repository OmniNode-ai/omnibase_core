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
  ``handle`` may be inherited: the classifier walks the MRO and checks the
  defining ancestor's module for the envelope reference.

Everything else is non-canonical: no handler binding, an unresolved
(phantom) binding, a class with only operation-named methods (no ``handle``),
an empty handler class, a non-adaptable ``handle`` (raw ``dict``/multi-positional),
or a core that reaches into the envelope directly (``envelope_in_core``).

Enforcement (mirrors the import-layering ratchet, OMN-14340):

* A package that still carries non-canonical debt has a committed baseline
  (``canonical_handler_shape_baseline.py`` in that repo, generated) that freezes
  its non-canonical node set as a plain tuple. A package with no baseline file
  has no grandfathered node, so the gate is a plain check there: every
  non-canonical node hard-fails. omnibase_core's own baseline emptied and was
  deleted (OMN-20559), and ``--update`` deletes a baseline that empties.
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
* A node that had NO legacy handler at the merge base (OMN-20298) has nothing to
  replay or keep byte-identical; its adequacy receipt records
  ``legacy_handler: "none"`` and the gate re-derives that from git (node file
  listing at ``base_ref``) and EXECUTES the new handler's own contract tests. A
  node that had a handler cannot take that path.

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
from collections import deque
from collections.abc import Callable
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


def _base_class_names(cls: ast.ClassDef) -> list[str]:
    """Extract simple and qualified base names in declaration order."""
    return [
        base.id if isinstance(base, ast.Name) else base.attr
        for base in cls.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    ]


def _resolve_class_by_name(
    name: str,
    parsed: list[tuple[Path, ast.Module]],
    seen_files: set[Path],
) -> tuple[ast.ClassDef | None, Path | None, list[tuple[Path, ast.Module]]]:
    """Find a local or imported base, retaining newly parsed source files."""
    for path, tree in parsed:
        for cls in _classes(tree):
            if cls.name == name:
                return cls, path, parsed
    for path, tree in list(parsed):
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            module = node.module
            if node.level:
                try:
                    parts = path.parent.relative_to(SRC_ROOT).parts
                except ValueError:
                    continue
                if node.level > len(parts):
                    continue
                module = ".".join((*parts[: len(parts) - node.level + 1], module))
            for alias in node.names:
                if (alias.asname or alias.name) != name:
                    continue
                for target in _module_to_files(module):
                    if target not in seen_files:
                        seen_files.add(target)
                        try:
                            imported = ast.parse(target.read_text(encoding="utf-8"))
                        except (OSError, SyntaxError):
                            continue
                        parsed.append((target, imported))
                    for cached_path, imported in parsed:
                        if cached_path != target:
                            continue
                        for cls in _classes(imported):
                            if cls.name == alias.name:
                                return cls, target, parsed
    return None, None, parsed


def _handle_via_mro(
    cls: ast.ClassDef,
    parsed: list[tuple[Path, ast.Module]],
    *,
    max_depth: int = 8,
) -> tuple[
    ast.FunctionDef | ast.AsyncFunctionDef | None, ast.ClassDef | None, Path | None
]:
    """Search ancestors breadth-first, bounded by depth and visited class names."""
    parsed = list(parsed)
    seen_files = {path for path, _tree in parsed}
    visited = {cls.name}
    pending = deque((name, 1) for name in _base_class_names(cls))
    while pending:
        name, depth = pending.popleft()
        if depth > max_depth or name in visited:
            continue
        visited.add(name)
        base, path, parsed = _resolve_class_by_name(name, parsed, seen_files)
        if base is None:
            continue
        fn = _handle_method(base)
        if fn is not None:
            return fn, base, path
        pending.extend((name, depth + 1) for name in _base_class_names(base))
    return None, None, None


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
                                fn = _handle_method(c)
                                if fn is None:
                                    inherited = _handle_via_mro(
                                        c, [(target, t2), *parsed]
                                    )
                                    if inherited[0] is not None:
                                        return inherited
                                return fn, c, target
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
                    if fn is None:
                        inherited = _handle_via_mro(c, parsed)
                        if inherited[0] is not None:
                            return inherited
                    if fn or _operation_methods(c):
                        return fn, c, f
    # any class with a handle
    for f, tree in parsed:
        for c in _classes(tree):
            fn = _handle_method(c)
            if fn is not None:
                return fn, c, f
            inherited = _handle_via_mro(c, parsed)
            if inherited[0] is not None:
                return inherited
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
                inherited = _handle_via_mro(c, parsed)
                if inherited[0] is not None:
                    return inherited
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
    """Return the grandfathered non-canonical node ids.

    No baseline file means no grandfathered node: the gate is a plain check and
    every non-canonical node fails (OMN-20559). That is the fail-closed reading,
    since an absent file can only make the gate stricter.
    """
    if not path.exists():
        return []
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
    """Write the frozen baseline, or delete it once it is empty (OMN-20559).

    An empty baseline is dead weight: ``load_baseline`` already reads an absent
    file as "nothing grandfathered", so the file goes and the gate stays a plain
    check rather than carrying an empty exception list.
    """
    if not non_canonical:
        path.unlink(missing_ok=True)
        return
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
# Sanctioned HAND-FLIP proof (OMN-14781): the legitimate proof for a def-B
# conversion done BY HAND (not RSD-regenerated), where a regen-vs-legacy
# equivalence-replay artifact cannot honestly exist. Proof = adequacy receipt +
# gate-RE-DERIVED verbatim-preservation (the named business-logic symbols are
# byte-identical between git-BASE and HEAD, so the flip only moved the envelope/
# adapter boundary) + green parity tests bound to the SAME selected input set.
HANDFLIP_SUFFIX = ".handflip.json"
EXPECTED_HANDFLIP_SCHEMA = "handflip_proof.v1"
# Sanctioned NO-LEGACY flip (OMN-20298): a baselined node that never had a handler
# (no binding, a phantom binding, or only non-handler code such as a consumer
# script) has nothing to keep byte-identical and nothing pure to replay. Its proof
# is the adequacy receipt itself, carrying ``legacy_handler: "none"``: the gate
# re-derives from git that no handler existed at the receipt's ``base_ref`` (and at
# the live merge base), byte-compares the recorded node file listing against
# ``git ls-tree`` at that commit, and EXECUTES the new handler's own contract tests
# green on HEAD. A node that HAD a handler can never take this path.
EXPECTED_NO_LEGACY_SCHEMA = "adequacy_receipt.no_legacy.v1"
LEGACY_HANDLER_NONE = "none"

#: Base ref the no-legacy path re-derives the live merge base against. ``main()``
#: sets it from ``--base-ref``; ``verify_flip_bundle`` sets it from its own.
BASE_REF = "origin/dev"


# --------------------------------------------------------------------------- #
# Executed-parity seam (OMN-15340)
# --------------------------------------------------------------------------- #
#
# Until OMN-15340 the hand-flip path credited ``parity.status == "pass"`` — a string
# the flip author wrote — and merely COUNTED ``parity.test_ids``. Nothing executed
# them, so "the parity tests are green" was an assertion about a file, not about the
# code. The status string is no longer evidence in the positive direction: a claimed
# ``pass`` must be EXECUTED (green on HEAD) or the proof is REJECTED. A self-declared
# non-``pass`` stays a hard fail — a confession is trustworthy only in the negative
# direction.
#
# The executor is injected so tests can state exactly what they are proving and so
# the pre-PR seam gate (``verify_flip_bundle``) can reuse one execution. The default
# executor really runs pytest (``scripts/ci/parity_replay.py``), imported lazily to
# keep this module's import cost and dependency surface unchanged for every caller
# that never touches a hand-flip receipt.


class ModelParityVerdict(BaseModel):
    """An EXECUTED verdict over a hand-flip receipt's declared parity test ids."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    executed: bool
    green: bool
    detail: str


#: ``(node_id, test_ids) -> ModelParityVerdict``.
ParityExecutor = Callable[[str, tuple[str, ...]], ModelParityVerdict]

#: Memoized per-process: assertion 2 (via ``verify_flip_receipt``) and any later
#: caller must not pay for the same pytest run twice within one gate invocation. The
#: key carries the active ``SRC_ROOT`` because the same node_id + test ids under a
#: different fan-out scope is a DIFFERENT tree and must be re-executed.
_PARITY_CACHE: dict[tuple[str, str, tuple[str, ...]], ModelParityVerdict] = {}


def default_parity_executor(
    node_id: str, test_ids: tuple[str, ...]
) -> ModelParityVerdict:
    """Execute the declared parity ids against the working tree; all must PASS."""
    cache_key = (str(SRC_ROOT), node_id, test_ids)
    cached = _PARITY_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        try:  # pragma: no cover - import shim (mirrors this module's own dual import)
            from scripts.ci import parity_replay
        except ImportError:  # pragma: no cover - script-dir invocation
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import parity_replay  # type: ignore[import-not-found, no-redef]
    except ImportError as exc:  # pragma: no cover - defensive, fail-closed
        return ModelParityVerdict(
            executed=False, green=False, detail=f"parity engine unavailable: {exc}"
        )
    repo_root = _git_repo_root(SRC_ROOT)
    if repo_root is None:
        verdict = ModelParityVerdict(
            executed=False,
            green=False,
            detail=f"cannot resolve a git repo root from {SRC_ROOT} to run parity tests",
        )
        _PARITY_CACHE[cache_key] = verdict
        return verdict
    run = parity_replay.run_on_head(repo_root, SRC_ROOT, test_ids)
    if not run.executed:
        verdict = ModelParityVerdict(executed=False, green=False, detail=run.detail)
    elif run.all_passed:
        verdict = ModelParityVerdict(
            executed=True,
            green=True,
            detail=f"{len(run.results)} declared parity id(s) executed GREEN on HEAD",
        )
    else:
        offenders = "; ".join(
            f"{r.test_id} -> {r.outcome.value}"
            for r in run.results
            if r.outcome.value != "passed"
        )
        verdict = ModelParityVerdict(
            executed=True,
            green=False,
            detail=f"declared parity id(s) NOT green on HEAD: {offenders}",
        )
    _PARITY_CACHE[cache_key] = verdict
    return verdict


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


def _display_path(path: Path) -> str:
    """Best-effort repo-relative display for a receipt/artifact path.

    OMN-14781: under fan-out (``--package``/``--receipts-dir`` pointing at a
    SIBLING repo, e.g. omnimarket), ``RECEIPTS_DIR`` lives outside this
    classifier's own ``REPO_ROOT`` (which always resolves to omnibase_core). A
    naive ``path.relative_to(REPO_ROOT)`` then raises ``ValueError`` and crashes
    the whole gate mid-classification. Fall back to the absolute/original path
    rather than raising — the message is cosmetic, the verdict is not.
    """
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- #
# git-BASE baseline resolution (OMN-14781: close the stateless in-PR-edit hole)
# --------------------------------------------------------------------------- #
#
# ``evaluate`` used to compare the live scan ONLY against the *post-edit committed*
# baseline. That is stateless: a PR that removes a node from ``NON_CANONICAL`` in
# the SAME commit that flips its shape evades the flip-proof entirely (the node is
# absent from both the working baseline and the current non-canonical set, so it is
# neither a NEW non-canonical node nor a detected flip). Comparing the working-tree
# baseline against the git-BASE (origin/dev) baseline surfaces every in-PR removal
# as a CLAIMED FLIP that must carry the 3-part proof.


def _git_repo_root(path: Path) -> Path | None:
    """Toplevel of the git repo that owns ``path`` (works cross-repo for fan-out)."""
    import subprocess

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
    """``git show <ref>:<rel_path>`` in ``repo_root``; None if absent/unresolvable."""
    import subprocess

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
    import subprocess

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


def _parse_non_canonical(source: str) -> list[str]:
    """Extract the ``NON_CANONICAL`` string tuple from baseline source, no exec()."""
    tree = ast.parse(source)
    for node in tree.body:
        target_names: list[str] = []
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_names = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        if "NON_CANONICAL" in target_names and value is not None:
            evaluated = ast.literal_eval(value)
            return [str(n) for n in evaluated]
    return []


def load_base_baseline(baseline_path: Path, base_ref: str) -> list[str] | None:
    """Load ``NON_CANONICAL`` as it existed at ``base_ref`` (the git BASE).

    Returns:
      * the base entries when resolvable;
      * ``[]`` when the baseline file did NOT exist at ``base_ref`` (a brand-new
        baseline file legitimately has no prior entries — nothing to protect);
      * ``None`` when the base cannot be determined at all (no git, unknown ref).
        A ``None`` disables the removal/growth check for that run WITHOUT
        hard-failing — mirrors the existing diff-unavailable tolerance. In CI the
        PR base (origin/dev) is always present, so the check is live there.
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
        # ref exists but file absent at base -> new baseline file, no prior entries.
        return []
    try:
        return _parse_non_canonical(source)
    except (SyntaxError, ValueError):
        return None


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
    """(repo_root, path-relative-to-repo-root) for a dotted module under SRC_ROOT."""
    file_path = SRC_ROOT / (module.replace(".", "/") + ".py")
    repo_root = _git_repo_root(SRC_ROOT if SRC_ROOT.exists() else file_path)
    if repo_root is None:
        return None
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    return repo_root, str(rel).replace(os.sep, "/")


def verify_handflip_proof(
    node_id: str,
    handler_module: str | None,
    *,
    parity_executor: ParityExecutor | None = None,
) -> tuple[bool, str, list[str]]:
    """Sanctioned proof for a HAND-authored def-B flip (no fabricated replay).

    Re-derives verbatim-preservation from git itself — the gate reads the named
    business-logic symbols from the git-BASE legacy module AND the HEAD canonical
    module and requires them byte-identical (post AST-normalization). This cannot
    be faked by writing a JSON file: the symbols must genuinely be unchanged across
    the flip.

    Parity tests attest the behavior the verbatim check cannot cover, and since
    OMN-15340 they are EXECUTED rather than credited from ``parity.status``: the
    declared ids must run GREEN on HEAD through ``parity_executor`` (default:
    ``default_parity_executor``, which really runs pytest). The complementary half —
    that those same ids are RED on the receipt's own ``base_ref``, i.e. that they
    discriminate the flip at all — is assertion 7 of ``verify_flip_bundle``. The
    input-set binding is enforced by ``verify_flip_receipt``.

    Returns ``(ok, reason, selected_input_hashes)``.
    """
    art_path = RECEIPTS_DIR / f"{node_id}{HANDFLIP_SUFFIX}"
    if not art_path.exists():
        return False, "no hand-flip proof artifact", []
    raw = _load_json(art_path)
    if raw is None:
        return False, "hand-flip artifact unparseable", []
    if raw.get("node_id") != node_id:
        return False, "hand-flip artifact node_id mismatch", []
    schema = raw.get("receipt_schema")
    if schema != EXPECTED_HANDFLIP_SCHEMA:
        return False, f"unexpected hand-flip receipt_schema {schema!r}", []

    symbols_raw = raw.get("preserved_symbols")
    symbols = [str(s) for s in symbols_raw] if isinstance(symbols_raw, list) else []
    if not symbols:
        return False, "hand-flip proof declares no preserved_symbols", []

    canonical_module = raw.get("canonical_handler_module") or handler_module
    legacy_module = raw.get("legacy_handler_module")
    base_ref = raw.get("base_ref")
    if not isinstance(canonical_module, str) or not canonical_module:
        return False, "hand-flip proof missing canonical_handler_module", []
    if not isinstance(legacy_module, str) or not legacy_module:
        return False, "hand-flip proof missing legacy_handler_module", []
    if not isinstance(base_ref, str) or not base_ref:
        return False, "hand-flip proof missing base_ref", []

    # HEAD side: live working-tree canonical module.
    head_file = _resolve_module_file(canonical_module)
    if head_file is None:
        return False, f"canonical_handler_module {canonical_module} not resolvable", []
    head_bodies = _extract_symbol_sources(
        head_file.read_text(encoding="utf-8"), symbols
    )
    if head_bodies is None:
        return False, "preserved_symbols not all found in HEAD module", []

    # BASE side: legacy module as of base_ref, read from git (never fabricated).
    rel = _module_repo_rel(legacy_module)
    if rel is None:
        return False, f"legacy_handler_module {legacy_module} path unresolvable", []
    repo_root, rel_path = rel
    if not _git_ref_exists(repo_root, base_ref):
        return False, f"base_ref {base_ref!r} unresolvable for verbatim check", []
    base_source = _git_show(repo_root, base_ref, rel_path)
    if base_source is None:
        return False, f"legacy module absent at {base_ref}:{rel_path}", []
    base_bodies = _extract_symbol_sources(base_source, symbols)
    if base_bodies is None:
        return False, "preserved_symbols not all found in git-BASE legacy module", []

    diverged = sorted(s for s in symbols if head_bodies[s] != base_bodies[s])
    if diverged:
        return (
            False,
            f"verbatim-preservation FAILED — logic changed for {diverged}",
            [],
        )

    parity = raw.get("parity")
    if not isinstance(parity, dict):
        return False, "hand-flip proof missing parity block", []
    if parity.get("status") != "pass":
        # A self-declared failure is a confession — trusted in the negative direction
        # only. A self-declared ``pass`` earns nothing; it must be executed below.
        return False, f"parity tests status={parity.get('status')!r}", []
    test_ids = parity.get("test_ids")
    if not isinstance(test_ids, list) or not test_ids:
        return False, "hand-flip parity block names no test_ids", []

    # OMN-15340: run them or reject them. The recorded ``status`` never survives as
    # evidence on its own.
    executor = (
        parity_executor if parity_executor is not None else default_parity_executor
    )
    verdict = executor(node_id, tuple(str(t) for t in test_ids))
    if not verdict.executed:
        return (
            False,
            f"parity claim UNEXECUTED — a recorded status string is not evidence "
            f"({verdict.detail})",
            [],
        )
    if not verdict.green:
        return False, f"parity tests NOT GREEN when executed: {verdict.detail}", []

    hashes = parity.get("selected_input_hashes")
    selected = [str(h) for h in hashes] if isinstance(hashes, list) else []
    return (
        True,
        f"handflip-verbatim-preserved({len(symbols)} symbol(s))"
        f"+parity-executed-green({len(test_ids)} test id(s))",
        selected,
    )


def _git_ls_tree(repo_root: Path, ref: str, rel_dir: str) -> list[str] | None:
    """Sorted repo-relative file paths under ``rel_dir`` at ``ref``; None on error."""
    import subprocess

    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "ls-tree",
                "-r",
                "--name-only",
                ref,
                "--",
                rel_dir,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def _git_is_ancestor(repo_root: Path, ancestor: str, ref: str = "HEAD") -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", ancestor, ref],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _git_merge_base(repo_root: Path, ref_a: str, ref_b: str = "HEAD") -> str | None:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", ref_a, ref_b],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _git_lines(repo_root: Path, *args: str) -> list[str] | None:
    """Stripped non-empty stdout lines of ``git <args>``; None on any error."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_no_diff(repo_root: Path, *args: str) -> bool:
    """True only when ``git diff --quiet <args>`` reports no difference."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--quiet", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _landed_no_legacy_flip(
    repo_root: Path, live_base: str, base_ref: str, node_id: str, receipt_path: Path
) -> tuple[bool, str]:
    """Whether the live merge base already carries this exact no-legacy flip.

    After a no-legacy flip merges, the live merge base holds the flip's own new
    handler, so the live-base check refuses the receipt on every later run until
    the baseline drops the node, and the change that drops it is refused for the
    same reason. The flip is accepted as landed only when every claim is
    re-derived from git:
      * the receipt was added by a commit ``L`` on the live merge base's history;
      * the node directory and the receipt are unchanged from ``L`` through the
        live merge base to the working tree, with no untracked file in the node
        directory (this run changes nothing the landed flip did not);
      * ``base_ref`` is an ancestor of ``L``, and every commit from ``base_ref``
        to ``L`` that changed the node either had no handler or already held the
        node exactly as ``L`` landed it (the flip's own handler commit).
    A different handler that existed on the base before the receipt landed is
    still refused, and so is any change to the node made after it landed.
    """
    src_rel = _src_rel(repo_root)
    if src_rel is None:
        return False, "SRC_ROOT is outside the git repo"
    try:
        receipt_rel = str(
            receipt_path.resolve().relative_to(repo_root.resolve())
        ).replace(os.sep, "/")
    except ValueError:
        return False, "receipt is outside the git repo"
    node_rel = "/".join(p for p in (src_rel, node_id.replace(".", "/")) if p)

    added = _git_lines(
        repo_root,
        "log",
        "-n1",
        "--diff-filter=A",
        "--format=%H",
        live_base,
        "--",
        receipt_rel,
    )
    if not added:
        return False, "the receipt did not land on the live merge base"
    landed = added[0]
    if not _git_no_diff(repo_root, landed, live_base, "--", node_rel, receipt_rel):
        return False, f"node or receipt changed between {landed[:12]} and the base"
    if not _git_no_diff(repo_root, landed, "--", node_rel, receipt_rel):
        return False, f"node or receipt changed since {landed[:12]} landed"
    untracked = _git_lines(
        repo_root, "ls-files", "--others", "--exclude-standard", "--", node_rel
    )
    if untracked is None or untracked:
        return False, "untracked files in the node directory"
    if not _git_is_ancestor(repo_root, base_ref, landed):
        return False, f"receipt base_ref is not an ancestor of {landed[:12]}"
    landed_tree = _git_lines(repo_root, "rev-parse", f"{landed}:{node_rel}")
    touching = _git_lines(
        repo_root, "rev-list", "--full-history", f"{base_ref}..{landed}", "--", node_rel
    )
    if landed_tree is None or touching is None:
        return False, f"cannot read the node history from base_ref to {landed[:12]}"
    for commit in touching:
        _, evidence = _legacy_handler_evidence(repo_root, commit, node_id)
        if evidence is None:
            continue
        if _git_lines(repo_root, "rev-parse", f"{commit}:{node_rel}") != landed_tree:
            return False, f"before the receipt landed: {evidence}"
    return True, f"flip landed at {landed[:12]} with no other handler before it"


def _src_rel(repo_root: Path) -> str | None:
    """``SRC_ROOT`` relative to ``repo_root`` (posix), or None if outside it."""
    try:
        rel = SRC_ROOT.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    rel_str = str(rel).replace(os.sep, "/")
    return "" if rel_str == "." else rel_str


def _module_rel_candidates(src_rel: str, module: str) -> list[str]:
    stem = module.replace(".", "/")
    prefix = f"{src_rel}/" if src_rel else ""
    return [f"{prefix}{stem}.py", f"{prefix}{stem}/__init__.py"]


def _legacy_handler_evidence(
    repo_root: Path, ref: str, node_id: str
) -> tuple[list[str] | None, str | None]:
    """``(node_files_at_ref, handler_evidence)`` for a node as it was at ``ref``.

    ``handler_evidence`` is None when NO handler existed at ``ref``; otherwise it
    names what the gate found. Fail-closed: anything handler-shaped counts, i.e.
      * a contract binding whose module file existed at ``ref``, or an empty-module
        binding whose class was defined in the node package at ``ref``;
      * a node file named ``handler*.py`` or under a ``handlers/`` directory;
      * a node module defining a ``Handler*`` class or a class with ``handle`` /
        ``handle_async``.
    ``node_files_at_ref`` is None when the listing itself is unreadable.
    """
    src_rel = _src_rel(repo_root)
    if src_rel is None:
        return None, "SRC_ROOT is outside the git repo; cannot read the node at ref"
    node_rel = "/".join(p for p in (src_rel, node_id.replace(".", "/")) if p)
    files = _git_ls_tree(repo_root, ref, node_rel)
    if files is None:
        return None, f"git ls-tree failed for {ref}:{node_rel}"
    if not files:
        return files, f"node directory {node_rel} absent at {ref}"

    node_classes: set[str] = set()
    for rel in files:
        tail = rel[len(node_rel) + 1 :]
        name = tail.rsplit("/", 1)[-1]
        if "/handlers/" in f"/{tail}" or (
            name.startswith("handler") and name.endswith(".py")
        ):
            return files, f"handler file {rel} existed at {ref}"
        if not rel.endswith(".py"):
            continue
        text = _git_show(repo_root, ref, rel)
        if text is None:
            return files, f"cannot read {ref}:{rel}"
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return files, f"{ref}:{rel} unparseable; cannot rule out a handler"
        for c in _classes(tree):
            node_classes.add(c.name)
            if c.name.startswith("Handler"):
                return files, f"class {c.name} in {rel} at {ref}"
            for m in c.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    m.name in ("handle", "handle_async")
                ):
                    return files, f"{c.name}.{m.name} in {rel} at {ref}"

    contract_src = _git_show(repo_root, ref, f"{node_rel}/contract.yaml")
    if contract_src is not None:
        try:
            data = yaml.safe_load(contract_src)
        except yaml.YAMLError:
            return files, f"contract.yaml unparseable at {ref}"
        if isinstance(data, dict):
            for module, cls in _contract_bindings(data):
                if not module:
                    if cls in node_classes:
                        return files, (
                            f"contract bound in-package class {cls!r}, defined at {ref}"
                        )
                    continue
                for cand in _module_rel_candidates(src_rel, module):
                    if _git_show(repo_root, ref, cand) is not None:
                        return files, (
                            f"contract bound handler module {module} and {cand} "
                            f"existed at {ref}"
                        )
    return files, None


def verify_no_legacy_flip(
    node_id: str,
    handler_module: str | None,
    *,
    parity_executor: ParityExecutor | None = None,
) -> tuple[bool, str]:
    """Proof for a flip of a node that had NO legacy handler (OMN-20298).

    The adequacy receipt carries ``legacy_handler: "none"``. Every claim in it is
    re-derived, never trusted:
      * ``base_ref`` resolves and is an ancestor of HEAD;
      * ``base_node_files`` equals ``git ls-tree`` of the node directory at
        ``base_ref`` (the evidence is the listing at that commit);
      * no handler existed at ``base_ref`` NOR at the live merge base of HEAD with
        ``BASE_REF`` (so an older handler-less commit cannot be cited past a handler
        that exists on the base today), unless that handler is this flip's own,
        already landed with no handler before it (``_landed_no_legacy_flip``);
      * the new handler module's sha256 is fresh;
      * every declared ``contract_tests`` file names the node package, and the ids
        are EXECUTED green on HEAD (a recorded status is not evidence).
    """
    receipt_path = RECEIPTS_DIR / f"{node_id}.json"
    raw = _load_json(receipt_path)
    if raw is None:
        return False, f"no-legacy receipt unreadable at {_display_path(receipt_path)}"
    if raw.get("node_id") != node_id:
        return False, f"receipt node_id {raw.get('node_id')!r} != {node_id!r}"
    if raw.get("legacy_handler") != LEGACY_HANDLER_NONE:
        return False, (
            f"legacy_handler={raw.get('legacy_handler')!r}; only 'none' is a "
            f"no-legacy receipt — a node with a legacy handler needs the "
            f"equivalence-replay or hand-flip proof"
        )
    if raw.get("receipt_schema") != EXPECTED_NO_LEGACY_SCHEMA:
        return (
            False,
            f"unexpected no-legacy receipt_schema {raw.get('receipt_schema')!r}",
        )

    module = raw.get("handler_module") or handler_module
    if not isinstance(module, str) or not module:
        return False, "no-legacy receipt has no handler_module"
    module_file = _resolve_module_file(module)
    if module_file is None:
        return False, f"handler_module {module} not resolvable for freshness check"
    if _sha256_file(module_file) != raw.get("handler_module_sha256"):
        return False, "stale receipt: live handler_module_sha256 != recorded"

    base_ref = raw.get("base_ref")
    if not isinstance(base_ref, str) or not base_ref:
        return False, "no-legacy receipt missing base_ref"
    repo_root = _git_repo_root(SRC_ROOT)
    if repo_root is None:
        return False, f"cannot resolve a git repo root from {SRC_ROOT}"
    if not _git_ref_exists(repo_root, base_ref):
        return False, f"base_ref {base_ref!r} unresolvable"
    if not _git_is_ancestor(repo_root, base_ref):
        return False, f"base_ref {base_ref!r} is not an ancestor of HEAD"

    files, evidence = _legacy_handler_evidence(repo_root, base_ref, node_id)
    if evidence is not None:
        return False, f"legacy handler existed: {evidence}"
    recorded = raw.get("base_node_files")
    if not isinstance(recorded, list) or sorted(str(f) for f in recorded) != files:
        return False, (
            f"base_node_files does not match git ls-tree at {base_ref}: "
            f"recorded={recorded!r} actual={files!r}"
        )
    live_base = (
        _git_merge_base(repo_root, BASE_REF)
        if _git_ref_exists(repo_root, BASE_REF)
        else None
    )
    if live_base is not None and live_base != base_ref:
        _, live_evidence = _legacy_handler_evidence(repo_root, live_base, node_id)
        if live_evidence is not None:
            landed, landed_reason = _landed_no_legacy_flip(
                repo_root, live_base, base_ref, node_id, receipt_path
            )
            if not landed:
                return (
                    False,
                    f"legacy handler existed at the live merge base: {live_evidence} "
                    f"(not a landed no-legacy flip: {landed_reason})",
                )
            # A no-legacy flip introduces a handler. Once it lands, the live
            # merge base necessarily has that handler, so descendants must be
            # able to retain the original proof. Only accept the identical
            # receipt AND handler already on the trusted base; an older
            # handlerless commit still cannot justify replacing a live handler.
            module_rel = _module_repo_rel(module)
            try:
                receipt_rel = receipt_path.resolve().relative_to(repo_root.resolve())
            except ValueError:
                receipt_rel = None
            already_landed = (
                receipt_rel is not None
                and module_rel is not None
                and _git_is_ancestor(repo_root, base_ref, live_base)
                and _git_show(repo_root, live_base, receipt_rel.as_posix())
                == receipt_path.read_text(encoding="utf-8")
                and _git_show(repo_root, live_base, module_rel[1])
                == module_file.read_text(encoding="utf-8")
            )
            if not already_landed:
                return (
                    False,
                    f"legacy handler existed at the live merge base: {live_evidence}",
                )

    tests_raw = raw.get("contract_tests")
    test_ids = tuple(str(t) for t in tests_raw) if isinstance(tests_raw, list) else ()
    if not test_ids:
        return False, "no-legacy receipt names no contract_tests"
    for test_file in sorted({t.split("::", 1)[0] for t in test_ids}):
        path = repo_root / test_file
        if not path.is_file():
            return False, f"contract test file {test_file} absent"
        if node_id not in path.read_text(encoding="utf-8"):
            return False, f"contract test file {test_file} never names {node_id}"
    executor = (
        parity_executor if parity_executor is not None else default_parity_executor
    )
    verdict = executor(node_id, test_ids)
    if not verdict.executed:
        return False, f"contract tests UNEXECUTED ({verdict.detail})"
    if not verdict.green:
        return False, f"contract tests NOT GREEN when executed: {verdict.detail}"
    return True, (
        f"no-legacy-handler-at-{base_ref[:12]}"
        f"+contract-tests-executed-green({len(test_ids)} test id(s))"
    )


def verify_flip_receipt(
    node_id: str,
    handler_module: str | None,
    *,
    parity_executor: ParityExecutor | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason) for a non-canonical -> canonical baseline flip.

    Requires an adequacy receipt (re-derived verdict) AND one of two sanctioned
    behavior proofs, each bound to the SAME selected input set as the receipt:
      * RSD regen path: a GREEN regen-vs-legacy equivalence-replay artifact; OR
      * HAND-flip path (OMN-14781): a hand-flip proof whose verbatim-preservation
        the gate re-derives from git and whose declared parity tests it EXECUTES
        green on HEAD (OMN-15340 — the recorded status string is not evidence).
    Fail-closed: no adequacy, or neither proof, or a mismatched input set -> RED.

    An adequacy receipt carrying ``legacy_handler`` takes the NO-LEGACY path
    (OMN-20298, ``verify_no_legacy_flip``) and only that path.
    """
    raw = _load_json(RECEIPTS_DIR / f"{node_id}.json")
    if raw is not None and "legacy_handler" in raw:
        ok_n, reason_n = verify_no_legacy_flip(
            node_id, handler_module, parity_executor=parity_executor
        )
        return ok_n, f"no-legacy: {reason_n}"

    ok_a, reason_a, sel_receipt = verify_adequacy_receipt(node_id, handler_module)
    if not ok_a:
        return False, f"adequacy: {reason_a}"

    ok_e, reason_e, sel_equiv = verify_equivalence_replay(node_id)
    ok_h, reason_h, sel_hand = verify_handflip_proof(
        node_id, handler_module, parity_executor=parity_executor
    )
    if not ok_e and not ok_h:
        return (
            False,
            f"proof: no equivalence-replay ({reason_e}) and no hand-flip proof "
            f"({reason_h})",
        )
    proof_reason, sel_proof = (reason_e, sel_equiv) if ok_e else (reason_h, sel_hand)

    # Bind coverage to the behavior proof: both must reference the same input set,
    # else a coverage-adequate golden could be replayed against an easier set.
    if set(sel_receipt) != set(sel_proof):
        return (
            False,
            "PAIR_INCOMPATIBLE: receipt/proof selected_input_hashes differ",
        )
    return True, f"{reason_a}+{proof_reason}"


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
    baseline_growth: tuple[str, ...] = ()

    @property
    def failed(self) -> bool:
        return bool(
            self.new_non_canonical or self.unproven_flips or self.baseline_growth
        )


def evaluate(
    findings: list[ModelHandlerShapeFinding],
    baseline: list[str],
    base_baseline: list[str] | None = None,
) -> RatchetResult:
    """Ratchet verdict.

    ``baseline`` is the working-tree (post-edit) committed baseline. ``base_baseline``
    is the baseline as it existed at the git BASE (origin/dev). When provided, an
    in-PR REMOVAL from the baseline is adjudicated as a claimed flip (OMN-14781):
    the stateless hole was comparing only the live scan against the post-edit
    baseline, which let an unproven flip land by shrinking the baseline in the same
    commit. When ``base_baseline`` is None (git/base unavailable) the removal/growth
    check is skipped and behavior is identical to the pre-OMN-14781 gate.
    """
    baseline_set = set(baseline)
    by_id = {f.node_id: f for f in findings}
    current_nc = set(current_non_canonical(findings))

    # NEW non-canonical node not in the baseline -> HARD-FAIL.
    new_nc = sorted(current_nc - baseline_set)

    # Baselined nodes still non-canonical -> WARN (known debt).
    warn = sorted(current_nc & baseline_set)

    # Baselined nodes that are now canonical -> a flip; require the full proof.
    proven: list[str] = []
    unproven: list[str] = []
    for node_id in sorted(baseline_set - current_nc):
        finding = by_id.get(node_id)
        if finding is None:
            continue  # node deleted; --update will drop it
        ok, _ = verify_flip_receipt(node_id, finding.handler_module)
        (proven if ok else unproven).append(node_id)

    # OMN-14781: nodes REMOVED from the baseline in this PR (present at the git
    # BASE, absent in the working baseline) are claimed flips and must carry the
    # SAME proof. This closes the stateless hole. Also enforce the monotonic
    # non-increasing invariant: the baseline may only shrink — hand-ADDING a node
    # (growth) to silence a new non-canonical node is illegal.
    baseline_growth: list[str] = []
    if base_baseline is not None:
        base_set = set(base_baseline)
        for node_id in sorted(base_set - baseline_set):
            finding = by_id.get(node_id)
            if finding is None:
                # Node no longer classified. A baseline edit forces a full scan, so
                # None here means the node was DELETED from the repo -> the removal
                # is self-justifying (nothing left to be non-canonical).
                continue
            if not finding.is_canonical:
                # Removed from the baseline but STILL non-canonical: already a
                # new_nc hard-fail above; don't double-report.
                continue
            ok, _ = verify_flip_receipt(node_id, finding.handler_module)
            (proven if ok else unproven).append(node_id)
        baseline_growth = sorted(baseline_set - base_set)

    return RatchetResult(
        new_non_canonical=tuple(new_nc),
        unproven_flips=tuple(sorted(set(unproven))),
        warn_baselined=tuple(warn),
        proven_flips=tuple(sorted(set(proven))),
        baseline_growth=tuple(baseline_growth),
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
            "  Baselined node(s) flipped to canonical shape WITHOUT valid flip proof"
        )
        lines.append(
            "  (includes in-PR NON_CANONICAL removals — OMN-14781: removing a node"
        )
        lines.append(
            "  from the baseline in the same commit as the flip is still a flip)."
        )
        lines.append(
            "  A shape flip is not proof of equivalence (OMN-14208 trap). Provide an"
        )
        lines.append(
            "  adequacy receipt (<node_id>.json) + EITHER a green equivalence-replay"
        )
        lines.append(
            "  (<node_id>.equivalence.json, RSD regen) OR a hand-flip proof "
            "(<node_id>.handflip.json)"
        )
        lines.append("  under scripts/ci/adequacy_receipts/, bound to one input set.")
        lines.append(
            "  A node with NO legacy handler at the merge base instead carries an"
        )
        lines.append(
            f"  adequacy receipt with legacy_handler: none ({EXPECTED_NO_LEGACY_SCHEMA}:"
        )
        lines.append(
            "  base_ref, base_node_files, handler_module(+sha256), contract_tests):"
        )
        for node_id in result.unproven_flips:
            f = by_id.get(node_id)
            _, reason = verify_flip_receipt(node_id, f.handler_module if f else None)
            lines.append(f"    + {node_id}  ({reason})")
    if result.baseline_growth:
        lines.append("")
        lines.append(
            "  Baseline GROWTH — the frozen NON_CANONICAL set is monotonically"
        )
        lines.append(
            "  non-increasing; new nodes must be born canonical, not hand-added here:"
        )
        for node_id in result.baseline_growth:
            lines.append(f"    + {node_id}")
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
    global PACKAGE, SRC_ROOT, NODES_GLOB, BASELINE_PATH, RECEIPTS_DIR, BASE_REF
    PACKAGE = args.package
    BASE_REF = args.base_ref
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
    # OMN-14781: the git-BASE baseline, to catch in-PR NON_CANONICAL removals/growth.
    base_baseline = load_base_baseline(BASELINE_PATH, args.base_ref)

    full = args.full or args.scope == "full"
    scope_label = "full"

    if base_baseline is None:
        print(
            "Canonical handler-shape ratchet NOTE — git BASE baseline unavailable; "
            "in-PR baseline-removal/growth check skipped for this run (it is active "
            "in CI where the PR base is present).",
            file=sys.stderr,
        )
    elif not full and set(base_baseline) != set(baseline):
        # The frozen baseline itself changed vs the base. Adjudicating a removal or
        # growth needs the COMPLETE node set (a removed node may be canonical now and
        # live anywhere), so escalate to a full scan (fail-closed).
        full = True
        scope_label = "full (escalated: baseline changed vs base)"

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
                # base==working here (a baseline change would have escalated above),
                # so passing base_baseline is a no-op removal/growth check.
                return _report(
                    evaluate(findings, baseline, base_baseline), findings, "changed"
                )

    findings = classify_all()
    return _report(evaluate(findings, baseline, base_baseline), findings, scope_label)


if __name__ == "__main__":
    raise SystemExit(main())
