# Protocol Migration Plan: omnibase_core → omnibase_spi

**Document Version:** 1.0.0
**Date:** 2025-10-03
**Status:** Planning Phase
**Objective:** Migrate 86 of 89 protocol files from `omnibase_core` to `omnibase_spi` to establish clear architectural boundaries

---

## Executive Summary

The `omnibase_core` package currently contains **91 protocol files** (including `__init__.py` files), of which **86 should migrate** to `omnibase_spi`. This migration establishes clear separation between:

- **Core Architecture Protocols** (3 files remaining in `omnibase_core`)
- **Service Provider Interface Protocols** (86 files moving to `omnibase_spi`)

### Success Criteria

✅ Only 3 foundational protocols remain in `omnibase_core`
✅ All SPI protocols moved to `omnibase_spi` with proper organization
✅ All imports updated and validated
✅ Zero breaking changes to public APIs
✅ All tests passing after migration
✅ Documentation updated to reflect new architecture

---

## 1. Complete Protocol Inventory

### 1.1 Total Count Analysis

```
Total protocol files:        91
  - Protocol implementations: 89
  - __init__.py files:        2

Migration breakdown:
  - Remaining in core:        3  (3.4%)
  - Moving to SPI:           86  (96.6%)
```

### 1.2 Current Import Usage

**Protocols imported from outside protocols directory (9 unique imports):**

```python
# CORE - Must remain
from omnibase_core.protocols.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocols.protocol_registry import ProtocolRegistry

# CORE SUPPORTING - Should remain
from omnibase_core.protocols.protocol_event_envelope_impl import ProtocolEventEnvelopeImpl
from omnibase_core.protocols.protocol_schema_loader import ProtocolSchemaLoader
from omnibase_core.protocols.protocol_canonical_serializer import ProtocolCanonicalSerializer

# SPI - Should move
from omnibase_core.protocols.protocol_output_field_tool import OutputFieldTool

# COMMENTED OUT - Already planned for removal
# from omnibase_core.protocols.protocol_database_connection import ProtocolDatabaseConnection
# from omnibase_core.protocols.protocol_service_discovery import ProtocolServiceDiscovery
```

**Import locations:**
- `src/omnibase_core/mixins/` - 6 imports (ProtocolEventBus, ProtocolRegistry, ProtocolSchemaLoader, ProtocolCanonicalSerializer)
- `src/omnibase_core/models/core/` - 2 imports (OutputFieldTool)
- `src/omnibase_core/models/events/` - 1 import (ProtocolEventEnvelopeImpl)

---

## 2. Core Protocols (Remaining in omnibase_core)

### 2.1 The Essential Three

#### Protocol 1: `protocol_event_bus.py`
**Rationale:** Defines the fundamental event-driven architecture contract for ONEX

```python
@runtime_checkable
class ProtocolEventBus(Protocol):
    """Canonical protocol for ONEX event bus (runtime/ placement)."""
    def publish(self, event: OnexEvent) -> None: ...
    async def publish_async(self, event: OnexEvent) -> None: ...
    def subscribe(self, callback: Callable, event_type: str | None) -> None: ...
    # ... (full event bus interface)
```

**Dependencies:**
- `OnexEvent` model
- `EventBusCredentialsModel`
- Used by 5 mixins

**Justification:**
- Core infrastructure for event-driven node communication
- Fundamental to ONEX architecture
- Required by multiple core mixins
- Cannot be abstracted further without breaking architecture

---

#### Protocol 2: `protocol_registry.py`
**Rationale:** Defines the core artifact and node registry contract

```python
class ProtocolRegistry(Protocol):
    """Cross-cutting registry protocol."""
    def get_status(self) -> ModelRegistryStatus: ...
    def get_artifacts(self) -> list[ModelRegistryArtifactInfo]: ...
    def get_artifacts_by_type(self, artifact_type: RegistryArtifactType) -> list: ...
    def get_artifact_by_name(self, name: str, artifact_type: RegistryArtifactType | None) -> ModelRegistryArtifactInfo: ...
    def has_artifact(self, name: str, artifact_type: RegistryArtifactType | None) -> bool: ...
```

**Dependencies:**
- `EnumOnexStatus`
- Registry models (ModelRegistryArtifactInfo, etc.)
- Used by `mixin_registry_injection.py`

**Justification:**
- Core infrastructure for artifact discovery and loading
- Required for dynamic node loading
- Foundation of ONEX plugin architecture

