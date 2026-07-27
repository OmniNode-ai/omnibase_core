# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for the shadow-mode test-selection record builder (OMN-14342)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.test_selection_loader import load_adjacency_map
from scripts.ci.test_selection_models import EnumFullSuiteReason, ModelTestSelection
from scripts.ci.test_selection_shadow import (
    build_record,
    collect_unit_junit,
    main,
    parse_junit_file,
)
from scripts.ci.test_selection_shadow_models import ModelShadowRecord

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
ADJ = REPO_ROOT / "scripts/ci/test_selection_adjacency.yaml"
CONFIG = load_adjacency_map(ADJ)


def _junit(cases: list[tuple[str, float, bool]]) -> str:
    """Render a junit XML from (file, time_s, failed) tuples."""
    rows = []
    for i, (file, time_s, failed) in enumerate(cases):
        classname = file.removesuffix(".py").replace("/", ".")
        body = '<failure message="boom"/>' if failed else ""
        rows.append(
            f'<testcase classname="{classname}" name="test_{i}" '
            f'file="{file}" time="{time_s}">{body}</testcase>'
        )
    inner = "".join(rows)
    return f'<testsuite name="pytest" tests="{len(cases)}">{inner}</testsuite>'


def _narrowed_selection() -> ModelTestSelection:
    return ModelTestSelection(
        selected_paths=["tests/unit/models/"],
        split_count=1,
        is_full_suite=False,
        full_suite_reason=None,
        matrix=[1],
    )


def _full_selection() -> ModelTestSelection:
    return ModelTestSelection(
        selected_paths=["tests/"],
        split_count=40,
        is_full_suite=True,
        full_suite_reason=EnumFullSuiteReason.SHARED_MODULE,
        matrix=list(range(1, 41)),
    )


def _write_junit(
    dirpath: Path, name: str, cases: list[tuple[str, float, bool]]
) -> None:
    (dirpath / name).write_text(_junit(cases), encoding="utf-8")


def _build(
    junit_dir: Path,
    selection: ModelTestSelection,
    changed_files: list[str],
) -> ModelShadowRecord:
    results, parsed = collect_unit_junit(junit_dir)
    return build_record(
        selection=selection,
        changed_files=changed_files,
        config=CONFIG,
        junit_results=results,
        junit_files_parsed=parsed,
        repo="OmniNode-ai/omnibase_core",
        pr_number=1234,
        head_sha="deadbeef",
        base_sha="cafef00d",
        event="pull_request",
        ref_name="jonah/feature",
    )


def test_escaped_failure_detected_outside_predicted_set(tmp_path: Path) -> None:
    # models test passes; a cli test FAILS but is NOT under the predicted
    # tests/unit/models/ set -> that failure "escapes" the narrowed selection.
    _write_junit(
        tmp_path,
        "junit-1.xml",
        [
            ("tests/unit/models/test_a.py", 2.0, False),
            ("tests/unit/cli/test_b.py", 0.5, True),
        ],
    )
    rec = _build(tmp_path, _narrowed_selection(), ["src/omnibase_core/models/x.py"])
    assert rec.full_suite_failure_count == 1
    assert rec.escaped_failure_count == 1
    assert rec.escaped_failures == ["tests/unit/cli/test_b.py"]
    assert rec.shadow_is_full_suite is False


def test_failure_inside_predicted_set_does_not_escape(tmp_path: Path) -> None:
    _write_junit(
        tmp_path,
        "junit-1.xml",
        [
            ("tests/unit/models/test_a.py", 2.0, True),
            ("tests/unit/cli/test_b.py", 0.5, False),
        ],
    )
    rec = _build(tmp_path, _narrowed_selection(), ["src/omnibase_core/models/x.py"])
    assert rec.full_suite_failure_count == 1
    assert rec.escaped_failure_count == 0
    # 1 of 2 test files selected; cli test (0.5s) is skipped by the shadow set.
    assert rec.total_test_files == 2
    assert rec.selected_test_files == 1
    assert rec.selected_fraction == 0.5
    assert rec.wall_clock_total_s == 2.5
    assert rec.wall_clock_selected_s == 2.0
    assert rec.wall_clock_saved_s == 0.5


