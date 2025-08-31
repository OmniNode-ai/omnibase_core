"""
Filesystem implementation of ProtocolFileWriter.

Writes files to the local filesystem with safety checks.
"""

import contextlib
from pathlib import Path

from omnibase.protocols.types import LogLevel

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)


class UtilityFileSystemWriter:
    """
    Filesystem implementation of file writing protocol.

    Features:
    - Safe file writing with directory creation
    - Atomic multi-file operations
    - Proper error handling
    - Structured logging
    """

    def __init__(self, base_path: Path | None = None):
        """
        Initialize filesystem writer.

        Args:
            base_path: Optional base path for relative file operations
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()

    def write_file(self, path: str | Path, content: str) -> Path:
        """
        Write content to a file, creating directories as needed.

        Args:
            path: Path where to write the file
            content: Content to write

        Returns:
            Path: Actual path where file was written

        Raises:
            IOError: If file cannot be written
        """
        # CRITICAL: Log all file writes with calling context
        import traceback

        call_stack = traceback.format_stack()
        (call_stack[-2].strip() if len(call_stack) > 1 else "Unknown caller")

        for _i, _frame in enumerate(call_stack[-5:]):  # Show last 5 stack frames
            pass

        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.base_path / file_path

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding="utf-8")

            emit_log_event(
                LogLevel.DEBUG,
                f"File written successfully: {file_path}",
                {"path": str(file_path), "size": len(content)},
            )

            return file_path

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to write file: {path}",
                {"path": str(path), "error": str(e)},
            )
            msg = f"Cannot write file {path}: {e}"
            raise OSError(msg)

    def write_files(self, files: list[tuple[str | Path, str]]) -> list[Path]:
        """
        Write multiple files, ensuring all succeed or none are written.

        Args:
            files: List of (path, content) tuples

        Returns:
            List of paths where files were written

        Raises:
            IOError: If any file cannot be written
        """
        # CRITICAL: Log batch file writes with calling context
        import traceback

        call_stack = traceback.format_stack()
        (call_stack[-2].strip() if len(call_stack) > 1 else "Unknown caller")

        written_paths = []

        try:
            # First ensure all directories exist
            for file_path, _ in files:
                path = Path(file_path)
                if not path.is_absolute():
                    path = self.base_path / path
                path.parent.mkdir(parents=True, exist_ok=True)

            # Write all files
            for file_path, content in files:
                written_path = self.write_file(file_path, content)
                written_paths.append(written_path)

            emit_log_event(
                LogLevel.INFO,
                f"Successfully wrote {len(written_paths)} files",
                {"count": len(written_paths)},
            )

            return written_paths

        except Exception as e:
            # Clean up any partially written files
            for path in written_paths:
                with contextlib.suppress(Exception):
                    path.unlink()

            emit_log_event(
                LogLevel.ERROR,
                "Failed to write files atomically",
                {"error": str(e), "attempted": len(files)},
            )
            msg = f"Cannot write files atomically: {e}"
            raise OSError(msg)

    def ensure_directory(self, path: str | Path) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists

        Returns:
            Path: The directory path

        Raises:
            IOError: If directory cannot be created
        """
        try:
            dir_path = Path(path)
            if not dir_path.is_absolute():
                dir_path = self.base_path / dir_path

            dir_path.mkdir(parents=True, exist_ok=True)

            emit_log_event(
                LogLevel.DEBUG,
                f"Directory ensured: {dir_path}",
                {"path": str(dir_path)},
            )

            return dir_path

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to create directory: {path}",
                {"path": str(path), "error": str(e)},
            )
            msg = f"Cannot create directory {path}: {e}"
            raise OSError(msg)

    def delete_file(self, path: str | Path) -> bool:
        """
        Delete a file if it exists.

        Args:
            path: Path to file to delete

        Returns:
            bool: True if file was deleted, False if it didn't exist

        Raises:
            IOError: If file exists but cannot be deleted
        """
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.base_path / file_path

            if file_path.exists():
                file_path.unlink()
                emit_log_event(
                    LogLevel.DEBUG,
                    f"File deleted: {file_path}",
                    {"path": str(file_path)},
                )
                return True

            return False

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to delete file: {path}",
                {"path": str(path), "error": str(e)},
            )
            msg = f"Cannot delete file {path}: {e}"
            raise OSError(msg)
