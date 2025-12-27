# Mixin Classification Reference

> **Version**: 1.0.0
> **Last Updated**: 2025-12-03

---

## R/H/D Classification System

**Quick Reference**: R = Runtime, H = Handler, D = Domain

All 40 mixins in omnibase_core are classified into three categories based on their responsibilities:

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

**Migration Target**: `omnibase_core/utils/` or `omnibase_core/domain/`

---

## Classification Summary

| Classification | Count | Percentage |
|----------------|-------|------------|
| **Runtime (R)** | 21 | 52.5% |
| **Handler (H)** | 3 | 7.5% |
| **Domain (D)** | 16 | 40% |
| **Total** | 40 | 100% |

---

## Complete Mixin Classification Table

| # | Mixin Name | Purpose | Class | Target Location |
|---|------------|---------|-------|-----------------|
| 1 | `MixinCaching` | In-memory caching for node operations | R | `NodeRuntime.cache_service` |
| 2 | `ModelCompletionData` | Tracks completion status/progress | R | `NodeRuntime.completion_tracker` |
| 3 | `MixinLazyValue` | Lazy evaluation wrapper class | D | `utils/lazy.py` |
| 4 | `MixinMetrics` | Prometheus-style metrics collection | R | `NodeRuntime.metrics_service` |
| 5 | `MixinNodeSetup` | Standard node initialization | R | `NodeRuntime.__init__()` |
| 6 | `MixinDiscovery` | Service discovery client | H | `omnibase_infra/handlers/discovery_handler.py` |
| 7 | `MixinFSMExecution` | Finite state machine execution | D | `domain/fsm/executor.py` |
| 8 | `MixinIntentPublisher` | Publishes ModelIntent events | R | `NodeRuntime.intent_emitter` |
| 9 | `MixinSerializable` | Basic serialization interface | D | `utils/serialization.py` |
| 10 | `MixinCanonicalSerialization` | Canonical YAML serialization | D | `utils/canonical_yaml.py` |
| 11 | `MixinCLIHandler` | CLI argument parsing/handling | H | `omnibase_infra/handlers/cli_handler.py` |
| 12 | `MixinContractMetadata` | Contract metadata extraction | D | `utils/contract_metadata.py` |
| 13 | `MixinContractStateReducer` | Contract-driven state reduction | D | `domain/fsm/contract_reducer.py` |
| 14 | `MixinDebugDiscoveryLogging` | Debug logging for discovery | R | `NodeRuntime.logger` (debug mode) |
| 15 | `MixinDiscoveryResponder` | Responds to discovery requests | R | `NodeRuntime.discovery_responder` |
| 16 | `MixinEventBus` | Event bus connection management | R | `NodeRuntime.event_bus` |
| 17 | `MixinEventDrivenNode` | Base event-driven node behavior | R | `NodeRuntime` (core) |
| 18 | `MixinEventHandler` | Event handler registration | R | `NodeRuntime.event_handlers` |
| 19 | `MixinEventListener` | Event subscription management | R | `NodeRuntime.subscriptions` |
| 20 | `MixinFailFast` | Fail-fast validation patterns | D | `utils/fail_fast.py` |
| 21 | `MixinHashComputation` | SHA256 hash for metadata blocks | D | `utils/hash.py` |
| 22 | `MixinHealthCheck` | Health check implementation | R | `NodeRuntime.health_service` |
| 23 | `MixinHybridExecution` | Direct/workflow/orchestrated modes | R | `NodeRuntime.execution_mode_resolver` |
| 24 | `MixinIntrospectFromContract` | Load introspection from contract | D | `utils/contract_introspection.py` |
| 25 | `MixinIntrospection` | Node introspection response | R | `NodeRuntime.introspection_service` |
| 26 | `MixinIntrospectionPublisher` | Publish introspection events | R | `NodeRuntime.introspection_publisher` |
| 27 | `MixinLazyEvaluation` | Lazy evaluation patterns | D | `utils/lazy.py` |
| 28 | `ModelLogData` | Structured log data model | D | `models/mixins/model_log_data.py` |
| 29 | `MixinNodeExecutor` | Persistent executor mode | R | `NodeRuntime.executor_service` |
| 30 | `MixinNodeIdFromContract` | Load node ID from contract | D | `utils/node_id.py` |
| 31 | `ModelNodeIntrospectionData` | Introspection data container | D | `models/mixins/model_node_introspection_data.py` |
| 32 | `MixinNodeLifecycle` | Node lifecycle events | R | `NodeRuntime.lifecycle_manager` |
| 33 | `MixinNodeService` | Service interface for nodes | R | `NodeRuntime.service_interface` |
| 34 | `MixinRedaction` | Sensitive field redaction | D | `utils/redaction.py` |
| 35 | `MixinRequestResponseIntrospection` | Real-time introspection | R | `NodeRuntime.realtime_introspection` |
| 36 | `MixinServiceRegistry` | Service registry maintenance | H | `omnibase_infra/handlers/service_registry_handler.py` |
| 37 | `MixinToolExecution` | Tool execution event handling | R | `NodeRuntime.tool_executor` |
| 38 | `MixinUtils` | Utility functions (canonicalize) | D | `utils/canonical.py` |
| 39 | `MixinWorkflowExecution` | Workflow execution from contracts | R | `NodeRuntime.workflow_executor` |
| 40 | `MixinYAMLSerialization` | YAML serialization with comments | D | `utils/yaml_serialization.py` |