---

#### Protocol 3: `protocol_onex_node.py`
**Rationale:** Defines the base contract that all ONEX nodes must implement

```python
@runtime_checkable
class ProtocolOnexNode(Protocol):
    """Protocol for ONEX node implementations."""
    def run(self, *args: Any, **kwargs: Any) -> Any: ...
    def get_node_config(self) -> dict[str, Any]: ...
    def get_input_model(self) -> type[Any]: ...
    def get_output_model(self) -> type[Any]: ...
```

**Dependencies:**
- None (pure protocol)
- Used by node loader and container orchestration

**Justification:**
- Defines the fundamental node interface
- Required by node loader for dynamic loading
- Cannot move to SPI without breaking core node system

---

### 2.2 Supporting Core Protocols (Edge Cases)

These protocols support the core 3 and should also remain, but are considered supporting infrastructure:

#### `protocol_event_bus_types.py`
- Supporting types for ProtocolEventBus
- Tightly coupled to event bus implementation
- **Decision:** Keep in core

#### `protocol_event_envelope_impl.py`
- Event envelope implementation details
- Used by models/events
- **Decision:** Keep in core

#### `protocol_schema_loader.py`
- Used by mixin_event_driven_node
- Required for contract loading
- **Decision:** Keep in core (reconsider in future)

#### `protocol_canonical_serializer.py`
- Used by mixin_canonical_serialization
- Core serialization contract
- **Decision:** Keep in core (reconsider in future)

**Total remaining in core: 3 primary + 4 supporting = 7 protocols**

---

## 3. SPI Protocols (Moving to omnibase_spi)

### 3.1 Migration Categories

#### Category A: LLM & AI Services (Priority: HIGH)
**Count:** 3 files
**Rationale:** Domain-specific service providers

```
protocols/llm/
├── protocol_llm_provider.py        → spi/llm/providers/
├── protocol_llm_tool_provider.py   → spi/llm/tools/
└── protocol_ollama_client.py       → spi/llm/clients/
```

**Migration Impact:**
- No core imports
- Self-contained domain
- **Risk Level:** LOW

---

#### Category B: Agent Management (Priority: HIGH)
**Count:** 4 files
**Rationale:** Service-level agent orchestration

```
protocols/
├── protocol_agent_configuration.py        → spi/agents/configuration/
├── protocol_agent_manager.py             → spi/agents/management/
├── protocol_agent_pool.py                → spi/agents/pools/
└── protocol_distributed_agent_orchestrator.py → spi/agents/orchestration/
```

**Migration Impact:**
- Depends on ModelAgentConfig, ModelAgentInstance
- **Risk Level:** LOW

---

#### Category C: Workflow & Orchestration (Priority: MEDIUM)
**Count:** 7 files
**Rationale:** Service-level workflow coordination

```
protocols/
├── protocol_work_coordinator.py           → spi/workflows/coordination/
├── protocol_workflow_event_coordinator.py → spi/workflows/events/
├── protocol_workflow_executor.py          → spi/workflows/execution/
├── protocol_workflow_orchestrator.py      → spi/workflows/orchestration/
├── protocol_workflow_reducer.py           → spi/workflows/reducers/
├── protocol_workflow_testing.py           → spi/workflows/testing/
└── protocol_event_orchestrator.py         → spi/events/orchestration/
```

**Migration Impact:**
- May depend on core events
- **Risk Level:** MEDIUM

---

#### Category D: File & I/O Operations (Priority: MEDIUM)
**Count:** 8 files
**Rationale:** Infrastructure services

```
protocols/
├── protocol_file_discovery_source.py      → spi/file_system/discovery/
├── protocol_file_io.py                    → spi/file_system/io/
├── protocol_file_processing.py            → spi/file_system/processing/
├── protocol_file_type_handler.py          → spi/file_system/handlers/
├── protocol_file_type_handler_registry.py → spi/file_system/registries/
├── protocol_file_writer.py                → spi/file_system/writers/
├── protocol_directory_traverser.py        → spi/file_system/traversal/
└── protocol_http_client.py                → spi/networking/http/
```

**Migration Impact:**
- Pure infrastructure
- **Risk Level:** LOW

---

#### Category E: CLI & Tool Infrastructure (Priority: HIGH)
**Count:** 9 files
**Rationale:** CLI is a service layer concern

