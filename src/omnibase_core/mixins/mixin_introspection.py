# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.607678'
# description: Stamped by ToolPython
# entrypoint: python://mixin_introspection
# hash: 8b168bc3f3b70fbd7d901ff91473c0db3f583b57e237aa8816e5717f62f604c8
# last_modified_at: '2025-05-29T14:13:58.690480+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: mixin_introspection.py
# namespace: python://omnibase.mixin.mixin_introspection
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 869ba89f-0a4f-4c22-af33-3c931a985c82
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Base Introspection Mixin for ONEX Nodes.

This module provides a reusable mixin class that implements standardized
introspection capabilities for ONEX nodes. All nodes should inherit from
this mixin to provide consistent --introspect functionality.
"""

import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from omnibase_core.protocols import ProtocolEventBus

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_node_capability import EnumNodeCapability
from omnibase_core.errors import ModelOnexError
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.core.model_cli_argument import ModelCLIArgument
from omnibase_core.models.core.model_cli_interface import ModelCLIInterface
from omnibase_core.models.core.model_contract import ModelContract
from omnibase_core.models.core.model_dependencies import ModelDependencies
from omnibase_core.models.core.model_error_code import ModelErrorCode
from omnibase_core.models.core.model_error_codes import ModelErrorCodes
from omnibase_core.models.core.model_event_channels import ModelEventChannels
from omnibase_core.models.core.model_event_type import create_event_type_from_registry
from omnibase_core.models.core.model_node_introspection import (
    create_node_introspection_response,
)
from omnibase_core.models.core.model_node_introspection_response import (
    ModelNodeIntrospectionResponse,
)
from omnibase_core.models.core.model_state_field import ModelStateField
from omnibase_core.models.core.model_state_models import ModelStates
from omnibase_core.models.infrastructure.model_state import ModelState
from omnibase_core.models.node_metadata.model_node_metadata_info import (
    ModelNodeMetadataInfo,
)
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.types.typed_dict_mixin_types import TypedDictPerformanceProfile


class MixinNodeIntrospection(ABC):
    """
    Base mixin providing standardized introspection capabilities for ONEX nodes.

    All ONEX nodes should inherit from this mixin to provide consistent
    --introspect functionality that enables auto-discovery and validation.

    Usage:
        class MyNode(NodeIntrospectionMixin):
            @classmethod
            def get_node_name(cls) -> str:
                return "my_node"

            # ... implement other abstract methods
    """

    @classmethod
    @abstractmethod
    def get_metadata_loader(cls) -> object:
        """
        Subclasses must implement this to provide a metadata loader instance.
        This enables dependency injection and avoids hardcoding.
        """

    @classmethod
    def get_node_name(cls) -> str:
        node_name: str = cls.get_metadata_loader().node_name  # type: ignore[attr-defined]  # Metadata loader duck-typed interface; attr exists at runtime
        return node_name

    @classmethod
    def get_node_version(cls) -> ModelSemVer:
        node_version: ModelSemVer = cls.get_metadata_loader().node_version  # type: ignore[attr-defined]  # Metadata loader duck-typed interface; attr exists at runtime
        return node_version

    @classmethod
    def get_node_description(cls) -> str:
        node_description: str = cls.get_metadata_loader().node_description  # type: ignore[attr-defined]  # Metadata loader duck-typed interface; attr exists at runtime
        return node_description

    @classmethod
    def get_input_state_class(cls) -> type[BaseModel]:
        """
        Return the input state model class.

        By default, attempts to get from metadata loader if available.
        Override this method to provide node-specific input state class.

        Returns:
            type[BaseModel]: Input state model class

        Raises:
            AttributeError: If metadata loader doesn't provide input_state_class
        """
        metadata_loader = cls.get_metadata_loader()
        if hasattr(metadata_loader, "input_state_class"):
            input_state_class: type[BaseModel] = metadata_loader.input_state_class
            return input_state_class
        # Fallback to generic BaseModel if not provided
        return BaseModel

    @classmethod
    def get_output_state_class(cls) -> type[BaseModel]:
        """
        Return the output state model class.

        By default, attempts to get from metadata loader if available.
        Override this method to provide node-specific output state class.

        Returns:
            type[BaseModel]: Output state model class

        Raises:
            AttributeError: If metadata loader doesn't provide output_state_class
        """
        metadata_loader = cls.get_metadata_loader()
        if hasattr(metadata_loader, "output_state_class"):
            output_state_class: type[BaseModel] = metadata_loader.output_state_class
            return output_state_class
        # Fallback to generic BaseModel if not provided
        return BaseModel

    @classmethod
    def get_error_codes_class(cls) -> type:
        """
        Return the error codes enum class.

        By default, attempts to get from metadata loader if available.
        Override this method to provide node-specific error codes enum.

        Returns:
            type: Error codes enum class

        Raises:
            AttributeError: If metadata loader doesn't provide error_codes_class
        """
        metadata_loader = cls.get_metadata_loader()
        if hasattr(metadata_loader, "error_codes_class"):
            error_codes_class: type = metadata_loader.error_codes_class
            return error_codes_class
        # Fallback to creating a minimal error codes enum
        from enum import Enum

        return type("DefaultErrorCodes", (Enum,), {"UNKNOWN": "UNKNOWN_ERROR"})

    @classmethod
    def get_node_author(cls) -> str:
        """Return the node author. Override if different from default."""
        return "ONEX Team"

    @classmethod
    def get_schema_version(cls) -> str:
        """Return the schema version. Override if different from default."""
        return "1.0.0"

    @classmethod
    def get_protocol_version(cls) -> str:
        """Return the protocol version. Override if different from default."""
        return "1.1.0"

    @classmethod
    def get_python_version_requirement(cls) -> str:
        """Return Python version requirement. Override if different from default."""
        return ">=3.11"

    @classmethod
    def get_runtime_dependencies(cls) -> list[str]:
        """Return runtime dependencies. Override to specify dependencies."""
        return ["omnibase.core", "omnibase.model"]

    @classmethod
    def get_optional_dependencies(cls) -> list[str]:
        """Return optional dependencies. Override to specify optional deps."""
        return []

    @classmethod
    def get_external_tools(cls) -> list[str]:
        """Return external tool dependencies. Override to specify tools."""
        return []

    @classmethod
    def get_node_capabilities(cls) -> list[EnumNodeCapability]:
        """Return node capabilities. Override to specify capabilities."""
        return []

    @classmethod
    def get_event_channels(cls) -> ModelEventChannels:
        """Return event channels configuration. Override to specify channels."""
        return ModelEventChannels(
            subscribes_to=["onex.discovery.broadcast"],
            publishes_to=["onex.discovery.response"],
        )

    @classmethod
    def get_cli_entrypoint(cls) -> str:
        """Return CLI entrypoint command. Override if different from default."""
        node_name = cls.get_node_name()
        return f"python -m omnibase.nodes.{node_name}.v1_0_0.node"

    @classmethod
    def get_cli_required_args(cls) -> list[ModelCLIArgument]:
        """Return required CLI arguments. Override to specify required args."""
        return []

    @classmethod
    def get_cli_optional_args(cls) -> list[ModelCLIArgument]:
        """Return optional CLI arguments. Override to specify optional args."""
        return [
            ModelCLIArgument(
                name="--introspect",
                type="bool",
                required=False,
                description="Display node contract and capabilities",
                default=None,
                choices=None,
            ),
        ]

    @classmethod
    def get_cli_exit_codes(cls) -> list[int]:
        """Return possible CLI exit codes. Override if different from default."""
        return [0, 1, 2]

    @classmethod
    def _extract_state_model_fields(
        cls,
        model_class: type[BaseModel],
    ) -> list[ModelStateField]:
        """Extract field information from a Pydantic model."""
        fields = []

        for field_name, field_info in model_class.model_fields.items():
            # Get field type as string
            field_type = str(field_info.annotation) if field_info.annotation else "Any"

            # Determine if field is required
            is_required = field_info.is_required()

            # Get field description
            description = field_info.description or f"Field {field_name}"

            # Get default value
            default_value = (
                field_info.default if hasattr(field_info, "default") else None
            )

            fields.append(
                ModelStateField(
                    name=field_name,
                    type=field_type,
                    required=is_required,
                    description=description,
                    default=default_value,
                ),
            )

        return fields

    @classmethod
    def _extract_error_codes(cls) -> ModelErrorCodes:
        """Extract error codes from the node's error codes class."""
        error_codes_class = cls.get_error_codes_class()

        # Get component name (e.g., "STAMP" from StamperErrorCode)
        component = "UNKNOWN"
        if hasattr(error_codes_class, "__name__"):
            class_name = error_codes_class.__name__
            if class_name.endswith("ErrorCode"):
                # Extract component from class name (e.g., StamperErrorCode -> STAMP)
                component = class_name.replace("ErrorCode", "").upper()

        # Extract error codes
        codes = []
        if hasattr(error_codes_class, "__members__"):
            for error_code in error_codes_class.__members__.values():
                # Get error code details
                code_value = error_code.value

                # Extract number from code (e.g., "ONEX_STAMP_001_..." -> 1)
                number = 0
                if hasattr(error_code, "get_number"):
                    number = error_code.get_number()

                # Get description
                description = "Unknown error"
                if hasattr(error_code, "get_description"):
                    description = error_code.get_description()

                # Get exit code
                exit_code = 1
                if hasattr(error_code, "get_exit_code"):
                    exit_code = error_code.get_exit_code()

                # Determine category from code name
                category = "general"
                if "_FILE_" in code_value:
                    category = "file"
                elif "_DIRECTORY_" in code_value:
                    category = "directory"
                elif "_VALIDATION_" in code_value:
                    category = "validation"
                elif "_CONFIG" in code_value:
                    category = "configuration"

                codes.append(
                    ModelErrorCode(
                        code=code_value,
                        number=number,
                        description=description,
                        exit_code=exit_code,
                        category=category,
                    ),
                )

        return ModelErrorCodes(component=component, codes=codes, total_codes=len(codes))

    @classmethod
    def get_introspection_response(cls) -> ModelNodeIntrospectionResponse:
        """
        Generate complete introspection response for the node.

        Returns:
            ModelNodeIntrospectionResponse with all node metadata and capabilities
        """
        node_name = cls.get_node_name()

        # Get version information from resolver
        # TODO(OMN-TBD): Implement global_resolver for version information  [NEEDS TICKET]
        # Once implemented, global_resolver should return ModelSemVer objects directly

        # Create enhanced node metadata with version information using composed models
        from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
        from omnibase_core.models.node_metadata.model_node_core_metadata import (
            ModelNodeCoreMetadata,
        )
        from omnibase_core.models.node_metadata.model_node_organization_metadata import (
            ModelNodeOrganizationMetadata,
        )

        node_metadata = ModelNodeMetadataInfo(
            core=ModelNodeCoreMetadata(
                node_display_name=node_name,
                node_type=EnumMetadataNodeType.FUNCTION,  # Default, could be made dynamic
                version=cls.get_node_version(),  # Already returns ModelSemVer
            ),
            organization=ModelNodeOrganizationMetadata(
                description=cls.get_node_description(),
                author=cls.get_node_author(),
                tags=cls._get_node_tags(),
                # categories expects list[EnumCategory], but _get_node_category() returns Sequence[str]
                # For now, leave as default empty list until proper conversion is implemented
            ),
        )

        # Create contract model
        contract = ModelContract(
            input_state_schema=f"{node_name}_input.schema.json",
            output_state_schema=f"{node_name}_output.schema.json",
            cli_interface=ModelCLIInterface(
                entrypoint=cls.get_cli_entrypoint(),
                exit_codes=cls.get_cli_exit_codes(),
                supports_introspect=True,
            ),
            protocol_version=parse_semver_from_string(cls.get_protocol_version()),
        )

        # Create state models (simplified - ModelState API has changed)
        from omnibase_core.models.core.model_protocol_metadata import (
            ModelGenericMetadata,
        )
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        state_models = ModelStates(
            input=ModelState(
                metadata=ModelGenericMetadata(
                    version=ModelSemVer(major=1, minor=0, patch=0)
                ),  # Default metadata
                version=0,
            ),
            output=ModelState(
                metadata=ModelGenericMetadata(
                    version=ModelSemVer(major=1, minor=0, patch=0)
                ),  # Default metadata
                version=0,
            ),
        )

        # Create error codes model
        error_codes = cls._extract_error_codes()

        # Create dependencies model
        # Parse python version requirement (e.g., ">=3.11" -> "3.11")
        python_version_str = (
            cls.get_python_version_requirement().replace(">=", "").strip()
        )
        dependencies = ModelDependencies(
            runtime=cls.get_runtime_dependencies(),
            optional=cls.get_optional_dependencies(),
            python_version=parse_semver_from_string(python_version_str),
            external_tools=cls.get_external_tools(),
        )

        # Get capabilities
        capabilities = cls.get_node_capabilities()

        # Get event channels
        event_channels = cls.get_event_channels()

        # Create and return the complete response
        return create_node_introspection_response(
            node_metadata=node_metadata,
            contract=contract,
            state_models=state_models,
            error_codes=error_codes,
            dependencies=dependencies,
            capabilities=capabilities,
            event_channels=event_channels,
            introspection_version=ModelSemVer(
                major=1, minor=1, patch=0
            ),  # Enhanced version with ecosystem info
        )

    @classmethod
    def _get_node_category(cls) -> str:
        """Return node category. Override to specify category."""
        return "utility"

    @classmethod
    def _get_node_tags(cls) -> list[str]:
        """Return node tags. Override to specify tags."""
        return []

    @classmethod
    def _get_node_maturity(cls) -> str:
        """Return node maturity level. Override to specify maturity."""
        return "stable"

    @classmethod
    def _get_node_use_cases(cls) -> list[str]:
        """Return node use cases. Override to specify use cases."""
        return []

    @classmethod
    def _get_performance_profile(cls) -> TypedDictPerformanceProfile:
        """Return performance profile. Override to specify performance characteristics."""
        return TypedDictPerformanceProfile(
            typical_execution_time="unknown",
            memory_usage="unknown",
            cpu_intensive=False,
        )

    @classmethod
    def handle_introspect_command(
        cls, event_bus: "ProtocolEventBus | None" = None
    ) -> None:
        """
        Handle the --introspect command by generating and emitting the response via the event bus/logger node.
        This method should be called from the node's main() function when --introspect is detected in the command line arguments.
        Emits a correlation_id if provided via event_bus, environment, or CLI args.
        """
        import os

        # 1. Try to extract correlation_id from event_bus (if it has one)
        correlation_id = None
        if hasattr(event_bus, "correlation_id"):
            correlation_id = event_bus.correlation_id  # type: ignore[union-attr]  # Checked via hasattr; optional protocol extension
        # 2. Fallback to ONEX_CORRELATION_ID env var
        if not correlation_id:
            correlation_id = os.environ.get("ONEX_CORRELATION_ID")
        # 3. Fallback to --correlation-id in sys.argv
        if not correlation_id:
            for i, arg in enumerate(sys.argv):
                if arg == "--correlation-id" and i + 1 < len(sys.argv):
                    correlation_id = sys.argv[i + 1]
                    break
        try:
            response = cls.get_introspection_response()
            emit_log_event_sync(
                LogLevel.INFO,
                response.model_dump_json(indent=2),
                {
                    "event_type": create_event_type_from_registry(
                        "INTROSPECTION_RESPONSE"
                    ),
                    "node_id": cls.get_node_name(),
                    "event_bus": event_bus,
                    "correlation_id": correlation_id,
                },
            )
            sys.exit(0)
        except (ModelOnexError, RuntimeError, ValueError) as e:
            error_response = {
                "error": "Introspection failed",
                "message": str(e),
                "node": cls.get_node_name(),
            }
            import json

            emit_log_event_sync(
                LogLevel.ERROR,
                json.dumps(error_response, indent=2),
                {
                    "event_type": create_event_type_from_registry(
                        "INTROSPECTION_RESPONSE"
                    ),
                    "node_id": cls.get_node_name(),
                    "event_bus": event_bus,
                    "correlation_id": correlation_id,
                },
            )
            sys.exit(1)
