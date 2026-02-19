# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
SPDX License Header Management CLI.

Provides CLI commands for adding, fixing, and validating canonical SPDX MIT
license headers across source files. Exposes `onex spdx fix` and
`onex spdx validate` subcommands.

Usage:
    onex spdx fix [--dry-run] [--check] [--verbose] [PATH]
    onex spdx validate [FILES...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Year intentionally frozen at 2025 per FILE_HEADERS.md policy:
# use creation year only, do not update on edits.
SPDX_COPYRIGHT_LINE = "# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc."
SPDX_LICENSE_LINE = "# SPDX-License-Identifier: MIT"
SPDX_HEADER = f"{SPDX_COPYRIGHT_LINE}\n{SPDX_LICENSE_LINE}\n"

# Number of header lines to inspect for validation / existing header detection
HEADER_SCAN_LINES = 10

# File extensions eligible for SPDX headers (hash-comment style)
INCLUDED_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".sh", ".bash", ".yml", ".yaml", ".toml"}
)

# Exact filenames (no extension matching) that should get headers
INCLUDED_FILENAMES: frozenset[str] = frozenset({"Dockerfile", "Makefile"})

# Directory names to skip entirely
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        "dist",
        "build",
        ".venv",
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "archived",
        "archive",
        "vendor",
        "third_party",
        "node_modules",
        ".tox",
        ".eggs",
    }
)

# Files to skip by name
EXCLUDED_FILES: frozenset[str] = frozenset({"uv.lock"})

# Bypass marker — if present in first HEADER_SCAN_LINES, skip the file
BYPASS_MARKER = "# spdx-skip:"

# Patterns that indicate an existing (possibly wrong) SPDX header
_SPDX_MARKERS = ("# SPDX-FileCopyrightText:", "# SPDX-License-Identifier:")


# ---------------------------------------------------------------------------
# Core helpers (shared by fix + validate)
# ---------------------------------------------------------------------------


def _is_excluded_dir(path: Path) -> bool:
    """Check whether any component of *path* matches an excluded directory."""
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
        # Handle glob-style patterns like "*.egg-info"
        if part.endswith(".egg-info"):
            return True
    return False


def _is_eligible_file(path: Path) -> bool:
    """Return True if *path* should carry an SPDX header."""
    if not path.is_file():
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if _is_excluded_dir(path):
        return False
    if path.suffix in INCLUDED_EXTENSIONS:
        return True
    if path.name in INCLUDED_FILENAMES:
        return True
    return False


def _discover_files(root: Path) -> list[Path]:
    """Walk *root* and return sorted list of eligible source files."""
    files: list[Path] = []
    if root.is_file():
        if _is_eligible_file(root):
            files.append(root)
        return files

    for child in sorted(root.rglob("*")):
        if _is_eligible_file(child):
            files.append(child)
    return files


def _is_shebang(line: str) -> bool:
    return line.startswith("#!")


_ENCODING_RE = re.compile(r"^[ \t\f]*#[ \t\-*\w]*coding[:=][ \t]*([-\w.]+)")


def _is_encoding(line: str) -> bool:
    return bool(_ENCODING_RE.match(line))


def _has_bypass(lines: list[str]) -> bool:
    """Return True if the file contains the spdx-skip bypass marker."""
    for line in lines[:HEADER_SCAN_LINES]:
        if BYPASS_MARKER in line.lower():
            return True
    return False


