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
    tmp_path,
    *,
    cwds=None,
    uv_pin=None,
    actions=None,
    workflows=None,
    unavailable=False,
    sibling_pins=None,
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
    if sibling_pins is not None:
        (caller / ".github").mkdir(parents=True, exist_ok=True)
        if callable(sibling_pins):
            sibling_pins(caller / ".github/sibling-pins.yaml")
        else:
            (caller / ".github/sibling-pins.yaml").write_text(sibling_pins)
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


# OMN-21166 part 31 (option B, Jonah 2026-10-25): a caller may declare a sibling's revision in
# .github/sibling-pins.yaml. A declared pin is the revision; every literal pin must agree with it;
# expression refs (a step output the resolver cannot read) are set aside only when a pin is declared.
OMNIDASH_CORE = "c" * 40
_CHECKOUT = "actions/checkout@" + "d" * 40
_STEP_OUTPUT_REF = "$" + "{{ steps.core-pin.outputs.ref }}"


def _omnidash_workflows():
    """Every checkout and core-pin step of omnidash's three omnibase_core workflows at omnidash
    dev 03a5f605, copied field for field; the resolver reads nothing else from them. The commit
    shas are stand-ins: the resolver compares pins, it does not read what they name."""
    core_by_step_output = {
        "persist-credentials": False,
        "repository": "OmniNode-ai/omnibase_core",
        "ref": _STEP_OUTPUT_REF,
        "path": "omnibase_core",
    }
    return {
        "check-handshake.yml": {
            "jobs": {
                "check-handshake": {
                    "steps": [
                        {"name": "Checkout repo", "uses": "actions/checkout@v4"},
                        {
                            "name": "Checkout omnibase_core",
                            "uses": "actions/checkout@v4",
                            "with": {
                                "repository": "OmniNode-ai/omnibase_core",
                                "ref": OMNIDASH_CORE,
                                "path": "omnibase_core",
                            },
                        },
                    ]
                }
            }
        },
        "type-sync-check.yml": {
            "jobs": {
                "type-sync-check": {
                    "steps": [
                        {
                            "name": "Checkout omnidash (shallow, for path detection)",
                            "uses": _CHECKOUT,
                            "with": {"persist-credentials": False, "fetch-depth": 0},
                        },
                        {
                            "name": "Resolve the handshake's omnibase_core pin",
                            "id": "core-pin",
                            "run": "true",
                        },
                        {
                            "name": "Checkout omnibase_core",
                            "if": "steps.changes.outputs.run_check == 'true'",
                            "uses": _CHECKOUT,
                            "with": core_by_step_output,
                        },
                        {
                            "name": "Checkout omniintelligence",
                            "if": "steps.changes.outputs.run_check == 'true'",
                            "uses": _CHECKOUT,
                            "with": {
                                "persist-credentials": False,
                                "repository": "OmniNode-ai/omniintelligence",
                                "ref": "e" * 40,
                                "path": "omniintelligence",
                            },
                        },
                    ]
                }
            }
        },
        "onex-schema-compat.yml": {
            "jobs": {
                "schema-compat": {
                    "steps": [
                        {
                            "name": "Checkout repo",
                            "uses": _CHECKOUT,
                            "with": {"persist-credentials": False},
                        },
                        {
                            "name": "Resolve the handshake's omnibase_core pin",
                            "id": "core-pin",
                            "run": "true",
                        },
                        {
                            "name": "Checkout omnibase_core",
                            "uses": _CHECKOUT,
                            "with": core_by_step_output,
                        },
                    ]
                }
            }
        },
    }


def _core(tmp_path, **kwargs):
    return _run(
        tmp_path,
        cwds=["${OMNI_HOME}/omnibase_core/tests"],
        workflows=_omnidash_workflows(),
        **kwargs,
    )


def test_omnidash_workflows_without_a_declared_pin_still_conflict(tmp_path):
    """Control: today's behaviour for omnidash's three workflows (a literal and two step outputs)."""
    home, dod, calls = _core(tmp_path)
    assert not (home / "omnibase_core").exists()
    assert (dod / "siblings.tsv").read_text() == ""
    assert not calls


