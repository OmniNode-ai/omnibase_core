# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Build a shadow-mode test-selection record for a dev PR (OMN-14342).

Observational only. The full unit suite runs unconditionally on the boundary;
this compares the counterfactual selector output (forced ``--feature-flag on``)
against the full-suite junit results to measure what the selector WOULD have
skipped — its escaped-failure count, selected fraction, and wall-clock saved.

Consumes:
  * a ``ModelTestSelection`` JSON (the forced-on shadow selection),
  * the change set (one path per line),
  * every unit junit-*.xml from the full-suite matrix,
  * the static adjacency map (for shared-module attribution).

Emits one ``ModelShadowRecord`` JSON line.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.ci.test_selection_loader import ModelAdjacencyMap, load_adjacency_map
from scripts.ci.test_selection_models import ModelTestSelection
from scripts.ci.test_selection_shadow_models import ModelShadowRecord

SRC_PREFIX = "src/omnibase_core/"
# Full-suite predicted marker: "tests/" (or "tests/unit/") selects everything.
_FULL_MARKERS = frozenset({"tests/", "tests/unit/"})


@dataclass(frozen=True)
class TestCaseResult:
    """One parsed junit <testcase>."""

    file: str
    name: str
    failed: bool
    time_s: float


def _classname_to_path(classname: str) -> str | None:
    """Best-effort fallback when a <testcase> has no ``file`` attribute.

    pytest reliably emits ``file`` on every testcase, so this is only a guard.
    A dotted classname like ``tests.unit.models.test_x`` maps back to
    ``tests/unit/models/test_x.py`` (a trailing ``.ClassName`` is not
    distinguishable from a module segment, so we accept coarse attribution).
    """
    if not classname:
        return None
    return classname.replace(".", "/") + ".py"


def parse_junit_file(path: Path) -> list[TestCaseResult]:
    """Parse one junit XML file into testcase results.

    Tolerant of both ``<testsuites>`` and bare ``<testsuite>`` roots. A malformed
    file yields an empty list rather than raising — a missing shard must not sink
    the whole shadow record.
    """
    try:
        root = ET.parse(path).getroot()  # noqa: S314 (trusted CI-produced junit)
    except ET.ParseError:
        return []
    results: list[TestCaseResult] = []
    for tc in root.iter("testcase"):
        file = tc.get("file") or _classname_to_path(tc.get("classname", "")) or ""
        # A testcase is a real failure on <failure> or <error>, not <skipped>.
        failed = tc.find("failure") is not None or tc.find("error") is not None
        try:
            time_s = float(tc.get("time", "0") or 0)
        except ValueError:
            time_s = 0.0
        results.append(
            TestCaseResult(
                file=file, name=tc.get("name", ""), failed=failed, time_s=time_s
            )
        )
    return results


def collect_unit_junit(junit_dir: Path) -> tuple[list[TestCaseResult], int]:
    """Collect unit-suite testcases under ``junit_dir``.

    Recurses (artifact downloads nest each shard in its own folder). Integration
    shards (``junit-int-*.xml``) are excluded — the selector never narrows the
    always-run integration job, so it is not part of the counterfactual.
    """
    results: list[TestCaseResult] = []
    files_parsed = 0
    for xml in sorted(junit_dir.rglob("junit-*.xml")):
        if xml.name.startswith("junit-int-"):
            continue
        parsed = parse_junit_file(xml)
        results.extend(parsed)
        files_parsed += 1
    return results, files_parsed


def _is_selected(file_path: str, predicted_paths: list[str], is_full: bool) -> bool:
    if is_full:
        return True
    norm = file_path.lstrip("./")
    for pred in predicted_paths:
        if pred in _FULL_MARKERS:
            return True
        if norm.startswith(pred):
            return True
    return False


def changed_modules_for(
    changed_files: list[str], config: ModelAdjacencyMap
) -> list[str]:
    """Top-level ``src/omnibase_core/<module>`` dirs touched by the change set.

    ``config`` is accepted for call-site stability only; the retired
    hand-curated ``adjacency`` map (OMN-14921) is no longer consulted here —
    every top-level module name under ``src/omnibase_core/`` is a real module,
    so no "known module" filter is needed.
    """
    mods = {
        path[len(SRC_PREFIX) :].split("/", 1)[0]
        for path in changed_files
        if path.startswith(SRC_PREFIX)
    }
    return sorted(mods)


