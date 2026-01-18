> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Documentation Architecture

# Documentation Architecture - omnibase_core

**Status**: Active
**Version**: 1.0.0
**Last Updated**: 2025-01-18

## Overview

This document defines the comprehensive documentation architecture for the omnibase_core repository, designed for developers building with the ONEX framework.

## Design Principles

1. **Progressive Disclosure**: Start simple, layer complexity
2. **Agent-Friendly**: Structured formats AI agents can easily parse and replicate
3. **Code-First**: Real examples from actual implementations
4. **Searchable**: Clear hierarchy and cross-references
5. **Maintainable**: Co-located with code, versioned, tested

## Documentation Structure

```
docs/
├── INDEX.md                          # Main navigation hub
├── DOCUMENTATION_ARCHITECTURE.md     # This file
│
├── getting-started/                  # New developer onboarding
│   ├── README.md                     # Getting started overview
│   ├── INSTALLATION.md               # Environment setup with Poetry
│   ├── QUICK_START.md                # 5-minute first steps
│   └── FIRST_NODE.md                 # Build your first node
│
├── guides/                           # Developer guides and tutorials
│   ├── node-building/                # **CRITICAL PRIORITY**
│   │   ├── README.md                 # Node building guide overview
│   │   ├── 01_WHAT_IS_A_NODE.md      # Fundamentals
│   │   ├── 02_NODE_TYPES.md          # EFFECT, COMPUTE, REDUCER, ORCHESTRATOR
│   │   ├── 03_COMPUTE_NODE_TUTORIAL.md   # Step-by-step COMPUTE
│   │   ├── 04_EFFECT_NODE_TUTORIAL.md    # Step-by-step EFFECT
│   │   ├── 05_REDUCER_NODE_TUTORIAL.md   # Step-by-step REDUCER
│   │   ├── 06_ORCHESTRATOR_NODE_TUTORIAL.md  # Step-by-step ORCHESTRATOR
│   │   ├── 07-patterns-catalog.md    # Common patterns library
│   │   ├── 08-TESTING_GUIDE.md       # Testing each node type
│   │   ├── 09-common-pitfalls.md     # What to avoid
│   │   └── 10-agent-templates.md     # Agent-friendly structured templates
│   ├── development-workflow.md       # Development process
│   ├── TESTING_GUIDE.md              # Comprehensive testing
│   └── debugging-guide.md            # Debugging strategies
│
├── architecture/                     # System architecture
│   ├── overview.md                   # Architecture overview
│   ├── four-node-pattern.md          # Link to ONEX_FOUR_NODE_ARCHITECTURE.md
│   ├── dependency-injection.md       # ModelONEXContainer patterns
│   ├── CONTRACT_SYSTEM.md            # Contract architecture
│   └── type-system.md                # Typing patterns
│
├── reference/                        # Reference materials (existing)
│   ├── README.md                     # Reference overview
│   ├── templates/                    # Detailed templates (existing)
│   │   ├── COMPUTE_NODE_TEMPLATE.md
│   │   ├── EFFECT_NODE_TEMPLATE.md
│   │   ├── REDUCER_NODE_TEMPLATE.md
│   │   ├── ORCHESTRATOR_NODE_TEMPLATE.md
│   │   └── ENHANCED_NODE_PATTERNS.md
│   ├── architecture-research/        # Design decisions (existing)
│   ├── patterns/                     # Design patterns (existing)
│   ├── mixin-architecture/           # Mixin system (existing)
│   └── api/                          # API reference (new)
│       ├── nodes.md                  # Node API reference
│       ├── models.md                 # Model API reference
│       ├── enums.md                  # Enum reference
│       └── utils.md                  # Utility reference
│
├── ONEX_FOUR_NODE_ARCHITECTURE.md    # Core architecture (existing, excellent)
├── ERROR_HANDLING_BEST_PRACTICES.md  # Error handling (existing)
├── THREADING.md                      # Threading guide (existing)
├── SUBCONTRACT_ARCHITECTURE.md       # Subcontracts (existing)
├── API_DOCUMENTATION.md              # API docs (existing)
├── MIGRATION_GUIDE.md                # Migration guide (existing)
│
└── reports/                          # Analysis reports (existing)
    └── (various analysis reports)
```

## Document Types

### 1. Getting Started (New Developer Focus)

**Target Audience**: Developers new to omnibase_core
**Format**: Tutorial-style with code examples
**Key Documents**:
- INSTALLATION.md - Environment setup
- QUICK_START.md - First 5 minutes
- FIRST_NODE.md - Build a simple node

### 2. Guides (Progressive Learning)

