#!/usr/bin/env python3
"""
Git Lock Manager for Workspace Janitor Service.

SEC-WORKSPACE-003: Janitor Cleanup Service - Utility for managing Git locks
with stale lock detection and cleanup capabilities.
"""

import os
import time
from datetime import datetime
from pathlib import Path

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.models.model_git_lock_summary import ModelGitLockSummary


class ModelGitLockInfo:
    """Information about a Git lock file."""

    def __init__(
        self,
        lock_file_path: Path,
        repository_path: Path,
        created_timestamp: float,
        lock_type: str,
        process_id: int | None = None,
    ):
        self.lock_file_path = lock_file_path
        self.repository_path = repository_path
        self.created_timestamp = created_timestamp
        self.lock_type = lock_type
        self.process_id = process_id

    @property
    def age_seconds(self) -> float:
        """Get the age of the lock in seconds."""
        return time.time() - self.created_timestamp

    @property
    def is_stale(self) -> bool:
        """Check if the lock is considered stale (older than 30 minutes by default)."""
        return self.age_seconds > 1800  # 30 minutes

    @property
    def created_datetime(self) -> datetime:
        """Get the creation time as a datetime object."""
        return datetime.fromtimestamp(self.created_timestamp)


class GitLockManager:
    """
    Manager for Git lock file operations with stale lock detection and cleanup.

    This utility handles detection, analysis, and cleanup of Git lock files that
    may be left behind by interrupted Git operations, preventing repository access.
    """

    # Common Git lock files
    LOCK_FILES = [
        ".git/index.lock",
        ".git/HEAD.lock",
        ".git/config.lock",
        ".git/refs/heads/*.lock",
        ".git/refs/remotes/origin/*.lock",
        ".git/logs/HEAD.lock",
        ".git/logs/refs/heads/*.lock",
        ".git/packed-refs.lock",
        ".git/COMMIT_EDITMSG.lock",
        ".git/MERGE_HEAD.lock",
        ".git/CHERRY_PICK_HEAD.lock",
        ".git/REVERT_HEAD.lock",
    ]

    def __init__(self, base_workspace_path: Path | None = None):
        """
        Initialize the Git lock manager.

        Args:
            base_workspace_path: Base path for workspace repositories
        """
        self.base_workspace_path = base_workspace_path or Path.cwd()
        self.stale_threshold_seconds = 1800  # 30 minutes default
        self.max_lock_age_seconds = 86400  # 24 hours absolute max

    def find_all_git_locks(
        self,
        search_path: Path | None = None,
    ) -> list[ModelGitLockInfo]:
        """
        Find all Git lock files in the specified path or base workspace path.

        Args:
            search_path: Path to search for Git locks (defaults to base workspace path)

        Returns:
            List of Git lock information objects

        Raises:
            OnexError: If search operation fails
        """
        search_root = search_path or self.base_workspace_path

        try:
            lock_files = []

            # Find all .git directories first
            for git_dir in search_root.rglob(".git"):
                if git_dir.is_dir():
                    repository_path = git_dir.parent
                    locks_found = self._find_locks_in_repository(repository_path)
                    lock_files.extend(locks_found)

            return lock_files

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to find Git locks in {search_root}: {e!s}",
                context={"search_path": str(search_root)},
                cause=e,
            )

    def _find_locks_in_repository(self, repo_path: Path) -> list[ModelGitLockInfo]:
        """
        Find all lock files in a specific Git repository.

        Args:
            repo_path: Path to the Git repository

        Returns:
            List of Git lock information objects
        """
        lock_files: list[ModelGitLockInfo] = []
        git_dir = repo_path / ".git"

        if not git_dir.exists():
            return lock_files

        # Check for common lock files
        for lock_pattern in self.LOCK_FILES:
            if "*" in lock_pattern:
                # Handle wildcard patterns
                pattern_parts = lock_pattern.split("/")
                current_path = repo_path

                for part in pattern_parts:
                    if "*" in part:
                        # Find matching files in current directory
                        if current_path.exists():
                            pattern = part.replace("*", "")
                            for file_path in current_path.iterdir():
                                if file_path.name.endswith(pattern):
                                    lock_info = self._create_lock_info(
                                        file_path,
                                        repo_path,
                                    )
                                    if lock_info:
                                        lock_files.append(lock_info)
                    else:
                        current_path = current_path / part
            else:
                # Direct file path
                lock_file_path = repo_path / lock_pattern
                if lock_file_path.exists():
                    lock_info = self._create_lock_info(lock_file_path, repo_path)
                    if lock_info:
                        lock_files.append(lock_info)

        return lock_files

    def _create_lock_info(
        self,
        lock_file_path: Path,
        repo_path: Path,
    ) -> ModelGitLockInfo | None:
        """
        Create a lock info object from a lock file path.

        Args:
            lock_file_path: Path to the lock file
            repo_path: Path to the repository

        Returns:
            Git lock information object or None if invalid
        """
        try:
            if not lock_file_path.exists():
                return None

            stat = lock_file_path.stat()
            created_timestamp = stat.st_mtime

            # Determine lock type from filename
            lock_type = self._get_lock_type(lock_file_path)

            # Try to read process ID if available
            process_id = self._extract_process_id(lock_file_path)

            return ModelGitLockInfo(
                lock_file_path=lock_file_path,
                repository_path=repo_path,
                created_timestamp=created_timestamp,
                lock_type=lock_type,
                process_id=process_id,
            )

        except Exception:
            # Skip files we can't read
            return None

    def _get_lock_type(self, lock_file_path: Path) -> str:
        """
        Determine the type of Git lock from the file path.

        Args:
            lock_file_path: Path to the lock file

        Returns:
            Lock type string
        """
        filename = lock_file_path.name

        # Check path-specific patterns first (more specific)
        if filename.endswith(".lock") and "logs/" in str(lock_file_path):
            return "log"
        if filename.endswith(".lock") and "refs/" in str(lock_file_path):
            return "reference"
        # Then check filename patterns (less specific)
        if filename == "index.lock":
            return "index"
        if filename == "HEAD.lock":
            return "head"
        if filename == "config.lock":
            return "config"
        if "COMMIT_EDITMSG.lock" in filename:
            return "commit"
        if "MERGE_HEAD.lock" in filename:
            return "merge"
        if "CHERRY_PICK_HEAD.lock" in filename:
            return "cherry_pick"
        if "REVERT_HEAD.lock" in filename:
            return "revert"
        if "packed-refs.lock" in filename:
            return "packed_refs"
        return "unknown"

    def _extract_process_id(self, lock_file_path: Path) -> int | None:
        """
        Try to extract process ID from lock file content.

        Args:
            lock_file_path: Path to the lock file

        Returns:
            Process ID if found, None otherwise
        """
        try:
            # Some Git lock files contain process information
            content = lock_file_path.read_text(encoding="utf-8", errors="ignore")

            # Look for PID patterns (this is Git implementation specific)
            lines = content.strip().split("\n")
            for line in lines:
                if line.isdigit():
                    return int(line)

            return None
        except Exception:
            return None

    def find_stale_locks(
        self,
        search_path: Path | None = None,
        stale_threshold_seconds: int | None = None,
    ) -> list[ModelGitLockInfo]:
        """
        Find all stale Git lock files.

        Args:
            search_path: Path to search for locks
            stale_threshold_seconds: Custom threshold for considering locks stale

        Returns:
            List of stale Git lock information objects

        Raises:
            OnexError: If search operation fails
        """
        threshold = stale_threshold_seconds or self.stale_threshold_seconds
        all_locks = self.find_all_git_locks(search_path)

        stale_locks = []
        for lock in all_locks:
            if lock.age_seconds > threshold:
                # Additional validation - check if process is still running
                if lock.process_id and self._is_process_running(lock.process_id):
                    continue  # Process still active, not stale

                stale_locks.append(lock)

        return stale_locks

    def _is_process_running(self, process_id: int) -> bool:
        """
        Check if a process with the given ID is still running.

        Args:
            process_id: Process ID to check

        Returns:
            True if process is running, False otherwise
        """
        try:
            # On Unix systems, sending signal 0 checks if process exists
            os.kill(process_id, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def cleanup_stale_locks(
        self,
        search_path: Path | None = None,
        stale_threshold_seconds: int | None = None,
        dry_run: bool = False,
    ) -> tuple[int, list[str], list[str]]:
        """
        Clean up stale Git lock files.

        Args:
            search_path: Path to search for locks
            stale_threshold_seconds: Custom threshold for considering locks stale
            dry_run: If True, only report what would be cleaned, don't actually clean

        Returns:
            Tuple of (locks_cleaned_count, success_messages, error_messages)

        Raises:
            OnexError: If cleanup operation fails critically
        """
        try:
            stale_locks = self.find_stale_locks(search_path, stale_threshold_seconds)

            cleaned_count = 0
            success_messages = []
            error_messages = []

            for lock in stale_locks:
                try:
                    if dry_run:
                        success_messages.append(
                            f"Would remove stale {lock.lock_type} lock: {lock.lock_file_path} "
                            f"(age: {lock.age_seconds:.1f}s)",
                        )
                        cleaned_count += 1
                    else:
                        # Attempt to remove the lock file
                        lock.lock_file_path.unlink()
                        cleaned_count += 1
                        success_messages.append(
                            f"Removed stale {lock.lock_type} lock: {lock.lock_file_path} "
                            f"(age: {lock.age_seconds:.1f}s)",
                        )

                except Exception as e:
                    error_messages.append(
                        f"Failed to remove lock {lock.lock_file_path}: {e!s}",
                    )

            return cleaned_count, success_messages, error_messages

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to cleanup stale Git locks: {e!s}",
                context={
                    "search_path": str(search_path) if search_path else None,
                    "dry_run": dry_run,
                },
                cause=e,
            )

    def is_repository_locked(self, repo_path: Path) -> bool:
        """
        Check if a Git repository has any active locks.

        Args:
            repo_path: Path to the Git repository

        Returns:
            True if repository has active locks, False otherwise
        """
        locks = self._find_locks_in_repository(repo_path)
        return len(locks) > 0

    def get_lock_summary(
        self,
        search_path: Path | None = None,
    ) -> ModelGitLockSummary:
        """
        Get a summary of Git locks by type.

        Args:
            search_path: Path to search for locks

        Returns:
            Git lock summary model with lock type counts
        """
        all_locks = self.find_all_git_locks(search_path)

        by_type_summary: dict[str, int] = {}
        stale_count = 0

        for lock in all_locks:
            # Count by type
            if lock.lock_type not in by_type_summary:
                by_type_summary[lock.lock_type] = 0
            by_type_summary[lock.lock_type] += 1

            # Count stale locks
            if lock.is_stale:
                stale_count += 1

        return ModelGitLockSummary(
            total_locks=len(all_locks),
            stale_locks=stale_count,
            by_type=by_type_summary,
        )

    def set_stale_threshold(self, threshold_seconds: int) -> None:
        """
        Set the threshold for considering locks stale.

        Args:
            threshold_seconds: Threshold in seconds (must be at least 300 - 5 minutes)
        """
        if threshold_seconds < 300:  # Minimum 5 minutes
            raise OnexError(
                error_code=CoreErrorCode.INVALID_PARAMETER,
                message="Stale threshold must be at least 300 seconds (5 minutes)",
                context={"provided_threshold": threshold_seconds},
            )

        self.stale_threshold_seconds = threshold_seconds
