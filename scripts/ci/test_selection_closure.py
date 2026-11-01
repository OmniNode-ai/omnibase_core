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

OMN-14206: the governing (non-shadow) closure primitive and its helpers moved
into the wheel (``omnibase_core.nodes.node_test_selector_compute.closure_selector``)
so other repositories consume it without a copy; they are re-exported here.
Only the shadow report and ``compute_shadow_closure`` remain script-side.

No new YAML/config surface is introduced, so the OMN-14897 duplicate-key
last-wins hole cannot re-open here: the only config parse on this path remains
``ModelAdjacencyMap.from_yaml_text`` (duplicate-key-rejecting, fail-closed).
"""

from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

# OMN-14206: the governing closure primitive ships in the wheel; this module
# re-exports it so every existing ``scripts.ci.test_selection_closure`` caller
# and the shadow report below share ONE implementation (no fork).
from omnibase_core.models.nodes.test_selector.model_closure_selection import (
    ModelClosureSelection,
)
from omnibase_core.nodes.node_test_selector_compute.closure_selector import (
    DYNAMIC_IMPORT_MARKERS,
    PACKAGE_NAME,
    PYPROJECT_PATH,
    _conftest_chain_imports,
    collect_candidate_files,
    collect_direct_imports,
    compute_closure_selection,
    compute_impacted_modules,
    graph_staleness_reason,
    refine_candidates,
    resolve_changed_src_modules,
)
from scripts.ci.test_selection_models import (
    EnumFullSuiteReason,
    ModelTestSelection,
)

__all__ = [
    "DYNAMIC_IMPORT_MARKERS",
    "PACKAGE_NAME",
    "PYPROJECT_PATH",
    "ModelClosureSelection",
    "ModelShadowClosureReport",
    "collect_direct_imports",
    "compute_closure_selection",
    "compute_impacted_modules",
    "compute_shadow_closure",
    "graph_staleness_reason",
    "refine_candidates",
    "resolve_changed_src_modules",
]

TEST_UNIT_PREFIX = "tests/unit/"
TEST_INTEGRATION_PREFIX = "tests/integration/"


def _collect_candidate_files(roots: list[str], repo_root: Path) -> list[str]:
    return collect_candidate_files(roots, repo_root)


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
