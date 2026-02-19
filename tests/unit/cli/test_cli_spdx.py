# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for cli_spdx.py core logic.

Tests cover:
- _strip_existing_spdx: shebang preservation, encoding line preservation,
  bare '#' separator removal, YAML '---' marker handling, remnant block removal
- _remove_body_spdx_blocks: stale SPDX blocks embedded in file body
- _fix_file_content: correct header insertion for all file types
- _has_correct_header / _validate_file: detection of valid vs. invalid headers
- validate_files: directory scanning, sorted deduplication, 0-vs-1 return value
- CLI: --dry-run, --check, --verbose flags via CliRunner
"""

from __future__ import annotations

import os
import pathlib

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_spdx import (
    SPDX_COPYRIGHT_LINE,
    SPDX_LICENSE_LINE,
    _fix_file_content,
    _has_correct_header,
    _remove_body_spdx_blocks,
    _strip_existing_spdx,
    _validate_file,
    spdx,
    validate_files,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

_CANONICAL_HEADER = f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n"


# ---------------------------------------------------------------------------
# _strip_existing_spdx
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStripExistingSpdx:
    """Tests for _strip_existing_spdx."""

    def test_strips_two_line_spdx_header(self) -> None:
        """Two-line copyright + license header is removed."""
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "def foo(): pass\n",
        ]
        result = _strip_existing_spdx(lines)
        assert result == ["def foo(): pass\n"]

    def test_preserves_shebang_before_header(self) -> None:
        """Shebang line is kept; SPDX lines that follow are removed."""
        lines = [
            "#!/usr/bin/env python3\n",
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "import sys\n",
        ]
        result = _strip_existing_spdx(lines)
        assert result[0] == "#!/usr/bin/env python3\n"
        assert "import sys\n" in result
        # SPDX lines must be gone
        assert not any(SPDX_LICENSE_LINE in ln for ln in result)

    def test_preserves_encoding_line_before_header(self) -> None:
        """Encoding declaration is kept; SPDX lines that follow are removed."""
        lines = [
            "# -*- coding: utf-8 -*-\n",
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "x = 1\n",
        ]
        result = _strip_existing_spdx(lines)
        assert result[0] == "# -*- coding: utf-8 -*-\n"
        assert not any(SPDX_COPYRIGHT_LINE in ln for ln in result)

    def test_strips_three_line_variant_with_bare_hash_separator(self) -> None:
        """Three-line header (copyright / bare '#' / license) is fully removed."""
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            "#\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "pass\n",
        ]
        result = _strip_existing_spdx(lines)
        assert result == ["pass\n"]

    def test_strips_remnant_block_after_blank_line(self) -> None:
        """A stale SPDX block separated by a blank line from the main block is removed."""
        # Simulate partial strip that left a remnant after a blank
        old_license = "# SPDX-License-Identifier: Apache-2.0\n"
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            old_license,
            "\n",
            "code = True\n",
        ]
        result = _strip_existing_spdx(lines)
        assert not any("Apache" in ln for ln in result)
        assert "code = True\n" in result

    def test_empty_file_returns_empty(self) -> None:
        """Empty input returns empty output."""
        assert _strip_existing_spdx([]) == []

    def test_no_spdx_lines_unchanged(self) -> None:
        """File with no SPDX markers is returned unchanged."""
        lines = ["# Regular comment\n", "x = 1\n"]
        result = _strip_existing_spdx(lines)
        assert result == lines


# ---------------------------------------------------------------------------
# _remove_body_spdx_blocks
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRemoveBodySpdxBlocks:
    """Tests for _remove_body_spdx_blocks."""

    def test_removes_stale_apache_block_in_body(self) -> None:
        """A non-canonical SPDX block embedded in the body is removed."""
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "import os\n",
            "\n",
            "# SPDX-FileCopyrightText: 2020 Old Corp.\n",
            "#\n",
            "# SPDX-License-Identifier: Apache-2.0\n",
            "\n",
            "def main(): pass\n",
        ]
        result = _remove_body_spdx_blocks(lines)
        assert not any("Apache-2.0" in ln for ln in result)
        assert not any("Old Corp" in ln for ln in result)
        assert "import os\n" in result
        assert "def main(): pass\n" in result

    def test_does_not_remove_canonical_license_line(self) -> None:
        """A standalone canonical SPDX-License-Identifier line is not removed."""
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "x = 1\n",
        ]
        result = _remove_body_spdx_blocks(lines)
        assert f"{SPDX_LICENSE_LINE}\n" in result

    def test_removes_preceding_blank_line_with_stale_block(self) -> None:
        """The blank line immediately before a stale body block is also removed."""
        lines = [
            "import sys\n",
            "\n",  # This blank should be eaten
            "# SPDX-FileCopyrightText: 2020 Bad.\n",
            "# SPDX-License-Identifier: GPL-3.0\n",
            "\n",
            "def run(): pass\n",
        ]
        result = _remove_body_spdx_blocks(lines)
        # Blank line before the block and the block itself are gone
        assert not any("GPL" in ln for ln in result)
        # Remaining content is preserved
        assert "import sys\n" in result
        assert "def run(): pass\n" in result

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty output."""
        assert _remove_body_spdx_blocks([]) == []


