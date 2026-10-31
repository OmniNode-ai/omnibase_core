# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: omnibase_core repo-owned evidence and its S6 evidence caller."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CALLER_PATH = WORKFLOWS_DIR / "call-repo-evidence-gate.yml"

# First release whose wheel ships node_dod_verify occ-difference, omnimarket#3277.
_DIFFERENCE_CLASSIFIER_FLOOR = (0, 4, 294)


def test_caller_workflow_shape() -> None:
    text = CALLER_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    # PyYAML 1.1 resolves the bare `on:` key to the boolean True.
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict), "caller must declare a mapping on: block"
    assert "pull_request_target" in triggers, "caller must run from the base branch"
    assert "pull_request" not in triggers, "caller must not use pull_request"
    assert "workflow_run" not in triggers, "caller must not use workflow_run"
    target = triggers["pull_request_target"]
    assert target["branches"] == ["dev", "main"], "caller must target dev and main"
    assert target["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "edited",
        "ready_for_review",
    ], "caller must cover the declared PR activity types"
    assert data["permissions"] == {"contents": "read", "pull-requests": "read"}, (
        "caller permissions must be exactly contents: read and pull-requests: read"
    )
    assert set(data["jobs"]) == {"repo-evidence"}, (
        "caller must have one repo-evidence job"
    )
    job = data["jobs"]["repo-evidence"]
    assert re.fullmatch(
        r"OmniNode-ai/omnibase_core/\.github/workflows/receipt-gate\.yml@dev-[0-9]{14}-[0-9a-f]{12}",
        job["uses"],
    ), "receipt-gate reusable must be pinned by a dev-merge tag (OMN-21495)"
    assert job["with"]["evidence-source"] == "caller", (
        "caller evidence mode is required"
    )
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", job["with"]["verifier-version"]), (
        "verifier-version must be a numeric semantic version"
    )
    for key in ("steps", "secrets", "if", "name", "permissions"):
        assert key not in job, f"caller job must not declare {key}"
    assert "secrets: inherit" not in text, "caller must not inherit secrets"


def test_caller_stops_comparing_with_occ_at_the_s6_cutover() -> None:
    job = yaml.safe_load(CALLER_PATH.read_text(encoding="utf-8"))["jobs"][
        "repo-evidence"
    ]
    assert job["with"].get("compare-with-occ") == "false", (
        'the S6 cut-over requires compare-with-occ: "false" (a quoted string input)'
    )
    version = tuple(int(part) for part in job["with"]["verifier-version"].split("."))
    assert version >= _DIFFERENCE_CLASSIFIER_FLOOR, (
        "verifier-version must ship node_dod_verify occ-difference "
        f"(>= {'.'.join(map(str, _DIFFERENCE_CLASSIFIER_FLOOR))})"
    )
    assert version >= (0, 4, 305), (
        "verifier-version must ship omnimarket#3563 "
        "(node_dod_verify names contract_in_another_repo, omnimarket v0.4.305), "
        "the verifier half of the receipt-gate pin"
    )


def test_caller_pins_the_writer_release_cut_reusable() -> None:
    job = yaml.safe_load(CALLER_PATH.read_text(encoding="utf-8"))["jobs"][
        "repo-evidence"
    ]
    # omnibase_core#1914's squash commit (committed 2026-10-08T21:49:13Z) carries
    # #1912's contract-home marker and adds the OCC writer app's release-cut
    # exemption in dod-verify. The caller names a dev-merge tag (OMN-21495), whose
    # 14-digit stamp is the tagged commit's commit time, at or after that commit.
    tag = re.search(r"@dev-(?P<stamp>[0-9]{14})-[0-9a-f]{12}$", job["uses"])
    assert tag is not None, job["uses"]
    assert tag["stamp"] >= "20261008214913", job["uses"]


_PYTEST_VALUE_OPTIONS = frozenset({"-k", "-m", "-o", "-n", "-c", "-p"})


