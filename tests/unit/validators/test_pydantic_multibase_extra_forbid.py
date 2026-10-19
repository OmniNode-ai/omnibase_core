# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17903: static config merging must agree with Pydantic's direct bases."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from omnibase_core.models.validation.model_extra_forbid_finding import (
    STATUS_UNRESOLVED,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env
from omnibase_core.validators.pydantic_extra_forbid import main, scan_paths

pytestmark = pytest.mark.unit

BASES = (
    "from pydantic import BaseModel, ConfigDict\n"
    "class A(BaseModel):\n"
    '    model_config = ConfigDict(extra="forbid")\n'
    "class B(BaseModel):\n"
    '    model_config = ConfigDict(extra="ignore")\n'
)

CASES = [
    pytest.param("class C(A, B): pass\n", id="later-ignore"),
    pytest.param("class C(B, A): pass\n", id="later-forbid"),
    pytest.param(
        "class Left(A): pass\nclass Right(B): pass\nclass C(Left, Right): pass\n",
        id="indirect-ignore",
    ),
    pytest.param(
        "class Left(A): pass\nclass Right(B): pass\nclass C(Right, Left): pass\n",
        id="indirect-forbid",
    ),
    pytest.param(
        "class Left(A):\n"
        '    model_config = ConfigDict(extra="ignore")\n'
        "class Right(A): pass\nclass C(Left, Right): pass\n",
        id="diamond-reuses-grandparent-config",
    ),
    pytest.param(
        "class Left(A): pass\nclass Right(A): pass\nclass C(Left, Right): pass\n",
        id="diamond-shared-grandparent",
    ),
    pytest.param(
        "class Empty(BaseModel): pass\nclass C(A, Empty): pass\n",
        id="absent-extra-does-not-overwrite",
    ),
    pytest.param(
        'class C(A, B):\n    model_config = ConfigDict(extra="forbid")\n',
        id="local-config-wins",
    ),
    pytest.param('class C(A, B, extra="forbid"): pass\n', id="class-keyword-wins"),
]


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_extra(tmp_path: Path, source: str) -> str:
    """Read the oracle from a real Pydantic class, including its merged config."""
    path = tmp_path / "oracle.py"
    path.write_text(source, encoding="utf-8")
    module = _load_module(path, "oracle")
    return str(module.C.model_config["extra"])


@pytest.mark.parametrize("child", CASES)
def test_multibase_matches_pydantic(tmp_path: Path, child: str) -> None:
    source = BASES + child
    path = tmp_path / "models.py"
    path.write_text(source, encoding="utf-8")
    expected = _runtime_extra(tmp_path, source)

    finding = next(
        f for f in scan_paths([path], use_runtime=False) if f.class_name == "C"
    )

    assert finding.effective_extra == expected
    assert finding.is_violation == (expected != "forbid")


@pytest.mark.parametrize("order", ["A, Missing", "Missing, A"])
def test_unresolved_base_fails_closed_in_either_order(
    tmp_path: Path, order: str
) -> None:
    path = tmp_path / "models.py"
    path.write_text(BASES + f"class C({order}): pass\n", encoding="utf-8")

    finding = next(
        f for f in scan_paths([path], use_runtime=False) if f.class_name == "C"
    )

    assert finding.status == STATUS_UNRESOLVED
    assert finding.is_violation


@pytest.mark.parametrize("base", ["(B if True else A)", "*[B]"])
def test_unresolved_base_expression_fails_closed(tmp_path: Path, base: str) -> None:
    source = BASES + f"class C(A, {base}): pass\n"
    path = tmp_path / "models.py"
    path.write_text(source, encoding="utf-8")
    assert _runtime_extra(tmp_path, source) == "ignore"

    finding = next(
        f for f in scan_paths([path], use_runtime=False) if f.class_name == "C"
    )

    assert finding.status == STATUS_UNRESOLVED
    assert finding.is_violation