```
protocols/
├── protocol_cli.py                        → spi/cli/base/
├── protocol_cli_workflow.py               → spi/cli/workflows/
├── protocol_cli_tool_discovery.py         → spi/cli/discovery/
├── protocol_cli_dir_fixture_case.py       → spi/cli/testing/
├── protocol_cli_dir_fixture_registry.py   → spi/cli/testing/
├── protocol_testable_cli.py               → spi/cli/testing/
├── protocol_tool.py                       → spi/tools/base/
├── protocol_tool_bootstrap.py             → spi/tools/bootstrap/
└── protocol_tool_health_check.py          → spi/tools/health/
```

**Migration Impact:**
- CLI is in __init__ exports
- **Risk Level:** HIGH - Requires careful API migration

---

#### Category F: Storage & Persistence (Priority: MEDIUM)
**Count:** 4 files
**Rationale:** Infrastructure concerns

```
protocols/
├── protocol_storage_backend.py            → spi/storage/backends/
├── protocol_database_connection.py        → spi/storage/databases/
├── protocol_event_store.py                → spi/storage/events/
└── protocol_stamper_engine.py             → spi/storage/stamping/
```

**Migration Impact:**
- Already commented out in some places
- **Risk Level:** LOW

---

#### Category G: Discovery & Registry Services (Priority: LOW)
**Count:** 5 files
**Rationale:** Service-level discovery

```
protocols/
├── protocol_discovery_client.py           → spi/discovery/clients/
├── protocol_service_discovery.py          → spi/discovery/services/
├── protocol_handler_discovery.py          → spi/discovery/handlers/
├── protocol_registry_resolver.py          → spi/registry/resolvers/
└── protocol_node_registry.py              → spi/registry/nodes/
```

**Migration Impact:**
- ProtocolRegistry stays in core
- These are implementation-level protocols
- **Risk Level:** MEDIUM

---

#### Category H: Testing & Validation (Priority: LOW)
**Count:** 6 files
**Rationale:** Testing infrastructure

```
protocols/
├── protocol_testable.py                   → spi/testing/base/
├── protocol_testable_registry.py          → spi/testing/registries/
├── protocol_fixture_loader.py             → spi/testing/fixtures/
├── protocol_coverage_provider.py          → spi/testing/coverage/
├── protocol_precommit_checker.py          → spi/testing/precommit/
└── protocol_validate.py                   → spi/validation/
```

**Migration Impact:**
- Testing utilities
- **Risk Level:** LOW

---

#### Category I: Advanced Services (Priority: LOW)
**Count:** 4 files
**Rationale:** Specialized services

```
protocols/advanced/
└── protocol_multi_vector_indexer.py       → spi/indexing/vectors/

protocols/semantic/
├── protocol_advanced_preprocessor.py      → spi/semantic/preprocessing/
└── protocol_hybrid_retriever.py           → spi/semantic/retrieval/

protocols/
└── protocol_adaptive_chunker.py           → spi/text/chunking/
```

**Migration Impact:**
- Specialized functionality
- **Risk Level:** LOW

---

#### Category J: Contract & Schema Management (Priority: HIGH)
**Count:** 9 files
**Rationale:** Contract management is infrastructure

```
protocols/
├── protocol_contract_analyzer.py          → spi/contracts/analysis/
├── protocol_contract_compliance.py        → spi/contracts/compliance/
├── protocol_naming_convention.py          → spi/contracts/naming/
├── protocol_naming_conventions.py         → spi/contracts/naming/
├── protocol_schema_exclusion_registry.py  → spi/schemas/registries/
├── protocol_trusted_schema_loader.py      → spi/schemas/loaders/
├── protocol_reference_resolver.py         → spi/schemas/resolvers/
├── protocol_type_mapper.py                → spi/schemas/mappers/
└── protocol_uri_parser.py                 → spi/schemas/parsers/
```

**Migration Impact:**
- Schema management is infrastructure
- `protocol_schema_loader.py` stays in core
- **Risk Level:** MEDIUM

---

#### Category K: Miscellaneous Infrastructure (Priority: MEDIUM)
**Count:** 27 files
**Rationale:** General infrastructure services

