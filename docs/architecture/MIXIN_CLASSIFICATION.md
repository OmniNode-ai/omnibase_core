> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Mixin Classification

# Mixin Classification Reference

> **Version**: 1.1.0
> **Last Updated**: 2026-02-14

---

## R/H/D Classification System

**Quick Reference**: R = Runtime, H = Handler, D = Domain

All mixins in omnibase_core are classified into three categories based on their responsibilities.

> **Note**: The tables below include both behavioral mixins and supporting data models. Data models (prefixed with `Model` rather than `Mixin`) are Pydantic classes used by mixins but are not behavioral mixins themselves. They are included for completeness as they reside in `models/mixins/`.

### Runtime (R) - Infrastructure Concerns

Cross-cutting concerns applied consistently across all node types.

**Characteristics**:
- Node lifecycle, identity, and infrastructure management
- Observability (metrics, logging, health)
- Event bus integration
- Applied to every node automatically

**Migration Target**: `NodeRuntime` / `NodeInstance` services

### Handler (H) - I/O Operations

External service integrations that perform I/O operations.

**Characteristics**:
- Network, database, file system, or external process operations
- Deployment-specific configurations
- Multiple implementations (mock vs. production)
- Implements SPI protocols

**Migration Target**: `omnibase_infra/handlers/` (NOT core - violates Core I/O Invariant)

### Domain (D) - Pure Business Logic

Pure computation with no side effects or runtime dependencies.

**Characteristics**:
- No I/O, no event bus, no external calls
- Stateless or explicitly state-passing
- Easily unit testable in isolation
- Framework-agnostic

**Migration Target**: `omnibase_core/utils/` and `omnibase_core/domain/`

---

## Classification Summary

| Classification | Mixins | Data Models | Total |
|----------------|--------|-------------|-------|
| **Runtime (R)** | 21 | 1 | 22 |
| **Handler (H)** | 3 | 0 | 3 |
| **Domain (D)** | 15 | 2 | 17 |
| **Total** | **39** | **3** | **42** |

> **Data Models in `models/mixins/`**: `ModelCompletionData` (R), `ModelLogData` (D), `ModelNodeIntrospectionData` (D)

---

## Complete Mixin Classification Table

| # | Mixin Name | Purpose | Class | Target Location |
|---|------------|---------|-------|-----------------|
| 1 | `MixinCaching` | In-memory caching for node operations | R | `NodeRuntime.cache_service` |
| 2 | `ModelCompletionData` | Tracks completion status/progress *(Data Model)* | R | `models/mixins/model_completion_data.py` |
| 3 | `MixinLazyValue` | Lazy evaluation wrapper class | D | `utils/lazy.py` |
| 4 | `MixinMetrics` | Prometheus-style metrics collection | R | `NodeRuntime.metrics_service` |
| 5 | `MixinNodeSetup` | Standard node initialization | R | `NodeRuntime.__init__()` |
| 6 | `MixinDiscovery` | Service discovery client | H | `omnibase_infra/handlers/discovery_handler.py` |
| 7 | `MixinFSMExecution` | Finite state machine execution | D | `domain/fsm/executor.py` |
| 8 | `MixinIntentPublisher` | Publishes ModelIntent events | R | `NodeRuntime.intent_emitter` |
| 9 | `MixinSerializable` | Basic serialization interface | D | `utils/serialization.py` |
| 10 | `MixinCanonicalYAMLSerializer` | Canonical YAML serialization | D | `utils/canonical_yaml.py` |
| 11 | `MixinCLIHandler` | CLI argument parsing/handling | H | `omnibase_infra/handlers/cli_handler.py` |
| 12 | `MixinContractMetadata` | Contract metadata extraction | D | `utils/contract_metadata.py` |
| 13 | `MixinContractStateReducer` | Contract-driven state reduction | D | `domain/fsm/contract_reducer.py` |
| 14 | `MixinDebugDiscoveryLogging` | Debug logging for discovery | R | `NodeRuntime.logger` (debug mode) |
| 15 | `MixinDiscoveryResponder` | Responds to discovery requests | R | `NodeRuntime.discovery_responder` |
| 16 | `MixinEventBus` | Event bus connection management | R | `NodeRuntime.event_bus` |
| 17 | `MixinEventDrivenNode` | Base event-driven node behavior | R | `NodeRuntime` (core) |
| 18 | `MixinEventHandler` | Event handler registration | R | `NodeRuntime.event_handlers` |
| 19 | `MixinComputeExecution` | Compute node execution logic | R | `NodeRuntime.compute_executor` |
| 20 | `MixinFailFast` | Fail-fast validation patterns | D | `utils/fail_fast.py` |
| 21 | `MixinHashComputation` | SHA256 hash for metadata blocks | D | `utils/hash.py` |
| 22 | `MixinHealthCheck` | Health check implementation | R | `NodeRuntime.health_service` |
| 23 | `MixinEffectExecution` | Effect node execution logic | R | `NodeRuntime.effect_executor` |
| 24 | `MixinIntrospectFromContract` | Load introspection from contract | D | `utils/contract_introspection.py` |
| 25 | `MixinNodeIntrospection` | Node introspection response | R | `NodeRuntime.introspection_service` |
| 26 | `MixinIntrospectionPublisher` | Publish introspection events | R | `NodeRuntime.introspection_publisher` |
| 27 | `MixinLazyEvaluation` | Lazy evaluation patterns | D | `utils/lazy.py` |
| 28 | `ModelLogData` | Structured log data model *(Data Model)* | D | `models/mixins/model_log_data.py` |
| 29 | `MixinNodeExecutor` | Persistent executor mode | R | `NodeRuntime.executor_service` |
| 30 | `MixinNodeIdFromContract` | Load node ID from contract | D | `utils/node_id.py` |
| 31 | `ModelNodeIntrospectionData` | Introspection data container *(Data Model)* | D | `models/mixins/model_node_introspection_data.py` |
| 32 | `MixinNodeLifecycle` | Node lifecycle events | R | `NodeRuntime.lifecycle_manager` |
| 33 | `MixinNodeService` | Service interface for nodes | R | `NodeRuntime.service_interface` |
| 34 | `MixinSensitiveFieldRedaction` | Sensitive field redaction | D | `utils/redaction.py` |
| 35 | `MixinRequestResponseIntrospection` | Real-time introspection | R | `NodeRuntime.realtime_introspection` |
| 36 | `MixinServiceRegistry` | Service registry maintenance | H | `omnibase_infra/handlers/service_registry_handler.py` |
| 37 | `MixinToolExecution` | Tool execution event handling | R | `NodeRuntime.tool_executor` |
| 38 | `MixinContractPublisher` | Contract event publishing | R | `NodeRuntime.contract_publisher` |
| 39 | `MixinWorkflowExecution` | Workflow execution from contracts | R | `NodeRuntime.workflow_executor` |
| 40 | `MixinYAMLSerialization` | YAML serialization with comments | D | `utils/yaml_serialization.py` |
| 41 | `MixinNodeTypeValidator` | Validates node type constraints | D | `utils/node_type_validation.py` |
| 42 | `MixinTruncationValidation` | Truncation boundary validation | D | `utils/truncation.py` |

