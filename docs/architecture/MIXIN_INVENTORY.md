# ONEX Mixin Inventory

**Ticket**: OMN-1115
**Status**: Complete
**Last Updated**: 2026-03-08

## Overview

The ONEX platform uses 40 mixin classes across 41 `.py` files (`mixin_utils.py` contains utilities only, no class). All mixins are documented in `src/omnibase_core/mixins/mixin_metadata.yaml` with structured metadata for discovery and code generation.

## Mixin Count by Category

| Category | Count | Examples |
|----------|-------|---------|
| data_management | 4 | MixinCanonicalYAMLSerializer, MixinSerializable, MixinYAMLSerialization, MixinHashComputation |
| discovery | 4 | MixinContractPublisher, MixinDiscovery, MixinIntrospectionPublisher, MixinServiceRegistry |
| execution | 3 | MixinComputeExecution, MixinEffectExecution, MixinNodeExecutor |
| contract | 3 | MixinContractMetadata, MixinNodeIdFromContract, MixinNodeSetup |
| orchestration | 2 | MixinEventDrivenNode, MixinNodeService |
| introspection | 2 | MixinIntrospectFromContract, MixinRequestResponseIntrospection |
| reliability | 2 | MixinFailFast, MixinValidation* |
| observability | 3 | MixinDebugDiscoveryLogging, MixinLogging*, MixinMetrics |
| security | 2 | MixinSensitiveFieldRedaction, MixinSecurity* |
| validation | 2 | MixinNodeTypeValidator, MixinTruncationValidation |
| performance | 2 | MixinLazyEvaluation, MixinLazyValue |
| state_management | 1 | MixinContractStateReducer |
| coordination | 1 | MixinIntentPublisher |
| routing | 1 | MixinHandlerRouting |
| integration | 1 | MixinCLIHandler |
| flow_control | 1 | MixinRetry*, MixinCaching |
| event_bus | 1 | MixinEventBus |
| state_machine | 1 | MixinFSMExecution |
| discovery_events | 2 | MixinDiscoveryResponder, MixinNodeLifecycle |
| event_handling | 1 | MixinEventHandler |
| workflow | 1 | MixinWorkflowExecution |
| health | 1 | MixinHealthCheck |
| tool_execution | 1 | MixinToolExecution |

*Items marked with `*` are documented in metadata but do not have a corresponding `.py` file (planned/abstract).

## Complete Mixin List (Alphabetical)

