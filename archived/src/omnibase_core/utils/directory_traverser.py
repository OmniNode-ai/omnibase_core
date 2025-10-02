"""
Directory traversal utility for finding and processing files in directories.
"""

import fnmatch
import importlib
import inspect
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TypeVar

try:
    pathspec: ModuleType | None = importlib.import_module("pathspec")
except ImportError:
    pathspec = None
import contextlib

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums import IgnorePatternSourceEnum, LogLevel, TraversalModeEnum
from omnibase_core.exceptions import OnexError
from omnibase_core.logging.structured import emit_log_event_sync
from omnibase_core.models.core.model_directory_processing_result import (
    ModelDirectoryProcessingResult,
)
from omnibase_core.models.core.model_file_filter import FileFilterModel
from omnibase_core.models.core.model_log_entry import LogModelContext
from omnibase_core.models.core.model_onex_message_result import (
    EnumOnexStatus,
    ModelOnexMessage,
    OnexResultModel,
)
from omnibase_core.models.core.model_tree_sync_result import ModelTreeSyncResult
from omnibase_core.protocol.protocol_directory_traverser import (
    ProtocolDirectoryTraverser,
)
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocol.protocol_file_discovery_source import (
    ProtocolFileDiscoverySource,
)

_COMPONENT_NAME = Path(__file__).stem
T = TypeVar("T")


class SchemaExclusionRegistry:
    """
    Registry for schema exclusion logic. Supports DI and extension.
    By default, excludes files in 'schemas/' directories or with known schema filenames.
    """

    DEFAULT_SCHEMA_DIRS = ["schemas", "schema"]
    DEFAULT_SCHEMA_PATTERNS = [
        "*_schema.yaml",
        "*_schema.yml",
        "*_schema.json",
        "onex_node.yaml",
        "onex_node.json",
        "state_contract.yaml",
        "state_contract.json",
        "tree_format.yaml",
        "tree_format.json",
        "execution_result.yaml",
        "execution_result.json",
    ]

    def __init__(
        self,
        extra_dirs: list[str] | None = None,
        extra_patterns: list[str] | None = None,
    ) -> None:
        self.schema_dirs = set(self.DEFAULT_SCHEMA_DIRS)
        if extra_dirs:
            self.schema_dirs.update(extra_dirs)
        self.schema_patterns = set(self.DEFAULT_SCHEMA_PATTERNS)
        if extra_patterns:
            self.schema_patterns.update(extra_patterns)

    def is_schema_file(self, path: Path) -> bool:
        if any(part in self.schema_dirs for part in path.parts):
            return True
        return any(path.match(pat) for pat in self.schema_patterns)


