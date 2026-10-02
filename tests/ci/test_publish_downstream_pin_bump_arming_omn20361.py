# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Exercise downstream auto-merge arming and manual fallback (OMN-20361)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github/workflows/publish-downstream-pin-bump.yml"
)
PR_URL = "https://github.com/OmniNode-ai/omnibase_spi/pull/338"


@pytest.fixture(scope="module")
def open_pr_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = [
        step
        for step in workflow["jobs"]["bump"]["steps"]
        if step.get("name") == "Open PR + enable auto-merge"
    ]
    assert len(steps) == 1, "Expected to find the Open PR + enable auto-merge step"
    return steps[0]["run"]


@pytest.mark.parametrize(
    ("allow", "graphql_rc", "graphql_out"),
    [
        pytest.param("false", 0, "", id="disabled-manual-fallback"),
        pytest.param("true", 0, "", id="enabled-armed"),
        pytest.param(
            "true", 1, "GraphQL: API rate limit exceeded", id="rate-limit-fails"
        ),
        pytest.param(
            "null",
            1,
            "gh: Auto merge is not allowed for this repository",
            id="null-policy-manual-fallback",
        ),
        pytest.param("", 0, "", id="empty-armed"),
    ],
)
def test_auto_merge_arming(
    tmp_path: Path,
    open_pr_script: str,
    allow: str,
    graphql_rc: int,
    graphql_out: str,
) -> None:
    gh = tmp_path / "gh"
    gh.write_text(
        """#!/bin/bash
if [[ "$1" == "pr" && "$2" == "list" ]]; then
    printf '%s\\n' 'https://github.com/OmniNode-ai/omnibase_spi/pull/338'
    exit 0
fi
for arg in "$@"; do
    case "$arg" in
        .default_branch) printf '%s\\n' dev; exit 0 ;;
        .node_id) printf '%s\\n' PR_stub_338; exit 0 ;;
        .allow_auto_merge) printf '%s\\n' "$STUB_ALLOW"; exit 0 ;;
        graphql)
            printf '%s\\n' graphql >> "$STUB_GRAPHQL_LOG"
            printf '%s\\n' "$STUB_GRAPHQL_OUT"
            exit "$STUB_GRAPHQL_RC"
            ;;
    esac
done
exit 0
""",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    summary = tmp_path / "summary.md"
    graphql_log = tmp_path / "graphql.log"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", open_pr_script],
        cwd=tmp_path,
        env={
            "PATH": f"{tmp_path}:/usr/local/bin:/usr/bin:/bin",
            "REPO": "omnibase_spi",
            "NEW_SHA": "ab" * 20,
            "GITHUB_TOKEN": "x",
            "GITHUB_STEP_SUMMARY": str(summary),
            "STUB_ALLOW": allow,
            "STUB_GRAPHQL_LOG": str(graphql_log),
            "STUB_GRAPHQL_OUT": graphql_out,
            "STUB_GRAPHQL_RC": str(graphql_rc),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if allow == "true" and graphql_rc == 1:
        assert result.returncode != 0, result.stdout + result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr

    calls = graphql_log.read_text().splitlines() if graphql_log.exists() else []
    assert len(calls) == (0 if allow == "false" else 1)
    if allow in {"false", "null"}:
        summary_text = summary.read_text(encoding="utf-8")
        assert PR_URL in summary_text
        if allow == "false":
            assert any(
                "gh pr merge 338 --repo OmniNode-ai/omnibase_spi --squash" in line
                and "--auto" not in line
                for line in summary_text.splitlines()
            )
