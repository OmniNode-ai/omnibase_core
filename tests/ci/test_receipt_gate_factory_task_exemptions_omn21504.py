# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""No exemption of the receipt gate admits a PR citing a factory task ticket (OMN-21504).

A factory task ticket is a Linear ticket whose parent is listed in the
``dod_verify`` overlay's ``parent_tickets``. The gate has no Linear reader, so
the caller resolves those tickets and passes them in the ``factory-task-tickets``
input. Each exemption step of ``dod-verify`` (the dependency-bot author step,
the writer app's pin-only step) refuses to apply when the pull request title
cites one of them, and the PR is then judged like any other. One fixture event
per exemption runs the step as the bash the runner executes. Fixture ticket
ids are invented.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _prepare as _prepare_writer,
)
from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _run as _run_writer,
)

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
FACTORY_TASK = "OMN-90102"
OTHER_FACTORY_TASK = "OMN-90103"
NON_FACTORY = "OMN-90201"
FACTORY_LIST = f"{FACTORY_TASK}\n{OTHER_FACTORY_TASK}"
FACTORY_LIST_JSON = f'["{FACTORY_TASK}", "{OTHER_FACTORY_TASK}"]'


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _steps() -> list[dict[str, Any]]:
    return _workflow()["jobs"]["dod-verify"]["steps"]


def _step(step_id: str) -> dict[str, Any]:
    return next(s for s in _steps() if s.get("id") == step_id)


