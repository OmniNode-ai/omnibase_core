# Registration FSM Contract v1.0.0

> **Version**: 1.0.0
> **Ticket**: OMN-938
> **Related**: OMN-889 (Dual Registration Reducer), OMN-912 (Registration Intents), OMN-913 (Registration Payloads)
> **Status**: Specification
> **Last Updated**: 2025-12-19

## Overview

This document defines the formal Finite State Machine (FSM) contract for the **Dual Registration Reducer** (OMN-889). The Registration FSM manages the lifecycle of ONEX node registration to both Consul (service discovery) and PostgreSQL (source of truth).

### Purpose

The Registration FSM provides:
- **Deterministic state transitions** for node registration lifecycle
- **Pure FSM semantics** following the ONEX Reducer pattern: `delta(state, event) -> (new_state, intents[])`
- **Dual registration coordination** for Consul and PostgreSQL
- **Failure recovery** with partial registration handling
- **Graceful deregistration** with cleanup

### Workflow Pattern

```text
IntrospectionEvent -> Reducer (emits intents) -> Effects (execute) -> Orchestrator (aggregate)
```

The Reducer is **pure** - it describes what should happen via Intent emission without performing I/O.

### Dual Registration Order

The FSM enforces a specific registration order:

1. **PostgreSQL First** (source of truth): The node is registered in PostgreSQL first because it serves as the authoritative source of truth for node state. If PostgreSQL registration fails, no Consul registration is attempted.

2. **Consul Second** (service discovery): After PostgreSQL succeeds, the node is registered in Consul for service discovery. If Consul fails after PostgreSQL succeeds, the FSM enters `partial_registered` state, allowing targeted retry of just the Consul component.

This ordering ensures that:
- The database always has an accurate record before the node becomes discoverable
- Partial failures can be recovered with targeted retries
- Service discovery only advertises nodes that are properly tracked in the database

---

## Table of Contents

