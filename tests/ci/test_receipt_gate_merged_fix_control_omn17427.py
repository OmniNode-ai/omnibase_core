# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Exercise the real caller control scripts against bindings for merged fixes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

_CONTROL_TOOLS_MISSING = any(
    shutil.which(tool) is None for tool in ("bash", "git", "jq")
)

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
PREPARE_STEP = "Prepare the merge base with the pull request's test side laid over it"
CONTROL_STEP = "Must-fail control at the merge base"
CONTRACT = """\
dod_evidence:
  - id: dod-omn-1-ac1
    binds_ac: [AC1]
    checks:
      - check_value: x
"""
# The contract a merged fix shipped: its evidence id is the merge base's, not the binding's.
FIX_CONTRACT = CONTRACT.replace("dod-omn-1-ac1", "dod-omn-1-shipped-with-fix")
PRODUCT_TEST = """\
from pathlib import Path


def test_product():
    assert "BROKEN = False" in Path("src/product.py").read_text()
"""
# A test the merged fix removed: the merge base no longer has it.
STALE_TEST = """\
def test_stale():
    assert True
"""
# The product test as later work left it on the merge base, after the fix.
EDITED_PRODUCT_TEST = PRODUCT_TEST + "# tightened after the fix\n"


def _pyproject(version: str, dependency: str) -> str:
    return dedent(f"""\
        [project]
        name = "product"
        version = "{version}"
        dependencies = [
            "{dependency}",
        ]
        """)


def _lock(version: str, digest: str) -> str:
    return dedent(f"""\
        {{
          "package_version": "{version}",
          "identity_digest": "{digest}",
          "protocol_count": 1
        }}
        """)


def _script(name: str) -> str:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text())
    script = next(
        step["run"]
        for step in workflow["jobs"]["dod-verify"]["steps"]
        if step.get("name") == name
    )
    assert isinstance(script, str)
    return script


@dataclass
class _GitFixture:
    head_tree: Path
    dod_dir: Path
    env: dict[str, str]
    commits: dict[str, str]

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.head_tree), *args],
            env=scrub_git_location_env(self.env),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def write(self, path: str, content: str) -> None:
        target = self.head_tree / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def commit(self, message: str) -> str:
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            message,
        )
        return self.git("rev-parse", "HEAD")


def _repository(
    tmp_path: Path,
    *,
    fix_subject: str = "fix(OMN-1): the product is fixed (#7)",
    later: bool = False,
    note_after_fix: bool = False,
    fix_contract: bool = False,
    contract_amended_after_fix: bool = False,
    version_bump: bool = False,
    dependency_change: bool = False,
    released_after_fix: bool = False,
    product_deleted_after_fix: bool = False,
    stale_test_removed_by_fix: bool = False,
    duration_record_with_fix: bool = False,
    test_edited_after_fix: bool = False,
    dotted_doc_after_fix: bool = False,
    glob_named_fixture_removed_after_fix: bool = False,
    dotted_test_fixture_after_fix: bool = False,
    product_file_becomes_test_dir_after_fix: bool = False,
    product_file_becomes_package_after_fix: bool = False,
    undecodable_doc_and_new_test_after_fix: bool = False,
    uncited_contract_becomes_test_dir_after_fix: bool = False,
    test_file_becomes_test_dir_after_fix: bool = False,
    symlinked_test_after_fix: bool = False,
    relative_order_file_after_fix: bool = False,
    ignore_stat: bool = False,
    sparse_test_removed_after_fix: bool = False,
    sparse_excludes_a_later_dir: bool = False,
    encoded_fixture_after_fix: bool = False,
    nested_attributes_after_fix: bool = False,
    test_dir_becomes_submodule_after_fix: bool = False,
    setup_initial: Callable[[_GitFixture], None] | None = None,
    setup_fix: Callable[[_GitFixture], None] | None = None,
) -> _GitFixture:
    workspace = tmp_path / "ws"
    head_tree = workspace / ".dod-verify" / "head_home" / "omnimarket"
    head_tree.mkdir(parents=True)
    dod_dir = tmp_path / "rt" / "dod"
    dod_dir.mkdir(parents=True)
    (dod_dir / "tickets.txt").write_text("OMN-1\n")

    # Replace the environment completely so hook git overrides cannot retarget git.
    tool_dirs = {
        str(Path(found).parent)
        for found in (shutil.which(tool) for tool in ("bash", "git", "jq"))
        if found
    }
    env = {
        "PATH": os.pathsep.join([*sorted(tool_dirs), "/usr/bin", "/bin"]),
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GITHUB_WORKSPACE": str(workspace),
        "RUNNER_TEMP": str(dod_dir.parent),
        "REPO_SHORT": "omnimarket",
    }
    repo = _GitFixture(head_tree, dod_dir, env, {})
    repo.git("init")
    repo.write("src/product.py", "BROKEN = True\n")
    if product_deleted_after_fix:
        repo.write("src/legacy.py", "BROKEN = True\n")
    repo.write("pyproject.toml", _pyproject("0.1.0", "dep>=1"))
    repo.write("contracts/runtime/protocol.lock.json", _lock("0.1.0", "aaa"))
    if stale_test_removed_by_fix:
        repo.write("tests/test_stale.py", STALE_TEST)
    if glob_named_fixture_removed_after_fix:
        # Two test fixtures whose names one glob pathspec would both match.
        repo.write("tests/case1.json", "{}\n")
        repo.write("tests/case[1].json", "{}\n")
    if (
        product_file_becomes_test_dir_after_fix
        or product_file_becomes_package_after_fix
    ):
        # A product file the merge base later replaces with a directory.
        repo.write("tools/runner", "#!/bin/sh\necho run\n")
    if uncited_contract_becomes_test_dir_after_fix:
        repo.write("contracts/OMN-10278.yaml", "ticket_id: OMN-10278\n")
    if test_file_becomes_test_dir_after_fix:
        repo.write("tests/agents", "fixture\n")
    if sparse_test_removed_after_fix:
        repo.write("tests/retired/test_old.py", "def test_old():\n    pass\n")
    if test_dir_becomes_submodule_after_fix:
        repo.write("tests/vendor/test_vendored.py", "def test_vendored():\n    pass\n")
    if setup_initial is not None:
        setup_initial(repo)
    repo.commits["initial"] = repo.commit("chore: initial")
    repo.write("src/product.py", "BROKEN = False\n")
    if product_deleted_after_fix:
        repo.write("src/legacy.py", "BROKEN = False\n")
    repo.write("tests/test_product.py", PRODUCT_TEST)
    if stale_test_removed_by_fix:
        (repo.head_tree / "tests/test_stale.py").unlink()
    if duration_record_with_fix:
        repo.write(DURATION_RECORD, '{"tests/test_product.py": 0.01}\n')
    if version_bump:
        # A squash-merged fix carries the release bump beside the product change.
        repo.write(
            "pyproject.toml",
            _pyproject("0.1.1", "dep>=2" if dependency_change else "dep>=1"),
        )
        repo.write("contracts/runtime/protocol.lock.json", _lock("0.1.1", "bbb"))
    if fix_contract:
        # A squash-merged fix ships its own contract beside the product change.
        repo.write("contracts/OMN-1.yaml", FIX_CONTRACT)
    if setup_fix is not None:
        setup_fix(repo)
    repo.commits["fix"] = repo.commit(fix_subject)
    if product_deleted_after_fix:
        (repo.head_tree / "src/legacy.py").unlink()
        repo.commits["delete"] = repo.commit("chore: delete the legacy product file")
    if test_edited_after_fix:
        repo.write("tests/test_product.py", EDITED_PRODUCT_TEST)
        repo.commits["test_edit"] = repo.commit("test: tighten the product test")
    if dotted_doc_after_fix:
        repo.write("docs/v1..v2.md", "Upgrade notes.\n")
        repo.commits["doc"] = repo.commit("docs: upgrade notes")
    if glob_named_fixture_removed_after_fix:
        (repo.head_tree / "tests/case[1].json").unlink()
        repo.commits["fixture"] = repo.commit("test: drop one fixture")
    if dotted_test_fixture_after_fix:
        repo.write("tests/fixtures/v1..v2.json", "{}\n")
        repo.commits["dotted"] = repo.commit("test: add an upgrade fixture")
    if product_file_becomes_test_dir_after_fix:
        (repo.head_tree / "tools/runner").unlink()
        repo.write("tools/runner/main.py", "print('run')\n")
        repo.write("tools/runner/tests/test_smoke.py", "def test_smoke():\n    pass\n")
        repo.commits["runner"] = repo.commit("refactor: runner becomes a package")
    if product_file_becomes_package_after_fix:
        (repo.head_tree / "tools/runner").unlink()
        repo.write("tools/runner/main.py", "print('run')\n")
        repo.commits["package"] = repo.commit("refactor: runner becomes a package")
    if undecodable_doc_and_new_test_after_fix:
        # A name ending in a byte that is not valid UTF-8, listed before a new test.
        (repo.head_tree / "docs").mkdir(parents=True, exist_ok=True)
        (repo.head_tree / os.fsdecode(b"docs/notes\xc3")).write_text("notes\n")
        repo.write("tests/test_late.py", "def test_late():\n    pass\n")
        repo.commits["late"] = repo.commit("test: add a late test beside raw notes")
    if uncited_contract_becomes_test_dir_after_fix:
        (repo.head_tree / "contracts/OMN-10278.yaml").unlink()
        repo.write(
            "contracts/OMN-10278.yaml/tests/test_parse.py",
            "def test_parse():\n    pass\n",
        )
        repo.commits["contract_dir"] = repo.commit("test: contract becomes a folder")
    if test_file_becomes_test_dir_after_fix:
        (repo.head_tree / "tests/agents").unlink()
        repo.write(
            "tests/agents/test_trajectory.py", "def test_trajectory():\n    pass\n"
        )
        repo.commits["agents"] = repo.commit("test: agents fixture becomes a folder")
        # A repository order file that lists the new test before the removed file.
        order = repo.head_tree.parent / "diff-order.txt"
        order.write_text("tests/agents/*\n*\n")
        repo.git("config", "diff.orderFile", str(order))
    if symlinked_test_after_fix:
        # A test the merge base adds as a symlink to another test.
        (repo.head_tree / "tests/test_link.py").symlink_to("test_product.py")
        repo.commits["link"] = repo.commit("test: link a test")
    if relative_order_file_after_fix:
        # An order file the repository adds after the fix, named relative to the
        # worktree, so it is absent from the parent's worktree.
        repo.write("diff-order.txt", "*\n")
        repo.commits["order"] = repo.commit("chore: add a diff order file")
        repo.git("config", "diff.orderFile", "diff-order.txt")
    if ignore_stat:
        repo.git("config", "core.ignoreStat", "true")
    if sparse_test_removed_after_fix:
        # The merge base deletes a test that the repository's sparse checkout
        # leaves out; a worktree at the parent inherits the patterns.
        (repo.head_tree / "tests/retired/test_old.py").unlink()
        repo.commits["retire"] = repo.commit("test: retire an old test")
        repo.git("sparse-checkout", "set", "--no-cone", "/*", "!/tests/retired/")
    if encoded_fixture_after_fix:
        # A fixture and the encoding rule that governs it, added together; the
        # fixture's name sorts before .gitattributes in the listing.
        repo.write("tests/.gitattributes", "*.txt working-tree-encoding=UTF-16LE\n")
        (repo.head_tree / "tests/-input.txt").write_bytes("hello".encode("utf-16-le"))
        repo.commits["encoded"] = repo.commit("test: add a UTF-16 fixture")
    if nested_attributes_after_fix:
        # A nested .gitattributes fixture and the parent folder's rule for it,
        # added together; the nested file sorts first in the listing.
        repo.write("tests/.gitattributes", "-sample/.gitattributes text eol=crlf\n")
        repo.write("tests/-sample/.gitattributes", "*.dat binary\n")
        repo.commits["nested"] = repo.commit("test: add nested attributes")
    if test_dir_becomes_submodule_after_fix:
        # The merge base replaces a folder of tests with a submodule of that name.
        repo.git("rm", "-r", "-q", "tests/vendor")
        repo.git(
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{repo.commits['initial']},tests/vendor",
        )
        # An unpopulated submodule is an empty folder; without it "git add ." drops it.
        (repo.head_tree / "tests/vendor").mkdir()
        repo.commits["submodule"] = repo.commit("test: vendor becomes a submodule")
    if sparse_excludes_a_later_dir:
        # A sparse rule that leaves out only a folder the merge base added, so the
        # parent has no skip-worktree entry at all.
        repo.write("tests/late/test_late.py", "def test_late():\n    pass\n")
        repo.commits["late_dir"] = repo.commit("test: add a late folder")
        repo.git("sparse-checkout", "set", "--no-cone", "/*", "!/tests/late/")
    if contract_amended_after_fix:
        repo.write("contracts/OMN-1.yaml", FIX_CONTRACT + "# amended on the base\n")
        repo.commits["amend"] = repo.commit("docs(OMN-1): amend the contract")
    if released_after_fix:
        repo.write(
            "pyproject.toml",
            _pyproject("0.1.2", "dep>=2" if dependency_change else "dep>=1"),
        )
        repo.write("contracts/runtime/protocol.lock.json", _lock("0.1.2", "ccc"))
        repo.commits["release"] = repo.commit("chore(release): 0.1.2")
    if note_after_fix:
        repo.write("src/notes.txt", "The product was fixed.\n")
        repo.commits["note"] = repo.commit("docs(OMN-1): note")
    if later:
        repo.write("src/other.py", "OTHER = True\n")
        repo.commits["later"] = repo.commit("chore: later")
    repo.commits["merge_base"] = repo.git("rev-parse", "HEAD")
    repo.env["BASE_SHA"] = repo.commits["merge_base"]
    return repo


