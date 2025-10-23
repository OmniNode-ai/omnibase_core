# Container Dependency Injection Design

**Version:** 1.0.0
**Status:** Draft
**Author:** ONEX Framework Team
**Date:** 2025-10-21

## Executive Summary

This document outlines the architecture for implementing `ProtocolServiceRegistry` from `omnibase_spi` to replace hardcoded service resolution in `omnibase_core` container domain with proper dependency injection patterns.

**Goal:** Transform the container from string-based service lookup to a full-featured dependency injection system with lifecycle management, health monitoring, and dependency graph tracking.

## Current State Analysis

### Existing Implementation

#### 1. `container_service_resolver.py`

**Current Approach:**
- Hardcoded `_build_registry_map()` function with 30+ service mappings
- String-based service lookup via `getattr(container, service_name)`
- Returns `ModelService` instances with minimal metadata
- No lifecycle management or dependency injection

**Service Categories (30+ services):**
1. **Generation Tool Registries (15 services):**
   - contract_validator_registry
   - model_regenerator_registry
   - contract_driven_generator_registry
   - workflow_generator_registry
   - ast_generator_registry
   - file_writer_registry
   - introspection_generator_registry
   - protocol_generator_registry
   - node_stub_generator_registry
   - ast_renderer_registry
   - reference_resolver_registry
   - type_import_registry_registry
   - python_class_builder_registry
   - subcontract_loader_registry
   - import_builder_registry

2. **Logging Tool Registries (2 services):**
   - smart_log_formatter_registry
   - logger_engine_registry

3. **File Processing Services (8 services):**
   - onextree_processor_registry
   - onexignore_processor_registry
   - unified_file_processor_tool_registry
   - rsd_cache_manager
   - rsd_rate_limiter
   - rsd_metrics_collector
   - tree_sitter_analyzer
   - unified_file_processor
   - onextree_regeneration_service

4. **AI Orchestrator Services (3 services):**
   - ai_orchestrator_cli_adapter
   - ai_orchestrator_node
   - ai_orchestrator_tool

5. **Infrastructure Services (1 service):**
   - infrastructure_cli

6. **Special Protocol Services (3 services):**
   - ProtocolEventBus
   - ProtocolConsulClient
   - ProtocolVaultClient

**Limitations:**
- No type safety for service resolution
- No lifecycle patterns (singleton, transient, scoped)
- No dependency injection capabilities
- No health monitoring or validation
- No circular dependency detection
- Hard to test and extend
- Tight coupling to container implementation

#### 2. `model_onex_container.py`

**Current Approach:**
- Wraps `_BaseModelONEXContainer` from dependency-injector
- `get_service_async()` / `get_service_sync()` methods
- Very limited protocol mapping (only ProtocolLogger → enhanced_logger)
- Has performance monitoring, caching, metrics tracking

**Strengths:**
- Performance monitoring infrastructure
- Async service resolution
- Caching layer
- Metrics tracking

**Limitations:**
- Protocol mapping is minimal
- No DI lifecycle patterns
- No dependency graph tracking
- No validation or health checks

## Target State: ProtocolServiceRegistry

### Protocol Requirements

The `ProtocolServiceRegistry` from `omnibase_spi` requires implementing:

#### Core Service Management
1. **Service Registration:**
   - `register_service()` - Register by interface/implementation
   - `register_instance()` - Register existing instance
   - `register_factory()` - Register factory function
   - `unregister_service()` - Remove registration

2. **Service Resolution:**
   - `resolve_service()` - Resolve single service
   - `resolve_named_service()` - Resolve by name
   - `resolve_all_services()` - Get all implementations
   - `try_resolve_service()` - Optional resolution

3. **Registration Management:**
   - `get_registration()` - Get registration by ID
   - `get_registrations_by_interface()` - Find by interface
   - `get_all_registrations()` - List all registrations

#### Advanced Features

4. **Lifecycle Management:**
   - **Singleton:** One instance shared across container
   - **Transient:** New instance on every resolution
   - **Scoped:** Instance per scope (request, session, thread)
   - **Pooled:** Fixed pool of instances
   - **Lazy:** Created on first use
   - **Eager:** Created at startup

