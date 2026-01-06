# Memory Snapshots Architecture - omnimemory

**Status**: Active

## Overview

Memory snapshots are the core persistence mechanism for the omnimemory system, providing structured storage of agent experiences, decisions, and failures. Each snapshot captures a point-in-time record of memory state, enabling agents to learn from past interactions, make informed decisions, and handle failures systematically.

The omnimemory system uses three classification enums to organize and query memory snapshots:

- **EnumSubjectType**: Classifies memory ownership (who owns this memory)
- **EnumDecisionType**: Classifies decision types (what kind of decision was made)
- **EnumFailureType**: Classifies failure types (what went wrong)

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        Memory Snapshot                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Subject Type   │  │  Decision Type  │  │  Failure Type   │     │
│  │  (Ownership)    │  │  (Analysis)     │  │  (Retry Logic)  │     │
│  │                 │  │                 │  │                 │     │
│  │  AGENT          │  │  MODEL_SELECTION│  │  TIMEOUT        │     │
│  │  USER           │  │  ROUTE_CHOICE   │  │  RATE_LIMIT     │     │
│  │  WORKFLOW       │  │  TOOL_SELECTION │  │  VALIDATION_ERR │     │
│  │  PROJECT        │  │  RETRY_STRATEGY │  │  MODEL_ERROR    │     │
│  │  ...            │  │  ...            │  │  ...            │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
├─────────────────────────────────────────────────────────────────────┤
│                     Payload / Context Data                          │
│                     (Structured JSON/Pydantic)                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Subject Types (EnumSubjectType)

Subject types classify the ownership and scope of memory snapshots, enabling multi-tenant memory management across different entity types.

### Entity Types

Entity types represent memory owned by specific actors in the system:

| Value | Description | Use Case |
|-------|-------------|----------|
| `AGENT` | Memory owned by an AI agent | Agent learning, preferences, capabilities |
| `USER` | Memory owned by a human user | User preferences, interaction history |
| `SERVICE` | Memory owned by a system service | Service configuration, operational state |

### Scope Types

Scope types represent memory bound to a specific context or execution scope:

| Value | Description | Use Case |
|-------|-------------|----------|
| `WORKFLOW` | Memory scoped to a workflow execution | Workflow state, intermediate results |
| `PROJECT` | Memory scoped to a project context | Project-specific knowledge, configurations |
| `ORG` | Memory scoped to an organization | Organizational policies, shared knowledge |
| `TASK` | Memory scoped to a specific task | Task-specific context, progress tracking |
| `SESSION` | Ephemeral session memory | Temporary context, not persisted long-term |
| `CORPUS` | Memory associated with a knowledge corpus | Document collections, RAG contexts |

### Special Types

| Value | Description | Use Case |
|-------|-------------|----------|
| `CUSTOM` | Forward-compatibility escape hatch | New subject types not yet in enum |

### Helper Methods

```python
from omnibase_core.enums import EnumSubjectType

# Check if subject type is an entity (agent, user, service)
EnumSubjectType.AGENT.is_entity_type()      # True
EnumSubjectType.WORKFLOW.is_entity_type()   # False

# Check if subject type is a scope (workflow, project, etc.)
EnumSubjectType.WORKFLOW.is_scope_type()    # True
EnumSubjectType.AGENT.is_scope_type()       # False

# Check if memory is typically persistent
EnumSubjectType.AGENT.is_persistent()       # True
EnumSubjectType.SESSION.is_persistent()     # False
```

## Decision Types (EnumDecisionType)

Decision types classify agent decisions recorded in memory snapshots, enabling systematic analysis and reporting of decision-making patterns.

### Selection Decisions

Decisions involving choosing from multiple options:

| Value | Description | Use Case |
|-------|-------------|----------|
| `MODEL_SELECTION` | Which AI model to use | LLM routing, capability matching |
| `ROUTE_CHOICE` | Routing or path selection | Workflow branching, API routing |
| `TOOL_SELECTION` | Which tool or capability to invoke | Function calling, tool use |
| `PARAMETER_CHOICE` | Parameter values or configuration | Configuration tuning, hyperparameters |

### Control Flow Decisions

Decisions affecting execution flow:

