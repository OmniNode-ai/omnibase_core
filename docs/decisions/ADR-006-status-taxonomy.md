> **Navigation**: [Home](../index.md) > [Decisions](README.md) > ADR-006

# ADR-006: Status Taxonomy and Categorical Organization

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Status** | 🟢 ACCEPTED |
| **Created** | 2026-01-12 |
| **Last Updated** | 2026-01-14 |
| **Author** | ONEX Framework Team |
| **Related Issue** | OMN-1296 |
| **Correlation ID** | `b8f4e2c1-7d3a-4f9e-a5b6-8c1d2e3f4a5b` |

## Executive Summary

This ADR establishes a formal taxonomy for the 57+ status enums in omnibase_core, organizing them into semantic categories with canonical representatives. This taxonomy gates future consolidation work (OMN-1310, OMN-1311) and provides clear guidance on when to use each status category.

## Target Audience

| Audience | Use Case |
|----------|----------|
| **Node Developers** | Selecting the appropriate status enum for their node type |
| **API Designers** | Understanding status semantics for return types |
| **Code Reviewers** | Evaluating status enum usage in PRs |
| **Future Contributors** | Understanding the status architecture before consolidation |

---

## Problem Statement

The omnibase_core codebase contains 57+ status-related enums that have evolved organically. This creates:

1. **Ambiguity**: Which status enum should be used for a given use case?
2. **Redundancy**: Multiple enums with overlapping semantics
3. **Inconsistency**: Similar concepts with different value sets
4. **Cognitive Load**: Developers must navigate many similar enums

Before any consolidation can occur, we need a documented taxonomy that:
- Categorizes existing enums by semantic purpose
- Identifies canonical enums per category
- Documents legitimate exceptions that should remain separate
- Provides clear usage guidance

---

## Decision

### Status Categories

We establish **six primary status categories** based on semantic purpose:

| Category | Purpose | Canonical Enum |
|----------|---------|----------------|
| **Execution** | Track task/node execution lifecycle | `EnumExecutionStatus` |
| **Operation** | Track service operation outcomes | `EnumOperationStatus` |
| **Workflow** | Track multi-step workflow progression | `EnumWorkflowStatus` |
| **Health** | Report system/service health state | `EnumHealthStatus` |
| **Lifecycle** | Track entity maturity/availability | `EnumLifecycle` |
| **Registration** | Track registry entry states | `EnumRegistryEntryStatus` |

Additionally, we establish **three severity categories**:

| Category | Purpose | Canonical Enum | Status |
|----------|---------|----------------|--------|
| **Issue Severity** | Classify violation/issue severity | `EnumSeverity` | Canonical |
| **Log Severity** | RFC 5424 logging levels | `EnumSeverityLevel` | Keep Separate |
| **Business Impact** | Business impact classification | `EnumImpactSeverity` | Keep Separate |

> **Note on Severity Enums**: The three severity enums serve distinct purposes:
> - **`EnumSeverity`** (Canonical): General-purpose severity classification for issues, violations, findings, and diagnostic messages. Uses a 6-level scale (DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL) with numeric ordering for comparison. Use this for validation results, code analysis findings, and any domain-specific severity classification.
> - **`EnumSeverityLevel`** (Keep Separate): RFC 5424-compliant logging levels with 11 values including TRACE, NOTICE, ALERT, and EMERGENCY. Use this when building logging infrastructure that requires strict RFC 5424 compliance or numeric level filtering.
> - **`EnumImpactSeverity`** (Keep Separate): Business impact classification using a 5-level scale (CRITICAL, HIGH, MEDIUM, LOW, MINIMAL). Use this when assessing business or operational impact of changes, outages, or issues.
>
> **Key Distinction**: When you call `logger.warning()` or `logger.info()`, you are NOT using any of these enums - you are using Python's logging module directly. These enums are for programmatic severity classification in your application logic.

---

### Category Definitions

#### 1. Execution Status (`EnumExecutionStatus`)

**Purpose**: Track the execution lifecycle of tasks, nodes, and individual operations.