class DirectoryTraverser(ProtocolDirectoryTraverser, ProtocolFileDiscoverySource):
    """
    Generic directory traversal implementation with filtering capabilities.

    This class implements the ProtocolDirectoryTraverser interface for finding,
    filtering, and processing files in directories. It provides flexible
    pattern matching and error handling.
    """

    DEFAULT_INCLUDE_PATTERNS = ["**/*.yaml", "**/*.yml", "**/*.json"]
    DEFAULT_IGNORE_DIRS = [
        ".git",
        ".github",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        ".venv",
        "venv",
        "node_modules",
    ]

    def __init__(self, *args, event_bus=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_bus = event_bus
        self.result = ModelDirectoryProcessingResult(
            processed_count=0,
            failed_count=0,
            skipped_count=0,
            total_size_bytes=0,
            directory=None,
            filter_config=None,
        )
        self.schema_exclusion_registry = (
            SchemaExclusionRegistry() if event_bus else SchemaExclusionRegistry()
        )

    def reset_counters(self) -> None:
        """Reset file counters."""
        self.result = ModelDirectoryProcessingResult(
            processed_count=0,
            failed_count=0,
            skipped_count=0,
            total_size_bytes=0,
            directory=self.directory if hasattr(self, "directory") else None,
            filter_config=(
                self.filter_config if hasattr(self, "filter_config") else None
            ),
        )

    def find_files(
        self,
        directory: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        recursive: bool = True,
        ignore_file: Path | None = None,
        event_bus: ProtocolEventBus | None = None,
    ) -> set[Path]:
        """
        Find all files matching the given patterns in the directory.

        Args:
            directory: Directory to search
            include_patterns: List of glob patterns to include (e.g., ['**/*.yaml'])
            exclude_patterns: List of glob patterns to exclude (e.g., ['**/.git/**'])
            recursive: Whether to recursively traverse subdirectories
            ignore_file: Path to ignore file (e.g., .onexignore)
            event_bus: ProtocolEventBus for logging

        Returns:
            Set of Path objects for matching files
        """
        filter_config = FileFilterModel(
            traversal_mode=(
                TraversalModeEnum.RECURSIVE if recursive else TraversalModeEnum.FLAT
            ),
            include_patterns=include_patterns or self.DEFAULT_INCLUDE_PATTERNS,
            exclude_patterns=exclude_patterns or [],
            ignore_file=ignore_file,
            ignore_pattern_sources=[
                IgnorePatternSourceEnum.FILE,
                IgnorePatternSourceEnum.DEFAULT,
            ],
            max_file_size=5 * 1024 * 1024,
            max_files=None,
            follow_symlinks=False,
            case_sensitive=False,
        )
        return self._find_files_with_config(directory, filter_config, event_bus)

    def _find_files_with_config(
        self,
        directory: Path,
        filter_config: FileFilterModel,
        event_bus: ProtocolEventBus | None = None,
    ) -> set[Path]:
        """
        Find all files matching filter criteria in the directory.

        Args:
            directory: Directory to search
            filter_config: Configuration for filtering files
            event_bus: ProtocolEventBus for logging

        Returns:
            Set of Path objects for matching files
        """
        if event_bus is None:
            if hasattr(self, "_event_bus") and self._event_bus is not None:
                event_bus = self._event_bus
            else:
                raise OnexError(
                    CoreErrorCode.UNSUPPORTED_OPERATION,
                    "Directory traversal operation not supported in this context.",
                )
        emit_log_event_sync(
            LogLevel.DEBUG,
            "Finding files with config",
            context=LogModelContext(
                calling_module=__name__,
                calling_function="_find_files_with_config",
                calling_line=inspect.currentframe().f_lineno,
                timestamp="auto",
                node_id="directory_traverser",
            ),
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        if not directory.exists() or not directory.is_dir():
            return set()
        self.reset_counters()
        self.result.directory = directory
        self.result.filter_config = filter_config
        recursive = filter_config.traversal_mode in [
            TraversalModeEnum.RECURSIVE,
            TraversalModeEnum.SHALLOW,
        ]
        emit_log_event_sync(
            LogLevel.DEBUG,
            "Traversal mode determined",
            context=LogModelContext(
                calling_module=__name__,
                calling_function="_find_files_with_config",
                calling_line=inspect.currentframe().f_lineno,
                timestamp="auto",
                node_id="directory_traverser",
            ),
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        ignore_patterns = self._load_ignore_patterns_from_sources(
            filter_config.ignore_pattern_sources,
            filter_config.ignore_file,
        )
        if filter_config.exclude_patterns:
            ignore_patterns.extend(filter_config.exclude_patterns)
        all_files: set[Path] = set()
        for pattern in filter_config.include_patterns:
            if recursive:
                if pattern.startswith(("**/", "**")):
                    pass
                elif pattern.startswith("*."):
                    pattern = f"**/{pattern}"
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    "Glob pattern matching (recursive)",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="_find_files_with_config",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                matched = list(directory.glob(pattern))
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    "Glob pattern results",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="_find_files_with_config",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                all_files.update(matched)
            else:
                if pattern.startswith("**/"):
                    pattern = pattern.replace("**/", "")
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    "Glob pattern matching (non-recursive)",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="_find_files_with_config",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                matched = list(directory.glob(pattern))
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    "Glob pattern results",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="_find_files_with_config",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                all_files.update(matched)
        emit_log_event_sync(
            LogLevel.DEBUG,
            "All files matched by include patterns",
            context=LogModelContext(
                calling_module=__name__,
                calling_function="_find_files_with_config",
                calling_line=inspect.currentframe().f_lineno,
                timestamp="auto",
                node_id="directory_traverser",
            ),
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        eligible_files: set[Path] = set()
        for file_path in all_files:
            skip_reason = None
            if not file_path.is_file():
                skip_reason = "not a file"
            elif (
                filter_config.traversal_mode == TraversalModeEnum.FLAT
                and file_path.parent != directory
            ):
                skip_reason = "not in directory (FLAT mode)"
            elif (
                filter_config.traversal_mode == TraversalModeEnum.SHALLOW
                and directory not in (file_path.parent, file_path.parent.parent)
            ):
                skip_reason = "not in immediate subdirectory (SHALLOW mode)"
            elif self.should_ignore(
                file_path,
                ignore_patterns,
                root_dir=directory,
                event_bus=event_bus,
            ):
                skip_reason = "ignored by pattern"
            elif self.schema_exclusion_registry.is_schema_file(file_path):
                skip_reason = "schema file"
            elif filter_config.max_file_size > 0:
                try:
                    file_size = file_path.stat().st_size
                    if file_size > filter_config.max_file_size:
                        skip_reason = "exceeds max file size"
                except OSError as e:
                    skip_reason = f"error checking file size: {e}"
            if (
                filter_config.max_files is not None
                and len(eligible_files) >= filter_config.max_files
            ):
                skip_reason = "max_files limit reached"
            if skip_reason:
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    "Skipping file",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="_find_files_with_config",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                self.result.skipped_count += 1
                self.result.skipped_files.add(file_path)
                from omnibase_core.models.core.model_skipped_file_reason import (
                    ModelSkippedFileReason,
                )

                self.result.skipped_file_reasons.append(
                    ModelSkippedFileReason(file=file_path, reason=skip_reason),
                )
                continue
            eligible_files.add(file_path)
        emit_log_event_sync(
            LogLevel.DEBUG,
            "Eligible files found",
            context=LogModelContext(
                calling_module=__name__,
                calling_function="_find_files_with_config",
                calling_line=inspect.currentframe().f_lineno,
                timestamp="auto",
                node_id="directory_traverser",
            ),
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        return eligible_files

    def _load_ignore_patterns_from_sources(
        self,
        sources: list[IgnorePatternSourceEnum],
        ignore_file: Path | None = None,
    ) -> list[str]:
        """
        Load ignore patterns from multiple sources.

        Args:
            sources: List of sources to check for ignore patterns
            ignore_file: Path to specific ignore file

        Returns:
            List of ignore patterns
        """
        patterns = []
        if IgnorePatternSourceEnum.FILE in sources:
            patterns.extend(self.load_ignore_patterns(ignore_file))
        if (
            IgnorePatternSourceEnum.DEFAULT in sources
            or IgnorePatternSourceEnum.DIRECTORY in sources
        ):
            patterns.extend([f"{d}/" for d in self.DEFAULT_IGNORE_DIRS])
        return patterns

    def load_ignore_patterns(self, ignore_file: Path | None = None) -> list[str]:
        """
        Load ignore patterns from .onexignore files, walking up parent directories from the file's directory to the repo root.
        Args:
            ignore_file: Path to a file or directory. If a file, start from its parent directory. If a directory, start from there.
        Returns:
            List of ignore patterns as strings, with child directory patterns taking precedence.
        """
        from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
        from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

        patterns = []
        if ignore_file is None:
            start_dir = Path.cwd()
        else:
            p = Path(ignore_file)
            start_dir = p if p.is_dir() else p.parent
        dirs = [start_dir, *list(start_dir.parents)]
        for d in dirs:
            onexignore = d / ".onexignore"
            if onexignore.exists():
                try:
                    # Load and validate YAML using Pydantic model
                    yaml_model = load_and_validate_yaml_model(
                        onexignore,
                        ModelGenericYaml,
                    )
                    data = yaml_model.model_dump()
                    if data:
                        if "all" in data and data["all"] and "patterns" in data["all"]:
                            patterns.extend(data["all"]["patterns"])
                        if (
                            "stamper" in data
                            and data["stamper"]
                            and "patterns" in data["stamper"]
                        ):
                            patterns.extend(data["stamper"]["patterns"])
                except Exception:
                    emit_log_event_sync(
                        LogLevel.WARNING,
                        "Failed to load onexignore file",
                        context=LogModelContext(
                            calling_module=__name__,
                            calling_function="load_ignore_patterns",
                            calling_line=inspect.currentframe().f_lineno,
                            timestamp="auto",
                            node_id="directory_traverser",
                        ),
                        node_id="directory_traverser",
                        event_bus=self._event_bus,
                    )
            if (d / ".git").exists():
                break
            if d == d.parent:
                break
        return patterns

    def should_ignore(
        self,
        path: Path,
        ignore_patterns: list[str],
        root_dir: Path | None = None,
        event_bus: ProtocolEventBus | None = None,
    ) -> bool:
        """
        Check if a file should be ignored based on patterns.

        Args:
            path: Path to check
            ignore_patterns: List of ignore patterns
            root_dir: Root directory for relative matching (default: cwd)
            event_bus: ProtocolEventBus for logging

        Returns:
            True if the file should be ignored, False otherwise
        """
        if event_bus is None:
            if hasattr(self, "_event_bus") and self._event_bus is not None:
                event_bus = self._event_bus
            else:
                raise OnexError(
                    CoreErrorCode.UNSUPPORTED_OPERATION,
                    "Directory traversal operation not supported in this context.",
                )
        if not ignore_patterns:
            emit_log_event_sync(
                LogLevel.DEBUG,
                "No ignore patterns provided",
                context=LogModelContext(
                    calling_module=__name__,
                    calling_function="should_ignore",
                    calling_line=inspect.currentframe().f_lineno,
                    timestamp="auto",
                    node_id="directory_traverser",
                ),
                node_id="directory_traverser",
                event_bus=event_bus,
            )
            return False
        if root_dir is None:
            root_dir = Path.cwd()
        try:
            rel_path = str(path.relative_to(root_dir).as_posix())
        except (ValueError, OnexError):
            rel_path = str(path.as_posix())
        rel_path = rel_path.lstrip("/")
        emit_log_event_sync(
            LogLevel.DEBUG,
            "Checking file against ignore patterns",
            context=LogModelContext(
                calling_module=__name__,
                calling_function="should_ignore",
                calling_line=inspect.currentframe().f_lineno,
                timestamp="auto",
                node_id="directory_traverser",
            ),
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        if pathspec:
            emit_log_event_sync(
                LogLevel.DEBUG,
                "Using pathspec for pattern matching",
                context=LogModelContext(
                    calling_module=__name__,
                    calling_function="should_ignore",
                    calling_line=inspect.currentframe().f_lineno,
                    timestamp="auto",
                    node_id="directory_traverser",
                ),
                node_id="directory_traverser",
                event_bus=event_bus,
            )
            spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
            matched = spec.match_file(rel_path)
            emit_log_event_sync(
                LogLevel.DEBUG,
                "Pathspec pattern matching result",
                context=LogModelContext(
                    calling_module=__name__,
                    calling_function="should_ignore",
                    calling_line=inspect.currentframe().f_lineno,
                    timestamp="auto",
                    node_id="directory_traverser",
                ),
                node_id="directory_traverser",
                event_bus=event_bus,
            )
            return bool(matched)
        for pattern in ignore_patterns:
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"[should_ignore] Checking pattern '{pattern}' for {rel_path}",
                context=LogModelContext(
                    calling_module=__name__,
                    calling_function="should_ignore",
                    calling_line=inspect.currentframe().f_lineno,
                    timestamp="auto",
                    node_id="directory_traverser",
                ),
                node_id="directory_traverser",
                event_bus=event_bus,
            )
            if pattern.endswith("/"):
                dir_name = pattern.rstrip("/")
                parts = rel_path.split("/")
                if dir_name in parts[:-1]:
                    emit_log_event_sync(
                        LogLevel.DEBUG,
                        f"[should_ignore] {rel_path} IGNORED due to directory pattern {pattern} (in parts)",
                        context=LogModelContext(
                            calling_module=__name__,
                            calling_function="should_ignore",
                            calling_line=inspect.currentframe().f_lineno,
                            timestamp="auto",
                            node_id="directory_traverser",
                        ),
                        node_id="directory_traverser",
                        event_bus=event_bus,
                    )
                    return True
                for parent in path.parents:
                    if parent.name == dir_name:
                        emit_log_event_sync(
                            LogLevel.DEBUG,
                            f"[should_ignore] {rel_path} IGNORED due to parent directory {parent} matching {dir_name}",
                            context=LogModelContext(
                                calling_module=__name__,
                                calling_function="should_ignore",
                                calling_line=__import__("inspect")
                                .currentframe()
                                .f_lineno,
                                timestamp="auto",
                                node_id="directory_traverser",
                            ),
                            node_id="directory_traverser",
                            event_bus=event_bus,
                        )
                        return True
                if rel_path.startswith(dir_name + "/"):
                    emit_log_event_sync(
                        LogLevel.DEBUG,
                        f"[should_ignore] {rel_path} IGNORED due to rel_path starting with {dir_name}/",
                        context=LogModelContext(
                            calling_module=__name__,
                            calling_function="should_ignore",
                            calling_line=inspect.currentframe().f_lineno,
                            timestamp="auto",
                            node_id="directory_traverser",
                        ),
                        node_id="directory_traverser",
                        event_bus=event_bus,
                    )
                    return True
            if fnmatch.fnmatch(rel_path, pattern):
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    f"[should_ignore] {rel_path} IGNORED by fnmatch on rel_path with pattern '{pattern}'",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="should_ignore",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                return True
            if fnmatch.fnmatch(path.name, pattern):
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    f"[should_ignore] {rel_path} IGNORED by fnmatch on path.name with pattern '{pattern}'",
                    context=LogModelContext(
                        calling_module=__name__,
                        calling_function="should_ignore",
                        calling_line=inspect.currentframe().f_lineno,
                        timestamp="auto",
                        node_id="directory_traverser",
                    ),
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                return True
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"[should_ignore] {rel_path} NOT ignored by pattern '{pattern}'",
                context=LogModelContext(
                    calling_module=__name__,
                    calling_function="should_ignore",
                    calling_line=inspect.currentframe().f_lineno,
                    timestamp="auto",
                    node_id="directory_traverser",
                ),
                node_id="directory_traverser",
                event_bus=event_bus,
            )
        emit_log_event_sync(
            LogLevel.DEBUG,
            f"[should_ignore] {rel_path} is NOT ignored by any pattern.",
            context=LogModelContext(
                calling_module=__name__,
                calling_function="should_ignore",
                calling_line=inspect.currentframe().f_lineno,
                timestamp="auto",
                node_id="directory_traverser",
            ),
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        return False

    def process_directory(
        self,
        directory: Path,
        processor: Callable[[Path], T],
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        recursive: bool = True,
        ignore_file: Path | None = None,
        dry_run: bool = False,
        max_file_size: int | None = None,
        event_bus: ProtocolEventBus | None = None,
    ) -> OnexResultModel:
        """
        Process all eligible files in a directory using the provided processor function.

        Args:
            directory: Directory to process
            processor: Callable that processes each file and returns a result
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            recursive: Whether to recursively traverse subdirectories
            ignore_file: Path to ignore file (e.g., .onexignore)
            dry_run: Whether to perform a dry run (don't modify files)
            max_file_size: Maximum file size in bytes to process
            event_bus: ProtocolEventBus for logging

        Returns:
            OnexResultModel with aggregate results
        """
        if event_bus is None:
            if hasattr(self, "_event_bus") and self._event_bus is not None:
                event_bus = self._event_bus
            else:
                raise OnexError(
                    CoreErrorCode.UNSUPPORTED_OPERATION,
                    "Directory traversal operation not supported in this context.",
                )
        emit_log_event_sync(
            LogLevel.DEBUG,
            f"[process_directory] directory={directory}",
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        emit_log_event_sync(
            LogLevel.DEBUG,
            f"[process_directory] include_patterns={include_patterns}",
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        emit_log_event_sync(
            LogLevel.DEBUG,
            f"[process_directory] exclude_patterns={exclude_patterns}",
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        if not directory.exists():
            return OnexResultModel(
                status=EnumOnexStatus.ERROR,
                target=str(directory),
                messages=[
                    ModelOnexMessage(
                        summary=f"Directory does not exist: {directory}",
                        level=LogLevel.ERROR,
                        file=None,
                        line=None,
                        details=None,
                        code=None,
                        context=None,
                        timestamp=None,
                        type=None,
                    ),
                ],
            )
        if not directory.is_dir():
            return OnexResultModel(
                status=EnumOnexStatus.ERROR,
                target=str(directory),
                messages=[
                    ModelOnexMessage(
                        summary=f"Path is not a directory: {directory}",
                        level=LogLevel.ERROR,
                        file=None,
                        line=None,
                        details=None,
                        code=None,
                        context=None,
                        timestamp=None,
                        type=None,
                    ),
                ],
            )
        filter_config = FileFilterModel(
            traversal_mode=(
                TraversalModeEnum.RECURSIVE if recursive else TraversalModeEnum.FLAT
            ),
            include_patterns=include_patterns or self.DEFAULT_INCLUDE_PATTERNS,
            exclude_patterns=exclude_patterns or [],
            ignore_file=ignore_file,
            max_file_size=max_file_size or 5 * 1024 * 1024,
            max_files=None,
            follow_symlinks=False,
            case_sensitive=False,
            ignore_pattern_sources=[
                IgnorePatternSourceEnum.FILE,
                IgnorePatternSourceEnum.DEFAULT,
            ],
        )
        eligible_files: set[Path] = self.find_files(
            directory,
            filter_config.include_patterns,
            filter_config.exclude_patterns,
            recursive,
            filter_config.ignore_file,
            event_bus=event_bus,
        )
        emit_log_event_sync(
            LogLevel.DEBUG,
            f"[process_directory] eligible_files={list(eligible_files)}",
            node_id="directory_traverser",
            event_bus=event_bus,
        )
        results: list[OnexResultModel] = []
        for file_path in eligible_files:
            try:
                if dry_run:
                    emit_log_event_sync(
                        LogLevel.INFO,
                        f"[DRY RUN] Would process: {file_path}",
                        node_id="directory_traverser",
                        event_bus=event_bus,
                    )
                    self.result.processed_count += 1
                    self.result.processed_files.add(file_path)
                else:
                    result = processor(file_path)
                    if isinstance(result, OnexResultModel):
                        results.append(result)
                    else:
                        results.append(
                            OnexResultModel(
                                status=EnumOnexStatus.SUCCESS,
                                target=str(file_path),
                                messages=[],
                            ),
                        )
                    self.result.processed_count += 1
                    self.result.processed_files.add(file_path)
                    with contextlib.suppress(OSError):
                        self.result.total_size_bytes += file_path.stat().st_size
            except Exception as e:
                emit_log_event_sync(
                    LogLevel.ERROR,
                    f"Error processing {file_path}: {e!s}",
                    node_id="directory_traverser",
                    event_bus=event_bus,
                )
                self.result.failed_count += 1
                self.result.failed_files.add(file_path)
                results.append(
                    OnexResultModel(
                        status=EnumOnexStatus.ERROR,
                        target=str(file_path),
                        messages=[
                            ModelOnexMessage(
                                summary=f"Error processing file: {e!s}",
                                level=LogLevel.ERROR,
                                file=None,
                                line=None,
                                details=None,
                                code=None,
                                context=None,
                                timestamp=None,
                                type=None,
                            ),
                        ],
                    ),
                )
        if not eligible_files:
            return OnexResultModel(
                status=EnumOnexStatus.WARNING,
                target=str(directory),
                messages=[
                    ModelOnexMessage(
                        summary=f"No eligible files found in {directory}",
                        level=LogLevel.WARNING,
                        file=None,
                        line=None,
                        details=None,
                        code=None,
                        context=None,
                        timestamp=None,
                        type=None,
                    ),
                ],
                metadata={
                    "processed": self.result.processed_count,
                    "failed": self.result.failed_count,
                    "skipped": self.result.skipped_count,
                },
            )
        status = EnumOnexStatus.SUCCESS
        if self.result.failed_count > 0:
            status = EnumOnexStatus.ERROR
        elif self.result.processed_count == 0:
            status = EnumOnexStatus.WARNING
        return OnexResultModel(
            status=status,
            target=str(directory),
            messages=[
                ModelOnexMessage(
                    summary=f"Processed {self.result.processed_count} files, {self.result.failed_count} failed, {self.result.skipped_count} skipped",
                    level=(
                        LogLevel.INFO
                        if status == EnumOnexStatus.SUCCESS
                        else (
                            LogLevel.WARNING
                            if status == EnumOnexStatus.WARNING
                            else LogLevel.ERROR
                        )
                    ),
                    file=None,
                    line=None,
                    details=None,
                    code=None,
                    context=None,
                    timestamp=None,
                    type=None,
                ),
            ],
            metadata={
                "processed": self.result.processed_count,
                "failed": self.result.failed_count,
                "skipped": self.result.skipped_count,
                "size_bytes": self.result.total_size_bytes,
                "skipped_files": list(self.result.skipped_files),
                "skipped_file_reasons": [
                    str(reason) for reason in self.result.skipped_file_reasons
                ],
            },
        )

    def validate_tree_sync(
        self,
        directory: Path,
        tree_file: Path,
    ) -> ModelTreeSyncResult:
        """
        ProtocolFileDiscoverySource compliance: validate .tree sync (not supported in filesystem mode).
        This is a protocol stub; always raises NotImplementedError.
        """
        msg = "validate_tree_sync is not supported in filesystem mode."
        raise NotImplementedError(
            msg,
        )

    def get_canonical_files_from_tree(self, tree_file: Path) -> set[Path]:
        """
        ProtocolFileDiscoverySource compliance: get canonical files from .tree (not supported in filesystem mode).
        This is a protocol stub; always raises NotImplementedError.
        """
        msg = "get_canonical_files_from_tree is not supported in filesystem mode."
        raise NotImplementedError(
            msg,
        )

    def discover_files(
        self,
        directory: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        ignore_file: Path | None = None,
        event_bus: ProtocolEventBus | None = None,
    ) -> set[Path]:
        """
        ProtocolFileDiscoverySource compliance: discover files in directory.
        """
        return self.find_files(
            directory,
            include_patterns,
            exclude_patterns,
            True,
            ignore_file,
            event_bus=self._event_bus,
        )
