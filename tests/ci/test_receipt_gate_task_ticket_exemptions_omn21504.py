# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""No receipt-gate exemption admits a PR that cites a factory task ticket (OMN-21504).

Extract the dod-verify steps from receipt-gate.yml and run them under bash with
controlled GitHub metadata, one fixture event per exemption: the dependency-bot
author, the writer app's dependency-pin-only change, and the docs-only zone. The
overlay lists come from a fixture ``dod_verify`` overlay, read at the PR's base
sha; the same facts run through the core checker must give the same verdict.
"""

from __future__ import annotations

import base64
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.handlers.handler_parent_ticket_citation import (
    check_parent_ticket_citation,
)
from omnibase_core.models.validation.model_dod_verify_overlay import (
    ModelDodVerifyOverlay,
)
from omnibase_core.models.validation.model_parent_ticket_citation_facts import (
    ModelParentTicketCitationFacts,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"
CALLER_PATH = REPO_ROOT / ".github" / "workflows" / "call-repo-evidence-gate.yml"
PARENT = "OMN-21433"
TASK = "OMN-21504"
OVERLAY_PATH = ".github/overlays/dod_verify/overlay.yaml"


def _steps() -> list[dict[str, Any]]:
    return yaml.safe_load(WORKFLOW_PATH.read_text())["jobs"]["dod-verify"]["steps"]


def _step(step_id: str) -> dict[str, Any]:
    return next(step for step in _steps() if step.get("id") == step_id)


def _overlay_text(parents: list[str], tasks: list[str]) -> str:
    return yaml.safe_dump(
        {"dod_verify": {"parent_tickets": parents, "factory_task_tickets": tasks}}
    )


def _run_policy(
    tmp_path: Path,
    *,
    title: str,
    parents: list[str],
    tasks: list[str],
    overlay_path: str = OVERLAY_PATH,
    overlay_text: str | None = None,
) -> tuple[int, dict[str, str], str]:
    step = _step("ticket_policy")
    script = str(step["run"])
    assert "${{" not in script
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    body = overlay_text if overlay_text is not None else _overlay_text(parents, tasks)
    encoded = base64.b64encode(body.encode()).decode()
    gh = shim_dir / "gh"
    gh.write_text(
        "#!/bin/bash\n"
        'printf "%s\\n" "$*" >> "$GH_CALLS"\n'
        f'case "$*" in *"contents/{OVERLAY_PATH}"*"ref=basesha"*) ;; *) exit 44 ;; esac\n'
        f'printf "%s" "{encoded}"\n'
    )
    gh.chmod(0o755)
    output = tmp_path / "github_output.txt"
    output.write_text("")
    values = {
        "GH_TOKEN": "t",
        "GH_REPO": "o/r",
        "PR_TITLE": title,
        "BASE_SHA": "basesha",
        "OVERLAY_PATH": overlay_path,
    }
    assert set(step["env"]) == set(values)
    env = {
        "PATH": f"{shim_dir}:/usr/bin:/bin",
        "GITHUB_OUTPUT": str(output),
        "GH_CALLS": str(tmp_path / "gh_calls.txt"),
        "RUNNER_TEMP": str(tmp_path),
        "HOME": str(tmp_path),
        **values,
    }
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = dict(
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )
    return result.returncode, outputs, result.stdout + result.stderr


def test_a_pr_citing_only_the_parent_is_refused_naming_the_ticket(
    tmp_path: Path,
) -> None:
    code, _, log = _run_policy(
        tmp_path, title=f"T-Q1: x ({PARENT})", parents=[PARENT], tasks=[TASK]
    )
    assert code != 0
    assert PARENT in log


def test_control_a_pr_citing_a_task_ticket_passes_and_is_marked(
    tmp_path: Path,
) -> None:
    code, outputs, _ = _run_policy(
        tmp_path, title=f"T-Q1: x ({TASK})", parents=[PARENT], tasks=[TASK]
    )
    assert code == 0
    assert outputs["cites_task_ticket"] == "true"


def test_the_same_pr_is_verified_normally_under_an_overlay_omitting_the_ticket(
    tmp_path: Path,
) -> None:
    code, outputs, _ = _run_policy(
        tmp_path, title=f"x ({PARENT})", parents=["OMN-21400"], tasks=[TASK]
    )
    assert code == 0
    assert outputs["cites_task_ticket"] == "false"


def test_no_overlay_input_leaves_the_gate_as_it_was(tmp_path: Path) -> None:
    code, outputs, _ = _run_policy(
        tmp_path, title=f"x ({PARENT})", parents=[], tasks=[], overlay_path=""
    )
    assert code == 0
    assert outputs["cites_task_ticket"] == "false"


@pytest.mark.parametrize(
    "overlay_text",
    ["not: [valid", "other: {}\n", "dod_verify: {parent_tickets: oops}\n"],
)
def test_an_unreadable_overlay_fails_closed(tmp_path: Path, overlay_text: str) -> None:
    code, _, _ = _run_policy(
        tmp_path,
        title=f"x ({TASK})",
        parents=[],
        tasks=[],
        overlay_text=overlay_text,
    )
    assert code != 0


@pytest.mark.parametrize(
    ("title", "parents", "tasks"),
    [
        (f"x ({PARENT})", [PARENT], [TASK]),
        (f"x ({TASK})", [PARENT], [TASK]),
        (f"x ({PARENT}) ({TASK})", [PARENT], [TASK]),
        (f"x ({PARENT})", ["OMN-21400"], [TASK]),
        ("no ticket", [PARENT], [TASK]),
    ],
)
def test_the_gate_step_agrees_with_the_core_checker(
    tmp_path: Path, title: str, parents: list[str], tasks: list[str]
) -> None:
    code, outputs, _ = _run_policy(tmp_path, title=title, parents=parents, tasks=tasks)
    cited = tuple(sorted(set(re.findall(r"OMN-\d+", title))))
    issues = check_parent_ticket_citation(
        ModelParentTicketCitationFacts(cited_tickets=cited),
        ModelDodVerifyOverlay(
            parent_tickets=tuple(parents), factory_task_tickets=tuple(tasks)
        ),
    )
    assert (code != 0) == bool(issues)
    if code == 0:
        assert (
            outputs["cites_task_ticket"] == str(TASK in cited and TASK in tasks).lower()
        )


def _run_author(
    tmp_path: Path, *, author: str, cites_task_ticket: str
) -> dict[str, str]:
    step = _step("bot_exempt")
    script = str(step["run"])
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    gh = shim_dir / "gh"
    gh.write_text('#!/bin/bash\nprintf "%s\\n" "$FAKE_AUTHOR"\n')
    gh.chmod(0o755)
    output = tmp_path / "github_output.txt"
    output.write_text("")
    env = {
        "PATH": f"{shim_dir}:/usr/bin:/bin",
        "GITHUB_OUTPUT": str(output),
        "FAKE_AUTHOR": author,
        "GH_TOKEN": "t",
        "PR_NUMBER": "7",
        "PR_EVENT_AUTHOR": author,
        "MERGE_GROUP_HEAD_REF": "",
        "GH_REPO": "o/r",
        "CITES_TASK_TICKET": cites_task_ticket,
    }
    assert set(step["env"]) == set(env) - {"PATH", "GITHUB_OUTPUT", "FAKE_AUTHOR"}
    subprocess.run(
        ["bash", "-e", "-c", script], env=env, check=True, capture_output=True
    )
    return dict(
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )


@pytest.mark.parametrize(
    "author",
    [
        "dependabot[bot]",
        "renovate[bot]",
        "onexbot-occ-writer[bot]",
        "app/onexbot-occ-writer",
    ],
)
def test_a_bot_author_citing_a_task_ticket_is_exempt_from_nothing(
    tmp_path: Path, author: str
) -> None:
    # The dependency-bot arm and the writer-app arm (whose pin-only verdict is
    # derived only when writer_app is true) both stop being exemptions.
    assert _run_author(tmp_path, author=author, cites_task_ticket="true") == {
        "exempt": "false",
        "writer_app": "false",
    }


def test_control_the_exemptions_stand_without_a_task_ticket(tmp_path: Path) -> None:
    bot = tmp_path / "a"
    bot.mkdir()
    writer = tmp_path / "b"
    writer.mkdir()
    assert _run_author(bot, author="dependabot[bot]", cites_task_ticket="false") == {
        "exempt": "true",
        "writer_app": "false",
    }
    assert _run_author(
        writer, author="onexbot-occ-writer[bot]", cites_task_ticket="false"
    ) == {"exempt": "false", "writer_app": "true"}


def test_the_writer_pin_only_exemption_only_follows_the_marked_writer_app() -> None:
    step = _step("writer_pin_only")
    assert "steps.bot_exempt.outputs.writer_app == 'true'" in str(step["if"])


def test_ticket_policy_runs_before_every_exemption_step() -> None:
    ids = [step.get("id") for step in _steps()]
    assert ids.index("ticket_policy") < ids.index("bot_exempt")
    assert "if" not in _step("ticket_policy")
    assert "steps.ticket_policy.outputs.cites_task_ticket" in str(
        _step("bot_exempt")["env"]
    )


def test_the_docs_only_zone_does_not_exempt_the_receipt_gate() -> None:
    # The docs-only zone narrows the heavy CI matrix. A docs-only PR citing a
    # factory task ticket still reaches the gate's verdict: neither the caller
    # nor any gate step reads the zone, and the caller has no path filter.
    text = WORKFLOW_PATH.read_text() + CALLER_PATH.read_text()
    assert "docs_only" not in text
    assert "zone-filter" not in text
    caller = yaml.safe_load(CALLER_PATH.read_text())
    event = (caller.get("on") or caller.get(True))["pull_request_target"]
    assert "paths" not in event and "paths-ignore" not in event
    job = yaml.safe_load(WORKFLOW_PATH.read_text())["jobs"]["dod-verify"]
    assert "needs" not in job
    assert not any("zone" in str(step.get("if", "")).lower() for step in job["steps"])


def test_the_shadow_verdict_lists_the_new_step() -> None:
    assert (
        "ticket_policy"
        in WORKFLOW_PATH.read_text().split("for step_id in", 1)[1].split(";", 1)[0]
    )


def test_workflow_declares_the_overlay_input() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    inputs = (data.get("on") or data.get(True))["workflow_call"]["inputs"]
    assert inputs["dod-verify-overlay"]["default"] == ""
