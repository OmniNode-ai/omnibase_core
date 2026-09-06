# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ValidatorLocalPaths — detect machine-specific absolute paths.

Catches hardcoded filesystem paths like /Volumes/..., /Users/..., /home/...
that break portability when code, skills, or configuration are distributed.

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorLocalPaths

        validator = ValidatorLocalPaths()
        violations = validator.check_paths([Path("src/"), Path("plugins/")])
        for v in violations:
            print(f"{v.file}:{v.line}: [{v.pattern_name}] {v.matched_text!r}")

    CLI — check staged files (pre-commit mode)::

        python -m omnibase_core.validation.validator_local_paths file1.py file2.md

    CLI — check entire repository::

        python -m omnibase_core.validation.validator_local_paths .
        python -m omnibase_core.validation.validator_local_paths src/ plugins/

    CLI — check every tracked repository-root file (OMN-17993)::

        python -m omnibase_core.validation.validator_local_paths --tracked-root

    The root scan exists because the pre-commit hook only ever sees the files
    a commit stages. A root file committed before the hook existed — or before
    its pattern matched — is never re-examined, which is how ``.mcp.json``
    carried an operator-home clone path at HEAD while the hook reported green
    on every subsequent commit. The root scan reads the **tracked set** (``git
    ls-files``), not the ignore rules, and it ignores the extension allowlist:
    a root file has no reason to be exempt because of its name.

Suppression:
    Add ``# local-path-ok`` anywhere on a line to suppress that line::

        DOCS_ROOT = "/Volumes/MY-DRIVE/Code"  # local-path-ok  (example only)

Schema Version:
    v1.0.0 - Initial version
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_LOCAL_PATH_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    ("macOS volume mount", re.compile(r"/Volumes/[A-Za-z][A-Za-z0-9_.-]*/")),
    ("macOS user home", re.compile(r"/Users/[A-Za-z_][A-Za-z0-9_.-]*/")),
    ("Linux user home", re.compile(r"/home/[A-Za-z_][A-Za-z0-9_.-]*/")),
    ("Windows user path", re.compile(r"[Cc]:[/\\][Uu]sers[/\\]")),
]

_SUPPRESSION_MARKER: Final[str] = "local-path-ok"

# Text-based file extensions to scan
_TEXT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".py",
        ".md",
        ".yaml",
        ".yml",
        ".json",
        ".sh",
        ".toml",
        ".txt",
        ".rst",
        ".cfg",
        ".ini",
    }
)

# Directories to skip during recursive scan.
#
# Three groups:
#   1. Standard generated/cache trees (.git, __pycache__, node_modules, venvs).
#   2. Frontend and graph generation output (.next, dist, build, graphify-out).
#      These mirror source strings into compiled output and would inflate
#      source-owner triage counts if scanned. See OMN-11007.
#   3. Immutable evidence and local runtime state. OCC receipts under
#      dod_receipts/ and evidence/, plus historical .evidence/ command
#      records and .onex_state/ runtime captures, preserve real cwds and so
#      look like source violations even though they are not source-owner
#      actionable.
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        # Standard
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        # Generated frontend / graph output (OMN-11007)
        ".next",
        "dist",
        "build",
        "graphify-out",
        # Evidence and local runtime state (OMN-11007)
        "dod_receipts",
        "evidence",
        ".evidence",
        ".onex_state",
    }
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class ModelLocalPathViolation(BaseModel):
    """A single local-path violation found in a file."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: Path
    line: int
    column: int
    pattern_name: str
    matched_text: str
    context: str  # full source line (stripped)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ValidatorLocalPaths(BaseModel):
    """Detect machine-specific absolute paths that break portability.

    Stateless: each call to check_file or check_paths returns violations
    without mutating any instance state. Safe to reuse across calls.

    Thread Safety:
        Instances are thread-safe because there is no mutable state.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    def check_file(
        self, path: Path, *, ignore_extension_filter: bool = False
    ) -> list[ModelLocalPathViolation]:
        """Check a single file. Returns violations found.

        ``ignore_extension_filter`` scans the file whatever its name. The
        extension allowlist is a cheap way to skip binaries during a recursive
        walk; on an explicitly enumerated set (the tracked repository-root
        scan) it is a blind spot, because an extension-less dotfile such as
        ``.envrc`` reads as "not text" and is skipped in silence.
        """
        if not ignore_extension_filter and path.suffix not in _TEXT_EXTENSIONS:
            return []

        file_violations: list[ModelLocalPathViolation] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except (OSError, PermissionError):
            return []

        for lineno, line in enumerate(lines, start=1):
            if _SUPPRESSION_MARKER in line:
                continue
            for pattern_name, pattern in _LOCAL_PATH_PATTERNS:
                for match in pattern.finditer(line):
                    file_violations.append(
                        ModelLocalPathViolation(
                            file=path,
                            line=lineno,
                            column=match.start() + 1,
                            pattern_name=pattern_name,
                            matched_text=match.group(),
                            context=line.rstrip(),
                        )
                    )

        return file_violations

    def check_paths(self, paths: list[Path]) -> list[ModelLocalPathViolation]:
        """Check a list of files or directories recursively."""
        all_violations: list[ModelLocalPathViolation] = []
        for p in paths:
            if p.is_file():
                all_violations.extend(self.check_file(p))
            elif p.is_dir():
                for child in sorted(
                    p.rglob("*")
                ):  # sorted for deterministic output order
                    if any(part in _SKIP_DIRS for part in child.parts):
                        continue
                    if child.is_file():
                        all_violations.extend(self.check_file(child))
            else:
                print(
                    f"Warning: check-local-paths: skipping non-existent path: {p}",
                    file=sys.stderr,
                )
        return all_violations