5. **Dependency Management:**
   - `detect_circular_dependencies()` - Detect cycles
   - `get_dependency_graph()` - Analyze dependencies
   - Automatic dependency injection

6. **Injection Scopes:**
   - `create_injection_scope()` - Create new scope
   - `dispose_injection_scope()` - Clean up scope
   - `get_injection_context()` - Get context info
   - Scopes: request, session, thread, process, global, custom

7. **Instance Management:**
   - `get_active_instances()` - List active instances
   - `dispose_instances()` - Cleanup instances
   - Instance counting and pooling

8. **Validation & Health:**
   - `validate_registration()` - Validate registration
   - `validate_service_health()` - Health check
   - `get_registry_status()` - Status reporting

9. **Configuration:**
   - `update_service_configuration()` - Update config
   - Registry configuration management

### Supporting Protocols

The implementation requires these supporting types:

1. **ProtocolServiceRegistration:**
   - registration_id, service_metadata, lifecycle, scope
   - dependencies, registration_status, health_status
   - registration_time, access statistics
   - validate_registration(), is_active()

2. **ProtocolServiceRegistrationMetadata (ProtocolDIServiceMetadata):**
   - service_id, service_name, service_interface, service_implementation
   - version, description, tags, configuration
   - created_at, last_modified_at

3. **ProtocolServiceDependency:**
   - dependency_name, dependency_interface, dependency_version
   - is_required, is_circular, injection_point, default_value
   - validate_dependency(), is_satisfied()

4. **ProtocolRegistryServiceInstance (ProtocolDIServiceInstance):**
   - instance_id, service_registration_id, instance
   - lifecycle, scope, created_at, last_accessed, access_count
   - is_disposed, metadata
   - validate_instance(), is_active()

5. **ProtocolDependencyGraph:**
   - service_id, dependencies, dependents
   - depth_level, circular_references, resolution_order

6. **ProtocolInjectionContext:**
   - context_id, target_service_id, scope
   - resolved_dependencies, injection_time
   - resolution_status, error_details, resolution_path

7. **ProtocolServiceRegistryStatus:**
   - registry_id, status, message
   - total_registrations, active_instances, failed_registrations
   - circular_dependencies, lifecycle/scope distributions
   - health_summary, memory_usage, avg_resolution_time

8. **ProtocolServiceRegistryConfig:**
   - registry_name, auto_wire_enabled, lazy_loading_enabled
   - circular_dependency_detection, max_resolution_depth
   - instance_pooling_enabled, health/performance monitoring

9. **ProtocolServiceValidator:**
   - validate_service(), validate_dependencies()

10. **ProtocolServiceFactory:**
    - create_instance(), dispose_instance()

## Proposed Architecture

### Phase 1: Core Implementation (v1.0)

#### 1.1 New Files

**File:** `src/omnibase_core/container/service_registry.py`

Core implementation of ProtocolServiceRegistry with:
- Service registration (interface, instance, factory)
- Service resolution with caching
- Lifecycle management (singleton, transient initially)
- Basic dependency tracking
- Health monitoring

**File:** `src/omnibase_core/container/models/`

Supporting model implementations:
- `model_service_registration.py` - Implements ProtocolServiceRegistration
- `model_service_metadata.py` - Implements ProtocolDIServiceMetadata
- `model_service_instance.py` - Implements ProtocolDIServiceInstance
- `model_dependency_graph.py` - Implements ProtocolDependencyGraph
- `model_injection_context.py` - Implements ProtocolInjectionContext
- `model_registry_status.py` - Implements ProtocolServiceRegistryStatus
- `model_registry_config.py` - Implements ProtocolServiceRegistryConfig

#### 1.2 Updated Files

**File:** `src/omnibase_core/models/container/model_onex_container.py`

Integration changes:
- Add `_service_registry: ServiceRegistry` property
- Update `get_service_async()` to use registry
- Maintain backward compatibility with existing code
- Add registry initialization in `__init__()`
- Add registry access methods

**File:** `src/omnibase_core/container/container_service_resolver.py`

Migration approach:
- Mark as deprecated (add deprecation warnings)
- Maintain for backward compatibility (Phase 1)
- Create migration helper to register existing services
- Remove in Phase 2

