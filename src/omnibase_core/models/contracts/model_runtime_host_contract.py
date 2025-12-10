"""
Runtime Host Contract Model.

Main contract model for RuntimeHost configuration combining:
- Handler configurations for I/O operations
- Event bus configuration for pub/sub messaging
- Node references for node graph management

MVP implementation - simplified for minimal viable product.
Advanced features (retry policies, rate limits) deferred to Beta.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_node_ref import ModelNodeRef
from omnibase_core.models.contracts.model_runtime_event_bus_config import (
    ModelRuntimeEventBusConfig,
)
from omnibase_core.models.contracts.model_runtime_handler_config import (
    ModelRuntimeHandlerConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelRuntimeHostContract(BaseModel):
    """
    Runtime Host Contract for ONEX RuntimeHostProcess.

    Defines the configuration for a runtime host including:
    - Handler configurations for I/O operations
    - Event bus configuration for pub/sub messaging
    - Node references for node graph management

    MVP implementation - simplified for minimal viable product.
    Advanced features (retry policies, rate limits) deferred to Beta.

    Attributes:
        handlers: List of handler configurations for I/O operations
        event_bus: Event bus configuration for pub/sub messaging
        nodes: List of node references for node graph management

    Example:
        >>> from omnibase_core.enums.enum_handler_type import EnumHandlerType
        >>> contract = ModelRuntimeHostContract(
        ...     handlers=[ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.FILESYSTEM)],
        ...     event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        ...     nodes=[ModelNodeRef(slug="node-compute-transformer")],
        ... )
        >>> contract.event_bus.kind
        'kafka'
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )

    handlers: list[ModelRuntimeHandlerConfig] = Field(
        default_factory=list,
        description="Handler configurations for I/O operations",
    )

    event_bus: ModelRuntimeEventBusConfig = Field(
        ...,
        description="Event bus configuration for pub/sub messaging",
    )

    nodes: list[ModelNodeRef] = Field(
        default_factory=list,
        description="Node references for node graph management",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> "ModelRuntimeHostContract":
        """
        Load RuntimeHostContract from a YAML file.

        Parses and validates a YAML contract file, returning a fully
        validated ModelRuntimeHostContract instance.

        Args:
            path: Path to the YAML contract file

        Returns:
            ModelRuntimeHostContract: Validated contract instance

        Raises:
            ModelOnexError: If file not found, invalid YAML, or validation fails

        Example:
            >>> from pathlib import Path
            >>> contract = ModelRuntimeHostContract.from_yaml(
            ...     Path("config/runtime_host.yaml")
            ... )  # doctest: +SKIP
        """
        if not path.exists():
            raise ModelOnexError(
                message=f"Contract file not found: {path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                file_path=str(path),
            )

        try:
            with path.open("r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ModelOnexError(
                message=f"Invalid YAML in contract file: {path}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                file_path=str(path),
                yaml_error=str(e),
            ) from e

        if not isinstance(yaml_data, dict):
            raise ModelOnexError(
                message=f"Contract file must contain a YAML mapping, got {type(yaml_data).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                file_path=str(path),
            )

        try:
            return cls.model_validate(yaml_data)
        except Exception as e:
            raise ModelOnexError(
                message=f"Contract validation failed: {e}",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                file_path=str(path),
            ) from e