| # | Mixin Class | File | Category | Phase |
|---|-------------|------|----------|-------|
| 1 | MixinCaching | mixin_caching.py | flow_control | 2 |
| 2 | MixinCanonicalYAMLSerializer | mixin_canonical_serialization.py | data_management | 1 |
| 3 | MixinCLIHandler | mixin_cli_handler.py | integration | 2 |
| 4 | MixinComputeExecution | mixin_compute_execution.py | execution | 1 |
| 5 | MixinContractMetadata | mixin_contract_metadata.py | contract | 2 |
| 6 | MixinContractPublisher | mixin_contract_publisher.py | discovery | 3 |
| 7 | MixinContractStateReducer | mixin_contract_state_reducer.py | state_management | 2 |
| 8 | MixinDebugDiscoveryLogging | mixin_debug_discovery_logging.py | observability | 3 |
| 9 | MixinDiscovery | mixin_discovery.py | discovery | 2 |
| 10 | MixinDiscoveryResponder | mixin_discovery_responder.py | discovery_events | 4 |
| 11 | MixinEffectExecution | mixin_effect_execution.py | execution | 3 |
| 12 | MixinEventBus | mixin_event_bus.py | event_bus | 3 |
| 13 | MixinEventDrivenNode | mixin_event_driven_node.py | orchestration | 4 |
| 14 | MixinEventHandler | mixin_event_handler.py | event_handling | 4 |
| 15 | MixinFailFast | mixin_fail_fast.py | reliability | 1 |
| 16 | MixinFSMExecution | mixin_fsm_execution.py | state_machine | 2 |
| 17 | MixinHandlerRouting | mixin_handler_routing.py | routing | 1 |
| 18 | MixinHashComputation | mixin_hash_computation.py | data_management | 1 |
| 19 | MixinHealthCheck | mixin_health_check.py | health | 3 |
| 20 | MixinIntentPublisher | mixin_intent_publisher.py | coordination | 3 |
| 21 | MixinIntrospectFromContract | mixin_introspect_from_contract.py | introspection | 2 |
| 22 | MixinIntrospectionPublisher | mixin_introspection_publisher.py | discovery | 3 |
| 23 | MixinLazyEvaluation | mixin_lazy_evaluation.py | performance | 1 |
| 24 | MixinLazyValue | mixin_lazy_value.py | performance | 1 |
| 25 | MixinMetrics | mixin_metrics.py | observability | 1 |
| 26 | MixinNodeExecutor | mixin_node_executor.py | execution | 4 |
| 27 | MixinNodeIdFromContract | mixin_node_id_from_contract.py | contract | 2 |
| 28 | MixinNodeIntrospection | mixin_introspection.py | introspection | 2 |
| 29 | MixinNodeLifecycle | mixin_node_lifecycle.py | discovery_events | 4 |
| 30 | MixinNodeService | mixin_node_service.py | orchestration | 4 |
| 31 | MixinNodeSetup | mixin_node_setup.py | contract | 2 |
| 32 | MixinNodeTypeValidator | mixin_node_type_validator.py | validation | 1 |
| 33 | MixinRequestResponseIntrospection | mixin_request_response_introspection.py | introspection | 4 |
| 34 | MixinSensitiveFieldRedaction | mixin_redaction.py | security | 1 |
| 35 | MixinSerializable | mixin_serializable.py | data_management | 1 |
| 36 | MixinServiceRegistry | mixin_service_registry.py | discovery | 4 |
| 37 | MixinToolExecution | mixin_tool_execution.py | tool_execution | 4 |
| 38 | MixinTruncationValidation | mixin_truncation_validation.py | validation | 1 |
| 39 | MixinWorkflowExecution | mixin_workflow_execution.py | workflow | 4 |
| 40 | MixinYAMLSerialization | mixin_yaml_serialization.py | data_management | 1 |

## Key Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Mixin Metadata | `src/omnibase_core/mixins/mixin_metadata.yaml` | Machine-readable metadata for all 40 mixins |
| Capability Mapping | `src/omnibase_core/mixins/mixin_capability_mapping.yaml` | Handler conversion targets and migration phases |
| Dependency Graph Script | `scripts/mixin_dependency_graph.py` | Validates acyclicity and generates migration order |
| ModelMixinMapping | `src/omnibase_core/models/core/model_mixin_mapping.py` | Pydantic model for mapping data |
| EnumNondeterminismClass | `src/omnibase_core/enums/enum_nondeterminism_class.py` | Nondeterminism classification enum |
| Metadata Collection Model | `src/omnibase_core/models/core/model_mixin_metadata_collection.py` | Pydantic model for metadata loading |
| Discovery API | `src/omnibase_core/mixins/mixin_discovery.py` | Runtime mixin discovery and querying |
| Subcontract Mapping Guide | `docs/guides/MIXIN_SUBCONTRACT_MAPPING.md` | Mixin-to-subcontract relationships |

## Migration Phases

The capability mapping assigns each mixin to a migration phase:

- **Phase 1** (13 mixins): Pure compute, deterministic, no I/O. Safest to migrate first.
- **Phase 2** (10 mixins): Stateful or nondeterministic compute. Requires careful state management.
- **Phase 3** (7 mixins): I/O and effect mixins. Needs effect handler wrappers.
- **Phase 4** (10 mixins): Orchestration and lifecycle. Most complex, migrate last.

Run `python scripts/mixin_dependency_graph.py` to see the full migration order.

## Metadata-Only Entries

Five entries in `mixin_metadata.yaml` document planned or abstract mixins that do not have corresponding `.py` files:

1. **MixinRetry** - Planned automatic retry mixin
2. **MixinCircuitBreaker** - Planned circuit breaker pattern
3. **MixinLogging** - Planned structured logging (currently uses `logging_structured` module directly)
4. **MixinSecurity** - Planned security mixin (redaction is in MixinSensitiveFieldRedaction)
5. **MixinValidation** - Planned validation mixin (fail-fast is in MixinFailFast)

These are retained in the metadata for forward compatibility and code generation planning.
