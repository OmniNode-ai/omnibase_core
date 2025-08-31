"""
Simplified ModelNodeBase - Phase 6 Final Implementation.
Thin orchestrator coordinating extracted services: <200 lines target.
Author: ONEX Framework Team
"""

from pathlib import Path

from omnibase_core.core.core_uuid_service import UUIDService
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.models.model_node_base import ModelNodeBase
from omnibase_core.core.models.model_registry_reference import ModelRegistryReference
from omnibase_core.core.services.cli_service.v1_0_0.cli_service import CliService
from omnibase_core.core.services.container_service.v1_0_0.container_service import (
    ContainerService,
)
from omnibase_core.core.services.contract_service.v1_0_0.contract_service import (
    ContractService,
)
from omnibase_core.core.services.event_bus_service.v1_0_0.event_bus_service import (
    EventBusService,
)
from omnibase_core.core.services.event_bus_service.v1_0_0.models.model_event_bus_config import (
    ModelEventBusConfig,
)
from omnibase_core.core.services.tool_discovery_service.v1_0_0.tool_discovery_service import (
    ToolDiscoveryService,
)
from omnibase_core.model.core.model_semver import ModelSemVer
from omnibase_core.protocol.protocol_reducer import ProtocolReducer
from omnibase_core.protocol.protocol_registry import ProtocolRegistry


class ModelNodeBase(ProtocolReducer):
    """Simplified ModelNodeBase - thin orchestrator coordinating extracted services."""

    def __init__(
        self,
        contract_path: Path,
        node_id: str | None = None,
        event_bus: object | None = None,
        registry: ProtocolRegistry | None = None,
        **kwargs,
    ):
        """Initialize ModelNodeBase with service coordination."""
        super().__init__(contract_path=contract_path, **kwargs)

        # Initialize services
        self._contract_service = ContractService()
        self._container_service = ContainerService()
        self._tool_discovery_service = ToolDiscoveryService()
        self._cli_service = CliService()
        self._event_bus_service = EventBusService(ModelEventBusConfig())

        try:
            contract_content = self._contract_service.load_contract(contract_path)

            # Derive node_id from contract if not provided
            if node_id is None:
                node_id = contract_content.node_name

            registry_reference = ModelRegistryReference(
                node_id=node_id,
                registry_class_name="ONEXContainer",
                registry_type="simplified",
            )

            self.state = ModelNodeBase(
                contract_path=contract_path,
                node_id=node_id,
                contract_content=contract_content,
                registry_reference=registry_reference,
                node_name=contract_content.node_name,
                version=f"{contract_content.contract_version.major}.{contract_content.contract_version.minor}.{contract_content.contract_version.patch}",
                node_tier=1,
                node_classification=contract_content.tool_specification.business_logic_pattern.value,
                initialization_metadata={"simplified_nodebase": "phase6"},
            )

            self._event_bus_service.initialize_event_bus(event_bus, auto_resolve=True)
            if registry is None:
                container_result = (
                    self._container_service.create_container_from_contract(
                        contract_content=contract_content,
                        node_id=node_id,
                        nodebase_ref=self,
                    )
                )
                self._registry = container_result.registry
            else:
                self._registry = registry

            # Add get_node_version method to registry for tool compatibility
            def get_node_version():
                return self.state.contract_content.contract_version

            self._registry._container.get_node_version = get_node_version

            tool_result = self._tool_discovery_service.resolve_tool_from_contract(
                contract_content=contract_content,
                registry=self._registry,
                contract_path=contract_path,
            )
            self._main_tool = tool_result.tool_instance

            # Publish introspection if event bus available
            if self._event_bus_service._event_bus:
                self._event_bus_service.publish_introspection_event(
                    node_id=self.state.node_id,
                    node_name=self.state.node_name,
                    version=str(self.state.version),
                    actions=["health_check", "process", "run"],
                    protocols=["event_bus", "registry"],
                    metadata={
                        "tier": self.state.node_tier,
                        "classification": self.state.node_classification,
                    },
                    correlation_id=UUIDService.generate_correlation_id(),
                )
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.INITIALIZATION_FAILED,
                message=f"ModelNodeBase initialization failed: {e!s}",
                context={"contract_path": str(contract_path)},
            ) from e

    def run(self, input_state: object) -> object:
        """Universal run method with complete event lifecycle."""
        correlation_uuid = UUIDService.generate_correlation_id()
        metadata = {
            "tier": self.state.node_tier,
            "classification": self.state.node_classification,
        }

        self._event_bus_service.emit_node_start(
            self.state.node_id,
            self.state.node_name,
            correlation_uuid,
            metadata,
        )

        try:
            result = self.process(input_state)
            self._event_bus_service.emit_node_success(
                self.state.node_id,
                self.state.node_name,
                correlation_uuid,
                result,
                {},
            )
            return result
        except Exception as e:
            error = (
                e
                if isinstance(e, OnexError)
                else OnexError(
                    message=f"Node execution failed: {e!s}",
                    code=CoreErrorCode.OPERATION_FAILED,
                    correlation_id=str(correlation_uuid),
                    context={"node_name": self.state.node_name},
                )
            )
            self._event_bus_service.emit_node_failure(
                self.state.node_id,
                self.state.node_name,
                correlation_uuid,
                error,
                {},
            )
            raise error from e

    def process(self, input_state: object) -> object:
        """Universal process method - delegates to main tool."""
        try:
            if hasattr(self._main_tool, "process"):
                return self._main_tool.process(input_state)
            if hasattr(self._main_tool, "run"):
                return self._main_tool.run(input_state)
            raise OnexError(
                code=CoreErrorCode.OPERATION_FAILED,
                message="Main tool does not implement process() or run() method",
                context={"node_name": self.state.node_name},
            )
        except Exception as e:
            if isinstance(e, OnexError):
                raise
            raise OnexError(
                code=CoreErrorCode.OPERATION_FAILED,
                message=f"Tool execution failed: {e!s}",
                context={"node_name": self.state.node_name},
            ) from e

    def health_check(self) -> object:
        """Universal health check method."""
        try:
            return (
                self._main_tool.health_check()
                if hasattr(self._main_tool, "health_check")
                else {"status": "healthy", "node_name": self.state.node_name}
            )
        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.RESOURCE_UNAVAILABLE,
                message=f"Health check failed: {e!s}",
                context={
                    "correlation_id": str(UUIDService.generate_correlation_id()),
                    "node_name": self.state.node_name,
                },
            ) from e

    # Essential property accessors
    @property
    def node_name(self) -> str:
        return self.state.node_name

    @property
    def version(self) -> str:
        return self.state.version

    @property
    def registry(self) -> ProtocolRegistry:
        return self._registry

    @property
    def node_version(self) -> ModelSemVer:
        return self.state.contract_content.contract_version

    def get_event_patterns(self) -> list[str]:
        """Get event patterns using EventBusService."""
        return self._event_bus_service.get_event_patterns_from_contract(
            contract_content=self.state.contract_content,
            node_name=self.state.node_name,
        )

    @staticmethod
    def run_cli(contract_path: Path, args: list[str] | None = None) -> int:
        """Static CLI entry point using CliService."""
        return CliService().run_cli(contract_path, args)