| Value | Description | Use Case |
|-------|-------------|----------|
| `RETRY_STRATEGY` | Retry behavior after failure | Backoff strategies, retry limits |
| `ESCALATION` | Escalate to human oversight | Human-in-the-loop triggers |
| `EARLY_TERMINATION` | Terminate early (success or abort) | Short-circuit evaluation, abort conditions |

### Special Types

| Value | Description | Use Case |
|-------|-------------|----------|
| `CUSTOM` | Forward-compatibility escape hatch | New decision types not yet in enum |

### Helper Methods

```python
from omnibase_core.enums import EnumDecisionType

# Check if decision typically terminates a workflow
EnumDecisionType.EARLY_TERMINATION.is_terminal_decision()  # True
EnumDecisionType.MODEL_SELECTION.is_terminal_decision()    # False

# Check if decision involves selecting from options
EnumDecisionType.MODEL_SELECTION.is_selection_decision()   # True
EnumDecisionType.ESCALATION.is_selection_decision()        # False
```

## Failure Types (EnumFailureType)

Failure types classify failures recorded in memory snapshots, enabling systematic analysis of failure patterns and informing retry logic.

### Retryable Failures

Failures that may be resolved by retrying:

| Value | Description | Retry Strategy |
|-------|-------------|----------------|
| `TIMEOUT` | Operation exceeded time limit | Increase timeout, retry with backoff |
| `RATE_LIMIT` | Rate limit exceeded | Wait and retry with exponential backoff |
| `EXTERNAL_SERVICE` | External service/API failure | Retry with circuit breaker |
| `MODEL_ERROR` | AI model error (generation failure, context overflow) | Retry with different model or reduced context |

### Non-Retryable Failures

Failures that typically require intervention:

| Value | Description | Resolution |
|-------|-------------|------------|
| `INVARIANT_VIOLATION` | Required invariant or constraint violated | Fix input data or logic |
| `VALIDATION_ERROR` | Input or output validation failed | Fix validation issues |
| `COST_EXCEEDED` | Operation exceeded cost budget | Adjust budget or optimize |

### Special Types

| Value | Description | Use Case |
|-------|-------------|----------|
| `UNKNOWN` | Unclassified failure | Unexpected failure modes, requires investigation |

### Helper Methods

```python
from omnibase_core.enums import EnumFailureType

# Check if failure is typically retryable
EnumFailureType.TIMEOUT.is_retryable()             # True
EnumFailureType.INVARIANT_VIOLATION.is_retryable() # False

# Check if failure is related to resource constraints
EnumFailureType.COST_EXCEEDED.is_resource_related()     # True
EnumFailureType.VALIDATION_ERROR.is_resource_related()  # False
```

## Usage Examples

### Recording a Decision in Memory

```python
from pydantic import BaseModel
from omnibase_core.enums import EnumSubjectType, EnumDecisionType

class DecisionSnapshot(BaseModel):
    """Memory snapshot for a decision event."""
    subject_type: EnumSubjectType
    subject_id: str
    decision_type: EnumDecisionType
    decision_rationale: str
    options_considered: list[str]
    selected_option: str

# Record a model selection decision by an agent
snapshot = DecisionSnapshot(
    subject_type=EnumSubjectType.AGENT,
    subject_id="agent-001",
    decision_type=EnumDecisionType.MODEL_SELECTION,
    decision_rationale="Selected GPT-4 for complex reasoning task",
    options_considered=["gpt-3.5-turbo", "gpt-4", "claude-3"],
    selected_option="gpt-4"
)
```

### Recording a Failure in Memory

```python
from pydantic import BaseModel
from datetime import datetime
from omnibase_core.enums import EnumSubjectType, EnumFailureType

class FailureSnapshot(BaseModel):
    """Memory snapshot for a failure event."""
    subject_type: EnumSubjectType
    subject_id: str
    failure_type: EnumFailureType
    error_message: str
    timestamp: datetime
    retry_count: int

# Record a timeout failure during workflow execution
snapshot = FailureSnapshot(
    subject_type=EnumSubjectType.WORKFLOW,
    subject_id="workflow-execution-123",
    failure_type=EnumFailureType.TIMEOUT,
    error_message="API call exceeded 30s timeout",
    timestamp=datetime.now(),
    retry_count=2
)

# Use helper method to determine retry behavior
if snapshot.failure_type.is_retryable():
    # Implement retry logic
    pass
```

