# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Keep hosted source comparisons in sync with the published implementation.

PR #2071 changed the CLI and repository-jobs handler without repinning the
carried deploy probes. The probes then compared the new files with their old
published bytes and failed. These offline cases check the immutable publication
URL and strict comparison commands. The live curl/cmp checks verify that the
published bytes match the checked-out implementation.
"""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
# PR #2071's public landed implementation.
PUBLISHED_SOURCE_ROOT = "https://raw.githubusercontent.com/OmniNode-ai/omnibase_core/1c9566e2c249fe54257a4b3ef3ff2e71de027b89"
CLI = "src/omnibase_core/handlers/handler_ci_inheritance_cli.py"
JOBS = "src/omnibase_core/handlers/handler_ci_repository_jobs.py"


@pytest.mark.parametrize(
    ("evidence_id", "source_path"),
    [
        ("dod-omn-17427-deploy-hosted-ci-inheritance", CLI),
        ("dod-omn-17427-deploy-hosted-repository-jobs", CLI),
        ("dod-omn-17427-deploy-hosted-repository-jobs", JOBS),
    ],
)
def test_hosted_probe_matches_published_source(
    evidence_id: str, source_path: str
) -> None:
    contract = yaml.safe_load((ROOT / "contracts/OMN-17427.yaml").read_text())
    evidence = next(
        item for item in contract["dod_evidence"] if item["id"] == evidence_id
    )
    assert evidence["execution_scope"] == "hosted_and_local"
    expected_url = f"{PUBLISHED_SOURCE_ROOT}/{source_path}"
    comparisons = [
        shlex.split(check["check_value"])
        for check in evidence["checks"]
        if check["check_type"] == "command"
        and check["check_value"].endswith(f"| cmp - {source_path}'")
    ]
    assert len(comparisons) == 1, "keep exactly one published-source comparison"
    assert comparisons[0][:4] == ["bash", "-o", "pipefail", "-c"]
    assert shlex.split(comparisons[0][4]) == [
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--location",
        "--max-time",
        "30",
        expected_url,
        "|",
        "cmp",
        "-",
        source_path,
    ], "repin the hosted probe when its published implementation changes"
