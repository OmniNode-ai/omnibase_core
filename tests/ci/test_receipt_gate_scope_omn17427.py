# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-17427: dod-verify verifies only what a pull request adds or changes.

An umbrella ticket contract carried 154 acceptance criteria, and every pull
request citing it ran every check at its head and again at its merge base, 28
to 40 minutes a run, so runs were cancelled at the job timeout. The scope step
writes the contract the verifier runs: the evidence items the pull request adds
or changes, the items whose checks name a path its diff touches, and the items
binding a criterion it adds or changes. The merge-base control runs the same
set without the diff-named items. A carried item passed on its earlier receipt.

These tests run the workflow's own step scripts against a real git history and
a stand-in verifier that records the contract it was handed.
"""

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
TICKET = "OMN-1"
REPO = "omnimarket"
SCOPE_STEP = "Scope each cited contract to what this pull request adds or changes"
TOOLS_MISSING = any(shutil.which(tool) is None for tool in ("bash", "git", "jq"))


def _steps() -> list[dict[str, Any]]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = data["jobs"]["dod-verify"]["steps"]
    assert isinstance(steps, list)
    return steps


def _step(step_id: str) -> dict[str, Any]:
    return next(step for step in _steps() if step.get("id") == step_id)


def _item(number: int, test_file: str = "tests/test_carried.py") -> dict[str, Any]:
    return {
        "id": f"dod-{number}",
        "description": f"criterion {number} holds",
        "source": "manual",
        "binds_ac": [f"AC{number}"],
        "checks": [
            {
                "check_type": "test_passes",
                "check_value": f"uv run pytest {test_file} -k case_{number} -q",
                "cwd": "${OMNI_HOME}/" + REPO,
            }
        ],
    }


def _criterion(number: int) -> dict[str, Any]:
    return {
        "id": f"req-{number}",
        "statement": f"requirement {number}",
        "acceptance": [
            {"id": f"AC{number}", "statement": f"AC{number}: criterion {number}"}
        ],
    }


def _contract(
    numbers: range, extra_items: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "title": "umbrella",
        "requirements": [_criterion(number) for number in numbers],
        "dod_evidence": [_item(number) for number in numbers] + (extra_items or []),
    }


def _with_new_criterion(contract: dict[str, Any], number: int) -> dict[str, Any]:
    changed = json.loads(json.dumps(contract))
    changed["requirements"].append(_criterion(number))
    changed["dod_evidence"].append(_item(number, "tests/test_new.py"))
    return changed


CARRIED = _contract(range(1, 151))


class _Gate:
    """One caller repository with a merge base and a head, and the job's state."""

    def __init__(
        self,
        tmp_path: Path,
        base: dict[str, Any] | str | None,
        head: dict[str, Any] | str,
        head_files: dict[str, str] | None = None,
    ) -> None:
        self.workspace = tmp_path / "ws"
        self.head_tree = self.workspace / ".dod-verify" / "head_home" / REPO
        self.head_tree.mkdir(parents=True)
        self.dod = tmp_path / "rt" / "dod"
        self.dod.mkdir(parents=True)
        (self.dod / "tickets.txt").write_text(TICKET + "\n")
        self.log = tmp_path / "verifier.log"
        tools = {
            str(Path(found).parent)
            for found in (shutil.which(tool) for tool in ("bash", "git", "jq"))
            if found
        }
        self.env = {
            "PATH": os.pathsep.join([*sorted(tools), "/usr/bin", "/bin"]),
            "HOME": str(tmp_path),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        contract = self.head_tree / "contracts" / f"{TICKET}.yaml"
        contract.parent.mkdir()
        (self.head_tree / "tests").mkdir()
        (self.head_tree / "tests" / "test_carried.py").write_text("# carried\n")
        self.git("init", "-q")
        if base is not None:
            contract.write_text(base if isinstance(base, str) else yaml.safe_dump(base))
        self.git("add", "-A")
        self.commit("merge base")
        self.base_sha = self.git("rev-parse", "HEAD")
        contract.write_text(head if isinstance(head, str) else yaml.safe_dump(head))
        # A product change beside the new test, so the control must fail.
        default_files = {"tests/test_new.py": "# new\n", "src/product.py": "# fix\n"}
        for path, text in (head_files or default_files).items():
            (self.head_tree / path).parent.mkdir(parents=True, exist_ok=True)
            (self.head_tree / path).write_text(text)
        self.git("add", "-A")
        self.commit("head")
        self.head_sha = self.git("rev-parse", "HEAD")
        self.verifier = tmp_path / "verifier"
        self.verifier.write_text(
            f"#!{sys.executable}\n"
            f"LOG = {str(self.log)!r}\n"
            + dedent("""\
                import json
                import os
                import sys

                if len(sys.argv) < 2 or sys.argv[1] != "-m":
                    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
                import yaml

                args = sys.argv[1:]
                path = args[args.index("--contract-path") + 1]
                contract = yaml.safe_load(open(path))
                items = contract["dod_evidence"]
                criteria = [
                    criterion["id"]
                    for requirement in contract.get("requirements", [])
                    for criterion in requirement["acceptance"]
                ]
                at_head = "/head_home/" in os.getcwd() + "/"
                with open(LOG, "a") as log:
                    log.write(json.dumps({
                        "at": "head" if at_head else "base",
                        "items": [item["id"] for item in items],
                        "criteria": criteria,
                    }) + "\\n")
                status = "verified" if at_head else "failed"
                print(json.dumps({
                    "status": status,
                    "checks": [
                        {"evidence_id": item["id"], "binds_ac": item.get("binds_ac", []),
                         "status": status}
                        for item in items
                    ],
                }, indent=2))
                print("Receipt written to: " + args[args.index("--output-path") + 1])
                sys.exit(0 if at_head else 1)
                """)
        )
        self.verifier.chmod(0o755)

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.head_tree), *args],
            env=scrub_git_location_env(self.env),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            message,
        )

    def run(self, step_id: str) -> subprocess.CompletedProcess[str]:
        script = _step(step_id)["run"]
        assert "${{" not in script
        return subprocess.run(
            ["bash", "-c", script],
            env={
                **self.env,
                "GITHUB_WORKSPACE": str(self.workspace),
                "RUNNER_TEMP": str(self.dod.parent),
                "REPO_SHORT": REPO,
                "BASE_SHA": self.base_sha,
                "HEAD_SHA": self.head_sha,
                "DOD_VERIFY_PY": str(self.verifier),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    def scoped(self, side: str) -> dict[str, Any]:
        loaded = yaml.safe_load(
            (self.dod / "scope" / f"{side}-{TICKET}.yaml").read_text()
        )
        assert isinstance(loaded, dict)
        return loaded

    def calls(self) -> list[dict[str, Any]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]


def _ids(contract: dict[str, Any]) -> list[str]:
    return [item["id"] for item in contract["dod_evidence"]]


def _criteria(contract: dict[str, Any]) -> list[str]:
    return [
        criterion["id"]
        for requirement in contract.get("requirements", [])
        for criterion in requirement["acceptance"]
    ]


def test_scope_step_sits_between_the_sibling_checkouts_and_the_head_run() -> None:
    ids = [step.get("id") for step in _steps()]
    assert ids[ids.index("scope") - 1 : ids.index("scope") + 2] == [
        "sibling_checkouts",
        "scope",
        "head_verify",
    ]
    step = _step("scope")
    assert step["name"] == SCOPE_STEP
    assert step["if"] == _step("head_verify")["if"]
    assert step["continue-on-error"] == "${{ inputs.shadow == 'true' }}"
    assert step["env"] == {
        "REPO_SHORT": "${{ github.event.repository.name }}",
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
    }
    assert '--contract-path "$scoped"' in _step("head_verify")["run"]
    assert '--contract-path "$scoped"' in _step("base_control")["run"]
    assert '"$RUNNER_TEMP/dod/scope/head-$ticket.yaml"' in _step("head_verify")["run"]
    assert '"$RUNNER_TEMP/dod/scope/base-$ticket.yaml"' in _step("base_control")["run"]
    summary = next(step for step in _steps() if step["name"] == "Summarise")["run"]
    assert "sibling_checkouts scope head_verify" in summary


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_150_carried_criteria_and_one_new_verify_one_at_head_and_one_at_base(
    tmp_path: Path,
) -> None:
    gate = _Gate(tmp_path, CARRIED, _with_new_criterion(CARRIED, 151))

    scope = gate.run("scope")
    assert scope.returncode == 0, scope.stdout + scope.stderr
    assert (
        f"{TICKET}: the head verifies 1 of 151 evidence items and 1 of 151 criteria; "
        "the merge-base control runs 1; 150 carried unchanged pass by their earlier receipt"
    ) in scope.stdout
    for side in ("head", "base"):
        assert _ids(gate.scoped(side)) == ["dod-151"]
        assert _criteria(gate.scoped(side)) == ["AC151"]
        assert gate.scoped(side)["ticket_id"] == TICKET

    head = gate.run("head_verify")
    assert head.returncode == 0, head.stdout + head.stderr
    assert f"{TICKET} head: verified" in head.stdout
    prepare = gate.run("merge_base")
    assert prepare.returncode == 0, prepare.stdout + prepare.stderr
    control = gate.run("base_control")
    assert control.returncode == 0, control.stdout + control.stderr
    assert (
        f"{TICKET} base control: passed; every bound check failed [dod-151]"
        in control.stdout
    )
    assert gate.calls() == [
        {"at": "head", "items": ["dod-151"], "criteria": ["AC151"]},
        {"at": "base", "items": ["dod-151"], "criteria": ["AC151"]},
    ]


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_new_criterion_that_passes_at_the_merge_base_is_still_refused(
    tmp_path: Path,
) -> None:
    gate = _Gate(tmp_path, CARRIED, _with_new_criterion(CARRIED, 151))
    for step_id in ("scope", "head_verify", "merge_base"):
        assert gate.run(step_id).returncode == 0
    # The stand-in verifier now reports a pass at the merge base too.
    gate.verifier.write_text(
        gate.verifier.read_text().replace(
            '"/head_home/" in os.getcwd()', '"/" in os.getcwd()'
        )
    )
    control = gate.run("base_control")
    assert control.returncode == 1
    assert (
        f"::error::{TICKET} [dod-151]: bound test also passes at the merge base"
        in control.stdout
    )


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_contract_with_nothing_new_is_refused_before_any_check_runs(
    tmp_path: Path,
) -> None:
    gate = _Gate(tmp_path, CARRIED, CARRIED)
    scope = gate.run("scope")
    assert scope.returncode == 1
    assert (
        f"::error::{TICKET}: every evidence item and acceptance criterion in "
        f"contracts/{TICKET}.yaml is carried unchanged from the merge base's "
        "contract; this pull request binds no evidence of its own"
    ) in scope.stdout
    assert not (gate.dod / "scope" / f"head-{TICKET}.yaml").exists()
    assert gate.calls() == []


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_an_item_whose_check_names_a_changed_path_runs_at_the_head_only(
    tmp_path: Path,
) -> None:
    head = _with_new_criterion(CARRIED, 151)
    gate = _Gate(
        tmp_path,
        CARRIED,
        head,
        head_files={
            "tests/test_new.py": "# new\n",
            "tests/test_carried.py": "# moved\n",
        },
    )
    assert gate.run("scope").returncode == 0
    # Every carried item names tests/test_carried.py, which the diff changes.
    assert len(_ids(gate.scoped("head"))) == 151
    assert _ids(gate.scoped("base")) == ["dod-151"]
    assert _criteria(gate.scoped("head")) == ["AC151"]


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_changed_criterion_brings_the_items_that_bind_it(tmp_path: Path) -> None:
    head = json.loads(json.dumps(CARRIED))
    head["requirements"][41]["acceptance"][0]["statement"] = "AC42: reworded"
    gate = _Gate(tmp_path, CARRIED, head)
    assert gate.run("scope").returncode == 0
    for side in ("head", "base"):
        assert _ids(gate.scoped(side)) == ["dod-42"]
        assert _criteria(gate.scoped(side)) == ["AC42"]
    summary = json.loads((gate.dod / "scope" / f"summary-{TICKET}.json").read_text())
    assert summary["new_criteria"] == ["AC42"]


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_changed_item_runs_and_its_carried_criterion_is_not_re_proven(
    tmp_path: Path,
) -> None:
    head = json.loads(json.dumps(CARRIED))
    head["dod_evidence"][6]["checks"][0]["check_value"] += " --no-cov"
    gate = _Gate(tmp_path, CARRIED, head)
    assert gate.run("scope").returncode == 0
    for side in ("head", "base"):
        assert _ids(gate.scoped(side)) == ["dod-7"]
        assert _criteria(gate.scoped(side)) == []


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_supersession_or_binding_retirement_is_never_split(tmp_path: Path) -> None:
    superseding = _item(151, "tests/test_new.py")
    superseding["evidence_artifact"] = "supersedes_dod_evidence:dod-3"
    retiring = _item(152, "tests/test_new.py")
    retiring["supersedes_ac_binding"] = [{"item": "dod-9", "label": "AC9"}]
    head = json.loads(json.dumps(CARRIED))
    head["dod_evidence"] += [superseding, retiring]
    head["requirements"] += [_criterion(151), _criterion(152)]
    gate = _Gate(tmp_path, CARRIED, head)
    assert gate.run("scope").returncode == 0
    for side in ("head", "base"):
        assert _ids(gate.scoped(side)) == ["dod-3", "dod-9", "dod-151", "dod-152"]


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_binding_records_on_one_label_travel_together(tmp_path: Path) -> None:
    def bound(number: int, label: str, by: str) -> dict[str, Any]:
        item = _item(number)
        item["ac_bindings"] = [
            {"label": label, "proposed_by": "lane-a", "accepted_by": by}
        ]
        return item

    base = _contract(range(1, 4), [bound(10, "AC1", "lane-b")])
    head = json.loads(json.dumps(base))
    head["dod_evidence"].append(bound(11, "AC1", "lane-a"))
    gate = _Gate(tmp_path, base, head)
    assert gate.run("scope").returncode == 0
    assert _ids(gate.scoped("head")) == ["dod-10", "dod-11"]


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_contract_new_at_this_head_is_verified_in_full(tmp_path: Path) -> None:
    head = _contract(range(1, 6))
    gate = _Gate(tmp_path, None, head)
    assert gate.run("scope").returncode == 0
    for side in ("head", "base"):
        assert _ids(gate.scoped(side)) == _ids(head)
        assert _criteria(gate.scoped(side)) == _criteria(head)


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
@pytest.mark.parametrize(
    "head_text",
    [
        "ticket_id: OMN-1\nticket_id: OMN-1\ndod_evidence: []\n",
        "ticket_id: OMN-1\ndod_evidence: [\n",
        "ticket_id: OMN-1\ndod_evidence: not-a-list\n",
    ],
    ids=["duplicate-key", "invalid-yaml", "evidence-not-a-list"],
)
def test_a_contract_that_cannot_be_compared_is_verified_in_full(
    tmp_path: Path, head_text: str
) -> None:
    gate = _Gate(tmp_path, CARRIED, head_text)
    scope = gate.run("scope")
    assert scope.returncode == 0, scope.stdout + scope.stderr
    assert f"{TICKET}: contract not scoped" in scope.stdout
    for side in ("head", "base"):
        assert (gate.dod / "scope" / f"{side}-{TICKET}.yaml").read_text() == head_text


@pytest.mark.skipif(TOOLS_MISSING, reason="bash, git and jq are required")
def test_a_missing_contract_is_left_to_the_head_step_to_name(tmp_path: Path) -> None:
    gate = _Gate(tmp_path, CARRIED, CARRIED)
    gate.git("rm", "-q", f"contracts/{TICKET}.yaml")
    gate.commit("drop the contract")
    gate.head_sha = gate.git("rev-parse", "HEAD")
    assert gate.run("scope").returncode == 0
    head = gate.run("head_verify")
    assert head.returncode == 1
    assert (
        f"::error::pull request cites {TICKET} but carries no contracts/{TICKET}.yaml"
        in head.stdout
    )