def _bind(
    repo: _GitFixture,
    trailers: list[str],
    *,
    extra_files: dict[str, str] | None = None,
) -> None:
    repo.write("contracts/OMN-1.yaml", CONTRACT)
    for path, content in (extra_files or {}).items():
        repo.write(path, content)
    message = "fix(OMN-17427): bind OMN-1"
    if trailers:
        message += "\n\n" + "\n".join(
            f"Binds-Merged-Fix: {value}" for value in trailers
        )
    repo.env["HEAD_SHA"] = repo.commit(message)


def _run_steps(
    repo: _GitFixture,
    *,
    head_status: str | None = "verified",
    head_evidence_id: str = "dod-omn-1-ac1",
    head_binds_ac: bool = True,
    requires: str | None = None,
    fix_output: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str] | None]:
    """Run the prepare and control steps against a stub verifier.

    The stub verifies when src/product.py says BROKEN = False and, if given,
    the file named by ``requires`` exists. With ``fix_output`` it prints that
    text instead when it runs inside the fix control's home (OMN-26434).
    """
    prepare = subprocess.run(
        ["bash", "-c", _script(PREPARE_STEP)],
        env=repo.env,
        capture_output=True,
        text=True,
        check=False,
    )
    if prepare.returncode != 0:
        return prepare, None

    if head_status is not None:
        (repo.dod_dir / "head-OMN-1.json").write_text(
            "not JSON"
            if head_status == "malformed"
            else json.dumps(
                {
                    "status": head_status,
                    "checks": [
                        {
                            "evidence_id": head_evidence_id,
                            "binds_ac": ["AC1"] if head_binds_ac else [],
                            "status": head_status,
                        }
                    ],
                }
            )
        )

    verifier = repo.dod_dir.parent / "verifier"
    verifier.write_text(
        f"#!{sys.executable}\n"
        f"REQUIRES = {requires!r}\n"
        f"FIX_OUTPUT = {fix_output!r}\n"
        + dedent("""\
            import json
            import os
            import sys
            from pathlib import Path

            if len(sys.argv) > 1 and sys.argv[1] == "-m":
                if FIX_OUTPUT is not None and "/fix_home/" in str(Path.cwd()):
                    print(FIX_OUTPUT)
                    sys.exit(0)
                product = (Path.cwd() / "src/product.py").read_text()
                ready = REQUIRES is None or (Path.cwd() / REQUIRES).exists()
                status = (
                    "verified" if "BROKEN = False" in product and ready else "failed"
                )
                print(json.dumps({
                    "status": status,
                    "checks": [{
                        "evidence_id": "dod-omn-1-ac1",
                        "binds_ac": ["AC1"],
                        "status": status,
                    }],
                }))
                sys.exit(0)
            os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
            """)
    )
    verifier.chmod(0o755)
    control = subprocess.run(
        ["bash", "-c", _script(CONTROL_STEP)],
        env={**repo.env, "DOD_VERIFY_PY": str(verifier)},
        capture_output=True,
        text=True,
        check=False,
    )
    return prepare, control


def _assert_success(completed: subprocess.CompletedProcess[str]) -> None:
    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    assert "::error::" not in output


