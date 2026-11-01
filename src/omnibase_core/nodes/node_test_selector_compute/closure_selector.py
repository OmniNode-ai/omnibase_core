# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""File-grain import-graph-closure test selector, packaged in the wheel (OMN-14206).

Promoted from ``scripts/ci/test_selection_closure.py`` (OMN-14921) so the one
closure primitive ships with ``omnibase_core`` and other repositories
(omnibase_infra, omnimarket) consume it without a copy. ``scripts/ci`` keeps
only a re-exporting shim plus the shadow-mode report.

What changed relative to the script it was promoted from:

* **Candidate roots are a parameter.** The script hardcoded ``tests/unit/`` as
  the only tree it collected candidates from. omnimarket has 3,692 test files
  and only 1,351 sit under ``tests/unit``; a consumer narrowing over
  ``tests/unit/`` alone can never select the other 2,341, which is fail-open.
  ``candidate_roots`` names the trees a repository's closure may narrow within
  (default ``("tests/unit/",)``, byte-identical behaviour for omnibase_core).
  The fail-closed sentinel is the configured roots, so a fallback covers every
  root, never just the first.
* **Test-file patterns and separately-gated prefixes are parameters** too, for
  repositories that collect ``*_test.py`` or gate a tree other than
  ``tests/integration/`` in its own job.
* A changed test file sitting directly under a root (no subdirectory to keep)
  is kept itself; a changed non-test file directly under a root (a root
  ``conftest.py`` or helper) keeps that whole root, because it can affect every
  test below it.

Fail-closed by construction (OMN-14921 requirement 1):
  * any changed file the graph cannot resolve (non-Python under src/, deleted,
    outside src/tests, unreadable) → no narrowing;
  * a dynamic-import marker (``importlib`` / ``__import__``) in a changed file
    → no narrowing (runtime edges bypass the static graph);
  * grimp unavailable / graph build failure → no narrowing (``grimp`` is the
    ``test-selection`` extra of this distribution);
  * graph staleness — the package resolving anywhere but this working tree
    (e.g. ambient PYTHONPATH shadowing the checkout) → no narrowing;
  * an unparseable / relatively-importing / dynamically-importing test file, a
    test file with zero package imports, or an unparseable conftest on its
    directory chain → that file is KEPT without positive evidence.

Every candidate test file's effective import set is the union of its own direct
imports and the direct imports of every ``conftest.py`` on its directory chain
(pytest fixture injection is not an import edge; the conftest chain carries it).