def test_full_suite_shadow_saves_nothing_and_escapes_nothing(tmp_path: Path) -> None:
    _write_junit(
        tmp_path,
        "junit-1.xml",
        [
            ("tests/unit/models/test_a.py", 2.0, True),
            ("tests/unit/cli/test_b.py", 0.5, True),
        ],
    )
    rec = _build(tmp_path, _full_selection(), ["src/omnibase_core/models/x.py"])
    assert rec.shadow_is_full_suite is True
    assert rec.shadow_reason == "shared_module"
    assert rec.escaped_failure_count == 0
    assert rec.wall_clock_saved_s == 0.0
    assert rec.selected_fraction == 1.0
    assert rec.triggering_shared_modules == ["models"]


def test_integration_junit_is_excluded(tmp_path: Path) -> None:
    _write_junit(tmp_path, "junit-1.xml", [("tests/unit/models/test_a.py", 1.0, False)])
    _write_junit(
        tmp_path, "junit-int-1.xml", [("tests/integration/test_z.py", 9.0, True)]
    )
    results, parsed = collect_unit_junit(tmp_path)
    assert parsed == 1  # only the unit shard
    assert all("integration" not in r.file for r in results)


def test_collect_recurses_nested_artifact_dirs(tmp_path: Path) -> None:
    # Artifact downloads nest each shard in its own directory.
    (tmp_path / "test-results-1").mkdir()
    (tmp_path / "test-results-2").mkdir()
    _write_junit(
        tmp_path / "test-results-1",
        "junit-1.xml",
        [("tests/unit/models/test_a.py", 1.0, False)],
    )
    _write_junit(
        tmp_path / "test-results-2",
        "junit-2.xml",
        [("tests/unit/cli/test_b.py", 1.0, True)],
    )
    results, parsed = collect_unit_junit(tmp_path)
    assert parsed == 2
    assert len(results) == 2


def test_parse_junit_tolerates_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "junit-1.xml"
    bad.write_text("<not-closed", encoding="utf-8")
    assert parse_junit_file(bad) == []


def test_missing_file_attr_falls_back_to_classname(tmp_path: Path) -> None:
    (tmp_path / "junit-1.xml").write_text(
        '<testsuite tests="1"><testcase classname="tests.unit.cli.test_b" '
        'name="test_x" time="0.1"/></testsuite>',
        encoding="utf-8",
    )
    results = parse_junit_file(tmp_path / "junit-1.xml")
    assert results[0].file == "tests/unit/cli/test_b.py"


def test_empty_junit_dir_yields_zero_fraction_no_crash(tmp_path: Path) -> None:
    rec = _build(tmp_path, _narrowed_selection(), ["src/omnibase_core/models/x.py"])
    assert rec.total_test_files == 0
    assert rec.selected_fraction == 0.0
    assert rec.junit_files_parsed == 0


def test_model_rejects_escaped_when_full_suite() -> None:
    with pytest.raises(ValueError, match="escaped_failure_count must be 0"):
        ModelShadowRecord(
            repo="r",
            head_sha="h",
            event="pull_request",
            ref_name="b",
            created_at="2026-07-10T00:00:00+00:00",
            changed_file_count=1,
            shadow_is_full_suite=True,
            predicted_split_count=40,
            total_test_files=1,
            selected_test_files=1,
            selected_fraction=1.0,
            full_suite_test_count=1,
            full_suite_failure_count=1,
            escaped_failures=["tests/unit/cli/test_b.py"],
            escaped_failure_count=1,
            wall_clock_total_s=1.0,
            wall_clock_selected_s=1.0,
            wall_clock_saved_s=0.0,
            junit_files_parsed=1,
        )


def test_cli_main_writes_record(tmp_path: Path) -> None:
    _write_junit(tmp_path, "junit-1.xml", [("tests/unit/models/test_a.py", 1.0, False)])
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(_narrowed_selection().model_dump_json(), encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("src/omnibase_core/models/x.py\n", encoding="utf-8")
    out = tmp_path / "shadow_record.json"
    rc = main(
        [
            "--selection",
            str(selection_path),
            "--changed-files-from",
            str(changed),
            "--junit-dir",
            str(tmp_path),
            "--adjacency",
            str(ADJ),
            "--out",
            str(out),
            "--repo",
            "OmniNode-ai/omnibase_core",
            "--pr-number",
            "42",
            "--head-sha",
            "abc",
        ]
    )
    assert rc == 0
    rec = ModelShadowRecord.model_validate_json(out.read_text(encoding="utf-8"))
    assert rec.pr_number == 42
    assert rec.repo == "OmniNode-ai/omnibase_core"
