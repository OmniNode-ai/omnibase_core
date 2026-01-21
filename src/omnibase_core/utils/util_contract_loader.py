from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
ContractLoader for ONEX Tool Generation Pattern Standardization.

This module provides unified contract loading and resolution functionality
that supports the new contract architecture with subcontract references,
$ref resolution, and validation. This is part of PATTERN-005 NodeBase
implementation to eliminate duplicate node.py code.

Security:
    Contract files are treated as configuration that may come from untrusted
    sources (e.g., third-party node packages, user-provided contract overrides).
    This module implements multiple layers of security validation:

    **YAML Parsing Security** (_validate_yaml_content_security):
        - Size limits: Max 10MB to prevent denial-of-service attacks
        - Suspicious pattern detection: Warns on !!python, __import__, eval(), exec()
        - Nesting depth limits: Max 50 levels to prevent YAML bombs
        - Uses yaml.safe_load() via util_safe_yaml_loader (no arbitrary code execution)

    **File Path Security**:
        - File paths are resolved using Path.resolve() to normalize paths
        - Contract paths should be validated by the caller to prevent path traversal
        - Only files with valid YAML extensions should be loaded

    **Content Validation**:
        - All loaded content is validated against Pydantic models (ModelContractContent)
        - Required fields (node_name, tool_specification.main_tool_class) are enforced
        - Enum values are strictly validated (no backwards compatibility fallbacks)

    Trust Model:
        - Contract file content: UNTRUSTED (validated via safe_load + Pydantic)
        - Contract file paths: SEMI-TRUSTED (should be validated by caller)
        - Subcontract references ($ref): UNTRUSTED (not yet implemented, will need validation)

    Warning:
        The tool_specification.main_tool_class field in contracts specifies a
        fully-qualified Python module path that will be dynamically imported by
        NodeBase._resolve_main_tool(). This path is NOT validated by this loader
        against an allowlist. NodeBase is responsible for ensuring only trusted
        code is executed. See infrastructure/node_base.py for details.

    See Also:
        - util_safe_yaml_loader.py: Uses yaml.safe_load() for parsing
        - model_reference.py: ALLOWED_MODULE_PREFIXES for import validation
        - infrastructure/node_base.py: Dynamic import of main_tool_class
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError as PydanticValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_contract_cache import ModelContractCache
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_contract_dependency import ModelContractDependency
from omnibase_core.models.core.model_contract_loader import ModelContractLoader
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