```
protocols/
├── protocol_ast_builder.py                → spi/code/ast/
├── protocol_base_tool_with_logger.py      → spi/tools/logging/
├── protocol_communication_bridge.py       → spi/communication/bridges/
├── protocol_direct_knowledge_pipeline.py  → spi/knowledge/pipelines/
├── protocol_enum_generator.py             → spi/code/generation/
├── protocol_event_bus_context_manager.py  → spi/events/context/
├── protocol_event_bus_in_memory.py        → spi/events/implementations/
├── protocol_handler.py                    → spi/handlers/base/
├── protocol_hub_execution.py              → spi/execution/hubs/
├── protocol_input_validation_tool.py      → spi/validation/input/
├── protocol_llm_agent_provider.py         → spi/agents/llm/
├── protocol_log_format_handler.py         → spi/logging/formatters/
├── protocol_logger.py                     → spi/logging/base/
├── protocol_model_registry_validator.py   → spi/validation/registry/
├── protocol_node_cli_adapter.py           → spi/adapters/cli/
├── protocol_node_runner.py                → spi/execution/runners/
├── protocol_onex_version_loader.py        → spi/versioning/loaders/
├── protocol_orchestrator.py               → spi/orchestration/base/
├── protocol_output_field_tool.py          → spi/tools/output/
├── protocol_output_formatter.py           → spi/formatting/output/
├── protocol_reducer.py                    → spi/reduction/base/
├── protocol_stamper.py                    → spi/stamping/base/
├── protocol_tool_name_resolver.py         → spi/tools/resolution/
└── protocol_onex_version_loader.py        → spi/versioning/
```

**Migration Impact:**
- Varied, requires careful analysis
- **Risk Level:** MIXED

---

## 4. Migration Strategy & Phases

### 4.1 Phase 1: Foundation (Week 1)

**Objective:** Establish omnibase_spi structure and migrate low-risk protocols

**Tasks:**
1. Create `omnibase_spi` package structure
2. Set up `omnibase_spi` as dependency of `omnibase_core`
3. Migrate Category A (LLM) - 3 files
4. Migrate Category B (Agents) - 4 files
5. Migrate Category I (Advanced) - 4 files

**Validation:**
- Run full test suite
- Verify imports work correctly
- Check for circular dependencies

**Deliverables:**
- ✅ `omnibase_spi` package created
- ✅ 11 protocols migrated
- ✅ All tests passing

---

### 4.2 Phase 2: Infrastructure (Week 2)

**Objective:** Migrate file system and storage protocols

**Tasks:**
1. Migrate Category D (File & I/O) - 8 files
2. Migrate Category F (Storage) - 4 files
3. Migrate Category H (Testing) - 6 files

**Validation:**
- Integration tests for file operations
- Storage backend tests
- Testing framework compatibility

**Deliverables:**
- ✅ 18 additional protocols migrated (29 total)
- ✅ File system tests passing
- ✅ Storage tests passing

---

### 4.3 Phase 3: Workflows (Week 3)

**Objective:** Migrate workflow and orchestration protocols

**Tasks:**
1. Migrate Category C (Workflows) - 7 files
2. Migrate Category G (Discovery) - 5 files
3. Update workflow documentation

**Validation:**
- Workflow execution tests
- Discovery mechanism tests
- Integration tests

**Deliverables:**
- ✅ 12 additional protocols migrated (41 total)
- ✅ Workflow tests passing

---

### 4.4 Phase 4: CLI & Tools (Week 4)

**Objective:** Migrate CLI and tool infrastructure (HIGH RISK)

**Tasks:**
1. Create compatibility layer in `omnibase_core`
2. Migrate Category E (CLI & Tools) - 9 files
3. Update `__init__.py` exports for backward compatibility
4. Update all CLI tool imports

**Validation:**
- CLI command tests
- Tool discovery tests
- Backward compatibility verification

**Deliverables:**
- ✅ 9 additional protocols migrated (50 total)
- ✅ CLI backward compatibility maintained
- ✅ All CLI tests passing

---

### 4.5 Phase 5: Contracts & Schema (Week 5)

**Objective:** Migrate contract and schema management protocols

**Tasks:**
1. Migrate Category J (Contracts) - 9 files
2. Ensure `protocol_schema_loader.py` stays in core
3. Update contract validation systems

**Validation:**
- Contract validation tests
- Schema loading tests
- Naming convention tests

**Deliverables:**
- ✅ 9 additional protocols migrated (59 total)
- ✅ Contract system functional

---

### 4.6 Phase 6: Cleanup & Optimization (Week 6)

**Objective:** Migrate remaining protocols and optimize

**Tasks:**
1. Migrate Category K (Miscellaneous) - 27 files
2. Clean up any remaining protocols
3. Optimize import paths
4. Update all documentation

