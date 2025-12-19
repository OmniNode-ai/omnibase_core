# Documentation Index - omnibase_core

**Welcome to the omnibase_core documentation!** This is your central hub for all documentation.

## 🚀 Quick Start Paths

### New to omnibase_core?
1. Read [Installation](getting-started/INSTALLATION.md) (5 min)
2. Follow [Quick Start](getting-started/QUICK_START.md) (10 min)
3. Build [Your First Node](getting-started/FIRST_NODE.md) (20 min)

### Building Nodes?
→ **Start here**: [Node Building Guide](guides/node-building/README.md) ← **RECOMMENDED**

### Need Reference?
→ **Templates**: [Node Templates](guides/templates/COMPUTE_NODE_TEMPLATE.md)
→ **Architecture**: [ONEX Four-Node Architecture](architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

## 📚 Documentation Structure

```text
omnibase_core/docs/
│
├── Getting Started          → New developer onboarding
├── Guides                   → Step-by-step tutorials
│   └── Node Building       ★ Critical priority
├── Architecture             → System design and concepts
├── Reference                → Templates and API docs
├── Standards                → Normative specifications
└── Specialized Topics       → Threading, errors, patterns
```

---

## 📖 Getting Started

**For developers new to omnibase_core**

| Document | Description | Time | Status |
|----------|-------------|------|--------|
| [Installation](getting-started/INSTALLATION.md) | Environment setup with Poetry | 5 min | ✅ Complete |
| [Quick Start](getting-started/QUICK_START.md) | First 5 minutes with omnibase_core | 10 min | ✅ Complete |
| [First Node](getting-started/FIRST_NODE.md) | Build your first simple node | 20 min | ✅ Complete |

---

## 🛠️ Guides

**Step-by-step tutorials for common tasks**

### Node Building Guide ⭐ CRITICAL PRIORITY

**Complete guide to building ONEX nodes - perfect for developers**

| # | Document | Description | Time | Status |
|---|----------|-------------|------|--------|
| 0 | [Node Building Overview](guides/node-building/README.md) | Guide navigation and overview | 5 min | ✅ Complete |
| 1 | [What is a Node?](guides/node-building/01_WHAT_IS_A_NODE.md) | Fundamentals and concepts | 5 min | ✅ Complete |
| 2 | [Node Types](guides/node-building/02_NODE_TYPES.md) | EFFECT, COMPUTE, REDUCER, ORCHESTRATOR | 10 min | ✅ Complete |
| 3 | [COMPUTE Node Tutorial](guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) | Build a price calculator | 30 min | ✅ Complete |
| 4 | [EFFECT Node Tutorial](guides/node-building/04_EFFECT_NODE_TUTORIAL.md) | Build a file backup system | 30 min | ✅ Complete (Phase 2) |
| 5 | [REDUCER Node Tutorial](guides/node-building/05_REDUCER_NODE_TUTORIAL.md) | Build a metrics aggregator | 30 min | ✅ Complete (Phase 2) |
| 6 | [ORCHESTRATOR Node Tutorial](guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md) | Build a workflow coordinator | 45 min | ✅ Complete |
| 7 | [Patterns Catalog](guides/node-building/07_PATTERNS_CATALOG.md) | Common patterns library | 20 min | ✅ Complete |
| 8 | [Common Pitfalls](guides/node-building/08_COMMON_PITFALLS.md) | What to avoid | 15 min | ✅ Complete |
| 9 | [Testing Intent Publisher](guides/node-building/09_TESTING_INTENT_PUBLISHER.md) | Testing with MixinIntentPublisher | 20 min | ✅ Complete |
| 10 | [Agent Templates](guides/node-building/10_AGENT_TEMPLATES.md) | Agent-friendly templates | 15 min | ✅ Excellent |

**Progress**: 10 of 10 complete (100%)

### Other Guides

| Document | Description | Status |
|----------|-------------|--------|
| [**Migrating to Declarative Nodes**](guides/MIGRATING_TO_DECLARATIVE_NODES.md) | Migration guide for v0.4.0 FSM/workflow-driven nodes ⭐ **v0.4.0** | ✅ Complete |
| [**Mixin-Subcontract Mapping**](guides/MIXIN_SUBCONTRACT_MAPPING.md) | Relationship between mixins and subcontracts | ✅ Complete |
| [Testing Guide](guides/TESTING_GUIDE.md) | Comprehensive testing strategies | ✅ Complete |

### Manifest Models

| Document | Description | Status |
|----------|-------------|--------|
| [ModelMixinMetadata](../src/omnibase_core/models/core/model_mixin_metadata.py) | Mixin metadata validation and discovery (11 models, 39 tests) | ✅ Complete |
| [ModelDockerComposeManifest](../src/omnibase_core/models/docker/model_docker_compose_manifest.py) | Docker Compose YAML validation (16 integrated models, 25 tests) | ✅ Complete |

---

## 🏗️ Architecture

**Understanding the ONEX system**

| Document | Description | Status |
|----------|-------------|--------|
| [Architecture Overview](architecture/OVERVIEW.md) | High-level system design | ✅ Complete |
| [**Four-Node Pattern**](architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) | Core ONEX architecture ⭐ **Excellent!** | ✅ Complete |
| [**Canonical Execution Shapes**](architecture/CANONICAL_EXECUTION_SHAPES.md) | Allowed/forbidden data flow patterns ⭐ **NEW** | ✅ Complete |
| [**Execution Shape Examples**](architecture/EXECUTION_SHAPE_EXAMPLES.md) | Practical examples for each canonical shape ⭐ **NEW** | ✅ Complete |
| [**Message Topic Mapping**](architecture/MESSAGE_TOPIC_MAPPING.md) | Event/Command/Intent to topic routing rules ⭐ **NEW** | ✅ Complete |
| [**Node Purity Guarantees**](architecture/NODE_PURITY_GUARANTEES.md) | Purity enforcement for COMPUTE/REDUCER nodes | ✅ Complete |
| [**Node Class Hierarchy**](architecture/NODE_CLASS_HIERARCHY.md) | ModelService* vs Node* vs NodeCoreBase ⭐ **CRITICAL** | ✅ Complete |
| [**Container Types**](architecture/CONTAINER_TYPES.md) | ModelContainer vs ModelONEXContainer ⚠️ **CRITICAL** | ✅ Complete |
| [Dependency Injection](architecture/DEPENDENCY_INJECTION.md) | ModelONEXContainer patterns | ✅ Complete |
| [Contract System](architecture/CONTRACT_SYSTEM.md) | Contract architecture | ✅ Complete |
| [Type System](architecture/TYPE_SYSTEM.md) | Typing patterns and conventions | ✅ Complete |
| [Documentation Architecture](architecture/DOCUMENTATION_ARCHITECTURE.md) | Documentation structure and organization | ✅ Complete |
| [Subcontract Architecture](architecture/SUBCONTRACT_ARCHITECTURE.md) | Contract system design and subcontract patterns | ✅ Complete |
| [Mixin Architecture](architecture/MIXIN_ARCHITECTURE.md) | Mixin system design and patterns | ✅ Complete |
| [Protocol Architecture](architecture/PROTOCOL_ARCHITECTURE.md) | Protocol design and compliance | ✅ Complete |
| [Effect Timeout Behavior](architecture/EFFECT_TIMEOUT_BEHAVIOR.md) | Timeout check points and retry behavior | ✅ Complete |
| [Ecosystem Directory Structure](architecture/ECOSYSTEM_DIRECTORY_STRUCTURE.md) | Repository organization and patterns across ONEX ecosystem | ✅ Available |
| [**Registration Trigger Design**](architecture/REGISTRATION_TRIGGER_DESIGN.md) | Registration trigger architecture and design patterns | ✅ Complete |

### Architecture Decision Records (ADRs)

**Key architectural decisions and their rationale**

| Document | Description | Status |
|----------|-------------|--------|
| [ADR-001: Protocol-Based DI](architecture/decisions/ADR-001-protocol-based-di-architecture.md) | Protocol-based dependency injection architecture | ✅ Complete |
| [ADR-002: Context Mutability](architecture/decisions/ADR-002-context-mutability-design-decision.md) | Design decision on context mutability | ✅ Complete |
| [**ADR-012: Validator Error Handling**](architecture/adr/ADR-012-VALIDATOR-ERROR-HANDLING.md) | ModelOnexError in Pydantic validators with future compatibility ⭐ **v0.4.0** | ✅ Complete |
| [ADR-003: Reducer Output Exception Consistency](architecture/decisions/ADR-003-reducer-output-exception-consistency.md) | Sentinel value pattern and exception handling strategy | ✅ Complete |
| [ADR-004: Registration Trigger Architecture](architecture/decisions/ADR-004-registration-trigger-architecture.md) | Registration trigger selection (event vs command) | ✅ Complete |
| [RISK-009: CI Workflow Modification](architecture/decisions/RISK-009-ci-workflow-modification-risk.md) | Risk assessment for CI workflow changes | ✅ Complete |

---

## 📋 Reference

**Templates, APIs, and detailed specifications**

### Node Templates

**Production-ready templates for each node type**

| Document | Description | Status |
|----------|-------------|--------|
| [COMPUTE Node Template](guides/templates/COMPUTE_NODE_TEMPLATE.md) | Complete COMPUTE node template | ✅ Excellent |
| [EFFECT Node Template](guides/templates/EFFECT_NODE_TEMPLATE.md) | Complete EFFECT node template | ✅ Excellent |
| [REDUCER Node Template](guides/templates/REDUCER_NODE_TEMPLATE.md) | Complete REDUCER node template | ✅ Excellent |
| [ORCHESTRATOR Node Template](guides/templates/ORCHESTRATOR_NODE_TEMPLATE.md) | Complete ORCHESTRATOR node template | ✅ Excellent |
| [Enhanced Node Patterns](guides/templates/ENHANCED_NODE_PATTERNS.md) | Advanced patterns | ✅ Available |

### API Reference

| Document | Description | Status |
|----------|-------------|--------|
| [API Documentation](reference/API_DOCUMENTATION.md) | Core API reference | ✅ Available |
| [Nodes API](reference/api/NODES.md) | Node class APIs | ✅ Complete |
| [Models API](reference/api/MODELS.md) | Model class APIs | ✅ Complete |
| [Enums API](reference/api/ENUMS.md) | Enumeration reference | ✅ Complete |
| [Utils API](reference/api/UTILS.md) | Utility function reference | ✅ Complete |

### TypedDict Types (Serialization Boundaries)

**Location**: `omnibase_core.types`

TypedDict types provide strongly-typed dictionary schemas for serialization boundaries, replacing `dict[str, Any]` with explicit type contracts. These types are used at API boundaries, event serialization, and inter-process communication.

| Category | Types | Purpose |
|----------|-------|---------|
| **CLI Serialization** | `TypedDictCliActionSerialized`, `TypedDictCliAdvancedParamsSerialized`, `TypedDictCliCommandOptionSerialized`, `TypedDictCliExecutionCoreSerialized`, `TypedDictCliExecutionMetadataSerialized`, `TypedDictCliNodeExecutionInputSerialized` | CLI input/output serialization |
| **Validation** | `TypedDictValidationContainerSerialized`, `TypedDictValidationErrorSerialized`, `TypedDictValidationValueSerialized` | Validation result serialization |
| **Events** | `TypedDictEventEnvelopeDict` | Event envelope serialization |
| **Kubernetes** | `TypedDictK8sResources`, `TypedDictK8sDeployment`, `TypedDictK8sService`, `TypedDictK8sConfigMap` (and related K8s types) | Kubernetes resource definitions |
| **Performance** | `TypedDictPerformanceCheckpointResult`, `TypedDictLoadBalancerStats` | Performance metrics serialization |
| **Migration** | `TypedDictMigrationReport` | Migration result reporting |
| **Workflow** | `TypedDictWorkflowOutputs` | Workflow output serialization |
| **Policy** | `TypedDictPolicyValueData` | Policy configuration serialization |
| **Custom Fields** | `TypedDictCustomFields` | Extensible custom field serialization |
| **Model Values** | `TypedDictModelValueSerialized`, `TypedDictOutputFormatOptionsSerialized` | Model value serialization |

**Usage Pattern**:
```python
from omnibase_core.types import TypedDictValidationErrorSerialized

def serialize_error(error: ModelOnexError) -> TypedDictValidationErrorSerialized:
    """Serialize error with explicit type contract."""
    return {
        "error_code": error.error_code.value,
        "message": error.message,
        "context": error.context,
    }
```

**See**: [Type System](architecture/TYPE_SYSTEM.md) for type philosophy and patterns.

### Architecture Research

| Document | Description | Status |
|----------|-------------|--------|
| [Reference Overview](reference/README.md) | Reference materials overview | ✅ Available |
| [ONEX Mixin System Research](architecture/architecture-research/ONEX_MIXIN_SYSTEM_RESEARCH.md) | Mixin architecture | ✅ Available |
| [4-Node Architecture Research](architecture/architecture-research/RESEARCH_REPORT_4_NODE_ARCHITECTURE.md) | Architecture research | ✅ Available |
| [Mixin Architecture Patterns](architecture/mixin-architecture/ONEX_MIXIN_ARCHITECTURE_PATTERNS.md) | Mixin patterns | ✅ Available |

### Design Patterns

| Document | Description | Status |
|----------|-------------|--------|
| [Circuit Breaker Pattern](patterns/CIRCUIT_BREAKER_PATTERN.md) | Circuit breaker implementation | ✅ Available |
| [Configuration Management](patterns/CONFIGURATION_MANAGEMENT.md) | Config patterns | ✅ Available |
| [Performance Benchmarks](guides/PERFORMANCE_BENCHMARKS.md) | Performance testing | ✅ Available |

### Performance & Optimization

| Document | Description | Status |
|----------|-------------|--------|
| [**Performance Benchmark Thresholds**](performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md) | Threshold rationale, CI vs local, environment configuration ⭐ **NEW** | ✅ Complete |
| [Model Reducer Output Benchmarks](performance/MODEL_REDUCER_OUTPUT_BENCHMARKS.md) | ModelReducerOutput performance baselines | ✅ Complete |
| [Source Node ID Benchmarks](performance/SOURCE_NODE_ID_BENCHMARKS.md) | source_node_id field overhead analysis | ✅ Complete |
| [**Performance Benchmark CI Integration**](ci/PERFORMANCE_BENCHMARK_CI_INTEGRATION.md) | CI pipeline integration, threshold enforcement, regression detection ⭐ **NEW** | ✅ Complete |

### Changelog

| Document | Description | Status |
|----------|-------------|--------|
| [CHANGELOG.md](../CHANGELOG.md) | All notable changes following [Keep a Changelog](https://keepachangelog.com) format | ✅ Current |

---

## 📖 Standards & Conventions

**Canonical references and project-wide standards**

| Document | Description | Status |
|----------|-------------|--------|
| [**ONEX Terminology Guide**](standards/onex_terminology.md) | Canonical definitions for Event, Intent, Action, Reducer, Orchestrator, Effect, Handler, Projection, Runtime | ✅ Complete |

---

## 🔧 Specialized Topics

**Deep dives into specific topics**

### Error Handling

| Document | Description | Status |
|----------|-------------|--------|
| [**Error Handling Best Practices**](conventions/ERROR_HANDLING_BEST_PRACTICES.md) | Comprehensive error handling guide | ✅ Excellent |
| [Anti-Patterns](patterns/ANTI_PATTERNS.md) | What to avoid | ✅ Available |

### Security & Validation

| Document | Description | Status |
|----------|-------------|--------|
| [**Security Validators**](../scripts/validation/README.md) | Secret detection and environment variable validation | ✅ Complete |

### Concurrency & Threading

| Document | Description | Status |
|----------|-------------|--------|
| [**Threading Guide**](guides/THREADING.md) | Thread safety and concurrency | ✅ Excellent |

### Testing & CI

| Document | Description | Status |
|----------|-------------|--------|
| [**CI Monitoring Guide**](ci/CI_MONITORING_GUIDE.md) | CI performance monitoring, alerting, and investigation | ✅ Complete |
| [**Performance Benchmark CI Integration**](ci/PERFORMANCE_BENCHMARK_CI_INTEGRATION.md) | CI pipeline integration, threshold enforcement, regression detection ⭐ **NEW** | ✅ Complete |
| [**Node Purity Failure Guide**](ci/CORE_PURITY_FAILURE.md) | Interpreting and fixing CI purity check failures | ✅ Complete |
| [**Deprecation Warnings**](ci/DEPRECATION_WARNINGS.md) | Deprecation warning configuration and v0.5.0 migration path | ✅ Complete |
| [**Integration Testing Guide**](testing/INTEGRATION_TESTING.md) | Integration test patterns, structure, and best practices | ✅ Complete |
| [CI Test Strategy](testing/CI_TEST_STRATEGY.md) | CI/CD test strategy and optimization | ✅ Complete |
| [Parallel Testing](testing/PARALLEL_TESTING.md) | Parallel test execution configuration | ✅ Complete |
| [Testing Guide](guides/TESTING_GUIDE.md) | Comprehensive testing strategies | ✅ Complete |

### Troubleshooting & Debugging

| Document | Description | Status |
|----------|-------------|--------|
| [**Async Hang Debugging**](troubleshooting/ASYNC_HANG_DEBUGGING.md) | Diagnose and fix async/event loop hangs in tests | ✅ Complete |

### Standards

| Document | Description | Status |
|----------|-------------|--------|
| [**ONEX Topic Taxonomy**](standards/onex_topic_taxonomy.md) | Kafka topic naming convention and configuration | ✅ Complete |

### Architecture Patterns

| Document | Description | Status |
|----------|-------------|--------|
| [**Subcontract Architecture**](architecture/SUBCONTRACT_ARCHITECTURE.md) | Contract system design | ✅ Excellent |
| [Approved Union Patterns](patterns/APPROVED_UNION_PATTERNS.md) | Type union patterns | ✅ Available |

### Project Documentation

| Document | Description | Status |
|----------|-------------|--------|
| [Production Cache Tuning](guides/PRODUCTION_CACHE_TUNING.md) | Cache optimization | ✅ Available |
| [Documentation Validation Report](quality/DOCUMENTATION_VALIDATION_REPORT.md) | Doc quality report | ✅ Available |

---

## 🎯 Common Tasks

**Quick links for common development tasks**

### I want to...

| Task | Go To |
|------|-------|
| **Build my first node** | [Node Building Guide](guides/node-building/README.md) → [COMPUTE Tutorial](guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) |
| **Understand node types** | [Node Types](guides/node-building/02_NODE_TYPES.md) |
| **Choose the right base class** | [Node Class Hierarchy](architecture/NODE_CLASS_HIERARCHY.md) |
| **Use a production template** | [Node Templates](guides/templates/COMPUTE_NODE_TEMPLATE.md) |
| **Handle errors properly** | [Error Handling Best Practices](conventions/ERROR_HANDLING_BEST_PRACTICES.md) |
| **Secure my code** | [Security Validators](../scripts/validation/README.md) |
| **Make nodes thread-safe** | [Threading Guide](guides/THREADING.md) |
| **Understand the architecture** | [ONEX Four-Node Architecture](architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| **Test my node** | [Testing Guide](guides/TESTING_GUIDE.md) |
| **Write integration tests** | [Integration Testing Guide](testing/INTEGRATION_TESTING.md) |
| **Monitor CI performance** | [CI Monitoring Guide](ci/CI_MONITORING_GUIDE.md) |
| **Fix CI purity failures** | [Node Purity Failure Guide](ci/CORE_PURITY_FAILURE.md) |
| **Understand performance thresholds** | [Performance Benchmark Thresholds](performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md) |
| **Fix slow performance tests** | [Performance Benchmark Thresholds](performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md#ci-performance-degradation) |
| **Debug async hangs** | [Async Hang Debugging](troubleshooting/ASYNC_HANG_DEBUGGING.md) |
| **Understand contracts** | [Subcontract Architecture](architecture/SUBCONTRACT_ARCHITECTURE.md) |
| **Use TypedDict for serialization** | [TypedDict Types](#typeddict-types-serialization-boundaries) - Strongly-typed serialization boundaries |
| **Validate mixin metadata** | [ModelMixinMetadata](../src/omnibase_core/models/core/model_mixin_metadata.py) - Mixin discovery & validation |
| **Validate docker-compose.yaml** | [ModelDockerComposeManifest](../src/omnibase_core/models/docker/model_docker_compose_manifest.py) - Docker validation |

---

## Development Resources

**Structured documentation for building ONEX nodes**

### Quick Start Resources

- **[Node Building Guide](guides/node-building/README.md)** - Structured, parseable, step-by-step
- **[Node Templates](guides/node-building/10_AGENT_TEMPLATES.md)** - Copy-paste ready templates
- **[Node Templates](guides/templates/COMPUTE_NODE_TEMPLATE.md)** - Production-ready reference implementations

### Development Workflow

1. Read [What is a Node?](guides/node-building/01_WHAT_IS_A_NODE.md) for concepts
2. Read [Node Types](guides/node-building/02_NODE_TYPES.md) to choose type
3. Follow type-specific tutorial:
   - [COMPUTE](guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) ✅
   - [EFFECT](guides/node-building/04_EFFECT_NODE_TUTORIAL.md) ✅
   - [REDUCER](guides/node-building/05_REDUCER_NODE_TUTORIAL.md) ✅
   - [ORCHESTRATOR](guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md) ✅
4. Use [Patterns Catalog](guides/node-building/07_PATTERNS_CATALOG.md) for common patterns
5. Test with [Testing Guide](guides/TESTING_GUIDE.md)

---

## 📝 Documentation Status

### Completion Overview

| Category | Complete | In Progress | Planned | Total |
|----------|----------|-------------|---------|-------|
| **Getting Started** | 3 | 0 | 0 | 3 |
| **Node Building** | 10 | 0 | 0 | 10 |
| **Architecture** | 18 | 0 | 0 | 18 |
| **Reference** | 14 | 0 | 0 | 14 |
| **Standards** | 1 | 0 | 0 | 1 |
| **Specialized** | 13 | 0 | 0 | 13 |
| **TOTAL** | **59** | **0** | **0** | **59** |

**Overall Progress**: 100% complete (59/59 documents)

### Priority Items

**Completed**:
- ✅ Node Building Guide (10/10 complete)
- ✅ Getting Started guides (3/3 complete)
- ✅ Architecture documentation (18/18 complete)
- ✅ Testing Guide
- ✅ Integration Testing Guide
- ✅ All node tutorials (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)
- ✅ Agent Templates (AI-optimized node templates)

---

## 🔍 Finding What You Need

### By Role

**New Developer**:
1. [Installation](getting-started/INSTALLATION.md) → [Quick Start](getting-started/QUICK_START.md) → [First Node](getting-started/FIRST_NODE.md)

**Experienced Developer**:
1. [Node Building Guide](guides/node-building/README.md) → Choose tutorial → Build

**Architect**:
1. [ONEX Four-Node Architecture](architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) → [Architecture Research](architecture/architecture-research/RESEARCH_REPORT_4_NODE_ARCHITECTURE.md)

**AI Agent**:
1. [Node Building Guide](guides/node-building/README.md) → [Agent Templates](guides/node-building/10_AGENT_TEMPLATES.md)

### By Task

**Building**:
- Nodes: [Node Building Guide](guides/node-building/README.md)
- Tests: [Testing Guide](guides/TESTING_GUIDE.md)
- Workflows: [ORCHESTRATOR Tutorial](guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)

**Learning**:
- Concepts: [What is a Node?](guides/node-building/01_WHAT_IS_A_NODE.md)
- Architecture: [ONEX Four-Node Architecture](architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- Patterns: [Patterns Catalog](guides/node-building/07_PATTERNS_CATALOG.md)

**Debugging**:
- Errors: [Error Handling](conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- Async Hangs: [Async Hang Debugging](troubleshooting/ASYNC_HANG_DEBUGGING.md)
- Performance: [Production Cache Tuning](guides/PRODUCTION_CACHE_TUNING.md)
- Threading: [Threading Guide](guides/THREADING.md)

---

## 🔗 External Resources

- **omnibase_core Repository**: [GitHub](https://github.com/OmniNode-ai/omnibase_core)
- **ONEX Ecosystem**: [Documentation](https://onex-framework.dev)
- **Poetry Documentation**: [python-poetry.org](https://python-poetry.org/)
- **Pydantic Documentation**: [pydantic.dev](https://pydantic.dev/)

---

## 📞 Getting Help

- **Documentation Issues**: File an issue in the repository
- **Questions**: Check existing documentation first, then ask
- **Contributions**: See [Contributing Guide](../CONTRIBUTING.md)

---

## 📚 Documentation Architecture

See [Documentation Architecture](architecture/DOCUMENTATION_ARCHITECTURE.md) for information about:
- Documentation organization
- Writing standards
- Maintenance strategy
- Quality gates

---

**Last Updated**: 2025-12-17
**Documentation Version**: 1.1.0
**Framework Version**: omnibase_core 0.4.0+

---

**Ready to start?** → [Node Building Guide](guides/node-building/README.md) ⭐