def _assert_parent_control(
    repo: _GitFixture, prepare: subprocess.CompletedProcess[str], fix: str
) -> Path:
    _assert_success(prepare)
    assert (
        f"::notice::the product changes of merged fix {fix} did not apply in reverse "
        "at the merge base; the control runs at the fix's parent"
    ) in prepare.stdout
    label = f"the parent of merged fix {fix}"
    assert f"OMN-1: control at {label}" in prepare.stdout
    assert (repo.dod_dir / "control-label-OMN-1.txt").read_text() == label + "\n"
    control_tree = (
        Path((repo.dod_dir / "control-home-OMN-1.txt").read_text().strip())
        / repo.env["REPO_SHORT"]
    )
    assert repo.git("-C", str(control_tree), "rev-parse", "HEAD") == repo.git(
        "rev-parse", f"{fix}^1"
    )
    assert (control_tree / "contracts/OMN-1.yaml").read_text() == CONTRACT
    return control_tree


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("later", [False, True], ids=["fix-is-base", "later-base"])
def test_contract_only_binding_fails_with_the_merged_fix_reverted(
    tmp_path: Path, later: bool
) -> None:
    repo = _repository(tmp_path, later=later)
    _bind(repo, [f"OMN-1 {repo.commits['fix']}"])
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert (
        f"OMN-1: control at the merge base with merged fix {repo.commits['fix']} reverted"
    ) in prepare.stdout
    assert f"Reverted from {repo.commits['fix']}: src/product.py" in prepare.stdout
    assert (repo.dod_dir / "control-home-OMN-1.txt").read_text() == (
        str(Path(repo.env["GITHUB_WORKSPACE"]) / ".dod-verify/fix_reverted_home/OMN-1")
        + "\n"
    )
    assert (repo.dod_dir / "control-label-OMN-1.txt").read_text() == (
        f"the merge base with merged fix {repo.commits['fix']} reverted\n"
    )
    assert not (repo.dod_dir / "control-sha-OMN-1.txt").exists()
    assert control is not None
    _assert_success(control)
    assert (
        "OMN-1 base control: passed; every bound check failed [dod-omn-1-ac1]"
        in control.stdout
    )


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    "amended", [False, True], ids=["contract-unchanged", "contract-amended-on-base"]
)
def test_merged_fix_contract_is_not_reverted_as_a_product_path(
    tmp_path: Path, amended: bool
) -> None:
    repo = _repository(tmp_path, fix_contract=True, contract_amended_after_fix=amended)
    _bind(repo, [f"OMN-1 {repo.commits['fix']}"])
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert f"Reverted from {repo.commits['fix']}: src/product.py" in prepare.stdout
    assert "contracts/OMN-1.yaml" not in "".join(
        line for line in prepare.stdout.splitlines() if line.startswith("Reverted from")
    )
    assert control is not None
    _assert_success(control)
    assert (
        "OMN-1 base control: passed; every bound check failed [dod-omn-1-ac1]"
        in control.stdout
    )


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    "released", [False, True], ids=["version-unchanged", "released-on-base"]
)
def test_merged_fix_version_bookkeeping_is_not_reverted(
    tmp_path: Path, released: bool
) -> None:
    repo = _repository(tmp_path, version_bump=True, released_after_fix=released)
    _bind(repo, [f"OMN-1 {repo.commits['fix']}"])
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    fix = repo.commits["fix"]
    assert f"Reverted from {fix}: src/product.py" in prepare.stdout
    for path in ("pyproject.toml", "contracts/runtime/protocol.lock.json"):
        assert f"Reverted from {fix}: {path}" not in prepare.stdout
        assert (
            f"Not reverted from {fix} (release version bookkeeping): {path}"
            in prepare.stdout
        )
    assert control is not None
    _assert_success(control)
    assert (
        "OMN-1 base control: passed; every bound check failed [dod-omn-1-ac1]"
        in control.stdout
    )


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_merged_fix_dependency_change_is_reverted_as_a_product_path(
    tmp_path: Path,
) -> None:
    repo = _repository(
        tmp_path, version_bump=True, dependency_change=True, released_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    _assert_parent_control(repo, prepare, fix)
    assert "Not reverted" not in "".join(
        line
        for line in prepare.stdout.splitlines()
        if line.endswith(": pyproject.toml")
    )
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_conflicting_merged_fix_uses_parent_control(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    fix = repo.commits["fix"]
    repo.write("src/product.py", "BROKEN = False  # rewritten\n")
    repo.env["BASE_SHA"] = repo.commit("chore: rewrite")
    bound_test = PRODUCT_TEST + "# bound at this head\n"
    _bind(repo, [f"OMN-1 {fix}"], extra_files={"tests/test_product.py": bound_test})
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/test_product.py").read_text() == bound_test
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_conflicting_merged_fix_whose_check_passes_at_parent_is_refused(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path, note_after_fix=True)
    fix = repo.commits["note"]
    repo.write("src/notes.txt", "The product was fixed and documented.\n")
    repo.env["BASE_SHA"] = repo.commit("chore: rewrite the note")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    _assert_parent_control(repo, prepare, fix)
    assert control is not None
    assert control.returncode != 0, control.stdout + control.stderr
    assert (
        "::error::OMN-1 [dod-omn-1-ac1]: bound test also passes at the parent "
        f"of merged fix {fix}: the control did not fail (always-pass)"
    ) in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_merged_fix_with_deleted_product_file_uses_parent_control(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert not (repo.head_tree / "src/legacy.py").exists()
    assert (control_tree / "src/legacy.py").read_text() == "BROKEN = True\n"
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_carries_the_merge_base_test_side(tmp_path: Path) -> None:
    """OMN-25103: a parent control runs the merge base's tests, not the parent's.

    The merged fix added tests/test_product.py, so its parent has no such file.
    A contract-only binding changes no test path, so before this the parent
    control ran with the bound test missing: every check failed because the
    file was absent, which proved nothing about the fix. The control now
    carries the merge base's test side, duration records included.
    """
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, duration_record_with_fix=True
    )
    fix = repo.commits["fix"]
    assert repo.git("cat-file", "-t", f"{fix}^1:src/product.py") == "blob"
    with pytest.raises(subprocess.CalledProcessError):
        repo.git("cat-file", "-e", f"{fix}^1:tests/test_product.py")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/test_product.py").read_text() == PRODUCT_TEST
    assert (control_tree / DURATION_RECORD).read_text() == (
        '{"tests/test_product.py": 0.01}\n'
    )
    assert "Carried from the merge base: tests/test_product.py" in prepare.stdout
    assert f"Carried from the merge base: {DURATION_RECORD}" in prepare.stdout
    assert (control_tree / "src/product.py").read_text() == "BROKEN = True\n"
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_drops_a_test_the_merge_base_no_longer_has(
    tmp_path: Path,
) -> None:
    """A test file present at the fix's parent but gone at the merge base is removed."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, stale_test_removed_by_fix=True
    )
    fix = repo.commits["fix"]
    assert repo.git("cat-file", "-t", f"{fix}^1:tests/test_stale.py") == "blob"
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert not (control_tree / "tests/test_stale.py").exists()
    assert (
        repo.git("-C", str(control_tree), "ls-files", "--", "tests/test_stale.py") == ""
    )
    assert "Removed, absent at the merge base: tests/test_stale.py" in prepare.stdout
    assert (control_tree / "tests/test_product.py").read_text() == PRODUCT_TEST
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_carries_a_test_edited_after_the_fix(tmp_path: Path) -> None:
    """The carry reads the merge base, not the fix: a later test edit arrives too."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, test_edited_after_fix=True
    )
    fix = repo.commits["fix"]
    assert repo.git("show", f"{fix}:tests/test_product.py") + "\n" == PRODUCT_TEST
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/test_product.py").read_text() == EDITED_PRODUCT_TEST
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_ignores_a_dotted_path_outside_the_test_side(
    tmp_path: Path,
) -> None:
    """A non-test path holding '..' changed after the fix does not stop the carry."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, dotted_doc_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/test_product.py").read_text() == PRODUCT_TEST
    assert not (control_tree / "docs/v1..v2.md").exists()
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_reads_carried_paths_literally(tmp_path: Path) -> None:
    """Removing 'tests/case[1].json' leaves 'tests/case1.json', which a glob would match."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        glob_named_fixture_removed_after_fix=True,
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert "Removed, absent at the merge base: tests/case[1].json" in prepare.stdout
    assert not (control_tree / "tests/case[1].json").exists()
    assert (control_tree / "tests/case1.json").read_text() == "{}\n"
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_carries_a_test_fixture_with_dots_in_its_name(
    tmp_path: Path,
) -> None:
    """Only a '..' path component is unsafe; 'v1..v2.json' is an ordinary file name."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, dotted_test_fixture_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/fixtures/v1..v2.json").read_text() == "{}\n"
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_an_overlay_that_would_change_a_product_path(
    tmp_path: Path,
) -> None:
    """The pull request's own test that replaces a product file at the parent stops the job.

    tools/runner is a file at the parent and a package at the merge base; the pull
    request adds the package's first test, and its overlay at the parent would turn
    the file into a directory holding only that test.
    """
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        product_file_becomes_package_after_fix=True,
    )
    fix = repo.commits["fix"]
    _bind(
        repo,
        [f"OMN-1 {fix}"],
        extra_files={
            "tools/runner/tests/test_smoke.py": "def test_smoke():\n    pass\n"
        },
    )
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the test-side carry onto the parent of merged fix {fix} would "
        "change a product path: tools/runner"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_reads_the_listing_byte_for_byte_under_a_utf8_locale(
    tmp_path: Path,
) -> None:
    """A name ending in an invalid UTF-8 byte does not swallow the next record."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        undecodable_doc_and_new_test_after_fix=True,
    )
    repo.env["LC_ALL"] = "C.UTF-8"
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert "Carried from the merge base: tests/test_late.py" in prepare.stdout
    assert (control_tree / "tests/test_late.py").is_file()
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_a_carry_that_would_replace_an_uncited_contract(
    tmp_path: Path,
) -> None:
    """Only the cited tickets' contracts may change; another contract is product."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        uncited_contract_becomes_test_dir_after_fix=True,
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the test-side carry onto the parent of merged fix {fix} would "
        "change a product path: contracts/OMN-10278.yaml"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_ignores_a_repository_diff_order_file(tmp_path: Path) -> None:
    """A diff.orderFile listing a new test before its parent's removal does not stop the carry."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        test_file_becomes_test_dir_after_fix=True,
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/agents/test_trajectory.py").is_file()
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_to_carry_a_symlinked_test(tmp_path: Path) -> None:
    """A carried symlink stops the job: it runs whatever it points at, not itself.

    The overlay lists only added, copied, modified and renamed paths, so a pull
    request that turns the symlink back into a file would not replace it.
    """
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, symlinked_test_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the test-side carry onto the parent of merged fix {fix} would "
        "install a symlink: tests/test_link.py"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_ignores_an_order_file_absent_at_the_parent(
    tmp_path: Path,
) -> None:
    """A relative diff.orderFile the parent's worktree lacks does not stop the guard."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, relative_order_file_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/test_product.py").is_file()
    assert control is not None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_guard_sees_paths_marked_unchanged(tmp_path: Path) -> None:
    """core.ignoreStat cannot hide a product file the carry replaced."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        product_file_becomes_test_dir_after_fix=True,
        ignore_stat=True,
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the test-side carry onto the parent of merged fix {fix} would "
        "change a product path: tools/runner"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_a_sparse_checkout(tmp_path: Path) -> None:
    """A parent control with skip-worktree entries stops the job.

    In a sparse checkout, removing a test outside the patterns leaves it in the
    index, and a skip-worktree entry hides its change from the guard's diff.
    """
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, sparse_test_removed_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the control at the parent of merged fix {fix} cannot run in a "
        "sparse checkout"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_a_sparse_checkout_without_excluded_parent_paths(
    tmp_path: Path,
) -> None:
    """A sparse checkout stops the job even when it leaves out no parent path."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, sparse_excludes_a_later_dir=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the control at the parent of merged fix {fix} cannot run in a "
        "sparse checkout"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_carries_a_fixture_under_its_new_encoding_rule(
    tmp_path: Path,
) -> None:
    """A fixture is written under the .gitattributes rule the merge base carries with it."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, encoded_fixture_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/-input.txt").read_bytes() == "hello".encode(
        "utf-16-le"
    )
    assert control is not None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_carries_a_nested_attributes_file_under_its_parent_rule(
    tmp_path: Path,
) -> None:
    """A carried .gitattributes is written under the rule another carried one sets for it."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, nested_attributes_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert (control_tree / "tests/-sample/.gitattributes").read_bytes() == (
        b"*.dat binary\r\n"
    )
    assert control is not None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_drops_tests_under_a_directory_that_became_a_submodule(
    tmp_path: Path,
) -> None:
    """A folder of tests the merge base replaced with a submodule leaves no test behind."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        test_dir_becomes_submodule_after_fix=True,
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert not (control_tree / "tests/vendor/test_vendored.py").exists()
    assert (
        repo.git(
            "-C", str(control_tree), "ls-files", "--", "tests/vendor/test_vendored.py"
        )
        == ""
    )
    assert control is not None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_a_carry_that_would_change_a_product_path(
    tmp_path: Path,
) -> None:
    """A carried test that would replace a product file at the parent stops the job.

    The parent has tools/runner as a file; the merge base turned it into a package
    with a test under it. Carrying that test would delete the parent's product file
    and leave no implementation, so a check could fail for that alone.
    """
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        product_file_becomes_test_dir_after_fix=True,
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    output = prepare.stdout + prepare.stderr
    assert prepare.returncode != 0, output
    assert (
        f"::error::the test-side carry onto the parent of merged fix {fix} would "
        "change a product path: tools/runner"
    ) in output
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_merged_fix_with_only_tests_and_version_bookkeeping_is_refused(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    repo.write("tests/test_more.py", PRODUCT_TEST)
    repo.write("pyproject.toml", _pyproject("0.1.1", "dep>=1"))
    named = repo.commit("test(OMN-1): more tests and the release bump")
    repo.commits["merge_base"] = named
    repo.env["BASE_SHA"] = named
    _bind(repo, [f"OMN-1 {named}"])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::merged fix {named} changes no product path, so reverting it "
        "cannot make a bound test fail"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_merged_fix_with_only_test_and_contract_changes_is_refused(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    repo.write("tests/test_more.py", PRODUCT_TEST)
    repo.write("contracts/OMN-1.yaml", CONTRACT + "# shipped with the tests\n")
    named = repo.commit("test(OMN-1): more tests and the contract")
    repo.commits["merge_base"] = named
    repo.env["BASE_SHA"] = named
    _bind(repo, [f"OMN-1 {named}"])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::merged fix {named} changes no product path, so reverting it "
        "cannot make a bound test fail"
    ) in prepare.stdout
    assert control is None


DURATION_RECORD = "config/test_file_durations.d/tests__test_product.json"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_merged_fix_with_only_tests_and_a_duration_record_is_refused(
    tmp_path: Path,
) -> None:
    """OMN-25969: a fix's own duration record is bookkeeping, so reverting it proves nothing."""
    repo = _repository(tmp_path)
    repo.write("tests/test_more.py", PRODUCT_TEST)
    repo.write(DURATION_RECORD, '{"seconds": 0.1}\n')
    named = repo.commit("test(OMN-1): more tests and their duration record")
    repo.commits["merge_base"] = named
    repo.env["BASE_SHA"] = named
    _bind(repo, [f"OMN-1 {named}"])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::merged fix {named} changes no product path, so reverting it "
        "cannot make a bound test fail"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_binding_duration_record_is_laid_over_the_control(tmp_path: Path) -> None:
    """OMN-25969: the binding's own record reaches the control, so a check reading it is real."""
    repo = _repository(tmp_path)
    _bind(
        repo,
        [f"OMN-1 {repo.commits['fix']}"],
        extra_files={DURATION_RECORD: '{"seconds": 0.1}\n'},
    )
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert f"Overlaid: {DURATION_RECORD}" in prepare.stdout
    control_tree = (
        Path((repo.dod_dir / "control-home-OMN-1.txt").read_text().strip())
        / repo.env["REPO_SHORT"]
    )
    assert (control_tree / DURATION_RECORD).read_text() == '{"seconds": 0.1}\n'
    assert (control_tree / "src/product.py").read_text() == "BROKEN = True\n"
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_duration_record_is_not_a_test_side_change(tmp_path: Path) -> None:
    """OMN-25969: a record is laid over the control but never counts as a test path."""
    repo = _repository(tmp_path)
    _bind(repo, [], extra_files={DURATION_RECORD: '{"seconds": 0.1}\n'})
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert f"Overlaid: {DURATION_RECORD}" in prepare.stdout
    assert (
        "::error::no test-side change: the bound tests cannot be shown to fail at the merge base"
        in prepare.stdout
    )
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_binding_whose_check_passes_with_the_fix_reverted_is_refused(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path, note_after_fix=True)
    _bind(repo, [f"OMN-1 {repo.commits['note']}"])
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert (
        f"OMN-1: control at the merge base with merged fix {repo.commits['note']} reverted"
    ) in prepare.stdout
    assert f"Reverted from {repo.commits['note']}: src/notes.txt" in prepare.stdout
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert (
        "::error::OMN-1 [dod-omn-1-ac1]: bound test also passes at the merge base "
        f"with merged fix {repo.commits['note']} reverted: the control did not fail (always-pass)"
    ) in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_contract_only_binding_without_a_trailer_is_refused(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    _bind(repo, [])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        "::error::no test-side change: the bound tests cannot be shown to fail at the merge base"
        in prepare.stdout
    )
    assert (
        "For an already-merged fix, add a commit trailer "
        "'Binds-Merged-Fix: OMN-<n> <full 40-character sha>'" in prepare.stdout
    )
    assert control is None
    assert not (repo.dod_dir / "base-OMN-1.control.txt").exists()


def test_missing_contract_names_the_caller_repair_before_running_tests(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    completed = subprocess.run(
        ["bash", "-c", _script("Verify the contract at the PR head")],
        env=repo.env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "pull request cites OMN-1 but carries no contracts/OMN-1.yaml" in (
        completed.stdout
    )
    assert (
        "Include contracts/OMN-1.yaml at this PR head; "
        "a later companion merge cannot supply evidence for this head."
        in completed.stdout
    )
    assert not (repo.dod_dir / "head-OMN-1.json").exists()


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    "test_path",
    [
        "tests/test_coverage.py",
        "tests/fixture.json",
        "test/test_more.py",
        "conftest.py",
    ],
)
def test_coverage_only_diff_names_impossible_control(
    tmp_path: Path, test_path: str
) -> None:
    repo = _repository(tmp_path)
    _bind(repo, [], extra_files={test_path: PRODUCT_TEST})
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert control is not None
    _assert_success(control)
    assert "IMPOSSIBLE TEST_ONLY_DIFF (test_only_diff)" in control.stdout
    assert "every bound check failed" not in control.stdout
    assert (repo.dod_dir / "base-OMN-1.control.txt").read_text() == (
        "passed: IMPOSSIBLE TEST_ONLY_DIFF (test_only_diff); coverage-only evidence, "
        "no earlier product behaviour to control\n"
    )


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    "product_path",
    [
        "src/other.py",
        ".github/workflows/ci.yml",
        "pyproject.toml",
        "contracts/OMN-2.yaml",
        "README.md",
    ],
)
def test_coverage_with_other_paths_still_refuses_always_pass(
    tmp_path: Path, product_path: str
) -> None:
    repo = _repository(tmp_path)
    _bind(
        repo,
        [],
        extra_files={"tests/test_coverage.py": PRODUCT_TEST, product_path: "changed\n"},
    )
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert "the control did not fail (always-pass)" in control.stdout
    assert "IMPOSSIBLE" not in control.stdout
    assert (repo.dod_dir / "base-OMN-1.control.txt").read_text() == "refused\n"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    "rename", [False, True], ids=["delete-source", "rename-source-to-test"]
)
def test_product_removal_cannot_be_hidden_by_test_additions(
    tmp_path: Path, rename: bool
) -> None:
    repo = _repository(tmp_path)
    repo.write("src/other.py", "OTHER = True\n")
    repo.commits["merge_base"] = repo.commit("chore: other source")
    repo.env["BASE_SHA"] = repo.commits["merge_base"]
    if rename:
        repo.git("mv", "src/other.py", "tests/test_other.py")
    else:
        repo.git("rm", "src/other.py")
    _bind(repo, [], extra_files={"tests/test_coverage.py": PRODUCT_TEST})
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert "the control did not fail (always-pass)" in control.stdout
    assert "IMPOSSIBLE" not in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("head_status", "head_evidence_id", "head_binds_ac"),
    [
        (None, "dod-omn-1-ac1", True),
        ("malformed", "dod-omn-1-ac1", True),
        ("failed", "dod-omn-1-ac1", True),
        ("verified", "wrong-id", True),
        ("verified", "dod-omn-1-ac1", False),
    ],
    ids=["absent", "malformed", "failed", "wrong-evidence", "unbound"],
)
def test_coverage_only_diff_requires_own_verified_head_evidence(
    tmp_path: Path, head_status: str | None, head_evidence_id: str, head_binds_ac: bool
) -> None:
    repo = _repository(tmp_path)
    _bind(repo, [], extra_files={"tests/test_coverage.py": PRODUCT_TEST})
    prepare, control = _run_steps(
        repo,
        head_status=head_status,
        head_evidence_id=head_evidence_id,
        head_binds_ac=head_binds_ac,
    )

    _assert_success(prepare)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert (
        "TEST_ONLY_DIFF requires verified head evidence for every own bound check"
        in control.stdout
    )
    assert (repo.dod_dir / "base-OMN-1.control.txt").read_text() == "refused\n"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_coverage_binding_for_merged_fix_still_requires_reverted_failure(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path, note_after_fix=True)
    _bind(
        repo,
        [f"OMN-1 {repo.commits['note']}"],
        extra_files={"tests/test_coverage.py": PRODUCT_TEST},
    )
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert "the control did not fail (always-pass)" in control.stdout
    assert "IMPOSSIBLE" not in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_real_product_repair_still_requires_all_own_checks_to_fail_at_base(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    repo.git("checkout", "--detach", repo.commits["initial"])
    repo.env["BASE_SHA"] = repo.commits["initial"]
    _bind(
        repo,
        [],
        extra_files={
            "src/product.py": "BROKEN = False\n",
            "tests/test_coverage.py": PRODUCT_TEST,
        },
    )
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout
    assert "IMPOSSIBLE" not in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("case", "message"),
    [
        (
            "short-sha",
            "::error::Binds-Merged-Fix must read 'OMN-<n> <full 40-character sha>'; refused: OMN-1 abc123",
        ),
        (
            "missing-commit",
            "::error::OMN-1: merged fix {named} is not a commit in this repository",
        ),
        (
            "unmerged-fix",
            "::error::OMN-1: {named} is not merged at the merge base {merge_base}; an unmerged fix proves red at the merge base",
        ),
        (
            "wrong-ticket",
            "::error::OMN-1: the subject of merged fix {named} does not cite OMN-1",
        ),
        (
            "two-fixes",
            "::error::OMN-1: Binds-Merged-Fix names more than one merged fix; name exactly one",
        ),
        (
            "product-change",
            "::error::OMN-1 names merged fix {named}, but this pull request changes src/product.py, which is neither test-side nor a contract; a product change proves red at the merge base",
        ),
        (
            "test-only-fix",
            "::error::merged fix {named} changes no product path, so reverting it cannot make a bound test fail",
        ),
        (
            "merge-commit",
            "::error::OMN-1: merged fix {named} does not have exactly one parent",
        ),
    ],
)
def test_invalid_merged_fix_bindings_are_refused_before_control(
    tmp_path: Path, case: str, message: str
) -> None:
    repo = _repository(
        tmp_path,
        fix_subject=(
            "fix(OMN-12): the product is fixed (#7)"
            if case == "wrong-ticket"
            else "fix(OMN-1): the product is fixed (#7)"
        ),
        note_after_fix=case == "two-fixes",
    )
    named = repo.commits["fix"]
    if case == "short-sha":
        named = "abc123"
    elif case == "missing-commit":
        named = "f" * 40
    elif case == "unmerged-fix":
        repo.git("checkout", "-b", "side-fix", repo.commits["initial"])
        repo.write("src/product.py", "BROKEN = False\n")
        repo.write("tests/test_side.py", PRODUCT_TEST)
        named = repo.commit("fix(OMN-1): side branch fix")
        repo.git("checkout", "--detach", repo.commits["merge_base"])
    elif case == "test-only-fix":
        repo.write("tests/test_more.py", PRODUCT_TEST)
        named = repo.commit("test(OMN-1): more tests")
    elif case == "merge-commit":
        repo.git("checkout", "-b", "side", repo.commits["fix"])
        repo.write("src/side.py", "SIDE = True\n")
        repo.commit("feat: side")
        repo.git("checkout", "--detach", repo.commits["fix"])
        repo.write("src/main.py", "MAIN = True\n")
        repo.commit("chore: main")
        repo.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "merge",
            "--no-ff",
            "side",
            "-m",
            "fix(OMN-1): merge the side work",
        )
        named = repo.git("rev-parse", "HEAD")
    repo.commits["merge_base"] = repo.git("rev-parse", "HEAD")
    repo.env["BASE_SHA"] = repo.commits["merge_base"]
    trailers = [f"OMN-1 {named}"]
    if case == "two-fixes":
        trailers.append(f"OMN-1 {repo.commits['note']}")
    extra_files = (
        {"src/product.py": "BROKEN = True\n"} if case == "product-change" else None
    )
    _bind(repo, trailers, extra_files=extra_files)
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert message.format(named=named, merge_base=repo.commits["merge_base"]) in (
        prepare.stdout
    )
    assert control is None
    assert not (repo.dod_dir / "base-OMN-1.control.txt").exists()


