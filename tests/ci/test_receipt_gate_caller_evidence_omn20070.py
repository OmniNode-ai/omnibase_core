# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Guards for caller verification, its must-fail control, and input refusals."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
HEAD_STEP = "Verify the contract at the PR head"
BASE_STEP = "Must-fail control at the merge base"
DIFFERENCE_STEP = "Difference against OCC's verdict for the same head"
PG_TOOLS_STEP = "Provide the PostgreSQL 16 server tools"
PG_ENV_STEP = "Export the Postgres service to the bound tests"


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _job() -> dict[str, Any]:
    return _workflow()["jobs"]["dod-verify"]


def _step(name: str) -> dict[str, Any]:
    return next(step for step in _job()["steps"] if step.get("name") == name)


def test_inputs_preserve_existing_defaults_and_expose_caller_verifier() -> None:
    workflow = _workflow()
    # PyYAML interprets the YAML 1.1 `on` key as True.
    trigger = workflow.get(True, workflow.get("on"))
    assert isinstance(trigger, dict)
    inputs = trigger["workflow_call"]["inputs"]
    expected = {
        "evidence-source": "caller",
        "verifier-version": "0.4.305",
        "compare-with-occ": "false",
        "shadow": "false",
    }
    assert set(inputs) == set(expected)
    for name, default in expected.items():
        assert inputs[name]["default"] == default
        assert inputs[name]["type"] == "string"
        assert inputs[name]["required"] is False


def test_jobs_run_without_conditions_and_preserve_caller_verification() -> None:
    verify = _workflow()["jobs"]["verify"]
    # OMN-20074: verify runs in every mode; caller mode makes it a no-op.
    assert "if" not in verify
    assert [step["name"] for step in verify["steps"]] == [
        "Caller evidence runs in dod-verify"
    ]
    caller = _job()
    assert caller["name"] == "dod-verify"
    assert "if" not in caller
    # Same routing as verify, with pull_request_target counted as a pull request.
    assert (
        caller["runs-on"].replace(
            "((github.event_name == 'pull_request' || github.event_name == 'pull_request_target') &&",
            "(github.event_name == 'pull_request' &&",
        )
        == verify["runs-on"]
    )
    assert caller["timeout-minutes"] == 40
    assert caller["env"] == {"ACTIONS_CACHE_URL": "", "ACTIONS_RUNTIME_URL": ""}
    assert caller["permissions"] == {"contents": "read", "pull-requests": "read"}


def test_caller_steps_run_in_order_without_an_occ_checkout() -> None:
    steps = _job()["steps"]
    assert [step.get("name") for step in steps] == [
        "Detect dependency-bot author (receipt-gate exemption)",
        "Refuse anything but a same-repository pull request",
        "Resolve the cited tickets",
        "Check out the pull request head",
        "Set up Python 3.13",
        "Install uv",
        "Install the pinned verifier",
        "Derive the OCC writer app's dependency-pin-only or release-cut verdict at the head (OMN-17427, OMN-20074)",
        PG_TOOLS_STEP,
        PG_ENV_STEP,
        "Provision the contracts' declared sibling checkouts",
        HEAD_STEP,
        "Prepare the merge base with the pull request's test side laid over it",
        BASE_STEP,
        "Summarise",
    ]
    for step in steps:
        assert (
            step.get("with", {}).get("repository") != "OmniNode-ai/onex_change_control"
        )
    checkout = _step("Check out the pull request head")
    assert checkout["uses"] == "actions/checkout@v7"
    assert checkout["with"] == {
        "repository": "${{ github.repository }}",
        "ref": "${{ github.event.pull_request.head.sha }}",
        "fetch-depth": 0,
        "persist-credentials": False,
        "path": ".dod-verify/head_home/${{ github.event.repository.name }}",
    }
    assert _step("Set up Python 3.13")["with"]["python-version"] == "3.13"
    assert _step("Install uv")["uses"] == "astral-sh/setup-uv@v7"


