# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the OMN-14921 file-grain closure SHADOW module.

Three layers:
  1. Pure refinement + changed-file resolution (no grimp, no filesystem graph).
  2. Real grimp graphs over synthetic packages — including the seeded
     dependency-edge RED→GREEN proof (the test is vacuous if the pre-edge graph
     already selects the dependent's test, so the RED half asserts it does NOT).
  3. Fail-closed end-to-end: every ambiguity forces narrowed=False with the
     file-grain set pinned to the full candidate set (module-grain behavior).

Shadow invariance (the returned selection never changes) is covered in
``test_detect_test_paths.py`` at the CLI/main layer, per escalation trigger.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from scripts.ci.test_selection_closure import (
    ModelShadowClosureReport,
    collect_direct_imports,
    compute_impacted_modules,
    compute_shadow_closure,
    graph_staleness_reason,
    refine_candidates,
    resolve_changed_src_modules,
)
from scripts.ci.test_selection_models import ModelTestSelection

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]


def _smart_selection(paths: list[str]) -> ModelTestSelection:
    return ModelTestSelection(
        selected_paths=paths,
        split_count=1,
        is_full_suite=False,
        full_suite_reason=None,
        matrix=[1],
    )


def _full_suite_selection(reason: str) -> ModelTestSelection:
    return ModelTestSelection(
        selected_paths=["tests/"],
        split_count=40,
        is_full_suite=True,
        full_suite_reason=reason,  # type: ignore[arg-type]
        matrix=list(range(1, 41)),
    )


# ---------------------------------------------------------------------------
# 1. Pure refinement
# ---------------------------------------------------------------------------


def test_refine_selects_only_import_intersecting_files() -> None:
    candidates = {
        "tests/unit/m/test_hit.py": frozenset({"pkg.a"}),
        "tests/unit/m/test_miss.py": frozenset({"pkg.b"}),
    }
    selected, kept = refine_candidates(candidates, frozenset({"pkg.a"}), frozenset())
    assert selected == ["tests/unit/m/test_hit.py"]
    assert kept == []


def test_refine_keeps_unparseable_file_fail_closed() -> None:
    candidates: dict[str, frozenset[str] | None] = {
        "tests/unit/m/test_broken.py": None,
        "tests/unit/m/test_miss.py": frozenset({"pkg.b"}),
    }
    selected, kept = refine_candidates(candidates, frozenset({"pkg.a"}), frozenset())
    assert selected == ["tests/unit/m/test_broken.py"]
    assert kept == ["tests/unit/m/test_broken.py"]


def test_refine_keeps_zero_import_file_fail_closed() -> None:
    # A subprocess-style test with no package imports cannot be cleared by the
    # import graph — it must be kept.
    candidates: dict[str, frozenset[str] | None] = {
        "tests/unit/m/test_subprocess.py": frozenset(),
    }
    selected, kept = refine_candidates(candidates, frozenset({"pkg.a"}), frozenset())
    assert selected == ["tests/unit/m/test_subprocess.py"]
    assert kept == ["tests/unit/m/test_subprocess.py"]


def test_refine_forced_keep_wins_over_negative_evidence() -> None:
    candidates = {"tests/unit/m/test_miss.py": frozenset({"pkg.b"})}
    selected, kept = refine_candidates(
        candidates, frozenset({"pkg.a"}), frozenset({"tests/unit/m/test_miss.py"})
    )
    assert selected == ["tests/unit/m/test_miss.py"]
    assert kept == ["tests/unit/m/test_miss.py"]


# ---------------------------------------------------------------------------
# 1b. Changed-file resolution — every unresolvable shape is a reason
# ---------------------------------------------------------------------------


def _write(root: Path, rel: str, content: str = "") -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_resolve_maps_module_and_package_init(tmp_path: Path) -> None:
    _write(tmp_path, "src/fakepkg/mod.py", "x = 1\n")
    _write(tmp_path, "src/fakepkg/sub/__init__.py", "")
    modules, reasons = resolve_changed_src_modules(
        ["src/fakepkg/mod.py", "src/fakepkg/sub/__init__.py"],
        tmp_path,
        package_name="fakepkg",
    )
    assert reasons == []
    assert modules == {"fakepkg.mod", "fakepkg.sub"}