# ---------------------------------------------------------------------------
# _fix_file_content  (covers _build_spdx_header insertion logic)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixFileContent:
    """Tests for _fix_file_content."""

    def test_adds_header_to_plain_python_file(self) -> None:
        """A plain Python file without a header gets the canonical header."""
        content = "def foo(): pass\n"
        result = _fix_file_content(content)
        assert result.startswith(_CANONICAL_HEADER)

    def test_idempotent_on_already_correct_file(self) -> None:
        """A file that already has the correct header is returned unchanged."""
        content = f"{_CANONICAL_HEADER}\ndef foo(): pass\n"
        assert _fix_file_content(content) == content

    def test_replaces_wrong_license_identifier(self) -> None:
        """A file with a non-MIT SPDX identifier gets the canonical header."""
        content = (
            f"{SPDX_COPYRIGHT_LINE}\n# SPDX-License-Identifier: Apache-2.0\n\nx = 1\n"
        )
        result = _fix_file_content(content)
        assert SPDX_LICENSE_LINE in result
        assert "Apache-2.0" not in result

    def test_yaml_file_no_blank_before_document_marker(self) -> None:
        """YAML files with '---' get header inserted without a blank separator."""
        content = "---\nkey: value\n"
        result = _fix_file_content(content)
        lines = result.splitlines()
        assert lines[0] == SPDX_COPYRIGHT_LINE
        assert lines[1] == SPDX_LICENSE_LINE
        assert lines[2] == "---"

    def test_shebang_stays_on_first_line(self) -> None:
        """Shebang is preserved as the first line; header follows immediately."""
        content = "#!/usr/bin/env python3\ndef main(): pass\n"
        result = _fix_file_content(content)
        lines = result.splitlines()
        assert lines[0] == "#!/usr/bin/env python3"
        assert lines[1] == SPDX_COPYRIGHT_LINE
        assert lines[2] == SPDX_LICENSE_LINE

    def test_empty_file_gets_header(self) -> None:
        """An empty file gets just the SPDX header."""
        result = _fix_file_content("")
        assert result == _CANONICAL_HEADER

    def test_bypass_marker_leaves_file_unchanged(self) -> None:
        """A file with the spdx-skip bypass marker is not modified."""
        content = "# spdx-skip: third-party file\nx = 1\n"
        assert _fix_file_content(content) == content

    def test_blank_separator_added_between_header_and_content(self) -> None:
        """A blank line separates the header from the first content line."""
        content = "x = 1\n"
        result = _fix_file_content(content)
        lines = result.splitlines()
        assert lines[0] == SPDX_COPYRIGHT_LINE
        assert lines[1] == SPDX_LICENSE_LINE
        assert lines[2] == ""
        assert lines[3] == "x = 1"


# ---------------------------------------------------------------------------
# _has_correct_header
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHasCorrectHeader:
    """Tests for _has_correct_header."""

    def test_returns_true_for_canonical_header(self) -> None:
        lines = [f"{SPDX_COPYRIGHT_LINE}\n", f"{SPDX_LICENSE_LINE}\n", "\n", "x=1\n"]
        assert _has_correct_header(lines) is True

    def test_returns_false_when_missing_copyright(self) -> None:
        lines = [f"{SPDX_LICENSE_LINE}\n", "\n", "x=1\n"]
        assert _has_correct_header(lines) is False

    def test_returns_false_when_wrong_license(self) -> None:
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            "# SPDX-License-Identifier: GPL-3.0\n",
            "\n",
        ]
        assert _has_correct_header(lines) is False

    def test_returns_false_when_stale_license_line_in_body(self) -> None:
        """Even if the header is correct, a stale license line in the body fails."""
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "# SPDX-License-Identifier: Apache-2.0\n",
        ]
        assert _has_correct_header(lines) is False

    def test_returns_true_with_shebang_before_header(self) -> None:
        lines = [
            "#!/usr/bin/env bash\n",
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
        ]
        assert _has_correct_header(lines) is True