def test_caller_scripts_use_env_for_expression_values() -> None:
    for step in _job()["steps"]:
        script = step.get("run", "")
        for expression in (
            "${{ github.event.",
            "${{ github.repository",
            "${{ github.workspace",
            "${{ inputs.",
        ):
            assert expression not in script, step.get("name")
    refusal = _step("Refuse anything but a same-repository pull request")
    assert "pull_request|pull_request_target" in refusal["run"]
    assert '[ "$HEAD_REPOSITORY" != "$CALLER_REPOSITORY" ]' in refusal["run"]
    assert refusal["env"]["COMPARE_WITH_OCC"] == "${{ inputs.compare-with-occ }}"
    assert refusal["env"]["EVIDENCE_SOURCE"] == "${{ inputs.evidence-source }}"
    for switch, allowed in (
        ("COMPARE_WITH_OCC", "false"),
        ("EVIDENCE_SOURCE", "caller"),
    ):
        assert f'[ "${switch}" != {allowed} ]' in refusal["run"]
    assert "::error::compare-with-occ must be false" in refusal["run"]
    assert "::error::evidence-source must be caller" in refusal["run"]
    tickets = _step("Resolve the cited tickets")
    assert tickets["env"]["PR_TITLE"] == "${{ github.event.pull_request.title }}"
    assert "grep -oE 'OMN-[0-9]+'" in tickets["run"]
    assert "^OMN-[0-9]+$" in tickets["run"]


def test_install_validates_and_pins_the_verifier_before_importing() -> None:
    step = _step("Install the pinned verifier")
    assert step["env"]["VERIFIER_VERSION"] == "${{ inputs.verifier-version }}"
    script = step["run"]
    assert r"^[0-9]+\.[0-9]+\.[0-9]+$" in script
    assert script.index(r"^[0-9]+\.[0-9]+\.[0-9]+$") < script.index("uv pip install")
    assert '"omnimarket==${VERIFIER_VERSION}"' in script
    assert "--no-config" in script
    assert (
        'uv venv --clear --python 3.13 "$GITHUB_WORKSPACE/.dod-verify/venv"' in script
    )
    assert '"$GITHUB_ENV"' in script
    assert '"$DOD_VERIFY_PY" -c "import omnimarket.nodes.node_dod_verify"' in script


@pytest.mark.parametrize("name", [HEAD_STEP, BASE_STEP])
def test_both_invocations_use_the_same_node_and_allow_detached_ci_clones(
    name: str,
) -> None:
    step = _step(name)
    assert step["env"]["DOD_VERIFY_ALLOW_STALE_PRODUCT_CLONE"] == "1"
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
    script = step["run"]
    assert '"$DOD_VERIFY_PY" -m omnimarket.nodes.node_dod_verify' in script
    assert "--execution-audience hosted" in script
    assert "Receipt written to:" in script


def test_head_failure_keeps_json_diagnostics() -> None:
    script = _step(HEAD_STEP)["run"]
    assert "set -euo pipefail" in script
    assert "|| rc=$?" in script
    assert "status=" in script
    assert "error_message=" in script
    assert "stdout is not JSON" in script
    assert "but carries no contracts/$ticket.yaml" in script


def test_base_overlay_requires_changed_tests_and_cited_contracts() -> None:
    script = _step(
        "Prepare the merge base with the pull request's test side laid over it"
    )["run"]
    assert 'merge-base "$BASE_SHA" "$HEAD_SHA"' in script
    assert 'fetch --no-tags origin "$BASE_SHA"' in script
    assert 'worktree add --detach "$control_tree" "$MB"' in script
    assert (
        'prepare_control "$GITHUB_WORKSPACE/.dod-verify/base_home" "the merge base"'
        in script
    )
    assert "--diff-filter=ACMR" in script
    assert "while IFS= read -r" in script
    assert '"$path" == *..* || "$path" == /*' in script
    assert 'rm -rf "$GITHUB_WORKSPACE/.dod-verify/base_home"' in script
    assert '"contracts/$ticket.yaml"' in script
    assert "no test-side change: the bound tests cannot be shown to fail" in script


def test_control_refuses_always_pass_non_failed_and_missing_bound_checks() -> None:
    script = _step(BASE_STEP)["run"]
    assert "select((.binds_ac | length) > 0)" in script
    assert 'select(.status == "verified")' in script
    assert 'select(.status != "failed" and .status != "verified")' in script
    assert 'where="$(cat "$RUNNER_TEMP/dod/control-label-$ticket.txt")"' in script
    for message in (
        "zero bound checks",
        "bound test also passes at $where: the control did not fail (always-pass)",
        "the control could not run, a control that did not run is not a pass",
        "control stdout is not parseable",
    ):
        assert message in script
    assert ".evidence_id" in script
    assert 'exit "$failed"' in script


