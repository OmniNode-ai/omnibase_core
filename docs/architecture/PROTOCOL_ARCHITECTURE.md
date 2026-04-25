> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Protocol Architecture

# Protocol Architecture

**Owner:** `omnibase_core`
**Status:** Current
**Last refreshed:** 2026-04-24

`omnibase_core` owns Core-native protocol interfaces that define structural
contracts used inside the Core package. These protocols keep Core isolated from
transport, deployment, and infrastructure implementations.

## Current Dependency Direction

The current dependency direction is:

```text
omnibase_core  <-  omnibase_spi  <-  omnibase_infra
```

- `omnibase_core` defines Core models, validators, node runtime vocabulary, and
  Core-native protocols.
- `omnibase_spi` depends on Core and may extend Core protocols for downstream
  service-provider interfaces.
- `omnibase_infra` implements SPI and runtime infrastructure using concrete
  libraries such as Kafka, Postgres, Infisical, Docker, and deployment tooling.

Core must not import `omnibase_spi` or `omnibase_infra`.

## What Belongs In Core Protocols

Core protocol files should describe package-internal structural behavior needed
by Core models, validators, services, handlers, and runtime helpers.

Appropriate Core protocol examples:

- Validator and checker interfaces used by Core validation tooling.
- Runtime-checkable structural interfaces needed by Core execution helpers.
- Lightweight protocols that avoid coupling Core to implementation classes.

Do not add protocols here just because a downstream repo needs an interface.
Cross-service or implementation-facing protocols belong in `omnibase_spi`.

## Current Protocol Locations

Use `src/omnibase_core/protocols/` for protocol modules that are intentionally
public within the Core architecture. Some legacy or narrow protocol definitions
may still live near their consuming modules; promote them only when multiple Core
modules need the same contract.

Related docs:

- [Dependency Inversion](DEPENDENCY_INVERSION.md)
- [Import Compatibility Matrix](IMPORT_COMPATIBILITY_MATRIX.md)
- [Validation Protocol Compliance](VALIDATION_PROTOCOL_COMPLIANCE.md)
- [ADR-001: Protocol-Based Dependency Injection](../decisions/ADR-001-protocol-based-di-architecture.md)

## Historical Material

The old protocol architecture audit was removed from primary Core docs during
the OMN-9599 documentation refresh. The current repository-relevant truth is
captured above: Core owns Core-native protocols; SPI depends on Core; Core must
not import SPI or infrastructure implementations.