**Validation:**
- Full integration test suite
- Performance benchmarks
- Documentation review

**Deliverables:**
- ✅ All 86 protocols migrated
- ✅ All tests passing
- ✅ Documentation complete

---

## 5. Step-by-Step Migration Guide

### 5.1 Pre-Migration Checklist

- [ ] Create `omnibase_spi` repository
- [ ] Set up package structure in `omnibase_spi`
- [ ] Configure `omnibase_core` to depend on `omnibase_spi`
- [ ] Create migration tracking spreadsheet
- [ ] Back up current state (git tag: `pre-protocol-migration`)
- [ ] Run full test suite and record baseline

---

### 5.2 Migration Steps (Per Protocol)

#### Step 1: Analyze Protocol
```bash
# 1. Identify all imports of the protocol
poetry run grep -r "from omnibase_core.protocols.PROTOCOL_NAME" src/

# 2. Check test coverage
poetry run pytest tests/ -k "PROTOCOL_NAME" -v

# 3. Identify dependencies
poetry run grep -A 10 "class PROTOCOL_CLASS" src/omnibase_core/protocols/PROTOCOL_NAME.py
```

#### Step 2: Create Target Location
```bash
# Create directory in omnibase_spi
mkdir -p ../omnibase_spi/src/omnibase_spi/CATEGORY/SUBCATEGORY

# Copy protocol to new location
cp src/omnibase_core/protocols/PROTOCOL_NAME.py \
   ../omnibase_spi/src/omnibase_spi/CATEGORY/SUBCATEGORY/
```

#### Step 3: Update Imports
```python
# In omnibase_spi protocol file:
# BEFORE:
from omnibase_core.models.xxx import YYY

# AFTER:
from omnibase_core.models.xxx import YYY  # Still valid - omnibase_spi depends on core
```

#### Step 4: Update omnibase_core References
```bash
# Find all references
poetry run grep -r "from omnibase_core.protocols.PROTOCOL_NAME" src/

# Update to new import path
# BEFORE:
from omnibase_core.protocols.protocol_llm_provider import ProtocolLLMProvider

# AFTER:
from omnibase_spi.llm.providers.protocol_llm_provider import ProtocolLLMProvider
```

#### Step 5: Create Compatibility Layer (If Needed)
```python
# In omnibase_core/protocols/__init__.py
# Add deprecation warning for high-usage protocols

from typing import TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from omnibase_spi.cli.base.protocol_cli import ProtocolCLI

def __getattr__(name: str):
    if name == "ProtocolCLI":
        warnings.warn(
            "Importing ProtocolCLI from omnibase_core.protocols is deprecated. "
            "Use: from omnibase_spi.cli.base import ProtocolCLI",
            DeprecationWarning,
            stacklevel=2,
        )
        from omnibase_spi.cli.base.protocol_cli import ProtocolCLI
        return ProtocolCLI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

#### Step 6: Update Tests
```bash
# Run tests for the migrated protocol
poetry run pytest tests/ -k "PROTOCOL_NAME" -xvs

# Check for import errors
poetry run mypy src/omnibase_core --show-error-codes
```

#### Step 7: Update Documentation
```markdown
# In migration tracking doc
- [x] protocol_PROTOCOL_NAME.py migrated
  - From: omnibase_core/protocols/
  - To: omnibase_spi/CATEGORY/SUBCATEGORY/
  - Tests: ✅ Passing
  - Imports: ✅ Updated
```

#### Step 8: Remove Original
```bash
# Only after all tests pass
git rm src/omnibase_core/protocols/PROTOCOL_NAME.py

# Update omnibase_core/__init__.py if exported
# Remove from __all__ list
```

---

### 5.3 Post-Migration Validation

#### Validation Checklist (Per Protocol)
- [ ] All imports updated
- [ ] All tests passing
- [ ] No circular dependencies
- [ ] Mypy type checking passes
- [ ] Ruff linting passes
- [ ] Documentation updated
- [ ] CHANGELOG.md entry added

#### Full System Validation
```bash
# Run complete test suite
poetry run pytest tests/ -v --cov=src/omnibase_core --cov=../omnibase_spi/src/omnibase_spi

# Type checking
poetry run mypy src/omnibase_core

# Linting
poetry run ruff check src/omnibase_core

# Check for unused imports
poetry run vulture src/omnibase_core