def _has_correct_header(lines: list[str]) -> bool:
    """Return True if the file already has the exact canonical SPDX header.

    Returns False if the canonical two-line header is present but stale
    SPDX-License-Identifier lines remain elsewhere in the file.
    """
    idx = 0
    # Skip shebang
    if idx < len(lines) and _is_shebang(lines[idx]):
        idx += 1
    # Skip encoding
    if idx < len(lines) and _is_encoding(lines[idx]):
        idx += 1
    # Now expect the two canonical lines
    if idx + 1 >= len(lines):
        return False
    if not (
        lines[idx].rstrip() == SPDX_COPYRIGHT_LINE
        and lines[idx + 1].rstrip() == SPDX_LICENSE_LINE
    ):
        return False
    # Confirm no stale SPDX-License-Identifier lines follow the canonical header.
    # Note: plain-text scan; a '# SPDX-License-Identifier:' line inside a docstring
    # or multi-line string would be a false positive. AST-based parsing is not used
    # for performance reasons.
    for line in lines[idx + 2 :]:
        if (
            line.strip().startswith("# SPDX-License-Identifier:")
            and line.rstrip() != SPDX_LICENSE_LINE
        ):
            return False
    return True


def _has_any_spdx(lines: list[str]) -> bool:
    """Return True if any SPDX marker exists in the header region.

    Only scans the first HEADER_SCAN_LINES lines. Files with SPDX markers
    exclusively beyond line 10 are treated as having no SPDX header and will
    receive a new header insertion.
    """
    for line in lines[:HEADER_SCAN_LINES]:
        stripped = line.strip()
        for marker in _SPDX_MARKERS:
            if stripped.startswith(marker):
                return True
    return False


# ---------------------------------------------------------------------------
# Fixer logic
# ---------------------------------------------------------------------------


def _strip_existing_spdx(lines: list[str]) -> list[str]:
    """Remove any existing SPDX header lines from the file content."""
    result: list[str] = []
    i = 0
    # Preserve shebang / encoding
    while i < len(lines) and (_is_shebang(lines[i]) or _is_encoding(lines[i])):
        result.append(lines[i])
        i += 1

    # Skip SPDX lines and the blank line that follows them
    spdx_removed = False
    while i < len(lines):
        stripped = lines[i].strip()
        is_spdx = False
        for marker in _SPDX_MARKERS:
            if stripped.startswith(marker):
                is_spdx = True
                break
        # Also match bare "#" separator lines within an SPDX header block.
        # A bare "#" is part of the block when:
        #   (a) spdx_removed is True (we are already inside the block), OR
        #   (b) the immediately preceding line is an SPDX marker (handles a
        #       bare "#" that sits between two SPDX lines, e.g. the middle of
        #       a 3-line header: copyright / # / license).
        # The previous guard checked that the *next* line was also an SPDX
        # marker, which was too strict: it left a trailing bare "#" (after the
        # last SPDX line) unconsumed.
        if stripped == "#" and (
            spdx_removed
            or (
                i > 0 and any(lines[i - 1].strip().startswith(m) for m in _SPDX_MARKERS)
            )
        ):
            is_spdx = True

        if is_spdx:
            spdx_removed = True
            i += 1
            continue
        break

    # Skip at most one blank line after removed SPDX block
    if spdx_removed and i < len(lines) and lines[i].strip() == "":
        i += 1

    # Strip any SPDX remnant block that survived because it was separated from
    # the main block by a blank line (e.g. "#\n# SPDX-License-Identifier: X").
    # Only do this immediately after the main block (no real content in between).
    # Only tolerates a single blank line separating the main block from a remnant
    # block. Files with two or more blank lines before a remnant rely on
    # _remove_body_spdx_blocks for cleanup.
    if spdx_removed:
        j = i
        remnant_consumed = False
        while j < len(lines):
            s = lines[j].strip()
            is_remnant = any(s.startswith(m) for m in _SPDX_MARKERS)
            if is_remnant:
                remnant_consumed = True
            # Bare "#": consume when already inside the remnant block (previous
            # SPDX line consumed) OR when the next line is an SPDX marker (e.g.
            # "#\n# SPDX-License-Identifier: X" multi-line remnant header).
            if (
                not is_remnant
                and s == "#"
                and (
                    remnant_consumed
                    or (
                        j + 1 < len(lines)
                        and any(
                            lines[j + 1].strip().startswith(m) for m in _SPDX_MARKERS
                        )
                    )
                )
            ):
                is_remnant = True
            if not is_remnant:
                break
            j += 1
        if j > i:
            i = j
            # Skip at most one blank line after the remnant block
            if i < len(lines) and lines[i].strip() == "":
                i += 1

    result.extend(lines[i:])
    return result