def test_resolve_non_python_src_file_fails_closed(tmp_path: Path) -> None:
    _write(tmp_path, "src/fakepkg/nodes/contract.yaml", "kind: COMPUTE\n")
    modules, reasons = resolve_changed_src_modules(
        ["src/fakepkg/nodes/contract.yaml"], tmp_path, package_name="fakepkg"
    )
    assert modules == set()
    assert len(reasons) == 1 and "invisible to the import graph" in reasons[0]


def test_resolve_deleted_src_file_fails_closed(tmp_path: Path) -> None:
    modules, reasons = resolve_changed_src_modules(
        ["src/fakepkg/gone.py"], tmp_path, package_name="fakepkg"
    )
    assert modules == set()
    assert len(reasons) == 1 and "missing from working tree" in reasons[0]


def test_resolve_dynamic_import_marker_fails_closed(tmp_path: Path) -> None:
    _write(tmp_path, "src/fakepkg/dyn.py", "import importlib\n")
    modules, reasons = resolve_changed_src_modules(
        ["src/fakepkg/dyn.py"], tmp_path, package_name="fakepkg"
    )
    assert modules == set()
    assert len(reasons) == 1 and "dynamic-import marker" in reasons[0]


def test_resolve_unclassifiable_file_fails_closed(tmp_path: Path) -> None:
    modules, reasons = resolve_changed_src_modules(
        ["Makefile"], tmp_path, package_name="fakepkg"
    )
    assert modules == set()
    assert len(reasons) == 1 and "cannot be resolved" in reasons[0]


def test_resolve_inert_files_contribute_nothing(tmp_path: Path) -> None:
    # Docs, integration tests, pyproject (already content-classified metadata-only
    # to reach the smart path), and tests/unit (forced-keep, handled by caller).
    modules, reasons = resolve_changed_src_modules(
        [
            "docs/x.md",
            "README.md",
            "tests/integration/test_x.py",
            "tests/unit/m/test_y.py",
            "pyproject.toml",
        ],
        tmp_path,
        package_name="fakepkg",
    )
    assert modules == set()
    assert reasons == []


# ---------------------------------------------------------------------------
# 1c. Test-file import collection
# ---------------------------------------------------------------------------


def test_collect_direct_imports_records_both_module_and_attr(tmp_path: Path) -> None:
    f = tmp_path / "test_x.py"
    f.write_text(
        "import fakepkg.a\nfrom fakepkg.b import Thing\nimport os\n", encoding="utf-8"
    )
    imports = collect_direct_imports(f, package_name="fakepkg")
    assert imports == frozenset({"fakepkg.a", "fakepkg.b", "fakepkg.b.Thing"})


def test_collect_direct_imports_unparseable_returns_none(tmp_path: Path) -> None:
    f = tmp_path / "test_broken.py"
    f.write_text("def broken(:\n", encoding="utf-8")
    assert collect_direct_imports(f, package_name="fakepkg") is None


def test_collect_direct_imports_relative_import_returns_none(tmp_path: Path) -> None:
    f = tmp_path / "test_rel.py"
    f.write_text("from .helpers import x\n", encoding="utf-8")
    assert collect_direct_imports(f, package_name="fakepkg") is None


def test_collect_direct_imports_dynamic_marker_returns_none(tmp_path: Path) -> None:
    f = tmp_path / "test_dyn.py"
    f.write_text("mod = __import__('fakepkg.a')\n", encoding="utf-8")
    assert collect_direct_imports(f, package_name="fakepkg") is None


# ---------------------------------------------------------------------------
# 2. Real grimp graphs over synthetic packages
# ---------------------------------------------------------------------------


def _make_pkg(root: Path, pkg: str, files: dict[str, str]) -> None:
    pkg_dir = root / pkg
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    for rel, content in files.items():
        _write(pkg_dir.parent, f"{pkg}/{rel}", content)