---

## Mixins by Classification

### Runtime (R) - 21 Mixins

| Mixin | Target |
|-------|--------|
| `MixinCaching` | `NodeRuntime.cache_service` |
| `ModelCompletionData` | `NodeRuntime.completion_tracker` |
| `MixinMetrics` | `NodeRuntime.metrics_service` |
| `MixinNodeSetup` | `NodeRuntime.__init__()` |
| `MixinIntentPublisher` | `NodeRuntime.intent_emitter` |
| `MixinDebugDiscoveryLogging` | `NodeRuntime.logger` |
| `MixinDiscoveryResponder` | `NodeRuntime.discovery_responder` |
| `MixinEventBus` | `NodeRuntime.event_bus` |
| `MixinEventDrivenNode` | `NodeRuntime` (core) |
| `MixinEventHandler` | `NodeRuntime.event_handlers` |
| `MixinEventListener` | `NodeRuntime.subscriptions` |
| `MixinHealthCheck` | `NodeRuntime.health_service` |
| `MixinHybridExecution` | `NodeRuntime.execution_mode_resolver` |
| `MixinIntrospection` | `NodeRuntime.introspection_service` |
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

### Domain (D) - 16 Mixins

| Mixin | Target |
|-------|--------|
| `MixinLazyValue` | `utils/lazy.py` |
| `MixinLazyEvaluation` | `utils/lazy.py` |
| `MixinSerializable` | `utils/serialization.py` |
| `MixinCanonicalSerialization` | `utils/canonical_yaml.py` |
| `MixinYAMLSerialization` | `utils/yaml_serialization.py` |
| `MixinContractMetadata` | `utils/contract_metadata.py` |
| `MixinIntrospectFromContract` | `utils/contract_introspection.py` |
| `MixinFailFast` | `utils/fail_fast.py` |
| `MixinHashComputation` | `utils/hash.py` |
| `MixinRedaction` | `utils/redaction.py` |
| `MixinNodeIdFromContract` | `utils/node_id.py` |
| `MixinUtils` | `utils/canonical.py` |
| `MixinFSMExecution` | `domain/fsm/executor.py` |
| `MixinContractStateReducer` | `domain/fsm/contract_reducer.py` |
| `ModelLogData` | `models/mixins/model_log_data.py` |
| `ModelNodeIntrospectionData` | `models/mixins/model_node_introspection_data.py` |

---

## File Locations

All mixins are located in:

```
src/omnibase_core/mixins/
```

Each mixin follows the naming convention: `mixin_<name>.py`
