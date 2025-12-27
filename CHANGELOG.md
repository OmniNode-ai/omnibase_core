# Changelog

All notable changes to the ONEX Core Framework (omnibase_core) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ⚠️ BREAKING CHANGES

#### Workflow Contract Model Hardening [OMN-654]

The following workflow contract models now enforce **immutability** (`frozen=True`) and **strict field validation** (`extra="forbid"`):

| Model | Changes Applied |
|-------|-----------------|
| `ModelWorkflowDefinition` | Added `frozen=True`, `extra="forbid"` |
| `ModelWorkflowDefinitionMetadata` | Added `frozen=True`, `extra="forbid"` |
| `ModelWorkflowStep` | Added `extra="forbid"` (already had `frozen=True`) |
| `ModelCoordinationRules` | Added `frozen=True`, `extra="forbid"` |
| `ModelExecutionGraph` | Added `frozen=True`, `extra="forbid"` |
| `ModelWorkflowNode` | Added `frozen=True`, `extra="forbid"` |

**Impact**:
- Code that **mutates these models after creation** will now raise `pydantic.ValidationError`
- Code that **passes unknown fields** to these models will now raise `pydantic.ValidationError`

**Thread Safety Benefits**:

Since these models are now `frozen=True`, they are **inherently thread-safe for reads**:

| Operation | Thread-Safe? | Notes |
|-----------|-------------|-------|
| Reading model attributes | Yes | No mutation possible after creation |
| Sharing models across threads | Yes | Immutable objects are safe to share |
| Creating modified copies with `model_copy()` | Yes | Creates new instance, no shared mutable state |
| Passing models between async tasks | Yes | No race conditions on immutable data |

This aligns with the ONEX thread safety model documented in [docs/guides/THREADING.md](docs/guides/THREADING.md). Workflow contract models now join other frozen models (like `ModelComputeInput`, `ModelReducerInput`, etc.) in being safe for concurrent access without synchronization.

**Migration Guide**:

**1. Direct Mutation to Immutable Copies**

```python
# Before (v0.3.x) - Direct mutation was possible
workflow = ModelWorkflowDefinition(...)
workflow.version = new_version  # ❌ Now raises pydantic.ValidationError

# After (v0.4.0+) - Use model_copy() for modifications
workflow = ModelWorkflowDefinition(...)
updated_workflow = workflow.model_copy(update={"version": new_version})  # ✅ Correct

# Multiple field updates in one call
updated = original.model_copy(update={
    "version": new_version,
    "workflow_metadata": new_metadata,
})
```

**2. Handling Extra Fields**

```python
# Before (v0.3.x) - Extra fields might have been silently ignored
definition = ModelWorkflowDefinition(
    version=version,
    workflow_metadata=metadata,
    execution_graph=graph,
    custom_field="value"  # ❌ Now raises pydantic.ValidationError
)

# After (v0.4.0+) - Only declared fields allowed
definition = ModelWorkflowDefinition(
    version=version,
    workflow_metadata=metadata,
    execution_graph=graph,
    # custom_field removed - use proper extension mechanisms instead
)

# If you need custom metadata, use designated fields:
metadata = ModelWorkflowDefinitionMetadata(
    version=version,
    workflow_name="my-workflow",
    workflow_version=workflow_version,
    description="Description with any custom info you need",
)
```

**3. Nested Model Updates**

```python
# For deeply nested updates, rebuild from the inside out:
original = ModelWorkflowDefinition(...)

# Update nested metadata
new_metadata = original.workflow_metadata.model_copy(
    update={"description": "Updated description"}
)

# Create new definition with updated metadata
updated = original.model_copy(update={"workflow_metadata": new_metadata})
```

**4. Pattern for Workflow Builders**

```python
# If you have a builder pattern that relied on mutation, convert to accumulation:

# Before (v0.3.x) - Mutable builder
class WorkflowBuilder:
    def __init__(self):
        self.workflow = ModelWorkflowDefinition(...)

    def set_timeout(self, ms: int):
        self.workflow.timeout_ms = ms  # ❌ No longer works

# After (v0.4.0+) - Immutable builder with accumulated state
class WorkflowBuilder:
    def __init__(self):
        self._updates: dict[str, Any] = {}
        self._base_config = {...}

    def set_timeout(self, ms: int) -> "WorkflowBuilder":
        self._updates["timeout_ms"] = ms
        return self

    def build(self) -> ModelWorkflowDefinition:
        return ModelWorkflowDefinition(**{**self._base_config, **self._updates})
```

**5. Testing Code Updates**

```python
# Tests that mutated models need updating:

# Before (v0.3.x)
def test_workflow_processing():
    workflow = create_workflow()
    workflow.status = "completed"  # ❌ No longer works
    assert workflow.status == "completed"

# After (v0.4.0+)
def test_workflow_processing():
    workflow = create_workflow()
    completed_workflow = workflow.model_copy(update={"status": "completed"})
    assert completed_workflow.status == "completed"
```

**Quick Migration Checklist**:

- [ ] Search codebase for direct attribute assignment to workflow contract models
- [ ] Replace direct mutations with `model_copy(update={...})` calls
- [ ] Remove any extra fields being passed to model constructors
- [ ] Update builder patterns to accumulate state rather than mutate
- [ ] Run tests to verify `pydantic.ValidationError` is not raised unexpectedly
- [ ] Verify thread safety requirements are met (frozen models are now safe to share)

#### Security: Deprecated MD5/SHA-1 Hash Algorithms [OMN-699]

`ModelSessionAffinity` now deprecates MD5 and SHA-1 hash algorithms due to known cryptographic weaknesses. These algorithms are auto-converted to SHA-256 with a `DeprecationWarning`. **Support will be fully removed in v0.6.0.**

**Impact**:
- Configurations with `hash_algorithm: "md5"` or `hash_algorithm: "sha1"` will emit `DeprecationWarning` and auto-convert to SHA-256
- Running with `-W error::DeprecationWarning` will convert these to errors (useful for CI/CD validation)
- Only SHA-256, SHA-384, and SHA-512 are recommended for new configurations
- **v0.6.0**: MD5/SHA-1 will be fully removed and raise `pydantic.ValidationError`

