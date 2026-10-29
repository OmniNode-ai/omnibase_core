# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Executable author classification for receipt-gate dod-verify (OMN-20161).

Dependency bots are exempt. Writer apps must derive their verdict at the head;
the author step only marks them and reads GitHub author metadata, never the body.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validation.validator_receipt_gate import (
    DEPENDENCY_BOT_AUTHORS,
    OCC_WRITER_BOT_AUTHORS,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "receipt-gate.yml"
WRITER_LOGINS = (
    "onexbot-occ-writer[bot]",
    "app/onexbot-occ-writer",
    "onexbot-occ-writer",
)
NEAR_MISSES = (
    "onexbot-occ-writer-fork",
    "app/onexbot-occ-writerx",
    "xonexbot-occ-writer",
    "dependabot-fork",
    "app/renovatex",
)
HUMANS = ("jonah", "jonahgabriel")


def _steps() -> list[dict[str, Any]]:
    return yaml.safe_load(WORKFLOW_PATH.read_text())["jobs"]["dod-verify"]["steps"]


def _bot_exempt() -> dict[str, Any]:
    return next(s for s in _steps() if s.get("id") == "bot_exempt")


def _run(
    tmp_path: Path,
    *,
    author: str,
    api_author: str | None = None,
    api_exit: int = 0,
    pr_number: str = "7",
    merge_group_head_ref: str = "",
    body: str = "Evidence-Source: OCC#123\nDEPENDENCY_PIN_ONLY",
) -> tuple[dict[str, str], list[str]]:
    step = _bot_exempt()
    script = str(step["run"])
    assert "${{" not in script
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    gh = shim_dir / "gh"
    gh.write_text(
        "#!/bin/bash\n"
        'printf "%s\\n" "$*" >> "$GH_CALLS"\n'
        '[ "$1 $2" = "pr view" ] || exit 99\n'
        'printf "%s\\n" "$FAKE_AUTHOR"\n'
        'exit "$FAKE_EXIT"\n'
    )
    gh.chmod(0o755)
    # Any attempted probe interpreter is observable and fails immediately.
    probe_calls = tmp_path / "probe_calls.txt"
    for command in ("python", "python3", "uv"):
        shim = shim_dir / command
        shim.write_text('#!/bin/bash\necho "$*" >> "$PROBE_CALLS"\nexit 99\n')
        shim.chmod(0o755)
    record = tmp_path / "gh_calls.txt"
    output = tmp_path / "github_output.txt"
    values = {
        "GH_TOKEN": "t",
        "PR_NUMBER": pr_number,
        "PR_EVENT_AUTHOR": author,
        "MERGE_GROUP_HEAD_REF": merge_group_head_ref,
        "GH_REPO": "o/r",
        "CITES_TASK_TICKET": "false",
    }
    assert set(step["env"]) == set(values)
    result = subprocess.run(
        ["/bin/bash", "-c", script],
        env={
            "PATH": f"{shim_dir}:/usr/bin:/bin",
            "GITHUB_OUTPUT": str(output),
            "FAKE_AUTHOR": author if api_author is None else api_author,
            "FAKE_EXIT": str(api_exit),
            "GH_CALLS": str(record),
            "PROBE_CALLS": str(probe_calls),
            "PR_BODY": body,
            **values,
        },
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    lines = output.read_text().splitlines()
    assert len(lines) == 2
    outputs = dict(line.split("=", 1) for line in lines)
    assert set(outputs) == {"exempt", "writer_app"}
    assert not probe_calls.exists()
    calls = record.read_text().splitlines() if record.exists() else []
    # All metadata reads must request the author alone, so body tokens cannot
    # manufacture an exemption or impersonate the writer app.
    resolved = pr_number or ("42" if merge_group_head_ref else "")
    assert calls == (
        [f"pr view {resolved} --repo o/r --json author --jq .author.login"]
        if resolved
        else []
    )
    assert ("::notice::Receipt-gate exemption" in result.stdout) == (
        outputs["exempt"] == "true"
    )
    return outputs, calls


@pytest.mark.parametrize("login", WRITER_LOGINS)
def test_writer_apps_require_a_job_local_verdict(tmp_path: Path, login: str) -> None:
    outputs, _ = _run(tmp_path, author=login)
    assert outputs == {"exempt": "false", "writer_app": "true"}


@pytest.mark.parametrize("login", [*HUMANS, *NEAR_MISSES])
@pytest.mark.parametrize(
    "body", ["", "onexbot-occ-writer[bot]\nDEPENDENCY_PIN_ONLY\nexempt=true"]
)
def test_humans_and_near_misses_are_not_exempt(
    tmp_path: Path, login: str, body: str
) -> None:
    outputs, _ = _run(tmp_path, author=login, body=body)
    assert outputs == {"exempt": "false", "writer_app": "false"}


@pytest.mark.parametrize("login", sorted(DEPENDENCY_BOT_AUTHORS))
def test_dependency_bots_stay_exempt(tmp_path: Path, login: str) -> None:
    outputs, _ = _run(tmp_path, author=login)
    assert outputs == {"exempt": "true", "writer_app": "false"}


@pytest.mark.parametrize("login", ["jonah", "dependabot[bot]", *WRITER_LOGINS])
@pytest.mark.parametrize("api_exit", [0, 1])
def test_author_falls_back_to_the_event_when_api_is_unavailable(
    tmp_path: Path, login: str, api_exit: int
) -> None:
    outputs, _ = _run(tmp_path, author=login, api_author="", api_exit=api_exit)
    assert outputs == {
        "exempt": str(login in DEPENDENCY_BOT_AUTHORS).lower(),
        "writer_app": str(login in OCC_WRITER_BOT_AUTHORS).lower(),
    }


def test_api_author_takes_precedence_over_event_login(tmp_path: Path) -> None:
    outputs, _ = _run(tmp_path, author="dependabot[bot]", api_author="jonah")
    assert outputs == {"exempt": "false", "writer_app": "false"}


def test_merge_group_resolves_the_pr_number_for_author_metadata(tmp_path: Path) -> None:
    outputs, _ = _run(
        tmp_path,
        author=WRITER_LOGINS[0],
        pr_number="",
        merge_group_head_ref="refs/heads/gh-readonly-queue/dev/pr-42-abc123",
    )
    assert outputs == {"exempt": "false", "writer_app": "true"}


def test_event_author_without_a_pr_number_needs_no_api_call(tmp_path: Path) -> None:
    outputs, calls = _run(tmp_path, author="dependabot[bot]", pr_number="")
    assert outputs == {"exempt": "true", "writer_app": "false"}
    assert calls == []


_ARM_RE = re.compile(r'^\s*((?:"[^"\n]+"\|)*"[^"\n]+")\)\s*$', re.MULTILINE)


def test_case_arms_match_the_python_sets() -> None:
    arms = [
        frozenset(re.findall(r'"([^"]+)"', m.group(1)))
        for m in _ARM_RE.finditer(str(_bot_exempt()["run"]))
    ]
    assert arms == [DEPENDENCY_BOT_AUTHORS, OCC_WRITER_BOT_AUTHORS]


def test_author_step_has_no_probe_or_pr_body_read() -> None:
    script = _bot_exempt()["run"]
    assert "--json author --jq '.author.login'" in script
    for retired in (
        "occ_preflight_wait.py",
        "--check-no-companion-required",
        "PR_BODY",
        "--json body",
    ):
        assert retired not in script
    assert "occ_probe_checkout" not in {s.get("id") for s in _steps()}


def test_every_dod_verify_step_after_bot_exempt_is_gated_on_it() -> None:
    steps = _steps()
    assert steps[0]["id"] == "ticket_policy"
    assert "if" not in steps[0]
    assert steps[1]["id"] == "bot_exempt"
    after = steps[2:]
    assert after
    ungated = [
        s["name"]
        for s in after
        if "steps.bot_exempt.outputs.exempt != 'true'" not in str(s.get("if", ""))
    ]
    assert ungated == ["Summarise"]
    assert after[-1]["if"] == "always()"
