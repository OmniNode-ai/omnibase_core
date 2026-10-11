# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21008: ``pr-title / check-title`` is decided by a published omnimarket node.

The required context used to come from the check-title bash step of the
change-control repository's pr-title-check-reusable.yml. The decision now lives in
omnimarket's ``node_pr_title_check_compute`` and the caller job runs it from a
pinned omnimarket release installed with ``--no-deps`` as a tool. Nothing under
``src/`` imports omnimarket. The context name must not move, or branch protection
would need a change: the job keeps its id ``pr-title`` and is named
``pr-title / check-title``, the name the reusable call produced.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.timeout(180)]

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/pr-title-check.yml"
MANIFEST = ROOT / ".github/required-checks.yaml"
NODE_DEPENDENCY = "pydantic>=2.11"
CONTEXT = "pr-title / check-title"
NODE_MODULE = "omnimarket.nodes.node_pr_title_check_compute"
RUNNER = """${{
  (github.event_name == 'pull_request' &&
   github.event.pull_request.head.repo.full_name != github.repository)
  && fromJSON(vars.OMNI_PUBLIC_PR_RUNS_ON_JSON || '["ubuntu-latest"]')
  || fromJSON(vars.OMNI_TRUSTED_CI_RUNS_ON_JSON || '["self-hosted","omnibase-ci"]')
}}"""

# Decision branches from the previously pinned reusable
# (onex_change_control pr-title-check-reusable.yml at
# 6ee1ebdb88514c91ab9017db41a575fc9e5dc674). Keep this oracle independent of the
# installed node, including empty-title precedence and the case-sensitive bot
# suffix and ticket pattern.
LEGACY_DECISION = r"""
if [[ -z "$PR_TITLE" ]]; then exit 1; fi
TITLE_LOWER=$(echo "$PR_TITLE" | tr '[:upper:]' '[:lower:]')
if [[ "$PR_AUTHOR" == *"[bot]" ]]; then exit 0; fi
if [[ "$TITLE_LOWER" =~ ^(chore\(deps|build\(deps|bump ) ]]; then exit 0; fi
if [[ "$TITLE_LOWER" =~ ^(chore:\ release|chore\(release\)|release:) ]]; then exit 0; fi
if echo "$PR_TITLE" | grep -qE 'OMN-[0-9]+'; then exit 0; fi
exit 1
"""


def _workflow() -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return loaded


def _job() -> dict[str, Any]:
    job: dict[str, Any] = _workflow()["jobs"]["pr-title"]
    return job


def _environment() -> dict[str, str]:
    return {
        key: value
        for step in _job()["steps"]
        for key, value in (step.get("env") or {}).items()
    }


def test_workflow_no_longer_calls_change_control() -> None:
    assert "onex_change_control" not in WORKFLOW.read_text(encoding="utf-8")
    assert "uses" not in _job()


def test_workflow_keeps_context_triggers_and_runner() -> None:
    job = _job()
    assert job["name"] == CONTEXT
    assert job["runs-on"] == RUNNER
    assert job["timeout-minutes"] == 10
    assert job["permissions"] == {"contents": "read"}
    assert job["needs"] == "occ-preflight"
    assert job["if"] == "always()"
    assert _workflow()[True]["pull_request"]["types"] == [
        "opened",
        "edited",
        "synchronize",
        "reopened",
    ]


def test_workflow_runs_the_pinned_node_without_a_checkout() -> None:
    steps = _job()["steps"]
    assert len(steps) == 2
    assert steps[0]["uses"] == (
        "astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78"
    )
    env = _environment()
    assert re.fullmatch(r"\d+\.\d+\.\d+", env["OMNIMARKET_VERSION"])
    assert tuple(map(int, env["OMNIMARKET_VERSION"].split("."))) >= (0, 4, 310)
    assert env["PR_TITLE"] == "${{ github.event.pull_request.title }}"
    assert env["PR_AUTHOR"] == "${{ github.event.pull_request.user.login }}"
    script = steps[1]["run"]
    assert f'"${{venv}}/bin/python" -I -m {NODE_MODULE}' in script
    assert '--no-deps "omnimarket==${OMNIMARKET_VERSION}"' in script
    assert f'"{NODE_DEPENDENCY}"' in script
    assert "json.dumps" in script
    assert 'os.environ["PR_TITLE"]' in script
    assert 'os.environ["PR_AUTHOR"]' in script
    assert "set -euo pipefail" in script