# OMN-26434: the overlay applies deletions, renames, type changes and submodule
# pins; the parent control is checked at the fix too; dotted, linked and
# attribute-only test paths are handled. MODES runs a case at the merge-base
# control (no trailer) and at the parent-of-fix control (a conflicting revert).
MODES = ["merge-base", "parent"]
OLD_PIN = "1" * 40
NEW_PIN = "2" * 40


def _control_tree(repo: _GitFixture) -> Path:
    home = (repo.dod_dir / "control-home-OMN-1.txt").read_text().strip()
    return Path(home) / repo.env["REPO_SHORT"]


def _rebase_point(repo: _GitFixture, message: str) -> str:
    repo.commits["merge_base"] = repo.commit(message)
    repo.env["BASE_SHA"] = repo.commits["merge_base"]
    return repo.commits["merge_base"]


def _scenario(
    tmp_path: Path,
    mode: str,
    setup_initial: Callable[[_GitFixture], None] | None = None,
) -> _GitFixture:
    return _repository(
        tmp_path,
        product_deleted_after_fix=mode == "parent",
        setup_initial=setup_initial,
    )


def _bind_for(
    repo: _GitFixture, mode: str, extra_files: dict[str, str] | None = None
) -> None:
    """Bind at the parent with a trailer, or at the merge base with a new test."""
    if mode == "parent":
        _bind(repo, [f"OMN-1 {repo.commits['fix']}"], extra_files=extra_files)
    else:
        files = {"tests/test_coverage.py": PRODUCT_TEST, **(extra_files or {})}
        _bind(repo, [], extra_files=files)