@pytest.mark.parametrize(
    ("source", "compare", "event", "head_repo", "error"),
    [
        ("caller", "false", "pull_request", "o/r", None),
        ("caller", "false", "pull_request_target", "o/r", None),
        ("occ", "false", "pull_request", "o/r", "evidence-source must be caller"),
        ("", "false", "pull_request", "o/r", "evidence-source must be caller"),
        ("caller", "true", "pull_request", "o/r", "compare-with-occ must be false"),
        ("caller", "FALSE", "pull_request", "o/r", "compare-with-occ must be false"),
        ("caller", "", "pull_request", "o/r", "compare-with-occ must be false"),
        (
            "caller",
            "false",
            "merge_group",
            "o/r",
            "requires a pull_request or pull_request_target event",
        ),
        (
            "caller",
            "false",
            "pull_request",
            "fork/r",
            "requires a same-repository pull request",
        ),
    ],
)
def test_same_repository_guard_accepts_only_supported_caller_inputs(
    source: str, compare: str, event: str, head_repo: str, error: str | None
) -> None:
    result = subprocess.run(
        [
            "/bin/bash",
            "-c",
            _step("Refuse anything but a same-repository pull request")["run"],
        ],
        env={
            "EVIDENCE_SOURCE": source,
            "COMPARE_WITH_OCC": compare,
            "EVENT_NAME": event,
            "HEAD_REPOSITORY": head_repo,
            "CALLER_REPOSITORY": "o/r",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if error is None else 1), result.stderr
    if error is None:
        assert result.stdout == ""
    else:
        assert len(result.stdout.splitlines()) == 1
        assert result.stdout.startswith("::error::")
        assert error in result.stdout


def test_retired_occ_difference_is_absent_from_the_caller_job() -> None:
    assert HEAD_STEP in {s["name"] for s in _job()["steps"]}
    assert DIFFERENCE_STEP not in {s["name"] for s in _job()["steps"]}
    assert "occ_difference" not in {s.get("id") for s in _job()["steps"]}


def test_summary_always_reports_head_and_base_without_failing() -> None:
    step = _step("Summarise")
    assert step["if"] == "always()"
    script = step["run"]
    for field in (
        "Verifier version:",
        "Head SHA:",
        "Merge base SHA:",
        "acceptance_basis",
    ):
        assert field in script
    assert "base control" in script
    assert "occ-difference.json" not in script
    assert "OCC difference:" not in script
    assert "occ_probe_checkout" not in script
    assert (
        'verdict_line="Shadow verdict: head=$HEAD_SHA new_path=$new_path refused_step=$refused_step"'
        in script
    )
    assert '"$GITHUB_STEP_SUMMARY" || true' in script
    assert script.rstrip().endswith("exit 0")


def test_control_compares_merge_base_contract_and_exempts_carried_evidence() -> None:
    script = _step(BASE_STEP)["run"]
    assert 'show "$MB:contracts/$ticket.yaml"' in script
    assert '"$RUNNER_TEMP/dod/base-$ticket.carried.json"' in script
    assert (
        "carried unchanged from the merge base's contract, not re-controlled" in script
    )
    assert "binds no evidence of its own" in script


_CONTROL_TOOLS_MISSING = any(
    shutil.which(tool) is None for tool in ("bash", "git", "jq")
)
_OLD_CONTRACT = "dod_evidence:\n  - id: old\n    binds_ac: [AC1]\n    check_value: X\n"
_NEW_CONTRACT = "dod_evidence:\n  - id: new\n    binds_ac: [AC2]\n"
_APPENDED_CONTRACT = _OLD_CONTRACT + "  - id: new\n    binds_ac: [AC2]\n"


def _run_base_control(
    tmp_path: Path,
    base_contract: str | None,
    head_contract: str,
    checks: list[dict[str, object]],
) -> tuple[subprocess.CompletedProcess[str], Path]:
    workspace = tmp_path / "ws"
    head_tree = workspace / ".dod-verify" / "head_home" / "omnimarket"
    base_tree = workspace / ".dod-verify" / "base_home" / "omnimarket"
    contract = head_tree / "contracts" / "OMN-1.yaml"
    contract.parent.mkdir(parents=True)
    base_tree.parent.mkdir(parents=True)

    # A full replacement env: nothing inherited, so a hook's GIT_DIR cannot retarget git.
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
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(head_tree), *args],
            env=scrub_git_location_env(env),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init")
    if base_contract is not None:
        contract.write_text(base_contract)
        git("add", "contracts/OMN-1.yaml")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-m",
        "merge base",
    )
    merge_base = git("rev-parse", "HEAD")
    contract.write_text(head_contract)
    git("add", "contracts/OMN-1.yaml")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-m",
        "head",
    )
    git("worktree", "add", "--detach", str(base_tree), merge_base)
    (base_tree / "contracts").mkdir(exist_ok=True)
    shutil.copyfile(contract, base_tree / "contracts" / "OMN-1.yaml")

    dod_dir = tmp_path / "rt" / "dod"
    dod_dir.mkdir(parents=True)
    (dod_dir / "tickets.txt").write_text("OMN-1\n")
    (dod_dir / "merge-base.txt").write_text(merge_base + "\n")
    (dod_dir / "control-home-OMN-1.txt").write_text(
        str(workspace / ".dod-verify" / "base_home") + "\n"
    )
    (dod_dir / "control-label-OMN-1.txt").write_text("the merge base\n")
    verdict = tmp_path / "verdict.json"
    verdict.write_text(json.dumps({"status": "verified", "checks": checks}))
    verifier = tmp_path / "verifier"
    verifier.write_text(
        f"#!{sys.executable}\n"
        f"VERDICT = {str(verdict)!r}\n"
        + dedent("""\
            import os
            import sys
            from pathlib import Path

            if len(sys.argv) > 1 and sys.argv[1] == "-m":
                print(Path(VERDICT).read_text())
                sys.exit(0)
            os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
            """)
    )
    verifier.chmod(0o755)
    completed = subprocess.run(
        ["bash", "-c", _step(BASE_STEP)["run"]],
        env={
            **env,
            "GITHUB_WORKSPACE": str(workspace),
            "RUNNER_TEMP": str(dod_dir.parent),
            "REPO_SHORT": "omnimarket",
            "HEAD_SHA": git("rev-parse", "HEAD"),
            "DOD_VERIFY_PY": str(verifier),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return completed, dod_dir


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("base_contract", "head_contract", "statuses", "exit_code", "message", "carried"),
    [
        pytest.param(
            _OLD_CONTRACT,
            _APPENDED_CONTRACT,
            {"old": "verified", "new": "failed"},
            0,
            "OMN-1 base control: passed; every bound check failed [new]",
            ["old"],
            id="inherited-pass-new-failure",
        ),
        pytest.param(
            _OLD_CONTRACT,
            _APPENDED_CONTRACT,
            {"old": "verified", "new": "verified"},
            1,
            "::error::OMN-1 [new]: bound test also passes at the merge base",
            ["old"],
            id="new-evidence-always-passes",
        ),
        pytest.param(
            _OLD_CONTRACT,
            _OLD_CONTRACT,
            {"old": "verified"},
            1,
            "this pull request binds no evidence of its own",
            ["old"],
            id="all-bound-evidence-carried",
        ),
        pytest.param(
            _OLD_CONTRACT,
            _OLD_CONTRACT.replace("X", "Y"),
            {"old": "verified"},
            1,
            "::error::OMN-1 [old]: bound test also passes at the merge base",
            [],
            id="changed-evidence-not-carried",
        ),
        pytest.param(
            _OLD_CONTRACT,
            _OLD_CONTRACT + "  - id: old\n    binds_ac: [AC1]\n    check_value: Z\n",
            {"old": "verified"},
            1,
            "::error::OMN-1 [old]: bound test also passes at the merge base",
            [],
            id="repeated-inherited-id-not-carried",
        ),
        pytest.param(
            None,
            _NEW_CONTRACT,
            {"new": "failed"},
            0,
            "OMN-1 base control: passed; every bound check failed [new]",
            [],
            id="no-contract-at-merge-base",
        ),
    ],
)
def test_base_control_only_requires_own_evidence_to_fail(
    tmp_path: Path,
    base_contract: str | None,
    head_contract: str,
    statuses: dict[str, str],
    exit_code: int,
    message: str,
    carried: list[str],
) -> None:
    checks: list[dict[str, object]] = [
        {
            "evidence_id": evidence_id,
            "binds_ac": ["AC1" if evidence_id == "old" else "AC2"],
            "status": status,
        }
        for evidence_id, status in statuses.items()
    ]
    completed, dod_dir = _run_base_control(
        tmp_path, base_contract, head_contract, checks
    )
    assert completed.returncode == exit_code, completed.stdout + completed.stderr
    assert message in completed.stdout
    assert json.loads((dod_dir / "base-OMN-1.carried.json").read_text()) == carried
    control = (dod_dir / "base-OMN-1.control.txt").read_text().splitlines()[0]
    assert control == (
        "passed: every bound check failed" if exit_code == 0 else "refused"
    )
    if carried:
        assert (
            "OMN-1: carried unchanged from the merge base's contract, not re-controlled [old]"
            in completed.stdout
        )
    else:
        assert "not re-controlled" not in completed.stdout
    errors = "\n".join(
        line for line in completed.stdout.splitlines() if line.startswith("::error::")
    )
    if "new" in statuses and statuses["new"] == "verified":
        assert "always-pass" in errors
        assert "old" not in errors


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("base_contract", "head_contract"),
    [(_OLD_CONTRACT, "dod_evidence: ["), ("dod_evidence: [", _OLD_CONTRACT)],
    ids=["invalid-head-yaml", "invalid-base-yaml"],
)
def test_base_control_fails_closed_when_contract_comparison_fails(
    tmp_path: Path, base_contract: str, head_contract: str
) -> None:
    completed, dod_dir = _run_base_control(tmp_path, base_contract, head_contract, [])
    assert completed.returncode == 1
    assert (
        "::error::OMN-1: cannot compare the contract with the merge base's; carried evidence unavailable"
        in completed.stdout
    )
    assert (dod_dir / "base-OMN-1.control.txt").read_text() == "refused\n"
    assert not (dod_dir / "base-OMN-1.json").exists()


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
def test_base_control_preserves_zero_bound_checks_refusal(tmp_path: Path) -> None:
    completed, dod_dir = _run_base_control(
        tmp_path,
        _OLD_CONTRACT,
        _OLD_CONTRACT,
        [{"evidence_id": "old", "binds_ac": [], "status": "verified"}],
    )
    assert completed.returncode == 1
    assert (
        "::error::OMN-1: zero bound checks (evidence ids: none); nothing is bound, so nothing can fail"
        in completed.stdout
    )
    assert "binds no evidence of its own" not in completed.stdout
    assert (dod_dir / "base-OMN-1.control.txt").read_text() == "refused\n"


