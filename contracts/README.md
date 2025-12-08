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

## Reference

See [OMN-467](https://linear.app/omninode/issue/OMN-467) for the runtime orchestrator implementation.
