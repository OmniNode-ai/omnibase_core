# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17427: merged dependency-bot PRs keep their exemption on dev push."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

BASH = shutil.which("bash")
if BASH is None:
    pytest.skip("bash is required to run the workflow step", allow_module_level=True)

CI_YML = Path(__file__).resolve().parents[4] / ".github/workflows/ci.yml"
REPO = "OmniNode-ai/omnibase_core"
COMMIT_SHA = "cc3dec48a"
TITLE = "chore(deps): bump the actions group with 14 updates"
WORKFLOW_FILES = [".github/workflows/ci.yml"]

# The canned answers are baked into the fake's own text (``__TOKEN__``
# placeholders), so neither it nor this module reads the process environment.
_FAKE_GH = r"""
import json
import sys
from pathlib import Path

args = sys.argv[1:]
with Path(__CALLS__).open("a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\n")
commit_endpoint = f"repos/{__REPO__}/commits/{__SHA__}/pulls"
files_endpoint = f"repos/{__REPO__}/pulls/{__EXPECTED_PR__}/files"
selection = "[.[] | select(.merged_at != null)] | sort_by(.merged_at) | last // {}"
if args == ["api", commit_endpoint, "--jq", selection]:
    merged = sorted(
        (pr for pr in __COMMIT_PULLS__ if pr["merged_at"] is not None),
        key=lambda pr: pr["merged_at"],
    )
    print(json.dumps(merged[-1] if merged else {}))
elif args == ["api", files_endpoint, "--paginate", "--jq", ".[].filename"]:
    for filename in __PR_FILES__:
        print(filename)
else:
    sys.exit(f"Unexpected gh arguments: {args!r}")
"""


def _tool_path(bindir: Path) -> str:
    tool_dirs = sorted(
        {
            str(Path(found).parent)
            for found in (shutil.which("bash"), shutil.which("env"))
            if found is not None
        }
    )
    return os.pathsep.join([str(bindir), *tool_dirs, "/usr/bin", "/bin"])


def _pr(
    *,
    number: int = 1899,
    author: str = "dependabot[bot]",
    title: str = TITLE,
    merged_at: str | None = "2026-10-06T12:00:00Z",
) -> dict[str, object]:
    return {
        "number": number,
        "user": {"login": author},
        "title": title,
        "merged_at": merged_at,
    }


def _run_step(
    tmp_path: Path,
    *,
    event: str,
    pulls: list[dict[str, object]],
    files: list[str],
    expected_pr: int = 1899,
) -> tuple[str, list[list[str]]]:
    workflow = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    step = next(
        step
        for step in workflow["jobs"]["contract-compliance"]["steps"]
        if step.get("id") == "dep-scope"
    )
    assert step["env"]["COMMIT_SHA"] == "${{ github.sha }}"
    assert "if" not in step
    script = step["run"].replace("${{ github.event_name }}", event)
    # Isolate the workflow's fixed scratch paths for each test execution.
    script = script.replace("/tmp/", f"{tmp_path}/")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    calls = tmp_path / "gh-calls"
    fake = _FAKE_GH
    for token, value in {
        "__CALLS__": str(calls),
        "__REPO__": REPO,
        "__SHA__": COMMIT_SHA,
        "__EXPECTED_PR__": str(expected_pr),
    }.items():
        fake = fake.replace(token, repr(value))
    fake = fake.replace("__COMMIT_PULLS__", repr(pulls))
    fake = fake.replace("__PR_FILES__", repr(files))
    gh.write_text(f"#!{sys.executable}\n" + fake, encoding="utf-8")
    gh.chmod(0o755)
    # Use the test interpreter for both embedded workflow Python blocks.
    (bindir / "python3").symlink_to(sys.executable)
    output = tmp_path / "github-output"
    env = {
        "PATH": _tool_path(bindir),
        "GITHUB_OUTPUT": str(output),
        "GH_REPO": REPO,
        "COMMIT_SHA": COMMIT_SHA,
        # Push must overwrite these unrelated event values with the resolved PR.
        "PR_AUTHOR": "dependabot[bot]" if event == "pull_request" else "event-human",
        "PR_NUMBER": "1899" if event == "pull_request" else "9999",
        "PR_TITLE": TITLE if event == "pull_request" else "event title",
    }
    result = subprocess.run(
        [BASH, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    decisions = [
        line
        for line in output.read_text(encoding="utf-8").splitlines()
        if line.startswith("exempt=")
    ]
    gh_calls = (
        [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
        if calls.exists()
        else []
    )
    return decisions[-1], gh_calls


@pytest.mark.parametrize(
    ("author", "title", "files", "expected"),
    [
        ("dependabot[bot]", TITLE, WORKFLOW_FILES, "exempt=true"),
        ("dependabot[bot]", TITLE, [*WORKFLOW_FILES, "pyproject.toml"], "exempt=false"),
        ("human", TITLE, WORKFLOW_FILES, "exempt=false"),
        ("dependabot[bot]", "Update workflows", WORKFLOW_FILES, "exempt=false"),
        ("dependabot[bot]", TITLE, [], "exempt=false"),
        ("github-actions[bot]", "Bump actions", WORKFLOW_FILES, "exempt=true"),
    ],
    ids=["workflow-only", "product-file", "human", "title", "empty", "actions-bot"],
)
def test_push_classifies_the_merged_pr(
    tmp_path: Path, author: str, title: str, files: list[str], expected: str
) -> None:
    decision, calls = _run_step(
        tmp_path,
        event="push",
        pulls=[_pr(author=author, title=title)],
        files=files,
    )
    assert decision == expected
    assert len(calls) == 2


@pytest.mark.parametrize(
    "pulls", [[], [_pr(merged_at=None)]], ids=["empty", "unmerged"]
)
def test_push_without_a_merged_pr_returns_without_fetching_files(
    tmp_path: Path, pulls: list[dict[str, object]]
) -> None:
    decision, calls = _run_step(
        tmp_path, event="push", pulls=pulls, files=WORKFLOW_FILES
    )
    assert decision == "exempt=false"
    assert len(calls) == 1
    assert calls[0][1] == f"repos/{REPO}/commits/{COMMIT_SHA}/pulls"


def test_push_selects_the_latest_merged_pr_like_the_resolver(tmp_path: Path) -> None:
    decision, calls = _run_step(
        tmp_path,
        event="push",
        pulls=[
            _pr(),
            _pr(number=2000, author="human", merged_at=None),
            _pr(number=1813, author="human", merged_at="2026-10-01T12:00:00Z"),
        ],
        files=WORKFLOW_FILES,
    )
    assert decision == "exempt=true"
    assert calls[-1][1] == f"repos/{REPO}/pulls/1899/files"


@pytest.mark.parametrize("event", ["merge_group", "workflow_dispatch"])
def test_other_events_return_without_calling_gh(tmp_path: Path, event: str) -> None:
    decision, calls = _run_step(
        tmp_path, event=event, pulls=[_pr()], files=WORKFLOW_FILES
    )
    assert decision == "exempt=false"
    assert calls == []


def test_pull_request_uses_event_metadata_and_keeps_the_exemption(
    tmp_path: Path,
) -> None:
    decision, calls = _run_step(
        tmp_path,
        event="pull_request",
        pulls=[_pr(number=1813, author="human", title="Unrelated PR")],
        files=WORKFLOW_FILES,
    )
    assert decision == "exempt=true"
    assert calls == [
        ["api", f"repos/{REPO}/pulls/1899/files", "--paginate", "--jq", ".[].filename"]
    ]
