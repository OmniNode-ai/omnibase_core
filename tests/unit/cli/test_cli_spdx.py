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
from unittest import mock

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_spdx import (
    SPDX_COPYRIGHT_LINE,
    SPDX_LICENSE_LINE,
    _fix_file_content,
    _has_correct_header,
    _is_encoding,
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

    def test_lone_copyright_comment_is_preserved(self) -> None:
        """A lone SPDX-FileCopyrightText comment without a license identifier is NOT removed.

        This is intentional behaviour: a standalone copyright notice (no
        SPDX-License-Identifier line in the same block) may be a legitimate
        third-party attribution and must be left in place.  _remove_body_spdx_blocks
        only removes a block when has_stale=True (i.e. a non-canonical license
        identifier is present).
        """
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            "import os\n",
            "\n",
            "# SPDX-FileCopyrightText: 2020 OldCorp.\n",
            "\n",
            "def main(): pass\n",
        ]
        result = _remove_body_spdx_blocks(lines)
        # The lone copyright line must still be present
        assert any("OldCorp" in ln for ln in result)
        # Other content is also preserved
        assert "import os\n" in result
        assert "def main(): pass\n" in result

    def test_lone_copyright_not_removed_by_fix_file_content(self) -> None:
        """_fix_file_content does not remove a lone SPDX-FileCopyrightText body comment.

        Verifies the same intentional behaviour end-to-end: a file body that
        contains only a copyright notice (no license identifier) is left
        untouched by the full fix pipeline.
        """
        content = (
            f"{SPDX_COPYRIGHT_LINE}\n"
            f"{SPDX_LICENSE_LINE}\n"
            "\n"
            "import os\n"
            "\n"
            "# SPDX-FileCopyrightText: 2020 OldCorp.\n"
            "\n"
            "def main(): pass\n"
        )
        result = _fix_file_content(content)
        assert "OldCorp" in result

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty output."""
        assert _remove_body_spdx_blocks([]) == []


# ---------------------------------------------------------------------------
# _fix_file_content  (covers _fix_file_content insertion logic)
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

    def test_yaml_file_no_blank_before_document_marker(
        self, tmp_path: pathlib.Path
    ) -> None:
        """YAML files with '---' get header inserted without a blank separator."""
        content = "---\nkey: value\n"
        yaml_path = tmp_path / "config.yml"
        result = _fix_file_content(content, file_path=yaml_path)
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

    def test_shebang_without_newline_is_not_corrupted(self) -> None:
        """A shebang with no trailing newline is not concatenated with the header.

        When content is '#!/usr/bin/env python3' (no trailing newline),
        splitlines(keepends=True) returns a single element without a newline
        character.  Without the guard in _fix_file_content the SPDX header
        would be appended directly to the shebang, producing a corrupted line
        like '#!/usr/bin/env python3# SPDX-FileCopyrightText: ...'.
        """
        content = "#!/usr/bin/env python3"
        result = _fix_file_content(content)
        # The shebang must be followed by a newline — not by a '#' character
        assert result.startswith("#!/usr/bin/env python3\n"), (
            f"Shebang not terminated with newline. Got: {result!r}"
        )
        # The concatenated form must never appear
        assert "#!/usr/bin/env python3#" not in result, (
            f"Shebang was corrupted (concatenated with header). Got: {result!r}"
        )
        # The copyright line must appear as its own line (not glued to shebang)
        lines = result.splitlines()
        assert lines[0] == "#!/usr/bin/env python3"
        assert lines[1] == SPDX_COPYRIGHT_LINE
        assert lines[2] == SPDX_LICENSE_LINE

    def test_no_duplicate_header_when_non_spdx_comment_precedes_spdx_block(
        self,
    ) -> None:
        """_fix_file_content is idempotent when a non-SPDX comment precedes the SPDX block.

        Regression test for a duplicate-header bug: _has_any_spdx() returns
        True (finds SPDX markers in the header region) but
        _strip_existing_spdx() is a no-op because a regular comment line
        appears before the SPDX block, causing the stripper to exit before
        reaching the SPDX lines.  The fix must NOT insert a second header;
        the output must contain exactly one SPDX-FileCopyrightText line and
        exactly one SPDX-License-Identifier line.
        """
        content = (
            "# some regular comment\n"
            f"{SPDX_COPYRIGHT_LINE}\n"
            f"{SPDX_LICENSE_LINE}\n"
            "\n"
            "x = 1\n"
        )
        result = _fix_file_content(content)
        copyright_count = result.count("SPDX-FileCopyrightText:")
        license_count = result.count("SPDX-License-Identifier:")
        assert copyright_count == 1, (
            f"Expected exactly 1 SPDX-FileCopyrightText line, got {copyright_count}.\n"
            f"Output:\n{result!r}"
        )
        assert license_count == 1, (
            f"Expected exactly 1 SPDX-License-Identifier line, got {license_count}.\n"
            f"Output:\n{result!r}"
        )


# ---------------------------------------------------------------------------
# _is_encoding  (false-positive guard)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsEncoding:
    """Tests for _is_encoding to ensure it does not false-positive on non-comment lines."""

    # Lines that MUST return True (genuine PEP 263 encoding declarations)
    def test_true_for_emacs_style(self) -> None:
        assert _is_encoding("# -*- coding: utf-8 -*-") is True

    def test_true_for_plain_coding_colon(self) -> None:
        assert _is_encoding("# coding: utf-8") is True

    def test_true_for_coding_equals(self) -> None:
        assert _is_encoding("# coding=utf-8") is True

    # Lines that MUST return False (no leading `#`)
    def test_false_for_string_literal_with_coding(self) -> None:
        """A string value containing 'coding:' is not a PEP 263 declaration."""
        assert _is_encoding('x = "coding: utf-8"') is False

    def test_false_for_yaml_style_key(self) -> None:
        """A bare YAML key 'coding: utf-8' with no '#' is not an encoding comment."""
        assert _is_encoding("coding: utf-8") is False

    def test_false_for_indented_no_hash(self) -> None:
        """An indented assignment-style line with no '#' is not an encoding comment."""
        assert _is_encoding("  coding=utf-8") is False

    def test_false_for_spdx_copyright_line_containing_coding(self) -> None:
        """A comment with arbitrary text before 'coding' is not an encoding declaration.

        Regression test for the tightened _ENCODING_RE: the old regex used .*?
        (non-greedy wildcard) between '#' and 'coding', which would match a line
        like '# SPDX-FileCopyrightText: coding=ascii' as a PEP 263 encoding
        declaration.  The stricter regex requires only optional whitespace between
        '#' and 'coding', so non-whitespace text before 'coding' is rejected.
        """
        assert _is_encoding("# SPDX-FileCopyrightText: coding=ascii") is False


# ---------------------------------------------------------------------------
# _fix_file_content — CRLF line endings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixFileContentCRLF:
    """Tests documenting _fix_file_content behaviour with CRLF line endings.

    The function uses ``str.splitlines(keepends=True)`` which treats ``\\r\\n``
    as a single line ending. Injected SPDX header lines always use ``\\n``
    (Unix) endings regardless of the source file's line endings — the result
    is therefore a mixed-ending file.  This class documents that known behaviour
    so that any future change to normalise endings is detected immediately.
    """

    def test_crlf_file_gets_header_injected(self) -> None:
        """A CRLF file without a header receives the canonical SPDX header."""
        content = "x = 1\r\ndef foo(): pass\r\n"
        result = _fix_file_content(content)
        assert SPDX_COPYRIGHT_LINE in result
        assert SPDX_LICENSE_LINE in result

    def test_injected_header_lines_use_lf_endings(self) -> None:
        """Injected header lines use LF (\\n) endings; body lines retain CRLF.

        This documents the current mixed-ending behaviour.  If the
        implementation is changed to normalise line endings, update this test
        to match.
        """
        content = "x = 1\r\n"
        result = _fix_file_content(content)
        lines_raw = result.splitlines(keepends=True)
        # The first two lines are the injected SPDX lines — they should end
        # with plain \\n (not \\r\\n) under the current implementation.
        assert lines_raw[0].endswith("\n") and not lines_raw[0].endswith("\r\n"), (
            "Expected injected copyright line to use LF endings"
        )
        assert lines_raw[1].endswith("\n") and not lines_raw[1].endswith("\r\n"), (
            "Expected injected license line to use LF endings"
        )

    def test_crlf_body_lines_are_preserved(self) -> None:
        """Body lines from a CRLF file are passed through unchanged."""
        content = "x = 1\r\n"
        result = _fix_file_content(content)
        # The original body line must appear somewhere in the result intact.
        assert "x = 1\r\n" in result

    def test_yaml_crlf_no_blank_before_document_marker(
        self, tmp_path: pathlib.Path
    ) -> None:
        """YAML CRLF file: header inserted before '---' with no blank separator."""
        content = "---\r\nkey: value\r\n"
        yaml_path = tmp_path / "config.yml"
        result = _fix_file_content(content, file_path=yaml_path)
        lines = result.splitlines()
        assert lines[0] == SPDX_COPYRIGHT_LINE
        assert lines[1] == SPDX_LICENSE_LINE
        assert lines[2] == "---"


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

    def test_spdx_identifier_inside_docstring_causes_false_positive(self) -> None:
        # known limitation: plain-text scan cannot distinguish comments inside strings
        #
        # A '# SPDX-License-Identifier: MIT' line that appears literally inside a
        # triple-quoted docstring is indistinguishable from a real comment by the
        # plain-text body scan.  The scan therefore returns False even though the
        # canonical header is present and the second occurrence is not a real comment.
        # This test documents that known behaviour; the fix would require AST-based
        # parsing which is intentionally avoided for performance reasons.
        lines = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            '"""\n',
            "Example usage::\n",
            "\n",
            "    # SPDX-License-Identifier: MIT\n",
            '"""\n',
        ]
        # The scan sees the SPDX-License-Identifier line inside the docstring and,
        # because it matches the canonical line exactly, returns True here — but if
        # it were a *different* license identifier it would return False.  Test with
        # a non-canonical identifier to confirm the false-positive path:
        lines_noncanonical = [
            f"{SPDX_COPYRIGHT_LINE}\n",
            f"{SPDX_LICENSE_LINE}\n",
            "\n",
            '"""\n',
            "Example usage::\n",
            "\n",
            "    # SPDX-License-Identifier: Apache-2.0\n",
            '"""\n',
        ]
        assert _has_correct_header(lines_noncanonical) is False


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

    def test_ineligible_file_is_skipped(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A file with an extension not in INCLUDED_EXTENSIONS is skipped with a warning."""
        f = tmp_path / "binary.dat"
        f.write_text("no header needed\n", encoding="utf-8")
        result = validate_files([str(f)])
        assert result == 0
        captured = capsys.readouterr()
        assert "skipping ineligible file" in (captured.err + captured.out).lower()


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

    def test_check_takes_precedence_over_dry_run(self, tmp_path: pathlib.Path) -> None:
        """--check takes precedence over --dry-run when both flags are supplied.

        When both --check and --dry-run are passed to the fix command on files
        that need headers, the behaviour must match --check alone:
          - exits non-zero
          - reports files needing headers ("NEEDS FIX")
          - does NOT modify files on disk
          - does NOT emit "DRY RUN" summary language
        """
        f = tmp_path / "needs_header.py"
        original = "x = 1\n"
        f.write_text(original, encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--check", "--dry-run", str(tmp_path)])

        # --check semantics: exit non-zero when files need headers
        assert result.exit_code != 0
        # Per-file "NEEDS FIX" line is emitted (shared by both modes)
        assert "NEEDS FIX" in result.output
        # --check summary language, not dry-run language
        assert "DRY RUN" not in result.output
        # File must remain unmodified
        assert f.read_text(encoding="utf-8") == original

    @pytest.mark.skipif(os.getuid() == 0, reason="chmod is bypassed as root")
    def test_dry_run_exits_nonzero_on_error_count(self, tmp_path: pathlib.Path) -> None:
        """--dry-run exits non-zero when error_count > 0 (file cannot be read).

        Regression test: the bottom error guard in fix() fires for the dry-run
        path when a file raises OSError during read. Confirms exit_code != 0.
        """
        f = tmp_path / "unreadable.py"
        f.write_text("x = 1\n", encoding="utf-8")
        f.chmod(0o000)  # Make unreadable to trigger OSError on read

        runner = CliRunner()
        result = runner.invoke(spdx, ["fix", "--dry-run", str(tmp_path)])

        # Restore permissions so pytest cleanup can remove the temp dir
        f.chmod(0o644)

        assert result.exit_code != 0

    def test_fix_check_and_validate_agree_on_malformed_header(
        self, tmp_path: pathlib.Path
    ) -> None:
        """fix --check and validate both exit non-zero for a malformed SPDX block.

        Regression test for the contradiction where `fix --check` reported
        "Already OK" (exit 0) while `validate` reported an error (exit non-zero)
        on a file whose SPDX block is preceded by a non-SPDX comment, making the
        block un-normalizable.
        """
        f = tmp_path / "malformed.py"
        f.write_text(
            f"# some comment\n{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n\nx=1\n",
            encoding="utf-8",
        )

        runner = CliRunner()

        # fix --check must exit non-zero (file is broken, not "already OK")
        check_result = runner.invoke(spdx, ["fix", "--check", str(f)])
        assert check_result.exit_code != 0, (
            f"Expected fix --check to exit non-zero for malformed header, "
            f"got {check_result.exit_code}.\nOutput:\n{check_result.output}"
        )

        # validate must also exit non-zero for the same file
        validate_result = runner.invoke(spdx, ["validate", str(f)])
        assert validate_result.exit_code != 0, (
            f"Expected validate to exit non-zero for malformed header, "
            f"got {validate_result.exit_code}.\nOutput:\n{validate_result.output}"
        )

    def test_write_fail_does_not_inflate_modified_count(
        self, tmp_path: pathlib.Path
    ) -> None:
        """modified_count is NOT incremented when write_text raises OSError.

        Regression test: a failed write must not count as a successful fix.
        The summary must show "Fixed: 0" and "Errors: 1", and exit non-zero.
        """
        f = tmp_path / "needs_header.py"
        f.write_text("x = 1\n", encoding="utf-8")

        runner = CliRunner()
        with mock.patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            result = runner.invoke(spdx, ["fix", str(tmp_path)])

        # Must exit non-zero because the write failed
        assert result.exit_code != 0
        # Error must be reported
        assert "Errors: 1" in result.output or "Errors: 1" in (
            result.output + str(result.exception)
        )
        # modified_count must NOT be inflated — "Fixed: 0" must appear
        assert "Fixed: 0" in result.output


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