**Migration**:
```python
# Current behavior (v0.5.0) - Deprecation warning + auto-conversion
affinity = ModelSessionAffinity(hash_algorithm="md5")   # ⚠️ Warning, converts to sha256
affinity = ModelSessionAffinity(hash_algorithm="sha1")  # ⚠️ Warning, converts to sha256

# Recommended - Use secure algorithms (no warnings)
affinity = ModelSessionAffinity(hash_algorithm="sha256")  # ✅ Default, recommended
affinity = ModelSessionAffinity(hash_algorithm="sha384")  # ✅ Stronger
affinity = ModelSessionAffinity(hash_algorithm="sha512")  # ✅ Strongest
```

**Recommendation**: Update configurations to use SHA-256 (default) before v0.6.0. Use SHA-384 or SHA-512 for high-security environments.

### Changed
- Renamed `ModelOnexEnvelopeV1` to `ModelOnexEnvelope` ()
- Renamed fields: `event_id`→`envelope_id`, `source_service`→`source_node`, `event_type`→`operation`
- Added new fields: `causation_id`, `target_node`, `handler_type`, `metadata`, `is_response`, `success`, `error`

## [0.5.5] - 2025-12-20

### Fixed

#### Missing Model Exports [OMN-989]

Exported 4 models from `omnibase_core.models.common` that existed but were not in the public API:

| Model | Purpose |
|-------|---------|
| `ModelTypedMapping` | Type-safe dict replacement for union reduction |
| `ModelValueContainer` | Value container used by ModelTypedMapping |
| `ModelOnexWarning` | Structured warning model |
| `ModelRegistryError` | Canonical registry error model |

**Impact**: Enables `omnibase_infra` to use `ModelTypedMapping` for ~80-100 potential union reductions with proper type safety.

**Canonical Import Paths**:
| Model | Canonical Import | Also Available From |
|-------|-----------------|---------------------|
| `ModelTypedMapping` | `omnibase_core.models.common` | - |
| `ModelValueContainer` | `omnibase_core.models.common` | - |
| `ModelOnexWarning` | `omnibase_core.errors` | `omnibase_core.models.common` |
| `ModelRegistryError` | `omnibase_core.errors` | `omnibase_core.models.common` |

For error/warning models, prefer importing from `omnibase_core.errors` for semantic clarity.

## [0.5.3] - 2025-12-19

### Changed
- Version bump for release tagging (no functional changes from 0.5.2)

## [0.5.2] - 2025-12-19

### Fixed

#### Tech Debt Resolution (P0/P1 Issues)

**Thread Safety Fixes**:
- Fixed circuit breaker race condition in `model_circuit_breaker.py`
  - Added thread-safe locking to all state-modifying operations
  - Created `_unlocked` internal methods to avoid deadlocks
  - Fixed `half_open_requests` counter increment bug

**Timeout Enforcement**:
- Implemented `pipeline_timeout_ms` enforcement in `compute_executor.py`
  - Uses `ThreadPoolExecutor` with timeout for synchronous execution
  - Returns failure result with `TIMEOUT_EXCEEDED` error on timeout
  - Added 8 new tests for timeout behavior

**Workflow Validation**:
- Fixed duplicate step ID validation in `workflow_executor.py`
  - Added validation to detect duplicate step IDs in workflow definitions

### Removed

#### Deprecation Removals (v0.5.0 Announced)
- Removed `computation_type` fallback chain in `node_compute.py` (~70 lines deprecated code)
- Removed `ProtocolRegistryWithBus` alias from `mixins/__init__.py`
- Removed deprecated `JsonSerializable` type alias from `model_onex_common_types.py`

#### Security Hardening
- Removed MD5/SHA-1 hash algorithm support in `model_session_affinity.py`
  - SHA-256 is now the minimum required algorithm
  - Previously deprecated algorithms now raise validation errors

### Changed

#### Documentation Improvements
- Reduced CLAUDE.md from 1145 to 564 lines (51% reduction) while preserving critical information
- Updated README.md import examples to v0.4.0+ patterns
- Updated 10 architecture docs to reflect v0.3.6 dependency inversion (omnibase_spi dependency removal)
- Marked `SPI_PROTOCOL_ADOPTION_ROADMAP.md` as HISTORICAL
- Added timeout thread documentation to `THREADING.md`:
  - Production monitoring for timeout threads
  - Prometheus metrics and warning thresholds
  - `ThreadMonitor` and `TimeoutPool` class implementations
  - Daemon thread lifecycle and resource implications

### Removed
- Deleted stale `README_NODE_REDUCER_TESTS.md` (referenced non-existent file)

## [0.5.1] - 2025-12-18

### Fixed

#### PEP 604 Validator Fix for Dependent Repos [OMN-902]
- Fixed `union_usage_checker.py` to correctly detect PEP 604 union types (`X | Y`) at runtime
- Added `types.UnionType` detection alongside existing `typing.Union` handling
- This fix enables dependent repositories (omnibase_spi, omnibase_nodes, etc.) to use the validator without false positives
- Comprehensive test coverage added for `types.UnionType` detection scenarios

#### UTC Import Fix
- Fixed incorrect UTC import in `model_onex_envelope_v1.py` (was `from datetime import UTC`, now correctly uses `from datetime import timezone`)
- Ensures compatibility across all Python 3.12+ environments

### Testing
- Added 553+ lines of new test coverage for `union_usage_checker.py`
- Comprehensive `types.UnionType` test scenarios including:
  - Direct `X | None` detection
  - Nested unions in generic types
  - Complex union combinations
  - Edge cases with mixed typing styles

### Documentation
- Updated CLAUDE.md with cross-reference to `types.UnionType` behavior differences from `typing.Union`
- Clarified that PEP 604 unions do NOT have `__origin__` accessible via `getattr()` - must use `isinstance(annotation, types.UnionType)` instead

## [0.5.0] - 2025-12-18

### Added

