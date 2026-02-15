#!/usr/bin/env python3
"""
ONEX Repository Cleanup Script

This script removes temporary analysis files, reports, and cache files that should
not be committed to the repository. It's designed to catch common patterns of
files generated during development and analysis.

Usage:
    uv run python scripts/cleanup.py [--dry-run] [--verbose] [--remove-from-git] [--tmp-only]

Options:
    --dry-run           Show what would be removed without removing
    --verbose, -v       Show detailed output
    --remove-from-git   Remove tracked files from git index (for tmp/ cleanup)
    --root DIR          Root directory to clean (default: current directory)
    --tmp-only          Only clean tmp/ directory (preserves caches)
                        Use this for pre-commit/pre-push hooks!

IMPORTANT: For pre-commit/pre-push hooks, ALWAYS use --tmp-only to avoid
invalidating mypy_cache, ruff_cache, pytest_cache which take significant
time to rebuild.
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from re import Pattern

# Configure module logger
logger = logging.getLogger(__name__)

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

# Directories to clean up entirely (FULL cleanup mode only)
# WARNING: These caches take significant time to rebuild!
# Use --tmp-only for pre-commit/pre-push hooks to avoid cache invalidation
CLEANUP_DIRECTORIES_FULL = [
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

# Directories to clean in --tmp-only mode (safe for pre-commit/pre-push)
CLEANUP_DIRECTORIES_TMP_ONLY = [
    "tmp",  # Only temporary files, preserves all caches
]

# Directories to skip entirely during traversal
SKIP_DIRS = {".git", ".venv", "venv", "ENV", "env", "node_modules"}


def compile_patterns(patterns: list[str]) -> list[Pattern[str]]:
    """Compile regex patterns for file matching."""
    return [re.compile(pattern) for pattern in patterns]


def find_cleanup_files(
    root_dir: Path, patterns: list[Pattern[str]], tmp_only: bool = False
) -> list[Path]:
    """Find files matching cleanup patterns.

    Args:
        root_dir: Root directory to search
        patterns: Compiled regex patterns for file matching
        tmp_only: If True, only clean tmp/ directory (preserves caches)
    """
    cleanup_files = []

    # Select which directories to clean based on mode
    cleanup_dirs = (
        CLEANUP_DIRECTORIES_TMP_ONLY if tmp_only else CLEANUP_DIRECTORIES_FULL
    )

    # In tmp_only mode, skip pattern matching entirely - just find tmp dirs
    if tmp_only:
        patterns = []

    for root, dirs, files in os.walk(root_dir):
        root_path = Path(root)

        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        # Check files (only in full mode)
        for file in files:
            file_path = root_path / file
            relative_path = file_path.relative_to(root_dir)

            for pattern in patterns:
                if pattern.search(str(relative_path)):
                    cleanup_files.append(file_path)
                    break

        # Check directories
        for dir_name in dirs[:]:  # Create a copy to modify during iteration
            if dir_name in cleanup_dirs:
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
            check=False,
        )

        if not result.stdout.strip():
            return False  # Not tracked, nothing to do

        if dry_run:
            if verbose:
                logger.info("[DRY RUN] Would remove from git: %s", relative_path)
            return True

        # Remove from git index
        subprocess.run(
            ["git", "rm", "-r", "--cached", "--quiet", str(relative_path)],
            cwd=root_dir,
            check=True,
            capture_output=True,
        )

        if verbose:
            logger.info("Removed from git index: %s", relative_path)
        return True

    except subprocess.CalledProcessError as e:
        # Always log errors at WARNING level regardless of verbose setting
        logger.warning("Git removal failed for %s: %s", path, e)
        return False
    except Exception as e:
        # Always log errors at WARNING level regardless of verbose setting
        logger.warning("Error removing from git %s: %s", path, e)
        return False


def remove_file_or_dir(
    path: Path, dry_run: bool = False, verbose: bool = False
) -> bool:
    """Remove a file or directory safely."""
    try:
        if dry_run:
            if verbose:
                logger.info("[DRY RUN] Would remove: %s", path)
            return True

        if path.is_dir():
            shutil.rmtree(path)
            if verbose:
                logger.info("Removed directory: %s", path)
        else:
            path.unlink()
            if verbose:
                logger.info("Removed file: %s", path)
        return True
    except Exception as e:
        # Always log errors at WARNING level regardless of verbose setting
        logger.warning("Error removing %s: %s", path, e)
        return False


def main() -> int:
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
    parser.add_argument(
        "--tmp-only",
        action="store_true",
        help="Only clean tmp/ directory (preserves mypy/ruff/pytest caches). "
        "Use this for pre-commit/pre-push hooks to avoid cache invalidation.",
    )

    args = parser.parse_args()

    # Check git availability upfront if --remove-from-git is requested
    if args.remove_from_git:
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Use print here since logging is not yet configured
            print("ERROR: git is not available. Cannot use --remove-from-git option.")
            return 1

    # Configure logging based on verbose flag
    # WARNING level is always enabled to capture errors
    # INFO level is enabled only in verbose mode
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    root_dir = Path(args.root).resolve()

    if not root_dir.exists():
        logger.error("Root directory %s does not exist", root_dir)
        return 1

    if args.verbose:
        logger.info("Cleaning up repository: %s", root_dir)
        if args.dry_run:
            logger.info("DRY RUN MODE - No files will be actually removed")
        if args.tmp_only:
            logger.info("TMP-ONLY MODE - Only cleaning tmp/ directory")

    # Compile cleanup patterns
    patterns = compile_patterns(CLEANUP_PATTERNS)

    # Find files to clean up
    cleanup_files = find_cleanup_files(root_dir, patterns, tmp_only=args.tmp_only)

    if not cleanup_files:
        if args.verbose:
            logger.info("No cleanup files found.")
        return 0

    # Sort files for consistent output
    cleanup_files.sort()

    # Remove from git index first (if requested)
    git_removed_count = 0
    if args.remove_from_git:
        if args.verbose:
            logger.info("Removing tracked files from git index...")

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
            print(f"  Removing: {relative_path}")

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
