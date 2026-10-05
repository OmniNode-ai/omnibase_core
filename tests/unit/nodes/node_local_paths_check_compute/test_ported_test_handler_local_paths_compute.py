# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Port the retired local-paths handler's scan assertions to the typed node."""

from __future__ import annotations

import pytest

from omnibase_core.models.nodes.local_paths_check.model_local_paths_check_input import (
    ModelLocalPathsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_local_paths_check_compute.handler import (
    NodeLocalPathsCheckCompute,
)
from omnibase_core.validation.validator_local_paths import (
    _LOCAL_PATH_PATTERNS,
    _SUPPRESSION_MARKER,
)

pytestmark = pytest.mark.unit

_VIOLATION_LINES: tuple[str, ...] = (
    '"/' + 'Users/alice/Code/project"  # comment',
    'Path("/' + 'Volumes/DISK/Code/worktrees")',
    'CACHE = "/' + 'home/runner/.cache/onex"',
    'WIN = "C:' + r'\Users\bob\Documents"',
    'WIN = "c:/' + 'Users/bob/Documents"',
    'subprocess.run(["cp", "/' + 'Users/dev/file", "d"])',
    'import os\nB = "/' + 'Users/ci/workspace/repo"\n',
)
_CLEAN_LINES: tuple[str, ...] = (
    'CONFIG = Path(__file__).parent / "c.yaml"',
    'ROOT = Path(os.environ["OMNI_HOME"])',
    'D = "/' + 'Users/jonah/Code/omni_home"  # local-path' + "-ok",
    '"/node_modules/some/pkg/index.js"',
    'BREW = "/usr/local/bin/python3.13"',
    'HOST = "/homelab/data/cache"',
    'NOTE = "see /Users for the home dirs"',
    'API = "https://example.com/users/alice/x"',
)


def _scan(source: str, path: str = "<input>") -> ModelValidationReport:
    return NodeLocalPathsCheckCompute().handle(
        ModelLocalPathsCheckInput(files=[ModelSourceFile(path=path, source=source)])
    )


def _ground_truth_flags(source: str) -> bool:
    """Retain the old test's oracle from the surviving hand-authored validator."""
    for line in source.splitlines():
        if _SUPPRESSION_MARKER in line:
            continue
        for _name, pattern in _LOCAL_PATH_PATTERNS:
            if pattern.search(line):
                return True
    return False


@pytest.mark.parametrize("source", _VIOLATION_LINES)
def test_scan_source_flags_every_violation(source: str) -> None:
    report = _scan(source, path="t.py")
    assert report.overall_status == "FAIL"
    assert len(report.findings) >= 1
    assert _ground_truth_flags(source) is True


@pytest.mark.parametrize("source", _CLEAN_LINES)
def test_scan_source_passes_every_clean(source: str) -> None:
    report = _scan(source, path="t.py")
    assert report.overall_status == "PASS"
    assert report.findings == ()
    assert _ground_truth_flags(source) is False


@pytest.mark.parametrize("source", [*_VIOLATION_LINES, *_CLEAN_LINES])
def test_equivalence_with_ground_truth(source: str) -> None:
    compute_flags = _scan(source).overall_status == "FAIL"
    assert compute_flags == _ground_truth_flags(source), (
        f"COMPUTE/ground-truth disagree on {source!r}: "
        f"compute={compute_flags} ground_truth={_ground_truth_flags(source)}"
    )


def test_findings_are_stably_ordered() -> None:
    source = '"/' + 'Users/a/x/"\n"/' + 'Volumes/D/y/"'
    findings = _scan(source).findings
    assert [finding.location for finding in findings] == ["<input>:1", "<input>:2"]


def test_suppression_marker_suppresses_line() -> None:
    source = 'X = "/' + 'Users/jonah/x/"  # local-path' + "-ok"
    assert _scan(source).overall_status == "PASS"


def test_handler_returns_compute_result_over_envelope() -> None:
    """Preserve the scan verdict; envelope kind and ID have no report equivalent."""
    report = _scan('X = "/' + 'Users/jonah/x/"', path="t.py")
    assert report is not None
    assert report.overall_status == "FAIL"
    assert report.findings[0].location == "t.py:1"
