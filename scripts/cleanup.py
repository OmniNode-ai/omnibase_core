#!/usr/bin/env python3
"""
ONEX Repository Cleanup Script

This script removes temporary analysis files, reports, and cache files that should
not be committed to the repository. It's designed to catch common patterns of
files generated during development and analysis.

Usage:
    python scripts/cleanup.py [--dry-run] [--verbose] [--remove-from-git]

Options:
    --dry-run           Show what would be removed without removing
    --verbose, -v       Show detailed output
    --remove-from-git   Remove tracked files from git index (for tmp/ cleanup)
    --root DIR          Root directory to clean (default: current directory)
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from re import Pattern

# Patterns for files and directories to clean up
CLEANUP_PATTERNS = [
    # Report and analysis files
    r".*_report.*\.json$",
    r".*_analysis.*\.json$",
    r".*_errors.*\.txt$",
    r"mypy_.*\.txt$",
    r".*_validation_results\.json$",
    r".*_go_no_go_results\.json$",
    r"container_security_validation\.json$",
    r"phase.*_.*\.json$",
    r"PHASE.*_.*\.md$",
    r"DESIGN_.*\.md$",
    r"PR_DESCRIPTION\.md$",
    # Cache and temporary files
    r"__pycache__$",
    r"\.mypy_cache$",
    r"\.ruff_cache$",
    r"\.pytest_cache$",
    r"\.coverage.*$",
    # Build artifacts
    r"build$",
    r"dist$",
    r".*\.egg-info$",
    # System files
    r"\.DS_Store$",
    r"Thumbs\.db$",
    # Development artifacts
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.pyd$",
    r".*\.so$",
]

# Directories to clean up entirely
CLEANUP_DIRECTORIES = [
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "build",
    "dist",
    ".coverage",
    "htmlcov",
    "reports",
    "tmp",  # Temporary files and PR review cache
]


def compile_patterns(patterns: list[str]) -> list[Pattern]:
    """Compile regex patterns for file matching."""
    return [re.compile(pattern) for pattern in patterns]


def find_cleanup_files(root_dir: Path, patterns: list[Pattern]) -> list[Path]:
    """Find files matching cleanup patterns."""
    cleanup_files = []

    # Directories to skip entirely during traversal
    SKIP_DIRS = {".git", ".venv", "venv", "ENV", "env", "node_modules"}

    for root, dirs, files in os.walk(root_dir):
        root_path = Path(root)

        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        # Skip if we're inside an excluded directory
        if any(part in SKIP_DIRS for part in root_path.parts):
            continue

        # Check files
        for file in files:
            file_path = root_path / file
            relative_path = file_path.relative_to(root_dir)

            for pattern in patterns:
                if pattern.search(str(relative_path)):
                    cleanup_files.append(file_path)
                    break

        # Check directories
        for dir_name in dirs[:]:  # Create a copy to modify during iteration
            if dir_name in CLEANUP_DIRECTORIES:
                dir_path = root_path / dir_name
                cleanup_files.append(dir_path)
                dirs.remove(dir_name)  # Don't recurse into directories we're removing

    return cleanup_files


def remove_from_git_index(
    path: Path, root_dir: Path, dry_run: bool = False, verbose: bool = False
) -> bool:
    """Remove a file or directory from git index (untrack it)."""
    try:
        relative_path = path.relative_to(root_dir)

        # Check if file is tracked by git
        result = subprocess.run(
            ["git", "ls-files", str(relative_path)],
            cwd=root_dir,
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            return False  # Not tracked, nothing to do

        if dry_run:
            if verbose:
                print(f"[DRY RUN] Would remove from git: {relative_path}")
            return True

        # Remove from git index
        subprocess.run(
            ["git", "rm", "-r", "--cached", "--quiet", str(relative_path)],
            cwd=root_dir,
            check=True,
            capture_output=True,
        )

        if verbose:
            print(f"Removed from git index: {relative_path}")
        return True

    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"Git removal failed for {path}: {e}")
        return False
    except Exception as e:
        if verbose:
            print(f"Error removing from git {path}: {e}")
        return False


def remove_file_or_dir(
    path: Path, dry_run: bool = False, verbose: bool = False
) -> bool:
    """Remove a file or directory safely."""
    try:
        if dry_run:
            if verbose:
                print(f"[DRY RUN] Would remove: {path}")
            return True

        if path.is_dir():
            shutil.rmtree(path)
            if verbose:
                print(f"Removed directory: {path}")
        else:
            path.unlink()
            if verbose:
                print(f"Removed file: {path}")
        return True
    except Exception as e:
        print(f"Error removing {path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Clean up temporary files and analysis reports from ONEX repository"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without actually removing anything",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output of cleanup operations",
    )
    parser.add_argument(
        "--remove-from-git",
        action="store_true",
        help="Remove tracked files from git index (for accidentally committed tmp files)",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Root directory to clean (default: current directory)",
    )

    args = parser.parse_args()

    root_dir = Path(args.root).resolve()

    if not root_dir.exists():
        print(f"Error: Root directory {root_dir} does not exist")
        return 1

    if args.verbose:
        print(f"Cleaning up repository: {root_dir}")
        if args.dry_run:
            print("DRY RUN MODE - No files will be actually removed")

    # Compile cleanup patterns
    patterns = compile_patterns(CLEANUP_PATTERNS)

    # Find files to clean up
    cleanup_files = find_cleanup_files(root_dir, patterns)

    if not cleanup_files:
        if args.verbose:
            print("No cleanup files found.")
        return 0

    # Sort files for consistent output
    cleanup_files.sort()

    # Remove from git index first (if requested)
    git_removed_count = 0
    if args.remove_from_git:
        if args.verbose:
            print("\n🔧 Removing tracked files from git index...")

        for file_path in cleanup_files:
            if remove_from_git_index(file_path, root_dir, args.dry_run, args.verbose):
                git_removed_count += 1

        if git_removed_count > 0:
            print(f"✓ Removed {git_removed_count} items from git index")

    # Remove files from filesystem
    removed_count = 0
    failed_count = 0

    print(f"\nFound {len(cleanup_files)} items to clean up:")

    for file_path in cleanup_files:
        relative_path = file_path.relative_to(root_dir)

        if not args.verbose and not args.dry_run:
            print(f"Removing: {relative_path}")

        if remove_file_or_dir(file_path, args.dry_run, args.verbose):
            removed_count += 1
        else:
            failed_count += 1

    # Summary
    if args.dry_run:
        print(f"\nDry run complete: {removed_count} items would be removed")
    else:
        print(f"\nCleanup complete: {removed_count} items removed")
        if failed_count > 0:
            print(f"Failed to remove {failed_count} items")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
