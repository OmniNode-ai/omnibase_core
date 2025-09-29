# Future Node Migration Plan

## Overview
This document tracks archived components that require full node architecture migration in future phases.

## Dev Adapters → Memory Implementation Nodes

**Location**: `archived/src/omnibase_core/dev_adapters/`
**Status**: Deferred - Requires Full Node Architecture
**Priority**: Low (Development/Testing components)

### Components Identified:
- `memory_event_bus.py` (28KB) → **MemoryEventBusNode**
- `memory_event_store.py` (31KB) → **MemoryEventStoreNode**
- `memory_snapshot_store.py` (18KB) → **MemorySnapshotStoreNode**
- `deterministic_utils.py` (11KB) → **Development utilities** (simpler migration)

### Migration Requirements:
1. **Full Node Architecture**: These need proper ONEX node structure with contracts, protocols, and versioning
2. **Contract Development**: Define interfaces for `ProtocolEventBus`, `ProtocolEventStore`, `ProtocolSnapshotStore`
3. **Dependency Injection**: Integration with `ModelOnexContainer` service registry
4. **Testing Framework**: Comprehensive node testing patterns
5. **Documentation**: Node lifecycle, deployment, and usage patterns

### Estimated Effort:
- **2-3 weeks** per node (contract definition + implementation + testing)
- **Dependencies**: Requires established node framework patterns
- **Coordination**: Should align with infrastructure team node standards

### Future Phase Plan:
- **Phase 1**: Establish node migration framework and patterns
- **Phase 2**: Migrate deterministic utilities (simpler, no protocol requirements)
- **Phase 3**: Full memory implementation nodes with contracts
- **Phase 4**: Integration testing and production readiness validation

## Standardized Migration Naming

**For Future Complex Migrations:**
- Create `FUTURE_MIGRATION_[DOMAIN]_PLAN.md` in archived directory
- Document effort estimates, dependencies, and requirements
- Focus current migration efforts on simpler targets

## Next Actions
- ✅ Document this complex migration for future
- 🎯 Find simpler migration targets (models, utilities, constants)
- 📋 Establish incremental migration process
