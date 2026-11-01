# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-14206: the file-grain closure selector ships in the wheel and takes
per-repository candidate test roots.

Before this change the closure primitive lived in ``scripts/ci`` (not part of
the ``omnibase_core`` wheel) and hardcoded ``tests/unit/`` as its only
candidate root. omnibase_infra and omnimarket could not consume it without a
copy, and a copy narrowing over ``tests/unit/`` alone fails OPEN on omnimarket
(3,692 test files, only 1,351 under ``tests/unit``: the other 2,341 can never
appear in a narrowed selection).

RED/GREEN shape: every test imports the packaged module, which did not exist
before; the root-sensitivity tests also pin the default (``tests/unit/`` only)
so the new parameter is proven to be what changes the answer.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.test_selector.model_closure_selection import (
    ModelClosureSelection,
)
from omnibase_core.nodes.node_test_selector_compute import closure_selector
from omnibase_core.nodes.node_test_selector_compute.closure_selector import (
    DEFAULT_CANDIDATE_ROOTS,
    collect_candidate_files,
    compute_closure_selection,
    normalize_candidate_roots,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]


def _write(root: Path, rel: str, content: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path, pkg: str) -> Path:
    """src/<pkg>/{core,leaf,other}.py (core->leaf) and tests under three roots."""
    repo = tmp_path / "repo"
    _write(repo, f"src/{pkg}/__init__.py")
    _write(repo, f"src/{pkg}/leaf.py", "X = 1\n")
    _write(repo, f"src/{pkg}/core.py", f"import {pkg}.leaf\n")
    _write(repo, f"src/{pkg}/other.py", "Y = 2\n")
    _write(repo, "tests/unit/m/test_core.py", f"import {pkg}.core\n")
    _write(repo, "tests/unit/m/test_other.py", f"import {pkg}.other\n")
    _write(repo, "tests/nodes/n/test_node_leaf.py", f"from {pkg}.leaf import X\n")
    _write(repo, "tests/nodes/n/test_node_other.py", f"import {pkg}.other\n")
    _write(repo, "tests/nodes/n/node_leaf_test.py", f"from {pkg}.leaf import X\n")
    _write(repo, "tests/integration/test_it.py", f"import {pkg}.leaf\n")
    return repo


# ---------------------------------------------------------------------------
# 1. Packaging: the selector is wheel content with no scripts/ dependency
# ---------------------------------------------------------------------------


def test_closure_selector_lives_in_the_wheel_package_tree() -> None:
    module_file = Path(closure_selector.__file__).resolve()
    wheel_root = (REPO_ROOT / "src" / "omnibase_core").resolve()
    assert wheel_root in module_file.parents, (
        "closure selector must live under src/omnibase_core so "
        "[tool.hatch.build.targets.wheel] packages = ['src/omnibase_core'] ships it"
    )


def test_closure_selector_does_not_import_from_scripts() -> None:
    """A wheel consumer has no ``scripts`` package: any import of it would make
    the packaged selector unusable (or silently shadowed by a same-named dir)."""
    modules = [
        closure_selector,
        importlib.import_module(
            "omnibase_core.models.nodes.test_selector.model_closure_selection"
        ),
    ]
    for module in modules:
        tree = ast.parse(Path(str(module.__file__)).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert name.split(".")[0] != "scripts", (
                    f"{module.__name__} imports {name}: not available in the wheel"
                )


def test_scripts_shim_reexports_the_packaged_primitive() -> None:
    """One implementation: the CI oracle's module re-exports, never forks."""
    from scripts.ci import test_selection_closure as shim

    assert shim.compute_closure_selection is compute_closure_selection
    assert shim.ModelClosureSelection is ModelClosureSelection


# ---------------------------------------------------------------------------
# 2. Candidate roots are configurable per repository
# ---------------------------------------------------------------------------


def test_default_candidate_roots_are_the_historical_unit_tree() -> None:
    assert DEFAULT_CANDIDATE_ROOTS == ("tests/unit/",)


def test_default_roots_cannot_see_tests_outside_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RED half: with the default root, a dependent test under tests/nodes/ is
    invisible. This is the omnibase_infra/omnimarket fail-open the parameter fixes."""
    pkg = "omn14206_default_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    result = compute_closure_selection(
        [f"src/{pkg}/leaf.py"], repo_root=repo, package_name=pkg
    )
    assert result.fail_closed is False, result.fail_closed_reasons
    assert result.selected_files == ["tests/unit/m/test_core.py"]
    assert result.candidate_file_count == 2


def test_configured_roots_select_dependents_in_every_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GREEN half: same repo, same change, roots extended to tests/nodes/."""
    pkg = "omn14206_roots_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    result = compute_closure_selection(
        [f"src/{pkg}/leaf.py"],
        repo_root=repo,
        package_name=pkg,
        candidate_roots=("tests/unit/", "tests/nodes/"),
    )
    assert result.fail_closed is False, result.fail_closed_reasons
    assert result.selected_files == [
        "tests/nodes/n/test_node_leaf.py",
        "tests/unit/m/test_core.py",
    ]
    assert result.candidate_file_count == 4


