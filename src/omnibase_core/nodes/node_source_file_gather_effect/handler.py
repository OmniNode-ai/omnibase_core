# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeSourceFileGatherEffect — source-file-gathering EFFECT handler.

Ports the eligible-file-discovery semantics of the archived
``DirectoryTraverser.find_files`` / ``_find_files_with_config``
(``omnibase_archived/src/omnibase/utils/directory_traverser.py:129-387``)
into a canonical EFFECT node on the def-B ``handle(request) -> response``
shape (OMN-14355). This is the I/O boundary: filesystem reads (glob +
``read_text``) are allowed here so the paired
``node_no_utcnow_check_compute`` node can stay pure over explicit
``(path, source)`` pairs, mirroring the routing_authority EFFECT-boundary
split (``checker_routing_authority.check_routing_authority_at_path``).

Deliberately stripped relative to the oracle: no ``event_bus`` parameter, no
``emit_log_event_sync`` calls, no ``OnexResultModel`` / ``ProtocolEventBus``
coupling — those observability concerns do not belong on a pure I/O-boundary
handler.

Ticket: OMN-14656 (RSD canary — Characterize -> Generate two-node split).
"""

from __future__ import annotations

from pathlib import Path

import pathspec
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_ignore_pattern_source import EnumTraversalMode
from omnibase_core.models.core.model_onex_ignore import ModelOnexIgnore
from omnibase_core.models.nodes.source_file_gather.model_gathered_source_file import (
    ModelGatheredSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_skipped_source_file import (
    ModelSkippedSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)

__all__ = ["NodeSourceFileGatherEffect"]

# Directory names always pruned during the walk (oracle DEFAULT_IGNORE_DIRS,
# directory_traverser.py:90-99).
_DEFAULT_IGNORE_DIRS = (
    ".git",
    ".github",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
)

# Additional directories pruned when source_only=True (OMN-9537, ported from
# node_compliance_scan_compute._VENV_DIR_NAMES). ".venv"/"venv" are already
# covered unconditionally by _DEFAULT_IGNORE_DIRS above; "env"/".env" are not.
_SOURCE_ONLY_EXTRA_IGNORE_DIRS = ("env", ".env")

# Schema-exclusion registry (oracle SchemaExclusionRegistry, directory_traverser.py:38-77).
_SCHEMA_DIRS = frozenset({"schemas", "schema"})
_SCHEMA_PATTERNS = (
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
)


class NodeSourceFileGatherEffect:
    """EFFECT handler that gathers eligible source files with content inline."""

    def handle(
        self, request: ModelSourceFileGatherInput
    ) -> ModelSourceFileGatherOutput:
        """Definition-B canonical entry-point (OMN-14355).

        Typed request in, typed response out — synchronous, no event bus.
        """
        root = Path(request.root)
        if not root.exists() or not root.is_dir():
            # Oracle: non-existent/not-a-dir root returns an empty result
            # (directory_traverser.py:208-209) with no skip records.
            return ModelSourceFileGatherOutput(root=request.root, files=[], skipped=[])

        ignore_patterns = self._build_ignore_patterns(request)
        candidates = self._glob_candidates(root, request)

        files: list[ModelGatheredSourceFile] = []
        skipped: list[ModelSkippedSourceFile] = []
        for file_path in sorted(candidates):
            skip_reason = self._eligibility_skip_reason(
                file_path=file_path,
                root=root,
                request=request,
                ignore_patterns=ignore_patterns,
            )
            if skip_reason is not None:
                skipped.append(
                    ModelSkippedSourceFile(path=str(file_path), reason=skip_reason)
                )
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                size_bytes = file_path.stat().st_size
            except OSError as exc:
                skipped.append(
                    ModelSkippedSourceFile(
                        path=str(file_path), reason=f"read error: {exc}"
                    )
                )
                continue

            files.append(
                ModelGatheredSourceFile(
                    path=str(file_path), size_bytes=size_bytes, source=source
                )
            )

        return ModelSourceFileGatherOutput(
            root=request.root, files=files, skipped=skipped
        )

    # =========================================================================
    # Ignore-pattern assembly
    # =========================================================================

    def _build_ignore_patterns(self, request: ModelSourceFileGatherInput) -> list[str]:
        """Build the effective ignore-pattern list for this request.

        Order: .onexignore-sourced patterns, then default ignore directories,
        then (if source_only) the extra venv-family directories, then the
        caller's exclude_patterns — matching the oracle's assembly order
        (directory_traverser.py:230-234, _load_ignore_patterns_from_sources).
        """
        patterns = self._load_ignore_patterns(request.ignore_file)
        patterns.extend(f"{d}/" for d in _DEFAULT_IGNORE_DIRS)
        if request.source_only:
            patterns.extend(f"{d}/" for d in _SOURCE_ONLY_EXTRA_IGNORE_DIRS)
        if request.exclude_patterns:
            patterns.extend(request.exclude_patterns)
        return patterns

    def _load_ignore_patterns(self, ignore_file: str | None) -> list[str]:
        """Port of ``DirectoryTraverser.load_ignore_patterns``
        (directory_traverser.py:412-462), stripped of event_bus logging.

        Walks up from ``ignore_file`` (or ``Path.cwd()`` when ``None``,
        matching oracle behavior) to the ``.git`` repo-root boundary, reading
        ``.onexignore`` YAML ``all.patterns`` + ``stamper.patterns`` at each
        level, closest directory first (the same iteration order as the
        oracle).
        """
        patterns: list[str] = []
        if ignore_file is None:
            start_dir = Path.cwd()
        else:
            p = Path(ignore_file)
            start_dir = p if p.is_dir() else p.parent

        dirs = [start_dir, *start_dir.parents]
        for d in dirs:
            onexignore = d / ".onexignore"
            if onexignore.exists():
                onexignore_model: ModelOnexIgnore | None
                try:
                    content = onexignore.read_text(encoding="utf-8")
                    raw = yaml.safe_load(content) or {}
                    onexignore_model = ModelOnexIgnore.model_validate(raw)
                except (
                    OSError,
                    TypeError,
                    ValueError,
                    ValidationError,
                    yaml.YAMLError,
                ):
                    onexignore_model = None  # fallback-ok: unreadable/invalid .onexignore contributes no patterns
                if onexignore_model is not None:
                    if onexignore_model.all is not None:
                        patterns.extend(onexignore_model.all.patterns)
                    if onexignore_model.stamper is not None:
                        patterns.extend(onexignore_model.stamper.patterns)
            if (d / ".git").exists():
                break
            if d == d.parent:
                break
        return patterns

    # =========================================================================
    # Glob
    # =========================================================================

    def _glob_candidates(
        self, root: Path, request: ModelSourceFileGatherInput
    ) -> set[Path]:
        """Port of the include-pattern glob loop (directory_traverser.py:236-301).

        ``recursive`` here means "prepend/keep '**/' so glob descends" — it is
        true for both RECURSIVE and SHALLOW because the FLAT/SHALLOW scoping
        itself is enforced afterward in the per-file eligibility filter, not
        in the glob.
        """
        recursive = request.traversal_mode in (
            EnumTraversalMode.RECURSIVE,
            EnumTraversalMode.SHALLOW,
        )

        all_files: set[Path] = set()
        for pattern in request.include_patterns:
            effective_pattern = pattern
            if recursive:
                if not pattern.startswith(("**/", "**")):
                    if pattern.startswith("*."):
                        effective_pattern = f"**/{pattern}"
            elif pattern.startswith("**/"):
                effective_pattern = pattern.replace("**/", "", 1)
            all_files.update(root.glob(effective_pattern))
        return all_files

    # =========================================================================
    # Per-file eligibility (precedence per directory_traverser.py:316-348)
    # =========================================================================

    def _eligibility_skip_reason(
        self,
        file_path: Path,
        root: Path,
        request: ModelSourceFileGatherInput,
        ignore_patterns: list[str],
    ) -> str | None:
        if not file_path.is_file():
            return "not a file"

        if (
            request.traversal_mode == EnumTraversalMode.FLAT
            and file_path.parent != root
        ):
            return "not in directory (FLAT mode)"

        if (
            request.traversal_mode == EnumTraversalMode.SHALLOW
            and file_path.parent != root
            and file_path.parent.parent != root
        ):
            return "not in immediate subdirectory (SHALLOW mode)"

        if self._should_ignore(file_path, ignore_patterns, root):
            return "ignored by pattern"

        if self._is_schema_file(file_path):
            return "schema file"

        if request.max_file_size > 0:
            try:
                file_size = file_path.stat().st_size
            except OSError as exc:
                return f"error checking file size: {exc}"
            if file_size > request.max_file_size:
                return "exceeds max file size"

        return None

    @staticmethod
    def _is_schema_file(path: Path) -> bool:
        """Port of ``SchemaExclusionRegistry.is_schema_file`` (directory_traverser.py:71-77)."""
        if any(part in _SCHEMA_DIRS for part in path.parts):
            return True
        return any(path.match(pat) for pat in _SCHEMA_PATTERNS)

    @staticmethod
    def _should_ignore(path: Path, ignore_patterns: list[str], root_dir: Path) -> bool:
        """Port of ``DirectoryTraverser.should_ignore`` (directory_traverser.py:464-682).

        Uses ``pathspec`` gitwildmatch semantics. ``pathspec`` is a hard
        runtime dependency of omnibase_core (see ``pyproject.toml``) — no
        optional-import fallback.
        """
        if not ignore_patterns:
            return False

        try:
            rel_path = path.relative_to(root_dir).as_posix()
        except ValueError:
            rel_path = path.as_posix()
        rel_path = rel_path.lstrip("/")

        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
        return bool(spec.match_file(rel_path))