### Phase 2: Advanced Features (v2.0)

#### 2.1 Advanced Lifecycle Support
- Scoped instances (request, session, thread)
- Pooled instances
- Lazy vs eager initialization

#### 2.2 Dependency Injection
- Automatic constructor injection
- Property injection
- Method injection
- Circular dependency detection and prevention

#### 2.3 Scope Management
- Request-scoped services
- Session-scoped services
- Thread-local services
- Custom scope definitions

#### 2.4 Factory Pattern
- Custom service factories
- Factory validation
- Factory-based lifecycle management

### Implementation Strategy

#### Step 1: Create Supporting Models

Implement protocol-compliant models first:

```python
# Example: model_service_metadata.py
from omnibase_spi import ProtocolDIServiceMetadata
from pydantic import BaseModel, Field
from datetime import datetime

class ModelServiceMetadata(BaseModel):
    """Implementation of ProtocolDIServiceMetadata."""

    service_id: str
    service_name: str
    service_interface: str
    service_implementation: str
    version: str  # Will use ModelSemVer
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified_at: datetime | None = None
```

#### Step 2: Implement Core ServiceRegistry

```python
# service_registry.py outline
from omnibase_spi import ProtocolServiceRegistry
from typing import TypeVar, Type

T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")

class ServiceRegistry:
    """
    Implementation of ProtocolServiceRegistry for omnibase_core.

    Provides dependency injection with lifecycle management,
    health monitoring, and dependency graph tracking.
    """

    def __init__(self, config: ProtocolServiceRegistryConfig):
        self._config = config
        self._registrations: dict[str, ProtocolServiceRegistration] = {}
        self._instances: dict[str, list[ProtocolDIServiceInstance]] = {}
        self._interface_map: dict[Type, list[str]] = {}
        self._dependency_graph: dict[str, ProtocolDependencyGraph] = {}
        self._scopes: dict[str, dict[str, Any]] = {}

    async def register_service(
        self,
        interface: Type[TInterface],
        implementation: Type[TImplementation],
        lifecycle: LiteralServiceLifecycle,
        scope: LiteralInjectionScope,
        configuration: dict[str, Any] | None = None,
    ) -> str:
        """Register service by interface and implementation."""
        # Generate registration ID
        # Create registration metadata
        # Store in registry
        # Update interface mapping
        # Return registration ID

    async def resolve_service(
        self,
        interface: Type[TInterface],
        scope: LiteralInjectionScope | None = None,
        context: dict[str, Any] | None = None,
    ) -> TInterface:
        """Resolve service instance with lifecycle management."""
        # Find registration
        # Check lifecycle
        # Return existing singleton or create new instance
        # Track in instances
        # Apply dependency injection
        # Return instance
```

#### Step 3: Migrate Existing Services

Create migration helper to register all 30+ existing services:

```python
async def migrate_existing_services(
    registry: ServiceRegistry,
    container: ModelONEXContainer
) -> None:
    """Migrate all hardcoded services to registry."""

    # Register generation tool registries
    await registry.register_instance(
        interface=object,  # Will use proper protocols later
        instance=container.contract_validator_registry(),
        scope="global",
        metadata={
            "service_name": "contract_validator_registry",
            "category": "generation_tools"
        }
    )

    # ... repeat for all 30+ services
```

#### Step 4: Update Container Integration

```python
# In model_onex_container.py
class ModelONEXContainer:
    def __init__(self, ...):
        # ... existing initialization

        # Initialize service registry
        registry_config = create_default_registry_config()
        self._service_registry = ServiceRegistry(registry_config)

        # Migrate existing services
        asyncio.run(migrate_existing_services(self._service_registry, self))

    async def get_service_async(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
        correlation_id: UUID | None = None,
    ) -> T:
        """Enhanced service resolution using registry."""

        # Try registry first (new approach)
        try:
            service = await self._service_registry.resolve_service(
                interface=protocol_type,
                context={"correlation_id": correlation_id}
            )
            return service
        except Exception:
            # Fallback to old approach for backward compatibility
            return await self._legacy_get_service(protocol_type, service_name)
```