def test_configured_test_file_patterns_collect_suffix_named_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pkg = "omn14206_patterns_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    result = compute_closure_selection(
        [f"src/{pkg}/leaf.py"],
        repo_root=repo,
        package_name=pkg,
        candidate_roots=("tests/nodes/",),
        test_file_patterns=("test_*.py", "*_test.py"),
    )
    assert result.selected_files == [
        "tests/nodes/n/node_leaf_test.py",
        "tests/nodes/n/test_node_leaf.py",
    ]


def test_fail_closed_sentinel_is_the_configured_roots(tmp_path: Path) -> None:
    """Whole-tree fallback must cover EVERY configured root, not just tests/unit/."""
    repo = tmp_path / "repo"
    _write(repo, "src/fakepkg/__init__.py")
    result = compute_closure_selection(
        ["Makefile"],  # outside src/tests: unresolvable -> fail closed
        repo_root=repo,
        package_name="fakepkg",
        candidate_roots=("tests/unit/", "tests/nodes/"),
    )
    assert result.fail_closed is True
    assert result.selected_files == ["tests/unit/", "tests/nodes/"]


def test_default_fail_closed_sentinel_is_unchanged(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo, "src/fakepkg/__init__.py")
    result = compute_closure_selection(
        ["Makefile"], repo_root=repo, package_name="fakepkg"
    )
    assert result.fail_closed is True
    assert result.selected_files == ["tests/unit/"]


def test_changed_test_in_extra_root_force_keeps_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directly changed test keeps its sibling directory, in any configured root."""
    pkg = "omn14206_forced_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))
    result = compute_closure_selection(
        [f"src/{pkg}/leaf.py", "tests/nodes/n/test_node_other.py"],
        repo_root=repo,
        package_name=pkg,
        candidate_roots=("tests/unit/", "tests/nodes/"),
    )
    assert result.fail_closed is False, result.fail_closed_reasons
    assert "tests/nodes/n/test_node_other.py" in result.selected_files
    assert "tests/nodes/n/test_node_leaf.py" in result.selected_files
    assert "tests/unit/m/test_other.py" not in result.selected_files


def test_test_only_change_in_extra_root_selects_its_directory(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, "omn14206_testonly_pkg")
    result = compute_closure_selection(
        ["tests/nodes/n/test_node_other.py"],
        repo_root=repo,
        package_name="omn14206_testonly_pkg",
        candidate_roots=("tests/unit/", "tests/nodes/"),
    )
    assert result.fail_closed is False
    assert result.selected_files == [
        "tests/nodes/n/test_node_leaf.py",
        "tests/nodes/n/test_node_other.py",
    ]


def test_loose_test_file_directly_under_root_is_force_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed test sitting directly under a root has no subdirectory to keep:
    the file itself must stay selected, not be dropped for lack of an import edge."""
    pkg = "omn14206_loose_pkg"
    repo = _make_repo(tmp_path, pkg)
    _write(repo, "tests/unit/test_loose.py", "import subprocess\n")
    _write(repo, "tests/unit/test_loose_unrelated.py", f"import {pkg}.other\n")
    monkeypatch.syspath_prepend(str(repo / "src"))
    result = compute_closure_selection(
        [f"src/{pkg}/leaf.py", "tests/unit/test_loose.py"],
        repo_root=repo,
        package_name=pkg,
    )
    assert "tests/unit/test_loose.py" in result.selected_files
    assert "tests/unit/test_loose_unrelated.py" not in result.selected_files