@pytest.mark.parametrize("order", ["A, B", "B, A"])
@pytest.mark.parametrize(
    "config",
    [
        "permissive",
        "ConfigDict(**permissive)",
        '{"extra": "forbid", **permissive}',
        '{**permissive, "extra": "forbid"}',
        'make_config(extra="forbid")',
    ],
)
def test_unresolved_base_config_fails_closed(
    tmp_path: Path, order: str, config: str
) -> None:
    source = (
        'permissive = {"extra": "ignore"}\n'
        "def make_config(**kwargs): return permissive\n"
        + BASES.replace('ConfigDict(extra="ignore")', config)
        + f"class C({order}): pass\n"
    )
    path = tmp_path / "models.py"
    path.write_text(source, encoding="utf-8")
    expected = _runtime_extra(tmp_path, source)

    finding = next(
        f for f in scan_paths([path], use_runtime=False) if f.class_name == "C"
    )

    # Unknown configs can conservatively reject a compliant runtime class, but
    # must never allow one that Pydantic actually makes permissive.
    if finding.status == STATUS_UNRESOLVED:
        assert finding.is_violation
    else:
        assert finding.effective_extra == expected
        assert finding.is_violation == (expected != "forbid")


@pytest.mark.parametrize("order", ["A, B", "B, A"])
@pytest.mark.parametrize("computed", [False, True], ids=["literal", "computed"])
@pytest.mark.parametrize("alternate", [False, True], ids=["index", "alternate-index"])
def test_snapshot_gate_ignores_worktree_and_module_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    order: str,
    computed: bool,
    alternate: bool,
) -> None:
    """The index consumer scans its snapshot without importing the live package."""
    snapshot = tmp_path / "selected" / "src" / "pkg"
    worktree = tmp_path / "worktree" / "src" / "pkg"
    worktree.mkdir(parents=True)
    (worktree / "__init__.py").write_text("", encoding="utf-8")
    snapshot.parents[1].mkdir(parents=True)
    selected_bases = (
        'permissive = {"extra": "ignore"}\n'
        + BASES.replace('ConfigDict(extra="ignore")', "ConfigDict(**permissive)")
        if computed
        else BASES
    )
    selected_child = f"from .bases import A, B\nclass C({order}): pass\n"
    (worktree / "bases.py").write_text(selected_bases, encoding="utf-8")
    (worktree / "child.py").write_text(selected_child, encoding="utf-8")
    repo = worktree.parents[1]

    def git(*args: str, selected: bool = False) -> None:
        subprocess.run(
            ["git", "-C", str(repo), *args],
            env={
                **scrub_git_location_env(),
                **(
                    {"GIT_INDEX_FILE": str(alt_index)} if selected and alternate else {}
                ),
            },
            check=True,
            text=True,
        )

    git("init", "-q")
    index_path = repo / ".git" / "index"
    alt_index = repo / ".git" / "selected-index"
    if alternate:
        # The real index has the opposite base configs: choosing it would flip
        # the literal child's verdict. Stage selected bytes only into the alt index.
        (worktree / "bases.py").write_text(
            BASES.replace('extra="forbid"', 'extra="allow"')
            .replace('extra="ignore"', 'extra="forbid"')
            .replace('extra="allow"', 'extra="ignore"'),
            encoding="utf-8",
        )
        git("add", "src")
        (worktree / "bases.py").write_text(selected_bases, encoding="utf-8")
    git("add", "src", selected=True)
    git("checkout-index", "--all", f"--prefix={snapshot.parents[1]}/", selected=True)
    real_before = index_path.read_bytes()
    selected_index = alt_index if alternate else index_path
    selected_before = selected_index.read_bytes()
    divergent = BASES.replace('extra="ignore"', 'extra="forbid"')
    (worktree / "bases.py").write_text(divergent, encoding="utf-8")
    (worktree / "child.py").write_text(selected_child, encoding="utf-8")
    monkeypatch.syspath_prepend(str(worktree.parent))
    cached = _load_module(worktree / "bases.py", "pkg.bases")
    monkeypatch.setitem(sys.modules, "pkg.bases", cached)
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text('violations: ["pkg.bases:B"]\n', encoding="utf-8")
    waivers = tmp_path / "waivers.yaml"
    waivers.write_text("waivers: []\n", encoding="utf-8")
    expected = _runtime_extra(tmp_path, selected_bases + f"class C({order}): pass\n")

    result = main(
        [
            str(snapshot),
            "--no-runtime",
            "--baseline",
            str(baseline),
            "--waivers",
            str(waivers),
        ]
    )

    assert result == int(computed or expected != "forbid")
    if result:
        assert "pkg.child:C" in capsys.readouterr().err
    assert sys.modules["pkg.bases"] is cached
    assert index_path.read_bytes() == real_before
    assert selected_index.read_bytes() == selected_before
