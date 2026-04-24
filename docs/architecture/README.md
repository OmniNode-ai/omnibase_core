# Core Architecture Docs

**Owner:** `omnibase_core`
**Last mapped:** 2026-04-24
**Mapping source:** OMN-9599 entrypoint pass

This is the architecture entrypoint for `omnibase_core`. It is a first-pass map
of the architecture docs, not a line-by-line content audit of every page. Use it
to find the likely current docs first and to keep migration, refactor, and
research docs from being mistaken for primary entrypoints.

## Current Architecture

Start with these docs for current Core behavior and ownership. If a page
conflicts with `README.md`, `CLAUDE.md`, or current code, treat the conflict as
follow-up documentation debt rather than silently trusting the older page.

| Document | Current use |
|----------|-------------|
| [Architecture Overview](overview.md) | High-level Core system shape. |
| [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) | Canonical EFFECT, COMPUTE, REDUCER, ORCHESTRATOR vocabulary. |
| [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md) | Allowed and forbidden execution/data-flow shapes. |
| [Execution Shape Examples](EXECUTION_SHAPE_EXAMPLES.md) | Concrete examples of valid shapes. |
| [Node Class Hierarchy](NODE_CLASS_HIERARCHY.md) | Node class inheritance and public node surface. |
| [Container Types](CONTAINER_TYPES.md) | Container model distinctions. |
| [Dependency Injection](DEPENDENCY_INJECTION.md) | Current DI guidance. |
| [Contract System](CONTRACT_SYSTEM.md) | Core contract architecture. |
| [Subcontract Architecture](SUBCONTRACT_ARCHITECTURE.md) | Subcontract system design. |
| [Protocol Architecture](PROTOCOL_ARCHITECTURE.md) | Protocol design within Core. |
| [Handler Architecture](HANDLER_ARCHITECTURE.md) | Handler routing and execution design. |
| [Mixin Architecture](MIXIN_ARCHITECTURE.md) | Current mixin system behavior and migration context. |
| [Message Topic Mapping](MESSAGE_TOPIC_MAPPING.md) | Event, command, and intent topic mapping. |
| [Validation Ownership](../reference/VALIDATION_OWNERSHIP.md) | Core-owned validator entrypoints and downstream consumption. |

## Boundary Docs

Use these docs when deciding whether something belongs in Core or a downstream
repo. These are boundary references, not proof that every linked page has been
fully reconciled.

| Document | Boundary |
|----------|----------|
| [Dependency Inversion](DEPENDENCY_INVERSION.md) | Core abstraction and dependency-direction guidance. |
| [Import Compatibility Matrix](IMPORT_COMPATIBILITY_MATRIX.md) | Import expectations and compatibility notes. |
| [Validation Protocol Compliance](VALIDATION_PROTOCOL_COMPLIANCE.md) | Protocol compliance validation. |
| [Contract Stability Spec](CONTRACT_STABILITY_SPEC.md) | Contract stability expectations. |
| [Model Intent Architecture](MODEL_INTENT_ARCHITECTURE.md) | Intent model ownership and routing context. |
| [Model Action Architecture](MODEL_ACTION_ARCHITECTURE.md) | Action model ownership and routing context. |
| [Envelope Flow Architecture](ENVELOPE_FLOW_ARCHITECTURE.md) | Envelope flow model. |
| [Payload Type Architecture](PAYLOAD_TYPE_ARCHITECTURE.md) | Payload typing model. |

## Migration Or Refactor Context

These docs contain durable migration or classification guidance that is still
useful in Core. Historical reports, design drafts, registration design files,
old contract-driven node specs, and research reports are not primary Core
architecture. Any current repository-relevant truth from those files must be
kept here in stable Core docs rather than delegated to historical material.

| Document | Treat as |
|----------|----------|
| [Mixin to Capability Migration](MIXIN_TO_CAPABILITY_MIGRATION.md) | Migration context. |
| [Mixins to Handlers Refactor](MIXINS_TO_HANDLERS_REFACTOR.md) | Refactor context. |
| [Mixin Inventory](MIXIN_INVENTORY.md) | Inventory/context. |
| [Mixin Classification](MIXIN_CLASSIFICATION.md) | Classification context. |
| [Handler Classification File I/O Services 3/4](HANDLER_CLASSIFICATION_FILE_IO_SERVICES_3_4.md) | Classification/refactor context. |

## Removed From Core

Removed historical/design material is retained only as background context
outside the primary Core documentation surface. Do not rely on it for current
behavior.

Promote content into Core only by extracting current truth into a stable
architecture, reference, decision, or migration document in this repository.

## Promotion Rule

When a migration, refactor, delta, design, or research doc still describes current
runtime behavior, extract the durable truth into a current architecture,
reference, or decision doc and link back to the source as history.