def _pytest_selector(check_value: str) -> str:
    """The path a pytest evidence command runs: a file, a ``file::node`` id or a tests directory."""
    previous = ""
    for token in shlex.split(check_value):
        value_of_option = previous in _PYTEST_VALUE_OPTIONS
        previous = token
        if value_of_option:
            continue
        path = token.partition("::")[0]
        if path.endswith((".py", "/tests")) or (
            path.startswith("tests/") and (REPO_ROOT / path).is_dir()
        ):
            return path
    return ""


def test_pytest_selector_reads_files_node_ids_and_directories() -> None:
    assert (
        _pytest_selector(
            "uv run pytest tests/ci/test_repo_evidence_caller_omn20074.py -q"
        )
        == "tests/ci/test_repo_evidence_caller_omn20074.py"
    )
    assert (
        _pytest_selector(
            "uv run pytest tests/ci/test_repo_evidence_caller_omn20074.py::test_caller_workflow_shape"
            " -q -o addopts=''"
        )
        == "tests/ci/test_repo_evidence_caller_omn20074.py"
    )
    assert _pytest_selector("uv run pytest tests/ci -q") == "tests/ci"
    assert _pytest_selector("uv run pytest tests/ci/ -q") == "tests/ci/"


def test_pytest_selector_reads_no_path_from_options_or_a_missing_directory() -> None:
    assert _pytest_selector("uv run pytest -q -o addopts='' -k 'tests/ci'") == ""
    assert _pytest_selector("uv run pytest tests/no_such_directory -q") == ""


def test_every_repo_contract_binds_every_criterion() -> None:
    contracts = sorted((REPO_ROOT / "contracts").glob("OMN-*.yaml"))
    assert contracts, "expected at least one repo-owned contracts/OMN-*.yaml"
    for path in contracts:
        contract = yaml.safe_load(path.read_text(encoding="utf-8"))
        criteria = {
            ac["id"]
            for requirement in contract.get("requirements", [])
            for ac in requirement.get("acceptance", [])
        }
        bound: set[str] = set()
        for item in contract.get("dod_evidence", []):
            if "binds_ac" not in item:
                continue
            label = f"{path.name}:{item['id']}"
            bound.update(item["binds_ac"])
            assert "ac_bindings" not in item, f"{label}: use binds_ac, not ac_bindings"
            checks = item.get("checks", [])
            assert checks, f"{label}: binds_ac requires at least one check"
            for check in checks:
                if check.get("check_type") != "test_passes" or not check.get(
                    "check_value", ""
                ).startswith("uv run pytest "):
                    continue
                selector = _pytest_selector(check["check_value"])
                assert (
                    selector
                    and not Path(selector).is_absolute()
                    and (REPO_ROOT / selector).exists()
                    and (REPO_ROOT / selector).resolve().is_relative_to(REPO_ROOT)
                ), (
                    f"{label}: pytest evidence must name an existing relative path inside the repo"
                )
        assert criteria <= bound, (
            f"{path.name}: acceptance criteria missing binds_ac: {sorted(criteria - bound)}"
        )


def test_the_caller_takes_the_slot_of_the_retired_occ_preflight_caller() -> None:
    budget = yaml.safe_load(
        (
            REPO_ROOT / "architecture-handshakes" / "pull-request-workflow-budget.yaml"
        ).read_text(encoding="utf-8")
    )
    allowlisted_workflows = budget["allowlisted_workflows"]
    assert "call-repo-evidence-gate.yml" in allowlisted_workflows
    assert "call-occ-preflight.yml" not in allowlisted_workflows
    assert budget["budget"] == 27
    assert len(allowlisted_workflows) == budget["budget"]
    assert not (WORKFLOWS_DIR / "call-occ-preflight.yml").exists()


def test_occ_preflight_context_is_retired_at_the_s6_cutover() -> None:
    manifest = yaml.safe_load(
        (REPO_ROOT / ".github" / "required-checks.yaml").read_text(encoding="utf-8")
    )
    rows = [g for g in manifest["gates"] if g["name"] == "occ-preflight / eligibility"]
    assert len(rows) == 1
    assert rows[0]["mode"] == "RETIRED"
    assert "OMN-20074" in rows[0]["rationale"]
    assert not (WORKFLOWS_DIR / "call-receipt-gate.yml").exists()