# OMN-20543: a bound test that needs a database gets the same one at the head and
# in the must-fail control, the way the caller's own test job provides it.
def test_dod_verify_job_provides_the_callers_postgres_service() -> None:
    service = _job()["services"]["postgres"]
    assert service["image"] == "postgres:16-alpine"
    assert set(service["env"]) == {"POSTGRES_PASSWORD", "POSTGRES_DB"}
    assert service["env"]["POSTGRES_PASSWORD"]
    assert service["env"]["POSTGRES_DB"] == "omnibase_infra"
    assert service["ports"] == ["5432/tcp"]
    assert "--health-cmd pg_isready" in service["options"]
    # The verify (OCC) job is untouched.
    assert "services" not in _workflow()["jobs"]["verify"]


def test_postgres_steps_are_gated_and_fail_closed_before_any_verdict() -> None:
    names = [step.get("name") for step in _job()["steps"]]
    assert names.index(PG_TOOLS_STEP) < names.index(PG_ENV_STEP)
    assert names.index(PG_ENV_STEP) < names.index(HEAD_STEP)
    for name in (PG_TOOLS_STEP, PG_ENV_STEP):
        # OMN-20073: a refused fork or ticket stops the steps that follow it.
        assert _step(name)["if"] == (
            "steps.bot_exempt.outputs.exempt != 'true' "
            "&& steps.same_repo.outcome != 'failure' "
            "&& steps.tickets.outcome != 'failure' "
            "&& steps.writer_pin_only.outputs.exempt != 'true'"
        )
        assert "set -euo pipefail" in _step(name)["run"]
    tools = _step(PG_TOOLS_STEP)["run"]
    assert "pg16_bin=/usr/lib/postgresql/16/bin" in tools
    assert 'test -x "${pg16_bin}/${tool}"' in tools
    assert "for tool in initdb pg_ctl psql; do" in tools
    assert "PostgreSQL\\) 16\\." in tools
    assert 'echo "${pg16_bin}" >> "$GITHUB_PATH"' in tools
    # A runner that cannot install the tools refuses by name, never continues.
    assert "cannot be installed (no sudo apt-get)" in tools
    assert "sudo -n apt-get install --yes postgresql-16" in tools
    export = _step(PG_ENV_STEP)
    assert export["env"] == {
        "POSTGRES_PORT": "${{ job.services.postgres.ports['5432'] }}"
    }
    assert '>> "$GITHUB_ENV"' in export["run"]


