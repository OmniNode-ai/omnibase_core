"""
ONEX Dependency Injection Container.

Contract-driven dependency injection container that automatically configures
services based on contract specifications across all ONEX tools and nodes.
"""

# mypy: disable-error-code="no-any-return,misc"

import asyncio
import os
from typing import Dict, Optional, Type, TypeVar, Union

from dependency_injector import containers, providers

from omnibase.core.bootstrap_logger import create_basic_logger
from omnibase.core.container_service_resolver import bind_get_service_method
from omnibase.core.core_error_codes import CoreErrorCode
from omnibase.core.decorators import allow_dict_str_any
from omnibase.core.hybrid_event_bus_factory import create_hybrid_event_bus_standalone
from omnibase.core.service_discovery_manager import ServiceDiscoveryManager
from omnibase.enums.enum_log_level import LogLevelEnum
from omnibase.exceptions import OnexError
from omnibase.protocol.protocol_logger import ProtocolLogger
from omnibase.tools.registry.tool_consul_service_discovery import (
    ToolConsulServiceDiscovery,
)

T = TypeVar("T")


@allow_dict_str_any("consul configuration requires flexible config structure")
async def _initialize_consul_client(
    consul_config: Dict[str, object], logger: ProtocolLogger
) -> ToolConsulServiceDiscovery:
    """Initialize Consul client with error handling."""
    try:
        # Create a basic registry for Consul client
        from omnibase.registry.base_registry import BaseOnexRegistry

        class ConsulRegistry(BaseOnexRegistry):
            def __init__(self) -> None:
                super().__init__(node_dir=".", logger=logger)

        registry = ConsulRegistry()
        consul_client = ToolConsulServiceDiscovery(
            registry=registry, node_id="onex_container_consul"
        )

        # Test connectivity
        is_available = await consul_client.check_consul_connectivity()
        if is_available:
            logger.emit_log_event_sync(
                level=LogLevelEnum.INFO,
                message="Consul client initialized successfully",
                event_type="consul_init",
            )
        else:
            logger.emit_log_event_sync(
                level=LogLevelEnum.WARNING,
                message="Consul not available, using fallback services",
                event_type="consul_unavailable",
            )

        return consul_client

    except Exception as e:
        logger.emit_log_event_sync(
            level=LogLevelEnum.ERROR,
            message=f"Failed to initialize Consul client: {e}",
            event_type="consul_init_failed",
        )
        raise OnexError(
            f"Consul initialization failed: {str(e)}", CoreErrorCode.OPERATION_FAILED
        ) from e


