# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI scan-scope regression tests for the three no-* validators (OMN-14082).

Guards the argv false-green bug: the CI invocation `<script> --report` (no
filenames) used to resolve an EMPTY file set and print `PASS` having scanned
zero files. These tests prove the fixed `main()`:

* scans the intended ``src/`` + ``scripts/`` tree on the report-mode CI
  invocation (files_scanned > 0, not the old zero);
* flags a planted violation and passes on clean input;
* FAILS CLOSED when the resolved scan scope is empty (exit 1, never a silent
  exit-0 PASS) — even in `--report` mode;
* preserves the pre-commit staged-file path and fails closed when the listed
  paths do not exist (the generalized form of the `--report`-parsed-as-a-file
  bug).
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

import validate_no_except_swallow as m_except
import validate_no_import_none_fallback as m_import
import validate_no_none_guard_publish as m_none

# (module, planted-violation source, clean source) per validator.
CASES = {
    "no_except_swallow": (
        m_except,
        'try:\n    do()\nexcept Exception:\n    logger.warning("swallowed")\n',
        'try:\n    do()\nexcept ValueError:\n    logger.warning("handled")\n',
    ),
    "no_import_none_fallback": (
        m_import,
        "try:\n    from foo import Bar\nexcept ImportError:\n    Bar = None\n",
        "try:\n    from foo import Bar\nexcept ImportError:\n    raise\n",
    ),
    "no_none_guard_publish": (
        m_none,
        'def f(event_bus):\n    if event_bus is not None:\n        event_bus.publish("x")\n',
        "def f(x):\n    if x is not None:\n        do_something(x)\n",
    ),
}

CASE_IDS = list(CASES)
CASE_VALUES = list(CASES.values())


def _plant(repo_root: Path, source: str) -> Path:
    pkg = repo_root / "src" / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    f = pkg / "subject.py"
    f.write_text(source, encoding="utf-8")
    return f


@pytest.mark.parametrize(("mod", "bad", "clean"), CASE_VALUES, ids=CASE_IDS)
class TestScanScopeOMN14082:
    def test_default_scan_flags_planted_violation(
        self, mod, bad, clean, tmp_path, capsys
    ):
        """Enforce mode (no --report) flags a planted in-scope violation."""
        _plant(tmp_path, bad)
        rc = mod.main([], repo_root=tmp_path)
        out = capsys.readouterr().out
        assert rc == 1, out
        assert "FAIL" in out
        assert "subject.py" in out

    def test_default_scan_passes_on_clean_input(
        self, mod, bad, clean, tmp_path, capsys
    ):
        """Enforce mode passes when the in-scope file is clean."""
        _plant(tmp_path, clean)
        rc = mod.main([], repo_root=tmp_path)
        out = capsys.readouterr().out
        assert rc == 0, out
        assert "PASS" in out

    def test_report_mode_scans_nonzero_files(self, mod, bad, clean, tmp_path, capsys):
        """Regression: `--report` with no filenames scans the tree, not zero files.

        Before OMN-14082 the `--report` token was parsed as a file path and the
        scan resolved zero files, printing a false-green PASS. The fixed main
        must self-report a non-zero scanned count and still surface the planted
        violation (report mode keeps exit 0 for the staged rollout).
        """
        _plant(tmp_path, bad)
        rc = mod.main(["--report"], repo_root=tmp_path)
        out = capsys.readouterr().out
        assert rc == 0, out  # report mode: violation is non-fatal
        assert "FAIL" in out  # ...but the violation is surfaced
        m = re.search(r"scanned (\d+) file", out)
        assert m is not None, out
        assert int(m.group(1)) >= 1, out  # proves >0 files scanned (bug fixed)

    def test_empty_scope_fails_closed_even_in_report_mode(
        self, mod, bad, clean, tmp_path, capsys
    ):
        """A required gate that resolves zero files must ERROR, not exit-0 PASS."""
        empty_root = tmp_path / "empty"
        empty_root.mkdir()
        rc = mod.main(["--report"], repo_root=empty_root)
        out = capsys.readouterr().out
        assert rc == 1, out
        assert "empty scan scope" in out

    def test_staged_file_mode_flags_and_passes(self, mod, bad, clean, tmp_path, capsys):
        """Pre-commit staged-file path: explicit file list is scanned correctly."""
        bad_f = tmp_path / "bad.py"
        bad_f.write_text(bad, encoding="utf-8")
        rc_bad = mod.main(["--report", str(bad_f)])
        out_bad = capsys.readouterr().out
        assert rc_bad == 0, out_bad
        assert "FAIL" in out_bad, out_bad

        clean_f = tmp_path / "ok.py"
        clean_f.write_text(clean, encoding="utf-8")
        rc_clean = mod.main([str(clean_f)])
        out_clean = capsys.readouterr().out
        assert rc_clean == 0, out_clean
        assert "PASS" in out_clean

    def test_staged_file_mode_nonexistent_paths_fail_closed(
        self, mod, bad, clean, tmp_path, capsys
    ):
        """Listed paths that don't exist -> fail closed (the flag-as-file bug class)."""
        rc = mod.main(["--report", str(tmp_path / "does_not_exist.py")])
        out = capsys.readouterr().out
        assert rc == 1, out
        assert "none exist as files" in out