#### Registration Models [OMN-913]
- **ModelRegistrationPayload**: Typed payload for registration intents with comprehensive validation
  - PostgreSQL record storage with `ModelRegistrationRecordBase` type safety
  - Consul service configuration (service ID, name, tags, health checks)
  - Network and deployment metadata (environment, network ID, deployment ID)
  - Field-level validation (min/max lengths, UUID types)
  - Supports flexible Consul health check schema (`dict[str, Any]` for booleans, integers, nested objects)
- **ModelDualRegistrationOutcome**: Registration outcome model with status consistency validation
  - Three status types: `success`, `partial`, `failed`
  - `@model_validator` ensures status consistency with operation flags
  - Error message fields with 2000 character constraints
  - Immutable with thread-safe design (`frozen=True`)
- All models follow ONEX patterns: frozen, extra="forbid", from_attributes=True
- Comprehensive test coverage: 60 tests covering construction, validation, serialization, edge cases

#### Core Intent Discriminated Union [OMN-912]
- Implemented discriminated union pattern for core intents using Pydantic's `Field(discriminator=...)`
- Type-safe intent deserialization with automatic subclass selection
- Enhanced IDE autocomplete and type checking for intent handling

#### Concurrency Testing [OMN-863]
- Comprehensive concurrency tests for all four node types (Effect, Compute, Reducer, Orchestrator)
- Validates thread-safety and parallel execution behavior
- Tests concurrent access patterns and race condition prevention

#### Integration Testing [OMN-864]
- Integration tests for `ModelReducerInput` → `ModelReducerOutput` flows
- End-to-end validation of reducer state management
- FSM transition testing with real workflow scenarios

### Changed

#### Type Safety Improvements [OMN-848]
- Replaced `dict[str, Any]` with strongly typed models across codebase
- Fixed pyright warnings for improved type checking
- Enhanced IDE support and compile-time safety

#### Protocol Standardization [OMN-861]
- Added `ProtocolCircuitBreaker` interface for cross-repository standardization
- Enables consistent circuit breaker patterns across ONEX ecosystem
- Supports dependency injection with protocol-based service resolution

#### Hybrid Type Elimination [OMN-847]
- Eliminated hybrid dict types in favor of pure Pydantic models
- Improved type safety and validation consistency
- Enhanced serialization/deserialization reliability

### Fixed
- Code review feedback from PR #212 (all MAJOR and NITPICK issues resolved)
- Type compliance issues for mypy strict mode (0 errors)
- Pyright basic mode compliance (0 errors, 0 warnings)

### Testing
- Added 60 comprehensive tests for registration models
- Added integration tests for reducer flows
- Added concurrency tests for all node types
- All 12,000+ tests passing across 20 parallel CI splits
- Test execution time: 0.84s for registration models

### Documentation
- Enhanced registration model documentation with usage examples
- Added FSM pattern documentation for discriminated unions
- Updated thread safety guidelines for frozen models

## [0.4.0] - 2025-12-05

> **WARNING**: This is a major release with significant breaking changes. Please review the migration guide before upgrading.

### ⚠️ BREAKING CHANGES

This release implements the **Node Architecture Overhaul**, promoting declarative (FSM/workflow-driven) node implementations as the primary classes. Legacy node implementations have been removed in favor of the new architecture.

#### Node Architecture Overhaul Summary

**What Changed**:
- `NodeReducerDeclarative` → `NodeReducer` (primary FSM-driven implementation)
- `NodeOrchestratorDeclarative` → `NodeOrchestrator` (primary workflow-driven implementation)
- The "Declarative" suffix has been removed - these ARE now the standard implementations
- Legacy implementations (`NodeOrchestratorLegacy`, `NodeReducerLegacy`) have been removed

#### Breaking Changes Summary

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| "Declarative" suffix removed | **HIGH** - Class names changed | Update imports (5 min) |
| Import paths changed | **HIGH** - Old paths removed | Update imports (5 min) |
| Legacy nodes hard deleted | **HIGH** - Must migrate to FSM/workflow patterns (no deprecation period) | See migration guide (30-60 min) |
| FSM-driven NodeReducer is now default | **MEDIUM** - API behavior changes | Review FSM patterns (30 min) |
| Workflow-driven NodeOrchestrator is now default | **MEDIUM** - API behavior changes | Review workflow patterns (30 min) |
| Error recovery patterns changed | **MEDIUM** - Error handling is now declarative | Review error patterns (15 min) |

#### Import Path Changes

**Primary Import Path**:
```python
from omnibase_core.nodes import NodeReducer, NodeOrchestrator, NodeCompute, NodeEffect
```

**Old Declarative Import Path** (no longer works):
```python
# These paths are removed - use omnibase_core.nodes instead
from omnibase_core.infrastructure.nodes.node_reducer_declarative import NodeReducerDeclarative
from omnibase_core.infrastructure.nodes.node_orchestrator_declarative import NodeOrchestratorDeclarative
```

### Changed

#### Node Architecture Overhaul
- **NodeReducer**: Now FSM-driven as the primary implementation (formerly `NodeReducerDeclarative`)
  - Uses `ModelIntent` pattern for pure state machine transitions
  - Intent-based state management separates transition logic from side effects
- **NodeOrchestrator**: Now workflow-driven as the primary implementation (formerly `NodeOrchestratorDeclarative`)
  - Uses `ModelAction` pattern with lease-based single-writer semantics
  - Workflow-driven action definitions with automatic retry and rollback

#### Class Renaming ("Declarative" Suffix Removed)
- `NodeReducerDeclarative` → `NodeReducer`
- `NodeOrchestratorDeclarative` → `NodeOrchestrator`
- All YAML contract-driven configuration is now the default and only approach

### Added

#### Unified Import Surface
- **Single Import Path**: All node types now available from `omnibase_core.nodes`:
  ```python
  from omnibase_core.nodes import (
      NodeCompute,
      NodeEffect,
      NodeReducer,
      NodeOrchestrator,
  )
  ```
