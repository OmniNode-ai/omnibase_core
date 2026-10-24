# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Execute the reusable's sibling provisioning step without network access."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/receipt-gate.yml"
SHA = "a" * 40
OTHER_SHA = "b" * 40


def _job():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["dod-verify"]


def _step():
    steps = [s for s in _job()["steps"] if s.get("id") == "sibling_checkouts"]
    assert len(steps) == 1, "declared siblings must be provisioned by the reusable"
    return steps[0]


def _run(
    tmp_path, *, cwds=None, uv_pin=None, actions=None, workflows=None, unavailable=False
):
    home = tmp_path / "ws/.dod-verify/head_home"
    caller = home / "caller"
    (caller / "contracts").mkdir(parents=True)
    (caller / "contracts/OMN-1.yaml").write_text(
        yaml.safe_dump(
            {
                "dod_evidence": [
                    {
                        "checks": [
                            {"cwd": cwd}
                            for cwd in (
                                cwds
                                if cwds is not None
                                else ["${OMNI_HOME}/sibling/subdir"]
                            )
                        ]
                    }
                ]
            }
        )
    )
    if uv_pin:
        (caller / "pyproject.toml").write_text(uv_pin)
    for folder, documents in (("actions", actions), ("workflows", workflows)):
        for name, doc in (documents or {}).items():
            path = caller / ".github" / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(doc))
    dod = tmp_path / "rt/dod"
    dod.mkdir(parents=True)
    (dod / "tickets.txt").write_text("OMN-1\n")
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if "ls-remote" in argv:
            if unavailable:
                raise subprocess.CalledProcessError(128, argv)
            return subprocess.CompletedProcess(argv, 0, f"{SHA}\tHEAD\n")
        return subprocess.CompletedProcess(argv, 0, "")

    script = _step()["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    env = {
        "GITHUB_WORKSPACE": str(tmp_path / "ws"),
        "RUNNER_TEMP": str(tmp_path / "rt"),
        "REPO_SHORT": "caller",
        "GH_TOKEN": "test-token",
    }
    script_path = tmp_path / "provision.py"
    script_path.write_text(script)
    with patch.dict("os.environ", env), patch("subprocess.run", side_effect=run):
        try:
            runpy.run_path(str(script_path), run_name="__main__")
        except SystemExit as outcome:
            assert outcome.code == 0
    return home, dod, calls


