# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File-grain import-graph-closure test selection — SHADOW MODE ONLY (OMN-14921).

Observational companion to the governed module-grain selector in
``scripts/ci/detect_test_paths.py``. When the shadow flag is on, this module
computes what a file-grain reverse-import-closure selection WOULD choose over
the real import graph (grimp — the same graph engine the ``.importlinter``
layering oracle already trusts, OMN-14216), emits both selections plus the
delta to a JSON artifact and the job log, and NEVER alters the selection the
selector returns. Promotion out of shadow is a later, separate, burn-in-gated
decision backed by the delta data this module produces.

Justification: import-graph-closure precision — the hand-curated module-grain
``reverse_deps`` map cannot distinguish "changed one leaf util imported by 9
test files" from "changed the envelope every model touches" — and the OMN-3210
layering architecture, whose seams are exactly the import edges this closure
walks. (Never a CI-cost argument; that rationale is struck.)

Fail-closed by construction (OMN-14921 requirement 1):
  * any changed file the graph cannot resolve (non-Python under src/, deleted,
    outside src/tests, unreadable) → no narrowing;
  * a dynamic-import marker (``importlib`` / ``__import__``) in a changed file
    → no narrowing (runtime edges bypass the static graph);
  * grimp unavailable / graph build failure → no narrowing;
  * graph staleness — the package resolving anywhere but this working tree
    (e.g. ambient PYTHONPATH shadowing the checkout) → no narrowing;
  * an unparseable / relatively-importing / dynamically-importing test file, a
    test file with zero package imports, or an unparseable conftest on its
    directory chain → that file is KEPT without positive evidence.

Every candidate test file's effective import set is the union of its own direct
imports and the direct imports of every ``conftest.py`` on its directory chain
(pytest fixture injection is not an import edge; the conftest chain carries it).

No new YAML/config surface is introduced, so the OMN-14897 duplicate-key
last-wins hole cannot re-open here: the only config parse on this path remains
``ModelAdjacencyMap.from_yaml_text`` (duplicate-key-rejecting, fail-closed).
"""

from __future__ import annotations

import ast
import importlib.util
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from scripts.ci.test_selection_models import (
    EnumFullSuiteReason,
    ModelTestSelection,
)

if TYPE_CHECKING:  # pragma: no cover - typing only; grimp import stays lazy
    from grimp.application.ports.graph import ImportGraph

__all__ = [
    "ModelShadowClosureReport",
    "collect_direct_imports",
    "compute_impacted_modules",
    "compute_shadow_closure",
    "graph_staleness_reason",
    "refine_candidates",
    "resolve_changed_src_modules",
]

PACKAGE_NAME = "omnibase_core"
TEST_UNIT_PREFIX = "tests/unit/"
TEST_INTEGRATION_PREFIX = "tests/integration/"
PYPROJECT_PATH = "pyproject.toml"

# Substring markers whose presence in a CHANGED file means runtime import edges
# may bypass the static graph — fail closed, do not narrow that run. (Test files
# containing these markers are individually kept, not globally blocking.)
DYNAMIC_IMPORT_MARKERS = ("importlib", "__import__")

# Escalations where a file-grain shadow adds no promotion signal: the boundary
# is unconditional (main / merge_group / schedule / flag-off), or the diff
# touches the selector itself (narrowing on a change to the selector would be
# self-referentially fail-open, so there is nothing to shadow-measure).
_SHADOW_SKIP_REASONS = frozenset(
    {
        EnumFullSuiteReason.FEATURE_FLAG_OFF,
        EnumFullSuiteReason.MAIN_BRANCH,
        EnumFullSuiteReason.MERGE_GROUP,
        EnumFullSuiteReason.SCHEDULED,
        EnumFullSuiteReason.TEST_INFRASTRUCTURE,
    }
)

# Paths that are affirmatively test-inert (mirrors the selector's docs-only
# classification): they can never carry executable code or fixture data.
_DOCS_ONLY_SUFFIXES = (".md",)
_DOCS_ONLY_PREFIXES = ("docs/",)


class ModelShadowClosureReport(BaseModel):
    """Both selections + delta for one selector run. Artifact/log payload only —
    nothing consumes this to alter CI behavior while OMN-14921 is in shadow."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    ticket: str = "OMN-14921"
    shadow_only: bool = True
    skipped_reason: str | None = None
    narrowed: bool = False
    fail_closed_reasons: list[str] = Field(default_factory=list)
    module_grain_is_full_suite: bool = False
    module_grain_reason: str | None = None
    module_grain_paths: list[str] = Field(default_factory=list)
    candidate_file_count: int = 0
    file_grain_files: list[str] = Field(default_factory=list)
    file_grain_file_count: int = 0
    delta_file_count: int = 0
    kept_fail_closed_count: int = 0
    impacted_module_count: int = 0
    changed_file_count: int = 0
    elapsed_seconds: float = 0.0


