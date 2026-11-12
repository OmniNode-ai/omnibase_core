# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-23845: after a release, report whether the tag, the package metadata and
the files PyPI serves agree (report only).

The fixtures are recorded from the published omnibase-core 0.47.72 release
(read 2026-11-12): its ``SHA256SUMS.txt`` GitHub Release asset and the PyPI JSON
for that version, trimmed to the fields the report reads. Each case writes them
to disk and runs the gather EFFECT over the files, then the pure COMPUTE node,
the way the release job's runtime does.

Failure modes this file must catch:

* a file PyPI serves has a different sha256 from the file the release built;
* the built wheel's METADATA ``Version`` is not the tag's version;
* PyPI reports another version for the release;
* a file the release built is missing from what PyPI serves;
* PyPI cannot be read, which must read UNKNOWN and never MISMATCH or AGREE;
* the runtime takes its summary path from an argument, never the environment
  (the typed-bootstrap boundary, OMN-17744).
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_RUNTIME = (
    "omnibase_core.nodes.node_release_consistency_check_compute."
    "runtime_release_consistency_check"
)

_TAG = "v0.47.72"
_WHEEL = "omnibase_core-0.47.72-py3-none-any.whl"
_SDIST = "omnibase_core-0.47.72.tar.gz"
# The v0.47.72 GitHub Release's SHA256SUMS.txt asset, as the release job wrote
# it (gh release download v0.47.72 --pattern SHA256SUMS.txt, 2026-11-12). PyPI's
# JSON for 0.47.72 served the same two sha256 values that day.
_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "release_consistency"
    / "v0_47_72"
    / "SHA256SUMS.txt"
)
_SUMS = _FIXTURE.read_text(encoding="utf-8")
_RECORDED = {
    Path(path).name: digest
    for digest, path in (line.split() for line in _SUMS.splitlines() if line)
}
_WHEEL_SHA = _RECORDED[_WHEEL]
_SDIST_SHA = _RECORDED[_SDIST]

# https://pypi.org/pypi/omnibase-core/0.47.72/json, trimmed.
_PYPI: dict[str, object] = {
    "info": {"version": "0.47.72"},
    "urls": [
        {
            "filename": _WHEEL,
            "packagetype": "bdist_wheel",
            "digests": {"sha256": _WHEEL_SHA},
        },
        {
            "filename": _SDIST,
            "packagetype": "sdist",
            "digests": {"sha256": _SDIST_SHA},
        },
    ],
}


def _write_dist(tmp_path: Path, *, wheel_version: str | None) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "SHA256SUMS.txt").write_text(_SUMS)
    if wheel_version is not None:
        with zipfile.ZipFile(dist / _WHEEL, "w") as wheel:
            wheel.writestr(
                "omnibase_core-0.47.72.dist-info/METADATA",
                "Metadata-Version: 2.4\nName: omnibase-core\n"
                f"Version: {wheel_version}\n",
            )
    return dist


def _write_pypi(tmp_path: Path, pypi: object) -> Path:
    path = tmp_path / "pypi.json"
    path.write_text(json.dumps(pypi))
    return path


def _report(
    tmp_path: Path,
    *,
    pypi: object | None = _PYPI,
    wheel_version: str | None = "0.47.72",
    pypi_text: str | None = None,
) -> tuple[str, int, list[str]]:
    """Gather the recorded files, then judge them: verdict, exit code, lines."""
    from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_gather_input import (
        ModelReleaseConsistencyGatherInput,
    )
    from omnibase_core.nodes.node_release_consistency_check_compute.handler import (
        NodeReleaseConsistencyCheckCompute,
    )
    from omnibase_core.nodes.node_release_consistency_gather_effect.handler import (
        NodeReleaseConsistencyGatherEffect,
    )

    dist = _write_dist(tmp_path, wheel_version=wheel_version)
    pypi_path: str | None = None
    if pypi_text is not None:
        raw = tmp_path / "pypi.json"
        raw.write_text(pypi_text)
        pypi_path = str(raw)
    elif pypi is not None:
        pypi_path = str(_write_pypi(tmp_path, pypi))
    facts = NodeReleaseConsistencyGatherEffect().handle(
        ModelReleaseConsistencyGatherInput(
            tag=_TAG, dist_dir=str(dist), pypi_json_path=pypi_path
        )
    )
    report = NodeReleaseConsistencyCheckCompute().handle(facts)
    return report.verdict, report.exit_code, list(report.lines)


