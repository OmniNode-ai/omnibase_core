# Changelog

All notable changes to the ONEX Core Framework (omnibase_core) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed `ModelOnexEnvelopeV1` to `ModelOnexEnvelope` (OMN-224)
- Renamed fields: `event_id`→`envelope_id`, `source_service`→`source_node`, `event_type`→`operation`
- Added new fields: `causation_id`, `target_node`, `handler_type`, `metadata`, `is_response`, `success`, `error`

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
- **Source Node Tracking**: Added `source_node_id` field to `ModelOnexEnvelopeV1` for node-to-node event correlation and tracking (Note: `ModelOnexEnvelopeV1` was later renamed to `ModelOnexEnvelope` in OMN-224)

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