def _is_docs_only_path(path: str) -> bool:
    return path.endswith(_DOCS_ONLY_SUFFIXES) or path.startswith(_DOCS_ONLY_PREFIXES)


def resolve_changed_src_modules(
    changed_files: list[str],
    repo_root: Path,
    package_name: str = PACKAGE_NAME,
) -> tuple[set[str], list[str]]:
    """Map changed files to fully-qualified module names, fail-closed.

    Returns ``(modules, fail_closed_reasons)``. ANY reason means the caller must
    not narrow. Files that are affirmatively impact-free (docs, integration
    tests — the integration job runs unconditionally, ``pyproject.toml`` — it
    already passed the selector's content-aware metadata-only classification to
    reach the smart path) contribute nothing. tests/unit/ files are handled by
    the caller as forced-keep directories.
    """
    src_prefix = f"src/{package_name}/"
    modules: set[str] = set()
    reasons: list[str] = []
    for path in changed_files:
        if path.startswith(src_prefix):
            if not path.endswith(".py"):
                reasons.append(
                    f"non-Python source change is invisible to the import graph: {path}"
                )
                continue
            file_path = repo_root / path
            if not file_path.is_file():
                reasons.append(
                    f"changed source file missing from working tree (deleted/renamed): {path}"
                )
                continue
            try:
                source = file_path.read_text(encoding="utf-8")
            except OSError as exc:  # boundary-ok: unreadable file must fail closed
                reasons.append(f"cannot read changed source file {path}: {exc}")
                continue
            marker = next((m for m in DYNAMIC_IMPORT_MARKERS if m in source), None)
            if marker is not None:
                reasons.append(
                    f"dynamic-import marker {marker!r} in changed file {path}: "
                    "runtime dependencies may bypass the static import graph"
                )
                continue
            dotted = path[len("src/") : -len(".py")].replace("/", ".")
            if dotted.endswith(".__init__"):
                dotted = dotted[: -len(".__init__")]
            modules.add(dotted)
        elif path.startswith(TEST_UNIT_PREFIX):
            continue  # forced-keep directory, handled by the caller
        elif path.startswith(TEST_INTEGRATION_PREFIX):
            continue  # integration job runs unconditionally on every PR
        elif path == PYPROJECT_PATH or _is_docs_only_path(path):
            continue
        else:
            reasons.append(
                f"changed file outside src/tests cannot be resolved by the import graph: {path}"
            )
    return modules, reasons


def graph_staleness_reason(
    repo_root: Path, package_name: str = PACKAGE_NAME
) -> str | None:
    """Non-None when the import graph would NOT describe this working tree.

    grimp locates the package through the interpreter's import machinery; if an
    ambient PYTHONPATH (or a stale install) resolves ``package_name`` to a
    different checkout, the closure would be computed over the WRONG source —
    silent staleness. Verified live: an inherited PYTHONPATH pointing at the
    canonical clone shadows a worktree checkout exactly this way.
    """
    try:
        spec = importlib.util.find_spec(package_name)
    except (ImportError, ValueError) as exc:  # boundary-ok: fail closed on lookup error
        return f"cannot locate package {package_name!r} for graph build: {exc}"
    if spec is None or spec.origin is None:
        return f"package {package_name!r} is not importable — cannot build import graph"
    origin = Path(spec.origin).resolve()
    expected = (repo_root / "src" / package_name / "__init__.py").resolve()
    if origin != expected:
        return (
            f"import graph would be STALE: {package_name!r} resolves to {origin}, "
            f"not this working tree ({expected}) — ambient PYTHONPATH or stale install"
        )
    return None