def test_manifest_names_the_local_producer() -> None:
    gates = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["gates"]
    row = next(gate for gate in gates if gate["name"] == CONTEXT)
    assert row["mode"] == "REQUIRED"
    assert row["producer_kind"] == "local"
    assert row["workflow"] == "pr-title-check.yml"
    assert row["job_path"] == ["pr-title"]
    assert row["skip_semantics"] == "never"
    assert not {"cross_repo_ref", "caller_job", "caller_workflow"} & row.keys()
    assert "onex_change_control" not in row["rationale"]


@pytest.fixture(scope="session")
def installed_node_python(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Install the workflow's published version, isolated from every clone."""
    uv = shutil.which("uv")
    assert uv, "uv is required to exercise the workflow's installation boundary"
    venv = tmp_path_factory.mktemp("published-pr-title") / "venv"
    subprocess.run(
        [uv, "venv", "--quiet", "--python", "3.12", str(venv)],
        check=True,
        timeout=90,
    )
    python = venv / "bin/python"
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--quiet",
            "--python",
            str(python),
            "--no-deps",
            f"omnimarket=={_environment()['OMNIMARKET_VERSION']}",
        ],
        check=True,
        timeout=90,
    )
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--quiet",
            "--python",
            str(python),
            NODE_DEPENDENCY,
        ],
        check=True,
        timeout=90,
    )
    return python


@pytest.mark.parametrize(
    ("title", "author", "expected"),
    [
        ("fix: OMN-21008 title check", "human", 0),
        ("fix: missing ticket", "human", 1),
        ("maintenance", "app[bot]", 0),
        ("maintenance", "app[BOT]", 1),
        ("maintenance", "app[bot]-human", 1),
        ("chore(deps): update", "human", 0),
        ("CHORE(DEPS-dev): update", "human", 0),
        ("build(deps): update", "human", 0),
        ("BUILD(DEPS-dev): update", "human", 0),
        ("bump package", "human", 0),
        ("BuMp package", "human", 0),
        ("chore: release package", "human", 0),
        ("CHORE: RELEASE package", "human", 0),
        ("chore(release): package", "human", 0),
        ("CHORE(RELEASE): package", "human", 0),
        ("release: package", "human", 0),
        ("RELEASE: package", "human", 0),
        ("fix: omn-21008", "human", 1),
        ("fix: OMN-abc", "human", 1),
        ("prefixOMN-1suffix", "human", 0),
        ("fix: OMN-1 and OMN-2", "human", 0),
        ("bump", "human", 1),
        (" chore(deps): update", "human", 1),
        ("fix: chore(deps): update", "human", 1),
        ("chore(release-extra): package", "human", 1),
        ("release package", "human", 1),
        ("", "human", 1),
        ("", "app[bot]", 1),
        ("fix: OMN-21008\nmore", "human", 0),
        ('fix: quotes " and $(false)', "human", 1),
    ],
)
def test_verdicts_equal_old_reusable(
    installed_node_python: Path, title: str, author: str, expected: int
) -> None:
    bash = shutil.which("bash")
    assert bash
    legacy = subprocess.run(
        [bash, "-c", LEGACY_DECISION],
        env={
            "PATH": "/usr/bin:/bin",
            "PR_TITLE": title,
            "PR_AUTHOR": author,
            "LC_ALL": "C",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    node = subprocess.run(
        [str(installed_node_python), "-I", "-m", NODE_MODULE],
        input=json.dumps({"title": title, "author": author}),
        cwd=installed_node_python.parent,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert legacy.returncode == expected, legacy.stderr
    assert node.returncode == legacy.returncode, node.stdout + node.stderr


@pytest.mark.parametrize("payload", ["{", "{}", '{"title": 42, "author": "human"}'])
def test_verdicts_malformed_request_exits_two(
    installed_node_python: Path, payload: str
) -> None:
    result = subprocess.run(
        [str(installed_node_python), "-I", "-m", NODE_MODULE],
        input=payload,
        cwd=installed_node_python.parent,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