def _prepared(
    repo: _GitFixture, mode: str, prepare: subprocess.CompletedProcess[str]
) -> Path:
    if mode == "parent":
        return _assert_parent_control(repo, prepare, repo.commits["fix"])
    _assert_success(prepare)
    return _control_tree(repo)


def _index_entry(tree: Path, repo: _GitFixture, path: str) -> str:
    return repo.git("-C", str(tree), "ls-files", "-s", "--", path)


def _checked_out_bytes(
    repo: _GitFixture, tmp_path: Path, commit: str, path: str
) -> bytes:
    """The bytes git writes for path in a fresh checkout of commit."""
    fresh = tmp_path / f"fresh-{commit[:12]}"
    if not fresh.exists():
        repo.git("worktree", "add", "--detach", str(fresh), commit)
    return (fresh / path).read_bytes()


def _symlink(repo: _GitFixture, path: str, target: str) -> None:
    link = repo.head_tree / path
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)


def _gitlink(repo: _GitFixture, path: str, pin: str) -> None:
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{pin},{path}")
    (repo.head_tree / path).mkdir(parents=True, exist_ok=True)


def _ignored_submodule(repo: _GitFixture, path: str) -> None:
    """A submodule at OLD_PIN whose .gitmodules entry sets ignore=all."""
    _gitlink(repo, path, OLD_PIN)
    repo.write(
        ".gitmodules",
        f'[submodule "vendored"]\n\tpath = {path}\n\turl = ./vendored.git\n\tignore = all\n',
    )


def _initial_link(repo: _GitFixture) -> None:
    repo.write("tests/fixtures/other.json", '{"v": 2}\n')
    _symlink(repo, "tests/fixtures/link.json", "other.json")


# AC1


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "path",
    ["tests/fixtures/old.json", "config/test_file_durations.d/tests__old.json"],
    ids=["fixture", "duration-record"],
)
def test_pull_request_deletes_a_test_fixture(
    tmp_path: Path, mode: str, path: str
) -> None:
    repo = _scenario(tmp_path, mode)
    repo.write(path, "{}\n")
    _rebase_point(repo, "test: add a fixture")
    repo.git("rm", "-q", path)
    _bind_for(repo, mode)
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, mode, prepare)
    assert not (tree / path).exists()
    assert _index_entry(tree, repo, path) == ""
    assert f"Removed by the pull request: {path}" in prepare.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_pull_request_deletion_only_is_not_a_test_side_change(tmp_path: Path) -> None:
    """A deletion alone cannot show a bound test failing, so the refusal still holds."""
    repo = _repository(tmp_path)
    repo.write("tests/fixtures/old.json", "{}\n")
    _rebase_point(repo, "test: add a fixture")
    repo.git("rm", "-q", "tests/fixtures/old.json")
    _bind(repo, [])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        "::error::no test-side change: the bound tests cannot be shown to fail at "
        "the merge base"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("mode", MODES)
