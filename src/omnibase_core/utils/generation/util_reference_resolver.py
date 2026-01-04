"""
Reference Resolver Utility for ONEX Contract Generation.

Handles resolution of JSON Schema $ref references to Python type names.
Provides consistent reference resolution across all ONEX tools.
"""

import re
from pathlib import Path

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.utils.generation.model_ref_info import ModelRefInfo
from omnibase_core.protocols.protocol_generation_config import ProtocolGenerationConfig
from omnibase_core.protocols.protocol_import_tracker import ProtocolImportTracker


class UtilityReferenceResolver:
    """
    Utility for resolving JSON Schema $ref references.

    Handles:
    - Internal references (#/definitions/...)
    - External references (file.yaml#/...)
    - Subcontract references (contracts/...)
    - Tool-specific prefix cleanup
    - Import tracking for subcontracts
    """

    # Known type mappings for clean resolution
    TYPE_MAPPINGS = {
        "ProcessingConfig": "ModelProcessingConfig",
        "ValidationConfig": "ModelValidationConfig",
        "ProcessingResult": "ModelProcessingResult",
        "ValidationResult": "ModelValidationResult",
        "NodeStatus": "ModelNodeStatus",
        "SemVerModel": "ModelSemVerModel",
        "OnexFieldModel": "ModelOnexFieldModel",
        "ActionSpec": "ModelActionSpec",
        "LogContext": "ModelLogContext",
        "ErrorInfo": "ModelErrorInfo",
        "SuccessInfo": "ModelSuccessInfo",
    }

    # Pattern for tool-specific prefixes to clean up
    TOOL_PREFIX_PATTERN = re.compile(
        r"^Tool[A-Z][a-zA-Z]*"
        r"(?:Generator|Parser|Manager|Processor|Validator|Analyzer|"
        r"Injector|Resolver|Builder|Runner|Tracker|Engine)?"
        r"(ProcessingConfig|ValidationConfig|ProcessingResult|"
        r"ValidationResult|NodeStatus|ActionSpec|LogContext)$",
    )

    def __init__(
        self,
        config: ProtocolGenerationConfig | None = None,
        import_tracker: ProtocolImportTracker | None = None,
    ):
        """
        Initialize the reference resolver.

        Args:
            config: Optional generation config for import mapping
            import_tracker: Optional import tracker for subcontracts
        """
        self.config = config
        self.import_tracker = import_tracker

    def set_config(self, config: ProtocolGenerationConfig | None) -> None:
        """Set the generation config after initialization."""
        self.config = config

    def set_import_tracker(self, import_tracker: ProtocolImportTracker | None) -> None:
        """Set the import tracker after initialization."""
        self.import_tracker = import_tracker

    def resolve_ref(self, ref: str) -> str:
        """
        Main entry point to resolve a $ref to a type name.

        Args:
            ref: Reference string (e.g., "#/definitions/User", "contracts/models.yaml#/Config")

        Returns:
            Resolved type name (e.g., "ModelUser", "ModelConfig")
        """
        ref_info = self.parse_reference(ref)

        # Track subcontract imports if configured
        if self._should_track_imports() and ref_info.is_subcontract:
            resolved_name = self.resolve_type_name(ref_info)
            self._track_subcontract_import(ref_info, resolved_name)
            return resolved_name

        return self.resolve_type_name(ref_info)

    def parse_reference(self, ref: str) -> ModelRefInfo:
        """
        Parse a reference string into structured data.

        Args:
            ref: Reference string

        Returns:
            Structured reference information
        """
        if ref.startswith("#/definitions/"):
            # Internal reference
            type_name = ref.split("/")[-1]
            return ModelRefInfo(file_path="", type_name=type_name, is_internal=True)

        if "#/" in ref:
            # External reference
            file_part, type_part = ref.split("#/", 1)
            # Remove any leading slashes from type_part
            type_name = type_part.split("/")[-1] if "/" in type_part else type_part

            return ModelRefInfo(
                file_path=file_part,
                type_name=type_name,
                is_subcontract=file_part.startswith("contracts/"),
            )

        # Fallback for malformed refs
        emit_log_event(
            LogLevel.WARNING,
            f"Malformed reference: {ref}",
            {"ref": ref},
        )
        return ModelRefInfo(file_path="", type_name=ref)

    def resolve_type_name(self, ref_info: ModelRefInfo) -> str:
        """
        Resolve reference info to proper model name.

        Args:
            ref_info: Parsed reference information

        Returns:
            Resolved Python type name
        """
        # Handle empty type names
        if not ref_info.type_name or ref_info.type_name.strip() == "":
            return "ModelObjectData"

        # Internal references
        if ref_info.is_internal:
            return self._ensure_model_prefix(ref_info.type_name)

        # Subcontract references
        if ref_info.is_subcontract:
            clean_name = self._clean_tool_prefix(ref_info.type_name)
            return self._ensure_model_prefix(clean_name)

        # External schema references based on file path
        if ref_info.file_path:
            resolved = self._resolve_by_file_path(ref_info)
            if resolved:
                return resolved

        # Default resolution
        return self._ensure_model_prefix(ref_info.type_name)

    def is_external_reference(self, ref: str) -> bool:
        """
        Check if a reference is external (not internal to current schema).

        Args:
            ref: Reference string

        Returns:
            True if external reference
        """
        if not ref:
            return False
        return not ref.startswith("#/definitions/")

    def get_package_name_for_subcontract(self, subcontract_path: str) -> str:
        """
        Get the package name for a subcontract.

        Args:
            subcontract_path: Path to subcontract file

        Returns:
            Package name for imports
        """
        # Check config mapping first
        if self.config and self.config.subcontract_import_map:
            mapping = self.config.subcontract_import_map.get(subcontract_path, {})
            if "package_name" in mapping:
                package_name = mapping["package_name"]
                # Type narrowing: ensure str return
                return str(package_name)

        # Default: derive from file path
        # contracts/contract_models.yaml -> models
        if subcontract_path.startswith("contracts/contract_"):
            return subcontract_path.replace("contracts/contract_", "").replace(
                ".yaml",
                "",
            )

        # Fallback to stem
        return Path(subcontract_path).stem

    def get_import_path_for_subcontract(self, subcontract_path: str) -> str:
        """
        Get the Python import path for a subcontract.

        Args:
            subcontract_path: Path to subcontract file

        Returns:
            Python import path
        """
        # Check config mapping first
        if self.config and self.config.subcontract_import_map:
            mapping = self.config.subcontract_import_map.get(subcontract_path, {})
            if "import_path" in mapping:
                import_path = mapping["import_path"]
                # Type narrowing: ensure str return
                return str(import_path)

        # Default convention
        package_name = self.get_package_name_for_subcontract(subcontract_path)
        return f"generated.{package_name}"

    # Private helper methods

    def _should_track_imports(self) -> bool:
        """Check if we should track subcontract imports."""
        return (
            self.config is not None
            and self.config.use_imports_for_subcontracts
            and self.import_tracker is not None
        )

    def _track_subcontract_import(
        self,
        ref_info: ModelRefInfo,
        resolved_name: str,
    ) -> None:
        """Track a subcontract import."""
        if not self.import_tracker:
            return

        package_name = self.get_package_name_for_subcontract(ref_info.file_path)
        import_path = self.get_import_path_for_subcontract(ref_info.file_path)

        self.import_tracker.add_subcontract_model(
            subcontract_path=ref_info.file_path,
            model_name=resolved_name,
            package_name=package_name,
            import_path=import_path,
        )

    def _clean_tool_prefix(self, type_name: str) -> str:
        """Remove tool-specific prefixes from type names."""
        # Check for known pattern
        match = self.TOOL_PREFIX_PATTERN.match(type_name)
        if match:
            config_type = match.group(1)
            return self.TYPE_MAPPINGS.get(config_type, config_type)

        # Check simple prefixes
        for prefix in ["Tool", "Node"]:
            if type_name.startswith(prefix):
                clean_name = type_name[len(prefix) :]
                return self.TYPE_MAPPINGS.get(clean_name, clean_name)

        return type_name

    def _ensure_model_prefix(self, name: str) -> str:
        """Ensure type name has Model prefix."""
        if not name:
            return "ModelObjectData"

        # Check if already has Model prefix
        if name.startswith("Model"):
            return name

        # Check if it's an enum
        if name.startswith("Enum"):
            return name

        # Add Model prefix
        return f"Model{name}"

    def _resolve_by_file_path(self, ref_info: ModelRefInfo) -> str | None:
        """Try to resolve type by examining file path."""
        path_lower = ref_info.file_path.lower()

        # Known file patterns
        if "onex_field_model" in path_lower:
            return "ModelOnexFieldModel"
        if "semver" in path_lower:
            return "ModelSemVer"
        if "action_spec" in path_lower:
            return "ModelActionSpec"
        if "log_context" in path_lower:
            return "ModelLogContext"

        return None