class ONEXContainer(containers.DeclarativeContainer):
    """
    Contract-driven ONEX dependency injection container.

    This container is auto-generated from contract specifications and provides
    dependency injection for all ONEX tools and nodes.
    """

    # === CONFIGURATION ===
    config = providers.Configuration()

    # === CORE BOOTSTRAP SERVICES ===
    basic_logger = providers.Factory(
        create_basic_logger,
        level=LogLevelEnum.INFO,
    )

    # === CONSUL INTEGRATION ===
    consul_client = providers.Resource(
        _initialize_consul_client, consul_config=config.consul, logger=basic_logger
    )

    # === SERVICE DISCOVERY MANAGER ===
    service_discovery = providers.Singleton(
        ServiceDiscoveryManager,
        consul_client=consul_client,
        static_config=config.services,
        logger=basic_logger,
    )

    # === GENERATION TOOL REGISTRIES ===
    # DI providers for generation tool registries

    contract_validator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_contract_validator.v1_0_0.registry.registry_tool_contract_validator",
            fromlist=["RegistryToolContractValidator"],
        ).RegistryToolContractValidator()
    )

    model_regenerator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_model_regenerator.v1_0_0.registry.registry_tool_model_regenerator",
            fromlist=["RegistryToolModelRegenerator"],
        ).RegistryToolModelRegenerator()
    )

    contract_driven_generator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_contract_driven_generator.v1_0_0.registry.registry_tool_contract_driven_generator",
            fromlist=["RegistryToolContractDrivenGenerator"],
        ).RegistryToolContractDrivenGenerator()
    )

    workflow_generator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_workflow_generator.v1_0_0.registry.registry_workflow_generator",
            fromlist=["RegistryWorkflowGenerator"],
        ).RegistryWorkflowGenerator()
    )

    ast_generator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_ast_generator.v1_0_0.registry.registry_tool_ast_generator",
            fromlist=["RegistryToolAstGenerator"],
        ).RegistryToolAstGenerator()
    )

    file_writer_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_file_writer.v1_0_0.registry.registry_file_writer",
            fromlist=["RegistryFileWriter"],
        ).RegistryFileWriter(container=None)
    )

    introspection_generator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_introspection_generator.v1_0_0.registry.registry_tool_introspection_generator",
            fromlist=["RegistryIntrospectiongenerator"],
        ).RegistryIntrospectiongenerator()
    )

    protocol_generator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_protocol_generator.v1_0_0.registry.registry_tool_protocol_generator",
            fromlist=["RegistryProtocolgenerator"],
        ).RegistryProtocolgenerator()
    )

    node_stub_generator_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_node_stub_generator.v1_0_0.registry.registry_tool_node_stub_generator",
            fromlist=["RegistryNodestubgenerator"],
        ).RegistryNodestubgenerator()
    )

    ast_renderer_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_ast_renderer.v1_0_0.registry.registry_tool_ast_renderer",
            fromlist=["RegistryToolAstRenderer"],
        ).RegistryToolAstRenderer()
    )

    reference_resolver_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_reference_resolver.v1_0_0.registry.registry_tool_reference_resolver",
            fromlist=["RegistryToolReferenceResolver"],
        ).RegistryToolReferenceResolver()
    )

    type_import_registry_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_type_import_registry.v1_0_0.registry.registry_tool_type_import_registry",
            fromlist=["RegistryToolTypeImportRegistry"],
        ).RegistryToolTypeImportRegistry()
    )

    python_class_builder_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_python_class_builder.v1_0_0.registry.registry_tool_python_class_builder",
            fromlist=["RegistryToolPythonClassBuilder"],
        ).RegistryToolPythonClassBuilder()
    )

    subcontract_loader_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_subcontract_loader.v1_0_0.registry.registry_tool_subcontract_loader",
            fromlist=["RegistryToolSubcontractLoader"],
        ).RegistryToolSubcontractLoader()
    )

    import_builder_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.generation.tool_import_builder.v1_0_0.registry.registry_tool_import_builder",
            fromlist=["RegistryToolImportBuilder"],
        ).RegistryToolImportBuilder()
    )

    # === FILE PROCESSING PROVIDERS ===

    # RSD Infrastructure providers (extracted from work ticket generator)
    rsd_cache_manager = providers.Singleton(
        lambda: __import__(
            "omnibase.services.rsd_cache_manager", fromlist=["RSDCacheManager"]
        ).RSDCacheManager()
    )

    rsd_rate_limiter = providers.Singleton(
        lambda: __import__(
            "omnibase.services.rsd_rate_limiter", fromlist=["RSDRateLimiter"]
        ).RSDRateLimiter()
    )

    rsd_metrics_collector = providers.Singleton(
        lambda: __import__(
            "omnibase.services.rsd_metrics_collector", fromlist=["RSDMetricsCollector"]
        ).RSDMetricsCollector()
    )

    # Tree-sitter foundation provider
    tree_sitter_analyzer = providers.Factory(
        lambda cache_manager, metrics_collector: __import__(
            "omnibase.services.tree_sitter_foundation",
            fromlist=["TreeSitterFoundation"],
        ).TreeSitterFoundation(
            cache_manager=cache_manager, metrics_collector=metrics_collector
        ),
        cache_manager=rsd_cache_manager,
        metrics_collector=rsd_metrics_collector,
    )

    # === METADATA TOOL SERVICES ===

    # File stamper service
    file_stamper = providers.Factory(
        lambda: __import__(
            "omnibase.tools.metadata.tool_file_stamper.v1_0_0.node",
            fromlist=["ToolFileStamper"],
        ).ToolFileStamper()
    )

    # OnexTree regeneration service
    onextree_regeneration_service = providers.Singleton(
        lambda container, event_bus: __import__(
            "omnibase.services.onextree_regeneration_service",
            fromlist=["OnexTreeRegenerationService"],
        ).OnexTreeRegenerationService(container=container, event_bus=event_bus),
        container=providers.DependenciesContainer(),
        event_bus=providers.Object(None),  # Placeholder for event bus
    )

    # Unified file processor provider
    unified_file_processor = providers.Factory(
        lambda cache_manager, metrics_collector, rate_limiter, container, file_stamper: __import__(
            "omnibase.services.unified_file_processor",
            fromlist=["UnifiedFileProcessor"],
        ).UnifiedFileProcessor(
            cache_manager=cache_manager,
            metrics_collector=metrics_collector,
            rate_limiter=rate_limiter,
            container=container,
            file_stamper=file_stamper,
        ),
        cache_manager=rsd_cache_manager,
        metrics_collector=rsd_metrics_collector,
        rate_limiter=rsd_rate_limiter,
        container=providers.DependenciesContainer(),
        file_stamper=file_stamper,
    )

    # OnexTree processor registry
    onextree_processor_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.file_processing.tool_onextree_processor.v1_0_0.registry.registry_tool_onextree_processor",
            fromlist=["RegistryToolOnextreeProcessor"],
        ).RegistryToolOnextreeProcessor()
    )

    # OnexIgnore processor registry
    onexignore_processor_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.file_processing.tool_onexignore_processor.v1_0_0.registry.registry_tool_onexignore_processor",
            fromlist=["RegistryToolOnexignoreProcessor"],
        ).RegistryToolOnexignoreProcessor()
    )

    # Unified file processor registry
    unified_file_processor_tool_registry = providers.Singleton(
        lambda: object()  # Placeholder - will be created on demand
    )

    # === KAFKA SERVICES ===

    # Kafka Topic Manager service
    kafka_topic_manager = providers.Factory(
        lambda container: __import__(
            "omnibase.services.kafka_topic_manager.kafka_topic_manager",
            fromlist=["KafkaTopicManager"],
        ).KafkaTopicManager(container=container),
        container=providers.DependenciesContainer(),
    )

    # === LOGGING TOOL REGISTRIES ===

    # Registry providers for smart log formatter tools
    smart_log_formatter_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.logging.tool_smart_log_formatter.v1_0_0.registry.registry_tool_smart_log_formatter",
            fromlist=["RegistryToolSmartLogFormatter"],
        ).RegistryToolSmartLogFormatter()
    )

    # Registry providers for logger engine tools
    logger_engine_registry = providers.Factory(
        lambda: __import__(
            "omnibase.tools.logging.tool_logger_engine.v1_0_0.registry.registry_tool_logger_engine",
            fromlist=["RegistryToolLoggerEngine"],
        ).RegistryToolLoggerEngine()
    )

    # === DYNAMIC SERVICE PROVIDERS ===
    # These will be auto-generated from contracts

    def get_service(
        self,
        protocol_type_or_name: Union[Type[T], str],
        service_name: Optional[str] = None,
    ) -> object:
        """
        Get service instance for protocol type or service name.

        Args:
            protocol_type_or_name: Protocol interface to resolve OR service name string
            service_name: Optional specific service name (when protocol_type is provided)

        Returns:
            Service implementation instance
        """
        # Handle string-only calls like get_service("event_bus")
        if isinstance(protocol_type_or_name, str) and service_name is None:
            service_name = protocol_type_or_name

            # Handle special service name "event_bus"
            if service_name == "event_bus":
                return create_hybrid_event_bus_standalone()

            # For other string names, try to resolve them in registry_map
            protocol_type = None  # Will be handled below
        else:
            protocol_type = protocol_type_or_name

        # Handle protocol type resolution
        if protocol_type and hasattr(protocol_type, "__name__"):
            protocol_name = protocol_type.__name__

            # Contract-driven service resolution for protocols
            if protocol_name == "ProtocolEventBus":
                return create_hybrid_event_bus_standalone()
            elif protocol_name == "ProtocolConsulClient":
                return self.consul_client()
            elif protocol_name == "ProtocolVaultClient":
                # TODO: Implement vault client resolution
                pass
        # Handle generation tool registries with registry pattern
        if service_name:
            registry_map = {
                "contract_validator_registry": self.contract_validator_registry,
                "model_regenerator_registry": self.model_regenerator_registry,
                "contract_driven_generator_registry": self.contract_driven_generator_registry,
                "workflow_generator_registry": self.workflow_generator_registry,
                "ast_generator_registry": self.ast_generator_registry,
                "file_writer_registry": self.file_writer_registry,
                "introspection_generator_registry": self.introspection_generator_registry,
                "protocol_generator_registry": self.protocol_generator_registry,
                "node_stub_generator_registry": self.node_stub_generator_registry,
                "ast_renderer_registry": self.ast_renderer_registry,
                "reference_resolver_registry": self.reference_resolver_registry,
                "type_import_registry_registry": self.type_import_registry_registry,
                "python_class_builder_registry": self.python_class_builder_registry,
                "subcontract_loader_registry": self.subcontract_loader_registry,
                "import_builder_registry": self.import_builder_registry,
                # Logging tool registries
                "smart_log_formatter_registry": self.smart_log_formatter_registry,
                "logger_engine_registry": self.logger_engine_registry,
                # File processing registries
                "onextree_processor_registry": self.onextree_processor_registry,
                "onexignore_processor_registry": self.onexignore_processor_registry,
                "unified_file_processor_tool_registry": self.unified_file_processor_tool_registry,
                # File processing services
                "rsd_cache_manager": self.rsd_cache_manager,
                "rsd_rate_limiter": self.rsd_rate_limiter,
                "rsd_metrics_collector": self.rsd_metrics_collector,
                "tree_sitter_analyzer": self.tree_sitter_analyzer,
                "unified_file_processor": self.unified_file_processor,
                "onextree_regeneration_service": self.onextree_regeneration_service,
            }

            # Add Kafka services to registry map
            registry_map.update(
                {
                    "kafka_topic_manager": self.kafka_topic_manager,
                }
            )

            # Add AI Orchestrator services to registry map
            registry_map.update(
                {
                    "ai_orchestrator_cli_adapter": self.ai_orchestrator_cli_adapter,
                    "ai_orchestrator_node": self.ai_orchestrator_node,
                    "ai_orchestrator_tool": self.ai_orchestrator_tool,
                }
            )

            if service_name in registry_map:
                return registry_map[service_name]()

        # Fallback to service discovery (only if we have a protocol_type)
        if protocol_type:
            discovery_manager = self.service_discovery()
            return asyncio.run(
                discovery_manager.resolve_service(protocol_type, service_name)
            )

        # If no protocol_type and service not found, raise error
        raise OnexError(
            f"Unable to resolve service: {service_name}",
            error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
        )

    # === EVENT BUS INTEGRATION ===

    event_bus_client = providers.Factory(
        create_hybrid_event_bus_standalone,
    )

    event_bus_adapter = providers.Factory(
        lambda url: __import__(
            "omnibase.services.event_bus_adapter", fromlist=["EventBusAdapter"]
        ).EventBusAdapter(base_url=url),
        url=config.event_bus.url.as_str(default="http://onex-event-bus:8080"),
    )

    # === AI ORCHESTRATOR NODE PROVIDERS ===

    # AI Orchestrator CLI adapter for tool discovery
    ai_orchestrator_cli_adapter = providers.Factory(
        lambda event_bus: __import__(
            "omnibase.nodes.node_ai_orchestrator.v1_0_0.cli_integration",
            fromlist=["AIOrchestratorCLIAdapter"],
        ).AIOrchestratorCLIAdapter(event_bus=event_bus),
        event_bus=event_bus_client,
    )

    # AI Orchestrator node provider
    ai_orchestrator_node = providers.Factory(
        lambda event_bus: __import__(
            "omnibase.nodes.node_ai_orchestrator.v1_0_0.node",
            fromlist=["NodeAiOrchestrator"],
        ).NodeAiOrchestrator(event_bus_client=event_bus),
        event_bus=event_bus_client,
    )

    # AI Orchestrator tool provider (for CLI discovery)
    ai_orchestrator_tool = providers.Factory(
        lambda registry: __import__(
            "omnibase.tools.orchestration.tool_ai_orchestrator.v1_0_0.tool_ai_orchestrator",
            fromlist=["ToolAiOrchestrator"],
        ).ToolAiOrchestrator(registry=registry),
        registry=None,  # Will be set when the container is ready
    )