def test_pull_request_renames_a_test_file(tmp_path: Path, mode: str) -> None:
    repo = _scenario(tmp_path, mode)
    repo.write("tests/test_old_name.py", STALE_TEST)
    _rebase_point(repo, "test: add a test")
    repo.git("mv", "tests/test_old_name.py", "tests/test_new_name.py")
    _bind_for(repo, mode)
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, mode, prepare)
    assert not (tree / "tests/test_old_name.py").exists()
    assert (tree / "tests/test_new_name.py").read_text() == STALE_TEST
    assert "Removed by the pull request: tests/test_old_name.py" in prepare.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_pull_request_type_change_to_a_symlink_lands_at_the_merge_base(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path)
    repo.write("tests/fixtures/data.json", '{"v": 1}\n')
    repo.write("tests/fixtures/other.json", '{"v": 2}\n')
    _rebase_point(repo, "test: add fixtures")
    _symlink(repo, "tests/fixtures/data.json", "other.json")
    _bind_for(repo, "merge-base")
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, "merge-base", prepare)
    assert (tree / "tests/fixtures/data.json").is_symlink()
    assert (tree / "tests/fixtures/data.json").readlink() == Path("other.json")


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_pull_request_type_change_to_a_symlink_is_refused_at_the_parent(
    tmp_path: Path,
) -> None:
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    repo.write("tests/fixtures/data.json", '{"v": 1}\n')
    repo.write("tests/fixtures/other.json", '{"v": 2}\n')
    _rebase_point(repo, "test: add fixtures")
    _symlink(repo, "tests/fixtures/data.json", "other.json")
    _bind_for(repo, "parent")
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::the pull request's overlay onto the parent of merged fix {fix} "
        "would install a symlink: tests/fixtures/data.json"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("mode", MODES)
def test_pull_request_type_change_to_a_file_lands(tmp_path: Path, mode: str) -> None:
    repo = _scenario(tmp_path, mode, setup_initial=_initial_link)
    link = repo.head_tree / "tests/fixtures/link.json"
    link.unlink()
    link.write_text('{"v": 3}\n')
    _bind_for(repo, mode)
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, mode, prepare)
    assert not (tree / "tests/fixtures/link.json").is_symlink()
    assert (tree / "tests/fixtures/link.json").read_text() == '{"v": 3}\n'


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_pull_request_type_change_only_is_a_test_side_change(tmp_path: Path) -> None:
    """A type change counts toward the "no test-side change" refusal, as a modification does."""
    repo = _repository(tmp_path, setup_initial=_initial_link)
    link = repo.head_tree / "tests/fixtures/link.json"
    link.unlink()
    link.write_text('{"v": 3}\n')
    _bind(repo, [])
    prepare, _ = _run_steps(repo)

    _assert_success(prepare)
    assert "Overlaid: tests/fixtures/link.json" in prepare.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("mode", MODES)
def test_pull_request_replaces_a_folder_with_a_file(tmp_path: Path, mode: str) -> None:
    repo = _scenario(tmp_path, mode)
    repo.write("tests/x/a.json", "{}\n")
    _rebase_point(repo, "test: add a fixture folder")
    repo.git("rm", "-q", "-r", "tests/x")
    repo.write("tests/x", "fixture\n")
    _bind_for(repo, mode)
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, mode, prepare)
    assert (tree / "tests/x").is_file()
    assert (tree / "tests/x").read_text() == "fixture\n"
    assert _index_entry(tree, repo, "tests/x/a.json") == ""


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("mode", MODES)
def test_pull_request_replaces_a_folder_with_a_submodule(
    tmp_path: Path, mode: str
) -> None:
    repo = _scenario(tmp_path, mode)
    repo.write("tests/vendor/test_vendored.py", "def test_vendored():\n    pass\n")
    _rebase_point(repo, "test: add a vendored test")
    repo.git("rm", "-q", "-r", "tests/vendor")
    _gitlink(repo, "tests/vendor", NEW_PIN)
    _bind_for(repo, mode)
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, mode, prepare)
    assert _index_entry(tree, repo, "tests/vendor").startswith(f"160000 {NEW_PIN} ")
    assert not (tree / "tests/vendor/test_vendored.py").exists()


# AC2


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_passes_the_bound_checks_at_the_fix(tmp_path: Path) -> None:
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    _assert_parent_control(repo, prepare, fix)
    fix_tree = (
        Path((repo.dod_dir / "control-fix-home-OMN-1.txt").read_text().strip())
        / repo.env["REPO_SHORT"]
    )
    assert repo.git("-C", str(fix_tree), "rev-parse", "HEAD") == fix
    assert (fix_tree / "tests/test_product.py").read_text() == PRODUCT_TEST
    assert (fix_tree / "contracts/OMN-1.yaml").read_text() == CONTRACT
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout
    assert (
        f"OMN-1 fix check: passed; every bound check passes at merged fix {fix} "
        "[dod-omn-1-ac1]"
    ) in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_refuses_a_check_that_also_fails_at_the_fix(
    tmp_path: Path,
) -> None:
    """A later product change, not the fix, makes the check fail at the parent."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    repo.write("src/feature.py", "FEATURE = True\n")
    _rebase_point(repo, "feat: a later feature")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo, requires="src/feature.py")

    _assert_parent_control(repo, prepare, fix)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert (
        f"::error::OMN-1 [dod-omn-1-ac1]: bound check also fails at merged fix {fix} "
        "with the same carry, so its failure at the fix's parent is not the fix's"
    ) in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("fix_output", "message"),
    [
        (
            "not JSON",
            "::error::OMN-1: the check at merged fix {fix} is not parseable as one JSON verdict with checks",
        ),
        (
            json.dumps({"status": "verified", "checks": []}),
            "::error::OMN-1: no own bound check ran at merged fix {fix}",
        ),
        (
            json.dumps(
                {
                    "status": "skipped",
                    "checks": [
                        {
                            "evidence_id": "dod-omn-1-ac1",
                            "binds_ac": ["AC1"],
                            "status": "skipped",
                        }
                    ],
                }
            ),
            "::error::OMN-1 [dod-omn-1-ac1]: bound check did not run at merged fix {fix}; a check that did not run is not a pass",
        ),
        (
            json.dumps(
                {
                    "status": "failed",
                    "checks": [
                        {
                            "evidence_id": "dod-omn-1-ac1",
                            "binds_ac": ["AC1"],
                            "status": "verified",
                        },
                        {
                            "evidence_id": "dod-omn-1-ac1",
                            "binds_ac": ["AC1"],
                            "status": "failed",
                        },
                    ],
                }
            ),
            "::error::OMN-1 [dod-omn-1-ac1]: bound check also fails at merged fix {fix} with the same carry, so its failure at the fix's parent is not the fix's",
        ),
    ],
    ids=["unparseable", "zero-bound", "not-run", "duplicate-id"],
)
def test_parent_control_refuses_a_fix_check_that_cannot_run(
    tmp_path: Path, fix_output: str, message: str
) -> None:
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo, fix_output=fix_output)

    _assert_parent_control(repo, prepare, fix)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert message.format(fix=fix) in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_parent_control_fix_home_is_cleared_between_runs(tmp_path: Path) -> None:
    """A self-hosted workspace outlives the job: a second run rebuilds the fix control."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    first, _ = _run_steps(repo)
    _assert_parent_control(repo, first, fix)
    second, control = _run_steps(repo)

    _assert_parent_control(repo, second, fix)
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_clean_revert_control_builds_no_fix_control(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    _bind(repo, [f"OMN-1 {repo.commits['fix']}"])
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert not (repo.dod_dir / "control-fix-home-OMN-1.txt").exists()
    assert control is not None
    _assert_success(control)
    assert "fix check" not in control.stdout


# AC3


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("mode", MODES)
def test_dots_inside_a_name_in_the_pull_request(tmp_path: Path, mode: str) -> None:
    repo = _scenario(tmp_path, mode)
    _bind_for(repo, mode, extra_files={"tests/fixtures/v1..v2.json": "{}\n"})
    prepare, _ = _run_steps(repo)

    tree = _prepared(repo, mode, prepare)
    assert (tree / "tests/fixtures/v1..v2.json").read_text() == "{}\n"
    assert "Overlaid: tests/fixtures/v1..v2.json" in prepare.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("path", ["tests/fixtures/v1..v2.json", "docs/v1..v2.md"])
def test_dots_inside_a_name_in_the_fix(tmp_path: Path, path: str) -> None:
    def touch(repo: _GitFixture) -> None:
        repo.write(path, "fixed\n")

    repo = _repository(tmp_path, setup_fix=touch)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    if not path.startswith("tests/"):
        assert f"Reverted from {fix}: {path}" in prepare.stdout
    assert control is not None
    _assert_success(control)
    assert "passed; every bound check failed [dod-omn-1-ac1]" in control.stdout


def _git_wrapper(
    tmp_path: Path, repo: _GitFixture, tokens: list[str], record: str
) -> Path:
    """Put a git on PATH that appends a raw record to one listing.

    Git refuses to store a '..' path component, so the refusal of one can only be
    reached by a listing that carries it. The wrapper runs the real git, then,
    when every token is an argument, prints the record and logs that it fired.
    """
    real = shutil.which("git")
    assert real is not None
    wrap = tmp_path / "wrap"
    wrap.mkdir()
    log = tmp_path / "wrap.log"
    script = wrap / "git"
    script.write_text(
        "#!/bin/bash\n"
        f'"{real}" "$@"\n'
        "rc=$?\n"
        'args=" $* "\n'
        "fire=1\n"
        "IFS='|' read -r -a want <<< \"$INJECT_TOKENS\"\n"
        'for token in "${want[@]}"; do\n'
        '  [[ "$args" == *" $token "* ]] || fire=0\n'
        "done\n"
        'if [ "$fire" -eq 1 ]; then\n'
        "  printf '%b' \"$INJECT_RECORD\"\n"
        f'  echo fired >> "{log}"\n'
        "fi\n"
        'exit "$rc"\n'
    )
    script.chmod(0o755)
    repo.env["PATH"] = f"{wrap}{os.pathsep}{repo.env['PATH']}"
    repo.env["INJECT_TOKENS"] = "|".join(tokens)
    repo.env["INJECT_RECORD"] = record
    return log


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("listing", ["revert", "overlay"])
def test_dotdot_component_is_still_refused(tmp_path: Path, listing: str) -> None:
    repo = _repository(tmp_path)
    fix = repo.commits["fix"]
    if listing == "revert":
        _bind(repo, [f"OMN-1 {fix}"])
        log = _git_wrapper(
            tmp_path, repo, ["--name-only", "-z", f"{fix}^1", fix], "../escape\\0"
        )
        message = "::error::unsafe revert path refused"
    else:
        _bind_for(repo, "merge-base")
        log = _git_wrapper(
            tmp_path,
            repo,
            ["--name-status", repo.commits["merge_base"], repo.env["HEAD_SHA"]],
            "A\\0../escape\\0",
        )
        message = "::error::unsafe overlay path refused"
    prepare, control = _run_steps(repo)

    assert log.exists(), "the wrapper never saw the listing, so the case proves nothing"
    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert message in prepare.stdout
    assert control is None


# AC4


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("kind", "path"),
    [("symlink", "test"), ("symlink", "pkg/tests"), ("submodule", "test")],
    ids=["root-symlink", "nested-symlink", "root-submodule"],
)
def test_test_folder_through_a_link_in_the_head(
    tmp_path: Path, kind: str, path: str
) -> None:
    repo = _repository(tmp_path)
    repo.write("qa/test_quality.py", "def test_quality():\n    pass\n")
    if kind == "symlink":
        target = os.path.relpath(repo.head_tree / "qa", (repo.head_tree / path).parent)
        _symlink(repo, path, target)
    else:
        _gitlink(repo, path, NEW_PIN)
    _bind(repo, [])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::the test side is reached through a link at the head: {path}"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_test_folder_through_a_link_at_the_merge_base_only(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.write("qa/test_quality.py", "def test_quality():\n    pass\n")
    _symlink(repo, "pkg/tests", "../qa")
    _rebase_point(repo, "test: link a test folder")
    (repo.head_tree / "pkg/tests").unlink()
    _bind_for(repo, "merge-base")
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        "::error::the test side is reached through a link at the merge base: pkg/tests"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_test_folder_through_a_link_at_the_fix_parent_only(tmp_path: Path) -> None:
    def link(repo: _GitFixture) -> None:
        repo.write("qa/test_quality.py", "def test_quality():\n    pass\n")
        _symlink(repo, "pkg/tests", "../qa")

    repo = _repository(tmp_path, product_deleted_after_fix=True, setup_initial=link)
    fix = repo.commits["fix"]
    (repo.head_tree / "pkg/tests").unlink()
    _rebase_point(repo, "test: drop the linked folder")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        "::error::the test side is reached through a link at the parent of merged "
        f"fix {fix}: pkg/tests"
    ) in prepare.stdout
    assert control is None


