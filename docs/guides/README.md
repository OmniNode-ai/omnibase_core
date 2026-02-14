> **Navigation**: [Home](../INDEX.md) > Guides

# Guides

This section contains comprehensive guides for ONEX development, covering node building, migrations, testing, performance, and more. For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

## Guide Collections

### Node Building

Complete tutorials for building production-ready ONEX nodes.

| Guide | Description |
|-------|-------------|
| [Node Building Guide](./node-building/README.md) | Comprehensive guide covering EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR nodes |

### Templates

Code templates and patterns for rapid node development.

| Template | Description |
|----------|-------------|
| [COMPUTE Node Template](./templates/COMPUTE_NODE_TEMPLATE.md) | Production-ready template for COMPUTE nodes |
| [EFFECT Node Template](./templates/EFFECT_NODE_TEMPLATE.md) | Production-ready template for EFFECT nodes |
| [REDUCER Node Template](./templates/REDUCER_NODE_TEMPLATE.md) | Production-ready template for REDUCER nodes |
| [ORCHESTRATOR Node Template](./templates/ORCHESTRATOR_NODE_TEMPLATE.md) | Production-ready template for ORCHESTRATOR nodes |
| [Enhanced Node Patterns](./templates/ENHANCED_NODE_PATTERNS.md) | Advanced patterns for complex node implementations |

### Mixin Development

Guides for creating reusable cross-cutting concerns.

| Guide | Description |
|-------|-------------|
| [Mixin Development Guide](./mixin-development/README.md) | Complete guide for creating production-ready mixins |

### Replay Safety

Guides for idempotent and replay-safe implementations.

| Guide | Description |
|-------|-------------|
| [Replay Safety Integration](./replay/REPLAY_SAFETY_INTEGRATION.md) | Ensuring idempotency and replay safety in nodes |

## Individual Guides

### Migration Guides

Step-by-step guides for upgrading to new patterns and APIs.

| Guide | Description |
|-------|-------------|
| [Migrating to Declarative Nodes](./MIGRATING_TO_DECLARATIVE_NODES.md) | Migrate from imperative to declarative node implementations |
| [Enum Node Kind Migration](./ENUM_NODE_KIND_MIGRATION.md) | Migrate to EnumNodeKind for architectural classification |
| [ISP Protocol Migration](./ISP_PROTOCOL_MIGRATION.md) | Interface Segregation Principle protocol migration |
| [Protocol UUID Migration](./PROTOCOL_UUID_MIGRATION.md) | Migrate to protocol-based UUID handling |
| [Migrating from Dict Any](./MIGRATING_FROM_DICT_ANY.md) | Replace `dict[str, Any]` with typed models |
| [Migrating to Mixin Event Bus v0.4](./MIGRATING_TO_MIXIN_EVENT_BUS_V0_4.md) | Update to v0.4 event bus mixin patterns |
| [Union Type Migration](./UNION_TYPE_MIGRATION.md) | Migrate to PEP 604 union syntax |
| [Handler Conversion Guide](./HANDLER_CONVERSION_GUIDE.md) | Convert legacy handlers to new patterns |
| [Handler Conversion Checklist](./HANDLER_CONVERSION_CHECKLIST.md) | Checklist for handler conversion |

### Contract and Subcontract Guides

Working with ONEX contracts and subcontracts.

| Guide | Description |
|-------|-------------|
| [Contract Patching Guide](./CONTRACT_PATCHING_GUIDE.md) | Patching and extending ONEX contracts |
| [Contract Profile Guide](./CONTRACT_PROFILE_GUIDE.md) | Working with contract profiles |
| [Effect Subcontract Guide](./EFFECT_SUBCONTRACT_GUIDE.md) | Comprehensive guide to EFFECT subcontracts |
| [Mixin Subcontract Mapping](./MIXIN_SUBCONTRACT_MAPPING.md) | Mapping mixins to subcontracts |

### Architecture and Development Guides

Core development patterns and practices.

| Guide | Description |
|-------|-------------|
| [Effect Boundary Guide](./EFFECT_BOUNDARY_GUIDE.md) | Managing side effects and I/O boundaries |
| [Declarative Node Import Rules](./DECLARATIVE_NODE_IMPORT_RULES.md) | Import conventions for declarative nodes |
| [Custom Callable Patterns](./CUSTOM_CALLABLE_PATTERNS.md) | Patterns for custom callable implementations |
| [Protocol Discovery Guide](./PROTOCOL_DISCOVERY_GUIDE.md) | Service discovery via protocols |
| [Pipeline Hook Registry](./PIPELINE_HOOK_REGISTRY.md) | Registering and using pipeline hooks |
| [Execution Corpus Guide](./EXECUTION_CORPUS_GUIDE.md) | Working with execution corpora |
| [Version Field Automation Strategy](./VERSION_FIELD_AUTOMATION_STRATEGY.md) | Automating version field management |

### Testing and Performance Guides

Testing strategies and performance optimization.

| Guide | Description |
|-------|-------------|
| [Testing Guide](./TESTING_GUIDE.md) | Comprehensive testing strategies for ONEX |
| [Intent Publisher Testing Documentation](./INTENT_PUBLISHER_TESTING_DOCUMENTATION.md) | Testing intent publishers |
| [Performance Benchmarks](./PERFORMANCE_BENCHMARKS.md) | Performance benchmarking guidelines |
| [Production Cache Tuning](./PRODUCTION_CACHE_TUNING.md) | Cache optimization for production |
| [Request Tracing](./REQUEST_TRACING.md) | Distributed request tracing |
| [Threading](./THREADING.md) | Thread safety and concurrent execution |

## Quick Reference

### Getting Started Path

```text
New to ONEX?
  1. Node Building Guide -> Learn the fundamentals
  2. Node Templates -> Start from production-ready code
  3. Testing Guide -> Ensure quality

Building a new node?
  1. Choose node type (EFFECT/COMPUTE/REDUCER/ORCHESTRATOR)
  2. Use appropriate template from templates/
  3. Follow Testing Guide for validation

Upgrading existing code?
  1. Check relevant Migration Guide
  2. Use Handler Conversion Checklist
  3. Run validation tests
```

### Guide Selection by Task

| Task | Recommended Guide |
|------|-------------------|
| Building first node | [Node Building Guide](./node-building/README.md) |
| Using a template | [Templates](./templates/) |
| Creating a mixin | [Mixin Development Guide](./mixin-development/README.md) |
| Upgrading to v0.4.0 | [Migrating to Declarative Nodes](./MIGRATING_TO_DECLARATIVE_NODES.md) |
| Improving performance | [Performance Benchmarks](./PERFORMANCE_BENCHMARKS.md), [Production Cache Tuning](./PRODUCTION_CACHE_TUNING.md) |
| Thread safety | [Threading](./THREADING.md) |
| Testing nodes | [Testing Guide](./TESTING_GUIDE.md) |

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [ONEX Patterns](../patterns/README.md)
- [ONEX Conventions](../conventions/NAMING_CONVENTIONS.md)
- [ONEX Standards](../standards/onex_terminology.md)

---

**Last Updated**: 2026-01-18 | **Maintainer**: ONEX Core Team