### Filtering Memory by Subject Type

```python
from omnibase_core.enums import EnumSubjectType

def get_persistent_memories(snapshots: list[dict]) -> list[dict]:
    """Filter to only persistent memory types."""
    return [
        s for s in snapshots
        if EnumSubjectType(s["subject_type"]).is_persistent()
    ]

def get_entity_memories(snapshots: list[dict]) -> list[dict]:
    """Filter to entity-owned memories (agents, users, services)."""
    return [
        s for s in snapshots
        if EnumSubjectType(s["subject_type"]).is_entity_type()
    ]
```

### Analyzing Decision Patterns

```python
from collections import Counter
from omnibase_core.enums import EnumDecisionType

def analyze_decision_patterns(decisions: list[dict]) -> dict:
    """Analyze decision patterns from memory snapshots."""
    decision_types = [d["decision_type"] for d in decisions]
    type_counts = Counter(decision_types)

    # Categorize by decision characteristics
    selection_count = sum(
        count for dt, count in type_counts.items()
        if EnumDecisionType(dt).is_selection_decision()
    )
    terminal_count = sum(
        count for dt, count in type_counts.items()
        if EnumDecisionType(dt).is_terminal_decision()
    )

    return {
        "total_decisions": len(decisions),
        "selection_decisions": selection_count,
        "terminal_decisions": terminal_count,
        "by_type": dict(type_counts)
    }
```

### Retry Logic Based on Failure Type

```python
from omnibase_core.enums import EnumFailureType

def get_retry_config(failure_type: EnumFailureType) -> dict:
    """Get retry configuration based on failure type."""
    if not failure_type.is_retryable():
        return {"should_retry": False}

    # Resource-related failures need longer backoff
    if failure_type.is_resource_related():
        return {
            "should_retry": True,
            "max_retries": 3,
            "base_delay_seconds": 5,
            "exponential_backoff": True
        }

    # Other retryable failures (external service, model error)
    return {
        "should_retry": True,
        "max_retries": 5,
        "base_delay_seconds": 1,
        "exponential_backoff": True
    }
```

## Design Principles

### 1. Type Safety

All enum values are string-backed (`str, Enum`) for JSON serialization compatibility while maintaining type safety in Python code.

```python
# String coercion works with Pydantic
class Snapshot(BaseModel):
    subject_type: EnumSubjectType

snapshot = Snapshot(subject_type="agent")  # Works
snapshot.subject_type == EnumSubjectType.AGENT  # True
```

### 2. Forward Compatibility

Each enum includes a `CUSTOM` or `UNKNOWN` value as an escape hatch for new types not yet added to the enum:

```python
# Handle unknown subject types gracefully
if subject_type == EnumSubjectType.CUSTOM:
    # Log and process with custom handling
    pass
```

### 3. Semantic Helper Methods

Helper methods like `is_retryable()`, `is_entity_type()`, and `is_terminal_decision()` encapsulate business logic about enum values, keeping this knowledge centralized:

```python
# Business logic is in the enum, not scattered across codebase
if failure.is_retryable():
    retry_operation()
```

### 4. Validation Support

The `is_valid()` class method enables safe parsing from external input:

```python
user_input = request.get("failure_type", "unknown")
if EnumFailureType.is_valid(user_input):
    failure_type = EnumFailureType(user_input)
else:
    failure_type = EnumFailureType.UNKNOWN
```

## See Also

### Source Files

- `src/omnibase_core/enums/enum_subject_type.py` - Subject type enum implementation
- `src/omnibase_core/enums/enum_decision_type.py` - Decision type enum implementation
- `src/omnibase_core/enums/enum_failure_type.py` - Failure type enum implementation

### Related Documentation

- [Event-Driven Architecture](../patterns/EVENT_DRIVEN_ARCHITECTURE.md) - Event patterns for memory events
- [Architecture Overview](../architecture/overview.md) - ONEX framework architecture
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node types and patterns

---

**Last Updated**: 2025-01-06 | **Version**: 0.6.0
