# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the node-home rule and canonical-file-shape CLI (OMN-20702)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation import (
    ModelNodeHomeRatchetFinding,
    ModelNodeHomeRatchetRequest,
    ModelNodeHomeRatchetResult,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.matcher_node_home import (
    NODE_HOME_BASELINE,
    NodeHomeRule,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    INDEX,
    GitRepo,
    gather_node_home_request,
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]

NODE = "src/pkg/nodes/node_zz"
OLD_NODE = "src/pkg/nodes/node_old"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _write(repo: Path, path: str, text: str = "") -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _plant(repo: Path, directory: str = NODE) -> None:
    _write(repo, f"{directory}/contract.yaml", "name: planted\n")
    _write(repo, f"{directory}/handlers/__init__.py")


def _request(
    repo: Path, *, head: str = INDEX, base: str | None = "HEAD"
) -> ModelNodeHomeRatchetRequest:
    return gather_node_home_request(
        GitRepo(repo, env=scrub_git_location_env()), head, base
    )


def _check(repo: Path) -> ModelNodeHomeRatchetResult:
    _git(repo, "add", "-A")
    return NodeHomeRule().check(_request(repo))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "dev")
    _write(tmp_path, "pyproject.toml", '[project]\nname = "other_repo"\n')
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


def _commit_baseline(repo: Path) -> None:
    _plant(repo, OLD_NODE)
    _write(repo, NODE_HOME_BASELINE, f"{OLD_NODE}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "existing node baseline")


def test_refuses_new_node_contract_and_handlers(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _plant(repo)
    result = _check(repo)
    assert result.node_directories == (NODE,)
    assert _request(repo).renamed_paths == ()
    assert [(finding.code, finding.path) for finding in result.findings] == [
        ("node-outside-market", NODE)
    ]
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1
    assert f"  {NODE}: [node-home:node-outside-market] " in capsys.readouterr().err


def test_refuses_new_node_baselined_initial_tree_passes(repo: Path) -> None:
    _plant(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "pre-existing node without baseline")
    _write(repo, NODE_HOME_BASELINE, f"{NODE}\n")
    assert _check(repo).findings == ()
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 0


@pytest.mark.parametrize("bases", ["(object)", ""])
def test_refuses_new_node_class_only(repo: Path, bases: str) -> None:
    _write(
        repo,
        "src/pkg/node_class_only/impl.py",
        f"class NodeExample{bases}:\n    pass\n",
    )
    result = _check(repo)
    assert result.node_directories == ("src/pkg/node_class_only",)
    assert [finding.code for finding in result.findings] == ["node-outside-market"]


def test_refuses_new_node_bare_contract_is_not_node(repo: Path) -> None:
    _write(repo, "src/pkg/contracts/service/contract.yaml", "name: service\n")
    assert _check(repo).node_directories == ()
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 0


@pytest.mark.parametrize(
    ("directory", "files"),
    [
        ("src/pkg/deep/service", {"contract.yaml": "", "handler_impl.py": ""}),
        ("src/pkg/service", {"contract.yaml": "", "node.py": ""}),
        ("src/pkg/service", {"contract.yaml": "", "handlers/deep/impl.py": ""}),
        ("src/pkg/nodes/service", {"contract.yaml": ""}),
        (
            "src/pkg/service",
            {"contract.yaml": "", "impl.py": "class NodeExample(object):\n    pass\n"},
        ),
    ],
)
def test_refuses_new_node_detection_branches(
    repo: Path, directory: str, files: dict[str, str]
) -> None:
    for filename, content in files.items():
        _write(repo, f"{directory}/{filename}", content)
    result = _check(repo)
    assert result.node_directories == (directory,)
    assert [finding.code for finding in result.findings] == ["node-outside-market"]


@pytest.mark.parametrize(
    "component",
    ["tests", "test", "fixtures", "examples", "__pycache__", "docs", ".hidden"],
)
def test_refuses_new_node_ignored_components(repo: Path, component: str) -> None:
    _plant(repo, f"src/pkg/{component}/nodes/node_example")
    _write(
        repo,
        f"src/pkg/{component}/node_class/impl.py",
        "class NodeExample(object):\n    pass\n",
    )
    assert _check(repo).node_directories == ()


def test_refuses_new_node_nested_under_baselined_node(repo: Path) -> None:
    _commit_baseline(repo)
    inner = f"{OLD_NODE}/nested/node_inner"
    _plant(repo, inner)
    result = _check(repo)
    assert result.node_directories == (OLD_NODE, inner)
    assert [(finding.code, finding.path) for finding in result.findings] == [
        ("node-outside-market", inner)
    ]


@pytest.mark.parametrize("directory", ["plugins/x/node_y", "lib/pkg/nodes/node_y"])
def test_refuses_new_node_outside_src(repo: Path, directory: str) -> None:
    _plant(repo, directory)
    result = _check(repo)
    assert result.node_directories == (directory,)
    assert [(finding.code, finding.path) for finding in result.findings] == [
        ("node-outside-market", directory)
    ]


def test_refuses_new_node_class_outside_src(repo: Path) -> None:
    directory = "plugins/x/node_y"
    _write(repo, f"{directory}/impl.py", "class NodeExample:\n    pass\n")
    result = _check(repo)
    assert result.node_directories == (directory,)
    assert [finding.code for finding in result.findings] == ["node-outside-market"]


@pytest.mark.parametrize(
    "source",
    [
        '"""\nclass NodeFake(object):\n    pass\n"""\n',
        "class Outer:\n    class NodeNested(object):\n        pass\n",
        "class Nodelower(object):\n    pass\n",
        "class Node:\n    pass\n",
    ],
)
def test_refuses_new_node_only_top_level_matching_definitions(
    repo: Path, source: str
) -> None:
    _write(repo, "src/pkg/node_candidate/impl.py", source)
    assert _check(repo).node_directories == ()


def test_refuses_new_node_class_in_unqualified_directory_is_not_node(
    repo: Path,
) -> None:
    _write(repo, "src/pkg/service/impl.py", "class NodeExample(object):\n    pass\n")
    assert _check(repo).node_directories == ()


def test_refuses_new_node_reads_staged_python_and_contracts(repo: Path) -> None:
    _write(
        repo, "src/pkg/node_candidate/impl.py", "class NodeExample(object):\n    pass\n"
    )
    _git(repo, "add", "-A")
    _write(repo, "src/pkg/node_candidate/impl.py", "VALUE = 1\n")
    assert NodeHomeRule().check(_request(repo)).node_directories == (
        "src/pkg/node_candidate",
    )
    _git(repo, "add", "-A")
    _plant(repo)
    assert NodeHomeRule().check(_request(repo)).node_directories == ()


def test_baseline_only_shrinks_growth_refused(repo: Path) -> None:
    _commit_baseline(repo)
    _plant(repo)
    _write(repo, NODE_HOME_BASELINE, f"{OLD_NODE}\n{NODE}\n")
    findings = _check(repo).findings
    assert [finding.code for finding in findings] == ["baseline-growth"]
    assert NODE in findings[0].message


def test_baseline_only_shrinks_stale_refused(repo: Path) -> None:
    _commit_baseline(repo)
    shutil.rmtree(repo / OLD_NODE)
    findings = _check(repo).findings
    assert [finding.code for finding in findings] == ["baseline-stale"]
    assert OLD_NODE in findings[0].message


def test_baseline_only_shrinks_delete_node_and_entry_passes(repo: Path) -> None:
    _commit_baseline(repo)
    shutil.rmtree(repo / OLD_NODE)
    _write(repo, NODE_HOME_BASELINE, "")
    assert _check(repo).findings == ()


@pytest.mark.parametrize("update_baseline", [False, True])
@pytest.mark.parametrize("head", [INDEX, "HEAD"])
def test_baselined_node_rename_inherits_baseline(
    repo: Path, update_baseline: bool, head: str
) -> None:
    _commit_baseline(repo)
    _git(repo, "tag", "rename_base")
    _git(repo, "mv", OLD_NODE, NODE)
    if update_baseline:
        _write(repo, NODE_HOME_BASELINE, f"{NODE}\n")
    _git(repo, "add", "-A")
    if head == "HEAD":
        _git(repo, "commit", "-q", "-m", "rename baselined node")

    request = _request(repo, head=head, base="rename_base")
    assert (
        f"{OLD_NODE}/contract.yaml",
        f"{NODE}/contract.yaml",
    ) in request.renamed_paths
    result = NodeHomeRule().check(request)
    assert result.node_directories == (NODE,)
    assert result.findings == ()
    assert (
        main(
            [
                "--rules",
                "node-home",
                "--repo-root",
                str(repo),
                "--base",
                "rename_base",
                "--head",
                head,
            ]
        )
        == 0
    )


def test_unbaselined_node_rename_is_refused(repo: Path) -> None:
    _plant(repo, OLD_NODE)
    _write(repo, NODE_HOME_BASELINE, "")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unbaselined node")
    _git(repo, "tag", "rename_base")
    _git(repo, "mv", OLD_NODE, NODE)
    _git(repo, "commit", "-q", "-m", "rename unbaselined node")

    request = _request(repo, head="HEAD", base="rename_base")
    assert (
        f"{OLD_NODE}/contract.yaml",
        f"{NODE}/contract.yaml",
    ) in request.renamed_paths
    assert [
        (finding.code, finding.path)
        for finding in NodeHomeRule().check(request).findings
    ] == [("node-outside-market", NODE)]
    assert (
        main(
            [
                "--rules",
                "node-home",
                "--repo-root",
                str(repo),
                "--base",
                "rename_base",
                "--head",
                "HEAD",
            ]
        )
        == 1
    )


def test_baseline_only_shrinks_reads_indexed_baseline(repo: Path) -> None:
    _plant(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "pre-existing node without baseline")
    _write(repo, NODE_HOME_BASELINE, f"{NODE}\n")
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1
    _git(repo, "add", "-A")
    (repo / NODE_HOME_BASELINE).unlink()
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 0


def test_baseline_only_shrinks_explicit_base_is_used(repo: Path) -> None:
    _commit_baseline(repo)
    _git(repo, "tag", "baseline_base")
    _plant(repo)
    _write(repo, NODE_HOME_BASELINE, f"{OLD_NODE}\n{NODE}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "grown baseline")
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 0
    assert (
        main(
            [
                "--rules",
                "node-home",
                "--repo-root",
                str(repo),
                "--base",
                "baseline_base",
            ]
        )
        == 1
    )


@pytest.mark.parametrize("argument", ["--baseline", "--allowlist"])
def test_no_exception_mechanism_cli_rejects_override(repo: Path, argument: str) -> None:
    with pytest.raises(SystemExit) as exc:
        main(
            ["--rules", "node-home", "--repo-root", str(repo), argument, "another.txt"]
        )
    assert exc.value.code == 2


def test_no_exception_mechanism_omnimarket_is_checked_like_any_repo(repo: Path) -> None:
    _commit_baseline(repo)
    _plant(repo)
    # Distinct files keep git from treating this new node as an inherited rename.
    _write(repo, f"{NODE}/contract.yaml", "name: new_node\n")
    _write(repo, f"{NODE}/handlers/__init__.py", "NEW_NODE = True\n")
    shutil.rmtree(repo / OLD_NODE)
    _write(repo, NODE_HOME_BASELINE, f"{OLD_NODE}\n{NODE}\n")
    _write(repo, "pyproject.toml", '[project]\nname = "omnimarket"\n')
    result = _check(repo)
    assert _request(repo).renamed_paths == ()
    assert {finding.code for finding in result.findings} == {
        "baseline-stale",
        "baseline-growth",
    }
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1
    _write(repo, NODE_HOME_BASELINE, "")
    assert "node-outside-market" in {finding.code for finding in _check(repo).findings}


def test_no_exception_mechanism_unstaged_market_identity_cannot_bypass(
    repo: Path,
) -> None:
    _plant(repo)
    _git(repo, "add", "-A")
    _write(repo, "pyproject.toml", '[project]\nname = "omnimarket"\n')
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1


def test_usage_and_git_error_exit_two(repo: Path) -> None:
    assert (
        main(
            [
                "--rules",
                "node-home",
                "--repo-root",
                str(repo),
                "--base",
                "missing-revision",
            ]
        )
        == 2
    )
    _write(repo, "pyproject.toml", "invalid toml")
    _git(repo, "add", "-A")
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 2


def test_request_and_result_models_are_frozen_and_forbid_extra() -> None:
    request = ModelNodeHomeRatchetRequest(
        tracked_paths=frozenset(),
        node_class_paths=frozenset(),
        head_baseline_text=None,
        base_baseline_text=None,
        base_node_directories=frozenset(),
        head_entry_points=frozenset(),
        base_entry_points=frozenset(),
    )
    finding = ModelNodeHomeRatchetFinding(
        code="node-outside-market", path=NODE, message="move"
    )
    result = NodeHomeRule().check(request)
    for model in (request, finding, result):
        assert model.model_config["frozen"]
        with pytest.raises(ValidationError):
            type(model).model_validate({**model.model_dump(), "unexpected": True})
    with pytest.raises(ValidationError):
        request.head_baseline_text = "changed"


def test_this_repository_tree_passes_written_baseline() -> None:
    request = gather_node_home_request(
        GitRepo(REPO_ROOT, env=scrub_git_location_env()), INDEX, "HEAD"
    )
    result = NodeHomeRule().check(request)
    assert result.node_directories
    assert result.findings == ()
    assert (
        main(
            ["--rules", "node-home", "--repo-root", str(REPO_ROOT), "--base", "HEAD"],
            env=scrub_git_location_env(),
        )
        == 0
    )


@pytest.mark.parametrize("shape", ["contract", "class"])
def test_baseline_only_shrinks_bootstrap_new_node_refused(
    repo: Path, shape: str
) -> None:
    if shape == "contract":
        _plant(repo)
    else:
        _write(repo, f"{NODE}/impl.py", "class NodeExample:\n    pass\n")
    _write(repo, NODE_HOME_BASELINE, f"{NODE}\n")
    findings = _check(repo).findings
    assert [finding.code for finding in findings] == ["baseline-growth"]
    assert NODE in findings[0].message
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1


@pytest.mark.parametrize("shape", ["contract", "class"])
def test_baseline_only_shrinks_bootstrap_reads_base_tree_and_python(
    repo: Path, shape: str
) -> None:
    directory = "plugins/x/node_y"
    if shape == "contract":
        _plant(repo, directory)
    else:
        _write(repo, f"{directory}/impl.py", "VALUE = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base snapshot without baseline")
    _write(repo, f"{directory}/impl.py", "class NodeExample:\n    pass\n")
    _write(repo, NODE_HOME_BASELINE, f"{directory}\n")
    findings = _check(repo).findings
    assert [finding.code for finding in findings] == (
        [] if shape == "contract" else ["baseline-growth"]
    )


def test_baseline_only_shrinks_bootstrap_existing_class_passes(repo: Path) -> None:
    directory = "plugins/x/node_y"
    _write(repo, f"{directory}/impl.py", "class NodeExample:\n    pass\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "pre-existing class node without baseline")
    _write(repo, NODE_HOME_BASELINE, f"{directory}\n")
    assert _check(repo).findings == ()


@pytest.mark.parametrize("remove_node", [False, True])
def test_baseline_only_shrinks_deleted_baseline_refused(
    repo: Path, remove_node: bool
) -> None:
    _commit_baseline(repo)
    (repo / NODE_HOME_BASELINE).unlink()
    if remove_node:
        shutil.rmtree(repo / OLD_NODE)
    findings = _check(repo).findings
    assert "baseline-removed" in {finding.code for finding in findings}
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1


@pytest.mark.parametrize("base_project", [None, "", '[project]\nname = "other_repo"\n'])
def test_refuses_new_node_entry_point_growth(
    repo: Path, base_project: str | None
) -> None:
    if base_project is None:
        (repo / "pyproject.toml").unlink()
    else:
        _write(repo, "pyproject.toml", base_project)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "entry-point base")
    _write(
        repo,
        "pyproject.toml",
        '[project.entry-points."onex.nodes"]\nnew_node = "pkg:NodeExample"\n',
    )
    findings = _check(repo).findings
    assert [finding.code for finding in findings] == ["entry-point-outside-market"]
    assert "new_node" in findings[0].path
    assert findings[0].message == (
        "a new onex.nodes registration outside omnimarket; register the node in omnimarket instead"
    )
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 1


def test_refuses_new_node_entry_points_read_index_and_explicit_base(repo: Path) -> None:
    _git(repo, "tag", "no_registrations")
    project = '[project.entry-points."onex.nodes"]\nexisting = "pkg:NodeExample"\n'
    _write(repo, "pyproject.toml", project)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "existing registration")
    _write(repo, "pyproject.toml", project + 'new_node = "pkg:NodeOther"\n')
    assert NodeHomeRule().check(_request(repo)).findings == ()
    assert [finding.code for finding in _check(repo).findings] == [
        "entry-point-outside-market"
    ]
    _write(repo, "pyproject.toml", project)
    _git(repo, "add", "-A")
    assert main(["--rules", "node-home", "--repo-root", str(repo)]) == 0
    assert (
        main(
            [
                "--rules",
                "node-home",
                "--repo-root",
                str(repo),
                "--base",
                "no_registrations",
            ]
        )
        == 1
    )
    _write(
        repo, "pyproject.toml", '[project.entry-points."other.group"]\nx = "pkg:X"\n'
    )
    assert _check(repo).findings == ()


@pytest.mark.parametrize("path", ["plugins/.hidden/node_y", "plugins/docs/node_y"])
def test_refuses_new_node_ignored_python_is_not_parsed(repo: Path, path: str) -> None:
    _write(repo, f"{path}/impl.py", "invalid python!")
    _plant(repo, path)
    assert _check(repo).node_directories == ()


def test_refuses_new_node_hidden_python_file_is_not_parsed(repo: Path) -> None:
    _write(repo, "plugins/node_y/.hidden.py", "invalid python!")
    assert _check(repo).node_directories == ()