# ---------------------------------------------------------------------------
# Tracked repository-root scan (OMN-17993)
# ---------------------------------------------------------------------------


def tracked_root_files(repo_root: Path | None = None) -> list[Path]:
    """Every tracked file at the repository root, dotfiles included.

    ``git ls-files`` is the source of truth rather than a directory listing:
    an ignore rule neither untracks an existing path nor stops ``git add -f``,
    so ignore state is not evidence about what is committed. Fails loud when
    git cannot answer — a scan that silently returns nothing is the defect
    this mode exists to close.
    """
    import os
    import subprocess

    from omnibase_core.validators.no_unguarded_git_subprocess import (
        scrub_git_location_env,
    )

    root = repo_root or Path.cwd()
    # The pre-commit hook that calls this runs INSIDE a git hook environment,
    # where GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE override both `cwd=` and
    # `git -C`. Without the scrub this would enumerate the invoking worktree
    # rather than `root` — the OMN-14891 failure shape.
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    return [
        root / rel
        for rel in result.stdout.split("\0")
        if rel and "/" not in rel and (root / rel).is_file()
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Accepts files (pre-commit staged mode) or directories (full scan).

    Exit codes:
        0 — no violations
        1 — violations found
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="check-local-paths",
        description=(
            "Detect machine-specific absolute paths that break portability. "
            "Checks /Volumes/..., /Users/..., /home/..., C:\\Users\\..."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--tracked-root",
        action="store_true",
        help=(
            "Scan every tracked repository-root file (dotfiles included, "
            "extension filter ignored) instead of the positional paths"
        ),
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-violation context lines and summary",
    )
    parsed = parser.parse_args(argv)

    validator = ValidatorLocalPaths()
    if parsed.tracked_root:
        import subprocess

        try:
            root_files = tracked_root_files()
        except (OSError, subprocess.CalledProcessError) as exc:
            print(
                f"check-local-paths: --tracked-root requires a git work tree: {exc}",
                file=sys.stderr,
            )
            return 1
        violations = [
            v
            for f in root_files
            for v in validator.check_file(f, ignore_extension_filter=True)
        ]
    else:
        violations = validator.check_paths(parsed.paths)

    for v in violations:
        print(f"{v.file}:{v.line}:{v.column}: [{v.pattern_name}] {v.matched_text!r}")
        if not parsed.quiet:
            print(f"  {v.context}")

    if not parsed.quiet:
        if violations:
            print(
                f"\n{len(violations)} local path violation(s). "
                f"Remove hardcoded paths or add `# {_SUPPRESSION_MARKER}` to suppress."
            )
        else:
            print("No local path violations found.")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