def test_agree_when_every_served_file_and_version_matches(tmp_path: Path) -> None:
    verdict, code, lines = _report(tmp_path)
    assert verdict == "AGREE", lines
    assert code == 0
    text = "\n".join(lines)
    assert f"AGREE {_WHEEL} sha256 {_WHEEL_SHA}" in text
    assert f"AGREE {_SDIST} sha256 {_SDIST_SHA}" in text
    assert "MISMATCH" not in text and "UNKNOWN" not in text


def test_mismatch_when_a_served_file_has_another_sha256(tmp_path: Path) -> None:
    pypi = copy.deepcopy(_PYPI)
    urls = pypi["urls"]
    assert isinstance(urls, list)
    urls[1]["digests"]["sha256"] = "0" * 64
    verdict, code, lines = _report(tmp_path, pypi=pypi)
    assert verdict == "MISMATCH"
    assert code == 1
    text = "\n".join(lines)
    assert f"MISMATCH {_SDIST}" in text
    assert f"AGREE {_WHEEL}" in text


def test_mismatch_when_the_wheel_metadata_version_is_not_the_tag(
    tmp_path: Path,
) -> None:
    verdict, code, lines = _report(tmp_path, wheel_version="0.47.71")
    assert verdict == "MISMATCH"
    assert code == 1
    assert any(
        "MISMATCH" in line and "metadata" in line.lower() and "0.47.71" in line
        for line in lines
    ), lines


def test_mismatch_when_pypi_reports_another_version(tmp_path: Path) -> None:
    pypi = copy.deepcopy(_PYPI)
    pypi["info"] = {"version": "0.47.70"}
    verdict, _, lines = _report(tmp_path, pypi=pypi)
    assert verdict == "MISMATCH"
    assert any("MISMATCH" in line and "0.47.70" in line for line in lines), lines


def test_mismatch_when_a_built_file_is_missing_from_pypi(tmp_path: Path) -> None:
    pypi = copy.deepcopy(_PYPI)
    urls = pypi["urls"]
    assert isinstance(urls, list)
    del urls[1]
    verdict, code, lines = _report(tmp_path, pypi=pypi)
    assert verdict == "MISMATCH"
    assert code == 1
    assert any(
        "MISMATCH" in line and _SDIST in line and "missing" in line.lower()
        for line in lines
    ), lines


def test_unknown_when_pypi_could_not_be_read(tmp_path: Path) -> None:
    verdict, code, lines = _report(tmp_path, pypi=None)
    assert verdict == "UNKNOWN"
    assert code == 2
    text = "\n".join(lines)
    assert "MISMATCH" not in text and f"AGREE {_WHEEL}" not in text


def test_unknown_when_the_pypi_body_is_not_json(tmp_path: Path) -> None:
    verdict, code, lines = _report(tmp_path, pypi_text="<html>503</html>")
    assert verdict == "UNKNOWN", lines
    assert code == 2
    assert "MISMATCH" not in "\n".join(lines)


def _run_cli(
    tmp_path: Path, *, wheel_version: str, pypi: object | None
) -> tuple[subprocess.CompletedProcess[str], Path]:
    dist = _write_dist(tmp_path, wheel_version=wheel_version)
    args = [sys.executable, "-m", _RUNTIME, "--tag", _TAG, "--dist", str(dist)]
    if pypi is not None:
        args += ["--pypi-json", str(_write_pypi(tmp_path, pypi))]
    summary = tmp_path / "summary.md"
    args += ["--summary-path", str(summary)]
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc, summary


def test_cli_reads_the_wheel_metadata_and_writes_the_summary_it_is_given(
    tmp_path: Path,
) -> None:
    proc, summary = _run_cli(tmp_path, wheel_version="0.47.72", pypi=_PYPI)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = summary.read_text()
    assert _TAG in text
    for name, sha in ((_WHEEL, _WHEEL_SHA), (_SDIST, _SDIST_SHA)):
        assert f"AGREE {name} sha256 {sha}" in proc.stdout
        assert f"AGREE {name} sha256 {sha}" in text
    assert "wheel metadata Version 0.47.72" in text
    assert "VERDICT AGREE" in proc.stdout


def test_cli_reports_a_wheel_built_with_another_version(tmp_path: Path) -> None:
    proc, _ = _run_cli(tmp_path, wheel_version="0.47.71", pypi=_PYPI)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "MISMATCH" in proc.stdout and "0.47.71" in proc.stdout


def test_cli_without_pypi_json_reads_unknown(tmp_path: Path) -> None:
    proc, _ = _run_cli(tmp_path, wheel_version="0.47.72", pypi=None)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "UNKNOWN" in proc.stdout and "MISMATCH" not in proc.stdout
