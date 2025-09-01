# ONEX Mixin Subcontracts

This directory contains mixin subcontracts that define reusable cross-cutting concerns for ONEX nodes. Mixins promote DRY principles and enforce architectural constraints.

## Core Mixins (Universal)
These mixins can be applied to any node type:

- **`mixin_health_check.yaml`** - Health monitoring and status reporting
- **`mixin_introspection.yaml`** - Node discovery and capability reporting
- **`mixin_event_handling.yaml`** - Event bus integration patterns
- **`mixin_service_resolution.yaml`** - Service discovery and dependency injection
- **`mixin_performance_monitoring.yaml`** - Metrics collection and performance tracking
- **`mixin_request_response.yaml`** - Standard request/response interaction patterns

## Specialized Mixins (Node-Type Specific)
These mixins are restricted to specific node types:

- **`mixin_state_management.yaml`** - State persistence and management (REDUCER only)
- **`mixin_external_dependencies.yaml`** - External service integrations (EFFECT only)
- **`mixin_workflow_coordination.yaml`** - Workflow orchestration patterns (ORCHESTRATOR only)

## Architectural Constraints

### COMPUTE Nodes
- ✅ Can use: Core mixins only
- ❌ Cannot use: state_management, external_dependencies, workflow_coordination

### EFFECT Nodes  
- ✅ Can use: Core mixins + external_dependencies
- ❌ Cannot use: state_management, workflow_coordination

### REDUCER Nodes
- ✅ Can use: Core mixins + state_management
- ❌ Cannot use: external_dependencies, workflow_coordination

### ORCHESTRATOR Nodes
- ✅ Can use: Core mixins + workflow_coordination
- ❌ Cannot use: state_management, external_dependencies

## Usage in Contracts

```yaml
# Example: canary_compute/v1_0_0/contract.yaml
node_type: "COMPUTE"
main_tool_class: "NodeCanaryCompute"

# Core compute functionality
algorithm: { ... }

# Applied mixins (validated against node type)
mixins:
  - mixin_health_check
  - mixin_introspection
  - mixin_event_handling
  - mixin_request_response
```

## Validation

The contract validation system will:
1. Load and validate each mixin subcontract
2. Enforce architectural constraints (prevent invalid mixin combinations)
3. Merge mixin definitions into the main contract for validation
4. Report mixin-specific validation errors clearly