# Performance benchmarks
poetry run pytest tests/benchmarks/ -v
```

---

## 6. Risk Assessment

### 6.1 High-Risk Areas

#### Risk 1: CLI Protocol Migration
**Impact:** HIGH
**Probability:** MEDIUM
**Description:** CLI protocols are exported in `omnibase_core/__init__.py` and widely used

**Mitigation:**
- Create comprehensive compatibility layer
- Phased deprecation (3 releases)
- Clear migration guide for users
- Add runtime warnings for deprecated imports

**Contingency:**
- Keep protocols in both locations temporarily
- Use `__future__` imports for gradual migration

---

#### Risk 2: Event Bus Coupling
**Impact:** MEDIUM
**Probability:** LOW
**Description:** Many protocols may have hidden dependencies on event bus

**Mitigation:**
- Careful dependency analysis before each migration
- Keep event bus protocols in core
- Comprehensive integration tests

**Contingency:**
- Revert specific migrations if coupling discovered
- Re-evaluate protocol categorization

---

#### Risk 3: Circular Dependencies
**Impact:** HIGH
**Probability:** LOW
**Description:** omnibase_spi depends on omnibase_core, but some core code might try to import from spi

**Mitigation:**
- Clear dependency rules: spi → core (allowed), core → spi (forbidden)
- Static analysis to detect circular imports
- Dependency injection where needed

**Contingency:**
- Extract shared abstractions to separate package
- Use TYPE_CHECKING imports where possible

---

#### Risk 4: Test Coverage Gaps
**Impact:** MEDIUM
**Probability:** MEDIUM
**Description:** Some protocols may lack comprehensive tests

**Mitigation:**
- Add missing tests before migration
- Integration tests for critical paths
- Manual testing for CLI operations

**Contingency:**
- Increase test coverage incrementally
- Use feature flags for gradual rollout

---

### 6.2 Risk Matrix

```
                    Probability
                 Low    Medium    High
Impact    High   [ ]      [R1]     [ ]
          Med    [R2]     [R4]     [ ]
          Low    [R3]     [ ]      [ ]
```

---

## 7. Rollback Plan

### 7.1 Rollback Triggers

Initiate rollback if:
- More than 10% of tests fail after migration phase
- Critical production bugs introduced
- Circular dependency issues discovered
- Performance degradation >20%

### 7.2 Rollback Procedure

#### Immediate Rollback (< 24 hours)
```bash
# 1. Revert to pre-migration tag
git reset --hard pre-protocol-migration

# 2. Force push to reset branch
git push origin feature/protocol-migration --force

# 3. Notify team
```

#### Selective Rollback (Protocol-Specific)
```bash
# 1. Identify problematic protocol
# 2. Copy back from omnibase_spi to omnibase_core
cp ../omnibase_spi/src/omnibase_spi/CATEGORY/PROTOCOL.py \
   src/omnibase_core/protocols/

# 3. Revert import changes
git checkout HEAD~1 -- src/omnibase_core/path/to/file_with_import.py

# 4. Remove from omnibase_spi
git rm ../omnibase_spi/src/omnibase_spi/CATEGORY/PROTOCOL.py

# 5. Test and commit
poetry run pytest tests/
git commit -m "Rollback: Keep PROTOCOL in omnibase_core"
```

---

## 8. Success Metrics

### 8.1 Quantitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Test Pass Rate | 100% | `pytest --tb=short` |
| Migration Completion | 86/86 protocols | Manual checklist |
| Import Errors | 0 | `mypy src/` |
| Performance Impact | <5% overhead | Benchmark suite |
| Documentation Coverage | 100% | Manual review |
| Code Coverage | >85% | `pytest --cov` |

### 8.2 Qualitative Metrics

- [ ] Clear architectural boundaries established
- [ ] Developer experience improved (clearer imports)
- [ ] Documentation accurately reflects new structure
- [ ] No breaking changes to public APIs
- [ ] Backward compatibility maintained for 3 releases

---

## 9. Communication Plan

### 9.1 Stakeholder Communication

#### Before Migration
- **Audience:** Development team
- **Message:** Migration plan review and feedback
- **Channel:** Team meeting + written document
- **Timeline:** 1 week before start

#### During Migration
- **Audience:** All developers
- **Message:** Weekly progress updates
- **Channel:** Slack/Email
- **Timeline:** Every Friday

#### After Migration
- **Audience:** All users
- **Message:** Migration complete + upgrade guide
- **Channel:** Release notes + documentation
- **Timeline:** With next release

### 9.2 Documentation Updates

- [ ] Update `README.md` with new protocol locations
- [ ] Update `CONTRIBUTING.md` with new protocol guidelines
- [ ] Create `PROTOCOL_ARCHITECTURE.md` explaining the split
- [ ] Update API documentation with new import paths
- [ ] Create migration guide for external users
- [ ] Update CHANGELOG.md with migration details

---

## 10. Future Considerations

### 10.1 Post-Migration Optimization

**Phase 7 (Optional - Month 2):**
- Re-evaluate remaining core protocols
- Consider moving `protocol_schema_loader.py` to SPI
- Consider moving `protocol_canonical_serializer.py` to SPI
- Optimize import paths for performance

### 10.2 Long-Term Architecture

**Potential Future State:**
```
omnibase_core/
├── protocols/
│   ├── protocol_event_bus.py           # CORE
│   ├── protocol_registry.py            # CORE
│   └── protocol_onex_node.py           # CORE