def _service_password() -> str:
    password = _job()["services"]["postgres"]["env"]["POSTGRES_PASSWORD"]
    assert isinstance(password, str)
    return password


def _export_path() -> str:
    tool_dirs = {
        str(Path(found).parent)
        for found in (shutil.which(tool) for tool in ("bash", "python3"))
        if found
    }
    return os.pathsep.join([*sorted(tool_dirs), "/usr/bin", "/bin"])


def _listening_port() -> tuple[Any, int]:
    import socket

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    return listener, listener.getsockname()[1]


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required")
def test_postgres_export_writes_the_integration_env_for_a_reachable_service(
    tmp_path: Path,
) -> None:
    listener, port = _listening_port()
    github_env = tmp_path / "github_env"
    try:
        completed = subprocess.run(
            ["bash", "-c", _step(PG_ENV_STEP)["run"]],
            env={
                "PATH": _export_path(),
                "POSTGRES_PORT": str(port),
                "GITHUB_ENV": str(github_env),
            },
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        listener.close()
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert github_env.read_text().splitlines() == [
        "INTEGRATION_POSTGRES_HOST=127.0.0.1",
        f"INTEGRATION_POSTGRES_PORT={port}",
        "INTEGRATION_POSTGRES_USER=postgres",
        f"INTEGRATION_POSTGRES_PASSWORD={_service_password()}",
        "INTEGRATION_POSTGRES_DB=omnibase_infra",
        f"POSTGRES_PASSWORD={_service_password()}",
    ]


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required")
def test_postgres_export_fails_when_the_service_is_unreachable(
    tmp_path: Path,
) -> None:
    listener, port = _listening_port()
    listener.close()
    github_env = tmp_path / "github_env"
    completed = subprocess.run(
        ["bash", "-c", _step(PG_ENV_STEP)["run"]],
        env={
            "PATH": _export_path(),
            "POSTGRES_PORT": str(port),
            "GITHUB_ENV": str(github_env),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "could not reach the Postgres service" in completed.stderr
    assert not github_env.exists()


_SCOPED_MESSAGE = (
    "NOT_EVALUATED [local_done_gate] -- hosted node_dod_verify is not an "
    "authorized consumer; the local Done gate must execute this item and "
    "persist its result."
)


@pytest.mark.skipif(_CONTROL_TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    ("message", "names_scope"),
    [
        pytest.param(_SCOPED_MESSAGE, True, id="local-done-gate-scope"),
        pytest.param("SKIPPED: environment unavailable", False, id="other-skip"),
    ],
)
def test_base_control_still_refuses_a_bound_check_that_did_not_run(
    tmp_path: Path, message: str, names_scope: bool
) -> None:
    completed, dod_dir = _run_base_control(
        tmp_path,
        _OLD_CONTRACT,
        _APPENDED_CONTRACT,
        [
            {"evidence_id": "old", "binds_ac": ["AC1"], "status": "verified"},
            {
                "evidence_id": "new",
                "binds_ac": ["AC2"],
                "status": "skipped",
                "message": message,
            },
        ],
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert (
        "::error::OMN-1 [new]: the control could not run, a control that did not run is not a pass"
        in completed.stdout
    )
    scoped = (
        "::error::OMN-1 [new]: scoped local_done_gate, which this hosted check "
        "runs neither at the head nor at the merge base"
    )
    assert (scoped in completed.stdout) is names_scope
    assert (dod_dir / "base-OMN-1.control.txt").read_text() == "refused\n"