# ---------------------------------------------------------------------------
# _validate_file  (via tmp_path)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFile:
    """Tests for _validate_file using real temporary files."""

    def test_valid_file_returns_none(self, tmp_path: pathlib.Path) -> None:
        """A file with the canonical header passes validation."""
        f = tmp_path / "ok.py"
        f.write_text(f"{_CANONICAL_HEADER}\ndef foo(): pass\n", encoding="utf-8")
        assert _validate_file(f) is None

    def test_missing_header_returns_error(self, tmp_path: pathlib.Path) -> None:
        """A file without any SPDX header returns an error message."""
        f = tmp_path / "no_header.py"
        f.write_text("def foo(): pass\n", encoding="utf-8")
        result = _validate_file(f)
        assert result is not None
        assert "Expected" in result or "Missing" in result

    def test_wrong_license_returns_error(self, tmp_path: pathlib.Path) -> None:
        """A file with an Apache license returns an error message."""
        f = tmp_path / "wrong.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n# SPDX-License-Identifier: Apache-2.0\n\nx=1\n",
            encoding="utf-8",
        )
        result = _validate_file(f)
        assert result is not None

    def test_bypass_marker_skips_validation(self, tmp_path: pathlib.Path) -> None:
        """A file with spdx-skip bypass marker returns None (skipped)."""
        f = tmp_path / "skip.py"
        f.write_text("# spdx-skip: vendored\nx = 1\n", encoding="utf-8")
        assert _validate_file(f) is None

    def test_empty_file_returns_error(self, tmp_path: pathlib.Path) -> None:
        """An empty file returns an error about missing header."""
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        result = _validate_file(f)
        assert result is not None
        assert "empty" in result.lower() or "header" in result.lower()

    def test_stale_license_in_body_returns_error(self, tmp_path: pathlib.Path) -> None:
        """A file with a correct header but stale license in the body fails."""
        f = tmp_path / "stale.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\n"
            "# SPDX-License-Identifier: Apache-2.0\n",
            encoding="utf-8",
        )
        result = _validate_file(f)
        assert result is not None
        assert "Stale" in result or "stale" in result