def _remove_body_spdx_blocks(lines: list[str]) -> list[str]:
    """Remove stale SPDX blocks that appear in the file body (after the header).

    Handles the case where a previous partial strip left an old Apache header
    embedded after real code (e.g. after ``import`` statements).
    Removes any run of ``# SPDX-FileCopyrightText:``, ``#``, and
    ``# SPDX-License-Identifier:`` lines along with the blank line that
    immediately precedes the block (when the preceding line is blank).
    """
    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # Detect the start of a stale SPDX block
        is_block_start = stripped.startswith("# SPDX-FileCopyrightText:") or (
            stripped.startswith("# SPDX-License-Identifier:")
            and stripped != SPDX_LICENSE_LINE
        )
        if is_block_start:
            # Walk forward, consuming all lines that belong to this SPDX block
            j = i
            while j < len(lines):
                s = lines[j].strip()
                is_spdx = any(s.startswith(m) for m in _SPDX_MARKERS) or s == "#"
                if not is_spdx:
                    break
                j += 1
            # Only remove if at least one non-canonical SPDX-License-Identifier
            # exists in the block (avoid removing intentional single-line comments)
            block = lines[i:j]
            has_stale = any(
                ln.strip().startswith("# SPDX-License-Identifier:")
                and ln.rstrip() != SPDX_LICENSE_LINE
                for ln in block
            )
            # Only remove the block if it contains a non-canonical license
            # identifier (has_stale=True). A lone copyright comment without a
            # license line is left in place intentionally — it may be a
            # legitimate third-party attribution.
            if has_stale:
                # Drop the blank line before the block if present
                if result and result[-1].strip() == "":
                    result.pop()
                i = j
                # Skip blank line after the removed block
                if i < len(lines) and lines[i].strip() == "":
                    i += 1
                continue
        result.append(lines[i])
        i += 1
    return result


def _fix_file_content(content: str, file_path: Path | None = None) -> str:
    """Return *content* with the canonical SPDX header inserted/replaced.

    YAML files (`.yml`/`.yaml`) whose first non-shebang/encoding line is "---"
    receive no blank separator between the SPDX header and the "---" document
    marker.  The ``file_path`` argument is used to determine the file extension;
    when omitted the YAML special-case is not applied.
    """
    lines = content.splitlines(keepends=True)

    if not lines:
        # Empty file — just add header
        return SPDX_HEADER

    # If file has bypass, leave it alone
    if _has_bypass(lines):
        return content

    # If already correct, return as-is
    if _has_correct_header(lines):
        return content

    # Strip any existing (wrong) SPDX header.
    # After stripping, compare against the original lines to detect whether the
    # strip was a no-op.  This happens when _has_any_spdx() found an SPDX
    # marker but _strip_existing_spdx() could not locate it at the expected
    # position (e.g. a non-SPDX comment precedes the SPDX block, so the
    # stripper exits its inner loop before reaching the SPDX lines).  In that
    # case inserting a new header would produce a duplicate — leave the file
    # unchanged so the existing (un-normalizable) block is preserved intact.
    if _has_any_spdx(lines):
        stripped = _strip_existing_spdx(lines)
        if stripped == lines:
            # Strip was a no-op despite an SPDX marker being present: the block
            # is in an unexpected position and cannot be safely replaced.
            # Return content unchanged to avoid duplicate header insertion.
            return content
        lines = stripped

    # Remove any stale SPDX blocks embedded in the file body
    lines = _remove_body_spdx_blocks(lines)

    # Determine insertion point (after shebang + encoding)
    insert_idx = 0
    if insert_idx < len(lines) and _is_shebang(lines[insert_idx]):
        insert_idx += 1
    if insert_idx < len(lines) and _is_encoding(lines[insert_idx]):
        insert_idx += 1

    # For YAML files: insert SPDX before "---" document marker (no blank separator).
    # Guard on file extension so that non-YAML files whose first content line
    # happens to be "---" are not treated as YAML.
    _is_yaml = file_path is not None and file_path.suffix.lower() in (".yml", ".yaml")
    if _is_yaml and insert_idx < len(lines) and lines[insert_idx].rstrip() == "---":
        # Insert SPDX before the "---"
        new_lines = list(lines[:insert_idx])
        new_lines.append(SPDX_COPYRIGHT_LINE + "\n")
        new_lines.append(SPDX_LICENSE_LINE + "\n")
        new_lines.extend(lines[insert_idx:])
        return "".join(new_lines)

    # Standard case: insert header at insert_idx
    new_lines = list(lines[:insert_idx])

    # Guard: if the last preserved line (shebang or encoding) has no trailing
    # newline, append one now so the SPDX header begins on its own line.
    if new_lines and not new_lines[-1].endswith(("\n", "\r\n")):
        new_lines[-1] += "\n"

    new_lines.append(SPDX_COPYRIGHT_LINE + "\n")
    new_lines.append(SPDX_LICENSE_LINE + "\n")

    # Ensure blank line separates header from content (unless content is empty)
    remaining = lines[insert_idx:]
    if remaining and remaining[0].strip() != "":
        new_lines.append("\n")

    new_lines.extend(remaining)
    return "".join(new_lines)