def build_record(
    *,
    selection: ModelTestSelection,
    changed_files: list[str],
    config: ModelAdjacencyMap,
    junit_results: list[TestCaseResult],
    junit_files_parsed: int,
    repo: str,
    pr_number: int | None,
    head_sha: str,
    base_sha: str | None,
    event: str,
    ref_name: str,
) -> ModelShadowRecord:
    is_full = selection.is_full_suite
    predicted = list(selection.selected_paths)

    changed_mods = changed_modules_for(changed_files, config)
    triggering = sorted(set(changed_mods) & set(config.shared_modules))

    all_files = {r.file for r in junit_results if r.file}
    selected_files = {f for f in all_files if _is_selected(f, predicted, is_full)}
    total_test_files = len(all_files)
    selected_test_files = len(selected_files)
    selected_fraction = (
        selected_test_files / total_test_files if total_test_files else 0.0
    )

    failures = [r for r in junit_results if r.failed]
    escaped = sorted(
        {r.file for r in failures if not _is_selected(r.file, predicted, is_full)}
    )

    wall_total = sum(r.time_s for r in junit_results)
    wall_selected = sum(
        r.time_s for r in junit_results if _is_selected(r.file, predicted, is_full)
    )
    wall_saved = 0.0 if is_full else max(0.0, wall_total - wall_selected)

    return ModelShadowRecord(
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        base_sha=base_sha,
        event=event,
        ref_name=ref_name,
        created_at=datetime.now(UTC).isoformat(),
        changed_file_count=len(changed_files),
        changed_modules=changed_mods,
        shadow_is_full_suite=is_full,
        shadow_reason=(
            selection.full_suite_reason.value
            if selection.full_suite_reason is not None
            else None
        ),
        triggering_shared_modules=triggering,
        predicted_paths=predicted,
        predicted_split_count=selection.split_count,
        total_test_files=total_test_files,
        selected_test_files=selected_test_files,
        selected_fraction=selected_fraction,
        full_suite_test_count=len(junit_results),
        full_suite_failure_count=len(failures),
        escaped_failures=escaped,
        escaped_failure_count=len(escaped),
        wall_clock_total_s=wall_total,
        wall_clock_selected_s=wall_selected,
        wall_clock_saved_s=wall_saved,
        junit_files_parsed=junit_files_parsed,
    )


def _read_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a shadow-mode test-selection record for a dev PR"
    )
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--changed-files-from", type=Path, required=True)
    parser.add_argument("--junit-dir", type=Path, required=True)
    parser.add_argument(
        "--adjacency",
        type=Path,
        default=Path(__file__).parent / "test_selection_adjacency.yaml",
    )
    parser.add_argument("--out", type=Path, default=Path("shadow_record.json"))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr-number", default=os.environ.get("SHADOW_PR_NUMBER", ""))
    parser.add_argument("--head-sha", default=os.environ.get("SHADOW_HEAD_SHA", ""))
    parser.add_argument("--base-sha", default=os.environ.get("SHADOW_BASE_SHA", ""))
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--ref-name", default=os.environ.get("GITHUB_REF_NAME", ""))
    args = parser.parse_args(argv)

    selection = ModelTestSelection.model_validate_json(
        args.selection.read_text(encoding="utf-8")
    )
    changed_files = _read_lines(args.changed_files_from)
    config = load_adjacency_map(args.adjacency)
    junit_results, files_parsed = collect_unit_junit(args.junit_dir)

    pr_number = int(args.pr_number) if str(args.pr_number).strip().isdigit() else None

    record = build_record(
        selection=selection,
        changed_files=changed_files,
        config=config,
        junit_results=junit_results,
        junit_files_parsed=files_parsed,
        repo=args.repo,
        pr_number=pr_number,
        head_sha=args.head_sha,
        base_sha=args.base_sha or None,
        event=args.event,
        ref_name=args.ref_name,
    )
    line = record.model_dump_json()
    args.out.write_text(line + "\n", encoding="utf-8")
    sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
