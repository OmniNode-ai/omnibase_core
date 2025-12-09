# ONEX Contracts

This directory contains YAML contract definitions for ONEX nodes.

## Directory Structure

```text
contracts/
└── runtime/           # Runtime orchestrator contracts (self-hosted ONEX)
    ├── runtime_orchestrator.yaml      # Main orchestrator
    ├── contract_loader_effect.yaml    # FS scanner for contracts
    ├── contract_registry_reducer.yaml # Contract registry FSM
    ├── node_graph_reducer.yaml        # Node graph lifecycle FSM
    └── event_bus_wiring_effect.yaml   # Event bus subscription wiring
```

## Contract Types

| Type | Node Type | Purpose |
|------|-----------|---------|
| Orchestrator | `ORCHESTRATOR_GENERIC` | Workflow coordination |
| Reducer | `REDUCER_GENERIC` | FSM-driven state management |
| Effect | `EFFECT_GENERIC` | External I/O operations |
| Compute | `COMPUTE_GENERIC` | Data transformation pipelines |

## Validation

Contracts are validated using `MinimalYamlContract` from:
- `scripts/validation/yaml_contract_validator.py`

Required fields:
- `node_type`: One of the valid EnumNodeType values
- `contract_version`: Semantic version `{major, minor, patch}`

## Action Execution Model

Actions execute in a defined order during FSM state transitions:

### Execution Order

1. **exit_actions** of source state (cleanup before leaving)
2. **transition actions** (from the transition definition)
3. **entry_actions** of target state (initialization after arriving)

Example from `node_graph_reducer.yaml`:
```text
initializing -> wiring transition:
  1. exit_actions: [log_initialization_complete]     # From initializing state
  2. actions: [emit_wiring_started, snapshot_registry_state]  # From transition
  3. entry_actions: [resolve_node_dependencies, ...]  # From wiring state
```

### Action Properties

| Property | Type | Description |
|----------|------|-------------|
| `action_name` | string | Unique identifier for the action |
| `action_type` | enum | Category of action (see below) |
| `is_critical` | bool | If `true`, failure aborts the transition and triggers rollback |
| `timeout_ms` | int | Maximum execution time in milliseconds |
| `version` | object | Semantic version for action compatibility |

### Action Types

| Type | Description | Example |
|------|-------------|---------|
| `event` | Emit events to the event bus | `emit_graph_running` |
| `logging` | Write to logs for observability | `log_shutdown_request` |
| `persistence` | Save state to durable storage | `persist_final_state` |
| `data_capture` | Capture diagnostic/snapshot data | `snapshot_registry_state` |
| `alert` | Send alerts for critical conditions | `emit_fatal_error_alert` |
| `cleanup` | Release resources and cleanup state | `emergency_resource_cleanup` |

### Error Handling

**Critical Actions** (`is_critical: true`):
- Failure aborts the entire transition
- Source state is preserved (no partial transitions)
- Rollback actions execute if defined
- Error propagates to orchestrator for handling

**Non-Critical Actions** (`is_critical: false`):
- Failure is logged but does not abort the transition
- Subsequent actions continue executing
- Transition completes to target state
- Error is recorded for observability

**Timeout Handling**:
- Actions exceeding `timeout_ms` are terminated
- Timeout counts as failure (respects `is_critical` flag)
- Recommended timeouts: events (1000ms), logging (500ms), persistence (5000ms)

### Idempotency Requirements

Actions in terminal states (e.g., `stopped`) MUST be idempotent because:
- Wildcard transitions (`from_state: '*'`) can reach terminal states from any state
- Multiple error paths may trigger the same entry_actions
- Recovery scenarios may re-enter terminal states

See `node_graph_reducer.yaml` for idempotency documentation patterns.

## Integration Testing

Integration tests for runtime contracts should cover the complete lifecycle:

| Test Scenario | Description | Key Assertions |
|--------------|-------------|----------------|
| **Happy Path Startup** | contract_loader → registry → node_graph → wiring → ready | All FSMs reach target states, `runtime.ready` event emitted |
| **Contract Validation Failure** | Invalid contract in contracts/ directory | Registry enters `error` state, error event emitted |
| **Graceful Shutdown** | `shutdown_requested` during `running` state | Drain completes, all resources released, `graph.stopped` emitted |
| **Fatal Error Recovery** | Inject fatal_error from each non-terminal state | Idempotent cleanup, consistent `stopped` state |
| **Hot Reload** | Add/modify contract during `running` state | Registry reloads, graph rewires without restart |

Test implementation pattern:
```python
@pytest.mark.integration
async def test_runtime_lifecycle_happy_path():
    orchestrator = RuntimeOrchestrator(contracts_dir="./test_contracts")
    await orchestrator.start()
    assert orchestrator.state == "running"
    await orchestrator.shutdown(graceful=True)
    assert orchestrator.state == "stopped"
```

## Performance Benchmarks

Target benchmarks for runtime operations:

| Operation | Target | Measurement Point |
|-----------|--------|-------------------|
| Contract scan (100 files) | < 500ms | `contract_loader.scan` completion |
| Contract validation (per file) | < 10ms | `contract_registry.validate` |
| Node wiring (50 nodes) | < 2s | `node_graph.wiring` → `running` |
| Event bus subscription | < 100ms | `event_bus_wiring` per subscription |
| Graceful shutdown (idle) | < 1s | `shutdown_requested` → `stopped` |
| Graceful shutdown (draining) | < 30s | Respects `drain_timeout_ms` |

Benchmark tooling:
```bash
# Run performance benchmarks
poetry run pytest tests/integration/benchmarks/ -v --benchmark-only
```

## Operational Monitoring

### Key Metrics

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| `onex.runtime.state` | FSM current state | Any error state > 1m |
| `onex.runtime.startup_duration_ms` | Startup timing | > 10s |
| `onex.contracts.loaded_count` | Registry | 0 (no contracts) |
| `onex.contracts.validation_errors` | Registry | > 0 |
| `onex.wiring.subscription_failures` | Event bus wiring | > 5 in 1m |
| `onex.circuit_breaker.open` | All effect nodes | Any open > 30s |

### Health Checks

All nodes expose health checks via `health_check` configuration:

```bash
# Check runtime health
curl http://localhost:8080/health/runtime

# Expected response when healthy
{"status": "healthy", "checks": {"registry": "ready", "graph": "running", "wiring": "complete"}}
```

### Event Topics for Monitoring

Subscribe to these topics for operational visibility:

| Topic | Purpose |
|-------|---------|
| `onex.runtime.ready` | Runtime fully initialized |
| `onex.runtime.error` | Runtime-level errors |
| `onex.runtime.state_changed` | FSM state transitions |
| `onex.contracts.loaded` | Contract discovery events |
| `onex.contracts.validation_failed` | Contract validation errors |

## Reference

See [OMN-467](https://linear.app/omninode/issue/OMN-467) for the runtime orchestrator implementation.