# ---------------------------------------------------------------------------
# Validate logic
# ---------------------------------------------------------------------------


def _validate_file(path: Path) -> str | None:
    """Validate a single file for correct SPDX header.

    Returns None if valid, or an error message string if invalid.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"Cannot read file: {e}"

    lines = content.splitlines()

    if _has_bypass(lines):
        return None  # Explicitly skipped

    if not lines:
        return "File is empty (expected SPDX header)"

    # Find where header should start (skip shebang / encoding)
    idx = 0
    if idx < len(lines) and _is_shebang(lines[idx]):
        idx += 1
    if idx < len(lines) and _is_encoding(lines[idx]):
        idx += 1

    # Check the two canonical lines
    if idx >= len(lines):
        return f"Missing SPDX header (file has only {len(lines)} lines)"

    # intentional: trailing whitespace on header lines is tolerated per policy.
    # Files that have the correct SPDX text but trailing spaces are accepted as
    # valid rather than rejected, to avoid false positives from editors that
    # insert trailing whitespace.  The fix command will not rewrite such files
    # because _has_correct_header uses the same rstrip() tolerance.
    if lines[idx].rstrip() != SPDX_COPYRIGHT_LINE:
        return (
            f"Line {idx + 1}: Expected '{SPDX_COPYRIGHT_LINE}', "
            f"got '{lines[idx].rstrip()[:80]}'"
        )

    if idx + 1 >= len(lines):
        return f"Line {idx + 2}: Missing '{SPDX_LICENSE_LINE}'"

    if lines[idx + 1].rstrip() != SPDX_LICENSE_LINE:
        return (
            f"Line {idx + 2}: Expected '{SPDX_LICENSE_LINE}', "
            f"got '{lines[idx + 1].rstrip()[:80]}'"
        )

    # Check for stale SPDX-License-Identifier lines beyond the canonical header.
    # Note: plain-text scan; a '# SPDX-License-Identifier:' line inside a docstring
    # or multi-line string would be a false positive. AST-based parsing is not used
    # for performance reasons.
    for lineno, line in enumerate(lines[idx + 2 :], start=idx + 3):
        if (
            line.strip().startswith("# SPDX-License-Identifier:")
            and line.rstrip() != SPDX_LICENSE_LINE
        ):
            return (
                f"Line {lineno}: Stale SPDX-License-Identifier found after canonical header: "
                f"'{line.rstrip()[:80]}'"
            )

    return None


def validate_files(file_args: list[str]) -> int:
    """Validate SPDX headers for a list of files or directories.

    Designed to be callable from both the CLI and the pre-commit wrapper.

    Args:
        file_args: File paths or directories to validate. If empty,
            defaults to scanning the current working directory. Callers are
            responsible for ensuring the CWD is the intended scan root when
            an empty list is passed.

    Returns:
        0 if all files are compliant, 1 if violations found.
    """
    # When called with no file args (e.g. manual invocation), scans CWD. In
    # pre-commit context with pass_filenames=true, this branch is unreachable
    # as pre-commit skips hook invocation when no files match.
    paths: list[Path] = [Path(a) for a in file_args] if file_args else [Path()]

    files_to_check: list[Path] = []
    for p in paths:
        if p.is_file():
            if _is_eligible_file(p):
                files_to_check.append(p)
            else:
                print(  # print-ok: CLI output
                    f"Warning: skipping ineligible file: {p}", file=sys.stderr
                )
        elif p.is_dir():
            files_to_check.extend(_discover_files(p))
        else:
            # intentional: a non-existent explicit path emits a warning but
            # does NOT count as a validation error (returns 0).  pre-commit
            # passes staged filenames which may have been deleted or renamed
            # since staging; silently skipping them avoids spurious CI failures
            # for in-flight deletions.  Callers that need stricter behaviour
            # (e.g. a fully authoritative CI scan) should pre-filter paths.
            print(  # print-ok: CLI output
                f"Warning: path does not exist: {p}", file=sys.stderr
            )

    # Deduplicate while preserving insertion order (e.g. when the same path is
    # passed more than once via pre-commit or the CLI).
    # Note: deduplication is by path string, not inode; symlinks to the same
    # underlying file may be validated twice.
    files_to_check = list(dict.fromkeys(files_to_check))

    violations: list[tuple[Path, str]] = []
    for f in sorted(files_to_check):
        error = _validate_file(f)
        if error is not None:
            violations.append((f, error))

    if violations:
        print(  # print-ok: CLI output
            f"\nSPDX Header Validation Failed — {len(violations)} file(s):\n"
        )
        for filepath, msg in violations:
            print(f"  {filepath}: {msg}")  # print-ok: CLI output
        print(  # print-ok: CLI output
            "\nRun `onex spdx fix <path>` to fix."
        )
        return 1

    return 0


# ---------------------------------------------------------------------------
# Click CLI
# ---------------------------------------------------------------------------


@click.group()
def spdx() -> None:  # stub-ok: Click group, subcommands via @spdx.command()
    """SPDX license header management.

    Add, fix, and validate canonical SPDX MIT license headers across
    source files.

    \b
    Commands:
        fix       - Add/fix SPDX headers (bulk rewrite)
        validate  - Check files for correct SPDX headers
    """


@spdx.command()
@click.argument(
    "path",
    default=".",
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
@click.option(
    "--check",
    is_flag=True,
    help="Exit 1 if any files need changes (for CI). No files are modified.",
)
@click.option("--verbose", "-v", is_flag=True, help="Show per-file status.")
@click.pass_context
def fix(
    ctx: click.Context,
    path: Path,
    dry_run: bool,
    check: bool,
    verbose: bool,
) -> None:
    """Add or fix SPDX headers in source files.

    Walks PATH (default: current directory) and ensures every eligible source
    file has the canonical two-line SPDX MIT header. Handles shebang lines,
    encoding declarations, YAML document markers, and replaces wrong or
    outdated headers.

    Idempotent — running twice produces no diff.

    \b
    Examples:
        onex spdx fix                  # Fix current directory
        onex spdx fix src/             # Fix src/ only
        onex spdx fix --dry-run .      # Preview changes
        onex spdx fix --check .        # CI gate (exit 1 if changes needed)
    """
    files = _discover_files(path)

    if verbose:
        click.echo(f"Scanning {path} — found {len(files)} eligible files")

    modified_count = 0
    already_ok_count = 0
    skipped_count = 0
    error_count = 0

    for filepath in files:
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            click.echo(click.style(f"ERROR: {filepath}: {e}", fg="red"), err=True)
            error_count += 1
            continue

        lines = content.splitlines()
        if _has_bypass(lines):
            if verbose:
                click.echo(f"  SKIP (bypass): {filepath}")
            skipped_count += 1
            continue

        new_content = _fix_file_content(content, file_path=filepath)

        if new_content == content:
            # Content returned unchanged — could mean "already correct" OR
            # "malformed block that cannot be auto-fixed".  Distinguish the
            # two cases so that `fix --check` and `validate` agree.
            file_lines = content.splitlines(keepends=True)
            if not _has_correct_header(file_lines) and _has_any_spdx(file_lines):
                # SPDX is present but not at the expected position; the fixer
                # could not normalise it.  This is an error, not "already OK".
                click.echo(
                    click.style(
                        f"Error: cannot normalize SPDX header in {filepath} "
                        f"(malformed block structure)",
                        fg="red",
                    ),
                    err=True,
                )
                error_count += 1
                continue
            if verbose:
                click.echo(f"  OK: {filepath}")
            already_ok_count += 1
            continue

        if check or dry_run:
            modified_count += 1
            click.echo(f"  NEEDS FIX: {filepath}")
        else:
            try:
                filepath.write_text(new_content, encoding="utf-8")
                modified_count += 1
                if verbose:
                    click.echo(f"  FIXED: {filepath}")
            except OSError as e:
                click.echo(
                    click.style(f"ERROR writing {filepath}: {e}", fg="red"), err=True
                )
                error_count += 1

    # Summary
    click.echo()
    if check:
        if modified_count > 0:
            click.echo(
                click.style(
                    f"{modified_count} file(s) need SPDX headers. "
                    f"Run `onex spdx fix` to apply.",
                    fg="red",
                )
            )
            ctx.exit(EnumCLIExitCode.ERROR)
        elif error_count > 0:
            click.echo(click.style(f"Errors: {error_count}", fg="red"), err=True)
            ctx.exit(EnumCLIExitCode.ERROR)
        else:
            click.echo(click.style("All files have correct SPDX headers.", fg="green"))
            ctx.exit(EnumCLIExitCode.SUCCESS)
    elif dry_run:
        # Surface errors before the summary counts so the ordering matches the
        # normal write path (error-first, then summary).
        if error_count:
            click.echo(click.style(f"Errors: {error_count}", fg="red"), err=True)
        click.echo(f"DRY RUN: {modified_count} file(s) would be modified")
        click.echo(f"Already OK: {already_ok_count} | Skipped: {skipped_count}")
        if error_count:
            ctx.exit(EnumCLIExitCode.ERROR)
    # For the normal write path, surface errors before the success summary so
    # the user sees the failure context rather than a misleading "Fixed: N" line.
    elif error_count:
        click.echo(click.style(f"Errors: {error_count}", fg="red"), err=True)
        click.echo(f"Fixed: {modified_count} file(s)")
        click.echo(f"Already OK: {already_ok_count} | Skipped: {skipped_count}")
        ctx.exit(EnumCLIExitCode.ERROR)
    else:
        click.echo(f"Fixed: {modified_count} file(s)")
        click.echo(f"Already OK: {already_ok_count} | Skipped: {skipped_count}")


@spdx.command(name="validate")
@click.argument("files", nargs=-1, type=click.Path(path_type=Path))
@click.pass_context
def validate_cmd(ctx: click.Context, files: tuple[Path, ...]) -> None:
    """Validate SPDX headers on source files.

    Checks that every eligible file has the canonical two-line header.
    Accepts file paths as arguments (for pre-commit pass_filenames mode).
    Defaults to scanning the current working directory if no arguments provided.

    \b
    Examples:
        onex spdx validate                     # Check current working directory
        onex spdx validate src/ tests/         # Check specific dirs
        onex spdx validate src/foo/bar.py      # Check single file
    """
    exit_code = validate_files([str(f) for f in files])
    ctx.exit(exit_code)


__all__ = ["spdx", "validate_files"]