### Backward Compatibility Strategy

**Phase 1 (v1.0):**
- Keep `container_service_resolver.py` functional
- Add deprecation warnings
- Registry runs in parallel with old system
- All new code uses registry
- Existing code continues to work

**Phase 2 (v2.0):**
- Remove `container_service_resolver.py`
- Remove backward compatibility layers
- Pure registry-based resolution
- Breaking change with migration guide

### Migration Path for Consumers

#### Old Approach
```python
# String-based resolution
service = container.get_service("contract_validator_registry")
```

#### New Approach (v1.0 - Compatible)
```python
# Protocol-based resolution (preferred)
from omnibase_spi import ProtocolContractValidator
validator = await container.get_service_async(ProtocolContractValidator)

# String-based still works (deprecated)
service = container.get_service("contract_validator_registry")  # Deprecation warning
```

#### New Approach (v2.0 - Registry Only)
```python
# Direct registry access
from omnibase_spi import ProtocolContractValidator
registry = container.service_registry
validator = await registry.resolve_service(ProtocolContractValidator)
```

## Testing Strategy

### Unit Tests

**File:** `tests/unit/container/test_service_registry.py`

Test coverage:
- Service registration (interface, instance, factory)
- Service resolution (single, named, all, try)
- Lifecycle management (singleton, transient)
- Registration management
- Instance management
- Status reporting

**File:** `tests/unit/container/test_container_integration.py`

Integration tests:
- Container + registry integration
- Backward compatibility
- Migration helper
- Performance benchmarks

### Integration Tests

**File:** `tests/integration/test_service_registry_workflows.py`

Workflow tests:
- Complete service lifecycle
- Multi-service dependency chains
- Health monitoring workflows
- Scope management

## Performance Considerations

### Benchmarks

Target performance metrics:
- Service registration: <1ms per service
- Service resolution (cached): <0.1ms
- Service resolution (new instance): <5ms
- Dependency graph analysis: <10ms for 30+ services
- Status reporting: <5ms

### Optimization Strategies

1. **Caching:**
   - Cache resolved instances for singletons
   - Cache dependency graphs
   - Cache interface mappings

2. **Lazy Loading:**
   - Don't resolve services until needed
   - Don't build dependency graphs until requested

3. **Index Structures:**
   - Fast interface-to-registration lookup
   - Fast registration-id-to-registration lookup

4. **Async Operations:**
   - All resolution is async
   - Parallel dependency resolution where possible

## Security Considerations

1. **Type Safety:**
   - Strong typing for all interfaces
   - Runtime type checking for registrations

2. **Validation:**
   - Validate all registrations before storing
   - Validate dependencies are satisfiable
   - Detect circular dependencies

3. **Resource Management:**
   - Proper disposal of instances
   - Scope-based cleanup
   - Memory leak prevention

## Documentation Requirements

### API Documentation

- Complete docstrings for all public methods
- Usage examples for common patterns
- Migration guide from old to new approach

### Architecture Documentation

- This design document
- UML diagrams for key workflows
- Sequence diagrams for resolution flows

### Migration Guide

**File:** `docs/migration/CONTAINER_DI_MIGRATION.md`

Content:
- Why migrate (benefits)
- What changed (breaking changes)
- How to migrate (step-by-step)
- Common patterns (before/after examples)
- Troubleshooting (FAQ)

## Timeline & Milestones

### Phase 1: Core Implementation (v1.0)

**Week 1:**
- Day 1-2: Create supporting models
- Day 3-4: Implement core ServiceRegistry
- Day 5: Unit tests for models and registry

**Week 2:**
- Day 1-2: Container integration
- Day 3: Migration helper for existing services
- Day 4-5: Integration tests and backward compatibility

**Week 3:**
- Day 1-2: Documentation
- Day 3-4: Performance testing and optimization
- Day 5: Code review and polish

### Phase 2: Advanced Features (v2.0)

**Future planning:**
- Advanced lifecycle patterns
- Dependency injection
- Scope management
- Factory pattern support

## Success Criteria

### Functional Requirements
- [ ] All 30+ services migrated to registry
- [ ] Backward compatibility maintained
- [ ] All tests passing
- [ ] Pre-commit hooks passing (ruff, mypy, black, isort)

