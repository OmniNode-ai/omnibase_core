from collections.abc import Mapping

"""
Contract Metadata Mixin for ONEX Tool Nodes.

Provides automatic loading and validation of contract metadata for tool nodes.
Eliminates boilerplate code for reading node.onex.yaml and tool contracts.
"""

from pathlib import Path

from omnibase_core.constants import constants_contract_fields as cf
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_node_metadata import ModelNodeMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Type alias for contract data - the output of ModelGenericYaml.model_dump()
# which contains arbitrary YAML fields loaded from contract files
ContractDataMapping = Mapping[str, object]


class MixinContractMetadata:
    """
    Mixin that provides contract metadata loading and validation.

    Automatically loads:
    - node.onex.yaml metadata
    - Tool contract YAML
    - Extracts all metadata fields

    Usage:
        class MyTool(MixinContractMetadata, ProtocolReducer):
            def __init__(self, **kwargs) -> None:
                super().__init__(**kwargs)
                # Access metadata via self properties
                print(f"Tool: {self.node_name} v{self.node_version}")
    """

    def __init__(self, **kwargs: object) -> None:
        """Initialize the contract metadata mixin."""
        super().__init__(**kwargs)

        # Initialize properties
        self._node_metadata: ModelNodeMetadata | None = None
        self._contract_data: dict[str, object] | None = None
        self._node_name: str | None = None
        self._node_version: str | None = None
        self._description: str | None = None
        self._tool_type: str | None = None

        # Load metadata
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from node.onex.yaml and contract files."""
        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Loading contract metadata",
            {"mixin_class": self.__class__.__name__},
        )

        # Find node.onex.yaml
        node_metadata_path = self._find_node_metadata()
        if node_metadata_path:
            self._load_node_metadata(node_metadata_path)

        # Find and load contract
        contract_path = self._find_contract()
        if contract_path:
            self._load_contract(contract_path)

    def _find_node_metadata(self) -> Path | None:
        """Find node.onex.yaml file."""
        # Start from current module location
        current_file = Path(__file__)

        # Check parent directories up to tools directory
        for parent in current_file.parents:
            metadata_path = parent / "node.onex.yaml"
            if metadata_path.exists():
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Found node.onex.yaml at: {metadata_path}",
                    {"path": str(metadata_path)},
                )
                return metadata_path

            # Stop at tools directory
            if parent.name == "tools":
                break

        emit_log_event(
            LogLevel.WARNING,
            "Could not find node.onex.yaml",
            {"search_from": str(current_file)},
        )
        return None

    def _find_contract(self) -> Path | None:
        """Find contract YAML file."""
        # Start from current module location
        current_file = Path(__file__)

        # Look for contracts directory
        for parent in current_file.parents:
            contracts_dir = parent / "contracts"
            if contracts_dir.exists():
                # Find first YAML file in contracts
                for yaml_file in contracts_dir.glob("*.yaml"):
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"Found contract at: {yaml_file}",
                        {"path": str(yaml_file)},
                    )
                    return yaml_file

            # Stop at tools directory
            if parent.name == "tools":
                break

        emit_log_event(
            LogLevel.WARNING,
            "Could not find contract YAML",
            {"search_from": str(current_file)},
        )
        return None

    def _load_node_metadata(self, path: Path) -> None:
        """Load node.onex.yaml metadata."""
        # Import here to avoid circular dependency
        from omnibase_core.utils.util_safe_yaml_loader import (
            load_and_validate_yaml_model,
        )

        try:
            # Load and validate YAML using Pydantic model
            yaml_model = load_and_validate_yaml_model(path, ModelGenericYaml)
            data = yaml_model.model_dump()

            # Create ModelNodeMetadata instance
            self._node_metadata = ModelNodeMetadata(**data)

            # Extract key fields
            if cf.NAME in data:
                self._node_name = data[cf.NAME]
            if cf.VERSION in data:
                self._node_version = data[cf.VERSION]

            emit_log_event(
                LogLevel.INFO,
                "✅ Loaded node metadata",
                {"node_name": self._node_name, "version": self._node_version},
            )

        except (AttributeError, ValueError) as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to load node metadata: {e}",
                {"path": str(path), "error": str(e)},
            )

    def _load_contract(self, path: Path) -> None:
        """Load tool contract YAML."""
        # Import here to avoid circular dependency
        from omnibase_core.utils.util_safe_yaml_loader import (
            load_and_validate_yaml_model,
        )

        try:
            # Load and validate YAML using Pydantic model
            yaml_model = load_and_validate_yaml_model(path, ModelGenericYaml)
            self._contract_data = yaml_model.model_dump()

            # Extract key fields with explicit string conversion
            if self._contract_data:
                if cf.NODE_NAME in self._contract_data:
                    value = self._contract_data[cf.NODE_NAME]
                    self._node_name = str(value) if value is not None else None
                if cf.DESCRIPTION in self._contract_data:
                    value = self._contract_data[cf.DESCRIPTION]
                    self._description = str(value) if value is not None else None
                if cf.TOOL_TYPE in self._contract_data:
                    value = self._contract_data[cf.TOOL_TYPE]
                    self._tool_type = str(value) if value is not None else None
                if cf.NODE_VERSION in self._contract_data:
                    value = self._contract_data[cf.NODE_VERSION]
                    self._node_version = str(value) if value is not None else None

            emit_log_event(
                LogLevel.INFO,
                "✅ Loaded contract data",
                {"node_name": self._node_name, "tool_type": self._tool_type},
            )

        except (OSError, RuntimeError, ValueError) as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to load contract: {e}",
                {"path": str(path), "error": str(e)},
            )

    @property
    def node_name(self) -> str:
        """Get node name from metadata."""
        return self._node_name or self.__class__.__name__.lower()

    @property
    def node_version(self) -> str:
        """Get node version from metadata."""
        # Use ModelSemVer for default version instead of string literal
        default_version = ModelSemVer(major=1, minor=0, patch=0)
        return self._node_version or str(default_version)

    @property
    def description(self) -> str:
        """Get description from contract."""
        return self._description or "No description available"

    @property
    def tool_type(self) -> str:
        """Get tool type from contract."""
        return self._tool_type or "generic"

    @property
    def contract_data(self) -> ContractDataMapping | None:
        """Get full contract data."""
        return self._contract_data

    @property
    def node_metadata(self) -> ModelNodeMetadata | None:
        """Get node metadata model."""
        return self._node_metadata

    @property
    def contract_path(self) -> Path | None:
        """Get path to contract file."""
        return self._find_contract()