1. [States](#states)
2. [Transitions](#transitions)
3. [Guards](#guards)
4. [State Diagram](#state-diagram)
5. [Intent Emission](#intent-emission)
6. [Validation Rules](#validation-rules)
7. [Implementation Notes](#implementation-notes)
8. [Error Handling](#error-handling)
9. [Related Documentation](#related-documentation)

---

## States

The Registration FSM defines 10 states across 6 state types.

### State Type Terminology

> **Important Distinction**: This FSM distinguishes between **success states** and **terminal states**:
>
> - **Success State** (`state_type: success`): A stable state indicating successful completion of the primary workflow goal. Success states may have outgoing transitions for graceful lifecycle management (e.g., shutdown). Example: `registered` allows `DEREGISTER` transition.
>
> - **Terminal State** (`state_type: terminal`): A final state with no outgoing transitions. Once entered, the FSM cannot leave this state. Example: `deregistered` has no outgoing transitions.
>
> The `is_terminal` field indicates whether a state has outgoing transitions (`false`) or not (`true`). A success state can have `is_terminal: false` if it allows graceful shutdown transitions.

### State Definitions

| State Name | Type | Terminal? | Recoverable? | Description |
|------------|------|-----------|--------------|-------------|
| `unregistered` | initial | No | Yes | Node has not initiated registration. Initial state before any registration attempt. |
| `validating` | operational | No | Yes | Validating registration payload. Checking node metadata, Consul config, and PostgreSQL record. |
| `registering_postgres` | operational | No | Yes | Emitting PostgreSQL upsert intent. First phase of dual registration. |
| `postgres_registered` | snapshot | No | Yes | PostgreSQL registration succeeded. Awaiting Consul registration. |
| `registering_consul` | operational | No | Yes | Emitting Consul register intent. Second phase of dual registration. |
| `registered` | success | No | No | Fully registered in both Consul and PostgreSQL. Success state allowing graceful shutdown. |
| `partial_registered` | error | No | Yes | Partial registration - one succeeded, one failed. Requires recovery. |
| `deregistering` | operational | No | Yes | Emitting deregistration intents for graceful shutdown. |
| `deregistered` | terminal | Yes | No | Fully deregistered from both systems. Terminal state. |
| `failed` | error | No | Yes | Registration failed completely because either both registration attempts failed or a validation error occurred. This state allows retry via the `RETRY` trigger. |

### State Details

#### `unregistered` (Initial State)

```yaml
state_name: unregistered
state_type: initial
description: "Node has not initiated registration. Awaiting introspection event."
is_terminal: false
is_recoverable: true
entry_actions: []
exit_actions:
  - "log_registration_start"
required_data: []
optional_data:
  - node_id
  - deployment_id
validation_rules: []
```

**Purpose**: Starting point for all registration workflows. Nodes enter this state on initial boot or after complete deregistration.

---

#### `validating` (Operational State)

```yaml
state_name: validating
state_type: operational
description: "Validating registration payload before initiating registration."
is_terminal: false
is_recoverable: true
timeout_ms: 5000
entry_actions:
  - "validate_payload"
exit_actions: []
required_data:
  - node_id
  - deployment_id
  - environment
  - network_id
  - consul_service_id
  - consul_service_name
  - postgres_record
optional_data:
  - consul_tags
  - consul_health_check
validation_rules:
  - "node_id != null"
  - "deployment_id != null"
  - "consul_service_id.length >= 1"
  - "consul_service_name.length >= 1"
```

**Purpose**: This state validates the `ModelRegistrationPayload` before proceeding with registration. Validation catches configuration errors early, ensuring that required fields are present and correctly formatted before attempting any external registrations.

---

#### `registering_postgres` (Operational State)

```yaml
state_name: registering_postgres
state_type: operational
description: "Emitting PostgreSQL upsert registration intent."
is_terminal: false
is_recoverable: true
timeout_ms: 10000
entry_actions:
  - "emit_postgres_upsert_intent"
exit_actions: []
required_data:
  - postgres_record
optional_data: []
validation_rules:
  - "postgres_record != null"
```

**Purpose**: Emits `ModelPostgresUpsertRegistrationIntent` for Effect node execution. PostgreSQL is registered first as the source of truth.

---

#### `postgres_registered` (Snapshot State)

```yaml
state_name: postgres_registered
state_type: snapshot
description: "PostgreSQL registration succeeded. Proceeding to Consul registration."
is_terminal: false
is_recoverable: true
entry_actions:
  - "log_postgres_success"
exit_actions: []
required_data:
  - postgres_applied
optional_data: []
validation_rules:
  - "postgres_applied == true"
```

**Purpose**: This is an intermediate checkpoint state that confirms PostgreSQL registration succeeded before proceeding to Consul. The checkpoint enables partial recovery if Consul registration subsequently fails, as the FSM knows that PostgreSQL was successfully registered and can retry only the Consul component.

---

#### `registering_consul` (Operational State)

```yaml
state_name: registering_consul
state_type: operational
description: "Emitting Consul register intent for service discovery."
is_terminal: false
is_recoverable: true
timeout_ms: 10000
entry_actions:
  - "emit_consul_register_intent"
exit_actions: []
required_data:
  - consul_service_id
  - consul_service_name
optional_data:
  - consul_tags
  - consul_health_check
validation_rules:
  - "consul_service_id.length >= 1"
  - "consul_service_name.length >= 1"
```

**Purpose**: Emits `ModelConsulRegisterIntent` for Effect node execution. Consul is registered second for service discovery.

---

#### `registered` (Success State)

```yaml
state_name: registered
state_type: success
description: "Fully registered in both Consul and PostgreSQL."
is_terminal: false
is_recoverable: false
entry_actions:
  - "log_registration_complete"
  - "emit_registration_success_metric"
exit_actions: []
required_data:
  - postgres_applied
  - consul_applied
optional_data: []
validation_rules:
  - "postgres_applied == true"
  - "consul_applied == true"
```

**Purpose**: Success state. Node is fully discoverable and registered. Allows transition to `deregistering` for graceful shutdown via `DEREGISTER` trigger.

> **Clarification**: The `registered` state is a **success state**, not a terminal state. It has `state_type: success` and `is_terminal: false` because it allows one outgoing transition (`DEREGISTER`) for graceful shutdown. This distinguishes it from the `deregistered` state, which is the true **terminal state** with `state_type: terminal` and `is_terminal: true` (no outgoing transitions). See [State Type Terminology](#state-type-terminology) for the full distinction.

---

#### `partial_registered` (Error State)

```yaml
state_name: partial_registered
state_type: error
description: "Partial registration - one system succeeded, one failed."
is_terminal: false
is_recoverable: true
entry_actions:
  - "log_partial_failure"
  - "emit_partial_registration_metric"
exit_actions: []
required_data:
  - postgres_applied
  - consul_applied
optional_data:
  - postgres_error
  - consul_error
validation_rules:
  - "postgres_applied != consul_applied"  # XOR condition
```

**Purpose**: This is a recoverable error state indicating that exactly one registration succeeded while the other failed. The state enables targeted retry of only the failed component, avoiding redundant re-registration of the already-successful component. From this state, use `RETRY` to retry Consul (if PostgreSQL succeeded) or `RETRY_POSTGRES` to retry PostgreSQL (if Consul succeeded).

---

#### `deregistering` (Operational State)

```yaml
state_name: deregistering
state_type: operational
description: "Emitting deregistration intents for graceful shutdown."
is_terminal: false
is_recoverable: true
timeout_ms: 15000
entry_actions:
  - "emit_consul_deregister_intent"
  - "emit_postgres_deregister_intent"
exit_actions: []
required_data:
  - node_id
  - consul_service_id
optional_data: []
validation_rules: []
```

**Purpose**: This is the graceful shutdown phase where deregistration intents are emitted for both Consul and PostgreSQL. The FSM cleans up both systems in parallel, with the Orchestrator aggregating both deregistration outcomes before transitioning to the terminal `deregistered` state.

**Note**: The `emit_consul_deregister_intent` and `emit_postgres_deregister_intent` entry actions are emitted in parallel. The Orchestrator aggregates both deregistration outcomes before transitioning to `deregistered`.

---

#### `deregistered` (Terminal State)

```yaml
state_name: deregistered
state_type: terminal
description: "Fully deregistered from both systems."
is_terminal: true
is_recoverable: false
entry_actions:
  - "log_deregistration_complete"
  - "emit_deregistration_metric"
exit_actions: []
required_data: []
optional_data: []
validation_rules: []
```

**Purpose**: This is the terminal state of the FSM, indicating that the node has been completely removed from both service discovery (Consul) and the database (PostgreSQL). Once the FSM reaches this state, no further transitions are possible, and the registration lifecycle is complete.

> **Clarification**: The `deregistered` state is the **only true terminal state** in this FSM. It has `state_type: terminal` and `is_terminal: true`, meaning there are no outgoing transitions. Once the FSM reaches this state, the registration lifecycle is complete. This contrasts with `registered`, which is a success state that still allows graceful shutdown via `DEREGISTER`. See [State Type Terminology](#state-type-terminology) for the full distinction.

---

#### `failed` (Error State)

```yaml
state_name: failed
state_type: error
description: "Registration failed completely. Either both registration attempts failed, or a validation error occurred."
is_terminal: false
is_recoverable: true
entry_actions:
  - "log_failure"
  - "emit_failure_metric"
exit_actions: []
required_data: []
optional_data:
  - postgres_error
  - consul_error
  - validation_error
validation_rules: []
```

**Purpose**: This is the complete failure state for the registration workflow, entered when either validation fails, PostgreSQL registration fails (before Consul is attempted), or both registrations fail. Unlike `partial_registered`, this state indicates no successful registrations exist. The registration workflow can be retried from the beginning via the `RETRY` trigger (subject to the `retry_count < 3` guard), or the registration can be abandoned entirely via the `ABANDON` trigger.

---

## Transitions

The Registration FSM defines 17 transitions:

### Transition Table

| # | Transition Name | From State | To State | Trigger | Priority | Description |
|---|-----------------|------------|----------|---------|----------|-------------|
| 1 | `start_registration` | `unregistered` | `validating` | `REGISTER` | 10 | Initiate registration workflow |
| 2 | `validation_success` | `validating` | `registering_postgres` | `VALIDATION_PASSED` | 10 | Payload validated successfully |
| 3 | `validation_failure` | `validating` | `failed` | `VALIDATION_FAILED` | 10 | Payload validation failed |
| 4 | `postgres_success` | `registering_postgres` | `postgres_registered` | `POSTGRES_SUCCEEDED` | 10 | PostgreSQL upsert succeeded |
| 5 | `postgres_failure` | `registering_postgres` | `failed` | `POSTGRES_FAILED` | 10 | PostgreSQL upsert failed |
| 6 | `start_consul_registration` | `postgres_registered` | `registering_consul` | `CONTINUE` | 10 | Proceed to Consul registration |
| 7 | `consul_success` | `registering_consul` | `registered` | `CONSUL_SUCCEEDED` | 10 | Consul registration succeeded |
| 8 | `consul_failure` | `registering_consul` | `partial_registered` | `CONSUL_FAILED` | 10 | Consul failed after Postgres succeeded |
| 9 | `retry_consul` | `partial_registered` | `registering_consul` | `RETRY` | 10 | Retry Consul registration |
| 10 | `retry_postgres` | `partial_registered` | `registering_postgres` | `RETRY_POSTGRES` | 10 | Retry PostgreSQL registration |
| 11 | `partial_recovery_success` | `partial_registered` | `registered` | `RECOVERY_COMPLETE` | 10 | Both registrations now complete |
| 12 | `initiate_deregistration` | `registered` | `deregistering` | `DEREGISTER` | 10 | Start graceful shutdown |
| 13 | `deregistration_complete` | `deregistering` | `deregistered` | `DEREGISTRATION_COMPLETE` | 10 | Deregistration succeeded |
| 14 | `retry_from_failed` | `failed` | `validating` | `RETRY` | 10 | Retry full registration workflow |
| 15 | `abandon_registration` | `failed` | `deregistered` | `ABANDON` | 5 | Abandon failed registration |
| 16 | `global_error_handler` | `*` | `failed` | `FATAL_ERROR` | 0 | Handle unrecoverable errors from any state |
| 17 | `retry_exhausted` | `partial_registered` | `failed` | `RETRY_EXHAUSTED` | 10 | Retry limit reached in partial_registered |

### Transition Details

#### Transition 1: `start_registration`

```yaml
transition_name: start_registration
from_state: unregistered
to_state: validating
trigger: REGISTER
priority: 10
is_atomic: true
conditions:
  - condition_name: has_registration_payload
    condition_type: expression
    expression: "payload exists true"
    required: true
actions:
  - action_name: log_registration_initiated
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Registration workflow initiated"
```

**Trigger**: `IntrospectionEvent` with registration payload received.

---

#### Transition 2: `validation_success`

```yaml
transition_name: validation_success
from_state: validating
to_state: registering_postgres
trigger: VALIDATION_PASSED
priority: 10
is_atomic: true
conditions:
  - condition_name: payload_valid
    condition_type: expression
    expression: "validation_result == passed"
    required: true
actions:
  - action_name: log_validation_passed
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Payload validation passed"
```

---

#### Transition 3: `validation_failure`

```yaml
transition_name: validation_failure
from_state: validating
to_state: failed
trigger: VALIDATION_FAILED
priority: 10
is_atomic: true
conditions:
  - condition_name: payload_invalid
    condition_type: expression
    expression: "validation_result == failed"
    required: true
actions:
  - action_name: log_validation_failed
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: ERROR
      message: "Payload validation failed"
```

---

#### Transition 4: `postgres_success`

```yaml
transition_name: postgres_success
from_state: registering_postgres
to_state: postgres_registered
trigger: POSTGRES_SUCCEEDED
priority: 10
is_atomic: true
conditions:
  - condition_name: postgres_applied
    condition_type: expression
    expression: "postgres_applied == true"
    required: true
actions:
  - action_name: record_postgres_success
    action_type: emit_intent
    action_config:
      intent_type: log_metric
      metric: registration_postgres_success
      value: 1
```

---

#### Transition 5: `postgres_failure`

```yaml
transition_name: postgres_failure
from_state: registering_postgres
to_state: failed
trigger: POSTGRES_FAILED
priority: 10
is_atomic: true
conditions:
  - condition_name: postgres_error
    condition_type: expression
    expression: "postgres_applied == false"
    required: true
actions:
  - action_name: record_postgres_failure
    action_type: emit_intent
    action_config:
      intent_type: log_metric
      metric: registration_postgres_failure
      value: 1
```

---

#### Transition 6: `start_consul_registration`

```yaml
transition_name: start_consul_registration
from_state: postgres_registered
to_state: registering_consul
trigger: CONTINUE
priority: 10
is_atomic: true
conditions: []
actions:
  - action_name: log_consul_start
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Starting Consul registration"
```

**CONTINUE Trigger Semantics**: The `CONTINUE` trigger enables automatic state progression without requiring an external event. Unlike external triggers (e.g., `REGISTER`, `DEREGISTER`) or Effect-sourced triggers (e.g., `POSTGRES_SUCCEEDED`), `CONTINUE` is a **synthetic internal trigger** that the Reducer emits to itself.

**Implementation Pattern**:

1. **When Emitted**: The Reducer emits `CONTINUE` synchronously as part of processing the `POSTGRES_SUCCEEDED` trigger. After transitioning to `postgres_registered`, the Reducer immediately evaluates if `CONTINUE` should fire.

2. **Not an External Event**: `CONTINUE` is never received from the event bus, Effect nodes, or external sources. It exists solely as an internal FSM mechanism for automatic progression.

3. **Single-Step vs Two-Step Execution**: Implementations may choose between:
   - **Single-step** (recommended): Process `POSTGRES_SUCCEEDED`, transition to `postgres_registered`, then immediately process `CONTINUE` and transition to `registering_consul` in one `delta()` call. This approach returns `registering_consul` as the final state with Consul registration intents.
   - **Two-step**: Return from `delta()` at `postgres_registered`, then have the runtime invoke `delta()` again with `CONTINUE`. This approach makes the checkpoint state observable but adds latency.

4. **Implementation Example** (single-step pattern):
   ```python
   async def delta(
       self, state: str, trigger: str, context: ModelFSMContext
   ) -> tuple[str, list[ModelIntent]]:
       if state == "registering_postgres" and trigger == "POSTGRES_SUCCEEDED":
           # Transition through postgres_registered checkpoint, then immediately
           # process CONTINUE to reach registering_consul (single-step pattern)
           return "registering_consul", [
               ModelLogIntent(kind="log_event", level="INFO",
                   message="PostgreSQL succeeded, proceeding to Consul"),
               ModelConsulRegisterIntent(
                   kind="consul.register",
                   service_id=context.consul_service_id,
                   correlation_id=context.correlation_id,
               )
           ]
   ```

5. **Why Use CONTINUE**: The `postgres_registered` state exists as a **checkpoint for observability and recovery**. If Consul registration fails, the FSM knows PostgreSQL succeeded (enabling targeted retry). The `CONTINUE` mechanism allows this checkpoint state to exist in the state diagram while enabling automatic progression in the happy path. Without `CONTINUE`, the FSM would require an explicit external trigger to proceed from `postgres_registered` to `registering_consul`.

6. **Observability Note**: Even with single-step execution, implementations should log the transition through `postgres_registered` for debugging and audit purposes. The checkpoint state is logically traversed even if not externally observable as a pause point.

7. **Error Handling**: If CONTINUE trigger processing fails (e.g., intent emission error during transition to `registering_consul`), the FSM should transition to `failed` state via `FATAL_ERROR`. Since CONTINUE is an internal mechanism with no external event to retry, failure during CONTINUE processing indicates a system-level issue that requires investigation. The Orchestrator should log the failure with full context including the `postgres_registered` checkpoint state.

---

#### Transition 7: `consul_success`

```yaml
transition_name: consul_success
from_state: registering_consul
to_state: registered
trigger: CONSUL_SUCCEEDED
priority: 10
is_atomic: true
conditions:
  - condition_name: consul_applied
    condition_type: expression
    expression: "consul_applied == true"
    required: true
actions:
  - action_name: record_registration_complete
    action_type: emit_intent
    action_config:
      intent_type: log_metric
      metric: registration_complete
      value: 1
```

---

#### Transition 8: `consul_failure`

```yaml
transition_name: consul_failure
from_state: registering_consul
to_state: partial_registered
trigger: CONSUL_FAILED
priority: 10
is_atomic: true
conditions:
  - condition_name: consul_error
    condition_type: expression
    expression: "consul_applied == false"
    required: true
actions:
  - action_name: record_partial_registration
    action_type: emit_intent
    action_config:
      intent_type: log_metric
      metric: registration_partial
      value: 1
```

---

#### Transition 9: `retry_consul`

```yaml
transition_name: retry_consul
from_state: partial_registered
to_state: registering_consul
trigger: RETRY
priority: 10
is_atomic: true
conditions:
  - condition_name: consul_failed_postgres_ok
    condition_type: expression
    expression: "postgres_applied == true"
    required: true
  - condition_name: retry_count_valid
    condition_type: expression
    expression: "retry_count < 3"
    required: true
actions:
  - action_name: increment_retry_count
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Retrying Consul registration"
```

**Guard Cross-Reference**: The `retry_count < 3` guard enforces the retry limit (maximum 3 attempts). See [Retry Limit Enforcement](#retry-limit-enforcement) for detailed enforcement behavior, counter increment semantics, reset events, and exhaustion handling.

---

#### Transition 10: `retry_postgres`

```yaml
transition_name: retry_postgres
from_state: partial_registered
to_state: registering_postgres
trigger: RETRY_POSTGRES
priority: 10
is_atomic: true
conditions:
  - condition_name: postgres_failed_consul_ok
    condition_type: expression
    expression: "consul_applied == true"
    required: true
  - condition_name: retry_count_valid
    condition_type: expression
    expression: "retry_count < 3"
    required: true
actions:
  - action_name: increment_retry_count
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Retrying PostgreSQL registration"
```

**Guard Cross-Reference**: The `retry_count < 3` guard enforces the retry limit (maximum 3 attempts). See [Retry Limit Enforcement](#retry-limit-enforcement) for detailed enforcement behavior, counter increment semantics, reset events, and exhaustion handling.

---

#### Transition 11: `partial_recovery_success`

```yaml
transition_name: partial_recovery_success
from_state: partial_registered
to_state: registered
trigger: RECOVERY_COMPLETE
priority: 10
is_atomic: true
conditions:
  - condition_name: both_applied
    condition_type: expression
    expression: "postgres_applied == true"
    required: true
  - condition_name: consul_now_applied
    condition_type: expression
    expression: "consul_applied == true"
    required: true
actions:
  - action_name: record_recovery_success
    action_type: emit_intent
    action_config:
      intent_type: log_metric
      metric: registration_recovery_success
      value: 1
```

---

#### Transition 12: `initiate_deregistration`

```yaml
transition_name: initiate_deregistration
from_state: registered
to_state: deregistering
trigger: DEREGISTER
priority: 10
is_atomic: true
conditions: []
actions:
  - action_name: log_deregistration_start
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Starting graceful deregistration"
```

**Note**: This is the ONLY valid outgoing transition from `registered` state, requiring an explicit `DEREGISTER` trigger. The `registered` state is a success state that allows graceful shutdown when needed.

---

#### Transition 13: `deregistration_complete`

```yaml
transition_name: deregistration_complete
from_state: deregistering
to_state: deregistered
trigger: DEREGISTRATION_COMPLETE
priority: 10
is_atomic: true
conditions: []
actions:
  - action_name: record_deregistration_complete
    action_type: emit_intent
    action_config:
      intent_type: log_metric
      metric: deregistration_complete
      value: 1
```

---

#### Transition 14: `retry_from_failed`

```yaml
transition_name: retry_from_failed
from_state: failed
to_state: validating
trigger: RETRY
priority: 10
is_atomic: true
conditions:
  - condition_name: retry_count_valid
    condition_type: expression
    expression: "retry_count < 3"
    required: true
actions:
  - action_name: log_retry_attempt
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: INFO
      message: "Retrying registration from failed state"
```

**Guard Cross-Reference**: The `retry_count < 3` guard enforces the retry limit (maximum 3 attempts). See [Retry Limit Enforcement](#retry-limit-enforcement) for detailed enforcement behavior, counter increment semantics, reset events, and exhaustion handling.

---

#### Transition 15: `abandon_registration`

```yaml
transition_name: abandon_registration
from_state: failed
to_state: deregistered
trigger: ABANDON
priority: 5
is_atomic: true
conditions: []
actions:
  - action_name: log_abandonment
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: WARNING
      message: "Registration abandoned after failures"
```

---

#### Transition 16: `global_error_handler`

```yaml
transition_name: global_error_handler
from_state: "*"
to_state: failed
trigger: FATAL_ERROR
priority: 0
is_atomic: true
conditions: []
actions:
  - action_name: log_fatal_error
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: CRITICAL
      message: "Fatal error during registration workflow"
```

**Note**: Wildcard `from_state: "*"` matches all non-terminal states. The only true terminal state is `deregistered`, which has no outgoing transitions and cannot receive this global error handler. The `registered` state is a **success state** (not terminal) with a single outgoing transition to `deregistering` for graceful shutdown, so it is still matched by the wildcard and can transition to `failed` on `FATAL_ERROR`.

---

#### Transition 17: `retry_exhausted`

```yaml
transition_name: retry_exhausted
from_state: partial_registered
to_state: failed
trigger: RETRY_EXHAUSTED
priority: 10
is_atomic: true
conditions:
  - condition_name: retry_limit_reached
    condition_type: expression
    expression: "retry_count >= 3"
    required: true
actions:
  - action_name: log_retry_exhausted
    action_type: emit_intent
    action_config:
      intent_type: log_event
      level: ERROR
      message: "Retry limit exhausted in partial_registered state"
```

**Note**: This transition handles the case when retry attempts in `partial_registered` state have been exhausted. When `retry_count >= 3`, the guard on the `retry_consul` (Transition 9) and `retry_postgres` (Transition 10) transitions will fail. The Reducer should then emit a `RETRY_EXHAUSTED` trigger to move to the `failed` state, from which the operator can either retry the full workflow or abandon the registration.

---

## Guards

Guards are conditions that must evaluate to `true` for a transition to occur.

### Guard Definitions

| Guard Name | Expression | Required? | Description |
|------------|------------|-----------|-------------|
| `has_registration_payload` | `payload exists true` | Yes | Payload must be present to start registration |
| `payload_valid` | `validation_result == passed` | Yes | Payload must pass validation |
| `payload_invalid` | `validation_result == failed` | Yes | Payload failed validation |
| `postgres_applied` | `postgres_applied == true` | Yes | PostgreSQL registration succeeded |
| `postgres_error` | `postgres_applied == false` | Yes | PostgreSQL registration failed |
| `consul_applied` | `consul_applied == true` | Yes | Consul registration succeeded |
| `consul_error` | `consul_applied == false` | Yes | Consul registration failed |
| `both_applied` | `postgres_applied == true` | Yes | Both registrations succeeded (checked with `consul_now_applied`) |
| `consul_now_applied` | `consul_applied == true` | Yes | Consul now succeeded after retry |
| `consul_failed_postgres_ok` | `postgres_applied == true` | Yes | Postgres OK but Consul failed |
| `postgres_failed_consul_ok` | `consul_applied == true` | Yes | Consul OK but Postgres failed |
| `retry_count_valid` | `retry_count < 3` | Yes | Haven't exceeded retry limit |
| `retry_limit_reached` | `retry_count >= 3` | Yes | Retry limit has been reached |

**Cross-Reference**: For retry limit guard (`retry_count < 3`) enforcement details including counter increment semantics, reset events, and exhaustion handling, see [Retry Limit Enforcement](#retry-limit-enforcement).

### Guard Expression Syntax

Guards use a strict 3-token expression format:

```text
<field> <operator> <value>
```

Where:
- **`<field>`**: Context field name (alphanumeric with underscores, must not start with a digit)
- **`<operator>`**: One of the supported operators listed below
- **`<value>`**: Literal value (boolean, number, string, or array)

**Token Separation**: Tokens are separated by whitespace. The expression is split into exactly 3 parts.

**Valid Operators**:

| Category | Operators | Value Types |
|----------|-----------|-------------|
| Equality | `==`, `!=`, `equals`, `not_equals` | boolean, number, string |
| Comparison | `<`, `>`, `<=`, `>=` | number |
| Existence | `exists`, `not_exists` | `true` or `false` |
| Containment | `in`, `not_in` | array (e.g., `[a, b, c]`) |
| Containment | `contains` | scalar value |
| Pattern | `matches` | regex pattern (unquoted) |

**Value Literal Syntax**:

| Type | Format | Examples | Notes |
|------|--------|----------|-------|
| **Boolean** | Lowercase `true` or `false` | `true`, `false` | Must be lowercase; `True`, `FALSE` are invalid |
| **Number** | Integer or decimal, optional sign | `3`, `3.14`, `-1`, `0`, `-0.5` | Scientific notation not supported |
| **String** | Unquoted alphanumeric with underscores | `passed`, `failed`, `in_progress` | No whitespace or special characters allowed |
| **Array** | Bracket-enclosed, comma-separated | `[a, b, c]`, `[registering_postgres]` | Whitespace around brackets/commas is ignored |
| **Pattern** | Unquoted regex (Python `re` flavor) | `^node-.*`, `^v[0-9]+\.[0-9]+$` | PCRE-compatible; see regex details below |

**Regex Pattern Syntax**:
- **Flavor**: Python `re` module (PCRE-compatible regular expressions)
- **Anchoring**: Patterns are NOT automatically anchored. Use `^` for start-of-string and `$` for end-of-string.
- **Case Sensitivity**: Patterns are case-sensitive by default. Use `(?i)` prefix for case-insensitive matching.
- **Escaping**: Backslashes in YAML require double-escaping (e.g., `\\d` to match digits). In Python contract definitions, use raw strings or single escapes.
- **Common Pattern Examples**:
  ```text
  ^node-.*                    # Starts with "node-"
  .*_test$                    # Ends with "_test"
  ^v[0-9]+\.[0-9]+\.[0-9]+$   # Semantic version (v1.2.3)
  (?i)^production             # Case-insensitive prefix match
  ^[a-z][a-z0-9_]*$           # Valid identifier format
  ```

**Case Sensitivity**: Field names and string values are case-sensitive. `Passed` != `passed`. Pattern matching is also case-sensitive unless the `(?i)` flag is used.

**Examples by Operator Category**:
```text
# Equality operators
postgres_applied == true
validation_result != failed
status equals active
error_code not_equals E001

# Comparison operators (numeric only)
retry_count < 3
retry_count >= 0
priority <= 5

# Existence operators
consul_error exists true
optional_field not_exists true

# Containment operators
state in [registering_postgres, registering_consul, partial_registered]
tags contains production
environment not_in [dev, test]

# Pattern matching
service_name matches ^node-.*
version matches ^v[0-9]+\\.[0-9]+$
```

**Nested Fields**: Guard expressions support only top-level field references (e.g., `postgres_applied`). Nested field access (e.g., `context.retry_count` or `payload.node_id`) is NOT supported in guard expressions. If nested data is required, the Reducer should flatten the context before guard evaluation.

### Guard Validation Rules

Guards are validated at two phases to ensure correctness and provide clear error messages.

#### Contract Load-Time Validation

When the FSM contract is loaded, all guard expressions are validated for syntactic correctness:

1. **Syntax validation**: Expression must follow `field operator value` format (exactly 3 tokens)
2. **Operator validation**: Operator must be in the supported operator set
3. **Field reference validation**: Field names must be valid identifiers (alphanumeric with underscores, not starting with a number)
4. **Value format validation**: Values must be parseable (booleans, numbers, strings, arrays)

**Contract Load-Time Validation Errors**:

| Error Code | Description | Example |
|------------|-------------|---------|
| `GUARD_SYNTAX_ERROR` | Expression doesn't follow 3-token format | `"postgres_applied"` (missing operator and value) |
| `GUARD_INVALID_OPERATOR` | Operator not in supported set | `"retry_count ~= 3"` (invalid operator `~=`) |
| `GUARD_INVALID_FIELD` | Field name is not a valid identifier | `"123field == true"` (starts with number) |
| `GUARD_INVALID_VALUE` | Value cannot be parsed | `"count < [invalid"` (malformed array) |

**Contract Validation Example**:
```python
# Valid guards - pass contract validation
"postgres_applied == true"      # Boolean comparison
"retry_count < 3"               # Numeric comparison
"validation_result == passed"   # String comparison
"tags contains production"      # Containment check
"state in [active, pending]"    # Array containment
"version matches ^v[0-9]+"      # Pattern matching

# Invalid guards - fail contract validation
"postgres_applied"              # GUARD_SYNTAX_ERROR: missing operator/value
"count <=> 5"                   # GUARD_INVALID_OPERATOR: unknown operator
"2fast == true"                 # GUARD_INVALID_FIELD: invalid identifier
"retry_count < "                # GUARD_SYNTAX_ERROR: missing value token
"field == == true"              # GUARD_SYNTAX_ERROR: too many tokens (4)
"count < [a, b"                 # GUARD_INVALID_VALUE: unclosed array bracket
```

**Edge Case Examples**:
```python
# Whitespace handling
"  retry_count   <   3  "       # Valid - extra whitespace is trimmed
"retry_count< 3"                # GUARD_SYNTAX_ERROR: operator attached to field

# Case sensitivity
"PostgresApplied == true"       # Valid syntax, but field name is case-sensitive
"postgres_applied == True"      # GUARD_INVALID_VALUE: boolean must be lowercase

# Boundary values
"retry_count >= 0"              # Valid - zero is allowed
"retry_count < -1"              # Valid - negative numbers allowed
"priority <= 999999999"         # Valid - large numbers supported

# Empty and null handling
"field exists true"             # Valid - checks for presence
"field exists false"            # Valid - checks for absence (same as not_exists true)
"field == null"                 # GUARD_INVALID_VALUE: use "exists" for null checks
```

#### Runtime Validation

At runtime, guards are validated when evaluated against the FSM context:

1. **Field resolution**: Field must exist in the FSM context (or be handled by `exists`/`not_exists`)
2. **Type compatibility**: Field value type must be compatible with the operator
3. **Value coercion**: Value must be coercible to the expected type for comparison

**Runtime Validation Errors** (see also "Error Handling" subsection below):

| Error Code | Description | Recovery |
|------------|-------------|----------|
| `GUARD_EVALUATION_ERROR` | Unsupported operator at runtime | Fix guard expression in contract |
| `GUARD_TYPE_ERROR` | Type mismatch during evaluation | Fix context data or guard expression |
| `GUARD_FIELD_UNDEFINED` | Referenced field not in context | Ensure context populated before transition |

**Runtime Behavior for Undefined Fields**:
- For `exists`/`not_exists` operators: Undefined fields return appropriate boolean
- For other operators: Guard evaluation returns `false`, transition is blocked
- No exception is raised for undefined fields (fail-safe behavior)

### Trigger Catalog

The FSM uses the following triggers to drive state transitions:

| Trigger | Source | Description |
|---------|--------|-------------|
| `REGISTER` | External | `IntrospectionEvent` received with registration payload. Initiates the registration workflow. |
| `VALIDATION_PASSED` | Internal | Payload validation succeeded. Emitted by the Reducer after validating `ModelRegistrationPayload`. |
| `VALIDATION_FAILED` | Internal | Payload validation failed. Emitted when required fields are missing or invalid. |
| `POSTGRES_SUCCEEDED` | Effect | PostgreSQL Effect returned success. The upsert operation completed successfully. |
| `POSTGRES_FAILED` | Effect | PostgreSQL Effect returned failure. Database error or constraint violation. |
| `CONSUL_SUCCEEDED` | Effect | Consul Effect returned success. Service registration completed successfully. |
| `CONSUL_FAILED` | Effect | Consul Effect returned failure. Network error or Consul unavailable. |
| `CONTINUE` | Internal | **Synthetic internal trigger** for automatic state progression. Emitted by the Reducer itself during `POSTGRES_SUCCEEDED` processing to advance from `postgres_registered` to `registering_consul`. Never received from external sources. See [Transition 6](#transition-6-start_consul_registration) for detailed implementation semantics including single-step vs two-step execution patterns. |
| `RECOVERY_COMPLETE` | Orchestrator | Both components are now registered. This trigger is emitted when partial registration is resolved through retry. |
| `DEREGISTER` | External | Shutdown signal received. Initiates graceful deregistration from both systems. |
| `DEREGISTRATION_COMPLETE` | Orchestrator | Both deregistrations succeeded. This trigger is emitted after Consul and PostgreSQL cleanup is complete. |
| `RETRY` | External/Internal | Initiates a retry after failure. This trigger can be invoked from `partial_registered` state (retries Consul registration via Transition 9) or from `failed` state (restarts full registration from `validating` via Transition 14). The trigger can be invoked by operator intervention or by an automatic retry policy, and is subject to the `retry_count < 3` guard. |
| `RETRY_POSTGRES` | External | Retries PostgreSQL specifically. This trigger is used when Consul succeeded but PostgreSQL failed. |
| `ABANDON` | External | Gives up on registration. This trigger transitions directly to `deregistered` without attempting cleanup. |
| `FATAL_ERROR` | Internal | Unrecoverable error detected. This trigger catches unexpected failures from any non-terminal state. |
| `RETRY_EXHAUSTED` | Internal | Retry limit reached. **Generated by the Orchestrator** (not the Reducer) when it detects that the Reducer returned without state change due to guard failure on retry transitions. The Orchestrator emits this trigger when `retry_count >= max_retries` to transition to `failed` state for operator intervention. |

**Trigger Sources**:
- **External**: Triggered by events from outside the FSM (user actions, lifecycle signals, introspection events)
- **Internal**: Triggered by the Reducer itself based on internal logic or validation results
- **Effect**: Triggered by Effect nodes returning execution results
- **Orchestrator**: Triggered by the Orchestrator after aggregating multiple Effect outcomes

### Guard Implementation Details

#### Type Resolution

Guard field types are inferred from FSM context at runtime:
- **Boolean fields**: `postgres_applied`, `consul_applied` - direct boolean comparison
- **Numeric fields**: `retry_count` - supports numeric comparison operators
- **String fields**: `validation_result` - string equality comparison

#### Field Resolution

Guard fields are resolved from the FSM state context object:
```python
# Example context structure
fsm_context = {
    "postgres_applied": True,
    "consul_applied": False,
    "retry_count": 2,
    "validation_result": "passed",
}
```

#### Operator Semantics

| Operator | Behavior | Example |
|----------|----------|---------|
| `==`, `equals` | Strict equality | `retry_count == 0` |
| `!=`, `not_equals` | Strict inequality | `validation_result != failed` |
| `<`, `>`, `<=`, `>=` | Numeric comparison | `retry_count < 3` |
| `exists` | Field is present and not null | `consul_error exists true` |
| `not_exists` | Field is null or absent | `postgres_error not_exists true` |
| `in` | Value in array | `state in [registering_postgres, registering_consul]` |
| `contains` | Array contains value | `tags contains production` |
| `matches` | Regex pattern match | `service_name matches ^node-.*` |

#### Error Handling

- **Undefined field**: Guard evaluation returns `false`, transition blocked
- **Unsupported operator**: Raises `ModelOnexError` with `GUARD_EVALUATION_ERROR` code
- **Type mismatch**: Raises `ModelOnexError` with `GUARD_TYPE_ERROR` code

---

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> unregistered

    unregistered --> validating : REGISTER

    validating --> registering_postgres : VALIDATION_PASSED
    validating --> failed : VALIDATION_FAILED

    registering_postgres --> postgres_registered : POSTGRES_SUCCEEDED
    registering_postgres --> failed : POSTGRES_FAILED

    postgres_registered --> registering_consul : CONTINUE

    registering_consul --> registered : CONSUL_SUCCEEDED
    registering_consul --> partial_registered : CONSUL_FAILED

    partial_registered --> registering_consul : RETRY [postgres_applied=true]
    partial_registered --> registering_postgres : RETRY_POSTGRES [consul_applied=true]
    partial_registered --> registered : RECOVERY_COMPLETE
    partial_registered --> failed : RETRY_EXHAUSTED [retry_count >= 3]

    registered --> deregistering : DEREGISTER

    deregistering --> deregistered : DEREGISTRATION_COMPLETE

    failed --> validating : RETRY [retry_count < 3]
    failed --> deregistered : ABANDON

    note right of registered
        Success state (non-terminal).
        Only DEREGISTER trigger
        allows transition out.
    end note

    note right of partial_registered
        Recoverable error state.
        Can retry the failed
        component (Consul or Postgres).
    end note

    note right of deregistered
        Terminal state.
        No outgoing transitions.
    end note

    deregistered --> [*]
```

### Simplified Flow Diagram

```text
                                    ┌────────────────────────────────────┐
                                    │        Registration FSM            │
                                    └────────────────────────────────────┘

    ┌─────────────┐     REGISTER     ┌─────────────┐   VALIDATION   ┌────────────────────┐
    │ unregistered │────────────────▶│  validating │───PASSED──────▶│ registering_postgres│
    └─────────────┘                  └─────────────┘                └────────────────────┘
                                            │                               │
                                     VALIDATION_FAILED               POSTGRES_SUCCEEDED
                                            │                               │
                                            ▼                               ▼
                                      ┌─────────┐                  ┌─────────────────┐
                                      │ failed  │◀──POSTGRES_FAILED│ postgres_registered│
                                      └─────────┘                  └─────────────────┘
                                            │                               │
                                        RETRY │                        CONTINUE
                                            │                               │
                                            ▼                               ▼
                                      ┌─────────────┐              ┌─────────────────┐
                                      │  validating │              │registering_consul│
                                      └─────────────┘              └─────────────────┘
                                                                           │
                              ┌────────────────────────────────────────────┼─────────────────┐
                              │                                            │                 │
                       CONSUL_FAILED                                CONSUL_SUCCEEDED         │
                              │                                            │                 │
                              ▼                                            ▼                 │
                   ┌──────────────────┐                          ┌────────────────┐         │
                   │partial_registered │─────RECOVERY_COMPLETE──▶│   registered   │         │
                   └──────────────────┘                          └────────────────┘         │
                         │    │                                          │                 │
                     RETRY│    │RETRY_EXHAUSTED                    DEREGISTER              │
                         │    │[retry_count>=3]                          │                 │
                         ▼    ▼                                          ▼                 │
                   ┌─────────────────┐  ┌─────────┐             ┌────────────────┐         │
                   │registering_consul│  │ failed  │             │  deregistering │         │
                   └─────────────────┘  └─────────┘             └────────────────┘         │
                                                                           │                 │
                                                               DEREGISTRATION_COMPLETE      │
                                                                           │                 │
                                                                           ▼                 │
                                                                ┌────────────────┐          │
                                                                │  deregistered  │◀─ABANDON─┘
                                                                └────────────────┘
```

---

## Intent Emission

The Reducer emits Intents based on state transitions and entry/exit actions.

### Intent Emission Matrix

| State/Transition | Intent Type | Intent Kind | Target | Description |
|-----------------|-------------|-------------|--------|-------------|
| `validating` entry | `log_event` | log | `logging_service` | Log validation start |
| `registering_postgres` entry | `postgres.upsert_registration` | registration | `postgres_effect` | Emit PostgreSQL upsert intent |
| `postgres_registered` entry | `log_metric` | metric | `metrics_service` | Record PostgreSQL success |
| `registering_consul` entry | `consul.register` | registration | `consul_effect` | Emit Consul register intent |
| `consul_success` transition | `log_metric` | metric | `metrics_service` | Record full registration success |
| `consul_failure` transition | `log_metric` | metric | `metrics_service` | Record partial registration |
| `partial_registered` entry | `log_event` | log | `logging_service` | Log partial failure with details |
| `registered` entry | `log_event` | log | `logging_service` | Log registration complete |
| `deregistering` entry | `consul.deregister` | registration | `consul_effect` | Emit Consul deregister intent |
| `deregistering` entry | `postgres.delete_registration` | registration | `postgres_effect` | Emit PostgreSQL delete intent |
| `deregistered` entry | `log_event` | log | `logging_service` | Log deregistration complete |
| `failed` entry | `log_event` | log | `logging_service` | Log failure with error details |

### Core Registration Intents

The following intents are emitted during registration:

#### 1. `ModelConsulRegisterIntent`

```python
ModelConsulRegisterIntent(
    kind="consul.register",
    service_id=payload.consul_service_id,
    service_name=payload.consul_service_name,
    tags=payload.consul_tags,
    health_check=payload.consul_health_check,
    correlation_id=context.correlation_id,
)
```

**Emitted**: On entry to `registering_consul` state
**Executed by**: Consul Effect Node

#### 2. `ModelConsulDeregisterIntent`

```python
ModelConsulDeregisterIntent(
    kind="consul.deregister",
    service_id=payload.consul_service_id,
    correlation_id=context.correlation_id,
)
```

**Emitted**: On entry to `deregistering` state
**Executed by**: Consul Effect Node

#### 3. `ModelPostgresUpsertRegistrationIntent`

```python
ModelPostgresUpsertRegistrationIntent(
    kind="postgres.upsert_registration",
    record=payload.postgres_record,
    correlation_id=context.correlation_id,
)
```

**Emitted**: On entry to `registering_postgres` state
**Executed by**: PostgreSQL Effect Node

---

## Validation Rules

### Contract-Level Validation

The FSM contract is validated at load time:

1. **Initial state exists**: `unregistered` must be in states list
2. **Success states exist**: `registered` must be in states list (success state allowing graceful shutdown)
3. **Terminal states exist**: `deregistered` must be in states list (true terminal with no outgoing transitions)
4. **Error states exist**: `partial_registered`, `failed` must be in states list
5. **No orphan states**: All states must have at least one incoming or outgoing transition
6. **No transitions from terminal states**: `deregistered` has no outgoing transitions; `registered` (success state) has one outgoing transition to `deregistering` for graceful shutdown
7. **Unique transition names**: All transition names must be unique
8. **Valid from/to states**: All transition `from_state` and `to_state` must exist in states list

### Runtime Validation

During execution, the Reducer validates:

1. **Payload completeness**: Required fields present before state transitions
2. **Guard satisfaction**: All required guards must pass
3. **State consistency**: Current state must match expected `from_state`
4. **Retry limits**: Retry count must not exceed maximum

### Validation Errors

| Error Code | Phase | Description | Recovery |
|------------|-------|-------------|----------|
| `VALIDATION_ERROR` | Runtime | Payload failed validation | Fix payload, retry |
| `INVALID_TRANSITION` | Runtime | No valid transition from current state | Check guards, fix state |
| `STATE_MISMATCH` | Runtime | Current state doesn't match expected | Reset FSM |
| `RETRY_EXHAUSTED` | Runtime | Maximum retry count exceeded | Manual intervention |
| `GUARD_FAILED` | Runtime | Required guard condition not satisfied | Fix context, retry |
| `GUARD_SYNTAX_ERROR` | Contract Load | Expression doesn't follow 3-token format | Fix guard expression syntax in contract |
| `GUARD_INVALID_OPERATOR` | Contract Load | Operator not in supported set | Use supported operator from operator set |
| `GUARD_INVALID_FIELD` | Contract Load | Field name is not a valid identifier | Fix field name (alphanumeric, underscores, no leading digits) |
| `GUARD_INVALID_VALUE` | Contract Load | Value cannot be parsed | Fix value format (boolean, number, string, or array literal) |
| `GUARD_EVALUATION_ERROR` | Runtime | Unsupported operator at runtime | Fix guard expression in contract |
| `GUARD_TYPE_ERROR` | Runtime | Type mismatch during evaluation | Ensure field type matches operator expectations |
| `GUARD_FIELD_UNDEFINED` | Runtime | Referenced field not in context | Ensure context populated before transition (see note) |
| `TIMEOUT_EXCEEDED` | Runtime | State timeout exceeded | Check Effect execution time, increase timeout or fix blocking issue |
| `INTENT_EMISSION_FAILED` | Runtime | Failed to emit intent during transition | Check intent payload, verify target Effect exists |

**Note on `GUARD_FIELD_UNDEFINED`**: This error code is available for strict mode implementations. By default, undefined fields cause guard evaluation to return `false` (fail-safe behavior) rather than raising an exception. Implementations may choose to raise `GUARD_FIELD_UNDEFINED` in strict validation mode when `strict_validation_enabled: true` is set in the FSM subcontract.

---

## Implementation Notes

### For OMN-889 (Dual Registration Reducer)

1. **Reducer Purity**: The Reducer must be pure - no I/O, no logging directly. All side effects via Intent emission.

2. **State Storage**: FSM state should be stored in the Reducer's internal state, passed through `ModelReducerInput`.

3. **Intent Batching**: When entering `deregistering`, emit both deregistration intents atomically.

4. **Outcome Handling**: Use `ModelDualRegistrationOutcome` to aggregate Effect results:
   ```python
   outcome = ModelDualRegistrationOutcome(
       node_id=payload.node_id,
       status="success" | "partial" | "failed",
       postgres_applied=True,
       consul_applied=True,
       correlation_id=context.correlation_id,
   )
   ```

5. **Retry Logic**: Implement exponential backoff in Effect nodes, not Reducer. Reducer just emits retry intents with incremented counter.

6. **Correlation Tracking**: All intents must include `correlation_id` from the originating event for distributed tracing.

### Retry Counter Management

The FSM uses a retry counter to limit retry attempts and prevent infinite loops.

```yaml
retry_counter:
  storage: fsm_state_context.retry_count
  increment_on: [RETRY, RETRY_POSTGRES]
  reset_on: [POSTGRES_SUCCEEDED, CONSUL_SUCCEEDED, VALIDATION_PASSED]
  max_value: 3
```

**Semantics**:

1. **Storage**: The retry counter is stored in `fsm_state_context.retry_count` and passed through `ModelReducerInput`.

2. **Increment**: The counter is incremented by the Reducer when processing `RETRY` or `RETRY_POSTGRES` triggers, before emitting the retry intent.

3. **Reset**: The counter is reset to 0 on successful operations (`POSTGRES_SUCCEEDED`, `CONSUL_SUCCEEDED`, `VALIDATION_PASSED`).

4. **Guard Check**: Transitions 9, 10, and 14 include the guard `retry_count < 3` which prevents retry if the limit has been reached.

5. **Exhaustion Handling**: When `retry_count >= 3` in `partial_registered` state, the guard on `RETRY` and `RETRY_POSTGRES` transitions fails. The Reducer should then emit a `RETRY_EXHAUSTED` trigger (Transition 17) to move to the `failed` state. From `failed`, the operator can either:
   - Trigger `RETRY` to restart the full workflow from `validating` (if retry_count allows)
   - Trigger `ABANDON` to move to `deregistered` state and give up on registration

#### Retry Limit Enforcement

The retry limit is enforced through the guard condition `retry_count < 3` on retry transitions. This section provides detailed enforcement behavior documentation.

**Maximum Retry Value**: `3`

The FSM allows a maximum of 3 retry attempts before considering the registration permanently failed. This value balances recovery resilience with avoiding infinite retry loops.

**Triggers That Increment the Counter**:

| Trigger | Transition | Effect |
|---------|------------|--------|
| `RETRY` | Transitions 9 and 14 | Increments `retry_count` before retrying Consul or full registration |
| `RETRY_POSTGRES` | Transition 10 | Increments `retry_count` before retrying PostgreSQL |

**When the Limit Is Reached**:

When `retry_count >= 3`, the guard condition `retry_count < 3` evaluates to `false`. This causes:

1. **Transition Blocked**: The retry transition (9, 10, or 14) cannot fire
2. **State Unchanged**: The FSM remains in current state (`partial_registered` or `failed`)
3. **No Intent Emitted**: No retry intent is emitted since no transition occurs
4. **Manual Intervention Required**: The Orchestrator or operator must trigger `RETRY_EXHAUSTED` or `ABANDON`

**Counter Reset Events**:

The counter resets to 0 when any of these success events occur:

| Event | States Where Reset Occurs |
|-------|--------------------------|
| `POSTGRES_SUCCEEDED` | After `registering_postgres` |
| `CONSUL_SUCCEEDED` | After `registering_consul` |
| `VALIDATION_PASSED` | After `validating` |

This allows fresh retry attempts if a later phase fails after an earlier retry succeeded.

**Implementation Example**:

The Reducer should implement retry limit handling as follows:

```python
async def handle_retry_trigger(
    self,
    current_state: str,
    context: ModelFSMContext,
) -> tuple[str, list[ModelIntent]]:
    """Handle RETRY trigger with limit enforcement."""
    retry_count = context.retry_count

    # Check guard condition
    if retry_count >= 3:
        # Guard failed - cannot transition
        # Emit exhaustion intent for Orchestrator awareness
        return current_state, [
            ModelLogIntent(
                kind="log_event",
                level="WARNING",
                message=f"Retry limit exhausted (count={retry_count}). "
                        "Trigger RETRY_EXHAUSTED or ABANDON to proceed.",
                correlation_id=context.correlation_id,
            )
        ]

    # Guard passed - proceed with retry transition
    new_context = context.model_copy(
        update={"retry_count": retry_count + 1}
    )

    if current_state == "partial_registered":
        # Transition 9: retry_consul
        return "registering_consul", [
            ModelConsulRegisterIntent(
                kind="consul.register",
                service_id=context.consul_service_id,
                correlation_id=context.correlation_id,
            )
        ]
    elif current_state == "failed":
        # Transition 14: retry_from_failed
        return "validating", [
            ModelLogIntent(
                kind="log_event",
                level="INFO",
                message="Retrying registration from failed state",
                correlation_id=context.correlation_id,
            )
        ]

    # Invalid state for RETRY trigger
    raise ModelOnexError(
        message=f"RETRY trigger invalid in state: {current_state}",
        error_code=EnumCoreErrorCode.INVALID_TRANSITION,
    )
```

**Orchestrator Responsibility**:

When the Reducer returns without a state change (guard failed), the Orchestrator should:

1. Detect the retry exhaustion condition
2. Log the exhaustion event with context
3. Either:
   - Trigger `RETRY_EXHAUSTED` to move to `failed` state (Transition 17)
   - Trigger `ABANDON` to move to `deregistered` (automatic cleanup)
   - Alert operators for manual intervention

### Timeout Handling

Several operational states define `timeout_ms` values that specify the maximum time allowed for state completion. This section documents timeout behavior and recovery strategies.

#### Timeout Configuration

The following states have timeout values defined:

| State | Timeout (ms) | Timeout (s) | Purpose |
|-------|-------------|-------------|---------|
| `validating` | 5000 | 5s | Payload validation should complete quickly |
| `registering_postgres` | 10000 | 10s | Database upsert with network latency |
| `registering_consul` | 10000 | 10s | Service registration with network latency |
| `deregistering` | 15000 | 15s | Cleanup of both systems (longer for graceful shutdown) |

**Note**: States without explicit `timeout_ms` (such as `unregistered`, `registered`, `failed`, `partial_registered`, `deregistered`) can remain in that state indefinitely until an external trigger is received.

#### Timeout Semantics

**What `timeout_ms` Represents**:

The `timeout_ms` value is the maximum wall-clock time the FSM should remain in an operational state awaiting an effect result or external trigger. If this duration elapses without a valid transition trigger, the state is considered timed out.

**Timeout Detection**:

Timeout detection is the responsibility of the **Orchestrator**, not the Reducer. The Reducer is pure and has no concept of wall-clock time. The Orchestrator must:

1. Record entry timestamp when the FSM enters a state with `timeout_ms`
2. Monitor elapsed time while awaiting Effect results
3. Emit appropriate timeout trigger when `timeout_ms` is exceeded

**Timeout Trigger Emission**:

When a timeout occurs, the Orchestrator should emit one of the following triggers based on severity:

| State | Timeout | On Timeout | Rationale |
|-------|---------|------------|-----------|
| `validating` | 5s | Emit `FATAL_ERROR` -> `failed` | Validation should be fast; timeout indicates system issue |
| `registering_postgres` | 10s | Emit `POSTGRES_FAILED` -> `failed` | Database unreachable; treat as failure |
| `registering_consul` | 10s | Emit `CONSUL_FAILED` -> `partial_registered` | Consul unreachable; PostgreSQL already succeeded |
| `deregistering` | 15s | Emit `DEREGISTRATION_COMPLETE` -> `deregistered` | Best-effort cleanup; proceed to terminal state |

#### Orchestrator Timeout Monitoring

The Orchestrator should implement timeout monitoring as follows:

```python
async def monitor_state_timeout(
    self,
    fsm_state: str,
    state_entered_at: datetime,
    timeout_ms: int | None,
) -> str | None:
    """
    Monitor for state timeout and return appropriate trigger if exceeded.

    Returns:
        Trigger name if timeout exceeded, None otherwise.
    """
    if timeout_ms is None:
        # No timeout configured for this state
        return None

    elapsed_ms = (datetime.utcnow() - state_entered_at).total_seconds() * 1000

    if elapsed_ms < timeout_ms:
        # Still within timeout window
        return None

    # Timeout exceeded - determine appropriate trigger
    timeout_triggers: dict[str, str] = {
        "validating": "FATAL_ERROR",
        "registering_postgres": "POSTGRES_FAILED",
        "registering_consul": "CONSUL_FAILED",
        "deregistering": "DEREGISTRATION_COMPLETE",
    }

    trigger = timeout_triggers.get(fsm_state, "FATAL_ERROR")

    self.logger.warning(
        f"State timeout exceeded: state={fsm_state}, "
        f"timeout_ms={timeout_ms}, elapsed_ms={elapsed_ms}, "
        f"emitting_trigger={trigger}"
    )

    return trigger
```

#### Timeout Recovery Strategies

**Strategy 1: Immediate Failure (Recommended for `validating`)**

Validation timeouts indicate a fundamental system issue (CPU overload, memory exhaustion). The FSM should transition to `failed` immediately and await manual intervention or retry.

```text
validating --[timeout]--> FATAL_ERROR --> failed
```

**Strategy 2: Retry-Eligible Failure (Recommended for `registering_postgres`)**

PostgreSQL timeouts are often transient (network blip, database restart). The FSM transitions to `failed` but can be retried.

```text
registering_postgres --[timeout]--> POSTGRES_FAILED --> failed --[RETRY]--> validating
```

**Strategy 3: Partial Registration (Recommended for `registering_consul`)**

If Consul times out after PostgreSQL succeeded, the node is partially registered. This allows targeted retry of just the Consul component.

```text
registering_consul --[timeout]--> CONSUL_FAILED --> partial_registered --[RETRY]--> registering_consul
```

**Strategy 4: Best-Effort Cleanup (Recommended for `deregistering`)**

During graceful shutdown, cleanup timeouts should not block the shutdown process. The FSM proceeds to terminal state with a warning.

```text
deregistering --[timeout]--> DEREGISTRATION_COMPLETE --> deregistered
```

#### Timeout vs. Failure Distinction

| Scenario | Trigger | Recovery Path |
|----------|---------|---------------|
| Effect returns error | `*_FAILED` | Normal retry logic applies |
| Effect times out | `*_FAILED` (via Orchestrator) | Same retry logic, but may need longer timeout |
| Effect hangs indefinitely | Orchestrator timeout trigger | Cancel pending effect, transition to failure |

**Important**: The Reducer cannot distinguish between a timeout and an explicit failure - both result in the same trigger. The Orchestrator should log timeout events distinctly for observability.

#### Timeout Metrics

The Orchestrator should emit metrics for timeout events:

```yaml
metrics:
  - name: registration_state_timeout_total
    type: counter
    labels: [state, trigger_emitted]
    description: "Count of state timeout events by state and resulting trigger"

  - name: registration_state_duration_ms
    type: histogram
    labels: [state, outcome]
    description: "Duration spent in each state, labeled by outcome (success/timeout/failure)"
```

### FSM Subcontract Configuration

```yaml
fsm_subcontract:
  version: { major: 1, minor: 0, patch: 0 }
  state_machine_name: "registration_fsm"
  state_machine_version: { major: 1, minor: 0, patch: 0 }
  description: "Dual Registration FSM for Consul and PostgreSQL"
  initial_state: "unregistered"
  success_states:
    - "registered"
  terminal_states:
    - "deregistered"
  error_states:
    - "partial_registered"
    - "failed"
  persistence_enabled: true
  checkpoint_interval_ms: 5000
  recovery_enabled: true
  rollback_enabled: true
  strict_validation_enabled: true
  conflict_resolution_strategy: "priority_based"
  concurrent_transitions_allowed: false
  transition_timeout_ms: 10000
```

---

## Error Handling

### Error Categories

| Category | States | Recovery Strategy |
|----------|--------|-------------------|
| **Validation Errors** | `validating` -> `failed` | Fix payload, retry via `RETRY` |
| **PostgreSQL Errors** | `registering_postgres` -> `failed` | Check database, retry via `RETRY` |
| **Consul Errors** | `registering_consul` -> `partial_registered` | Retry Consul via `RETRY` |
| **Partial Failures** | `partial_registered` | Retry failed component |
| **Fatal Errors** | Any -> `failed` | Manual intervention or `ABANDON` |
| **Guard Errors** | Any (contract load or runtime) | Fix guard expression or context data |
| **Timeout Errors** | Operational states with `timeout_ms` | Increase timeout, fix blocking Effect, or manual intervention |
| **Intent Emission Errors** | Any state with entry actions | Verify intent payload and target Effect availability |

### Guard Error Details

Guard errors can occur at two phases:

1. **Contract Load-Time**: Malformed guard expressions (`GUARD_SYNTAX_ERROR`, `GUARD_INVALID_OPERATOR`, `GUARD_INVALID_FIELD`, `GUARD_INVALID_VALUE`) prevent the FSM contract from loading. These must be fixed in the contract definition before the FSM can be used.

2. **Runtime**: Guard evaluation errors occur during transition attempts. The transition is blocked and the FSM remains in its current state. Check the error context to identify the problematic guard and fix either the expression or the context data.
   - `GUARD_EVALUATION_ERROR`: Unsupported operator encountered at runtime
   - `GUARD_TYPE_ERROR`: Type mismatch during evaluation (e.g., comparing string to number)
   - `GUARD_FIELD_UNDEFINED`: Referenced field not found in context (only raised in strict mode when `strict_validation_enabled: true`; default behavior returns `false` and blocks transition without raising an exception)

### Timeout Error Details

States with `timeout_ms` configured (`validating`: 5000ms, `registering_postgres`: 10000ms, `registering_consul`: 10000ms, `deregistering`: 15000ms) will trigger a `TIMEOUT_EXCEEDED` error if the state is not exited within the configured time.

**Recovery**:
- Check Effect node execution time and optimize if needed
- Increase `timeout_ms` in state configuration if timeouts are legitimate
- Investigate network or database connectivity issues for external dependencies
- Consider triggering `FATAL_ERROR` if timeout indicates an unrecoverable condition

### Intent Emission Error Details

Intent emission errors occur when the Reducer fails to emit intents during a transition. This can happen during:
- Entry actions on the target state
- Exit actions on the source state
- Transition actions (executed between exit and entry)
- **CONTINUE trigger processing** (internal automatic progression)

**Error Scenarios**:

| Scenario | Trigger Context | Error Code | Recovery |
|----------|-----------------|------------|----------|
| Invalid intent payload | Any transition | `INTENT_PAYLOAD_ERROR` | Fix payload construction in Reducer |
| Target Effect unavailable | Any transition | `EFFECT_NOT_FOUND` | Verify Effect registration in container |
| Intent serialization failure | Any transition | `INTENT_SERIALIZATION_ERROR` | Check intent model compatibility |
| CONTINUE processing failure | `POSTGRES_SUCCEEDED` -> `registering_consul` | `INTERNAL_TRANSITION_ERROR` | Transition to `failed` via `FATAL_ERROR` |

#### CONTINUE Trigger Failure Handling

The `CONTINUE` trigger is a special case for intent emission errors because it is an internal mechanism with no external retry source. This section details the specific error handling requirements for CONTINUE failures.

**Why CONTINUE Failures Are Special**:

1. **No External Retry Available**: Unlike `POSTGRES_FAILED` or `CONSUL_FAILED` which can be retried via `RETRY` trigger from an external source, `CONTINUE` is internally generated by the Reducer itself. There is no external event to replay that would re-trigger CONTINUE processing.

2. **Indicates System-Level Issue**: Failure during `CONTINUE` processing (after successfully completing `POSTGRES_SUCCEEDED` and transitioning through `postgres_registered`) suggests a fundamental system problem rather than a transient error:
   - Intent construction logic bug in the Reducer
   - Memory exhaustion during intent creation
   - Corrupted FSM context preventing proper intent building
   - Unexpected exception in intent serialization

3. **PostgreSQL Already Succeeded**: At the point CONTINUE fails, PostgreSQL registration has already completed successfully. The system is in an inconsistent state where the database knows about the node but Consul does not.

**Recovery Strategy**:

When CONTINUE processing fails, the FSM should:

1. **Transition to `failed` state via `FATAL_ERROR`**: Since CONTINUE is internal, the only appropriate response is to treat this as a fatal error requiring investigation.

2. **Log comprehensive failure context**: The Orchestrator should capture:
   - The `postgres_registered` checkpoint state (logically traversed even in single-step execution)
   - The specific intent that failed to emit (e.g., `ModelConsulRegisterIntent`)
   - FSM context at time of failure including `correlation_id`
   - Exception details and stack trace

3. **Emit failure metric**: Record `registration_internal_error` metric for alerting and dashboards.

4. **Require operator intervention**: From `failed` state, operator can:
   - Investigate the root cause of CONTINUE failure
   - Trigger `RETRY` to restart full registration from `validating`
   - Trigger `ABANDON` to give up and transition to `deregistered`

**Implementation Pattern**:

```python
async def delta(
    self, state: str, trigger: str, context: ModelFSMContext
) -> tuple[str, list[ModelIntent]]:
    if state == "registering_postgres" and trigger == "POSTGRES_SUCCEEDED":
        try:
            # Log checkpoint traversal (observability requirement)
            checkpoint_log = ModelLogIntent(
                kind="log_event",
                level="DEBUG",
                message="Checkpoint: postgres_registered (proceeding via CONTINUE)",
                correlation_id=context.correlation_id,
            )

            # Build Consul registration intent for CONTINUE progression
            consul_intent = ModelConsulRegisterIntent(
                kind="consul.register",
                service_id=context.consul_service_id,
                service_name=context.consul_service_name,
                correlation_id=context.correlation_id,
            )

            return "registering_consul", [
                checkpoint_log,
                ModelLogIntent(
                    kind="log_event",
                    level="INFO",
                    message="PostgreSQL succeeded, proceeding to Consul",
                ),
                consul_intent,
            ]

        except Exception as e:
            # CONTINUE processing failed - this is a fatal error
            # Log with full context for debugging
            self.logger.error(
                "CONTINUE processing failed during POSTGRES_SUCCEEDED",
                error=str(e),
                error_type=type(e).__name__,
                checkpoint_state="postgres_registered",
                correlation_id=str(context.correlation_id),
            )

            # Transition to failed state with diagnostic intents
            return "failed", [
                ModelLogIntent(
                    kind="log_event",
                    level="CRITICAL",
                    message=f"Internal transition error during CONTINUE: {e}",
                    correlation_id=context.correlation_id,
                ),
                ModelMetricIntent(
                    kind="log_metric",
                    metric="registration_internal_error",
                    value=1,
                    labels={"phase": "continue_processing", "error_type": type(e).__name__},
                ),
            ]
```

**Observability Requirements**:

Even with single-step execution (where `postgres_registered` is not externally observable as a pause point), implementations must:

1. **Log checkpoint traversal**: Emit a DEBUG or INFO log when transitioning through `postgres_registered`. This creates an audit trail showing the logical state progression.

2. **Log CONTINUE initiation**: Emit a log when CONTINUE processing begins. This helps distinguish between "never reached CONTINUE" and "CONTINUE processing failed".

3. **Log failure with full context**: If CONTINUE fails, emit a CRITICAL log with:
   - Checkpoint state (`postgres_registered`)
   - Correlation ID for distributed tracing
   - Exception type and message
   - Relevant context fields

4. **Emit metrics**: Record `registration_internal_error` counter with labels for phase and error type.

**Logging Is Always Safe**: Since logging is performed through intent emission (not direct I/O), the Reducer remains pure. Log intents are processed by the Orchestrator and forwarded to the logging Effect. If even the log intent emission fails, the exception bubbles up and triggers the FATAL_ERROR path.

### Recovery Flows

#### Scenario 1: PostgreSQL Fails First

```text
unregistered -> validating -> registering_postgres -> failed
                                                        |
                                                      RETRY
                                                        |
                                                        v
                                                   validating -> ...
```

#### Scenario 2: Consul Fails After PostgreSQL

```text
unregistered -> validating -> registering_postgres -> postgres_registered ->
    registering_consul -> partial_registered
                              |
                            RETRY (retry Consul only)
                              |
                              v
                         registering_consul -> registered
```

#### Scenario 3: Graceful Shutdown

```text
registered -> deregistering -> deregistered
```

#### Scenario 4: Validation Failure

```text
unregistered -> validating -> failed
                                |
                              RETRY
                                |
                                v
                           validating -> ... (if payload fixed)
```

#### Scenario 5: Retry Exhaustion in Partial State

```text
partial_registered (retry_count >= 3)
        |
   RETRY_EXHAUSTED
        |
        v
      failed
        |
     ABANDON
        |
        v
   deregistered
```

#### Scenario 6: Fatal Error from Any State

```text
Any non-terminal state (e.g., registering_consul)
        |
   FATAL_ERROR
        |
        v
      failed
        |
   RETRY or ABANDON
        |
        v
   validating or deregistered
```

#### Scenario 7: Timeout Recovery (Consul)

```text
registering_consul --[timeout, 10s]--> CONSUL_FAILED --> partial_registered
                                                              |
                                                            RETRY
                                                              |
                                                              v
                                                       registering_consul -> ...
```

#### Scenario 8: CONTINUE Processing Failure

```text
registering_postgres -> [POSTGRES_SUCCEEDED] -> postgres_registered (checkpoint)
                                                        |
                                               [CONTINUE processing fails]
                                                        |
                                                   FATAL_ERROR
                                                        |
                                                        v
                                                     failed
                                                        |
                                       +----------------+----------------+
                                       |                                 |
                                     RETRY                            ABANDON
                                       |                                 |
                                       v                                 v
                                   validating                      deregistered
```

**Context**: This scenario occurs when PostgreSQL registration succeeds but the internal CONTINUE trigger processing fails before Consul registration can begin. Since CONTINUE is an internal mechanism, there is no external event that can be replayed to retry the operation.

**Recovery Options**:
1. **RETRY**: Restarts the full registration workflow from `validating`. The PostgreSQL Effect will receive another upsert intent (idempotent operation).
2. **ABANDON**: Transitions directly to `deregistered`, leaving PostgreSQL in an orphaned state (node record exists but node is not running). Cleanup may be required.

**Investigation Required**: CONTINUE failures indicate a system-level bug. Before retrying, operators should investigate logs and metrics to identify the root cause.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) | Complete architecture overview |
| [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md) | Allowed/forbidden data flows |
| [ModelIntent Architecture](MODEL_INTENT_ARCHITECTURE.md) | Intent pattern for Reducer -> Effect |
| [CONTRACT_DRIVEN_NODEREDUCER_V1_0.md](CONTRACT_DRIVEN_NODEREDUCER_V1_0.md) | Reducer contract specification |
| [Node Purity Guarantees](NODE_PURITY_GUARANTEES.md) | Purity enforcement for Reducer |
| [ONEX Terminology Guide](../standards/onex_terminology.md) | Canonical definitions |

### Implementation Tickets

| Ticket | Description |
|--------|-------------|
| OMN-889 | Dual Registration Reducer implementation |
| OMN-912 | Core Registration Intents |
| OMN-913 | Registration Payload and Outcome models |
| OMN-938 | This FSM Contract (you are here) |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-19
**Primary Maintainer**: ONEX Framework Team