# AC5


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_pull_request_pin_reaches_the_control(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    _ignored_submodule(repo, "tests/vendor")
    _rebase_point(repo, "test: vendor a submodule")
    _gitlink(repo, "tests/vendor", NEW_PIN)
    _bind(repo, [])
    prepare, _ = _run_steps(repo)

    _assert_success(prepare)
    tree = _control_tree(repo)
    assert _index_entry(tree, repo, "tests/vendor").startswith(f"160000 {NEW_PIN} ")
    assert "Overlaid: tests/vendor" in prepare.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_product_pin_is_not_a_test_only_diff(tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    _ignored_submodule(repo, "vendor/lib")
    _rebase_point(repo, "chore: vendor a library")
    _gitlink(repo, "vendor/lib", NEW_PIN)
    _bind(repo, [], extra_files={"tests/test_coverage.py": PRODUCT_TEST})
    prepare, control = _run_steps(repo)

    _assert_success(prepare)
    assert control is not None
    assert control.returncode == 1, control.stdout + control.stderr
    assert "IMPOSSIBLE" not in control.stdout
    assert "the control did not fail (always-pass)" in control.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_product_pin_is_refused_beside_a_named_fix(tmp_path: Path) -> None:
    repo = _repository(
        tmp_path, setup_initial=lambda r: _ignored_submodule(r, "vendor/lib")
    )
    fix = repo.commits["fix"]
    _gitlink(repo, "vendor/lib", NEW_PIN)
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::OMN-1 names merged fix {fix}, but this pull request changes "
        "vendor/lib, which is neither test-side nor a contract; a product change "
        "proves red at the merge base"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_fix_pin_is_reverted_as_product(tmp_path: Path) -> None:
    repo = _repository(
        tmp_path,
        setup_initial=lambda r: _ignored_submodule(r, "vendor/lib"),
        setup_fix=lambda r: _gitlink(r, "vendor/lib", NEW_PIN),
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, _ = _run_steps(repo)

    _assert_success(prepare)
    assert f"OMN-1: control at the merge base with merged fix {fix} reverted" in (
        prepare.stdout
    )
    assert f"Reverted from {fix}: vendor/lib" in prepare.stdout


# AC6


CRLF_RULE = "*.txt eol=crlf\n"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("change", ["rule-added", "rule-removed"])
def test_attribute_only_change_in_the_carry(tmp_path: Path, change: str) -> None:
    def fixture(repo: _GitFixture) -> None:
        repo.write("tests/data.txt", "a\nb\n")
        if change == "rule-removed":
            repo.write("tests/.gitattributes", CRLF_RULE)

    repo = _repository(tmp_path, product_deleted_after_fix=True, setup_initial=fixture)
    fix = repo.commits["fix"]
    if change == "rule-added":
        repo.write("tests/.gitattributes", CRLF_RULE)
    else:
        repo.git("rm", "-q", "tests/.gitattributes")
    merge_base = _rebase_point(repo, "test: change the line-ending rule")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, _ = _run_steps(repo)

    tree = _assert_parent_control(repo, prepare, fix)
    expected = _checked_out_bytes(repo, tmp_path, merge_base, "tests/data.txt")
    assert expected == (b"a\r\nb\r\n" if change == "rule-added" else b"a\nb\n")
    assert (tree / "tests/data.txt").read_bytes() == expected


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize("change", ["rule-added", "rule-removed"])
def test_attribute_only_change_in_the_overlay(tmp_path: Path, change: str) -> None:
    repo = _repository(tmp_path)
    repo.write("tests/data.txt", "a\nb\n")
    if change == "rule-removed":
        repo.write("tests/.gitattributes", CRLF_RULE)
    _rebase_point(repo, "test: add a text fixture")
    if change == "rule-added":
        _bind(repo, [], extra_files={"tests/.gitattributes": CRLF_RULE})
    else:
        repo.git("rm", "-q", "tests/.gitattributes")
        _bind_for(repo, "merge-base")
    prepare, _ = _run_steps(repo)

    _assert_success(prepare)
    tree = _control_tree(repo)
    expected = _checked_out_bytes(
        repo, tmp_path, repo.env["HEAD_SHA"], "tests/data.txt"
    )
    assert expected == (b"a\r\nb\r\n" if change == "rule-added" else b"a\nb\n")
    assert (tree / "tests/data.txt").read_bytes() == expected


# AC7


MAGIC_NAME = ":(exclude)x/tests/a.json"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_literal_checkout_in_the_carry(tmp_path: Path) -> None:
    """Read as a pathspec, the name would check out everything else at the merge base."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    repo.write(MAGIC_NAME, '{"carried": true}\n')
    repo.write("x/tests/a.json", '{"decoy": true}\n')
    _rebase_point(repo, "test: add a fixture with a pathspec-like name")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, _ = _run_steps(repo)

    tree = _assert_parent_control(repo, prepare, fix)
    assert (tree / MAGIC_NAME).read_text() == '{"carried": true}\n'
    assert f"Carried from the merge base: {MAGIC_NAME}" in prepare.stdout
    assert (tree / "src/product.py").read_text() == "BROKEN = True\n"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_literal_checkout_in_the_overlay(tmp_path: Path) -> None:
    """Read as a pathspec, the name would check out every other head path, product included."""
    repo = _repository(tmp_path)
    repo.write("x/tests/a.json", '{"decoy": true}\n')
    repo.write("src/other.py", "OTHER = 1\n")
    _rebase_point(repo, "test: add a decoy fixture and a product file")
    _bind_for(
        repo,
        "merge-base",
        extra_files={MAGIC_NAME: '{"overlaid": true}\n', "src/other.py": "OTHER = 2\n"},
    )
    prepare, _ = _run_steps(repo)

    _assert_success(prepare)
    tree = _control_tree(repo)
    assert (tree / MAGIC_NAME).read_text() == '{"overlaid": true}\n'
    assert f"Overlaid: {MAGIC_NAME}" in prepare.stdout
    assert (tree / "src/other.py").read_text() == "OTHER = 1\n"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_pin_only_fix_reverts_at_the_merge_base(tmp_path: Path) -> None:
    """A fix whose only product change is a hidden pin reverts at the merge base.

    With the pin left out of the revert patch, the patch is empty, does not
    apply, and the control falls back to the fix's parent for no real conflict.
    """
    repo = _repository(
        tmp_path, setup_initial=lambda r: _ignored_submodule(r, "vendor/lib")
    )
    _gitlink(repo, "vendor/lib", NEW_PIN)
    pin_fix = _rebase_point(repo, "fix(OMN-1): pin the library (#8)")
    _bind(repo, [f"OMN-1 {pin_fix}"])
    prepare, _ = _run_steps(repo)

    _assert_success(prepare)
    assert f"Reverted from {pin_fix}: vendor/lib" in prepare.stdout
    assert (
        f"OMN-1: control at the merge base with merged fix {pin_fix} reverted"
    ) in prepare.stdout


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_fix_control_carries_the_merge_base_test_side(tmp_path: Path) -> None:
    """The control at the fix runs the merge base's tests, edited after the fix."""
    repo = _repository(
        tmp_path, product_deleted_after_fix=True, test_edited_after_fix=True
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    _assert_parent_control(repo, prepare, fix)
    fix_tree = (
        Path((repo.dod_dir / "control-fix-home-OMN-1.txt").read_text().strip())
        / repo.env["REPO_SHORT"]
    )
    assert (fix_tree / "tests/test_product.py").read_text() == EDITED_PRODUCT_TEST
    assert (
        f"At merged fix {fix}: Carried from the merge base: tests/test_product.py"
    ) in prepare.stdout
    assert control is not None
    _assert_success(control)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_sibling_checkouts_at_the_fix_and_its_parent(tmp_path: Path) -> None:
    """The real prepare step gives the parent and the fix controls the frozen sibling."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    sibling = Path(repo.env["GITHUB_WORKSPACE"]) / ".dod-verify/head_home/sibling"
    sibling.mkdir(parents=True)
    sibling_repo = _GitFixture(sibling, repo.dod_dir, repo.env, {})
    sibling_repo.git("init", "-q")
    sibling_repo.write("revision", "frozen\n")
    frozen = sibling_repo.commit("frozen")
    (repo.dod_dir / "siblings.tsv").write_text(f"sibling\t{frozen}\n")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, _ = _run_steps(repo)

    _assert_parent_control(repo, prepare, fix)
    homes = [
        Path((repo.dod_dir / "control-home-OMN-1.txt").read_text().strip()),
        Path((repo.dod_dir / "control-fix-home-OMN-1.txt").read_text().strip()),
    ]
    for home in homes:
        assert (home / "sibling/revision").read_text() == "frozen\n"
        assert (
            sibling_repo.git("-C", str(home / "sibling"), "rev-parse", "HEAD") == frozen
        )


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_test_folder_through_a_link_at_the_fix_only(tmp_path: Path) -> None:
    def link(repo: _GitFixture) -> None:
        repo.write("qa/test_quality.py", "def test_quality():\n    pass\n")
        _symlink(repo, "pkg/tests", "../qa")

    repo = _repository(tmp_path, product_deleted_after_fix=True, setup_fix=link)
    fix = repo.commits["fix"]
    (repo.head_tree / "pkg/tests").unlink()
    _rebase_point(repo, "test: drop the linked folder")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::the test side is reached through a link at merged fix {fix}: pkg/tests"
    ) in prepare.stdout
    assert control is None


# OMN-26434 carry-side cases: the carry listing and the guard repeat checks the
# overlay and the revert already have, and each needs a case of its own.


def _staging_wrapper(tmp_path: Path, repo: _GitFixture, where: str, entry: str) -> Path:
    """Put a git on PATH that stages one index entry just before the guard reads.

    No code path stages a product change in a control tree today, so a guard
    whose listing went blind would pass every other case. The wrapper stands in
    for such a defect: on the guard's first ``diff --cached --name-only`` in a
    tree whose path holds ``where``, it stages ``entry`` there, logs that it
    fired, and then runs the real git.
    """
    real = shutil.which("git")
    assert real is not None
    wrap = tmp_path / "stage-wrap"
    wrap.mkdir()
    log = tmp_path / "stage-wrap.log"
    script = wrap / "git"
    script.write_text(
        "#!/bin/bash\n"
        'args=" $* "\n'
        'dir=""\n'
        'prev=""\n'
        'for arg in "$@"; do\n'
        '  [ "$prev" = "-C" ] && dir="$arg"\n'
        '  prev="$arg"\n'
        "done\n"
        f'if [ ! -e "{log}" ] && [[ "$args" == *" diff --cached --name-only "* ]]'
        ' && [[ "$dir" == *"$STAGE_WHERE"* ]]; then\n'
        f'  "{real}" -C "$dir" update-index --add --cacheinfo "$STAGE_ENTRY"\n'
        f'  echo fired >> "{log}"\n'
        "fi\n"
        f'exec "{real}" "$@"\n'
    )
    script.chmod(0o755)
    repo.env["PATH"] = f"{wrap}{os.pathsep}{repo.env['PATH']}"
    repo.env["STAGE_WHERE"] = where
    repo.env["STAGE_ENTRY"] = entry
    return log


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_guard_at_the_fix_refuses_a_staged_product_change(tmp_path: Path) -> None:
    """The fix control's own product-path guard runs, and names what changed."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    log = _staging_wrapper(
        tmp_path, repo, "/fix_home/", f"160000,{NEW_PIN},src/injected"
    )
    prepare, control = _run_steps(repo)

    assert log.exists(), "the guard at the fix never listed, so the case proves nothing"
    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::the test-side carry onto merged fix {fix} would change a "
        "product path: src/injected"
    ) in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_dotdot_component_in_the_carry_is_refused(tmp_path: Path) -> None:
    """A '..' component in the carry listing stops the job, as in the overlay."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    log = _git_wrapper(
        tmp_path,
        repo,
        ["--name-status", f"{fix}^1", repo.commits["merge_base"]],
        "A\\0tests/../escape\\0",
    )
    prepare, control = _run_steps(repo)

    assert log.exists(), (
        "the wrapper never saw the carry listing, so the case proves nothing"
    )
    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert "::error::unsafe test-side path refused" in prepare.stdout
    assert control is None


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_merge_base_pin_is_carried(tmp_path: Path) -> None:
    """A test-side pin the merge base moved reaches the parent control under ignore=all."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        setup_initial=lambda r: _ignored_submodule(r, "tests/vendor"),
    )
    fix = repo.commits["fix"]
    _gitlink(repo, "tests/vendor", NEW_PIN)
    _rebase_point(repo, "test: move the vendored pin")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, _ = _run_steps(repo)

    control_tree = _assert_parent_control(repo, prepare, fix)
    assert repo.git("ls-tree", f"{fix}^1", "tests/vendor").startswith(
        f"160000 commit {OLD_PIN}"
    )
    assert _index_entry(control_tree, repo, "tests/vendor").startswith(
        f"160000 {NEW_PIN} "
    )


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_ignore_all_guard_sees_a_staged_product_pin(tmp_path: Path) -> None:
    """The guard lists a product pin that .gitmodules hides with ignore=all."""
    repo = _repository(
        tmp_path,
        product_deleted_after_fix=True,
        setup_initial=lambda r: _ignored_submodule(r, "vendor/lib"),
    )
    fix = repo.commits["fix"]
    _bind(repo, [f"OMN-1 {fix}"])
    log = _staging_wrapper(
        tmp_path, repo, "/fix_reverted_home/", f"160000,{NEW_PIN},vendor/lib"
    )
    prepare, control = _run_steps(repo)

    assert log.exists(), (
        "the guard at the parent never listed, so the case proves nothing"
    )
    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        f"::error::the test-side carry onto the parent of merged fix {fix} would "
        "change a product path: vendor/lib"
    ) in prepare.stdout
    assert control is None