class UtilContractLoader:
    """
    Unified contract loading and resolution for NodeBase implementation.

    Handles:
    - Main contract loading with validation
    - Subcontract reference resolution ($ref handling)
    - Contract structure validation
    - Performance optimization through caching
    - Error handling with detailed context

    Thread Safety:
        This class is NOT thread-safe. It maintains mutable internal state
        including contract_cache, loaded_contracts, and resolution_stack that
        are modified during load_contract() and clear_cache() operations.
        Concurrent access from multiple threads could corrupt the cache or
        cause inconsistent results. Each thread should use its own instance,
        or disable caching (cache_enabled=False) and wrap access with external
        locks. See docs/guides/THREADING.md for more details.

    Example:
        >>> from omnibase_core.utils import UtilContractLoader
        >>> from pathlib import Path
        >>> loader = UtilContractLoader(base_path=Path("contracts/"))
        >>> contract = loader.load_contract(Path("contracts/my_node.yaml"))
        >>> print(contract.node_name)

    .. note::
        Previously named ``ProtocolContractLoader``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Protocol``
        prefix is reserved for typing.Protocol interfaces; ``Util``
        prefix indicates a utility class.
    """

    def __init__(self, base_path: Path, cache_enabled: bool = True):
        """
        Initialize the contract loader.

        Args:
            base_path: Base path for contract resolution
            cache_enabled: Whether to enable contract caching for performance
        """
        self.state = ModelContractLoader(
            cache_enabled=cache_enabled,
            base_path=base_path,
        )

    def load_contract(self, contract_path: Path) -> ModelContractContent:
        """
        Load a contract with full subcontract resolution.

        Args:
            contract_path: Path to the main contract file

        Returns:
            ModelContractContent: Fully resolved contract with all subcontracts

        Raises:
            ModelOnexError: If contract loading or resolution fails
        """
        try:
            contract_path = contract_path.resolve()

            if not contract_path.exists():
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Contract file not found: {contract_path}",
                    context={"contract_path": str(contract_path)},
                )

            # Check cache first
            contract_path_str = str(contract_path)
            if contract_path_str in self.state.loaded_contracts:
                return self.state.loaded_contracts[contract_path_str]

            # Load main contract
            raw_contract = self._load_contract_file(contract_path)

            # Parse contract content
            contract_content = self._parse_contract_content(raw_contract, contract_path)

            # Validate basic contract structure
            self._validate_contract_structure(contract_content, contract_path)

            # Resolve all references
            resolved_contract = self._resolve_all_references(
                contract_content,
                contract_path,
            )

            # Cache the result
            self.state.loaded_contracts[contract_path_str] = resolved_contract

            return resolved_contract

        except ModelOnexError:
            raise
        except OSError as e:
            # File system errors (FileNotFoundError, PermissionError, etc.)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"File system error loading contract: {e!s}",
                context={"contract_path": str(contract_path)},
            ) from e
        except (TypeError, ValueError, KeyError) as e:
            # Data parsing/conversion errors
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid contract data: {e!s}",
                context={"contract_path": str(contract_path)},
            ) from e

    def _load_contract_file(self, file_path: Path) -> dict[str, object]:
        """
        Load a single contract file with caching support.

        Args:
            file_path: Path to the contract file

        Returns:
            Dict[str, object]: Raw contract content from YAML
        """
        file_path_str = str(file_path)

        # Check cache if enabled
        if self.state.cache_enabled and file_path_str in self.state.contract_cache:
            cached = self.state.contract_cache[file_path_str]
            current_mtime = file_path.stat().st_mtime

            if current_mtime <= cached.file_modified_at.timestamp():
                return self._convert_contract_content_to_dict(cached.content)

        # Load from file with security validation
        try:
            # Validate YAML content for security
            with open(file_path, encoding="utf-8") as f:
                raw_content = f.read()
            self._validate_yaml_content_security(raw_content, file_path)

            # Load and validate YAML using Pydantic model
            yaml_model = load_and_validate_yaml_model(file_path, ModelGenericYaml)
            content = yaml_model.model_dump()

            # Parse and cache if enabled
            if self.state.cache_enabled:
                parsed_content = self._parse_contract_content(content, file_path)
                stat = file_path.stat()
                content_str = str(content)
                self.state.contract_cache[file_path_str] = ModelContractCache(
                    cache_key=f"{file_path_str}_{stat.st_mtime}",
                    file_path=file_path,
                    content=parsed_content,
                    cached_at=datetime.now(),
                    file_modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    file_size=stat.st_size,
                    content_hash=hashlib.sha256(content_str.encode()).hexdigest(),
                    is_valid=True,
                    validation_errors=[],
                    access_count=0,
                    last_accessed_at=None,
                    ttl_seconds=None,
                    max_age_seconds=None,
                )

            return content

        except yaml.YAMLError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid YAML in contract file: {e!s}",
                context={"file_path": file_path_str},
            ) from e
        except OSError as e:
            # File system errors (FileNotFoundError, PermissionError, etc.)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Cannot access contract file: {e!s}",
                context={"file_path": file_path_str},
            ) from e
        except UnicodeDecodeError as e:
            # Encoding issues when reading the file
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid encoding in contract file: {e!s}",
                context={"file_path": file_path_str},
            ) from e

    def _parse_contract_content(
        self,
        raw_content: dict[str, object],
        contract_path: Path,
    ) -> ModelContractContent:
        """
        Parse raw YAML content into strongly-typed contract content.

        Args:
            raw_content: Raw YAML content
            contract_path: Path to contract for error context

        Returns:
            ModelContractContent: Parsed contract content
        """
        try:
            # Fail fast on deprecated 'version' field (OMN-1431)
            # Contracts must use 'contract_version' per ONEX specification
            if "version" in raw_content:
                raise ModelOnexError(
                    message="Contract uses deprecated 'version' field. Rename to 'contract_version' per ONEX specification (OMN-1431).",
                    error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                    context={
                        "contract_path": str(contract_path),
                        "field": "version",
                        "expected": "contract_version",
                        "ticket": "OMN-1431",
                    },
                )

            # Parse contract version
            version_data = raw_content.get("contract_version", {})
            if not isinstance(version_data, dict):
                version_data = {}
            contract_version = ModelSemVer(
                major=int(version_data.get("major", 1)),
                minor=int(version_data.get("minor", 0)),
                patch=int(version_data.get("patch", 0)),
            )

            # Parse tool specification
            tool_spec_data = raw_content.get("tool_specification", {})
            if not isinstance(tool_spec_data, dict):
                tool_spec_data = {}
            tool_specification = ModelToolSpecification(
                main_tool_class=str(
                    tool_spec_data.get("main_tool_class", "DefaultToolNode"),
                ),
            )

            # Parse input/output state (simplified for now)
            input_state = ModelYamlSchemaObject(
                object_type="object",
                description="Input state schema",
            )

            output_state = ModelYamlSchemaObject(
                object_type="object",
                description="Output state schema",
            )

            # Parse definitions section (optional)
            definitions = ModelContractDefinitions()

            # Parse dependencies section (optional, for Phase 0 pattern)
            # Construct ModelContractDependency objects from raw dicts for type safety
            dependencies: list[ModelContractDependency] | None = None
            if "dependencies" in raw_content:
                deps_data = raw_content["dependencies"]
                if isinstance(deps_data, list):
                    dependencies = []
                    for index, dep_item in enumerate(deps_data):
                        if isinstance(dep_item, dict):
                            # Construct typed ModelContractDependency from dict
                            dep = ModelContractDependency.model_validate(dep_item)
                            dependencies.append(dep)
                        else:
                            emit_log_event(
                                LogLevel.WARNING,
                                f"Skipping non-dict dependency item at index {index}: {type(dep_item).__name__}",
                                context={
                                    "contract_path": str(contract_path),
                                    "item_type": type(dep_item).__name__,
                                    "index": index,
                                    "item_repr": repr(dep_item)[:100],
                                },
                            )

            # Parse node type (default to COMPUTE_GENERIC if not specified)
            # No legacy fallback - invalid enum values must fail fast
            node_type_str = raw_content.get("node_type", "COMPUTE_GENERIC")
            if isinstance(node_type_str, str):
                node_type_upper = node_type_str.upper()
                try:
                    node_type = EnumNodeType(node_type_upper)
                except ValueError as e:
                    valid_values = [v.value for v in EnumNodeType]
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Invalid node_type '{node_type_str}'. Valid values are: {valid_values}",
                        context={
                            "contract_path": str(contract_path),
                            "invalid_value": node_type_str,
                            "valid_values": valid_values,
                        },
                    ) from e
            else:
                node_type = EnumNodeType.COMPUTE_GENERIC

            # Create contract content
            return ModelContractContent(
                contract_version=contract_version,
                node_name=str(raw_content.get("node_name", "")),
                node_type=node_type,
                tool_specification=tool_specification,
                input_state=input_state,
                output_state=output_state,
                definitions=definitions,
                dependencies=dependencies,
                contract_name=None,
                description=None,
                name=None,
                version=None,
                node_version=None,
                input_model=None,
                output_model=None,
                main_tool_class=None,
                actions=None,
                primary_actions=None,
                validation_rules=None,
                infrastructure=None,
                infrastructure_services=None,
                service_configuration=None,
                service_resolution=None,
                performance=None,
                aggregation=None,
                state_management=None,
                reduction_operations=None,
                streaming=None,
                conflict_resolution=None,
                memory_management=None,
                state_transitions=None,
                routing=None,
                workflow_registry=None,
                io_operations=None,
                interface=None,
                metadata=None,
                capabilities=None,
                configuration=None,
                algorithm=None,
                caching=None,
                error_handling=None,
                observability=None,
                event_type=None,
                contract_driven=None,
                protocol_based=None,
                strong_typing=None,
                zero_any_types=None,
                subcontracts=None,
                original_dependencies=None,
            )

        except PydanticValidationError as e:
            # Pydantic model validation errors
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Contract schema validation failed: {e!s}",
                context={"contract_path": str(contract_path)},
            ) from e
        except (TypeError, ValueError) as e:
            # Type conversion errors (e.g., int() on non-numeric values)
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid value in contract: {e!s}",
                context={"contract_path": str(contract_path)},
            ) from e

    def _convert_contract_content_to_dict(
        self,
        content: ModelContractContent,
    ) -> dict[str, object]:
        """Convert ModelContractContent back to dict[str, Any]for current standards."""
        return {
            "contract_version": {
                "major": content.contract_version.major,
                "minor": content.contract_version.minor,
                "patch": content.contract_version.patch,
            },
            "node_name": content.node_name,
            "node_type": str(content.node_type),
            "tool_specification": {
                "main_tool_class": content.tool_specification.main_tool_class,
            },
        }

    def _validate_contract_structure(
        self,
        contract: ModelContractContent,
        contract_path: Path,
    ) -> None:
        """
        Validate basic contract structure for NodeBase compatibility.

        Args:
            contract: Contract content to validate
            contract_path: Path to contract for error context

        Raises:
            ModelOnexError: If contract structure is invalid
        """
        if not contract.node_name:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Contract missing required node_name field",
                context={"contract_path": str(contract_path)},
            )

        if not contract.tool_specification.main_tool_class:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Contract missing required tool_specification.main_tool_class field",
                context={"contract_path": str(contract_path)},
            )

        # Phase 0 NodeBase pattern - registry_class completely removed
        # Dependencies will be resolved directly from contract dependencies section
        emit_log_event(
            LogLevel.INFO,
            "Using Phase 0 NodeBase pattern - dependencies will be resolved from contract",
            {"contract_path": str(contract_path)},
        )

    def _resolve_all_references(
        self,
        contract: ModelContractContent,
        base_path: Path,
    ) -> ModelContractContent:
        """
        Recursively resolve all $ref references in the contract.

        Args:
            contract: Contract content with potential references
            base_path: Base path for resolving relative references

        Returns:
            ModelContractContent: Contract with all references resolved
        """
        # Reset resolution stack for new resolution
        self.state.resolution_stack = []

        # For now, return as-is. Full $ref resolution will be implemented later
        return contract

    def clear_cache(self) -> None:
        """Clear the contract cache."""
        self.state.contract_cache.clear()
        self.state.loaded_contracts.clear()

    def validate_contract_compatibility(self, contract_path: Path) -> bool:
        """
        Check if a contract is compatible with NodeBase.

        Args:
            contract_path: Path to contract to validate

        Returns:
            bool: True if contract is NodeBase compatible
        """
        try:
            self.load_contract(contract_path)
            return True
        except ModelOnexError:
            # fallback-ok: Validation method should return bool status, not raise ModelOnexError
            return False
        except (OSError, RuntimeError):
            # fallback-ok: Validation method should return bool status for file system or runtime errors
            return False

    def _validate_yaml_content_security(self, content: str, file_path: Path) -> None:
        """
        Validate YAML content for security concerns before parsing.

        Args:
            content: Raw YAML content string
            file_path: Path to the file being loaded (for error reporting)

        Raises:
            ModelOnexError: If security validation fails
        """
        # Check for excessively large content (DoS protection)
        max_size = 10 * 1024 * 1024  # 10MB limit
        if len(content) > max_size:
            msg = f"YAML file too large ({len(content)} bytes, max {max_size}): {file_path}"
            raise ModelOnexError(
                msg,
                EnumCoreErrorCode.VALIDATION_FAILED,
            )

        # Check for suspicious YAML constructs
        suspicious_patterns = [
            "!!python",  # Python object instantiation
            "!!map",  # Explicit map constructor
            "!!omap",  # Ordered map constructor
            "!!pairs",  # Pairs constructor
            "!!set",  # Set constructor
            "!!binary",  # Binary data
            "__import__",  # Python import function
            "eval(",  # Python eval function
            "exec(",  # Python exec function
        ]

        for pattern in suspicious_patterns:
            if pattern in content:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Suspicious YAML pattern detected in {file_path}: {pattern}",
                    {
                        "source": "contract_loader",
                        "pattern": pattern,
                        "file_path": str(file_path),
                    },
                )

        # Check for YAML bombs (deeply nested structures)
        nesting_depth = 0
        max_nesting = 50

        for char in content:
            if char in ["{", "["]:
                nesting_depth += 1
                if nesting_depth > max_nesting:
                    msg = (
                        f"YAML nesting too deep (>{max_nesting} levels) in {file_path}"
                    )
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.VALIDATION_FAILED,
                    )
            elif char in ["}", "]"]:
                nesting_depth = max(0, nesting_depth - 1)