omnibase_spi/
├── llm/                                # All LLM protocols
├── agents/                             # All agent protocols
├── workflows/                          # All workflow protocols
├── cli/                                # All CLI protocols
├── storage/                            # All storage protocols
├── tools/                              # All tool protocols
└── ...                                 # All other protocols
```

### 10.3 Versioning Strategy

**Breaking Change Policy:**
- Major version bump: Required for breaking protocol changes
- Minor version bump: Adding new protocols
- Patch version bump: Bug fixes in existing protocols

**Deprecation Timeline:**
- Release N: Deprecation warning added
- Release N+1: Warning continues
- Release N+2: Warning continues
- Release N+3: Backward compatibility removed

---

## 11. Appendix

### 11.1 Complete Protocol List

```
All 91 protocols (89 implementations + 2 __init__.py):

REMAINING IN omnibase_core (3):
├── protocol_event_bus.py                 ✅ CORE
├── protocol_registry.py                  ✅ CORE
└── protocol_onex_node.py                 ✅ CORE

SUPPORTING (4 - reconsider in future):
├── protocol_event_bus_types.py           → Keep for now
├── protocol_event_envelope_impl.py       → Keep for now
├── protocol_schema_loader.py             → Keep for now
└── protocol_canonical_serializer.py      → Keep for now

MIGRATING TO omnibase_spi (86):

Category A - LLM (3):
├── llm/protocol_llm_provider.py
├── llm/protocol_llm_tool_provider.py
└── llm/protocol_ollama_client.py

Category B - Agents (4):
├── protocol_agent_configuration.py
├── protocol_agent_manager.py
├── protocol_agent_pool.py
└── protocol_distributed_agent_orchestrator.py

Category C - Workflows (7):
├── protocol_work_coordinator.py
├── protocol_workflow_event_coordinator.py
├── protocol_workflow_executor.py
├── protocol_workflow_orchestrator.py
├── protocol_workflow_reducer.py
├── protocol_workflow_testing.py
└── protocol_event_orchestrator.py

Category D - File & I/O (8):
├── protocol_file_discovery_source.py
├── protocol_file_io.py
├── protocol_file_processing.py
├── protocol_file_type_handler.py
├── protocol_file_type_handler_registry.py
├── protocol_file_writer.py
├── protocol_directory_traverser.py
└── protocol_http_client.py

Category E - CLI & Tools (9):
├── protocol_cli.py
├── protocol_cli_workflow.py
├── protocol_cli_tool_discovery.py
├── protocol_cli_dir_fixture_case.py
├── protocol_cli_dir_fixture_registry.py
├── protocol_testable_cli.py
├── protocol_tool.py
├── protocol_tool_bootstrap.py
└── protocol_tool_health_check.py

Category F - Storage (4):
├── protocol_storage_backend.py
├── protocol_database_connection.py
├── protocol_event_store.py
└── protocol_stamper_engine.py

Category G - Discovery (5):
├── protocol_discovery_client.py
├── protocol_service_discovery.py
├── protocol_handler_discovery.py
├── protocol_registry_resolver.py
└── protocol_node_registry.py

Category H - Testing (6):
├── protocol_testable.py
├── protocol_testable_registry.py
├── protocol_fixture_loader.py
├── protocol_coverage_provider.py
├── protocol_precommit_checker.py
└── protocol_validate.py