ATTRIBUTES_MAGIC = ":(exclude)x/tests/.gitattributes"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_literal_checkout_of_a_carried_attributes_file(tmp_path: Path) -> None:
    """Read as a pathspec, the name would check out every other merge-base path instead."""
    repo = _repository(tmp_path, product_deleted_after_fix=True)
    fix = repo.commits["fix"]
    repo.write(ATTRIBUTES_MAGIC, "*.json text eol=lf\n")
    repo.write("x/tests/.gitattributes", "*.json -text\n")
    _rebase_point(repo, "test: add a fixture with a pathspec-like name")
    _bind(repo, [f"OMN-1 {fix}"])
    prepare, _ = _run_steps(repo)

    tree = _assert_parent_control(repo, prepare, fix)
    assert (tree / ATTRIBUTES_MAGIC).read_text() == "*.json text eol=lf\n"
    assert (
        f"Rewritten under every carried attributes rule: {ATTRIBUTES_MAGIC}"
        in prepare.stdout
    )
    assert (tree / "src/product.py").read_text() == "BROKEN = True\n"


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_test_folder_through_a_link_bare_tests_at_the_root(tmp_path: Path) -> None:
    """Reject a bare tests/ folder that is a symlink to qa."""
    repo = _repository(tmp_path)
    repo.git("rm", "-r", "-q", "tests")
    shutil.rmtree(repo.head_tree / "tests", ignore_errors=True)
    repo.write("qa/test_quality.py", "def test_quality():\n    pass\n")
    _symlink(repo, "tests", "qa")
    _bind(repo, [])
    prepare, control = _run_steps(repo)

    assert prepare.returncode == 1, prepare.stdout + prepare.stderr
    assert (
        "::error::the test side is reached through a link at the head: tests"
    ) in prepare.stdout
    assert control is None
