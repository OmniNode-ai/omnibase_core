# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Release-identity regressions ported onto the canonical node runtime."""

import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from omnibase_core.models.nodes.release_identity_check.model_release_identity_check_input import (
    ModelReleaseIdentityCheckInput,
)
from omnibase_core.models.nodes.release_identity_check.model_release_identity_gather_input import (
    ModelReleaseIdentityGatherInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_release_identity_check_compute.handler import (
    NodeReleaseIdentityCheckCompute,
)
from omnibase_core.nodes.node_release_identity_check_compute.runtime_release_identity_check import (
    main,
)
from omnibase_core.nodes.node_release_identity_gather_effect.handler import (
    NodeReleaseIdentityGatherEffect,
)

from .conftest import REPO, checkout, commit, git

pytestmark = pytest.mark.unit


def repository(
    tmp_path: Path, version: str = "0.45.0", tags: tuple[str, ...] = ("v0.45.0",)
) -> Path:
    root = checkout(tmp_path / "repo", {"name": "equal", "tags": list(tags)})
    (root / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    return root


def run(root: Path, *args: str) -> tuple[int, ModelValidationReport]:
    destination = root.parent / "report.json"
    code = main(["--root", str(root), "--report-json", str(destination), *args])
    return code, ModelValidationReport.model_validate_json(destination.read_text())


@pytest.mark.parametrize(
    ("version", "published", "changed", "code"),
    [
        pytest.param(
            "0.46.0",
            ("v0.45.0",),
            ("src/omnibase_core/foo.py",),
            0,
            id="test_passes_when_version_ahead_of_published",
        ),
        pytest.param(
            "0.45.0",
            ("v0.45.0",),
            ("src/omnibase_core/foo.py",),
            1,
            id="test_fails_when_src_changed_and_version_equals_published",
        ),
        pytest.param(
            "0.44.0",
            ("v0.45.0",),
            ("src/omnibase_core/foo.py",),
            1,
            id="test_fails_when_src_changed_and_version_behind_published",
        ),
        pytest.param(
            "0.45.0",
            ("v0.45.0",),
            (),
            0,
            id="test_exempt_when_no_packaged_source_changed",
        ),
        pytest.param("0.1.0", (), None, 0, id="test_passes_when_no_published_tag_yet"),
    ],
)
def test_release_decision(
    version: str, published: tuple[str, ...], changed: tuple[str, ...] | None, code: int
) -> None:
    report = NodeReleaseIdentityCheckCompute().handle(
        ModelReleaseIdentityCheckInput(
            pyproject_version_raw=version,
            published_tags=published,
            changed_files=changed,
        )
    )
    assert report.overall_status == ("FAIL" if code else "PASS")
    assert len(report.findings) == code
    if code:
        finding = report.findings[0]
        assert finding.location == "pyproject.toml:1"
        assert finding.rule_id == "version_not_ahead"
        assert finding.message == (
            "FAIL: packaged source changed but pyproject version "
            f"{version} is NOT ahead of the latest published version "
            "0.45.0 (OMN-13411 release-identity gate)."
        )


def test_config_error_on_missing_version(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "pyproject.toml").write_text("[project]\n")
    code, report = run(root, "--base", "origin/dev")
    assert code == 2
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "no_pyproject_version"
    assert (
        report.findings[0].message
        == f"ERROR: no project.version in {root / 'pyproject.toml'}"
    )


def test_packaged_source_changed_detects_src_prefix(tmp_path: Path) -> None:
    root = repository(tmp_path)
    code, report = run(root, "--changed-file", "src/omnibase_core/enums/enum_x.py")
    assert code == 1
    assert report.overall_status == "FAIL"
    paths = ["docs/foo.md", "tests/test_x.py", ".github/workflows/ci.yml"]
    args = [arg for path in paths for arg in ("--changed-file", path)]
    code, report = run(root, *args)
    assert code == 0
    assert report.overall_status == "PASS"


def test_explicit_changed_file_overrides_base(tmp_path: Path) -> None:
    root = repository(tmp_path)
    code, report = run(root, "--changed-file", "src/omnibase_core/foo.py")
    assert code == 1
    assert report.overall_status == "FAIL"
    code, report = run(root, "--changed-file", "docs/foo.md")
    assert code == 0
    assert report.overall_status == "PASS"
    # A missing base would enforce the invariant if the explicit list were ignored.
    assert run(root, "--base", "origin/dev", "--changed-file", "docs/foo.md")[0] == 0


@pytest.mark.parametrize(
    ("tag", "code", "fragment"),
    [
        pytest.param(
            "v0.0.1", 0, "ahead of latest published", id="test_live_invocation_smoke"
        ),
        pytest.param(
            "v99.0.0",
            1,
            "is NOT ahead of the latest published version",
            id="test_live_invocation_fails_when_version_is_not_ahead",
        ),
    ],
)
def test_live_invocation(
    tag: str,
    code: int,
    fragment: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document = (REPO / "pyproject.toml").read_text()
    version = str(tomllib.loads(document)["project"]["version"])
    root = repository(tmp_path, version, (tag,))
    (root / "pyproject.toml").write_text(document)
    actual, report = run(root)
    output = capsys.readouterr()
    assert actual == code, f"stdout={output.out}\nstderr={output.err}"
    assert report.overall_status == ("FAIL" if code else "PASS")
    assert fragment in (output.err if code else output.out)


def test_omn18058_empty_branch_diff_never_attributes_a_peers_packaged_source(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    commit(root)
    git(root, "branch", "origin/dev")
    git(root, "checkout", "-qb", "peer")
    peer = root / "src/peer_pkg/landed_by_someone_else.py"
    peer.parent.mkdir(parents=True)
    peer.write_text("# a peer's packaged-source landing\n", encoding="utf-8")
    commit(root)
    git(root, "branch", "-f", "origin/dev", "HEAD")
    git(root, "checkout", "-q", "main")
    assert git(root, "diff", "--name-only", "origin/dev...HEAD").strip() == ""
    assert "src/peer_pkg/landed_by_someone_else.py" in git(
        root, "diff", "--name-only", "origin/dev", "HEAD"
    )
    code, report = run(root, "--base", "origin/dev")
    assert code == 0
    assert report.overall_status == "PASS"
    own = root / "src/own_pkg/mine.py"
    own.parent.mkdir(parents=True)
    own.write_text("# uncommitted, mine\n", encoding="utf-8")
    git(root, "add", "-A")
    code, report = run(root, "--base", "origin/dev")
    assert code == 1
    assert report.overall_status == "FAIL"


def test_release_identity_base_comparison_fails_closed_when_ref_is_missing(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    assert git(root, "branch", "--list", "origin/dev") == ""
    code, report = run(root, "--base", "origin/dev")
    assert code == 1
    assert report.overall_status == "FAIL"


def test_release_identity_base_comparison_includes_pending_src_edits(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    (root / "src/pending_unstaged.py").write_text("# initial source\n")
    commit(root)
    git(root, "branch", "origin/dev")
    (root / "tests").mkdir()
    (root / "tests/already-committed.py").write_text("# committed test\n")
    commit(root)
    (root / "src/pending_staged.py").write_text("# staged source\n")
    git(root, "add", "src/pending_staged.py")
    (root / "src/pending_unstaged.py").write_text("# edited unstaged source\n")
    assert (
        git(root, "diff", "--name-only", "origin/dev...HEAD")
        == "tests/already-committed.py"
    )
    assert git(root, "diff", "--cached", "--name-only") == "src/pending_staged.py"
    assert git(root, "diff", "--name-only") == "src/pending_unstaged.py"
    assert run(root, "--base", "origin/dev")[0] == 1
    # Prove each pending set independently keeps the gate armed.
    (root / "src/pending_unstaged.py").write_text("# initial source\n")
    assert run(root, "--base", "origin/dev")[0] == 1
    git(root, "restore", "--staged", "src/pending_staged.py")
    (root / "src/pending_unstaged.py").write_text("# only unstaged source\n")
    assert run(root, "--base", "origin/dev")[0] == 1


@pytest.mark.parametrize(
    ("version", "code", "fragment"),
    [
        pytest.param(
            "2.0.0",
            0,
            "ahead of latest published",
            id="test_release_cut_off_this_lineage_does_not_arm_the_gate",
        ),
        pytest.param(
            "1.0.0",
            1,
            "is NOT ahead of the latest published version",
            id="test_version_equal_to_a_reachable_release_still_fails",
        ),
        pytest.param(
            "0.9.0",
            1,
            "is NOT ahead of the latest published version",
            id="test_version_behind_a_reachable_release_still_fails",
        ),
    ],
)
def test_reachable_release_comparison(
    version: str,
    code: int,
    fragment: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = repository(tmp_path, version, ("v1.0.0",))
    git(root, "checkout", "-qb", "omn18443-peer")
    (root / "peer.txt").write_text("peer release\n", encoding="utf-8")
    commit(root)
    git(root, "tag", "v2.0.0")
    git(root, "checkout", "-q", "main")
    (root / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    assert "v2.0.0" in git(root, "tag", "--list").split()
    assert "v2.0.0" not in git(root, "tag", "--merged", "HEAD").split()
    actual, report = run(root)
    output = capsys.readouterr()
    assert actual == code, f"stdout={output.out}\nstderr={output.err}"
    assert report.overall_status == ("FAIL" if code else "PASS")
    assert fragment in (output.err if code else output.out)


def collect_with_git(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_git: Callable[[tuple[str, ...]], str],
) -> ModelReleaseIdentityCheckInput:
    def fake(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        assert repo == root
        return subprocess.CompletedProcess(["git", *args], 0, fake_git(args), "")

    monkeypatch.setattr(NodeReleaseIdentityGatherEffect, "_git", staticmethod(fake))
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(repo_root=str(root))
    )
    assert NodeReleaseIdentityCheckCompute().handle(facts).overall_status == "FAIL"
    assert run(root)[0] == 1
    return facts


def test_published_tags_are_anchored_to_the_evaluated_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, ...]] = []

    def fake_git(args: tuple[str, ...]) -> str:
        seen.append(args)
        if args[:2] == ("rev-parse", "--is-shallow-repository"):
            return "false"
        if args[:2] == ("tag", "--merged"):
            return "v1.0.0\nv1.0.1"
        raise AssertionError(f"unexpected git call: {args}")

    facts = collect_with_git(repository(tmp_path), monkeypatch, fake_git)
    assert facts.published_tags == ("v1.0.0", "v1.0.1")
    assert ("tag", "--merged", "HEAD") in seen
    assert ("tag", "--list") not in seen


def test_shallow_clone_falls_back_to_the_full_tag_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, ...]] = []

    def fake_git(args: tuple[str, ...]) -> str:
        seen.append(args)
        if args[:2] == ("rev-parse", "--is-shallow-repository"):
            return "true"
        if args[:2] == ("tag", "--merged"):
            raise AssertionError("must not ancestry-anchor on a shallow clone")
        return "v1.0.0\nv9.9.9"

    facts = collect_with_git(repository(tmp_path), monkeypatch, fake_git)
    assert facts.published_tags == ("v1.0.0", "v9.9.9")
    assert ("tag", "--list") in seen


def test_empty_merged_result_falls_back_to_the_full_tag_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_git(args: tuple[str, ...]) -> str:
        if args[:2] == ("rev-parse", "--is-shallow-repository"):
            return "false"
        if args[:2] == ("tag", "--merged"):
            return ""
        return "v1.0.0\nv7.7.7"

    facts = collect_with_git(repository(tmp_path), monkeypatch, fake_git)
    assert facts.published_tags == ("v1.0.0", "v7.7.7")
