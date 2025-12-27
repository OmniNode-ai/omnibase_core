# SPI Protocol Adoption Roadmap

**Status:** HISTORICAL - Superseded by Dependency Inversion (v0.3.6)
**Original Date:** 2025-10-21
**Updated:** 2025-12-18

> **IMPORTANT (v0.3.6+)**: This document is **HISTORICAL** and no longer reflects the
> current architecture. As of v0.3.6, the dependency was **inverted** - SPI now depends
> on Core, not the reverse.
> **What Changed**:
> - Protocol definitions moved from `omnibase_spi` to `omnibase_core.protocols`
> - `omnibase_core` is now the source of truth for all protocol interfaces
> - SPI imports Core protocols (not the other way around)
> **Current Documentation**:
> - [Import Compatibility Matrix](IMPORT_COMPATIBILITY_MATRIX.md) - Current import paths
> - [Protocol Architecture](PROTOCOL_ARCHITECTURE.md) - Updated protocol documentation
> - [Dependency Inversion](DEPENDENCY_INVERSION.md) - Current architecture patterns
> The content below is preserved for historical reference only.

---

## Summary (Historical)

This roadmap was created when omnibase_core depended on omnibase_spi for protocol definitions.
This is no longer the case - Core is now the source of truth for protocols.

---

## Priority 1: Container Domain (CRITICAL)

**Current State:**
- Hardcoded string-based service resolution
- No lifecycle management (everything is singleton)
- No dependency injection capabilities
- Returns data models instead of service instances

**Recommended Action:**
Implement `ProtocolServiceRegistry` from `omnibase_spi.protocols.container`:
```python
from omnibase_spi.protocols.container import (
    ProtocolServiceRegistry,
    ProtocolServiceRegistration,
    ProtocolDIServiceInstance,
)
```

**Benefits:**
- Comprehensive DI system (singleton, transient, scoped, pooled)
- Health monitoring and validation
- Type-safe service resolution
- Automatic dependency injection

**Files to Update:**
- `src/omnibase_core/container/container_service_resolver.py`
- `src/omnibase_core/models/container/model_onex_container.py`

**Effort:** High (2-3 weeks)
**Breaking Change:** No (additive only)

---

## Priority 2: Validation Domain (IMPORTANT)

**Current State:**
- Contract validation works well but isn't formally protocol-compliant
- No standardized interface for cross-project validation

**Recommended Action:**
Implement validation protocols for public interfaces:
```python
from omnibase_spi.protocols.validation import (
    ProtocolComplianceValidator,
    ProtocolQualityValidator,
    ProtocolValidator,
)
```

**Benefits:**
- Type-safe contracts ensure interface compliance
- Interoperability with other omni* projects
- Easier testing with protocol mocks
- Standardized validation across ecosystem

**Files to Update:**
- `src/omnibase_core/validation/contract_validator.py` → implement `ProtocolComplianceValidator`
- `src/omnibase_core/validation/auditor_protocol.py` → implement `ProtocolQualityValidator`

**Keep as-is:**
- CLI tools (concrete implementations)
- Migration utilities (one-time tools)
- Internal checkers (implementation details)

**Effort:** Medium (1-2 weeks)
**Breaking Change:** No (backward compatible)

---

## Priority 3: Nodes Domain (OPTIONAL)

**Current State:**
- Hardcoded configurations in node constructors
- Event-driven architecture via Kafka (no direct invocation)

**Recommended Action:**
Add `ProtocolNodeConfiguration` support (externalize configs):
```python
from omnibase_spi.protocols.node import ProtocolNodeConfiguration

# Before
self.default_timeout_ms = 30000  # Hardcoded

# After
self.config = await container.get_service(ProtocolNodeConfiguration)
self.default_timeout_ms = await self.config.get_timeout_ms("effect_execution", 30000)
```

**Benefits:**
- Environment-specific configs (dev/staging/prod)
- Configuration hot-reload
- Better testability

**NOT Needed:**
- `ProtocolOnexNode` - Event-driven architecture doesn't need it
- `ProtocolNodeRegistry` - Infrastructure concern, not domain responsibility
- `ProtocolNodeRunner` - Too generic for ONEX typed architecture

**Effort:** Low (3-5 days)
**Breaking Change:** No (fallback to defaults)

---

## Discovery Domain: No Action Needed ✅

**Finding:** Current implementation is correct for build-time metadata discovery
**Reason:** Different architectural purpose than runtime plugin discovery

---

## Implementation Timeline

### Phase 1 (Immediate - 1 week)
- Document protocol adoption requirements
- Create implementation plan for container domain
- Add configuration protocol support to nodes (optional quick win)

### Phase 2 (Short-term - 2-4 weeks)
- Implement `ProtocolServiceRegistry` in container domain
- Add protocol compliance to validation domain
- Comprehensive testing

### Phase 3 (Long-term - Future)
- Monitor protocol usage patterns
- Evaluate additional protocol adoption opportunities
- Community feedback and iteration

---

## Migration Safety

All recommended changes are:
- ✅ **Backward compatible** (additive only, no breaking changes)
- ✅ **Incremental** (can adopt one protocol at a time)
- ✅ **Non-blocking** (existing code continues working)
- ✅ **Well-tested** (protocols have comprehensive test coverage in omnibase_spi)

---

## References

- Analysis Date: 2025-10-21
- Source: SPI import alignment analysis (96% aligned, 1 misalignment fixed)
- Related: Protocol usage analysis across 4 domains (container, discovery, validation, nodes)