- **Input/Output Models**: All node I/O models exported from `omnibase_core.nodes`:
  ```python
  from omnibase_core.nodes import (
      ModelComputeInput,
      ModelComputeOutput,
      ModelReducerInput,
      ModelReducerOutput,
      ModelOrchestratorInput,
      ModelOrchestratorOutput,
      ModelEffectInput,
      ModelEffectOutput,
  )
  ```
- **Public Enums**: Reducer and Orchestrator enums available from `omnibase_core.nodes`

#### Documentation Updates
- **Updated Node Building Guides**: All tutorials reflect v0.4.0 architecture
- **Migration Guide**: New `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md` for upgrade instructions
- **CLAUDE.md Updates**: Project instructions updated to reflect v0.4.0 patterns

### Removed

#### Legacy Node Implementations (Hard Deletion - No Deprecation Period)
- **`NodeOrchestratorLegacy`**: Fully deleted in favor of workflow-driven `NodeOrchestrator`
- **`NodeReducerLegacy`**: Fully deleted in favor of FSM-driven `NodeReducer`
- **Legacy namespace**: The `omnibase_core.nodes.legacy` namespace does not exist and was never created

#### Legacy Patterns (No Longer Supported)
- **Imperative state management**: Direct state mutation in Reducer nodes (use FSM transitions instead)
- **Custom error handling**: Per-step try/except blocks in Orchestrator nodes (use YAML `failure_recovery_strategy`)
- **Non-lease-based orchestration**: Workflow patterns without `lease_id` and `epoch` (use ModelAction with lease semantics)

#### Old Import Paths
- **Declarative import paths**: `omnibase_core.infrastructure.nodes.node_*_declarative` paths removed
- **Direct infrastructure imports**: Must use `omnibase_core.nodes` for primary implementations

#### Error Recovery Changes (BREAKING)

The error recovery system has been **significantly changed** to align with the declarative architecture. **Existing error handling code will need to be rewritten.**

##### What Changed

| Aspect | Before (v0.3.x) | After (v0.4.0) |
|--------|----------------|----------------|
| **Reducer Error Handling** | `try/except` blocks with direct state mutation | FSM wildcard transitions (`from_state: "*"`) |
| **Orchestrator Error Handling** | Custom Python error handling per step | YAML `failure_recovery_strategy` (retry/skip/abort) |
| **Error State Transitions** | Imperative code sets error state | Declarative FSM transitions via `ModelIntent` |
| **Retry Logic** | Custom retry loops in Python | Lease-based idempotent retries with `lease_id` + `epoch` |

##### Reducer Nodes - Error Recovery Migration

**Before (v0.3.x)** - Imperative error handling:
```python
# Legacy pattern (removed in v0.4.0)
class MyReducer(NodeReducerBase):
    async def process(self, input_data):
        try:
            result = await self.do_work()
            self.state = "completed"
        except Exception as e:
            self.state = "failed"  # Direct state mutation
            self.error = str(e)
            raise
```

**After (v0.4.0)** - Declarative FSM transitions:
```yaml
# In your YAML contract
transitions:
  - from_state: "*"           # Wildcard: catches errors from ANY state
    to_state: failed
    trigger: error_occurred
    actions:
      - action_name: "log_error"
        action_type: "logging"
      - action_name: "emit_failure_event"
        action_type: "event"
```

```python
# Recommended: Use FSM-driven base class
class MyReducer(NodeReducer):
    pass  # Error handling is declarative via YAML
```

##### Orchestrator Nodes - Error Recovery Migration

**Before (v0.3.x)** - Per-step error handling:
```python
# Legacy pattern (removed in v0.4.0)
class MyOrchestrator(NodeOrchestratorBase):
    async def process(self, input_data):
        try:
            await self.step1()
        except Exception:
            await self.retry_step1()  # Custom retry logic
```

**After (v0.4.0)** - Workflow-level failure strategy:
```yaml
# In your YAML contract
coordination_rules:
  failure_recovery_strategy: retry  # Options: retry, skip, abort
  max_retries: 3
  retry_backoff_ms: 1000
```

Actions now include `lease_id` and `epoch` for idempotent retries, preventing duplicate execution.

##### Migration Checklist for Error Handling

- [ ] Remove all `try/except` blocks that mutate state directly in Reducer nodes
- [ ] Add FSM wildcard transitions (`from_state: "*"`) for error handling
- [ ] Remove custom retry loops in Orchestrator nodes
- [ ] Configure `failure_recovery_strategy` in YAML workflow contracts
- [ ] Verify `ModelIntent` emission replaces direct error state mutations
- [ ] Test error recovery paths with the new declarative patterns

---

### Migration Guide (v0.3.x to v0.4.0)

