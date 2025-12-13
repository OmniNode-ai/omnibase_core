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

### Changelog

| Document | Description | Status |
|----------|-------------|--------|
| [CHANGELOG.md](../CHANGELOG.md) | All notable changes following [Keep a Changelog](https://keepachangelog.com) format | ✅ Current |

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
| [**Node Purity Failure Guide**](ci/CORE_PURITY_FAILURE.md) | Interpreting and fixing CI purity check failures | ✅ Complete |
| [CI Test Strategy](testing/CI_TEST_STRATEGY.md) | CI/CD test strategy and optimization | ✅ Complete |
| [Parallel Testing](testing/PARALLEL_TESTING.md) | Parallel test execution configuration | ✅ Complete |
| [Testing Guide](guides/TESTING_GUIDE.md) | Comprehensive testing strategies | ✅ Complete |

### Troubleshooting & Debugging

| Document | Description | Status |
|----------|-------------|--------|
| [**Async Hang Debugging**](troubleshooting/ASYNC_HANG_DEBUGGING.md) | Diagnose and fix async/event loop hangs in tests | ✅ Complete |

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
| **Monitor CI performance** | [CI Monitoring Guide](ci/CI_MONITORING_GUIDE.md) |
| **Fix CI purity failures** | [Node Purity Failure Guide](ci/CORE_PURITY_FAILURE.md) |
| **Debug async hangs** | [Async Hang Debugging](troubleshooting/ASYNC_HANG_DEBUGGING.md) |
| **Understand contracts** | [Subcontract Architecture](architecture/SUBCONTRACT_ARCHITECTURE.md) |
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
| **Architecture** | 13 | 0 | 0 | 13 |
| **Reference** | 13 | 0 | 0 | 13 |
| **Specialized** | 11 | 0 | 0 | 11 |
| **TOTAL** | **50** | **0** | **0** | **50** |

**Overall Progress**: 100% complete (50/50 documents)

### Priority Items

**Completed**:
- ✅ Node Building Guide (10/10 complete)
- ✅ Getting Started guides (3/3 complete)
- ✅ Architecture documentation (13/13 complete)
- ✅ Testing Guide
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

**Last Updated**: 2025-12-06
**Documentation Version**: 1.1.0
**Framework Version**: omnibase_core 0.4.0+

---

**Ready to start?** → [Node Building Guide](guides/node-building/README.md) ⭐
