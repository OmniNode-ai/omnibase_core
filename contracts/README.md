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
```
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

## Reference

See [OMN-467](https://linear.app/omninode/issue/OMN-467) for the runtime orchestrator implementation.
