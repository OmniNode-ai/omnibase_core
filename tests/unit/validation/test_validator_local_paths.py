# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorLocalPaths.

Covers:
- Clean file returns no violations
- macOS volume mount detection
- macOS user home detection (lowercase and uppercase)
- Linux home detection
- Windows path detection
- Suppression marker skips the line
- Non-.py extensions (e.g., .md) are scanned
- Unsupported extensions (e.g., .lock) are skipped
- check_paths with a directory scans recursively
- CLI main() returns 0 on clean, 1 on violations
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_local_paths import (
    ModelLocalPathViolation,
    ValidatorLocalPaths,
    main,
)


@pytest.mark.unit
class TestCheckFileClean:
    """check_file returns no violations for clean content."""

    def test_clean_python_file_no_violations(self, tmp_path: Path) -> None:
        """A file with no local paths produces no violations."""
        f = tmp_path / "clean.py"
        f.write_text('x = "hello world"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        assert validator.check_file(f) == []

    def test_no_accumulated_state_across_calls(self, tmp_path: Path) -> None:
        """Validator is stateless — successive calls do not accumulate violations."""
        f1 = tmp_path / "a.py"
        f1.write_text('path = "/Volumes/PRO-G40/file"\n', encoding="utf-8")
        f2 = tmp_path / "b.py"
        f2.write_text('x = 1\n', encoding="utf-8")

        validator = ValidatorLocalPaths()
        v1 = validator.check_file(f1)
        v2 = validator.check_file(f2)

        assert len(v1) == 1
        assert len(v2) == 0
        # Calling check_file again on f2 still returns 0 (no leakage from f1)
        assert len(validator.check_file(f2)) == 0


@pytest.mark.unit
class TestMacOSVolume:
    """macOS volume mount pattern."""

    def test_volume_mount_detected(self, tmp_path: Path) -> None:
        """'/Volumes/PRO-G40/' is detected as a macOS volume mount."""
        f = tmp_path / "cfg.py"
        f.write_text('ROOT = "/Volumes/PRO-G40/Code"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        v = violations[0]
        assert v.pattern_name == "macOS volume mount"
        assert "/Volumes/" in v.matched_text


@pytest.mark.unit
class TestMacOSUserHome:
    """macOS user home pattern — lowercase and uppercase usernames."""

    def test_lowercase_username_detected(self, tmp_path: Path) -> None:
        """'/Users/jonah/' triggers macOS user home violation."""
        f = tmp_path / "cfg.py"
        f.write_text('HOME = "/Users/jonah/projects"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].pattern_name == "macOS user home"

    def test_uppercase_username_detected(self, tmp_path: Path) -> None:
        """'/Users/Jonah/' (uppercase) triggers macOS user home violation."""
        f = tmp_path / "cfg.py"
        f.write_text('HOME = "/Users/Jonah/projects"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].pattern_name == "macOS user home"


@pytest.mark.unit
class TestLinuxHome:
    """Linux home pattern."""

    def test_linux_home_detected(self, tmp_path: Path) -> None:
        """'/home/ubuntu/' triggers Linux user home violation."""
        f = tmp_path / "cfg.py"
        f.write_text('HOME = "/home/ubuntu/work"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].pattern_name == "Linux user home"

    def test_linux_home_uppercase_detected(self, tmp_path: Path) -> None:
        """'/home/Ubuntu/' (uppercase) triggers Linux user home violation."""
        f = tmp_path / "cfg.py"
        f.write_text('HOME = "/home/Ubuntu/work"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].pattern_name == "Linux user home"


@pytest.mark.unit
class TestWindowsPath:
    """Windows user path pattern."""

    def test_windows_path_detected(self, tmp_path: Path) -> None:
        r"""'C:\Users\' triggers Windows user path violation."""
        f = tmp_path / "cfg.py"
        f.write_text(r'PATH = "C:\Users\alice\Documents"' + "\n", encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].pattern_name == "Windows user path"

    def test_windows_lowercase_c_detected(self, tmp_path: Path) -> None:
        r"""'c:\users\' (lowercase) triggers Windows user path violation."""
        f = tmp_path / "cfg.py"
        f.write_text(r'PATH = "c:\users\alice\Documents"' + "\n", encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].pattern_name == "Windows user path"


@pytest.mark.unit
class TestSuppressionMarker:
    """# local-path-ok suppression marker."""

    def test_suppression_marker_skips_line(self, tmp_path: Path) -> None:
        """Line containing '# local-path-ok' is not flagged."""
        f = tmp_path / "cfg.py"
        f.write_text(
            'DOCS_ROOT = "/Volumes/PRO-G40/Code"  # local-path-ok\n',
            encoding="utf-8",
        )
        validator = ValidatorLocalPaths()
        assert validator.check_file(f) == []

    def test_suppression_only_suppresses_matching_line(self, tmp_path: Path) -> None:
        """Suppression on one line does not suppress other lines."""
        f = tmp_path / "cfg.py"
        f.write_text(
            'A = "/Volumes/PRO-G40/Code"  # local-path-ok\n'
            'B = "/Volumes/PRO-G40/Other"\n',
            encoding="utf-8",
        )
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1
        assert violations[0].line == 2


@pytest.mark.unit
class TestFileExtensions:
    """Extension filtering behaviour."""

    def test_md_file_is_scanned(self, tmp_path: Path) -> None:
        """Markdown (.md) files are scanned for violations."""
        f = tmp_path / "README.md"
        f.write_text("See `/Users/jonah/projects` for details.\n", encoding="utf-8")
        validator = ValidatorLocalPaths()
        violations = validator.check_file(f)
        assert len(violations) == 1

    def test_lock_file_is_skipped(self, tmp_path: Path) -> None:
        """'.lock' extension is not in the scanned set and is skipped."""
        f = tmp_path / "lockfile.lock"
        f.write_text('path = "/Users/jonah/work"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        assert validator.check_file(f) == []

    def test_binary_extension_skipped(self, tmp_path: Path) -> None:
        """'.so' extension is skipped."""
        f = tmp_path / "lib.so"
        f.write_text('path = "/Users/jonah/work"\n', encoding="utf-8")
        validator = ValidatorLocalPaths()
        assert validator.check_file(f) == []


@pytest.mark.unit
class TestCheckPathsDirectory:
    """check_paths with a directory scans recursively."""

    def test_directory_scanned_recursively(self, tmp_path: Path) -> None:
        """Nested files inside a directory are all scanned."""
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "a.py").write_text('X = "/Volumes/PRO-G40/a"\n', encoding="utf-8")
        (sub / "b.py").write_text('Y = "/home/ubuntu/b"\n', encoding="utf-8")
        (sub / "clean.py").write_text('Z = 42\n', encoding="utf-8")

        validator = ValidatorLocalPaths()
        violations = validator.check_paths([tmp_path])
        assert len(violations) == 2

    def test_non_existent_path_prints_warning(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A path that is neither a file nor a directory prints a stderr warning."""
        ghost = tmp_path / "ghost.py"
        # Do not create the file — it doesn't exist
        validator = ValidatorLocalPaths()
        violations = validator.check_paths([ghost])
        assert violations == []
        captured = capsys.readouterr()
        assert "skipping non-existent path" in captured.err
        assert str(ghost) in captured.err


@pytest.mark.unit
class TestModelLocalPathViolation:
    """ModelLocalPathViolation Pydantic model properties."""

    def test_violation_is_immutable(self, tmp_path: Path) -> None:
        """ModelLocalPathViolation instances are frozen (immutable)."""
        from pydantic import ValidationError

        f = tmp_path / "f.py"
        v = ModelLocalPathViolation(
            file=f,
            line=1,
            column=5,
            pattern_name="macOS volume mount",
            matched_text="/Volumes/X",
            context='x = "/Volumes/X/y"',
        )
        with pytest.raises((ValidationError, TypeError)):
            v.line = 99  # type: ignore[misc]

    def test_violation_extra_fields_forbidden(self, tmp_path: Path) -> None:
        """Extra fields are rejected by ConfigDict(extra='forbid')."""
        from pydantic import ValidationError

        f = tmp_path / "f.py"
        with pytest.raises(ValidationError):
            ModelLocalPathViolation(
                file=f,
                line=1,
                column=5,
                pattern_name="macOS volume mount",
                matched_text="/Volumes/X",
                context="x",
                unexpected_field="oops",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestCLIMain:
    """CLI main() exit code behaviour."""

    def test_main_returns_0_on_clean_directory(self, tmp_path: Path) -> None:
        """main() returns 0 when no violations are found."""
        f = tmp_path / "clean.py"
        f.write_text("x = 42\n", encoding="utf-8")
        result = main([str(f)])
        assert result == 0

    def test_main_returns_1_on_violations(self, tmp_path: Path) -> None:
        """main() returns 1 when violations are found."""
        f = tmp_path / "bad.py"
        f.write_text('ROOT = "/Volumes/PRO-G40/Code"\n', encoding="utf-8")
        result = main([str(f)])
        assert result == 1

    def test_main_quiet_flag_suppresses_context(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--quiet suppresses per-violation context lines and summary."""
        f = tmp_path / "bad.py"
        f.write_text('ROOT = "/Volumes/PRO-G40/Code"\n', encoding="utf-8")
        result = main(["--quiet", str(f)])
        assert result == 1
        captured = capsys.readouterr()
        # The context line (indented) and summary must not appear
        assert "  ROOT" not in captured.out
        assert "violation(s)" not in captured.out

    def test_main_no_args_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() with no paths argument defaults to current directory."""
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n", encoding="utf-8")
        result = main([])
        assert result == 0