This module must not import from ``scripts``: a wheel consumer has no such
package (enforced by ``test_closure_selector_does_not_import_from_scripts``).
"""

from __future__ import annotations

import ast
import fnmatch
import importlib.util
import time
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.test_selector.model_closure_selection import (
    ModelClosureSelection,
)

if TYPE_CHECKING:  # typing only; the grimp import stays lazy
    from grimp import ImportGraph

__all__ = [
    "DEFAULT_CANDIDATE_ROOTS",
    "DEFAULT_IGNORED_PREFIXES",
    "DEFAULT_TEST_FILE_PATTERNS",
    "DYNAMIC_IMPORT_MARKERS",
    "ModelClosureSelection",
    "collect_candidate_files",
    "collect_direct_imports",
    "compute_closure_selection",
    "compute_impacted_modules",
    "graph_staleness_reason",
    "normalize_candidate_roots",
    "refine_candidates",
    "resolve_changed_src_modules",
]

PACKAGE_NAME = "omnibase_core"
PYPROJECT_PATH = "pyproject.toml"

#: Trees the closure may narrow within. Per-repository: omnimarket passes
#: ``("tests/unit/", "tests/nodes/", ...)`` so its non-unit tests are candidates.
DEFAULT_CANDIDATE_ROOTS: tuple[str, ...] = ("tests/unit/",)

#: Trees with their own unconditional CI job: a change there contributes
#: nothing to the closure (the job runs on every PR regardless).
DEFAULT_IGNORED_PREFIXES: tuple[str, ...] = ("tests/integration/",)

#: Candidate collection patterns (``fnmatch`` on the file name).
DEFAULT_TEST_FILE_PATTERNS: tuple[str, ...] = ("test_*.py",)

# Substring markers whose presence in a CHANGED file means runtime import edges
# may bypass the static graph — fail closed, do not narrow that run. (Test files
# containing these markers are individually kept, not globally blocking.)
DYNAMIC_IMPORT_MARKERS = ("importlib", "__import__")

# Paths that are affirmatively test-inert (mirrors the selector's docs-only
# classification): they can never carry executable code or fixture data.
_DOCS_ONLY_SUFFIXES = (".md",)
_DOCS_ONLY_PREFIXES = ("docs/",)


def _is_docs_only_path(path: str) -> bool:
    return path.endswith(_DOCS_ONLY_SUFFIXES) or path.startswith(_DOCS_ONLY_PREFIXES)


def normalize_candidate_roots(roots: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize candidate roots to repo-relative ``dir/`` strings.

    Raises ``ModelOnexError`` (``INVALID_PARAMETER``) for an empty set, an empty/absolute/``..`` root, or
    nested roots (a candidate would be counted twice). A malformed root must be
    a loud error, never a silently empty candidate universe that "proves" no
    test is affected.
    """
    normalized: list[str] = []
    for raw in roots:
        if not raw or not raw.strip("/"):
            raise ModelOnexError(
                f"candidate root must be a non-empty relative path: {raw!r}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts:
            raise ModelOnexError(
                f"candidate root must be repo-relative with no '..': {raw!r}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        root = path.as_posix().rstrip("/") + "/"
        if root.startswith("./"):
            root = root[2:]
        if root not in normalized:
            normalized.append(root)
    if not normalized:
        raise ModelOnexError(
            "at least one candidate root is required",
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        )
    for outer in normalized:
        for inner in normalized:
            if outer != inner and inner.startswith(outer):
                raise ModelOnexError(
                    f"candidate roots must not be nested: {inner!r} is inside {outer!r}",
                    error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                )
    return tuple(normalized)


def _normalize_prefixes(prefixes: Iterable[str]) -> tuple[str, ...]:
    return tuple(p if p.endswith("/") else p + "/" for p in prefixes)


def resolve_changed_src_modules(
    changed_files: list[str],
    repo_root: Path,
    package_name: str = PACKAGE_NAME,
    *,
    candidate_roots: Sequence[str] = DEFAULT_CANDIDATE_ROOTS,
    ignored_prefixes: Sequence[str] = DEFAULT_IGNORED_PREFIXES,
) -> tuple[set[str], list[str]]:
    """Map changed files to fully-qualified module names, fail-closed.

    Returns ``(modules, fail_closed_reasons)``. ANY reason means the caller must
    not narrow. Files that are affirmatively impact-free (docs, ignored
    separately-gated trees — the integration job runs unconditionally,
    ``pyproject.toml`` — it already passed the selector's content-aware
    metadata-only classification to reach the smart path) contribute nothing.
    Files under a candidate root are handled by the caller as forced-keep
    directories.
    """
    roots = tuple(normalize_candidate_roots(candidate_roots))
    ignored = _normalize_prefixes(ignored_prefixes)
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
            except OSError as exc:  # unreadable file must fail closed
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
        elif path.startswith(roots):
            continue  # forced-keep directory, handled by the caller
        elif path.startswith(ignored):
            continue  # separately gated: its own job runs unconditionally
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
    except (ImportError, ValueError) as exc:  # lookup error must fail closed
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
    except (OSError, SyntaxError, ValueError):  # unparseable → keep the file
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


def collect_candidate_files(
    roots: Sequence[str],
    repo_root: Path,
    test_file_patterns: Sequence[str] = DEFAULT_TEST_FILE_PATTERNS,
) -> list[str]:
    """Sorted repo-relative test files under ``roots`` matching the patterns."""
    files: set[str] = set()
    for root in roots:
        directory = repo_root / root
        if not directory.is_dir():
            continue
        for match in directory.rglob("*.py"):
            if any(fnmatch.fnmatch(match.name, pat) for pat in test_file_patterns):
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


def _forced_keep_keys(
    changed_files: list[str],
    roots: tuple[str, ...],
    test_file_patterns: Sequence[str],
) -> set[str]:
    """Prefixes (``dir/``) or exact files a directly-changed test path keeps.

    A change at ``<root><dir>/...`` keeps ``<root><dir>/``. A test file directly
    under a root keeps itself; any other file directly under a root (a root
    ``conftest.py`` or helper) keeps the whole root, since it can affect every
    test below it.
    """
    keys: set[str] = set()
    for path in changed_files:
        root = next((r for r in roots if path.startswith(r)), None)
        if root is None:
            continue
        parts = path[len(root) :].split("/")
        if len(parts) >= 2:
            keys.add(f"{root}{parts[0]}/")
        elif any(fnmatch.fnmatch(parts[0], pat) for pat in test_file_patterns):
            keys.add(path)
        else:
            keys.add(root)
    return keys


def compute_closure_selection(
    changed_files: list[str],
    repo_root: Path,
    package_name: str = PACKAGE_NAME,
    *,
    candidate_roots: Sequence[str] = DEFAULT_CANDIDATE_ROOTS,
    test_file_patterns: Sequence[str] = DEFAULT_TEST_FILE_PATTERNS,
    ignored_prefixes: Sequence[str] = DEFAULT_IGNORED_PREFIXES,
) -> ModelClosureSelection:
    """File-grain closure selection over the configured candidate roots.

    There is no module-grain answer to shrink within (the hand-curated map that
    produced it is retired: 26/40 declarations were false against the real
    graph), so candidates are collected over EVERY root in ``candidate_roots``.
    This is the single primitive ``scripts/ci/detect_test_paths.py`` (direct
    call — CLI/I/O boundary), ``node_test_selector_compute`` (caller/EFFECT
    boundary, injected as ``ModelTestSelectionRequest.closure_selected_files``)
    and downstream repositories consume; none re-implements reverse-dependency
    logic.

    Every ambiguity fails closed to the conservative whole-tree sentinel — the
    configured roots themselves, ``["tests/unit/"]`` by default — never a
    partial, best-effort list.
    """
    started = time.monotonic()
    roots = normalize_candidate_roots(candidate_roots)
    patterns = tuple(test_file_patterns)

    def _result(**overrides: object) -> ModelClosureSelection:
        base: dict[str, object] = {
            "elapsed_seconds": round(time.monotonic() - started, 3)
        }
        base.update(overrides)
        return ModelClosureSelection.model_validate(base)

    def _fail_closed(reasons: list[str]) -> ModelClosureSelection:
        return _result(
            selected_files=list(roots),
            fail_closed=True,
            fail_closed_reasons=reasons,
        )

    changed_modules, reasons = resolve_changed_src_modules(
        changed_files,
        repo_root,
        package_name,
        candidate_roots=roots,
        ignored_prefixes=ignored_prefixes,
    )
    if reasons:
        return _fail_closed(reasons)

    # Forced-keep: a directly-changed test file keeps its own directory,
    # independent of any src closure (module-grain parity for test-only edits).
    forced_keys = _forced_keep_keys(changed_files, roots, patterns)

    def _is_forced(candidate: str) -> bool:
        return any(candidate.startswith(key) or candidate == key for key in forced_keys)

    if not changed_modules:
        if not forced_keys:
            # Nothing resolvable at all (unrecognized/ambiguous paths,
            # separately-gated-only, or a metadata-only pyproject.toml alone) —
            # the conservative whole-tree fallback, never an empty or
            # near-empty false-confidence selection. Docs-only diffs are
            # handled by the caller BEFORE this function is reached.
            return _result(selected_files=list(roots))
        # Test-only change(s), no src impact to compute a closure over: select
        # exactly the changed test directories.
        candidates = [
            c
            for c in collect_candidate_files(roots, repo_root, patterns)
            if _is_forced(c)
        ]
        return _result(
            selected_files=candidates,
            candidate_file_count=len(candidates),
        )

    stale = graph_staleness_reason(repo_root, package_name)
    if stale is not None:
        return _fail_closed([stale])

    try:
        import grimp  # deliberate lazy import: the ``test-selection`` extra
        from grimp.exceptions import GrimpException
    except ImportError as exc:
        return _fail_closed([f"grimp is not installed (test-selection extra): {exc!r}"])

    try:
        graph = grimp.build_graph(package_name, cache_dir=None)
    except (
        GrimpException,
        ImportError,
        OSError,
        RuntimeError,
        SyntaxError,
        ValueError,
    ) as exc:
        # Any graph build failure must fail closed to the whole-tree sentinel.
        return _fail_closed([f"import graph build failed: {exc!r}"])

    impacted, closure_reasons = compute_impacted_modules(graph, changed_modules)
    if closure_reasons:
        return _fail_closed(closure_reasons)

    candidates = collect_candidate_files(roots, repo_root, patterns)
    forced_keep = {c for c in candidates if _is_forced(c)}

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

    selected, _kept = refine_candidates(
        candidate_imports, impacted, frozenset(forced_keep)
    )

    return _result(
        selected_files=selected,
        candidate_file_count=len(candidates),
        impacted_module_count=len(impacted),
    )