**Canonical Values**:
```python
class EnumExecutionStatus(str, Enum):
    PENDING = "pending"      # Queued, not yet started
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Finished execution (neutral)
    SUCCESS = "success"      # Finished with success
    FAILED = "failed"        # Finished with failure
    SKIPPED = "skipped"      # Intentionally not executed
    CANCELLED = "cancelled"  # Terminated by external request
    TIMEOUT = "timeout"      # Exceeded time limit
    PARTIAL = "partial"      # Some steps succeeded, others failed
```

**Value Classifications**:
- **Active States**: `PENDING`, `RUNNING`
- **Terminal Success**: `COMPLETED`, `SUCCESS`
- **Terminal Failure**: `FAILED`, `TIMEOUT`
- **Terminal Neutral**: `SKIPPED`, `CANCELLED`, `PARTIAL`

**When to Use**: Node execution, task processing, batch operations, pipeline steps.

**Location**: `src/omnibase_core/enums/enum_execution_status.py`

---

#### 2. Operation Status (`EnumOperationStatus`)

**Purpose**: Track the outcome of discrete service operations (API calls, CRUD operations).

**Canonical Values**:
```python
class EnumOperationStatus(str, Enum):
    SUCCESS = "success"        # Operation completed successfully
    FAILED = "failed"          # Operation failed
    IN_PROGRESS = "in_progress"  # Operation ongoing
    CANCELLED = "cancelled"    # Operation cancelled
    PENDING = "pending"        # Operation queued
    TIMEOUT = "timeout"        # Operation timed out
```

**When to Use**: Service manager operations, API responses, repository operations.

**Distinction from Execution**: Operation status is for discrete, atomic operations. Execution status is for longer-running tasks with richer lifecycle tracking.

**Location**: `src/omnibase_core/enums/enum_operation_status.py`

---

#### 3. Workflow Status (`EnumWorkflowStatus`)

**Purpose**: Track multi-step workflow progression.

**Canonical Values**:
```python
class EnumWorkflowStatus(str, Enum):
    PENDING = "pending"      # Workflow not yet started
    RUNNING = "running"      # Workflow in progress
    COMPLETED = "completed"  # Workflow finished successfully
    FAILED = "failed"        # Workflow failed
    CANCELLED = "cancelled"  # Workflow cancelled
    SIMULATED = "simulated"  # Workflow executed in simulation mode
```

**When to Use**: ORCHESTRATOR nodes, multi-step pipelines, workflow coordination.

**Location**: `src/omnibase_core/enums/enum_workflow_status.py`

---

#### 4. Health Status (`EnumHealthStatus`)

**Purpose**: Report the current health state of systems, services, or components.

**Canonical Values**:
```python
class EnumHealthStatus(str, Enum):
    HEALTHY = "healthy"          # Fully operational
    DEGRADED = "degraded"        # Operational with reduced capacity
    UNHEALTHY = "unhealthy"      # Not operational
    CRITICAL = "critical"        # Severe issues requiring immediate attention
    UNKNOWN = "unknown"          # Health cannot be determined
    WARNING = "warning"          # Potential issues detected
    UNREACHABLE = "unreachable"  # Cannot connect to determine health
    AVAILABLE = "available"      # Service is available
    UNAVAILABLE = "unavailable"  # Service is unavailable
    ERROR = "error"              # Health check encountered error
```

**Health Classifications**:
- **Operational**: `HEALTHY`, `DEGRADED`, `AVAILABLE`
- **Non-Operational**: `UNHEALTHY`, `CRITICAL`, `UNAVAILABLE`, `UNREACHABLE`, `ERROR`
- **Indeterminate**: `UNKNOWN`, `WARNING`

**When to Use**: Health checks, monitoring endpoints, service discovery, circuit breakers.

**Location**: `src/omnibase_core/enums/enum_health_status.py`

---

#### 5. Lifecycle Status (`EnumLifecycle`)

**Purpose**: Track the maturity/availability lifecycle of entities (nodes, features, APIs).