def test_graph_build_failure_fails_closed_to_configured_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import grimp
    from grimp.exceptions import SourceSyntaxError

    pkg = "omn14206_buildfail_pkg"
    repo = _make_repo(tmp_path, pkg)
    monkeypatch.syspath_prepend(str(repo / "src"))

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise SourceSyntaxError(filename="x.py", lineno=1, text="def broken(:")

    monkeypatch.setattr(grimp, "build_graph", _boom)
    result = compute_closure_selection(
        [f"src/{pkg}/leaf.py"],
        repo_root=repo,
        package_name=pkg,
        candidate_roots=("tests/unit/", "tests/nodes/"),
    )
    assert result.fail_closed is True
    assert result.selected_files == ["tests/unit/", "tests/nodes/"]
    assert "import graph build failed" in result.fail_closed_reasons[0]


def test_changed_root_conftest_keeps_the_whole_root(tmp_path: Path) -> None:
    """A conftest directly under a root can affect every test below it."""
    repo = _make_repo(tmp_path, "omn14206_rootconf_pkg")
    _write(repo, "tests/nodes/conftest.py")
    result = compute_closure_selection(
        ["tests/nodes/conftest.py"],
        repo_root=repo,
        package_name="omn14206_rootconf_pkg",
        candidate_roots=("tests/unit/", "tests/nodes/"),
    )
    assert result.fail_closed is False
    assert result.selected_files == [
        "tests/nodes/n/test_node_leaf.py",
        "tests/nodes/n/test_node_other.py",
    ]


def test_changed_file_in_unconfigured_test_root_fails_closed(
    tmp_path: Path,
) -> None:
    """tests/nodes/ is not a candidate root here, so a change there is not
    resolvable and must not silently narrow."""
    repo = _make_repo(tmp_path, "omn14206_unconfigured_pkg")
    result = compute_closure_selection(
        ["tests/nodes/n/test_node_other.py"],
        repo_root=repo,
        package_name="omn14206_unconfigured_pkg",
    )
    assert result.fail_closed is True
    assert result.selected_files == ["tests/unit/"]


def test_ignored_prefixes_are_configurable(tmp_path: Path) -> None:
    """A repo whose separately-gated tree is not tests/integration/ names its own."""
    repo = _make_repo(tmp_path, "omn14206_ignored_pkg")
    _write(repo, "tests/e2e/test_e2e.py")
    result = compute_closure_selection(
        ["tests/e2e/test_e2e.py"],
        repo_root=repo,
        package_name="omn14206_ignored_pkg",
        ignored_prefixes=("tests/e2e/",),
    )
    assert result.fail_closed is False
    assert result.selected_files == ["tests/unit/"]


def test_collect_candidate_files_spans_all_roots_sorted(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, "omn14206_collect_pkg")
    assert collect_candidate_files(["tests/nodes/", "tests/unit/"], repo) == [
        "tests/nodes/n/test_node_leaf.py",
        "tests/nodes/n/test_node_other.py",
        "tests/unit/m/test_core.py",
        "tests/unit/m/test_other.py",
    ]


def test_collect_candidate_files_skips_missing_root(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, "omn14206_missing_pkg")
    assert collect_candidate_files(["tests/nope/"], repo) == []


# ---------------------------------------------------------------------------
# 3. Root validation: a malformed root must not become a silent empty universe
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        (),
        ("",),
        ("/abs/tests/",),
        ("../tests/",),
        ("tests/../../etc/",),
        ("tests/unit/", "tests/unit/sub/"),  # nested: double-counted candidates
    ],
)
def test_normalize_candidate_roots_rejects_malformed(bad: tuple[str, ...]) -> None:
    with pytest.raises(ModelOnexError):
        normalize_candidate_roots(bad)


def test_normalize_candidate_roots_adds_trailing_slash_and_dedups() -> None:
    assert normalize_candidate_roots(["tests/unit", "tests/nodes/", "tests/unit/"]) == (
        "tests/unit/",
        "tests/nodes/",
    )


def test_compute_closure_selection_rejects_malformed_roots(tmp_path: Path) -> None:
    with pytest.raises(ModelOnexError):
        compute_closure_selection(
            ["src/x.py"], repo_root=tmp_path, candidate_roots=("../tests/",)
        )


def test_result_model_is_frozen_and_forbids_extra() -> None:
    result = ModelClosureSelection(selected_files=["tests/unit/"], fail_closed=True)
    with pytest.raises(ValidationError):
        result.__setattr__("fail_closed", False)
    with pytest.raises(ValidationError):
        ModelClosureSelection.model_validate({"unknown_field": 1})
