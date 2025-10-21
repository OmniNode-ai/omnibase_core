# Changelog

All notable changes to the ONEX Core Framework (omnibase_core) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-10-20

### Added

#### Core Architecture
- **4-Node ONEX Pattern**: Complete implementation of EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow architecture
- **Protocol-Driven Dependency Injection**: ONEXContainer with `container.get_service("ProtocolName")` pattern
- **Mixin System**: 15+ reusable behavior mixins for cross-cutting concerns
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
- **OnexError Exception**: Structured error handling with Pydantic models
- **ModelONEXError**: Comprehensive error context with correlation tracking
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
- **Pre-commit Hooks**: 27 custom ONEX validation hooks for code quality
- **Pattern Validation**: Automatic detection of anti-patterns and violations
- **Naming Conventions**: Enforced ONEX naming standards (SUFFIX-based)
- **Documentation**: Comprehensive inline documentation and docstrings

#### Testing Infrastructure
- **135+ Unit Tests**: Comprehensive test coverage across all components
- **Integration Tests**: Multi-node workflow testing
- **Performance Tests**: Baseline and optimization testing
- **Edge Case Coverage**: Extensive edge case and error scenario testing

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