# ---------------------------------------------------------------------------
# validate_files  (public function: directory scanning, dedup, return codes)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFiles:
    """Tests for the validate_files() public function."""

    def test_returns_zero_when_all_files_valid(self, tmp_path: pathlib.Path) -> None:
        """Returns 0 when every eligible file has a correct SPDX header."""
        f = tmp_path / "good.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\nx = 1\n", encoding="utf-8"
        )
        assert validate_files([str(tmp_path)]) == 0

    def test_returns_one_when_violation_found(self, tmp_path: pathlib.Path) -> None:
        """Returns 1 when at least one eligible file lacks a correct header."""
        f = tmp_path / "bad.py"
        f.write_text("x = 1\n", encoding="utf-8")
        assert validate_files([str(tmp_path)]) == 1

    def test_directory_scanning_discovers_nested_files(
        self, tmp_path: pathlib.Path
    ) -> None:
        """_discover_files is invoked for directory args and finds nested files."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        good = sub / "ok.py"
        good.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\npass\n", encoding="utf-8"
        )
        bad = sub / "missing.py"
        bad.write_text("pass\n", encoding="utf-8")
        # Should detect the violation in the nested file
        assert validate_files([str(tmp_path)]) == 1

    def test_deduplication_does_not_double_count(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Passing the same file twice reports the violation exactly once."""
        f = tmp_path / "dup.py"
        f.write_text("x = 1\n", encoding="utf-8")
        # Both args refer to the same file; validate_files deduplicates the
        # list so the file is only validated once.
        result = validate_files([str(f), str(f)])
        assert result == 1
        captured = capsys.readouterr()
        # The violation message for this one file should appear exactly once.
        assert captured.out.count(str(f)) == 1

    def test_empty_file_list_defaults_to_cwd_scan(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Passing an empty list causes validate_files to scan the CWD."""
        monkeypatch.chdir(tmp_path)
        good = tmp_path / "fine.py"
        good.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\npass\n", encoding="utf-8"
        )
        assert validate_files([]) == 0

    def test_nonexistent_path_prints_warning_and_returns_zero(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A path that does not exist emits a warning but does not crash."""
        missing = str(tmp_path / "does_not_exist.py")
        result = validate_files([missing])
        assert result == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "Warning" in captured.out

    def test_ineligible_file_is_skipped(self, tmp_path: pathlib.Path) -> None:
        """A file with an extension not in INCLUDED_EXTENSIONS is silently skipped."""
        f = tmp_path / "binary.dat"
        f.write_text("no header needed\n", encoding="utf-8")
        assert validate_files([str(f)]) == 0


# ---------------------------------------------------------------------------
# CLI integration tests via CliRunner
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCLIFix:
    """Click CLI tests for `onex spdx fix` subcommand flags."""

    def test_dry_run_reports_needs_fix_without_writing(
        self, tmp_path: pathlib.Path
    ) -> None:
        """--dry-run prints 'NEEDS FIX' but does not modify the file."""
        f = tmp_path / "unfixed.py"
        original = "x = 1\n"
        f.write_text(original, encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--dry-run", str(tmp_path)])
        assert result.exit_code == 0
        assert "NEEDS FIX" in result.output
        # File must be unchanged
        assert f.read_text(encoding="utf-8") == original

    def test_check_exits_nonzero_when_files_need_fix(
        self, tmp_path: pathlib.Path
    ) -> None:
        """--check exits non-zero when files are missing headers."""
        f = tmp_path / "bad.py"
        f.write_text("x = 1\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--check", str(tmp_path)])
        assert result.exit_code != 0

    def test_check_exits_zero_when_all_files_correct(
        self, tmp_path: pathlib.Path
    ) -> None:
        """--check exits 0 when every eligible file already has a correct header."""
        f = tmp_path / "ok.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\nx = 1\n", encoding="utf-8"
        )
        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--check", str(tmp_path)])
        assert result.exit_code == 0

    @pytest.mark.skipif(os.getuid() == 0, reason="chmod is bypassed as root")
    def test_check_exits_nonzero_on_error_count_with_zero_modified(
        self, tmp_path: pathlib.Path
    ) -> None:
        """--check exits non-zero when error_count > 0 even if modified_count == 0.

        Regression test: previously, errors were only reported after the summary
        block; if modified_count was 0 the command could silently exit 0 despite
        real I/O errors encountered during the scan.
        """
        f = tmp_path / "unreadable.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\nx = 1\n", encoding="utf-8"
        )
        f.chmod(0o000)  # Make file unreadable to trigger an OSError

        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--check", str(tmp_path)])

        # Restore permissions so pytest cleanup can remove the temp dir
        f.chmod(0o644)

        # With an unreadable file: modified_count == 0 but error_count > 0 — must
        # exit non-zero (the bug was that this path exited 0).
        assert result.exit_code != 0

    def test_verbose_flag_prints_per_file_status(self, tmp_path: pathlib.Path) -> None:
        """--verbose emits per-file status lines alongside the summary."""
        f = tmp_path / "verbose_ok.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\nx = 1\n", encoding="utf-8"
        )
        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--verbose", str(tmp_path)])
        assert result.exit_code == 0
        # Verbose mode reports at least the scan line and a per-file status
        assert "Scanning" in result.output or "OK" in result.output

    def test_fix_without_flags_writes_header(self, tmp_path: pathlib.Path) -> None:
        """Running fix without flags actually rewrites missing-header files."""
        f = tmp_path / "needs_header.py"
        f.write_text("x = 1\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", str(tmp_path)])
        assert result.exit_code == 0
        updated = f.read_text(encoding="utf-8")
        assert updated.startswith(SPDX_COPYRIGHT_LINE)


@pytest.mark.unit
class TestCLIValidate:
    """Click CLI tests for `onex spdx validate` subcommand."""

    def test_validate_exits_zero_for_valid_file(self, tmp_path: pathlib.Path) -> None:
        """validate exits 0 when the provided file has the correct header."""
        f = tmp_path / "valid.py"
        f.write_text(
            f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\nx = 1\n", encoding="utf-8"
        )
        runner = CliRunner()
        result = runner.invoke(spdx, ["validate", str(f)])
        assert result.exit_code == 0

    def test_validate_exits_nonzero_for_invalid_file(
        self, tmp_path: pathlib.Path
    ) -> None:
        """validate exits non-zero when a file is missing its header."""
        f = tmp_path / "invalid.py"
        f.write_text("x = 1\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(spdx, ["validate", str(f)])
        assert result.exit_code != 0
