# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Exercise the real caller control scripts against bindings for merged fixes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
PRODUCT_TEST = """\
from pathlib import Path


def test_product():
    assert "BROKEN = False" in Path("src/product.py").read_text()
"""


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
    repo.commits["initial"] = repo.commit("chore: initial")
    repo.write("src/product.py", "BROKEN = False\n")
    repo.write("tests/test_product.py", PRODUCT_TEST)
    repo.commits["fix"] = repo.commit(fix_subject)
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
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str] | None]:
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
        + dedent("""\
            import json
            import os
            import sys
            from pathlib import Path

            if len(sys.argv) > 1 and sys.argv[1] == "-m":
                product = (Path.cwd() / "src/product.py").read_text()
                status = "verified" if "BROKEN = False" in product else "failed"
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
    assert control is None
    assert not (repo.dod_dir / "base-OMN-1.control.txt").exists()


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
            "not-revertible",
            "::error::the product changes of merged fix {named} do not revert cleanly at the merge base, so the control cannot run",
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
    elif case == "not-revertible":
        repo.write("src/product.py", "BROKEN = False  # rewritten\n")
        repo.commit("chore: rewrite")
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