**Target Audience**: Developers building with ONEX
**Format**: Step-by-step tutorials with real code
**Key Documents**:
- node-building/* - **CRITICAL PRIORITY** comprehensive node guide
- development-workflow.md - Development process
- TESTING_GUIDE.md - Testing strategies

### 3. Architecture (Understanding the System)

**Target Audience**: Developers needing deep understanding
**Format**: Conceptual with diagrams and examples
**Key Documents**:
- four-node-pattern.md - Core pattern
- dependency-injection.md - DI patterns
- CONTRACT_SYSTEM.md - Contract architecture

### 4. Reference (Lookup and Templates)

**Target Audience**: Developers needing specific information
**Format**: Structured reference, API docs, templates
**Key Documents**:
- templates/* - Production-ready templates
- api/* - API reference documentation

## Critical Priority: Node Building Guide

The node building guide is the **highest priority** deliverable. It must be:

1. **Comprehensive**: Cover all 4 node types in depth
2. **Progressive**: Start simple, add complexity
3. **Code-First**: Real examples from actual nodes
4. **Agent-Friendly**: Structured for AI replication
5. **Testing-Focused**: How to test each pattern

### Node Building Guide Structure

```
guides/node-building/
├── README.md                           # Overview and navigation
├── 01_WHAT_IS_A_NODE.md                # Definition, purpose, role in ONEX
├── 02_NODE_TYPES.md                    # EFFECT, COMPUTE, REDUCER, ORCHESTRATOR
├── 03_COMPUTE_NODE_TUTORIAL.md         # Step-by-step COMPUTE
├── 04_EFFECT_NODE_TUTORIAL.md          # Step-by-step EFFECT
├── 05_REDUCER_NODE_TUTORIAL.md         # Step-by-step REDUCER
├── 06_ORCHESTRATOR_NODE_TUTORIAL.md    # Step-by-step ORCHESTRATOR
├── 07-patterns-catalog.md              # Common patterns with code
├── 08-TESTING_GUIDE.md                 # Testing each node type
├── 09-common-pitfalls.md               # What to avoid
└── 10-agent-templates.md               # Agent-friendly templates
```

### Agent-Friendly Format Requirements

Each tutorial must include:

1. **Clear Objectives**: What you'll build
2. **Prerequisites**: Required knowledge/setup
3. **Step-by-Step Instructions**: Numbered, actionable steps
4. **Complete Code Examples**: Copy-paste ready
5. **Explanation Blocks**: Why each step matters
6. **Common Errors**: What to watch for
7. **Testing Validation**: How to verify success
8. **Pattern Summary**: Reusable template at end

## Documentation Standards

### File Naming

- Use lowercase with hyphens: `node-building-guide.md`
- Number tutorial sequences: `01_WHAT_IS_A_NODE.md`
- Descriptive names: `compute-node-tutorial.md` not `tutorial1.md`

### Code Examples

- **Always use Poetry**: `poetry run pytest`, `poetry add`, etc.
- **Real code**: From actual implementations, not pseudo-code
- **Fully typed**: Show complete type annotations
- **Error handling**: Include proper error handling
- **Comments**: Explain non-obvious logic

### Cross-References

- Use relative links: `[Architecture](../architecture/overview.md)`
- Link to source: `[NodeCompute](../../src/omnibase_core/nodes/node_compute.py)`
- Reference line numbers when useful

### Formatting

- **Markdown**: All documentation in Markdown
- **Code blocks**: Always specify language (```python)
- **Tables**: For comparisons and specifications
- **Diagrams**: ASCII art or Mermaid for diagrams
- **Admonitions**: Use blockquotes for warnings/notes

## Maintenance Strategy

### Versioning

- Major version bump: Breaking changes to architecture
- Minor version bump: New sections added
- Patch version bump: Corrections and clarifications

### Review Cycle

- **Quarterly**: Review all documentation for accuracy
- **On release**: Update for any breaking changes
- **On request**: Community feedback incorporation

### Quality Gates

Before publishing documentation:

1. ✅ Code examples tested and working
2. ✅ Links verified (no 404s)
3. ✅ Spelling and grammar checked
4. ✅ Agent replication tested (if applicable)
5. ✅ Peer review completed

## Migration Plan

### Phase 1: Critical Foundations (Week 1)
- ✅ Create directory structure
- [ ] Build comprehensive node building guide (CRITICAL)
- [ ] Create getting started guides
- [ ] Create INDEX.md navigation

### Phase 2: Developer Experience (Week 2)
- [ ] Build development workflow guide
- [ ] Build testing guide
- [ ] Build debugging guide
- [ ] Audit and update existing docs

### Phase 3: Reference and Polish (Week 3)
- [ ] Build API reference documentation
- [ ] Create architecture guides
- [ ] Cross-reference all documents
- [ ] Quality validation and review

## Success Metrics

### Quantitative

- **Coverage**: >95% of core functionality documented
- **Accuracy**: Code examples have 100% success rate
- **Findability**: <3 clicks to any information
- **Agent Success**: AI agents can build nodes with >90% success rate

### Qualitative

- **Developer Feedback**: Positive feedback on ease of use
- **Contribution Rate**: Increased community contributions
- **Question Reduction**: Fewer repetitive questions in issues/discussions

## Ownership

- **Maintainer**: Documentation team
- **Contributors**: All ONEX developers
- **Reviewers**: Core team + community
- **Agent Testing**: AI agents validate tutorials

## Related Documents

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) - Core architecture
- [Threading Guide](../guides/THREADING.md) - Thread safety
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error patterns
- [API Documentation](../reference/API_DOCUMENTATION.md) - API reference

---

**Next Steps**: See [Documentation Roadmap](#migration-plan) for implementation phases.