def test_declared_pin_resolves_omnidash_workflows(tmp_path):
    home, dod, calls = _core(
        tmp_path, sibling_pins=f"pins:\n  omnibase_core: {OMNIDASH_CORE}\n"
    )
    assert (home / "omnibase_core").is_dir()
    assert (dod / "siblings.tsv").read_text() == f"omnibase_core\t{OMNIDASH_CORE}\n"
    assert any("fetch" in argv and OMNIDASH_CORE in argv for argv, _ in calls)
    assert not any("ls-remote" in argv for argv, _ in calls)


def test_declared_pin_that_disagrees_with_a_literal_is_a_conflict(tmp_path):
    home, dod, calls = _core(
        tmp_path, sibling_pins=f"pins:\n  omnibase_core: {OTHER_SHA}\n"
    )
    assert not (home / "omnibase_core").exists()
    assert (dod / "siblings.tsv").read_text() == ""
    assert not calls


@pytest.mark.parametrize(
    "pins",
    [
        "pins: [",  # not YAML
        "pins:\n  omnibase_core: dev\n",  # a branch name, not a commit
        f"pins:\n  omnibase_core: {OMNIDASH_CORE[:12]}\n",  # short sha
        f"omnibase_core: {OMNIDASH_CORE}\n",  # no pins mapping
        "pins:\n  omnibase_core:\n",  # empty value
    ],
)
def test_malformed_declared_pin_leaves_sibling_absent(tmp_path, pins):
    home, dod, calls = _core(tmp_path, sibling_pins=pins)
    assert not (home / "omnibase_core").exists()
    assert (dod / "siblings.tsv").read_text() == ""
    assert not any("ls-remote" in argv or "fetch" in argv for argv, _ in calls)


def test_pin_declared_for_another_sibling_changes_nothing(tmp_path):
    home, dod, calls = _core(
        tmp_path, sibling_pins=f"pins:\n  omniintelligence: {OTHER_SHA}\n"
    )
    assert not (home / "omnibase_core").exists()
    assert (dod / "siblings.tsv").read_text() == ""
    assert not calls


def test_declared_pin_also_binds_uv_pins(tmp_path):
    home, dod, _ = _run(
        tmp_path,
        uv_pin=f'[tool.uv.sources]\nsibling = {{git = "https://github.com/OmniNode-ai/sibling.git", rev = "{OTHER_SHA}"}}\n',
        sibling_pins=f"pins:\n  sibling: {SHA}\n",
    )
    assert not (home / "sibling").exists()
    assert (dod / "siblings.tsv").read_text() == ""


@pytest.mark.parametrize(
    "pins",
    [
        "pins: [",
        "pins:\n  sibling: dev\n",
        f"pins:\n  sibling: {SHA[:12]}\n",
        f"sibling: {SHA}\n",
        f"pins:\n  sibling: {OTHER_SHA}\n  sibling: {SHA}\n",  # duplicate key: PyYAML keeps the last
        f"pins:\n  sibling: {OTHER_SHA}\npins:\n  sibling: {SHA}\n",  # duplicate pins mapping
    ],
)
def test_malformed_declared_pin_withholds_an_otherwise_resolved_sibling(tmp_path, pins):
    """AC210: a bad pin file never falls back, even where the uv pin alone would resolve."""
    home, dod, calls = _run(
        tmp_path,
        uv_pin=f'[tool.uv.sources]\nsibling = {{git = "https://github.com/OmniNode-ai/sibling.git", rev = "{SHA}"}}\n',
        sibling_pins=pins,
    )
    assert not (home / "sibling").exists()
    assert (dod / "siblings.tsv").read_text() == ""
    assert not any("fetch" in argv for argv, _ in calls)


def _dangling_symlink(path):
    path.symlink_to(path.parent / "missing-pins.yaml")


def _directory(path):
    path.mkdir()
    (path / "pins.yaml").write_text(f"pins:\n  sibling: {SHA}\n")


