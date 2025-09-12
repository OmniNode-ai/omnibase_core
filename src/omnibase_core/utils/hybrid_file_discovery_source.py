# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.782144'
# description: Stamped by ToolPython
# entrypoint: python://hybrid_file_discovery_source
# hash: 3f0ee5a482b1e31b9cf10dfe7186bb67e2354b0103efc3132e56f70b0e2e199b
# last_modified_at: '2025-05-29T14:14:00.960897+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: hybrid_file_discovery_source.py
# namespace: python://omnibase.utils.hybrid_file_discovery_source
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 9f5d3bca-750e-4c21-b256-ef19234bcfbc
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Hybrid file discovery source for stamping/validation tools.
Combines filesystem and .tree-based discovery, with drift detection and enforcement.
Implements ProtocolFileDiscoverySource.
"""

from pathlib import Path

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.core_structured_logging import emit_log_event_sync
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.exceptions import OnexError
from omnibase_core.models.core.model_tree_sync_result import (
    ModelTreeSyncResult,
    TreeSyncStatusEnum,
)
from omnibase_core.protocol.protocol_file_discovery_source import (
    ProtocolFileDiscoverySource,
)
from omnibase_core.utils.directory_traverser import DirectoryTraverser
from omnibase_core.utils.tree_file_discovery_source import TreeFileDiscoverySource


class HybridFileDiscoverySource(ProtocolFileDiscoverySource):
    """
    Hybrid file discovery source: uses filesystem, but cross-checks with .tree if present.
    Warns or errors on drift depending on strict_mode.
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.fs_source = DirectoryTraverser(event_bus=None)
        self.tree_source = TreeFileDiscoverySource()

    def discover_files(
        self,
        directory: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        ignore_file: Path | None = None,
        event_bus=None,
    ) -> set[Path]:
        """
        Discover files using filesystem, but cross-check with .tree if present.
        Warn or error on drift depending on strict_mode.
        """
        tree_file = directory / ".tree"
        files = self.fs_source.find_files(
            directory,
            include_patterns,
            exclude_patterns,
            True,
            ignore_file,
            event_bus=event_bus,
        )
        if tree_file.exists():
            sync_result = self.validate_tree_sync(directory, tree_file)
            if sync_result.status == TreeSyncStatusEnum.DRIFT:
                msg = "; ".join(m.summary for m in sync_result.messages)
                if self.strict_mode:
                    msg = f"Drift detected between filesystem and .tree: {msg}"
                    raise OnexError(
                        msg,
                        CoreErrorCode.VALIDATION_FAILED,
                    )
                emit_log_event_sync(
                    LogLevel.WARNING,
                    f"[WARNING] Drift detected between filesystem and .tree: {msg}",
                    context=None,
                    node_id="hybrid_file_discovery_source",
                    event_bus=event_bus,
                )
            # Optionally, filter to only files in .tree if strict_mode
            if self.strict_mode:
                files = files & self.tree_source.get_canonical_files_from_tree(
                    tree_file,
                )
        return files

    def validate_tree_sync(
        self,
        directory: Path,
        tree_file: Path,
    ) -> ModelTreeSyncResult:
        """
        Validate that the .tree file and filesystem are in sync.
        """
        return self.tree_source.validate_tree_sync(directory, tree_file)

    def get_canonical_files_from_tree(self, tree_file: Path) -> set[Path]:
        """
        Get canonical files from .tree file.
        """
        return self.tree_source.get_canonical_files_from_tree(tree_file)