# === CONTAINER FACTORY ===


async def create_onex_container() -> ONEXContainer:
    """
    Create and configure ONEX container.

    This would typically be called during application startup.
    """
    container = ONEXContainer()

    # Load configuration from multiple sources
    container.config.from_dict(
        {
            "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
            "consul": {
                "agent_url": f"http://{os.getenv('CONSUL_HOST', 'localhost')}:{os.getenv('CONSUL_PORT', '8500')}",
                "datacenter": os.getenv("CONSUL_DATACENTER", "dc1"),
                "timeout": int(os.getenv("CONSUL_TIMEOUT", "10")),
            },
            "event_bus": {
                "url": os.getenv("EVENT_BUS_URL", "http://onex-event-bus:8080"),
            },
            "kafka": {
                "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            },
            "kafka_api": {
                "auth_enabled": os.getenv("KAFKA_API_AUTH_ENABLED", "true"),
                "auth_token": os.getenv("KAFKA_API_TOKEN", ""),
                "environment": os.getenv("ENVIRONMENT", "development"),
                "cors_allowed_origins": os.getenv(
                    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
                ),
                "rate_limit": os.getenv("KAFKA_API_RATE_LIMIT", "100"),
                "rate_window": os.getenv("KAFKA_API_RATE_WINDOW", "60"),
                "port": os.getenv("KAFKA_TOPIC_MANAGER_PORT", "8089"),
            },
            "services": {
                # Static service configurations would be loaded here
                # These would be populated from contract analysis
            },
        }
    )

    # Initialize resources
    try:
        await container.consul_client.init()
    except Exception:
        # Consul unavailable, continue with fallback services
        # This is expected during development or when Consul is not running
        container.basic_logger().info("Consul unavailable, using fallback services")

    # Restore get_service method lost during DynamicContainer transformation

    def get_service(
        protocol_type_or_name: Union[Type[T], str],
        service_name: Optional[str] = None,
    ) -> object:
        """
        Get service instance for protocol type or service name.

        Restored method for DynamicContainer instances.
        """
        # Handle string-only calls like get_service("event_bus")
        if isinstance(protocol_type_or_name, str) and service_name is None:
            service_name = protocol_type_or_name

            # Handle special service name "event_bus"
            if service_name == "event_bus":
                return create_hybrid_event_bus_standalone()

            # For other string names, try to resolve them in registry_map
            protocol_type = None  # Will be handled below
        else:
            protocol_type = protocol_type_or_name

        # Handle protocol type resolution
        if protocol_type and hasattr(protocol_type, "__name__"):
            protocol_name = protocol_type.__name__

            # Contract-driven service resolution for protocols
            if protocol_name == "ProtocolEventBus":
                return create_hybrid_event_bus_standalone()
            elif protocol_name == "ProtocolConsulClient":
                return container.consul_client()
            elif protocol_name == "ProtocolVaultClient":
                # TODO: Implement vault client resolution
                pass
        # Handle generation tool registries with registry pattern
        if service_name:
            registry_map = {
                "contract_validator_registry": container.contract_validator_registry,
                "model_regenerator_registry": container.model_regenerator_registry,
                "contract_driven_generator_registry": container.contract_driven_generator_registry,
                "workflow_generator_registry": container.workflow_generator_registry,
                "ast_generator_registry": container.ast_generator_registry,
                "file_writer_registry": container.file_writer_registry,
                "introspection_generator_registry": container.introspection_generator_registry,
                "protocol_generator_registry": container.protocol_generator_registry,
                "node_stub_generator_registry": container.node_stub_generator_registry,
                "ast_renderer_registry": container.ast_renderer_registry,
                "reference_resolver_registry": container.reference_resolver_registry,
                "type_import_registry_registry": container.type_import_registry_registry,
                "python_class_builder_registry": container.python_class_builder_registry,
                "subcontract_loader_registry": container.subcontract_loader_registry,
                "import_builder_registry": container.import_builder_registry,
                # Logging tool registries
                "smart_log_formatter_registry": container.smart_log_formatter_registry,
                "logger_engine_registry": container.logger_engine_registry,
                # File processing registries
                "onextree_processor_registry": container.onextree_processor_registry,
                "onexignore_processor_registry": container.onexignore_processor_registry,
                "unified_file_processor_tool_registry": container.unified_file_processor_tool_registry,
                # File processing services
                "rsd_cache_manager": container.rsd_cache_manager,
                "rsd_rate_limiter": container.rsd_rate_limiter,
                "rsd_metrics_collector": container.rsd_metrics_collector,
                "tree_sitter_analyzer": container.tree_sitter_analyzer,
                "unified_file_processor": container.unified_file_processor,
                "onextree_regeneration_service": container.onextree_regeneration_service,
            }

            # Add Kafka services to registry map
            registry_map.update(
                {
                    "kafka_topic_manager": container.kafka_topic_manager,
                }
            )

            # Add AI Orchestrator services to registry map
            registry_map.update(
                {
                    "ai_orchestrator_cli_adapter": container.ai_orchestrator_cli_adapter,
                    "ai_orchestrator_node": container.ai_orchestrator_node,
                    "ai_orchestrator_tool": container.ai_orchestrator_tool,
                }
            )

            if service_name in registry_map:
                return registry_map[service_name]()

        # Fallback to service discovery (only if we have a protocol_type)
        if protocol_type:
            discovery_manager = container.service_discovery()
            return asyncio.run(
                discovery_manager.resolve_service(protocol_type, service_name)
            )

        # If no protocol_type and service not found, raise error
        raise OnexError(
            f"Unable to resolve service: {service_name}",
            error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
        )

    # Bind the method to the container instance
    import types

    container.get_service = types.MethodType(get_service, container)

    return container


# === GLOBAL CONTAINER INSTANCE ===
_container: Optional[ONEXContainer] = None


async def get_container() -> ONEXContainer:
    """Get or create global container instance."""
    global _container
    if _container is None:
        _container = await create_onex_container()
    return _container


def get_container_sync() -> ONEXContainer:
    """Get container synchronously (for startup scenarios)."""
    return asyncio.run(get_container())