@pytest.mark.parametrize(
    "make_path", [_dangling_symlink, _directory], ids=["dangling-symlink", "directory"]
)
def test_malformed_declared_pin_withholds_an_otherwise_resolved_sibling_path(
    tmp_path, make_path
):
    """AC210: a pin path that exists but is not a readable regular file is unreadable, not absent;
    the uv pin that alone would resolve (the control below) must not be fetched."""
    uv_pin = f'[tool.uv.sources]\nsibling = {{git = "https://github.com/OmniNode-ai/sibling.git", rev = "{SHA}"}}\n'
    _, control_dod, _ = _run(tmp_path / "control", uv_pin=uv_pin)
    assert (control_dod / "siblings.tsv").read_text() == f"sibling\t{SHA}\n"
    home, dod, calls = _run(tmp_path / "case", uv_pin=uv_pin, sibling_pins=make_path)
    assert not (home / "sibling").exists()
    assert (dod / "siblings.tsv").read_text() == ""
    assert not any("fetch" in argv for argv, _ in calls)


@pytest.mark.parametrize(
    ("source", "resolves"),
    [
        (
            f'{{git = "ssh://git@github.com/OmniNode-ai/sibling", rev = "{OTHER_SHA}"}}',
            False,
        ),
        (
            f'{{git = "git@github.com:OmniNode-ai/sibling.git", rev = "{OTHER_SHA}"}}',
            False,
        ),
        (
            f'{{git = "https://github.com/omninode-ai/Sibling.git", rev = "{OTHER_SHA}"}}',
            False,
        ),
        (
            '{git = "https://github.com/OmniNode-ai/sibling.git", branch = "main"}',
            False,
        ),
        ('{git = "https://github.com/OmniNode-ai/sibling.git"}', False),
        (
            f'{{git = "https://mirror.example/OmniNode-ai/sibling.git", rev = "{OTHER_SHA}"}}',
            False,
        ),
        (
            f'{{git = "https://github.com/someone/sibling.git", rev = "{OTHER_SHA}"}}',
            False,
        ),
        (f'{{git = "ssh://git@github.com/OmniNode-ai/sibling", rev = "{SHA}"}}', True),
    ],
    ids=[
        "ssh-other",
        "scp-other",
        "case-other",
        "branch-only",
        "unpinned",
        "lookalike-host",
        "fork-other",
        "ssh-same",
    ],
)
def test_declared_pin_also_binds_uv_pins_in_every_url_form(tmp_path, source, resolves):
    """AC209: every uv source uv itself would fetch for the sibling is a literal the declared pin
    must equal; a form the resolver cannot read leaves the checkout absent."""
    home, dod, _ = _run(
        tmp_path,
        uv_pin=f"[tool.uv.sources]\nsibling = {source}\n",
        sibling_pins=f"pins:\n  sibling: {SHA}\n",
    )
    assert (home / "sibling").is_dir() is resolves
    assert (dod / "siblings.tsv").read_text() == (
        f"sibling\t{SHA}\n" if resolves else ""
    )


@pytest.mark.parametrize(
    ("step", "resolves"),
    [
        (
            {
                "uses": "actions/checkout@v4",
                "with": {"repository": "omninode-ai/SIBLING", "ref": OTHER_SHA},
            },
            False,
        ),
        (
            {
                "uses": "Actions/Checkout@v4",
                "with": {"repository": "OmniNode-ai/sibling", "ref": OTHER_SHA},
            },
            False,
        ),
        (
            {
                "uses": "actions/checkout@v4",
                "with": {"repository": "OmniNode-ai/sibling"},
            },
            False,
        ),
        ({"uses": f"omninode-ai/Sibling/.github/actions/setup@{OTHER_SHA}"}, False),
        (
            {
                "uses": "actions/checkout@v4",
                "with": {"repository": "omninode-ai/SIBLING", "ref": SHA},
            },
            True,
        ),
    ],
    ids=[
        "repo-case-other",
        "checkout-case-other",
        "no-ref",
        "action-case-other",
        "repo-case-same",
    ],
)
def test_declared_pin_binds_every_checkout_and_action_form(tmp_path, step, resolves):
    """AC209: GitHub owner and repository names are case-insensitive, and a sibling checkout with
    no ref fetches the default branch, so beside a declared pin each is a literal it must equal."""
    home, dod, _ = _run(
        tmp_path,
        workflows={"ci.yml": {"jobs": {"build": {"steps": [step]}}}},
        sibling_pins=f"pins:\n  sibling: {SHA}\n",
    )
    assert (home / "sibling").is_dir() is resolves
    assert (dod / "siblings.tsv").read_text() == (
        f"sibling\t{SHA}\n" if resolves else ""
    )
