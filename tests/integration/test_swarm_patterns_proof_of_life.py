# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_zone_classifier_against_real_repo() -> None:
    from omnibase_core.enums.enum_file_zone import EnumFileZone
    from omnibase_core.validation.zone_classifier import classify_path

    assert (
        classify_path(REPO_ROOT / "src" / "omnibase_core" / "topics.py")
        == EnumFileZone.PRODUCTION
    )
    assert classify_path(REPO_ROOT / "tests" / "conftest.py") == EnumFileZone.TEST
    assert classify_path(REPO_ROOT / "pyproject.toml") == EnumFileZone.CONFIG


@pytest.mark.integration
def test_completion_verify_real_file() -> None:
    from omnibase_core.validation.completion_verify import verify

    target = REPO_ROOT / "src" / "omnibase_core" / "topics.py"
    assert target.exists(), "fixture file missing"
    result = verify(
        task_id="proof-of-life",
        description="Verify `TopicBase` is defined in topics.py",
        files_touched=[str(target.relative_to(REPO_ROOT))],
        project_root=REPO_ROOT,
    )
    assert result.found.get("TopicBase") == str(target.resolve()), result


@pytest.mark.integration
def test_co_change_dark_matter_cli_runs() -> None:
    rc = subprocess.run(
        ["python", "scripts/analysis/co_change_dark_matter.py", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rc.returncode == 0, rc.stderr
    payload = json.loads(rc.stdout)
    assert "pairs" in payload
    # may be empty on a young repo, that's OK
    for pair in payload["pairs"]:
        assert {"a", "b", "npmi", "co_changes"} <= set(pair)


@pytest.mark.integration
def test_prm_detectors_no_false_positive_on_empty() -> None:
    from omnibase_core.agents.prm_detectors import (
        detect_context_thrash,
        detect_expansion_drift,
        detect_ping_pong,
        detect_repetition_loop,
        detect_stuck_on_test,
    )

    for fn in (
        detect_repetition_loop,
        detect_ping_pong,
        detect_expansion_drift,
        detect_stuck_on_test,
        detect_context_thrash,
    ):
        assert fn([], last_processed_step=0) == []


@pytest.mark.integration
def test_semantic_diff_round_trip() -> None:
    from omnibase_core.analysis.semantic_diff import compute_diff

    old = "def foo(x): return x\n"
    new = "def foo(x, y): return x + y\n"
    report = compute_diff(old, new, file_path="x.py", consumers_count=0)
    kinds = [c.kind for c in report.changes]
    assert "signature_change" in kinds, kinds
