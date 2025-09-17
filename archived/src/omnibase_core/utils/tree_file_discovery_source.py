# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.813870'
# description: Stamped by ToolPython
# entrypoint: python://tree_file_discovery_source
# hash: 1a4163e9b71a42bce66cc2baa24dffe7b9fb29486800fe75cc877063030c586f
# last_modified_at: '2025-05-29T14:14:00.982515+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: tree_file_discovery_source.py
# namespace: python://omnibase.utils.tree_file_discovery_source
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: f93a3f4c-64d9-48b7-976b-f50982fdd89d
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
.tree-based file discovery source for stamping/validation tools.
Implements ProtocolFileDiscoverySource.
"""

from pathlib import Path

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_onex_message_result import ModelOnexMessage
from omnibase_core.models.core.model_tree_sync_result import (
    ModelTreeSyncResult,
    TreeSyncStatusEnum,
)
from omnibase_core.protocol.protocol_file_discovery_source import (
    ProtocolFileDiscoverySource,
)
from omnibase_core.utils.safe_yaml_loader import (
    load_and_validate_yaml_model,
)


class TreeFileDiscoverySource(ProtocolFileDiscoverySource):
    """
    File discovery source that uses a .tree file as the canonical source of truth.
    """

    def discover_files(
        self,
        directory: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        ignore_file: Path | None = None,
        event_bus=None,
    ) -> set[Path]:
        """
        Discover files listed in the .tree file in the given directory.
        Ignores include/exclude patterns; only files in .tree are returned.
        """
        tree_file = directory / ".tree"
        return self.get_canonical_files_from_tree(tree_file)

    def validate_tree_sync(
        self,
        directory: Path,
        tree_file: Path,
    ) -> ModelTreeSyncResult:
        """
        Validate that the .tree file and filesystem are in sync.
        """
        canonical_files = self.get_canonical_files_from_tree(tree_file)
        files_on_disk = {p for p in directory.rglob("*") if p.is_file()}
        extra_files = files_on_disk - canonical_files
        missing_files = canonical_files - files_on_disk
        status = (
            TreeSyncStatusEnum.OK
            if not extra_files and not missing_files
            else TreeSyncStatusEnum.DRIFT
        )
        messages = []
        if extra_files:
            messages.append(
                ModelOnexMessage(
                    summary=f"Extra files on disk: {sorted(str(f) for f in extra_files)}",
                    level=LogLevel.WARNING,
                    file=None,
                    line=None,
                    details=None,
                    code=None,
                    context=None,
                    timestamp=None,
                    type=None,
                ),
            )
        if missing_files:
            messages.append(
                ModelOnexMessage(
                    summary=f"Missing files in .tree: {sorted(str(f) for f in missing_files)}",
                    level=LogLevel.WARNING,
                    file=None,
                    line=None,
                    details=None,
                    code=None,
                    context=None,
                    timestamp=None,
                    type=None,
                ),
            )
        return ModelTreeSyncResult(
            extra_files_on_disk=extra_files,
            missing_files_in_tree=missing_files,
            status=status,
            messages=messages,
        )

    def get_canonical_files_from_tree(self, tree_file: Path) -> set[Path]:
        """
        Parse the .tree file and return the set of canonical files.
        """
        if not tree_file.exists():
            return set()
        with open(tree_file) as f:
            # Load and validate YAML using Pydantic model

            yaml_model = load_and_validate_yaml_model(tree_file, ModelGenericYaml)

            data = yaml_model.model_dump()
        return set(self._extract_files_from_tree_data(tree_file.parent, data))

    def _extract_files_from_tree_data(self, base_dir: Path, data: object) -> list[Path]:
        """
        Recursively extract file paths from .tree data structure.
        """
        files = []
        if isinstance(data, dict):
            if data.get("type") == "file" and "name" in data:
                files.append(base_dir / data["name"])
            elif data.get("type") == "directory" and "children" in data:
                dir_path = base_dir / data.get("name", "")
                for child in data["children"]:
                    files.extend(self._extract_files_from_tree_data(dir_path, child))
        elif isinstance(data, list):
            for item in data:
                files.extend(self._extract_files_from_tree_data(base_dir, item))
        return files