Category I - Advanced (4):
├── advanced/protocol_multi_vector_indexer.py
├── semantic/protocol_advanced_preprocessor.py
├── semantic/protocol_hybrid_retriever.py
└── protocol_adaptive_chunker.py

Category J - Contracts (9):
├── protocol_contract_analyzer.py
├── protocol_contract_compliance.py
├── protocol_naming_convention.py
├── protocol_naming_conventions.py
├── protocol_schema_exclusion_registry.py
├── protocol_trusted_schema_loader.py
├── protocol_reference_resolver.py
├── protocol_type_mapper.py
└── protocol_uri_parser.py

Category K - Miscellaneous (27):
├── protocol_ast_builder.py
├── protocol_base_tool_with_logger.py
├── protocol_communication_bridge.py
├── protocol_direct_knowledge_pipeline.py
├── protocol_enum_generator.py
├── protocol_event_bus_context_manager.py
├── protocol_event_bus_in_memory.py
├── protocol_handler.py
├── protocol_hub_execution.py
├── protocol_input_validation_tool.py
├── protocol_llm_agent_provider.py
├── protocol_log_format_handler.py
├── protocol_logger.py
├── protocol_model_registry_validator.py
├── protocol_node_cli_adapter.py
├── protocol_node_runner.py
├── protocol_onex_version_loader.py
├── protocol_orchestrator.py
├── protocol_output_field_tool.py
├── protocol_output_formatter.py
├── protocol_reducer.py
├── protocol_stamper.py
└── protocol_tool_name_resolver.py
```

### 11.2 Import Dependency Graph

```
CORE PROTOCOLS (omnibase_core):
  protocol_event_bus.py
    ← mixin_discovery_responder.py
    ← mixin_event_listener.py
    ← mixin_workflow_support.py
    ← mixin_event_driven_node.py

  protocol_registry.py
    ← mixin_registry_injection.py

  protocol_onex_node.py
    ← (Used by node loader - not in codebase grep)

SUPPORTING PROTOCOLS (omnibase_core):
  protocol_event_envelope_impl.py
    ← models/events/__init__.py

  protocol_schema_loader.py
    ← mixin_event_driven_node.py

  protocol_canonical_serializer.py
    ← mixin_canonical_serialization.py

SPI PROTOCOLS (to migrate):
  protocol_output_field_tool.py
    ← models/core/model_output_field_utils.py
```

### 11.3 Test Coverage Requirements

**Pre-Migration Requirements:**
- [ ] Event bus tests: 100% coverage
- [ ] Registry tests: 100% coverage
- [ ] Node interface tests: 100% coverage
- [ ] Integration tests for all imported protocols
- [ ] End-to-end CLI tests

**Post-Migration Requirements:**
- [ ] All existing tests still pass
- [ ] New import path tests added
- [ ] Backward compatibility tests (if applicable)
- [ ] Performance regression tests
- [ ] Documentation tests (doctest)

---

## 12. Execution Timeline

```
Week 1: Foundation
├── Day 1-2: Set up omnibase_spi structure
├── Day 3-4: Migrate LLM protocols (3)
└── Day 5: Migrate Agent protocols (4) + validation

Week 2: Infrastructure
├── Day 1-2: Migrate File & I/O protocols (8)
├── Day 3-4: Migrate Storage protocols (4)
└── Day 5: Migrate Testing protocols (6) + validation

Week 3: Workflows
├── Day 1-3: Migrate Workflow protocols (7)
├── Day 4: Migrate Discovery protocols (5)
└── Day 5: Integration tests + validation

Week 4: CLI & Tools (High Risk)
├── Day 1-2: Create compatibility layer
├── Day 3-4: Migrate CLI protocols (9)
└── Day 5: Extensive backward compatibility testing

Week 5: Contracts
├── Day 1-3: Migrate Contract protocols (9)
├── Day 4: Update validation systems
└── Day 5: Integration tests

Week 6: Cleanup
├── Day 1-3: Migrate Miscellaneous protocols (27)
├── Day 4: Final integration tests
└── Day 5: Documentation review + release prep
```

---

## 13. Sign-Off

**Prepared by:** AI Development Team
**Date:** 2025-10-03
**Version:** 1.0.0
**Status:** Pending Review

**Approvals Required:**
- [ ] Technical Lead
- [ ] Architecture Team
- [ ] QA Team
- [ ] Product Owner

**Review Comments:**
```
(To be filled during review)
```

---

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-10-03 | AI Team | Initial migration plan created |

---

**END OF DOCUMENT**