def compute_impacted_modules(
    graph: ImportGraph,
    changed_modules: set[str],
) -> tuple[frozenset[str], list[str]]:
    """Changed modules plus every transitive importer (grimp downstream closure).

    A changed package ``__init__`` contaminates every descendant (importing any
    submodule executes ancestor ``__init__``s), so packages add their descendant
    set and its importers too. A changed module absent from the graph is a
    fail-closed reason (deleted-but-listed, namespace quirk, graph gap).
    """
    impacted: set[str] = set()
    reasons: list[str] = []
    for module in sorted(changed_modules):
        if module not in graph.modules:
            reasons.append(f"changed module not present in import graph: {module}")
            continue
        impacted.add(module)
        impacted.update(graph.find_downstream_modules(module))
        descendants = graph.find_descendants(module)
        if descendants:
            impacted.update(descendants)
            impacted.update(graph.find_downstream_modules(module, as_package=True))
    return frozenset(impacted), reasons


def collect_direct_imports(
    py_file: Path, package_name: str = PACKAGE_NAME
) -> frozenset[str] | None:
    """Dotted ``package_name`` imports this file makes directly, or None.

    None (⇒ the caller keeps the file, fail closed) when the file cannot be
    read/parsed, uses relative imports (unresolvable without package context),
    or contains a dynamic-import marker. ``from pkg.x import y`` records both
    ``pkg.x`` and ``pkg.x.y`` so a submodule-or-attribute name matches whichever
    of the two is a real graph module.
    """
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, ValueError):  # boundary-ok: unparseable → keep
        return None
    if any(marker in source for marker in DYNAMIC_IMPORT_MARKERS):
        return None
    prefix = package_name + "."
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package_name or alias.name.startswith(prefix):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                return None  # relative import — fail closed for this file
            if node.module and (
                node.module == package_name or node.module.startswith(prefix)
            ):
                found.add(node.module)
                for alias in node.names:
                    found.add(f"{node.module}.{alias.name}")
    return frozenset(found)


def refine_candidates(
    candidate_imports: dict[str, frozenset[str] | None],
    impacted_modules: frozenset[str],
    forced_keep: frozenset[str],
) -> tuple[list[str], list[str]]:
    """Pure file-grain refinement over pre-collected data.

    Returns ``(selected_files, kept_fail_closed)``. A candidate is selected when
    its effective import set intersects the impacted closure; it is kept WITHOUT
    positive evidence (and recorded in ``kept_fail_closed``) when it is
    force-kept, has ``None`` imports (unparseable / relative / dynamic), or has
    zero package imports (a subprocess-style test the graph cannot clear).
    """
    selected: list[str] = []
    kept: list[str] = []
    for candidate in sorted(candidate_imports):
        imports = candidate_imports[candidate]
        if candidate in forced_keep or imports is None or not imports:
            selected.append(candidate)
            kept.append(candidate)
        elif imports & impacted_modules:
            selected.append(candidate)
    return selected, kept


def _candidate_roots(selection: ModelTestSelection) -> tuple[list[str], str | None]:
    """Candidate unit-test roots for the shadow computation, or a skip reason."""
    if selection.is_full_suite:
        if selection.full_suite_reason in _SHADOW_SKIP_REASONS:
            return [], (
                "shadow not applicable to unconditional/self-referential escalation: "
                f"{selection.full_suite_reason}"
            )
        # SHARED_MODULE / THRESHOLD_MODULES: the whole unit tree is the honest
        # candidate set — this is exactly the shadow data the adjacency YAML
        # names as the precondition for ever demoting a shared module.
        return [TEST_UNIT_PREFIX], None
    if not selection.selected_paths:
        return [], "docs-only empty selection — nothing to refine"
    return list(selection.selected_paths), None


def _collect_candidate_files(roots: list[str], repo_root: Path) -> list[str]:
    files: set[str] = set()
    for root in roots:
        directory = repo_root / root
        if not directory.is_dir():
            continue
        for match in directory.rglob("test_*.py"):
            files.add(match.relative_to(repo_root).as_posix())
    return sorted(files)


