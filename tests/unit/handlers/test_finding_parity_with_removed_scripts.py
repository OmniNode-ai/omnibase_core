# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Old-versus-new parity for check-no-dict-any and check-no-backward-compat (OMN-21501 AC3).

The two repository scripts were removed by the OMN-21501 squash. Their behaviour was recorded
from git history (see ``recorded_old_findings.json``: the script blobs at the parent of the
removing commit, run over ``tests/fixtures/finding_parity/src``). Each case here runs the
current hook over the same tree and requires the same ``(path, line, message)`` findings and
the same pass or fail verdict as the recording. The comparison counts duplicates, so a finding
reported twice by the old script must be reported twice by the new one.
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "finding_parity"
RECORDING = FIXTURE_ROOT / "recorded_old_findings.json"
FIXTURE_SUFFIX = ".fx"

MODULES = {
    "dict_any": "omnibase_core.nodes.node_dict_any_check_compute.runtime_dict_any_check",
    "backward_compat": "omnibase_core.nodes.node_backward_compat_check_compute.runtime_backward_compat_check",
}
CLEAN_FILES = ("src/pkg/clean.py", "src/pkg/models/epic/model_epic_state.py")
FINDING_LINE = re.compile(
    r"^FAIL: (?P<path>[^:]+\.py):(?P<line>\d+): \[[^\]]+\] (?P<message>.*)$"
)


Finding = tuple[str, int, str]


@dataclass(frozen=True)
class RecordedCase:
    tool: str
    mode: str
    exit_code: int
    findings: tuple[Finding, ...]


def _recorded_cases() -> list[RecordedCase]:
    document = json.loads(RECORDING.read_text("utf-8"))
    return [
        RecordedCase(
            tool=str(raw["tool"]),
            mode=str(raw["mode"]),
            exit_code=int(raw["exit_code"]),
            findings=tuple(
                (str(path), int(line), str(message))
                for path, line, message in raw["findings"]
            ),
        )
        for raw in document["cases"]
    ]


def _materialise(destination: Path) -> list[str]:
    """Copy the fixture tree, dropping the suffix that keeps the files out of every linter."""
    shutil.copytree(FIXTURE_ROOT / "src", destination / "src")
    for source in sorted((destination / "src").rglob(f"*.py{FIXTURE_SUFFIX}")):
        source.rename(source.with_suffix(""))
    return sorted(
        path.relative_to(destination).as_posix()
        for path in (destination / "src").rglob("*.py")
    )


def parse_findings(output: str) -> Counter[Finding]:
    found: Counter[Finding] = Counter()
    for line in output.splitlines():
        match = FINDING_LINE.match(line)
        if match:
            found[(match["path"], int(match["line"]), match["message"])] += 1
    return found


def differences(
    recorded: Counter[Finding], current: Counter[Finding]
) -> tuple[list[Finding], list[Finding]]:
    """(findings only the old script reported, findings only the new hook reports)."""
    return (
        sorted((recorded - current).elements()),
        sorted((current - recorded).elements()),
    )


@pytest.fixture
def run_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> Callable[[str, str], tuple[int, str]]:
    all_files = _materialise(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _run(tool: str, mode: str) -> tuple[int, str]:
        main = importlib.import_module(MODULES[tool]).main
        args = {
            "dir": ["--dir", "src"],
            "files": all_files,
            "clean": list(CLEAN_FILES),
        }[mode]
        capsys.readouterr()
        code: int = main(args)
        return code, capsys.readouterr().out

    return _run


@pytest.mark.parametrize(
    "case",
    _recorded_cases(),
    ids=lambda case: f"{case.tool}-{case.mode}",
)
def test_hook_reports_what_the_removed_script_reported(
    case: RecordedCase,
    run_current: Callable[[str, str], tuple[int, str]],
) -> None:
    code, out = run_current(case.tool, case.mode)
    only_old, only_new = differences(Counter(case.findings), parse_findings(out))
    assert only_old == [], (
        f"findings the old script reported and the hook lost: {only_old}"
    )
    assert only_new == [], f"findings the hook invented: {only_new}"
    assert code == case.exit_code, out


def test_the_recording_is_not_vacuous() -> None:
    cases = {(case.tool, case.mode): case for case in _recorded_cases()}
    assert len(cases) == 6
    for key, case in cases.items():
        has_findings = bool(case.findings)
        assert has_findings == (key[1] != "clean"), key
        assert case.exit_code == (1 if has_findings else 0), key
    assert len(cases[("dict_any", "dir")].findings) == 5
    assert len(cases[("backward_compat", "dir")].findings) == 24


def test_a_planted_difference_is_reported() -> None:
    """Falsifier for the comparison itself: a lost and an invented finding both show."""
    recorded = Counter({("src/a.py", 1, "m"): 2, ("src/b.py", 3, "n"): 1})
    current = Counter({("src/a.py", 1, "m"): 1, ("src/c.py", 9, "x"): 1})
    only_old, only_new = differences(recorded, current)
    assert only_old == [("src/a.py", 1, "m"), ("src/b.py", 3, "n")]
    assert only_new == [("src/c.py", 9, "x")]