def test_provisions_declared_sibling_at_uv_pin(tmp_path):
    home, dod, calls = _run(
        tmp_path,
        uv_pin=f'[tool.uv.sources]\nsibling = {{git = "https://github.com/OmniNode-ai/sibling.git", rev = "{SHA}"}}\n',
    )
    assert (home / "sibling").is_dir()
    assert (dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    assert any("fetch" in argv and SHA in argv for argv, _ in calls)
    assert not any("ls-remote" in argv for argv, _ in calls)


def test_ignores_callers_own_repository_and_nonregistry_cwds(tmp_path):
    home, dod, calls = _run(
        tmp_path,
        cwds=["${OMNI_HOME}/caller", ".", "/tmp/sibling", "${OMNI_HOME}/../escape"],
        uv_pin="not valid TOML",
    )
    assert not calls
    assert (dod / "siblings.tsv").read_text() == ""
    assert (home / "caller/contracts/OMN-1.yaml").is_file()


def test_freezes_unpinned_revision_once_for_head_and_controls(tmp_path):
    home, dod, calls = _run(
        tmp_path, cwds=["${OMNI_HOME}/sibling", "${OMNI_HOME}/sibling/tests"]
    )
    assert sum("ls-remote" in argv for argv, _ in calls) == 1
    assert (dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    prepare = next(s["run"] for s in _job()["steps"] if s.get("id") == "merge_base")
    assert '"$RUNNER_TEMP/dod/siblings.tsv"' in prepare
    assert '"$control_home/$sibling" "$sibling_sha"' in prepare
    assert "ls-remote" not in prepare
    assert _job()["steps"].index(_step()) < next(
        i for i, s in enumerate(_job()["steps"]) if s.get("id") == "head_verify"
    )
    # Exercise the actual control loop on a real git history whose head moves.
    sibling = home / "sibling"
    env = {
        "PATH": os.defpath,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(sibling), *args],
            env={
                "PATH": os.defpath,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            },
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init")
    (sibling / "revision").write_text("frozen")
    git("add", "revision")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "frozen",
    )
    frozen = git("rev-parse", "HEAD")
    (dod / "siblings.tsv").write_text(f"sibling\t{frozen}\n")
    (sibling / "revision").write_text("moved")
    git("add", "revision")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "moved",
    )
    loop = prepare.split("# OMN-21013: reuse", 1)[1].split("local path test_side", 1)[0]
    loop = "# OMN-21013: reuse" + loop
    for name in ("base_home", "fix_reverted_home/OMN-1"):
        control_home = home.parent / name
        control_home.mkdir(parents=True)
        completed = subprocess.run(
            ["bash", "-c", loop],
            env={
                **env,
                "control_home": str(control_home),
                "GITHUB_WORKSPACE": str(home.parents[1]),
                "RUNNER_TEMP": str(dod.parent),
            },
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert (control_home / "sibling/revision").read_text() == "frozen"


def test_conflicting_pins_leave_sibling_absent(tmp_path):
    _, dod, calls = _run(
        tmp_path,
        workflows={
            "ci.yml": {
                "jobs": {
                    "test": {
                        "steps": [
                            {
                                "uses": f"OmniNode-ai/sibling/.github/actions/check@{SHA}"
                            },
                            {
                                "uses": f"OmniNode-ai/sibling/.github/actions/other@{OTHER_SHA}"
                            },
                        ]
                    }
                }
            }
        },
    )
    assert not calls
    assert (dod / "siblings.tsv").read_text() == ""


def test_read_only_permissions_and_ephemeral_default_token(tmp_path):
    _, _, calls = _run(tmp_path)
    assert _job()["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert _step()["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert _step()["continue-on-error"] == "${{ inputs.shadow == 'true' }}"
    assert "secrets." not in json.dumps(_step())
    for argv, kwargs in calls:
        assert "test-token" not in " ".join(argv)
        assert "config" not in argv, "credentials must never be persisted"
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    checkout = next(s for s in _job()["steps"] if s.get("id") == "head_checkout")
    assert checkout["with"]["persist-credentials"] is False


@pytest.mark.parametrize("source", ["action", "checkout"])
def test_action_pin_then_explicit_checkout_ref(tmp_path, source):
    step = (
        {"uses": f"OmniNode-ai/sibling/.github/actions/check@{SHA}"}
        if source == "action"
        else {
            "uses": "actions/checkout@v7",
            "with": {"repository": "OmniNode-ai/sibling", "ref": SHA},
        }
    )
    _, dod, calls = _run(
        tmp_path,
        actions={
            "verify/action.yaml": {"runs": {"using": "composite", "steps": [step]}}
        },
    )
    assert (dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    assert not any("ls-remote" in argv for argv, _ in calls)


def test_uv_precedes_action_and_action_precedes_checkout(tmp_path):
    _, dod, calls = _run(
        tmp_path,
        uv_pin=f'[tool.uv.sources]\nsibling = {{git = "https://github.com/OmniNode-ai/sibling.git", rev = "{SHA}"}}\n',
        workflows={
            "ci.yaml": {
                "jobs": {
                    "test": {
                        "steps": [
                            {
                                "uses": f"OmniNode-ai/sibling/.github/actions/check@{OTHER_SHA}"
                            },
                            {
                                "uses": "actions/checkout@v7",
                                "with": {
                                    "repository": "OmniNode-ai/sibling",
                                    "ref": "dev",
                                },
                            },
                        ]
                    }
                }
            }
        },
    )
    assert (dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    assert not any("ls-remote" in argv for argv, _ in calls)


def test_reusable_workflow_pins_do_not_conflict_with_composite_action(tmp_path):
    _, dod, calls = _run(
        tmp_path,
        workflows={
            "ci.yml": {
                "jobs": {
                    "receipts": {
                        "uses": f"OmniNode-ai/sibling/.github/workflows/receipt-gate.yml@{OTHER_SHA}"
                    },
                    "test": {
                        "steps": [
                            {
                                "uses": f"OmniNode-ai/sibling/.github/actions/check@{SHA}"
                            },
                            {
                                "uses": "actions/checkout@v7",
                                "with": {
                                    "repository": "OmniNode-ai/sibling",
                                    "ref": "dev",
                                },
                            },
                        ]
                    },
                }
            }
        },
    )
    assert (dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    assert not any("ls-remote" in argv for argv, _ in calls)


@pytest.mark.parametrize("bad_metadata", [False, True])
def test_unresolvable_sibling_is_absent_for_verifier_refusal(tmp_path, bad_metadata):
    home, dod, _ = _run(
        tmp_path,
        unavailable=True,
        uv_pin="not valid TOML" if bad_metadata else None,
    )
    assert not (home / "sibling").exists()
    assert (dod / "siblings.tsv").read_text() == ""


# OMN-21166: a checkout ref written as a step output (``${{ ... }}``) is not a
# revision. omnidash pins omnibase_core once, as a literal in
# check-handshake.yml, and two other workflows check out the same commit through
# ``${{ steps.core-pin.outputs.ref }}``, a step that reads that literal. The
# fixtures are those three files as they are on omnidash dev 3713a036, with
# their commit ids replaced by low-entropy placeholders of the same length,
# because the secret scanner reads a real commit id as a hex secret.
OMNIDASH_WORKFLOWS = Path(__file__).parent / "fixtures/omn21166_omnidash_workflows"
OMNIDASH_CORE_PIN = "c" * 40
STEP_OUTPUT_REF = "${{ steps.core-pin.outputs.ref }}"


def _checkout(repository, ref):
    return {
        "uses": "actions/checkout@v7",
        "with": {"repository": repository, "ref": ref},
    }


def _workflow(*steps):
    return {"jobs": {"test": {"steps": list(steps)}}}


def test_omnidash_step_output_core_pin_resolves_to_the_handshake_literal(tmp_path):
    workflows = {
        path.name: yaml.safe_load(path.read_text())
        for path in sorted(OMNIDASH_WORKFLOWS.glob("*.yml"))
    }
    assert sorted(workflows) == [
        "check-handshake.yml",
        "onex-schema-compat.yml",
        "type-sync-check.yml",
    ]
    _, dod, calls = _run(
        tmp_path, cwds=["${OMNI_HOME}/omnibase_core"], workflows=workflows
    )
    assert (dod / "siblings.tsv").read_text() == f"omnibase_core\t{OMNIDASH_CORE_PIN}\n"
    assert any("fetch" in argv and OMNIDASH_CORE_PIN in argv for argv, _ in calls)
    assert not any("ls-remote" in argv for argv, _ in calls)


def test_two_literal_checkout_refs_still_conflict(tmp_path):
    _, dod, calls = _run(
        tmp_path,
        workflows={
            "a.yml": _workflow(_checkout("OmniNode-ai/sibling", SHA)),
            "b.yml": _workflow(
                _checkout("OmniNode-ai/sibling", OTHER_SHA),
                _checkout("OmniNode-ai/sibling", STEP_OUTPUT_REF),
            ),
        },
    )
    assert not calls
    assert (dod / "siblings.tsv").read_text() == ""


def test_step_output_ref_alone_is_unresolved_never_head(tmp_path):
    home, dod, calls = _run(
        tmp_path,
        workflows={
            "a.yml": _workflow(_checkout("OmniNode-ai/sibling", STEP_OUTPUT_REF))
        },
    )
    assert not calls, "an unreadable ref must not fall back to the sibling's HEAD"
    assert not (home / "sibling").exists()
    assert (dod / "siblings.tsv").read_text() == ""


def test_uv_pin_still_wins_over_literal_and_step_output_checkout_refs(tmp_path):
    _, dod, calls = _run(
        tmp_path,
        uv_pin=f'[tool.uv.sources]\nsibling = {{git = "https://github.com/OmniNode-ai/sibling.git", rev = "{SHA}"}}\n',
        workflows={
            "a.yml": _workflow(
                _checkout("OmniNode-ai/sibling", OTHER_SHA),
                _checkout("OmniNode-ai/sibling", STEP_OUTPUT_REF),
            )
        },
    )
    assert (dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    assert not any("ls-remote" in argv for argv, _ in calls)
