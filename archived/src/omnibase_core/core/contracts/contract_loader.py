"""
ContractLoader for ONEX Tool Generation Pattern Standardization.

This module provides unified contract loading and resolution functionality
that supports the new contract architecture with subcontract references,
$ref resolution, and validation. This is part of PATTERN-005 ModelNodeBase
implementation to eliminate duplicate node.py code.

Author: ONEX Framework Team
"""

import hashlib
from datetime import datetime
from pathlib import Path

import yaml

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.node import EnumNodeType
from omnibase_core.models.core.model_contract_cache import ModelContractCache
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_contract_loader import ModelContractLoader
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject
from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model


class ContractLoader:
    """
    Unified contract loading and resolution for ModelNodeBase implementation.

    Handles:
    - Main contract loading with validation
    - Subcontract reference resolution ($ref handling)
    - Contract structure validation
    - Performance optimization through caching
    - Error handling with detailed context
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
            OnexError: If contract loading or resolution fails
        """
        try:
            contract_path = contract_path.resolve()

            if not contract_path.exists():
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
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

        except OnexError:
            raise
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to load contract: {e!s}",
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

            if current_mtime <= cached.last_modified:
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

            if content is None:
                content = {}

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
                    file_modified_at=datetime.fromtimestamp(stat.st_mtime),
                    file_size=stat.st_size,
                    content_hash=hashlib.sha256(content_str.encode()).hexdigest(),
                )

            return content

        except yaml.YAMLError as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid YAML in contract file: {e!s}",
                context={"file_path": file_path_str},
            ) from e
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to read contract file: {e!s}",
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
            # Parse contract version
            version_data = raw_content.get("contract_version", {})
            contract_version = ModelSemVer(
                major=int(version_data.get("major", 1)),
                minor=int(version_data.get("minor", 0)),
                patch=int(version_data.get("patch", 0)),
            )

            # Parse tool specification
            tool_spec_data = raw_content.get("tool_specification", {})
            tool_specification = ModelToolSpecification(
                main_tool_class=str(
                    tool_spec_data.get("main_tool_class", "DefaultToolNode"),
                ),
                business_logic_pattern=str(
                    tool_spec_data.get("business_logic_pattern", "stateful"),
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
            dependencies = None
            if "dependencies" in raw_content:
                from omnibase_core.models.core.model_contract_dependency import (
                    ModelContractDependency,
                )

                deps_data = raw_content["dependencies"]
                if isinstance(deps_data, list):
                    dependencies = []
                    for dep_item in deps_data:
                        if isinstance(dep_item, dict):
                            dependencies.append(ModelContractDependency(**dep_item))

            # Parse node type (default to COMPUTE if not specified)
            node_type_str = raw_content.get("node_type", "COMPUTE")
            if isinstance(node_type_str, str):
                node_type = EnumNodeType(node_type_str.upper())
            else:
                node_type = EnumNodeType.COMPUTE

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
            )

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to parse contract content: {e!s}",
                context={"contract_path": str(contract_path)},
            ) from e

    def _convert_contract_content_to_dict(
        self,
        content: ModelContractContent,
    ) -> dict[str, object]:
        """Convert ModelContractContent back to dict for current standards."""
        return {
            "contract_version": {
                "major": content.contract_version.major,
                "minor": content.contract_version.minor,
                "patch": content.contract_version.patch,
            },
            "node_name": content.node_name,
            "tool_specification": {
                "main_tool_class": content.tool_specification.main_tool_class,
                "business_logic_pattern": content.tool_specification.business_logic_pattern.value,
            },
        }

    def _validate_contract_structure(
        self,
        contract: ModelContractContent,
        contract_path: Path,
    ) -> None:
        """
        Validate basic contract structure for ModelNodeBase compatibility.

        Args:
            contract: Contract content to validate
            contract_path: Path to contract for error context

        Raises:
            OnexError: If contract structure is invalid
        """
        if not contract.node_name:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Contract missing required node_name field",
                context={"contract_path": str(contract_path)},
            )

        if not contract.tool_specification.main_tool_class:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Contract missing required tool_specification.main_tool_class field",
                context={"contract_path": str(contract_path)},
            )

        # Phase 0 ModelNodeBase pattern - registry_class completely removed
        # Dependencies will be resolved directly from contract dependencies section
        emit_log_event(
            LogLevel.INFO,
            "Using Phase 0 ModelNodeBase pattern - dependencies will be resolved from contract",
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
        Check if a contract is compatible with ModelNodeBase.

        Args:
            contract_path: Path to contract to validate

        Returns:
            bool: True if contract is ModelNodeBase compatible
        """
        try:
            self.load_contract(contract_path)
            return True
        except OnexError:
            return False
        except Exception:
            return False

    def _validate_yaml_content_security(self, content: str, file_path: Path) -> None:
        """
        Validate YAML content for security concerns before parsing.

        Args:
            content: Raw YAML content string
            file_path: Path to the file being loaded (for error reporting)

        Raises:
            OnexError: If security validation fails
        """
        # Check for excessively large content (DoS protection)
        max_size = 10 * 1024 * 1024  # 10MB limit
        if len(content) > max_size:
            msg = f"YAML file too large ({len(content)} bytes, max {max_size}): {file_path}"
            raise OnexError(
                msg,
                CoreErrorCode.VALIDATION_FAILED,
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
                    raise OnexError(
                        msg,
                        CoreErrorCode.VALIDATION_FAILED,
                    )
            elif char in ["}", "]"]:
                nesting_depth = max(0, nesting_depth - 1)