### Performance Requirements
- [ ] Service resolution <5ms (99th percentile)
- [ ] No memory leaks in long-running tests
- [ ] Startup time increase <100ms

### Quality Requirements
- [ ] 100% type coverage (mypy strict)
- [ ] 90%+ test coverage
- [ ] Zero ruff violations
- [ ] Complete API documentation

### Deliverables Checklist
- [ ] `src/omnibase_core/container/service_registry.py`
- [ ] Supporting models in `src/omnibase_core/container/models/`
- [ ] Updated `model_onex_container.py`
- [ ] Migration helper
- [ ] Unit tests (`tests/unit/container/`)
- [ ] Integration tests
- [ ] Architecture documentation (this file)
- [ ] Migration guide
- [ ] API documentation

## References

- `omnibase_spi` protocols: `/Volumes/PRO-G40/Code/omnibase_spi/src/omnibase_spi/protocols/container/`
- Current implementation: `src/omnibase_core/container/container_service_resolver.py`
- Container: `src/omnibase_core/models/container/model_onex_container.py`
- ONEX patterns: `docs/patterns/`

## Appendix A: Service Inventory

Complete list of 30+ services to migrate:

### Generation Tool Registries (15)
1. contract_validator_registry
2. model_regenerator_registry
3. contract_driven_generator_registry
4. workflow_generator_registry
5. ast_generator_registry
6. file_writer_registry
7. introspection_generator_registry
8. protocol_generator_registry
9. node_stub_generator_registry
10. ast_renderer_registry
11. reference_resolver_registry
12. type_import_registry_registry
13. python_class_builder_registry
14. subcontract_loader_registry
15. import_builder_registry

### Logging Tool Registries (2)
16. smart_log_formatter_registry
17. logger_engine_registry

### File Processing Services (9)
18. onextree_processor_registry
19. onexignore_processor_registry
20. unified_file_processor_tool_registry
21. rsd_cache_manager
22. rsd_rate_limiter
23. rsd_metrics_collector
24. tree_sitter_analyzer
25. unified_file_processor
26. onextree_regeneration_service

### AI Orchestrator Services (3)
27. ai_orchestrator_cli_adapter
28. ai_orchestrator_node
29. ai_orchestrator_tool

### Infrastructure Services (1)
30. infrastructure_cli

### Special Protocol Services (3)
31. ProtocolEventBus
32. ProtocolConsulClient
33. ProtocolVaultClient

**Total: 33 services**

## Appendix B: Protocol Method Mapping

### ProtocolServiceRegistry Methods (30 methods)

**Properties (3):**
- config
- validator
- factory

**Registration (4):**
- register_service
- register_instance
- register_factory
- unregister_service

**Resolution (4):**
- resolve_service
- resolve_named_service
- resolve_all_services
- try_resolve_service

**Registration Management (3):**
- get_registration
- get_registrations_by_interface
- get_all_registrations

**Instance Management (2):**
- get_active_instances
- dispose_instances

**Validation (2):**
- validate_registration
- validate_service_health

**Dependency Management (2):**
- detect_circular_dependencies
- get_dependency_graph

**Status & Configuration (2):**
- get_registry_status
- update_service_configuration

**Scope Management (3):**
- create_injection_scope
- dispose_injection_scope
- get_injection_context

## Appendix C: Implementation Phases

### Phase 1.1: Foundation (Days 1-2)
- Create model files
- Implement basic data structures
- Unit tests for models

### Phase 1.2: Core Registry (Days 3-4)
- Implement ServiceRegistry class
- Registration methods
- Resolution methods (basic)
- Unit tests

### Phase 1.3: Lifecycle Management (Day 5)
- Singleton lifecycle
- Transient lifecycle
- Instance tracking
- Unit tests

### Phase 1.4: Container Integration (Days 6-7)
- Update ModelONEXContainer
- Migration helper
- Backward compatibility layer
- Integration tests

### Phase 1.5: Documentation & Polish (Days 8-10)
- API documentation
- Migration guide
- Performance testing
- Code review fixes

---

**End of Design Document**