> **Estimated Migration Time**: 30-60 minutes for typical projects. **Full Guide**: See [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for comprehensive migration instructions with complete examples.

#### Quick Migration Checklist

- [ ] Update all node imports to use `omnibase_core.nodes`
- [ ] Replace legacy reducer implementations with `NodeReducer`
- [ ] Replace legacy orchestrator implementations with `NodeOrchestrator`
- [ ] Convert imperative state management to FSM YAML contracts
- [ ] Convert workflow coordination to workflow YAML contracts
- [ ] Update error handling to use declarative patterns
- [ ] Run tests to verify behavior

#### Step 1: Update Imports
```python
# Before (v0.3.x) - Old declarative import paths
from omnibase_core.infrastructure.nodes.node_reducer_declarative import NodeReducerDeclarative

# After (v0.4.0) - Use primary implementation
from omnibase_core.nodes import NodeReducer
```

#### Step 2: Update Class Inheritance
```python
# Before (v0.3.x)
class MyReducer(NodeReducerBase):
    pass

# After (v0.4.0)
class MyReducer(NodeReducer):
    pass
```

#### Step 3: Adopt FSM/Workflow Patterns
- **Reducer nodes**: Implement `ModelIntent` emission instead of direct state updates
- **Orchestrator nodes**: Use `ModelAction` with lease management for coordination
- See [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for detailed examples

#### Step 4: Update Error Handling
```python
# Before (v0.3.x) - Imperative error handling
class MyReducer(NodeReducerBase):
    async def process(self, input_data):
        try:
            result = await self.do_work()
            self.state = "completed"
        except Exception as e:
            self.state = "failed"
            raise

# After (v0.4.0) - Declarative error handling via YAML
# In your contract.yaml:
# transitions:
#   - from_state: "*"
#     to_state: failed
#     trigger: error_occurred
```

---

### ⚠️ Implementation Note: Hard Deletion (Not Soft Deprecation)

> **BREAKING CHANGE**: After reviewing the architecture and confirming that no users currently exist on the legacy node implementations, we pivoted from the originally planned Phase 1 (soft deprecation with warnings) directly to **hard deletion** of legacy nodes.

**Why Hard Deletion Instead of Soft Deprecation?**

1. **No Existing Users**: The legacy `NodeReducerLegacy` and `NodeOrchestratorLegacy` classes had no production usage
2. **Cleaner Codebase**: Removing legacy code entirely eliminates maintenance burden and confusion
3. **Simpler Migration**: Users only need to learn the new patterns, not navigate deprecated APIs
4. **Reduced Risk**: No transition period means no risk of users depending on soon-to-be-removed code

**What This Means for You**:

- Legacy imports (`NodeReducerLegacy`, `NodeOrchestratorLegacy`) will **fail immediately** - no deprecation warnings
- The `omnibase_core.nodes.legacy` namespace **does not exist**
- All nodes must use FSM-driven (`NodeReducer`) or workflow-driven (`NodeOrchestrator`) patterns
- See [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for migration instructions

---

## [0.3.3] - 2025-11-19

### Added

#### Subcontract Models
- **6 New Subcontract Models**: Complete mixin-subcontract architecture with comprehensive Pydantic models
  - `ModelDiscoverySubcontract`: Service discovery configuration with channel validation
  - `ModelEventHandlingSubcontract`: Event subscription and filtering patterns
  - `ModelIntrospectionSubcontract`: Node metadata and capability introspection
  - `ModelLifecycleSubcontract`: Initialization and shutdown lifecycle management
  - `ModelObservabilitySubcontract`: Metrics, logging, and tracing configuration
  - `ModelToolExecutionSubcontract`: Tool and capability execution framework
- **Comprehensive Test Coverage**: 960+ tests for all subcontract models with validation, serialization, and edge case testing

#### Metadata & Manifest Models
- **ModelMixinMetadata**: Declarative mixin metadata with schema validation and subcontract integration
- **ModelDockerComposeManifest**: Docker Compose configuration parsing with port conflict detection and YAML validation
- **Mixin Metadata YAML**: 305-line metadata file (`mixin_metadata.yaml`) with schemas and examples for 5 mixins

#### Documentation Enhancements
- **NODE_CLASS_HIERARCHY.md** (1364 lines): Complete guide to ONEX node class hierarchy with decision trees and migration paths
- **MIXIN_SUBCONTRACT_MAPPING.md** (1104 lines): Comprehensive mapping guide for mixin-to-subcontract relationships
- **TERMINOLOGY_AUDIT_REPORT.md**: Standardization audit for ONEX v2.0 terminology
- **TERMINOLOGY_FIXES_CHECKLIST.md**: Checklist for terminology consistency across codebase

#### Tools & Scripts
- **validate_docs_links.py**: Markdown link validation tool scanning for broken file and anchor references
- **fix_documentation_links.py**: Automated link correction script for predefined fixes

### Changed

#### Error Handling Standardization
- **ModelOnexError Migration**: Renamed `OnexError` → `ModelOnexError` across all documentation and templates (27+ files)
- **Import Path Consolidation**: Standardized import paths to `omnibase_core.models.errors.model_onex_error`
- **correlation_id Best Practices**: Added correlation_id parameter to 19+ error examples for improved traceability

#### Documentation Improvements
- **Pydantic v2 Migration**: Updated 25+ template examples from `@validator` → `@field_validator`
- **Code Example Fixes**: Fixed 91 malformed markdown code fences and 22 inconsistent import paths
- **Template Updates**: Replaced `BaseNodeConfig` with `BaseModel` in 3 template files
- **Processing Time Calculations**: Fixed duration calculation bugs in ENHANCED_NODE_PATTERNS
- **Security Sanitization**: Fixed output propagation in security validation examples

#### Node Base Class Updates
- **Service Wrapper Promotion**: Documentation now recommends `ModelService*` wrappers over legacy `Node*` bases
- **Advanced Patterns Introduction**: Added ONEX v2.0 patterns (ModelIntent for REDUCER, ModelAction for ORCHESTRATOR)

### Fixed

#### Source Code Bugs
- **Discovery Validation**: Fixed `model_discovery_subcontract.py` to only validate channels when `enabled=True`
- **Port Parsing**: Enhanced `model_docker_compose_manifest.py` to handle all Docker port formats (IP prefix, protocol suffix)
- **Import Ordering**: Fixed isort configuration alignment between local and CI environments

#### Documentation Fixes
- **Missing Imports**: Added `ModelOnexError`, `CircuitBreakerError`, `datetime`, `UUID` imports to 8+ code examples
- **Enum Naming**: Standardized to `EnumCoreErrorCode` across 4+ occurrences
- **Legacy Module Paths**: Updated manifest dependency paths from `models.model_onex_error` → `errors.model_onex_error`
- **Stray Artifacts**: Removed generator artifacts from 2 template files

### Quality & CI
- **CI Performance**: All test splits running within expected 2m30s-3m30s benchmark
- **Test Coverage**: Maintained 60%+ coverage requirement with 12,198 tests
- **Type Safety**: 100% mypy strict compliance (0 errors in 1,840 source files)
- **Code Quality**: Black, isort, and ruff all passing

## [0.2.0] - 2025-10-31

### Added

#### Discovery System Enhancements
- **TypedDict for Discovery Stats**: Introduced `TypedDictDiscoveryStats` for type-safe statistics tracking in discovery system
- **Filtered Requests Counter**: Added `filtered_requests` counter to track requests that don't match discovery criteria (separate from errors and throttling)
- **Enhanced Error Tracking**: Added `error_count` field to discovery stats for comprehensive observability

#### Node Introspection Improvements
- **ONEX Architecture Classification**: Added `node_type` field with 4-node validation (effect, compute, reducer, orchestrator) to `ModelNodeIntrospectionEvent`
- **Node Role Support**: Added optional `node_role` field for specialization within node types
- **Source Node Tracking**: Added `source_node_id` field to `ModelOnexEnvelopeV1` for node-to-node event correlation and tracking (Note: `ModelOnexEnvelopeV1` was later renamed to `ModelOnexEnvelope` in )

#### Documentation Enhancements
- **Mermaid Diagrams**: Added 5 visual diagrams for ONEX architecture flows:
  - Four-node architecture flow with side effects
  - Intent emission and execution sequence (pure FSM pattern)
  - Action validation and execution flow (lease-based orchestration)
  - Service wrapper decision flowchart
  - Event-driven communication integrated into Intent flow
- **Research Documentation**:
  - In-Memory Event Bus Research Report (746 lines)
  - Union Type Quick Reference (319 lines)
  - Union Type Remediation Plan (1045 lines)
  - Ecosystem Directory Structure documentation (396 lines)
- **Enhanced Architecture Docs**: Improved ONEX four-node architecture documentation with better examples and terminology
- **Getting Started Updates**: Enhanced Quick Start guide with production patterns (ModelServiceCompute)
- **Node Building Guides**: Improved node type tutorials with FSM and Intent/Action pattern introductions
- **Container Types Documentation**: Comprehensive 657-line guide (docs/architecture/CONTAINER_TYPES.md) clarifying ModelContainer vs ModelONEXContainer distinction
- **Architectural Decision Record**: ADR-001 documenting protocol-based DI architecture design rationale
- **Container Type Compliance Report**: Audit report validating correct container type usage across codebase

### Changed

#### Dependencies
- **omnibase_spi Upgrade**: Updated from v0.1.1 → v0.2.0 with 9 new protocols for enhanced type safety and capability expansion

#### Discovery System Improvements
- **Error Handling**: Replaced silent exception handling with structured logging (ProtocolLogger warnings) for non-fatal discovery errors
- **TypedDict Usage**: Simplified TypedDict usage by removing defensive isinstance checks (trust TypedDict type safety)
- **Stats Initialization**: Updated discovery stats initialization and reset methods to include new `error_count` field

#### Validation Improvements
- **Validation Rules**: Replaced improper `dict[str, Any] | list[dict[str, Any]] | None` Union pattern with strongly-typed `ModelValidationRules | None`
- **Field Validators**: Enhanced validation using `ModelValidationRulesConverter` for backward compatibility with dict/list/string formats

### Fixed

#### Build & CI Fixes
- **Import Path**: Corrected import path for `EnumCoreErrorCode` from `omnibase_core.errors.error_codes` to `omnibase_core.enums.enum_core_error_code`
- **Import Ordering**: Fixed isort import ordering in `mixin_discovery_responder.py` (omnibase_core before omnibase_spi)
- **Missing Parameters**: Added missing `node_type` parameter to `create_from_node_info()` calls in introspection publisher

#### Node Introspection Fixes
- **Explicit Node Type**: Required explicit `get_node_type()` implementation in nodes, removing fallback to `__class__.__name__` which could produce invalid values
- **Validation Error Prevention**: Prevents runtime ValidationError from invalid node_type patterns through early error detection
- **Test Updates**: Updated 5 introspection publisher tests to include required `node_type` parameter

#### Configuration Fixes
- **isort/Ruff Conflict**: Resolved infinite loop where isort and ruff conflicted on import ordering for `mixin_discovery_responder.py`
- **Pre-commit Configuration**: Added proper exclusions in both ruff and isort configurations for files with intentional import ordering

#### Documentation Fixes
- **Docstring Typos**: Fixed 6 docstring typos:
  - "list[Any]en" → "listen"
  - "list[Any]: List of capabilities" → "list[str]: List of capabilities"
  - "list[Any]rather" → "list rather"
  - "list[Any]ings" → "listings"
  - "list[Any]ener" → "listener"
- **Broken Path References**: Fixed 3 broken path references to THREADING.md
- **Cross-Linking**: Added 8 navigation paths connecting beginner to advanced topics across documentation index, testing guide, protocol architecture, and event-driven patterns

### Refactored

#### Validation System
- **Backward Compatibility Removal**: Removed field_validator for `validation_rules` that provided automatic conversion from legacy dict/list/string formats
- **Strong Typing Enforcement**: `validation_rules` now strictly requires `ModelValidationRules | None` without automatic conversions
- **Cleaner Code**: Eliminated conversion logic and hidden transformations

### Tests

#### New Test Coverage
- **TypedDict Tests**: Added 262 comprehensive tests across 18 TypedDict implementations:
  - Structure validation tests for each TypedDict type
  - Field type and edge case tests (zero values, high volume, None handling)
  - Incremental update and reset scenarios
  - Error tracking and throttling scenarios
- **Test Updates**: Updated 5 introspection publisher tests for new `node_type` parameter requirement

### Chore

#### Repository Maintenance
- **Temporary File Cleanup**: Removed spurious temporary files that shouldn't be in version control:
  - ADVANCED_DOCS_VALIDATION_REPORT.md
  - performance_analysis_results.txt
- **MCP Configuration**: Cleaned up `.mcp.json` by removing all MCP server configurations and resetting to empty mcpServers object
- **Dependencies**: Updated `poetry.lock` and `pyproject.toml` for related dependencies

## [0.1.0] - 2025-10-21

### Added

#### Core Architecture
- **4-Node ONEX Pattern**: Complete implementation of EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow architecture
- **Protocol-Driven Dependency Injection**: ModelONEXContainer with `container.get_service("ProtocolName")` pattern
- **Mixin/Subcontract System**: 38 specialized mixins for reusable behavior and cross-cutting concerns
- **Contract-Driven Development**: 17 comprehensive contracts for type-safe node development
- **Event-Driven Communication**: ModelEventEnvelope for inter-service messaging with correlation tracking
- **FSM-Based State Management**: Pure finite state machine implementation for Intent → Action workflows

#### Node Infrastructure
- `NodeEffect`: External I/O, API calls, side effects with transaction support
- `NodeCompute`: Pure transformations and algorithms with caching
- `NodeReducer`: State aggregation and persistence with FSM-based Intent emission
- `NodeOrchestrator`: Workflow coordination with dependency tracking and Action lease management
- `NodeCoreBase`: Unified base class with Protocol mixins for all node types

#### Pre-Composed Service Classes
- `ModelServiceEffect`: Pre-wired Effect node with service mode + health + events + metrics
- `ModelServiceCompute`: Pre-wired Compute node with service mode + health + events + metrics
- `ModelServiceReducer`: Pre-wired Reducer node with service mode + health + events + metrics + FSM
- `ModelServiceOrchestrator`: Pre-wired Orchestrator node with service mode + health + events + metrics + coordination

#### Mixins & Cross-Cutting Concerns
- `MixinNodeService`: Persistent service mode for long-lived MCP servers
- `MixinHealthCheck`: Health monitoring with configurable checks and reporting
- `MixinEventBus`: Event publishing/subscription for inter-node communication
- `MixinMetrics`: Performance metrics collection and reporting
- `MixinCaching`: Result caching with TTL and invalidation strategies
- `MixinCanonicalSerialization`: Deterministic JSON serialization for hashing
- `MixinEventDrivenNode`: Event-driven processing with envelope handling
- `MixinDiscoveryResponder`: Tool discovery and capability advertisement
- Additional specialized mixins for specific use cases

#### Contracts & Validation
- **Base Contracts**: ModelContractBase with version, description, and validation rules
- **Specialized Contracts**: ModelContractEffect, ModelContractCompute, ModelContractReducer, ModelContractOrchestrator
- **Subcontracts**: 6 specialized subcontract types (FSM, EventType, Aggregation, StateManagement, Routing, Caching)
- **Validation Framework**: Comprehensive runtime validation with Pydantic models
- **Migration System**: Protocol-based migration framework with rollback support

#### Models & Data Structures
- **Core Models**: ModelEventEnvelope, ModelHealthStatus, ModelSemVer, ModelMetadataToolCollection
- **Workflow Models**: ModelWorkflowStepExecution, ModelDependencyGraph with topological ordering
- **Action Models**: ModelAction (formerly Thunk) with lease semantics for single-writer guarantees
- **Discovery Models**: ModelToolDefinition, ModelToolParameter, ModelCapability
- **Security Models**: ModelPermission with granular access control
- **60+ production-ready Pydantic models** with full type safety

#### Error Handling
- **ModelOnexError Exception**: Structured error handling with Pydantic models
- **ModelOnexError**: Comprehensive error context with correlation tracking
- **Error Chaining**: Full exception context preservation with `__cause__`
- **Error Recovery**: Automatic retry logic with exponential backoff

#### Performance & Optimization
- **Compute Caching**: Automatic result caching for pure computations
- **Performance Baselines**: Baseline establishment and monitoring
- **Optimization Opportunities**: Automatic detection and recommendations
- **Metrics Collection**: Detailed performance metrics with thresholds

#### Type Safety & Validation
- **Zero Tolerance for Any**: Comprehensive type annotations throughout codebase
- **Pydantic Model Validation**: Runtime validation for all data structures
- **Protocol-Based Design**: Type-safe dependency injection via Protocols
- **MyPy Strict Mode**: Full static type checking compliance (in progress)

#### Developer Experience
- **Comprehensive Validation Scripts**: 42 validators across architecture, naming, patterns, and compliance
- **Pre-commit Hooks**: 27 custom ONEX validation hooks for code quality enforcement
- **Pattern Validation**: Automatic detection of anti-patterns and violations
- **Naming Conventions**: Enforced ONEX naming standards (SUFFIX-based)
- **Professional README**: Complete with badges for License (MIT), Python 3.12+, Black, MyPy, Pre-commit, and Framework status
- **Documentation**: Comprehensive inline documentation and docstrings

#### Testing Infrastructure
- **135+ Unit Tests**: Comprehensive test coverage across all components
- **Integration Tests**: Multi-node workflow testing
- **Performance Tests**: Baseline and optimization testing
- **Edge Case Coverage**: Extensive edge case and error scenario testing

#### Documentation
- **78+ Documentation Files**: Comprehensive documentation covering all aspects of the framework
- **Node-Building Guide Series**: Complete tutorials for building EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR nodes
- **Mixin Development Guides**: Detailed guides for creating and composing mixins
- **Architecture Documentation**: In-depth architectural principles and design patterns
- **API Reference**: Complete API documentation with examples and usage patterns
- **Migration Guides**: Step-by-step migration instructions for breaking changes
- **CONTRIBUTING.md**: Comprehensive contribution guidelines following ONEX standards
- **README.md**: Professional project overview with architecture principles and quick start

#### Legal & Licensing
- **MIT LICENSE**: Open-source license granting broad permissions for use, modification, and distribution
- **Copyright Notices**: Proper attribution and copyright headers throughout codebase

### Changed

#### Breaking Changes - Thunk → Action Refactoring
- **Renamed**: `ModelThunk` → `ModelAction` for clearer intent semantics
- **Renamed**: `EnumThunkType` → `EnumActionType` for consistency
- **Field Renaming**:
  - `thunk_id` → `action_id`
  - `thunk_type` → `action_type`
  - `operation_data` → `payload`
- **Lease Management**: Added `lease_id` and `epoch` fields for single-writer semantics
- **Migration Path**: All test files and internal references updated
- **Backward Compatibility**: Field name `thunks` retained in ModelWorkflowStepExecution for compatibility

#### Architecture Improvements
- **NodeCoreBase Refactoring**: Migrated to Protocol-based mixin composition
- **FSM Implementation**: Pure FSM in Reducer with Intent emission (no backward compatibility methods)
- **Service Classes**: Eliminated boilerplate with pre-composed service wrappers
- **Method Resolution Order**: Optimized MRO for proper mixin composition

#### Code Quality Improvements
- **164 Ruff Auto-Fixes**: Removed unused imports, fixed formatting, simplified expressions
- **Import Organization**: Consistent isort configuration across codebase
- **Type Annotations**: Enhanced type coverage (ongoing)
- **Error Messages**: Improved error context and debugging information

#### Repository Management
- **Fresh Git History**: Clean git history established after migration from development backup
- **Conventional Commits**: Standardized commit message format for clarity
- **Branch Strategy**: Established main branch as primary development branch

### Deprecated
- **Backward Compatibility Methods in Reducer**: Removed all compatibility methods for previous state management
- **Manual YAML Generation**: Deprecated in favor of Pydantic model exports
- **String-Based Versions**: Enforced ModelSemVer usage throughout

### Removed
- **Legacy Thunk Terminology**: Removed from all public APIs (replaced with Action)
- **Redundant Base Classes**: Consolidated into pre-composed service classes
- **Dead Code**: Removed unused utilities and archived patterns
- **Deprecated Imports**: Cleaned up old import paths

### Fixed
- **Test Collection Errors**: Fixed 3 test files with EnumThunkType → EnumActionType imports
- **Import Errors**: Resolved circular import issues with proper dependency structure
- **Type Errors**: Fixed multiple type annotation issues (ongoing - 267 remaining)
- **Ruff Violations**: Reduced from 1037 to 873 violations
- **Pre-commit Hooks**: All 27 custom hooks passing

### Security
- **Protocol-Based DI**: Prevents direct class coupling and improves testability
- **Type Safety**: Strong typing reduces runtime errors and vulnerabilities
- **Validation**: Runtime validation of all inputs via Pydantic models
- **Error Context**: Comprehensive error tracking without exposing sensitive data

## Known Limitations (v0.1.0)

### Type Safety (In Progress)
- **MyPy Errors**: 267 remaining type errors requiring fixes
  - NodeCoreBase missing mixin attribute definitions (requires Protocol refinement)
  - ModelSemVer import issues in metadata collections
  - Type annotation gaps in utility functions
- **Target**: 0 mypy errors before v0.2.0

### Code Quality (In Progress)
- **Ruff Violations**: 873 remaining (down from 1037)
  - UP035: Deprecated typing imports (366 violations) - migrate to modern syntax
  - F403: Undefined star imports (80 violations) - explicit imports needed
  - PTH: Path operations (use pathlib.Path)
  - Other minor violations
- **Target**: <100 violations before v0.2.0

### Documentation
- **API Documentation**: Docstrings present but API docs generation pending
- **Architecture Diagrams**: Workflow diagrams and architecture visualizations pending
- **Migration Guides**: Detailed migration documentation for breaking changes pending
- **Examples**: More real-world usage examples needed

### Test Coverage
- **Current Coverage**: >60% overall coverage
- **Target**: >80% coverage before v0.2.0
- **Integration Tests**: Additional multi-service integration tests needed
- **Performance Tests**: Baseline and regression testing framework in development

### Configuration Management
- **PEP 621 Migration**: pyproject.toml still using legacy Poetry format
- **Deprecation Warnings**: 8 Poetry warnings for non-PEP 621 fields
- **Target**: Full PEP 621 compliance before v0.2.0

## Migration Guide

### From Pre-0.1.0 (Thunk → Action)

#### Import Changes
```python
# OLD
from omnibase_core.models.orchestrator.model_action import ModelThunk
from omnibase_core.enums.enum_workflow_execution import EnumThunkType

# NEW
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_workflow_execution import EnumActionType
```

#### Field Name Changes
```python
# OLD
thunk = ModelThunk(
    thunk_id=uuid4(),
    thunk_type=EnumThunkType.COMPUTE,
    operation_data={"key": "value"}
)

# NEW
action = ModelAction(
    action_id=uuid4(),
    action_type=EnumActionType.COMPUTE,
    payload={"key": "value"},
    lease_id=uuid4(),  # Required
    epoch=0  # Required
)
```

#### Workflow Step References
```python
# Field name 'thunks' retained for compatibility
step = ModelWorkflowStepExecution(
    step_name="my_step",
    execution_mode=EnumExecutionMode.SEQUENTIAL,
    thunks=[action]  # Still uses 'thunks' field name
)
```

### Reducer FSM Migration

#### Old Pattern (Removed)
```python
# REMOVED - No longer supported
await self.update_state(new_state)
await self.persist_state()
```

#### New Pattern (Pure FSM)
```python
# NEW - Emit Intent, Orchestrator converts to Action
intent = ModelIntent(
    intent_type=EnumIntentType.UPDATE_STATE,
    target_state=EnumMyState.PROCESSING,
    payload={"data": value}
)
await self.emit_intent(intent)
```

## Contributing

This project follows ONEX architectural patterns and standards. See CONTRIBUTING.md for guidelines.

### Code Quality Standards
- All code must pass pre-commit hooks (27 custom ONEX validators)
- Zero tolerance for `Any` types (strict type annotations required)
- Comprehensive test coverage (target: >80%)
- Pydantic models for all data structures
- Protocol-based dependency injection

### ONEX Naming Conventions
- **Classes**: `Node<Name><Type>` (e.g., `NodeDatabaseWriterEffect`)
- **Files**: `node_*_<type>.py` (e.g., `node_database_writer_effect.py`)
- **Methods**:
  - Effect: `execute_effect(contract: ModelContractEffect)`
  - Compute: `execute_compute(contract: ModelContractCompute)`
  - Reducer: `execute_reduction(contract: ModelContractReducer)`
  - Orchestrator: `execute_orchestration(contract: ModelContractOrchestrator)`

## Acknowledgments

Built with the ONEX framework principles:
- **Zero Boilerplate**: Eliminate repetitive code through base classes
- **Protocol-Driven**: Type-safe dependency injection via Protocols
- **Event-Driven**: Inter-service communication via ModelEventEnvelope
- **4-Node Pattern**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow

## License

MIT License - See LICENSE file for details

---

**Note**: This is the initial public release (v0.1.0). While production-ready for many use cases, some rough edges remain (see Known Limitations). Contributions welcome!