---

## Mixins by Classification

### Runtime (R) - 21 Mixins + 1 Data Model

| Mixin | Target |
|-------|--------|
| `MixinCaching` | `NodeRuntime.cache_service` |
| `ModelCompletionData` *(Data Model)* | `models/mixins/model_completion_data.py` |
| `MixinComputeExecution` | `NodeRuntime.compute_executor` |
| `MixinContractPublisher` | `NodeRuntime.contract_publisher` |
| `MixinMetrics` | `NodeRuntime.metrics_service` |
| `MixinNodeSetup` | `NodeRuntime.__init__()` |
| `MixinIntentPublisher` | `NodeRuntime.intent_emitter` |
| `MixinDebugDiscoveryLogging` | `NodeRuntime.logger` |
| `MixinDiscoveryResponder` | `NodeRuntime.discovery_responder` |
| `MixinEffectExecution` | `NodeRuntime.effect_executor` |
| `MixinEventBus` | `NodeRuntime.event_bus` |
| `MixinEventDrivenNode` | `NodeRuntime` (core) |
| `MixinEventHandler` | `NodeRuntime.event_handlers` |
| `MixinHealthCheck` | `NodeRuntime.health_service` |
| `MixinNodeIntrospection` | `NodeRuntime.introspection_service` |
| `MixinIntrospectionPublisher` | `NodeRuntime.introspection_publisher` |
| `MixinNodeExecutor` | `NodeRuntime.executor_service` |
| `MixinNodeLifecycle` | `NodeRuntime.lifecycle_manager` |
| `MixinNodeService` | `NodeRuntime.service_interface` |
| `MixinRequestResponseIntrospection` | `NodeRuntime.realtime_introspection` |
| `MixinToolExecution` | `NodeRuntime.tool_executor` |
| `MixinWorkflowExecution` | `NodeRuntime.workflow_executor` |

### Handler (H) - 3 Mixins

| Mixin | Target |
|-------|--------|
| `MixinDiscovery` | `omnibase_infra/handlers/discovery_handler.py` |
| `MixinCLIHandler` | `omnibase_infra/handlers/cli_handler.py` |
| `MixinServiceRegistry` | `omnibase_infra/handlers/service_registry_handler.py` |

### Domain (D) - 15 Mixins + 2 Data Models

| Mixin | Target |
|-------|--------|
| `MixinLazyValue` | `utils/lazy.py` |
| `MixinLazyEvaluation` | `utils/lazy.py` |
| `MixinSerializable` | `utils/serialization.py` |
| `MixinCanonicalYAMLSerializer` | `utils/canonical_yaml.py` |
| `MixinYAMLSerialization` | `utils/yaml_serialization.py` |
| `MixinContractMetadata` | `utils/contract_metadata.py` |
| `MixinContractStateReducer` | `domain/fsm/contract_reducer.py` |
| `MixinIntrospectFromContract` | `utils/contract_introspection.py` |
| `MixinFailFast` | `utils/fail_fast.py` |
| `MixinHashComputation` | `utils/hash.py` |
| `MixinSensitiveFieldRedaction` | `utils/redaction.py` |
| `MixinNodeIdFromContract` | `utils/node_id.py` |
| `MixinNodeTypeValidator` | `utils/node_type_validation.py` |
| `MixinTruncationValidation` | `utils/truncation.py` |
| `MixinFSMExecution` | `domain/fsm/executor.py` |
| `ModelLogData` *(Data Model)* | `models/mixins/model_log_data.py` |
| `ModelNodeIntrospectionData` *(Data Model)* | `models/mixins/model_node_introspection_data.py` |

---

## File Locations

All mixins are located in:

```text
src/omnibase_core/mixins/
```

Each mixin follows the naming convention: `mixin_<name>.py`