def _run_author_step(
    tmp_path: Path,
    *,
    author: str,
    title: str,
    factory: str = FACTORY_LIST,
    pr_number: str = "7",
    merge_group_head_ref: str = "",
    api_title: str = "",
) -> dict[str, str]:
    step = _step("bot_exempt")
    script = str(step["run"])
    assert "${{" not in script
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    gh = shim_dir / "gh"
    gh.write_text(
        "#!/bin/bash\n"
        '[ "$1 $2" = "pr view" ] || exit 99\n'
        'case "$*" in\n'
        '  *"--json title"*) printf "%s\\n" "$FAKE_TITLE" ;;\n'
        '  *) printf "%s\\n" "$FAKE_AUTHOR" ;;\n'
        "esac\n"
    )
    gh.chmod(0o755)
    output = tmp_path / "github_output.txt"
    values = {
        "GH_TOKEN": "t",
        "PR_NUMBER": pr_number,
        "PR_EVENT_AUTHOR": author,
        "PR_TITLE": title,
        "FACTORY_TASK_TICKETS": factory,
        "MERGE_GROUP_HEAD_REF": merge_group_head_ref,
        "GH_REPO": "o/r",
    }
    assert set(step["env"]) == set(values)
    result = subprocess.run(
        ["/bin/bash", "-c", script],
        env={
            "PATH": f"{shim_dir}:/usr/bin:/bin:/opt/homebrew/bin",
            "GITHUB_OUTPUT": str(output),
            "FAKE_AUTHOR": author,
            "FAKE_TITLE": api_title,
            **values,
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert set(outputs) == {"exempt", "writer_app"}
    outputs["stdout"] = result.stdout
    return outputs


@pytest.mark.parametrize("bot", ["dependabot[bot]", "app/renovate"])
def test_bot_author_citing_a_factory_task_ticket_is_not_exempt(
    tmp_path: Path, bot: str
) -> None:
    outputs = _run_author_step(
        tmp_path, author=bot, title=f"chore: bump ({FACTORY_TASK})"
    )
    assert outputs["exempt"] == "false"
    assert outputs["writer_app"] == "false"
    assert FACTORY_TASK in outputs["stdout"]


@pytest.mark.parametrize("bot", ["dependabot[bot]", "app/renovate"])
def test_control_bot_author_citing_a_non_factory_ticket_stays_exempt(
    tmp_path: Path, bot: str
) -> None:
    outputs = _run_author_step(
        tmp_path, author=bot, title=f"chore: bump ({NON_FACTORY})"
    )
    assert outputs["exempt"] == "true"


def test_bot_author_with_no_factory_list_stays_exempt_as_before(tmp_path: Path) -> None:
    outputs = _run_author_step(
        tmp_path,
        author="dependabot[bot]",
        title=f"chore: bump ({FACTORY_TASK})",
        factory="",
    )
    assert outputs["exempt"] == "true"


def test_factory_list_accepts_a_json_array(tmp_path: Path) -> None:
    outputs = _run_author_step(
        tmp_path,
        author="dependabot[bot]",
        title=f"chore: bump ({OTHER_FACTORY_TASK})",
        factory=FACTORY_LIST_JSON,
    )
    assert outputs["exempt"] == "false"


def test_a_ticket_id_that_only_prefixes_a_factory_id_is_not_a_match(
    tmp_path: Path,
) -> None:
    outputs = _run_author_step(
        tmp_path, author="dependabot[bot]", title="chore: bump (OMN-9010)"
    )
    assert outputs["exempt"] == "true"


def test_writer_app_citing_a_factory_task_ticket_is_not_marked(tmp_path: Path) -> None:
    outputs = _run_author_step(
        tmp_path, author="onexbot-occ-writer[bot]", title=f"chore: pin ({FACTORY_TASK})"
    )
    assert outputs["exempt"] == "false"
    assert outputs["writer_app"] == "false"


def test_control_writer_app_citing_a_non_factory_ticket_is_marked(
    tmp_path: Path,
) -> None:
    outputs = _run_author_step(
        tmp_path, author="onexbot-occ-writer[bot]", title=f"chore: pin ({NON_FACTORY})"
    )
    assert outputs["exempt"] == "false"
    assert outputs["writer_app"] == "true"


def test_merge_group_event_reads_the_title_from_the_pull_request(
    tmp_path: Path,
) -> None:
    outputs = _run_author_step(
        tmp_path,
        author="dependabot[bot]",
        title="",
        pr_number="",
        merge_group_head_ref="gh-readonly-queue/dev/pr-42-abc",
        api_title=f"chore: bump ({FACTORY_TASK})",
    )
    assert outputs["exempt"] == "false"


def test_unreadable_title_is_not_exempt_when_a_factory_list_is_set(
    tmp_path: Path,
) -> None:
    outputs = _run_author_step(
        tmp_path,
        author="dependabot[bot]",
        title="",
        pr_number="",
        merge_group_head_ref="gh-readonly-queue/dev/pr-42-abc",
        api_title="",
    )
    assert outputs["exempt"] == "false"
    assert "unreadable" in outputs["stdout"]


def _writer_env(
    tmp_path: Path, title: str, factory: str = FACTORY_LIST
) -> dict[str, str]:
    env, _ = _prepare_writer(tmp_path)
    return {**env, "PR_TITLE": title, "FACTORY_TASK_TICKETS": factory}


def test_writer_pin_only_citing_a_factory_task_ticket_is_not_exempt(
    tmp_path: Path,
) -> None:
    env = _writer_env(tmp_path, f"chore: pin ({FACTORY_TASK})")
    result = _run_writer(env)
    assert Path(env["GITHUB_OUTPUT"]).read_text().splitlines() == ["exempt=false"]
    assert FACTORY_TASK in result.stdout


def test_control_writer_pin_only_citing_a_non_factory_ticket_stays_exempt(
    tmp_path: Path,
) -> None:
    env = _writer_env(tmp_path, f"chore: pin ({NON_FACTORY})")
    _run_writer(env)
    assert Path(env["GITHUB_OUTPUT"]).read_text().splitlines() == ["exempt=true"]


def test_writer_pin_only_with_an_unreadable_title_is_not_exempt(tmp_path: Path) -> None:
    env = _writer_env(tmp_path, "")
    _run_writer(env)
    assert Path(env["GITHUB_OUTPUT"]).read_text().splitlines() == ["exempt=false"]


def test_writer_pin_only_with_no_factory_list_is_unchanged(tmp_path: Path) -> None:
    env = _writer_env(tmp_path, f"chore: pin ({FACTORY_TASK})", factory="")
    _run_writer(env)
    assert Path(env["GITHUB_OUTPUT"]).read_text().splitlines() == ["exempt=true"]


def test_docs_only_zone_is_not_an_exemption_of_the_gate() -> None:
    # The zone filter decides which CI jobs run; no dod-verify step reads it,
    # so a docs-only change citing a factory task ticket is judged on its
    # contract like any other pull request.
    for step in _steps():
        text = yaml.safe_dump(step).lower()
        assert "docs_only" not in text, step.get("id")
        assert "zone" not in text, step.get("id")


def test_only_the_two_tested_steps_can_exempt_a_pull_request() -> None:
    writers = [
        s.get("id")
        for s in _steps()
        if "exempt=" in str(s.get("run", ""))
        and "GITHUB_OUTPUT" in str(s.get("run", ""))
    ]
    assert writers == ["bot_exempt", "writer_pin_only"]


def test_the_factory_input_is_declared_and_passed_to_both_exemption_steps() -> None:
    workflow = _workflow()
    inputs = workflow[True]["workflow_call"]["inputs"]  # YAML reads `on` as True
    assert inputs["factory-task-tickets"]["default"] == ""
    for step_id in ("bot_exempt", "writer_pin_only"):
        env = _step(step_id)["env"]
        assert env["FACTORY_TASK_TICKETS"] == "${{ inputs.factory-task-tickets }}"
        assert env["PR_TITLE"] == "${{ github.event.pull_request.title }}"
