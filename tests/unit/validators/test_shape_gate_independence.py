# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the shape-gate independence guard (OMN-20298)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.handlers.handler_shape_gate_independence import main, validate_paths

REPO_ROOT = Path(__file__).resolve().parents[3]

PREFLIGHT_JOB = """
  occ-preflight:
    uses: ./.github/workflows/occ-preflight.yml
"""


def _write(tmp_path: Path, jobs: str) -> Path:
    path = tmp_path / "gate.yml"
    path.write_text(f"name: gate\non: [pull_request]\njobs:{jobs}", encoding="utf-8")
    return path


@pytest.mark.unit
def test_repository_workflows_have_no_dependent_detector() -> None:
    findings = validate_paths([REPO_ROOT / ".github" / "workflows"])
    assert [f.format() for f in findings] == []


@pytest.mark.unit
def test_detector_skipped_behind_preflight_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + """
  canonical-inference-gate:
    needs: occ-preflight
    runs-on: ubuntu-latest
    steps:
      - run: echo detector
""",
    )
    findings = validate_paths([path])
    assert len(findings) == 1
    assert "skipped when the preflight fails" in findings[0].reason


@pytest.mark.unit
def test_transitive_dependency_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + """
  zone-filter:
    needs: occ-preflight
    runs-on: ubuntu-latest
    steps:
      - run: echo zone
  url-authority-gate:
    needs: zone-filter
    runs-on: ubuntu-latest
    steps:
      - run: echo detector
""",
    )
    assert len(validate_paths([path])) == 1


@pytest.mark.unit
def test_step_that_reads_the_preflight_result_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + """
  canonical-inference-gate:
    needs: occ-preflight
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Fail when OCC preflight fails
        if: needs.occ-preflight.result != 'success'
        run: exit 1
""",
    )
    findings = validate_paths([path])
    assert len(findings) == 1
    assert "never branches on the preflight result" in findings[0].reason


@pytest.mark.unit
def test_independent_detector_is_accepted(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + """
  canonical-inference-gate:
    runs-on: ubuntu-latest
    steps:
      - run: echo detector
""",
    )
    assert validate_paths([path]) == []


@pytest.mark.unit
def test_non_detector_may_depend_on_preflight(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + """
  build:
    needs: occ-preflight
    runs-on: ubuntu-latest
    steps:
      - run: echo build
""",
    )
    assert validate_paths([path]) == []


@pytest.mark.unit
def test_aggregator_reading_detector_result_is_not_a_detector(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + """
  canonical-inference-gate:
    runs-on: ubuntu-latest
    steps:
      - run: echo detector
  quality-gate:
    needs: [occ-preflight, canonical-inference-gate]
    runs-on: ubuntu-latest
    steps:
      - run: test "${{ needs.canonical-inference-gate.result }}" = success
""",
    )
    assert validate_paths([path]) == []


@pytest.mark.unit
def test_suppression_comment_does_not_suppress(tmp_path: Path) -> None:
    # The marker is assembled at runtime so this test file carries no
    # suppression comment of its own (OMN-20304 canonical-file-shape).
    marker = "#" + " shape-gate-ok"
    path = _write(
        tmp_path,
        PREFLIGHT_JOB
        + f"""
  canonical-inference-gate:
    {marker}: reason
    needs: occ-preflight  {marker}
    runs-on: ubuntu-latest
    steps:
      - run: echo detector
""",
    )
    assert len(validate_paths([path])) == 1


@pytest.mark.unit
def test_main_exit_codes(tmp_path: Path) -> None:
    bad = _write(
        tmp_path,
        PREFLIGHT_JOB
        + "\n  url-authority-gate:\n    needs: occ-preflight\n    runs-on: x\n    steps:\n      - run: y\n",
    )
    assert main([str(bad)]) == 1
    good = tmp_path / "good.yml"
    good.write_text(
        "name: g\non: [push]\njobs:\n  url-authority-gate:\n    runs-on: x\n    steps:\n      - run: y\n",
        encoding="utf-8",
    )
    assert main([str(good)]) == 0