**Canonical Values**:
```python
class EnumLifecycle(str, Enum):
    DRAFT = "draft"            # Under development, not ready for use
    ACTIVE = "active"          # Ready for production use
    DEPRECATED = "deprecated"  # Still functional, but scheduled for removal
    ARCHIVED = "archived"      # No longer functional, kept for history
```

**When to Use**: Node metadata, feature flags, API versioning, documentation status.

**Location**: `src/omnibase_core/enums/enum_metadata.py`

---

#### 6. Registration Status (`EnumRegistryEntryStatus`)

**Purpose**: Track the state of entries in discovery/registry systems.

**Canonical Values**:
```python
class EnumRegistryEntryStatus(str, Enum):
    EPHEMERAL = "ephemeral"  # Temporary registration
    ONLINE = "online"        # Registered and available
    VALIDATED = "validated"  # Registration verified
```

**When to Use**: Service discovery, node registration, tool registry.

**Location**: `src/omnibase_core/enums/enum_registry_entry_status.py`

---

### Severity Enums (Three Categories)

#### Issue Severity (`EnumSeverity`) - Canonical

**Purpose**: Classify the severity of violations, issues, and findings using a standard 6-level scale aligned with logging conventions.

**Values**:
```python
class EnumSeverity(str, Enum):
    DEBUG = "debug"        # Detailed diagnostic information for debugging
    INFO = "info"          # General operational information
    WARNING = "warning"    # Unexpected situation that doesn't prevent operation
    ERROR = "error"        # Operation failed but system can continue
    CRITICAL = "critical"  # Serious error requiring attention, system can continue degraded
    FATAL = "fatal"        # Unrecoverable error, system must terminate
```

**When to Use**: Validation findings, code analysis results, issue classification, diagnostic messages. **Not for log level selection** - when you call `logger.warning()` or `logger.info()`, you are not using `EnumSeverity`. For logging infrastructure requiring numeric level ordering, use `EnumSeverityLevel`.

**Location**: `src/omnibase_core/enums/enum_severity.py`

---

#### Log Severity (`EnumSeverityLevel`) - Keep Separate

**Purpose**: RFC 5424-inspired logging levels with numeric ordering.

**Values**:
```python
class EnumSeverityLevel(str, Enum):
    EMERGENCY = "emergency"  # 80 - System unusable
    ALERT = "alert"          # 70 - Immediate action required
    CRITICAL = "critical"    # 60 - Critical conditions
    ERROR = "error"          # 50 - Error conditions
    WARNING = "warning"      # 40 - Warning conditions
    NOTICE = "notice"        # 35 - Normal but significant
    INFO = "info"            # 30 - Informational
    DEBUG = "debug"          # 20 - Debug messages
    TRACE = "trace"          # 10 - Detailed debug
    FATAL = "fatal"          # 80 - Alias for EMERGENCY
    WARN = "warn"            # 40 - Alias for WARNING
```

**Why Keep Separate**: RFC 5424 compliance, numeric level ordering, logging framework integration.

**Location**: `src/omnibase_core/enums/enum_severity_level.py`

---

#### Business Impact (`EnumImpactSeverity`) - Keep Separate

**Purpose**: Classify business impact of issues or changes.

**Values**:
```python
class EnumImpactSeverity(str, Enum):
    CRITICAL = "critical"  # Business-critical impact
    HIGH = "high"          # Significant business impact
    MEDIUM = "medium"      # Moderate business impact
    LOW = "low"            # Minor business impact
    MINIMAL = "minimal"    # Negligible business impact
```

**Why Keep Separate**: Different semantic domain (business vs. technical), different usage context.

**Location**: `src/omnibase_core/enums/enum_impact_severity.py`

---

## Usage Guidelines

### Selecting the Right Category

```text
Question                                          -> Category
-----------------------------------------------------------
"Has the task/node finished executing?"           -> Execution
"Did the API call succeed?"                       -> Operation
"Where is the workflow in its process?"           -> Workflow
"Is the service healthy?"                         -> Health
"Is this feature production-ready?"               -> Lifecycle
"Is this node registered in the discovery?"       -> Registration
"How severe is this code violation?"              -> Issue Severity
"What log level should this message have?"        -> Log Severity
"What is the business impact of this change?"     -> Business Impact
```

