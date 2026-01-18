> **Navigation**: [Home](../index.md) > [Decisions](README.md) > ADR-004

# ADR-004: Registration Trigger Architecture

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Document Number** | ADR-004 |
| **Status** | 🟢 **ACCEPTED** |
| **Created** | 2025-12-19 |
| **Last Updated** | 2025-12-19 |
| **Author** | Claude Code (AI Assistant) |
| **Related Issue** | [OMN-943](https://linear.app/omninode/issue/OMN-943) |
| **Implementation** | `src/omnibase_core/models/discovery/model_nodeintrospectionevent.py` |

---

## Document Purpose

This Architecture Decision Record defines how node registration is triggered in the ONEX system. It establishes that event-driven registration (via `NodeIntrospected` EVENT) is the canonical/default path, while command-driven registration (via `RegisterNodeRequested` COMMAND) is an optional/gated path for administrative use cases.

**Why this document exists**:
- To establish clear architectural boundaries between automatic and administrative registration flows
- To document the rationale for preferring event-driven registration as the canonical approach
- To define the execution shapes that govern registration orchestration
- To guide future implementation of the Registration Orchestrator

**When to reference this document**:
- When implementing registration orchestrator nodes
- When designing node lifecycle management
- When evaluating registration flow changes
- When troubleshooting registration issues

---

## Document Status and Maintenance

**Current Status**: ACCEPTED - Decision made, awaiting implementation

**Maintenance Model**: This is an **active specification** guiding implementation. Updates should occur when:
- Implementation reveals issues with the architecture
- New registration trigger types are needed
- The canonical/gated distinction needs refinement

**Supersession**: This document is NOT superseded. If the decision changes, this ADR should be:
1. Updated with a "SUPERSEDED" status indicator
2. Linked to the new ADR documenting the change
3. Retained for historical context

---

## Target Audience

| Audience | Use Case |
|----------|----------|
| **Backend Developers** | Implementing registration handlers and orchestrators |
| **Node Developers** | Understanding how their nodes will be registered |
| **Platform Engineers** | Configuring registration infrastructure |
| **Architects** | Evaluating registration flow design decisions |

---

## Executive Summary

Node registration in ONEX can be triggered through two distinct mechanisms:

1. **Event-Driven (Canonical)**: Nodes publish `NodeIntrospected` EVENTs on startup, which the Registration Orchestrator consumes, automatically registering the node.

2. **Command-Driven (Gated/Optional)**: Administrative systems send `RegisterNodeRequested` COMMANDs for explicit registration control.

This ADR establishes that **event-driven registration is the canonical default**, aligning with ONEX's event-driven architecture and automatic startup flows. Command-driven registration is reserved for administrative, exceptional, or gated scenarios.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Background](#background)
3. [Options Considered](#options-considered)
4. [Decision](#decision)
5. [Implementation](#implementation)
6. [Trade-offs](#trade-offs)
7. [References](#references)

---

## Problem Statement

The ONEX node registration system needs to support multiple entry points for triggering registration. Two primary mechanisms exist:

1. **Automatic startup flow**: Nodes announce themselves when they start
2. **Administrative control**: External systems explicitly request node registration

**Questions to resolve**:
- Which trigger mechanism should be the canonical/default path?
- How should the Registration Orchestrator handle both trigger types?
- What execution shapes govern these registration flows?
- When should each trigger mechanism be used?

---

## Background

### Existing Infrastructure

The ONEX codebase already has infrastructure supporting event-driven registration:

**Event Type Constant** (`src/omnibase_core/constants/event_types.py`):
```python
NODE_INTROSPECTION_EVENT = "node_introspection_event"
```

**Event Model** (`src/omnibase_core/models/discovery/model_nodeintrospectionevent.py`):
```python
class ModelNodeIntrospectionEvent(ModelOnexEvent):
    """
    Event published by nodes to announce their capabilities for discovery.

    This event is automatically published by the MixinEventDrivenNode when a node
    starts up, enabling other services to discover its capabilities.
    """
    event_type: str = Field(default=NODE_INTROSPECTION_EVENT)
    node_name: str
    version: ModelSemVer
    node_type: str  # effect, compute, reducer, orchestrator
    capabilities: ModelNodeCapability
    # ... additional fields
```

**Topic Taxonomy** (`docs/standards/onex_topic_taxonomy.md`):
```text
onex.registration.commands   # Registration commands (incl. RegisterNodeRequested)
onex.registration.events     # Registration events (incl. NodeIntrospected)
onex.registration.intents    # Registration coordination
onex.registration.snapshots  # Registration state snapshots
```

### Canonical Execution Shapes

The ONEX architecture defines allowed execution shapes (`docs/architecture/CANONICAL_EXECUTION_SHAPES.md`):

| Shape | Pattern | Valid? |
|-------|---------|--------|
| Shape 1 | Event -> Orchestrator | **Yes** |
| Shape 2 | Event -> Reducer | **Yes** |
| Shape 4 | Command -> Orchestrator | **Yes** |

Both Event->Orchestrator (Shape 1) and Command->Orchestrator (Shape 4) are valid execution shapes, confirming that the Registration Orchestrator can accept both trigger types.

### ONEX Event-Driven Philosophy

ONEX emphasizes event-driven architecture:
- Events represent facts that happened (immutable, past tense)
- Commands represent requests to perform actions (imperative, may fail)
- Orchestrators coordinate workflows triggered by events or commands

---

## Options Considered

### Option A: Event-Driven as Canonical (CHOSEN)

**Description**: `NodeIntrospected` EVENT is the default registration trigger. Nodes automatically publish this event on startup. `RegisterNodeRequested` COMMAND is available but gated/optional.

**Trigger Flow**:
```text
NODE STARTUP (Canonical):
┌─────────────┐     ┌───────────────────────┐     ┌─────────────────────┐
│    Node     │────▶│ NodeIntrospected      │────▶│    Registration     │
│  Startup    │     │    EVENT              │     │   Orchestrator [O]  │
│             │     │                       │     │                     │
│ (automatic) │     │ onex.registration.    │     │ Processes event,    │
│             │     │ events                │     │ registers node      │
└─────────────┘     └───────────────────────┘     └─────────────────────┘

ADMINISTRATIVE (Gated/Optional):
┌─────────────┐     ┌───────────────────────┐     ┌─────────────────────┐
│   Admin     │────▶│ RegisterNodeRequested │────▶│    Registration     │
│   System    │     │    COMMAND            │     │   Orchestrator [O]  │
│             │     │                       │     │                     │
│ (explicit)  │     │ onex.registration.    │     │ Validates, then     │
│             │     │ commands              │     │ registers node      │
└─────────────┘     └───────────────────────┘     └─────────────────────┘
```

**Pros**:
- Aligns with ONEX event-driven architecture philosophy
- Automatic startup flow requires no external coordination
- Events are immutable facts (node started, announced itself)
- Simpler operational model (nodes self-register)
- Commands reserved for exceptional/administrative cases

**Cons**:
- Less explicit control over registration timing
- Requires event bus infrastructure to be available at startup

### Option B: Command-Driven as Canonical

**Description**: `RegisterNodeRequested` COMMAND is the default. External systems must explicitly request registration.

**Pros**:
- More explicit control over what gets registered
- Registration can be gated by external policy
- Easier to implement admission control

**Cons**:
- Requires external coordination for basic node startup
- Violates ONEX event-driven philosophy
- Commands may be rejected, adding complexity
- Additional operational burden

### Option C: Dual Primary (No Preference)

**Description**: Both triggers are equally valid with no canonical preference.

**Pros**:
- Maximum flexibility

**Cons**:
- No clear guidance for implementers
- Potential for inconsistent behavior
- Harder to reason about system behavior

---

## Decision

**CHOSEN**: **Option A - Event-Driven as Canonical**

### Rationale

1. **Alignment with ONEX Philosophy**: ONEX is fundamentally event-driven. Events represent facts (the node started and announced itself). This is more natural than requiring an external command.

2. **Automatic Startup Flow**: Nodes should be able to register themselves without external coordination. This reduces operational complexity and aligns with container/orchestration patterns.

3. **Clear Semantic Distinction**:
   - **Events** = Facts about what happened (node announced itself)
   - **Commands** = Requests to perform actions (please register this node)

4. **Administrative Use Case Preservation**: Command-driven registration remains available for:
   - Pre-registration before node startup
   - Administrative bulk registration
   - Policy-gated registration flows
   - Re-registration after failures

5. **Execution Shape Compliance**: Both patterns are valid under ONEX canonical execution shapes (Event->Orchestrator and Command->Orchestrator).

### Registration Trigger Mapping

| Trigger | Message Category | Canonical/Gated | Use Case |
|---------|------------------|-----------------|----------|
| `NodeIntrospected` | EVENT | **Canonical** | Automatic node startup |
| `RegisterNodeRequested` | COMMAND | Gated/Optional | Administrative control |

### Orchestrator Behavior

The Registration Orchestrator MUST:

1. **Accept both triggers**: Handle `NodeIntrospected` events and `RegisterNodeRequested` commands
2. **Apply consistent validation**: Same validation logic regardless of trigger source
3. **Emit consistent events**: Both paths produce the same `NodeRegistered` event on success
4. **Support gating for commands**: Commands may have additional authorization checks

```text
Registration Orchestrator Processing:

                    ┌────────────────────────┐
                    │  Registration          │
                    │  Orchestrator [O]      │
                    └──────────┬─────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ NodeIntro-   │   │ RegisterNode │   │ (Future      │
    │ spected      │   │ Requested    │   │  triggers)   │
    │ EVENT        │   │ COMMAND      │   │              │
    └──────┬───────┘   └──────┬───────┘   └──────────────┘
           │                  │
           │  No extra gate   │  May require gate
           ▼                  ▼
    ┌──────────────────────────────────────────────────┐
    │           Common Registration Logic              │
    │  1. Validate node metadata                       │
    │  2. Check for duplicate registration             │
    │  3. Apply registration policy                    │
    │  4. Emit NodeRegistered event                    │
    └──────────────────────────────────────────────────┘
```

---

## Implementation

### Current State

**Implemented**:
- `NODE_INTROSPECTION_EVENT` constant in `src/omnibase_core/constants/event_types.py`
- `ModelNodeIntrospectionEvent` model in `src/omnibase_core/models/discovery/model_nodeintrospectionevent.py`
- `MixinIntrospectionPublisher` for publishing introspection events in `src/omnibase_core/mixins/mixin_introspection_publisher.py`
- Topic taxonomy for registration domain in `docs/standards/onex_topic_taxonomy.md`

**Planned/Reserved**:
- `RegisterNodeRequested` COMMAND model (not yet implemented)
- Registration Orchestrator node
- Gating logic for command-driven registration

### Naming Convention Mapping

| Semantic Name | Implementation |
|---------------|----------------|
| `NodeIntrospected` EVENT | `ModelNodeIntrospectionEvent` with `event_type=NODE_INTROSPECTION_EVENT` |
| `RegisterNodeRequested` COMMAND | Future: `ModelRegisterNodeRequestedCommand` |
| Registration Events Topic | `onex.registration.events` |
| Registration Commands Topic | `onex.registration.commands` |

### Message Flow Examples

**Canonical Flow (Event-Driven)**:
```python
# Node startup triggers introspection event
introspection_event = ModelNodeIntrospectionEvent.create_from_node_info(
    node_id=node_id,
    node_name="MyComputeNode",
    version=ModelSemVer(major=1, minor=0, patch=0),
    node_type="compute",
    actions=["transform", "validate"],
)

# Published to onex.registration.events
await event_bus.publish(
    topic="onex.registration.events",
    event=introspection_event,
)

# Registration Orchestrator consumes and processes
# Shape 1: Event -> Orchestrator
```

**Gated Flow (Command-Driven)**:
```python
# Administrative system sends registration command
# (Future implementation)
register_command = ModelRegisterNodeRequestedCommand(
    node_id=node_id,
    node_name="MyComputeNode",
    node_type="compute",
    requested_by="admin@example.com",
    reason="Pre-registration for deployment",
)

# Published to onex.registration.commands
await event_bus.publish(
    topic="onex.registration.commands",
    command=register_command,
)

# Registration Orchestrator consumes with additional gate checks
# Shape 4: Command -> Orchestrator
```

---

## Trade-offs

### Accepted Trade-offs

1. **Event Bus Dependency at Startup**
   - **Impact**: Nodes cannot register if event bus is unavailable
   - **Rationale**: Event bus is core ONEX infrastructure; if unavailable, other operations would also fail
   - **Mitigation**: Retry logic with exponential backoff in introspection publisher

2. **Less Explicit Control for Default Path**
   - **Impact**: Automatic registration may register nodes before policy checks
   - **Rationale**: Policy checks can be applied in orchestrator; most nodes should register automatically
   - **Mitigation**: Command-driven path available for gated scenarios

3. **Two Code Paths in Orchestrator**
   - **Impact**: Orchestrator must handle both events and commands
   - **Rationale**: Both are valid ONEX execution shapes; shared validation logic minimizes duplication
   - **Mitigation**: Factor common logic into shared functions

### Benefits Realized

1. **Alignment with ONEX Architecture**: Event-driven as default matches ONEX philosophy
2. **Operational Simplicity**: Nodes self-register without external coordination
3. **Clear Semantic Model**: Events for facts, commands for requests
4. **Flexibility Preserved**: Administrative use cases still supported via commands
5. **Execution Shape Compliance**: Both paths follow canonical ONEX patterns

---

## References

### Related Documentation

- **CANONICAL_EXECUTION_SHAPES.md**: Defines allowed Event->Orchestrator and Command->Orchestrator patterns
- **onex_topic_taxonomy.md**: Defines `onex.registration.{commands,events,intents,snapshots}` topics
- **ONEX_FOUR_NODE_ARCHITECTURE.md**: Overall ONEX architecture
- **onex_terminology.md**: Canonical definitions of Event, Command, Orchestrator

### Related Code

- **Event Constant**: `src/omnibase_core/constants/event_types.py` - `NODE_INTROSPECTION_EVENT`
- **Event Model**: `src/omnibase_core/models/discovery/model_nodeintrospectionevent.py` - `ModelNodeIntrospectionEvent`
- **Introspection Publisher**: `src/omnibase_core/mixins/mixin_introspection_publisher.py` - `MixinIntrospectionPublisher`
- **Discovery Tests**: `tests/unit/models/discovery/test_discovery_events.py`

### Related Issues

- **OMN-943**: Define canonical node registration event structure

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-19 | 1.0 | Claude Code | Initial ADR documenting registration trigger architecture |

---

**Document Status**: ACCEPTED - Decision documented, implementation pending
**Verification**: References validated against codebase as of 2025-12-19