def _conftest_chain_imports(
    test_rel_path: str,
    repo_root: Path,
    cache: dict[str, frozenset[str] | None],
    package_name: str,
) -> frozenset[str] | None:
    """Union of direct imports of every conftest.py above ``test_rel_path``.

    None when ANY conftest on the chain is unparseable — every test below it is
    then kept fail-closed.
    """
    parts = Path(test_rel_path).parent.parts
    merged: set[str] = set()
    for depth in range(len(parts) + 1):
        rel_dir = "/".join(parts[:depth])
        if rel_dir in cache:
            chain = cache[rel_dir]
        else:
            conftest = repo_root / rel_dir / "conftest.py"
            chain = (
                collect_direct_imports(conftest, package_name)
                if conftest.is_file()
                else frozenset()
            )
            cache[rel_dir] = chain
        if chain is None:
            return None
        merged.update(chain)
    return frozenset(merged)


def compute_shadow_closure(
    changed_files: list[str],
    selection: ModelTestSelection,
    repo_root: Path,
    package_name: str = PACKAGE_NAME,
) -> ModelShadowClosureReport:
    """Compute the shadow file-grain selection + delta for one selector run.

    Pure observation: the returned report never feeds back into the selection.
    Every ambiguity lands in ``fail_closed_reasons`` and forces
    ``narrowed=False`` with the file-grain set pinned to the full candidate set
    (i.e. exactly what module grain runs today).
    """
    started = time.monotonic()

    def _report(**overrides: object) -> ModelShadowClosureReport:
        base: dict[str, object] = {
            "module_grain_is_full_suite": selection.is_full_suite,
            "module_grain_reason": (
                selection.full_suite_reason.value
                if selection.full_suite_reason is not None
                else None
            ),
            "module_grain_paths": list(selection.selected_paths),
            "changed_file_count": len(changed_files),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        base.update(overrides)
        return ModelShadowClosureReport.model_validate(base)

    roots, skip_reason = _candidate_roots(selection)
    if skip_reason is not None:
        return _report(skipped_reason=skip_reason)

    candidates = _collect_candidate_files(roots, repo_root)

    def _fail_closed(reasons: list[str]) -> ModelShadowClosureReport:
        return _report(
            narrowed=False,
            fail_closed_reasons=reasons,
            candidate_file_count=len(candidates),
            file_grain_files=candidates,
            file_grain_file_count=len(candidates),
            delta_file_count=0,
        )

    changed_modules, reasons = resolve_changed_src_modules(
        changed_files, repo_root, package_name
    )
    if reasons:
        return _fail_closed(reasons)

    stale = graph_staleness_reason(repo_root, package_name)
    if stale is not None:
        return _fail_closed([stale])

    try:
        import grimp  # deliberate lazy import: optional at selector runtime

        graph = grimp.build_graph(package_name, cache_dir=None)
    except Exception as exc:  # noqa: BLE001  # boundary-ok: graph build failure must fail closed
        return _fail_closed([f"import graph build failed: {exc!r}"])

    impacted, closure_reasons = compute_impacted_modules(graph, changed_modules)
    if closure_reasons:
        return _fail_closed(closure_reasons)

    forced_keep: set[str] = set()
    for path in changed_files:
        if path.startswith(TEST_UNIT_PREFIX):
            parts = path.split("/")
            if len(parts) >= 3:
                forced_dir = f"{TEST_UNIT_PREFIX}{parts[2]}/"
                forced_keep.update(c for c in candidates if c.startswith(forced_dir))

    conftest_cache: dict[str, frozenset[str] | None] = {}
    candidate_imports: dict[str, frozenset[str] | None] = {}
    for candidate in candidates:
        own = collect_direct_imports(repo_root / candidate, package_name)
        if own is None:
            candidate_imports[candidate] = None
            continue
        chain = _conftest_chain_imports(
            candidate, repo_root, conftest_cache, package_name
        )
        candidate_imports[candidate] = None if chain is None else own | chain

    file_grain, kept = refine_candidates(
        candidate_imports, impacted, frozenset(forced_keep)
    )

    return _report(
        narrowed=len(file_grain) < len(candidates),
        candidate_file_count=len(candidates),
        file_grain_files=file_grain,
        file_grain_file_count=len(file_grain),
        delta_file_count=len(candidates) - len(file_grain),
        kept_fail_closed_count=len(kept),
        impacted_module_count=len(impacted),
    )