### Category vs. Enum Mapping

When you identify your category, use the canonical enum:

| If you need... | Use... |
|----------------|--------|
| Execution tracking | `EnumExecutionStatus` |
| Operation result | `EnumOperationStatus` |
| Workflow progress | `EnumWorkflowStatus` |
| Health monitoring | `EnumHealthStatus` |
| Entity lifecycle | `EnumLifecycle` |
| Registry state | `EnumRegistryEntryStatus` |
| Issue severity | `EnumSeverity` |
| Log levels | `EnumSeverityLevel` |
| Business impact | `EnumImpactSeverity` |

---

## Scope Limitations

This ADR explicitly **does not** cover:

1. **FSM Transition Rules**: Valid state transitions (e.g., `PENDING -> RUNNING -> COMPLETED`) are intentionally deferred to a future ADR. This ADR defines what states exist, not how they relate.

2. **Cross-Category Root Enum**: A unified `StatusBase` or `EnumStatus` root is not established. Each category remains independent.

3. **Consolidation Implementation**: The actual merging of redundant enums (e.g., `EnumExecutionStatusV2` -> `EnumExecutionStatus`) is tracked in OMN-1310/OMN-1311.

4. **Mapping Rules**: Formal mapping between categories (e.g., how `EnumExecutionStatus.FAILED` maps to `EnumHealthStatus`) is deferred.

---

## Consequences

### Positive

- **Clarity**: Clear taxonomy enables consistent status enum selection
- **Foundation**: Establishes basis for future consolidation work
- **Documentation**: Developers have authoritative reference for status semantics
- **Reduced Ambiguity**: Category definitions eliminate "which enum?" confusion

### Neutral

- **Learning Curve**: Developers must learn the taxonomy
- **Incremental**: Does not immediately reduce enum count

### Negative

- **Partial Enforcement**: Enum governance checker (`checker_enum_governance.py`) is implemented and runs in pre-commit hooks, but currently operates in **warning mode** (uses `|| true` to avoid blocking commits). The checker reports violations but does not fail builds. It will become a blocking check after existing violations are addressed (tracked in OMN-1296).
- **Deferred Work**: FSM transitions and consolidation still required

---

## Future Work

| ADR | Topic | Dependency |
|-----|-------|------------|
| ADR-007 (planned) | FSM Transition Semantics | This ADR |
| OMN-1310 | Severity Enum Consolidation | This ADR |
| OMN-1311 | Status Enum Consolidation | This ADR |

---

## References

### Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [CANONICAL_EXECUTION_SHAPES.md](../architecture/CANONICAL_EXECUTION_SHAPES.md)

### Enum Locations

| Enum | Location |
|------|----------|
| `EnumExecutionStatus` | `src/omnibase_core/enums/enum_execution_status.py` |
| `EnumOperationStatus` | `src/omnibase_core/enums/enum_operation_status.py` |
| `EnumWorkflowStatus` | `src/omnibase_core/enums/enum_workflow_status.py` |
| `EnumHealthStatus` | `src/omnibase_core/enums/enum_health_status.py` |
| `EnumLifecycle` | `src/omnibase_core/enums/enum_metadata.py` |
| `EnumRegistryEntryStatus` | `src/omnibase_core/enums/enum_registry_entry_status.py` |
| `EnumSeverity` | `src/omnibase_core/enums/enum_severity.py` |
| `EnumSeverityLevel` | `src/omnibase_core/enums/enum_severity_level.py` |
| `EnumImpactSeverity` | `src/omnibase_core/enums/enum_impact_severity.py` |

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-12 | 1.0 | ONEX Team | Initial taxonomy proposal |
| 2026-01-14 | 1.1 | ONEX Team | Enhanced severity enum documentation with clearer distinctions between EnumSeverity, EnumSeverityLevel, and EnumImpactSeverity (PR #378 review) |

---

**Next Review**: 2026-02-12
