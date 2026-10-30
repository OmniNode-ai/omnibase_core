# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Keep hosted source comparisons in sync with the published implementation.

PR #2071 changed the CLI and repository-jobs handler without repinning the
carried deploy probes. The probes then compared the new files with their old
published bytes and failed. These offline cases check the immutable publication
URL and strict comparison commands. The live curl/cmp checks verify that the
published bytes match the checked-out implementation.
The probes name files that exist in the tree.
"""

from __future__ import annotations

import shlex
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
# Immutable commits that last wrote the relocated CLI runtime and jobs handler.
CLI = "src/omnibase_core/nodes/node_ci_inheritance_check_compute/runtime_ci_inheritance_check.py"
CLI_ROOT = "https://raw.githubusercontent.com/OmniNode-ai/omnibase_core/04fca965946ab651513af256b8f84cdecec4a2ab"
JOBS = "src/omnibase_core/nodes/node_ci_repository_jobs_check_compute/handler_ci_repository_jobs.py"
JOBS_ROOT = "https://raw.githubusercontent.com/OmniNode-ai/omnibase_core/095ea7558cf0584f84ef4ba71319ef66ec0369e1"


@pytest.mark.parametrize(
    ("evidence_id", "source_path", "published_root"),
    [
        ("dod-omn-17427-deploy-hosted-ci-inheritance", CLI, CLI_ROOT),
        ("dod-omn-17427-deploy-hosted-repository-jobs", CLI, CLI_ROOT),
        ("dod-omn-17427-deploy-hosted-repository-jobs", JOBS, JOBS_ROOT),
    ],
)
def test_hosted_probe_matches_published_source(
    evidence_id: str, source_path: str, published_root: str
) -> None:
    contract = yaml.safe_load((ROOT / "contracts/OMN-17427.yaml").read_text())
    assert (ROOT / source_path).is_file(), (
        "the compared file is gone; repoint the probe at the file that now holds the code"
    )
    evidence = next(
        item for item in contract["dod_evidence"] if item["id"] == evidence_id
    )
    assert evidence["execution_scope"] == "hosted_and_local"
    expected_url = f"{published_root}/{source_path}"
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
