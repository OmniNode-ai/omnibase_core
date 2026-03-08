# Mixin-to-Capability Migration Plan

**Ticket**: OMN-1115
**Status**: Inventory Complete, Migration Planning Ready
**Last Updated**: 2026-03-08

## Overview

This document describes the strategy for migrating from class-based mixins to contract-driven capability handlers. The migration preserves all existing behavior while transitioning to the ONEX handler architecture.

## Migration Model

Each mixin maps to a handler conversion target via `ModelMixinMapping`:

```python
class ModelMixinMapping(BaseModel):
    mixin_name: str                                    # e.g., "MixinMetrics"
    handler_contract_stub: str                         # path to generated contract YAML
    handler_type_category: EnumHandlerTypeCategory     # compute | effect | nondeterministic_compute
    capability_set: list[str]                          # capability identifiers
    nondeterminism_classification: EnumNondeterminismClass  # deterministic | time | random | network | external_state
    legacy_shim_required: bool = True                  # True until proven otherwise
    conversion_evidence: str | None = None             # Required when legacy_shim_required=False
```

## Nondeterminism Classification

The `EnumNondeterminismClass` categorizes the source of nondeterminism:

| Class | Description | Handler Type | Example Mixins |
|-------|-------------|-------------|----------------|
| `deterministic` | Same input always produces same output | COMPUTE | MixinHashComputation, MixinSerializable |
| `time` | Uses time-dependent operations | NONDETERMINISTIC_COMPUTE | MixinCaching |
| `random` | Uses random/UUID generation | NONDETERMINISTIC_COMPUTE | (none currently) |
| `network` | Performs network I/O | EFFECT | MixinEventBus, MixinEffectExecution |
| `external_state` | Reads env vars, config, filesystem | NONDETERMINISTIC_COMPUTE | MixinContractMetadata, MixinDiscovery |

## Migration Phases

### Phase 1: Pure Compute (13 mixins)

Deterministic mixins with no I/O or external state. Safest to migrate first.

| Mixin | Priority | Capabilities |
|-------|----------|-------------|
| MixinHashComputation | 1 | hash_computation, integrity_verification |
| MixinCanonicalYAMLSerializer | 1 | serialization, canonical_output |
| MixinSerializable | 1 | serialization, deserialization |
| MixinYAMLSerialization | 1 | serialization, yaml_output |
| MixinTruncationValidation | 1 | validation, truncation_checking |
| MixinNodeTypeValidator | 1 | validation, node_type_mapping |
| MixinSensitiveFieldRedaction | 2 | security, field_redaction |
| MixinLazyValue | 2 | lazy_evaluation, caching |
| MixinLazyEvaluation | 2 | lazy_evaluation, performance_optimization |
| MixinFailFast | 2 | error_handling, validation, fail_fast |
| MixinComputeExecution | 2 | compute_pipeline, contract_driven_execution |
| MixinHandlerRouting | 2 | routing, handler_dispatch |
| MixinMetrics | 3 | metrics, observability |

### Phase 2: Stateful / Nondeterministic (10 mixins)

Mixins that read external state (config files, env vars) but do not perform I/O.

| Mixin | Priority | Dependencies |
|-------|----------|-------------|
| MixinCaching | 2 | (none) |
| MixinFSMExecution | 2 | (none) |
| MixinContractStateReducer | 2 | MixinFSMExecution |
| MixinContractMetadata | 3 | (none) |
| MixinNodeSetup | 3 | MixinContractMetadata |
| MixinNodeIdFromContract | 3 | MixinContractMetadata |
| MixinIntrospectFromContract | 3 | MixinContractMetadata |
| MixinNodeIntrospection | 3 | (none) |
| MixinDiscovery | 3 | (none) |
| MixinCLIHandler | 4 | MixinContractMetadata, MixinFailFast |

### Phase 3: I/O and Effects (7 mixins)

Mixins that perform network I/O or interact with external systems.

| Mixin | Priority | Dependencies |
|-------|----------|-------------|
| MixinEventBus | 1 | (none) |
| MixinEffectExecution | 1 | MixinEventBus |
| MixinHealthCheck | 2 | (none) |
| MixinContractPublisher | 2 | MixinEventBus |
| MixinIntentPublisher | 2 | MixinEventBus |
| MixinIntrospectionPublisher | 2 | MixinEventBus, MixinNodeIntrospection |
| MixinDebugDiscoveryLogging | 4 | (none) |

### Phase 4: Orchestration and Lifecycle (10 mixins)

Complex mixins that compose other mixins and manage node lifecycle.

| Mixin | Priority | Dependencies |
|-------|----------|-------------|
| MixinNodeLifecycle | 1 | MixinEventBus, MixinIntrospectionPublisher |
| MixinEventHandler | 1 | MixinEventBus |
| MixinEventDrivenNode | 1 | MixinIntrospectionPublisher, MixinEventHandler, MixinNodeLifecycle |
| MixinNodeExecutor | 1 | MixinEventDrivenNode |
| MixinNodeService | 1 | MixinNodeExecutor, MixinEventDrivenNode |
| MixinDiscoveryResponder | 2 | MixinEventBus |
| MixinRequestResponseIntrospection | 2 | MixinEventBus, MixinNodeIntrospection |
| MixinServiceRegistry | 2 | MixinEventBus |
| MixinToolExecution | 2 | MixinEventBus |
| MixinWorkflowExecution | 2 | MixinEventBus, MixinFSMExecution |

## Conversion Evidence Rules

Setting `legacy_shim_required = False` requires documented evidence:

| Format | Meaning | Example |
|--------|---------|---------|
| `test:<test_name>` | Test proves determinism | `test:test_metrics_pure` |
| `rule:<rule_name>` | Static analysis rule passed | `rule:pure_function` |
| `audit:YYYY-MM-DD` | Manual audit with date | `audit:2026-03-15` |

Without evidence, `legacy_shim_required` stays `True`.

## Dependency Graph

Run the dependency graph script to visualize and validate:

```bash
# Text output with migration order
python scripts/mixin_dependency_graph.py

# DOT format for Graphviz visualization
python scripts/mixin_dependency_graph.py --format dot > mixins.dot
dot -Tpng mixins.dot -o mixins.png

# Validate no circular dependencies
python scripts/mixin_dependency_graph.py --validate-only
```

## Mapping Artifact

The canonical mapping lives at `src/omnibase_core/mixins/mixin_capability_mapping.yaml` and is validated by `ModelMixinMapping` / `ModelMixinMappingCollection` Pydantic models.

## Related Documents

- [MIXIN_INVENTORY.md](MIXIN_INVENTORY.md) -- Complete inventory of all 40 mixins
- [MIXIN_SUBCONTRACT_MAPPING.md](../guides/MIXIN_SUBCONTRACT_MAPPING.md) -- Mixin-to-subcontract relationships
- [MIXIN_DISCOVERY_API.md](../reference/MIXIN_DISCOVERY_API.md) -- Runtime discovery API