def _build_graph(pkg: str):
    import grimp

    importlib.invalidate_caches()
    return grimp.build_graph(pkg, cache_dir=None)


def test_seeded_dependency_edge_red_then_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ticket AC shape (OMN-14921 #4): introduce import edge A→B, change B, and
    prove A's test is newly selected — RED (not selected) before the edge exists,
    GREEN (selected) after. Vacuity guard: the pre-edge assertion is the RED half."""
    pkg = "omn14921_seeded_edge_pkg"
    _make_pkg(tmp_path, pkg, {"a.py": "", "b.py": ""})
    monkeypatch.syspath_prepend(str(tmp_path))

    candidates = {"tests/unit/x/test_a.py": frozenset({f"{pkg}.a"})}

    impacted_before, reasons_before = compute_impacted_modules(
        _build_graph(pkg), {f"{pkg}.b"}
    )
    assert reasons_before == []
    selected_before, _ = refine_candidates(candidates, impacted_before, frozenset())
    assert selected_before == [], "RED half violated: selected without the A->B edge"

    (tmp_path / pkg / "a.py").write_text(f"import {pkg}.b\n", encoding="utf-8")
    impacted_after, reasons_after = compute_impacted_modules(
        _build_graph(pkg), {f"{pkg}.b"}
    )
    assert reasons_after == []
    selected_after, _ = refine_candidates(candidates, impacted_after, frozenset())
    assert selected_after == ["tests/unit/x/test_a.py"]


def test_changed_package_init_contaminates_descendants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Importing any submodule executes ancestor __init__s, so a changed package
    # __init__ must impact every descendant and their importers.
    pkg = "omn14921_init_pkg"
    _make_pkg(tmp_path, pkg, {"sub/__init__.py": "", "sub/leaf.py": ""})
    monkeypatch.syspath_prepend(str(tmp_path))
    impacted, reasons = compute_impacted_modules(_build_graph(pkg), {f"{pkg}.sub"})
    assert reasons == []
    assert f"{pkg}.sub.leaf" in impacted


def test_changed_module_absent_from_graph_is_a_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = "omn14921_absent_pkg"
    _make_pkg(tmp_path, pkg, {"a.py": ""})
    monkeypatch.syspath_prepend(str(tmp_path))
    _impacted, reasons = compute_impacted_modules(_build_graph(pkg), {f"{pkg}.ghost"})
    assert len(reasons) == 1 and "not present in import graph" in reasons[0]


# ---------------------------------------------------------------------------
# 2b. Hermetic end-to-end over a synthetic repo
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path, pkg: str, conftest: str | None = None) -> Path:
    """src/<pkg>/{core,leaf,other}.py with core->leaf; four unit tests."""
    repo = tmp_path / "repo"
    _write(repo, f"src/{pkg}/__init__.py", "")
    _write(repo, f"src/{pkg}/leaf.py", "X = 1\n")
    _write(repo, f"src/{pkg}/core.py", f"import {pkg}.leaf\n")
    _write(repo, f"src/{pkg}/other.py", "Y = 2\n")
    _write(repo, "tests/unit/m/test_core.py", f"import {pkg}.core\n")
    _write(repo, "tests/unit/m/test_leaf.py", f"from {pkg}.leaf import X\n")
    _write(repo, "tests/unit/m/test_other.py", f"import {pkg}.other\n")
    _write(repo, "tests/unit/m/test_subprocess.py", "import subprocess\n")
    if conftest is not None:
        _write(repo, "tests/unit/m/conftest.py", conftest)
    return repo


def test_end_to_end_narrows_to_import_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = "omn14921_e2e_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    report = compute_shadow_closure(
        [f"src/{pkg}/leaf.py"],
        _smart_selection(["tests/unit/m/"]),
        repo,
        package_name=pkg,
    )
    assert report.fail_closed_reasons == []
    assert report.narrowed is True
    assert report.candidate_file_count == 4
    # test_core (imports core -> leaf), test_leaf (direct), test_subprocess
    # (kept fail-closed: zero package imports); test_other is excluded.
    assert report.file_grain_files == [
        "tests/unit/m/test_core.py",
        "tests/unit/m/test_leaf.py",
        "tests/unit/m/test_subprocess.py",
    ]
    assert report.delta_file_count == 1
    assert report.kept_fail_closed_count == 1
    assert report.shadow_only is True


def test_end_to_end_conftest_chain_carries_import_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # pytest fixture injection is not an import edge: a conftest importing core
    # makes EVERY test under it depend on core's closure — so test_other must now
    # be kept when leaf changes.
    pkg = "omn14921_conftest_pkg"
    repo = _make_repo(tmp_path, pkg, conftest=f"import {pkg}.core\n")
    monkeypatch.syspath_prepend(str(repo / "src"))
    report = compute_shadow_closure(
        [f"src/{pkg}/leaf.py"],
        _smart_selection(["tests/unit/m/"]),
        repo,
        package_name=pkg,
    )
    assert report.fail_closed_reasons == []
    assert "tests/unit/m/test_other.py" in report.file_grain_files
    assert report.file_grain_file_count == 4


def test_end_to_end_unparseable_conftest_keeps_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = "omn14921_badconftest_pkg"
    repo = _make_repo(tmp_path, pkg, conftest="def broken(:\n")
    monkeypatch.syspath_prepend(str(repo / "src"))
    report = compute_shadow_closure(
        [f"src/{pkg}/leaf.py"],
        _smart_selection(["tests/unit/m/"]),
        repo,
        package_name=pkg,
    )
    assert report.fail_closed_reasons == []
    assert report.file_grain_file_count == report.candidate_file_count == 4
    assert report.kept_fail_closed_count == 4
    assert report.narrowed is False


def test_end_to_end_changed_test_dir_is_force_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A changed unit-test file keeps its whole directory (module-grain parity for
    # test-only edits): no narrowing below the directory the change touched.
    pkg = "omn14921_forcekeep_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    report = compute_shadow_closure(
        [f"src/{pkg}/leaf.py", "tests/unit/m/test_other.py"],
        _smart_selection(["tests/unit/m/"]),
        repo,
        package_name=pkg,
    )
    assert report.fail_closed_reasons == []
    assert report.file_grain_file_count == report.candidate_file_count == 4
    assert report.narrowed is False


# ---------------------------------------------------------------------------
# 3. Fail-closed end-to-end + skip semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changed_file", "reason_fragment"),
    [
        ("src/{pkg}/nodes/contract.yaml", "invisible to the import graph"),
        ("src/{pkg}/does_not_exist.py", "missing from working tree"),
        ("scripts/random_tool.py", "cannot be resolved"),
    ],
)
def test_fail_closed_pins_file_grain_to_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_file: str,
    reason_fragment: str,
) -> None:
    pkg = "omn14921_failclosed_pkg"
    repo = _make_repo(tmp_path, pkg)
    _write(repo, f"src/{pkg}/nodes/contract.yaml", "kind: COMPUTE\n")
    monkeypatch.syspath_prepend(str(repo / "src"))
    report = compute_shadow_closure(
        [changed_file.format(pkg=pkg)],
        _smart_selection(["tests/unit/m/"]),
        repo,
        package_name=pkg,
    )
    assert report.narrowed is False
    assert any(reason_fragment in r for r in report.fail_closed_reasons)
    assert report.file_grain_file_count == report.candidate_file_count == 4


def test_graph_build_failure_fails_closed(tmp_path: Path) -> None:
    pkg = "omn14921_never_importable_pkg"
    repo = _make_repo(tmp_path, pkg)
    # Deliberately NOT on sys.path → staleness guard reports not importable.
    report = compute_shadow_closure(
        [f"src/{pkg}/leaf.py"],
        _smart_selection(["tests/unit/m/"]),
        repo,
        package_name=pkg,
    )
    assert report.narrowed is False
    assert report.fail_closed_reasons  # not importable / cannot build graph
    assert report.file_grain_file_count == report.candidate_file_count


def test_graph_staleness_detected_for_wrong_repo_root(tmp_path: Path) -> None:
    # omnibase_core resolves to the real checkout, never to tmp_path — the guard
    # must refuse to narrow rather than compute a closure over the WRONG source.
    # (Live hazard: an ambient PYTHONPATH shadowing a worktree checkout.)
    reason = graph_staleness_reason(tmp_path, package_name="omnibase_core")
    assert reason is not None and "STALE" in reason


def test_graph_staleness_none_for_resolved_tree() -> None:
    spec = importlib.util.find_spec("omnibase_core")
    assert spec is not None and spec.origin is not None
    resolved_root = Path(spec.origin).resolve().parents[2]
    assert graph_staleness_reason(resolved_root, package_name="omnibase_core") is None


@pytest.mark.parametrize(
    "reason",
    [
        "feature_flag_off",
        "main_branch",
        "merge_group",
        "scheduled",
        "test_infrastructure",
    ],
)
def test_shadow_skips_unconditional_escalations(reason: str, tmp_path: Path) -> None:
    report = compute_shadow_closure(
        ["src/omnibase_core/cli/foo.py"],
        _full_suite_selection(reason),
        tmp_path,
    )
    assert report.skipped_reason is not None
    assert report.narrowed is False
    assert report.file_grain_files == []
    assert report.module_grain_is_full_suite is True
    assert report.module_grain_reason == reason


def test_shadow_skips_docs_only_empty_selection(tmp_path: Path) -> None:
    report = compute_shadow_closure(
        ["docs/x.md"],
        _smart_selection([]),
        tmp_path,
    )
    assert report.skipped_reason is not None
    assert report.narrowed is False


def test_shared_module_escalation_gets_unit_tree_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # SHARED_MODULE escalation is shadow-measured over the whole unit tree — the
    # data the adjacency YAML names as the precondition for ever demoting a
    # shared module. Here the changed file resolves cleanly, so the shadow
    # narrows within the synthetic unit tree.
    pkg = "omn14921_shared_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    report = compute_shadow_closure(
        [f"src/{pkg}/leaf.py"],
        _full_suite_selection("shared_module"),
        repo,
        package_name=pkg,
    )
    assert report.skipped_reason is None
    assert report.candidate_file_count == 4
    assert report.narrowed is True
    assert "tests/unit/m/test_other.py" not in report.file_grain_files


def test_report_json_roundtrip(tmp_path: Path) -> None:
    report = compute_shadow_closure(["docs/x.md"], _smart_selection([]), tmp_path)
    parsed = ModelShadowClosureReport.model_validate(
        json.loads(report.model_dump_json())
    )
    assert parsed == report


# ---------------------------------------------------------------------------
# 4. Real-repo integration: the closure narrows a leaf util change
# ---------------------------------------------------------------------------


def test_real_repo_leaf_util_change_narrows_within_module_grain() -> None:
    """Import-graph-closure precision on the REAL tree: a leaf util edit keeps
    only the test files whose (conftest-chain-unioned) imports intersect the
    reverse closure — strictly fewer than the whole tests/unit/utils/ directory
    module grain runs today. Uses the resolved package root so the graph is
    never computed over a shadowed checkout."""
    spec = importlib.util.find_spec("omnibase_core")
    assert spec is not None and spec.origin is not None
    resolved_root = Path(spec.origin).resolve().parents[2]

    changed = "src/omnibase_core/utils/util_uuid_utilities.py"
    assert (resolved_root / changed).is_file()

    report = compute_shadow_closure(
        [changed],
        _smart_selection(["tests/unit/utils/"]),
        resolved_root,
    )
    assert report.fail_closed_reasons == []
    assert report.narrowed is True
    assert 0 < report.file_grain_file_count < report.candidate_file_count
    # All selected files stay inside the module-grain candidate scope.
    assert all(f.startswith("tests/unit/utils/") for f in report.file_grain_files)
    # The direct test for the changed util is positively selected.
    assert "tests/unit/utils/test_uuid_utilities.py" in report.file_grain_files
