# Documentation Audit Report — omnibase_core

> **Date**: 2026-02-14
> **Scope**: All 141 `.md` files under `docs/` (~120,000 lines)
> **Audited by**: 8 parallel agents across 6 categories
> **Purpose**: Identify errors, outdated patterns, and missing content

---

## Executive Summary

| Category | Count |
|----------|-------|
| **REWRITE** (fundamentally wrong) | 15 files |
| **DELETE** (stale, duplicate, or misplaced) | 4 files |
| **UPDATE** (partially correct, needs fixes) | 62 files |
| **KEEP** (no significant issues) | 42 files |
| **Not fully audited** (spot-checked or skipped) | 18 files |
| **Total** | **141 files** |

### Severity Rubric

| Severity | Definition |
|----------|-----------|
| **CRITICAL** | Leads to incorrect production usage or architectural violation. If a developer follows this doc, they will write code that violates invariants. |
| **HIGH** | Blocks onboarding or causes large refactor churn. A new developer reading this will form wrong mental models. |
| **MEDIUM** | Correctness is OK but style, modernization, or minor drift from standards. Causes confusion, not bugs. |
| **LOW** | Cosmetic, historical, or informational drift. Version stamps, dates, link formatting. |

### Top 10 Systemic Issues

| # | Issue | Files Affected | Severity |
|---|-------|---------------|----------|
| 1 | **No handler architecture** — business logic put directly in nodes instead of handlers | 50+ files | CRITICAL |
| 2 | **Imperative patterns** — docs teach `class MyNode(NodeX)` + override `process()` instead of YAML contract + handler | 40+ files | CRITICAL |
| 3 | **Missing ModelHandlerInput/ModelHandlerOutput** — per-node-kind output constraints not documented | 55+ files | HIGH |
| 4 | **No real node examples** — no references to actual implementations in `omnibase_infra` | 60+ files | HIGH |
| 5 | **PEP 604 violations** — `Optional[X]`, `Union[X, Y]`, `Dict`, `List` throughout examples | 25+ files | MEDIUM |
| 6 | **Custom node subclasses** — teaches subclassing instead of handlers + contracts | 35+ files | HIGH |
| 7 | **Threading anti-patterns** — manual `Lock`, `ThreadPoolExecutor` instead of event bus / stateless nodes | 8 files | HIGH |
| 8 | **Manual node wiring** — direct `NodeX(container)` instead of container/registry resolution | 20+ files | MEDIUM |
| 9 | **Legacy/removed patterns** — references to deleted methods, `black`/`isort`, stale versions | 30+ files | MEDIUM |
| 10 | **Stale version references** — docs say v0.1.0-v0.4.0 when codebase is at v0.17.0 | 20+ files | LOW |

---

## Source of Truth and Invariant Hierarchy

### Canonical Invariant Sources

The following files define non-negotiable architectural invariants, listed in precedence order:

1. **Architecture handshake** (`architecture-handshakes/repos/omnibase_core.md`) — Cross-repo contract; highest authority for repo boundaries and principles
2. **ADRs** (`docs/decisions/ADR-*.md`) — Accepted ADRs supersede general documentation for the specific decision they cover. An ADR marked "Accepted" or "Implemented" is authoritative for its scope.
3. **Architecture docs** (`docs/architecture/`) — Define system-level patterns. Must align with handshake and ADRs; if conflict exists, escalate.
4. **Convention docs** (`docs/conventions/`) — Define coding standards. Authoritative for style; defer to architecture docs for structural patterns.
5. **Guides and tutorials** (`docs/guides/`, `docs/getting-started/`) — Teach patterns. Must faithfully reflect architecture docs; never introduce new invariants.

### Conflict Resolution

- If two ADRs conflict (e.g., ADR-006 vs ADR-013), one must be marked SUPERSEDED. Both cannot be authoritative.
- If a guide contradicts an architecture doc, the guide is wrong.
- If an architecture doc contradicts the handshake, the architecture doc is wrong.

### IDE/Agent Integration

References to IDE-specific or AI-agent-specific configurations (e.g., editor settings, agent instruction files) should be confined to a dedicated integration section and never cited as the source of architectural truth. The platform is IDE-agnostic and agent-agnostic. Invariants must be defined in the docs themselves.

---

## Key Terminology

These terms are used throughout the report and throughout the codebase. They are related but not synonymous:

| Term | Definition |
|------|-----------|
| **Contract-driven** | Behavior is defined by a contract (YAML schema + Pydantic model) and enforced by validation. The contract is the source of truth, not code. |
| **Handler-based** | Business logic lives in handler classes, not in node classes. Nodes are thin coordination shells that delegate to handlers. |
| **Declarative** | Configuration-driven wiring with minimal imperative control flow in the node layer. Nodes do not decide what to do; contracts and the registry decide. |

These three concepts form a stack: contracts define *what*, handlers implement *how*, and declarative wiring connects them *without imperative glue*.

---

## The Handler Architecture (Reference Specification)

This section defines the minimal handler pattern that all rewritten docs must teach. It replaces the imperative "subclass and override" pattern found in 50+ files.

### Invariants

1. **Nodes are thin shells** — A node class contains `__init__` (calling `super().__init__(container)`) and delegates to a handler. No business logic.
2. **Handlers own business logic** — All computation, transformation, side effects, and state transitions live in handler classes.
3. **Contracts define behavior** — A YAML contract declares what the node does, its capabilities, input/output models, and handler binding.
4. **Resolution via container/registry** — Handlers are resolved by the DI container using protocol-based or capability-based lookup. No direct `HandlerFoo()` instantiation.

### File Locations

| Component | Location | Naming Convention |
|-----------|----------|------------------|
| Node class | `src/omnibase_core/nodes/` or `omnibase_infra/nodes/` | `node_<name>_<kind>.py` |
| Handler class | `omnibase_infra/handlers/` (or `src/omnibase_core/pipeline/`) | `handler_<capability>_<name>.py` |
| YAML contract | alongside the node or in `contracts/` | `<name>.onex.yaml` |
| Input/output models | `src/omnibase_core/models/` | `model_<name>_input.py`, `model_<name>_output.py` |

### Minimal Example

```yaml
# contracts/temperature_converter.onex.yaml
node:
  name: temperature_converter
  kind: COMPUTE
  version: 1.0.0
  handler:
    module: omnibase_infra.handlers.handler_temperature
    class: HandlerTemperatureConverter
  input_model: omnibase_core.models.model_temperature_input.ModelTemperatureInput
  output_model: omnibase_core.models.model_temperature_output.ModelTemperatureOutput
```

```python
# nodes/node_temperature_converter_compute.py
class NodeTemperatureConverterCompute(NodeCompute):
    """Thin shell — all logic is in HandlerTemperatureConverter."""
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

```python
# handlers/handler_temperature.py
class HandlerTemperatureConverter:
    """Owns all conversion business logic."""
    def execute(self, input_data: ModelTemperatureInput) -> ModelTemperatureOutput:
        celsius = (input_data.value - 32) * 5 / 9
        return ModelTemperatureOutput(result=celsius, unit="celsius")
```

### Output Constraints (Enforceable Contract)

Every tutorial or template that shows a node **must** include the constraints table for that node kind:

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |

**Enforcement**: `ModelHandlerOutput` Pydantic validator at construction + CI `node-purity-check` job.

**Acceptance criterion**: A doc linter can verify the presence of this table (or a reference to it) in every node-building doc.

---

## New Document: Handler Architecture Guide (Skeleton)

This document does not exist yet. It is the single most important missing piece. Suggested outline:

```text
# Handler Architecture Guide

## 1. Goal and Invariants
   - Nodes are thin shells; handlers own logic
   - Output constraints matrix
   - Contract-driven behavior

## 2. Minimal Example
   - YAML contract
   - Handler class
   - Thin node shell
   - Input/output Pydantic models

## 3. DI and Registry Resolution
   - Protocol-based resolution: container.get_service(ProtocolHandler)
   - Capability-based resolution
   - No manual instantiation

## 4. Handler Lifecycle
   - Construction, execution, teardown
   - Stateless vs. stateful handlers
   - Thread safety: handlers are single-request-scoped

## 5. Testing Pattern
   - Handler unit test (no container needed)
   - Contract validation test (golden fixtures)
   - Integration test with container

## 6. Migration from Imperative Nodes
   - Before: logic in process()
   - After: logic in handler, node delegates
   - Checklist
```text

---

## Documentation Example Policy

### Rule: Prefer Real Code, Label Pseudocode

1. **Prefer** references to real implementations in `omnibase_infra` with actual file paths and class names.
2. **If pseudocode is used**, it must:
   - Be labeled explicitly: `# Illustrative — not actual API`
   - Use class/method names that match real APIs (no fabricated `execute_effect()` when the real method is `process()`)
   - Never be presented as "current implementation"
3. **Fabricated base classes** (e.g., `ModelServiceCompute` with methods that don't exist) are forbidden in tutorials and templates. If the class exists but the methods shown don't, the example is wrong.
4. **Version-specific examples** must use a "current" marker rather than pinning to a release number, unless the doc is explicitly historical (ADR, migration guide).

---

## Version Reference Policy

Avoid pinning documentation to specific release numbers unless the document is explicitly historical (ADR, migration guide, changelog). Instead:

- Use "current" or "as of the latest release" for live documentation
- If version is mentioned, it should be derived from a single canonical constant and updated automatically
- Migration guides **should** reference the source and target versions (that's their purpose)
- Architecture docs **should not** — they describe the current system, not a point in time

---

## Files Requiring REWRITE (15)

These files are fundamentally wrong — they teach anti-patterns or contradict architectural invariants.

### 1. `docs/getting-started/FIRST_NODE.md`
- Teaches ALL anti-patterns: business logic in nodes, imperative subclassing, no handlers, wrong file naming (`temperature_unit.py` not `enum_temperature_unit.py`), `Optional[X]` instead of `X | None`, `Dict[str, Any]` process signature
- No mention of YAML contracts, handlers, or `ModelHandlerOutput`
- **Action**: Rewrite using the handler architecture pattern defined above

### 2. `docs/getting-started/QUICK_START.md`
- Same fundamental issues as FIRST_NODE.md — all four node examples use imperative subclass-and-override
- No handlers, no contracts, `Dict[str, Any]` signatures
- **Action**: Rewrite with declarative pattern

### 3. `docs/guides/node-building/07_PATTERNS_CATALOG.md`
- Most problematic file in the audit — nearly every pattern contradicts invariants
- `OrderStateMachineReducer` uses mutable `self.state` (contradicts pure FSM pattern in 05_REDUCER_NODE_TUTORIAL)
- `DataAggregationReducer` uses `defaultdict(list)` accumulating state
- `WorkflowOrchestrator` has mutable `self.active_workflows` with `asyncio.sleep` simulation
- **Action**: Complete rewrite with handler-based patterns

### 4. `docs/guides/templates/COMPUTE_NODE_TEMPLATE.md`
- ~85 lines of business logic in node class; uses Pydantic v1 `class Config:` and `regex=`; references `black`/`isort`
- Claims "backward_compatibility: 1_major_version" (contradicts repo non-goals)
- **Action**: Rewrite with thin node shell + handler + YAML contract

### 5. `docs/guides/templates/EFFECT_NODE_TEMPLATE.md`
- Directly instantiates `HttpHandler()`, `DatabaseHandler()` instead of container resolution
- No `ModelHandlerOutput` constraints documented
- **Action**: Rewrite with handler delegation pattern

### 6. `docs/guides/templates/ORCHESTRATOR_NODE_TEMPLATE.md`
- Extensive business logic in node class (~15 methods)
- `_create_timeout_output()` constructs typed result (ORCHESTRATOR cannot return result)
- **Action**: Rewrite, enforce "emit events/intents only" constraint

### 7. `docs/guides/templates/ENHANCED_NODE_PATTERNS.md`
- Compounds template problems with more imperative patterns (security validation in nodes, abstract methods for override)
- Uses deprecated `regex=` in Pydantic Field; wrong import paths
- **Action**: Rewrite or delete (templates already cover this)

### 8. `docs/guides/THREADING.md` (2,028 lines)
- **User's concern confirmed**: Advocates extensive manual threading (Lock, ThreadPoolExecutor, Timer, thread-local storage) when nodes should be stateless and single-request-scoped
- Contains ~1,200 lines of utility class code (`ThreadSafeComputeCache`, `ThreadSafeCircuitBreaker`, `ThreadMonitor`, `PrometheusThreadExporter`, `TimeoutPool`, `ThreadAffinityMixin`) that belong in source code, not documentation
- Document's own "Design Rationale" admits "Most ONEX workloads use asyncio which is single-threaded"
- **Action**: Rewrite to ~400 lines. See "Threading Rewrite Guidance" below.

#### Threading Rewrite Guidance

The rewritten THREADING.md should replace manual threading with the supported concurrency model:

**What replaces threads:**
- **Async tasks** (`asyncio.create_task`) for I/O-bound concurrency within a node
- **Event bus fan-out** for cross-node parallelism (emit events, let the bus distribute)
- **Separate process workers** (via orchestrator intents) for CPU-bound parallelism
- **Per-request node instances** instead of shared instances with locks

**Replacement checklist for doc authors:**
- If you think you need a `Lock`, you almost certainly need a different scoping boundary
- If you think you need `ThreadPoolExecutor`, you need event bus fan-out or an orchestrator
- If you think you need `threading.local()`, you need per-request instance creation
- If you think you need `Timer`, you need `EFFECT_TIMEOUT_BEHAVIOR` (timeout subcontract)

**What the rewrite should contain (~400 lines):**
1. Safety rules: nodes are single-request-scoped, do NOT share across threads
2. `ONEX_DEBUG_THREAD_SAFETY` built-in feature documentation
3. Concurrency model: async, event bus, process workers
4. Cancellation and timeout patterns (reference `EFFECT_TIMEOUT_BEHAVIOR.md`)
5. Production checklist (the existing one, trimmed)

### 9. `docs/architecture/CONTRACT_SYSTEM.md`
- Pre-declarative view — teaches imperative `class ModelContractBase(BaseModel)` pattern
- No mention of YAML contracts, handlers, or declarative behavior
- **Action**: Rewrite to show YAML-driven contract system

### 10. `docs/architecture/DEPENDENCY_INJECTION.md`
- Too thin (123 lines), uses wrong class names (`ModelServiceCompute`), shows `ModelONEXContainer(BaseModel)` (legacy)
- No handler context, no registry-based handler resolution
- **Action**: Rewrite with handler-aware DI patterns

### 11. `docs/architecture/DECLARATIVE_WORKFLOW_FINDINGS.md`
- References imperative methods (`orchestrate_rsd_ticket_lifecycle`, `aggregate_rsd_tickets`, etc.) that **no longer exist** in source code
- Stale sprint TODO items; historical findings presented as current
- **Action**: Archive as ADR or rewrite to reflect current declarative state only

### 12. `docs/architecture/TYPE_SYSTEM.md`
- Every code example uses patterns the project has explicitly banned: `Optional`, `Union`, `Dict`, `List`, `Any`, untyped `dict`
- Best Practices section recommends `Optional` (forbidden)
- **Action**: Full rewrite with PEP 604 and modern type patterns

### 13. `docs/patterns/ANTI_PATTERNS.md`
- Contains only ONE anti-pattern (String Version Literals)
- Missing critical anti-patterns: imperative node logic, container type confusion, ORCHESTRATOR returning results, skipping `super().__init__`, thread-unsafe node sharing, reducer side effects
- **Action**: Rewrite with 8-10 anti-patterns covering architectural invariants

### 14. `docs/patterns/EVENT_DRIVEN_ARCHITECTURE.md`
- Too skeletal (234 lines) for a core pattern — no DLQ, error handling, event ordering, idempotency, replay, backpressure
- Uses fabricated base classes (`ModelServiceCompute`, `ModelServiceEffect`)
- **Action**: Rewrite with comprehensive event patterns

### 15. `docs/reference/API_DOCUMENTATION.md`
- Anchored to "PR #36" (extremely stale); extensive PEP 604 violations
- Claims "Maintain backward compatibility when possible" (contradicts repo non-goals)
- Shows aspirational rather than actual APIs
- **Action**: Rewrite from current source code

---

## Files Requiring DELETION (4)

### 1. `docs/architecture/mixin-architecture/ONEX_MIXIN_ARCHITECTURE_PATTERNS.md`
- AI-generated knowledge capture for a single mixin implementation
- Incorrect file references; YAML layer it describes does not exist
- No value beyond what MIXIN_ARCHITECTURE.md covers
- **Action**: Delete

### 2. `docs/architecture/architecture-research/ONEX_MIXIN_SYSTEM_RESEARCH.md`
- Stale imports (`omnibase` not `omnibase_core`); wrong directory paths (`model/` not `models/`)
- Heavily duplicates MIXIN_ARCHITECTURE.md content
- **Action**: Delete (or mark SUPERSEDED with banner)

### 3. `docs/architecture/INHERITANCE_MODES_VALIDATION_RULES.md`
- This is a PR summary/changelog, not an architecture document
- References `black`/`isort` (project uses `ruff`)
- **Action**: Delete — useful content should be docstrings in the model

### 4. `docs/decisions/ADR-013-status-taxonomy.md`
- **Conflicts with ADR-006** on which enums are canonical for 4 of 6 status categories
- ADR-006 says `EnumHealthStatus`; ADR-013 says `EnumNodeHealthStatus`
- ADR-006 says `EnumLifecycle`; ADR-013 says `EnumNodeLifecycleStatus`
- **Action**: Merge into ADR-006 or mark SUPERSEDED — current state is harmful

---

## Files Requiring UPDATE (62)

### Getting Started & Node Building (10 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `getting-started/installation.md` | VS Code config references `black`/`pylint`/`flake8` (should be `ruff`) | Low |
| `node-building/README.md` | No mention of handlers or YAML contracts; word "handler" absent | High |
| `node-building/01_WHAT_IS_A_NODE.md` | References `ModelServiceCompute`, `nodes/legacy/`; no handler concept | High |
| `node-building/02_NODE_TYPES.md` | All code examples imperative; `container.db_pool` direct access | High |
| `node-building/03_COMPUTE_NODE_TUTORIAL.md` | Good structure but all logic in node class; no `ModelHandlerOutput` | Medium |
| `node-building/04_EFFECT_NODE_TUTORIAL.md` | Good Pydantic models but no handler delegation | Medium |
| `node-building/05_REDUCER_NODE_TUTORIAL.md` | Best tutorial — FSM/Intent correct; minor handler gap | Low |
| `node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md` | Good constraint docs; add handler architecture | Medium |
| `node-building/08_COMMON_PITFALLS.md` | Missing critical pitfall: "putting logic in nodes instead of handlers"; threading advice recommends locks instead of separate instances | Medium |
| `node-building/10_AGENT_TEMPLATES.md` | REDUCER/ORCH templates close to correct; COMPUTE/EFFECT need handlers; references `black`/`isort` | Medium |

### Templates & Architecture Core (7 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `templates/REDUCER_NODE_TEMPLATE.md` | Better than others but still has logic in node; no `ModelHandlerOutput` constraints | Medium |
| `NODE_CLASS_HIERARCHY.md` | Tier system concept valuable; all examples put logic in nodes | Medium |
| `ONEX_FOUR_NODE_ARCHITECTURE.md` | ModelIntent/ModelAction sections excellent; EFFECT/COMPUTE examples need handlers | Medium |
| `NODE_PURITY_GUARANTEES.md` | Purity concept correct; "After (Pure)" example still has logic in node | Low |
| `overview.md` | Shows imperative `process()` pattern; `Dict[str, Any]` usage | Low |
| `reference/api/nodes.md` | All four examples teach subclass+override; `Dict[str, Any]`; threading section recommends `threading.local()` | Medium |
| `reference/node-archetypes.md` | Best-aligned doc — thin nodes with contracts; needs real impl references and complete output constraints | Low |

### Contract/Handler/DI (9 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md` | Needs explicit handler principle and `ModelHandlerOutput` constraints table | Low |
| `CONTRACT_DRIVEN_NODEEFFECT_V1_0.md` | Needs `ModelHandlerOutput` constraints for EFFECT kind | Low |
| `CONTRACT_DRIVEN_NODEORCHESTRATOR_V1_0.md` | Needs `ModelHandlerOutput` constraints; extremely long | Low |
| `CONTRACT_DRIVEN_NODEREDUCER_V1_0.md` | Needs `ModelHandlerOutput` constraints table | Low |
| `CONTAINER_TYPES.md` | Node example puts logic in `process()`; no handler registry | Medium |
| `CONTAINER_DI_DESIGN.md` | References `black`/`isort` (should be `ruff`) | Low |
| `MODEL_INTENT_ARCHITECTURE.md` | Intent declaration excellent; Effect node section shows imperative inline routing | Medium |
| `MODEL_ACTION_ARCHITECTURE.md` | Node examples have inline logic; should delegate to handlers | Medium |
| `HANDLER_CONTRACT_GUIDE.md` | Best handler doc — add per-node-kind `ModelHandlerOutput` constraints | Low |

### Mixin/Subcontract/Protocol (7 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `MIXIN_ARCHITECTURE.md` | YAML layer at `nodes/canary/mixins/` does not exist; wrong model paths | High |
| `MIXIN_CLASSIFICATION.md` | Incomplete mixin inventory (missing ~6); non-existent target dirs (`domain/`) | Medium |
| `MIXINS_TO_HANDLERS_REFACTOR.md` | Status stuck at "Draft" despite Phase 1 progress; stale manifest caveat | High |
| `SUBCONTRACT_ARCHITECTURE.md` | No date header; business logic in node examples; 1,748 lines | Medium |
| `mixin-development/ (README + 01-05)` | Wrong Python version (3.11 -> 3.12); wrong import paths; teaches nonexistent YAML workflow | High |
| `MIXIN_SUBCONTRACT_MAPPING.md` | ~50% of "imperative mixins" table lists nonexistent mixins | High |
| `RESEARCH_REPORT_4_NODE_ARCHITECTURE.md` | Needs HISTORICAL label; references `omnibase_3` | Low |

### Threading/Execution/Migration (12 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `CANONICAL_EXECUTION_SHAPES.md` | Code examples use imperative orchestrator API; Shape 2 violates reducer purity (I/O) | Medium |
| `EXECUTION_SHAPE_EXAMPLES.md` | Same imperative API and reducer purity issues | Medium |
| `ENVELOPE_FLOW_ARCHITECTURE.md` | Wrong method signatures; mutation of frozen models; orchestrator returns typed result | Medium |
| `MUTABLE_STATE_STRATEGY.md` | Phases 2-4 target v0.5.0-1.0.0 (current is v0.17.0); references non-existent guides | Low |
| `EFFECT_TIMEOUT_BEHAVIOR.md` | Draft artifact ("Wait... that's not quite right") in Example 5 | Low |
| `PAYLOAD_TYPE_ARCHITECTURE.md` | Stale historical section; mutable defaults; `Union` syntax | Low |
| `MESSAGE_TOPIC_MAPPING.md` | `dict[str, Any]` payloads; business logic in node examples | Medium |
| `REGISTRATION_TRIGGER_DESIGN.md` | Parallel-vs-sequential inconsistency with FSM doc | Medium |
| `VALIDATION_PROTOCOL_COMPLIANCE.md` | Says v0.1.0 (project at v0.17.0); stale SPI references | Low |
| `MIGRATING_TO_DECLARATIVE_NODES.md` | Stale Pydantic v1 `.parse_file()` references | Low |
| `MIGRATING_TO_MIXIN_EVENT_BUS_V0_4.md` | Fragile line-number refs; QUERY category inconsistency | Low |
| `MIGRATING_FROM_DICT_ANY.md` | `from_dict()` mutation bug should be a code fix | Low |

### Conventions/Patterns (7 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `NAMING_CONVENTIONS.md` | File naming section covers only `model_*`; architecture defines 16+ directory prefixes — **MISMATCH** | High |
| `ERROR_HANDLING_BEST_PRACTICES.md` | PEP 604 violations; fabricated `ModelServiceEffect`/`ModelServiceCompute` classes; `ONEXContainer` wrong name | Medium |
| `DOCSTRING_TEMPLATES.md` | PEP 604 violations throughout (`Optional`, `List`, `Union`) | Low |
| `CIRCUIT_BREAKER_PATTERN.md` | Fabricated class names; missing note that circuit breakers belong in EFFECT nodes | Low |
| `CONFIGURATION_MANAGEMENT.md` | Mixes implemented and "planned for future release" features without clear delineation | Low |
| `LEASE_MANAGEMENT_PATTERN.md` | `datetime.now()` without UTC; incorrect `ModelEvent` reference | Low |
| `PURE_FSM_REDUCER_PATTERN.md` | Broken related doc links; stale date | Low |

### ADRs/Testing/CI (13 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `ADR-001` | Version refs stale (v0.2.0 migration path) | Low |
| `ADR-002` | Incorrectly says "ADR-001: (Reserved for future use)" | Low |
| `ADR-003` | Overlaps significantly with ADR-012 | Low |
| `ADR-005` | Shell script vs Python script inconsistency | Low |
| `ADR-006` | Conflicts with ADR-013 — see DELETION section | High |
| `ADR-012` | Filename casing wrong (UPPERCASE); date inconsistency | Low |
| `ADR_BEST_PRACTICES.md` | Missing ADR-012 and ADR-013 references | Low |
| `decisions/README.md` | Date inconsistencies; ADR-006/013 conflict described as complementary | Medium |
| `CI_TEST_STRATEGY.md` | References `black`/`isort` instead of `ruff`; stale Q2/Q3 2025 timelines | Medium |
| `PERFORMANCE_TESTING_GUIDE.md` | Non-existent `@pytest.mark.serial` marker | Low |
| `CI_MONITORING_GUIDE.md` | Baseline metrics 15+ months stale; review date 1+ year past | Medium |
| `DEPRECATION_WARNINGS.md` | Entire premise (v0.5.0 migration) stale at v0.17.0 | Medium |
| `PERFORMANCE_BENCHMARK_CI_INTEGRATION.md` | Q1/Q2/Q3 2025 timelines all past; stale `pytest.ini` reference | Low |

### Reference/Guides/Misc (10 files)

| File | Key Issues | Priority |
|------|-----------|----------|
| `reference/api/models.md` | PEP 604 violations; Pydantic v1 `regex=`/`max_items=`; unhashable `lru_cache` dict param | Medium |
| `reference/api/utils.md` | Wrong import path; broken cross-refs (uppercase filenames); version says 0.1.0 | Medium |
| `SERVICE_WRAPPERS.md` | Wrong imports; stale "waiting for Agent 2"; aspirational mixin/method names | Medium |
| `TESTING_GUIDE.md` | PEP 604; deprecated `event_loop` fixture; says "Black, isort" | Medium |
| `INDEX.md` | Claims all sections "Complete" (inaccurate); missing reference docs in listing | Medium |
| `ECOSYSTEM_DIRECTORY_STRUCTURE.md` | Version 0.2.0; stale file counts; claims `ModelServiceEffect` is deprecated (it isn't) | Medium |
| `IMPORT_COMPATIBILITY_MATRIX.md` | v0.4.0 migration artifact; uncompleted checklist; `NodeReducerDeclarative` shims | Low |
| `VALIDATION_FRAMEWORK.md` | Says `pip install` instead of `poetry install` | Low |
| `reference/README.md` | Uppercase filenames in links; wrong import paths | Low |
| `CONTRACT_VALIDATOR_API.md` | Import path may not match actual exports; stale date | Low |

---

## Files to KEEP (42)

No significant issues found in these files:

| Category | Files |
|----------|-------|
| **Getting Started** | `09_TESTING_INTENT_PUBLISHER.md` |
| **Contract/Handler** | `CONTRACT_STABILITY_SPEC.md`, `CONTRACT_DRIVEN_NODEREDUCER_V1_0_4_DELTA.md`, `DEPENDENCY_INVERSION.md`, `MODELACTION_TYPED_PAYLOADS.md`, `OPERATION_BINDINGS_DSL.md`, `INTROSPECTION_SUBCONTRACT_GUIDE.md`, `HANDLER_CONVERSION_GUIDE.md`, `HANDLER_CONVERSION_CHECKLIST.md` |
| **Mixin/Protocol** | `PROTOCOL_ARCHITECTURE.md`, `CAPABILITY_RESOLUTION.md`, `ISP_PROTOCOL_MIGRATION.md`, `PROTOCOL_DISCOVERY_GUIDE.md`, `EFFECT_SUBCONTRACT_GUIDE.md`, `EFFECT_BOUNDARY_GUIDE.md` |
| **Registration** | `REGISTRATION_FSM_CONTRACT.md` |
| **Migration** | `ENUM_NODE_KIND_MIGRATION.md`, `UNION_TYPE_MIGRATION.md`, `PROTOCOL_UUID_MIGRATION.md`, `DECLARATIVE_NODE_IMPORT_RULES.md` |
| **Conventions** | `PYDANTIC_BEST_PRACTICES.md`, `ERROR_CODE_STANDARDS.md`, `CAPABILITY_NAMING.md`, `FILE_HEADERS.md`, `VERSION_SEMANTICS.md`, `TERMINOLOGY_GUIDE.md`, `CUSTOM_BOOL_PATTERN.md`, `APPROVED_UNION_PATTERNS.md`, `patterns/README.md` |
| **Standards** | `onex_terminology.md`, `onex_topic_taxonomy.md`, `STANDARD_DOC_LAYOUT.md` |
| **ADRs** | `ADR-004`, `ADR-007`, `ADR_FIXES_SUMMARY.md`, `RISK-009` |
| **Testing/CI** | `COVERAGE.md`, `PARALLEL_TESTING.md`, `TESTMON_USAGE.md`, `CORE_PURITY_FAILURE.md` |
| **Reference** | `api/enums.md`, `contracts.md`, `MANIFEST_MODELS.md`, `MIXIN_DISCOVERY_API.md`, `CONTRACT_PATCHING_GUIDE.md`, `CONTRACT_PROFILE_GUIDE.md`, `PIPELINE_HOOK_REGISTRY.md`, `guides/README.md`, `BETA_DEMO_GUIDE.md` |

---

## Not Fully Audited (18)

These files received either spot-checking or no detailed review. "Not fully audited" means the agent either skipped the file or read it without producing per-line findings. Files are listed here for transparency; none are expected to have critical architectural issues (they are performance benchmarks, CI guides, and utility docs), but they may have staleness.

**High-risk unaudited files** (involve execution, DI, or handler resolution — should be prioritized for manual review):
- `docs/guides/PIPELINE_HOOK_REGISTRY.md` (partially audited — kept, but complex)
- `docs/guides/CUSTOM_CALLABLE_PATTERNS.md`
- `docs/guides/EXECUTION_CORPUS_GUIDE.md`
- `docs/architecture/DICT_STR_ANY_PREVENTION.md`

**Lower-risk unaudited files**:
- `docs/guides/INTENT_PUBLISHER_TESTING_DOCUMENTATION.md`
- `docs/guides/PRODUCTION_CACHE_TUNING.md`
- `docs/guides/REQUEST_TRACING.md`
- `docs/guides/PERFORMANCE_BENCHMARKS.md`
- `docs/guides/VERSION_FIELD_AUTOMATION_STRATEGY.md`
- `docs/guides/replay/REPLAY_SAFETY_INTEGRATION.md`
- `docs/performance/MODEL_REDUCER_OUTPUT_BENCHMARKS.md`
- `docs/performance/PERFORMANCE_BENCHMARK_THRESHOLDS.md`
- `docs/performance/SOURCE_NODE_ID_BENCHMARKS.md`
- `docs/services/invariant/CUSTOM_CALLABLES.md`
- `docs/services/README.md`
- `docs/tech_debt/TYPE_SAFETY_DICT_UNION_ANALYSIS.md`
- `docs/templates/LINEAR_ISSUE_TEMPLATE.md`
- `docs/omnimemory/memory_snapshots.md`
- `docs/troubleshooting/ASYNC_HANG_DEBUGGING.md`
- `docs/validation/REGEX_PATTERN_IMPROVEMENTS.md`
- `docs/architecture/CLAUDE_CODE_HOOKS.md`
- `docs/testing/INTEGRATION_TESTING.md` (partially audited — version stale)
- `docs/testing/TEST_COUNT_CLARIFICATION_SUMMARY.md` (partially audited — stale line refs)
- `docs/ci/TRANSPORT_IMPORT_CHECKER_EVALUATION.md` (partially audited — allowlist expiry)

> **Note**: The bullet count here exceeds 18 because 3 "partially audited" files were categorized in the UPDATE section but are also listed here for completeness. The 18 count in the summary refers to files that received no detailed per-line findings.

---

## Critical Cross-Cutting Findings

### 1. The "Build a Node" Path Is Entirely Wrong

The developer onboarding path (Getting Started -> Tutorials -> Templates -> Patterns) consistently teaches:
- Subclass `NodeCompute`/`NodeEffect`/`NodeReducer`/`NodeOrchestrator`
- Override `process()` with business logic
- Directly instantiate nodes: `MyNode(container)`

The **correct** pattern per architectural invariants is:
- Write a YAML contract defining behavior
- Write a handler containing business logic
- Node is a thin shell resolved by the container/registry

**No document in the entire `docs/` directory teaches this correct end-to-end pattern.** The closest is `node-archetypes.md` (thin nodes with contracts) and `HANDLER_CONTRACT_GUIDE.md` (handler system), but neither provides a complete "here's how to build a node" walkthrough.

### 2. ModelHandlerOutput Constraints Are Undocumented

The output constraints matrix (see "The Handler Architecture" section above) appears only in agent-specific configuration files, not in any platform documentation. No developer-facing doc presents these constraints. The ORCHESTRATOR "cannot return result" rule is mentioned in `06_ORCHESTRATOR_NODE_TUTORIAL.md` and `node-archetypes.md`, but the complete constraint matrix is absent from all docs.

### 3. YAML Mixin Contracts Don't Exist

Multiple documents describe a three-layer mixin architecture (YAML + Pydantic + Integration) where the YAML layer lives at `nodes/canary/mixins/`. **There are zero YAML files in that directory.** The Pydantic subcontract models exist at `models/contracts/subcontracts/`, but the YAML layer described extensively in:
- `MIXIN_ARCHITECTURE.md`
- `ONEX_MIXIN_ARCHITECTURE_PATTERNS.md`
- `ONEX_MIXIN_SYSTEM_RESEARCH.md`
- `mixin-development/` guide series (5 files)

...does not exist in the codebase. The entire mixin development guide teaches a workflow that cannot be followed.

### 4. ADR-006 vs ADR-013 Actively Conflicts

Both cover "status taxonomy" with contradictory canonical enum selections:

| Category | ADR-006 says | ADR-013 says |
|----------|-------------|-------------|
| Health | `EnumHealthStatus` | `EnumNodeHealthStatus` |
| Lifecycle | `EnumLifecycle` | `EnumNodeLifecycleStatus` |
| Registration | `EnumRegistryEntryStatus` | `EnumToolRegistrationStatus` |
| Workflow | `EnumWorkflowStatus` | `EnumWorkflowState` |

A developer following one ADR would use different enums than a developer following the other.

### 5. Threading Documentation Contradicts Architecture

`THREADING.md` (2,028 lines) prescribes manual threading patterns (Lock, ThreadPoolExecutor, Timer, thread-local storage) throughout. The architecture says:
- Nodes are single-request-scoped
- Nodes should NOT be shared across threads
- Inter-node communication goes through the event bus

The document's own "Design Rationale" admits "Most ONEX workloads use asyncio which is single-threaded," making ~1,500 lines of manual threading infrastructure documentation largely unnecessary.

### 6. `black`/`isort` Referenced in 7+ Files

The project uses `ruff` for linting, formatting, and import sorting. These files still reference `black` and/or `isort`:
- `installation.md` (VS Code config)
- `10_AGENT_TEMPLATES.md` (validation checklist)
- `CI_TEST_STRATEGY.md` (pre-commit validation)
- `CONTAINER_DI_DESIGN.md` (pre-commit hooks)
- `TESTING_GUIDE.md` (code quality section)
- `INHERITANCE_MODES_VALIDATION_RULES.md` (test results)
- `ERROR_HANDLING_BEST_PRACTICES.md` (implied through patterns)

### 7. Fabricated Base Classes in Examples

Multiple files use `ModelServiceCompute`, `ModelServiceEffect`, `ModelServiceReducer`, `ModelServiceOrchestrator` as base classes in examples. While these classes exist in the codebase, the examples show them with fabricated method names (`execute_effect()`, `execute_compute()`, `execute_orchestration()`, `execute_reduction()`) that may not match the actual API (`process()`). See "Documentation Example Policy" above for remediation rules.

---

## Risk Analysis

What breaks if this documentation is not fixed:

| Risk | Impact | Likelihood | Consequence |
|------|--------|-----------|-------------|
| **Wrong onboarding docs** | New developers write imperative nodes with business logic inline | HIGH (every new dev reads getting-started) | Architecture drift, costly refactors, PRs that must be rewritten |
| **Missing output constraints** | Developers return `result` from ORCHESTRATOR or emit `events[]` from REDUCER | MEDIUM (constraint exists in validator, but docs don't teach it) | Runtime `ValueError` in production; confusing error messages |
| **Threading guidance** | Developers add `Lock`/`ThreadPoolExecutor` to nodes instead of using event bus | MEDIUM (threading doc is long and authoritative-looking) | Race conditions, heisenbugs, incident risk |
| **Conflicting ADRs** | Teams use different canonical enums for the same concept | HIGH (both ADRs are equally discoverable) | Enum fragmentation, incompatible telemetry, broken state machines |
| **Fabricated examples** | Developers call methods that don't exist (`execute_effect()`) | MEDIUM | `AttributeError` at runtime; erodes trust in documentation |
| **Stale version refs** | Developers think features are "planned" when they already exist (or vice versa) | LOW | Wasted effort reimplementing existing features; confusion |

---

## Docs CI Automation Recommendations

Manual cleanup will regress unless automated checks prevent reintroduction of known issues.

### Proposed CI Checks

| Check | Rule | Enforcement |
|-------|------|-------------|
| **PEP 604** | Reject `Optional[`, `Union[`, `Dict[`, `List[` in fenced code blocks | grep/regex in CI |
| **Banned tools** | Reject `black`, `isort` mentions (except in historical/migration context) | grep with allowlist |
| **Deleted symbols** | Maintain deny-list of removed APIs (`orchestrate_rsd_ticket_lifecycle`, `aggregate_rsd_tickets`, etc.) | grep |
| **Output constraints** | Every file in `guides/node-building/` and `guides/templates/` must contain the string `ModelHandlerOutput` or reference the constraints table | grep |
| **Link validation** | Check that all `[text](path)` links resolve to existing files; validate filename casing | script |
| **Last-reviewed header** | Files in `architecture/` and `reference/` must have a `Last Updated:` header less than 6 months old | script |
| **Handler mention** | Every file in `guides/node-building/` must contain the word "handler" | grep |

### Implementation Notes

- These checks should be non-blocking initially (report warnings) to avoid breaking CI on day one
- Transition to blocking after the Phase 1 rewrites are complete
- The deny-list of removed APIs should be maintained in a `.docs-lint.yaml` or similar config file

---

## Golden Path Acceptance Test

### Definition of Done for Phase 1

The documentation rewrite is complete when:

> **A new developer can build a working ONEX node using ONLY the docs, without subclassing nodes for business logic, and without manual container wiring.**

### Testable Criteria

1. A developer reading `FIRST_NODE.md` -> `QUICK_START.md` -> any tutorial produces a node that:
   - Has a YAML contract
   - Has a handler class containing all business logic
   - Has a thin node shell with only `__init__` calling `super().__init__(container)`
   - Uses `ModelHandlerOutput` with correct per-kind constraints
   - Does not directly instantiate any other node

2. No doc in the onboarding path (`getting-started/`, `guides/node-building/`, `guides/templates/`) teaches or shows the imperative `class MyNode(NodeX): def process(self):` pattern as the recommended approach.

3. The output constraints table appears in every node tutorial and template.

### Validation Method

Run a "docs-driven integration test": have a team member (or an AI agent) follow the docs from scratch and verify the resulting code matches the handler architecture. If it doesn't, the docs are still wrong.

---

## Recommended Priority Order for Fixes

### Phase 1: Critical Path (Developer Onboarding)
1. Rewrite `FIRST_NODE.md` — first-contact tutorial
2. Rewrite `QUICK_START.md` — second first-contact tutorial
3. Update `node-building/README.md` — add handler architecture as fundamental concept
4. Rewrite `ANTI_PATTERNS.md` — add 8+ critical anti-patterns
5. Create new doc: **Handler Architecture Guide** (see skeleton above)

### Phase 2: Templates (Copy-Paste Propagation)
6. Rewrite `COMPUTE_NODE_TEMPLATE.md`
7. Rewrite `EFFECT_NODE_TEMPLATE.md`
8. Rewrite `ORCHESTRATOR_NODE_TEMPLATE.md`
9. Delete `ENHANCED_NODE_PATTERNS.md`
10. Rewrite `07_PATTERNS_CATALOG.md`

### Phase 3: Architecture Truth
11. Rewrite `CONTRACT_SYSTEM.md`
12. Rewrite `DEPENDENCY_INJECTION.md`
13. Rewrite `THREADING.md` (cut to ~400 lines; see rewrite guidance above)
14. Rewrite `TYPE_SYSTEM.md`
15. Rewrite `EVENT_DRIVEN_ARCHITECTURE.md`
16. Delete ADR-013 (merge into ADR-006)

### Phase 4: Cleanup Sweep
17. Delete `ONEX_MIXIN_ARCHITECTURE_PATTERNS.md`
18. Delete `ONEX_MIXIN_SYSTEM_RESEARCH.md`
19. Delete `INHERITANCE_MODES_VALIDATION_RULES.md`
20. Fix `NAMING_CONVENTIONS.md` to match the 16-directory table
21. Archive `DECLARATIVE_WORKFLOW_FINDINGS.md`
22. Update all `black`/`isort` references to `ruff`
23. Update all PEP 604 violations across docs
24. Update `INDEX.md` to accurately reflect doc health

### Phase 5: Enhancements
25. Add `ModelHandlerOutput` constraints table to all node-building docs
26. Add real `omnibase_infra` node examples to tutorials
27. Update mixin development guides to reflect actual (non-YAML) workflow
28. Update `MIXINS_TO_HANDLERS_REFACTOR.md` status from "Draft" to reflect Phase 1 progress
29. Fix `MIXIN_SUBCONTRACT_MAPPING.md` — remove ~15 non-existent mixin entries
30. Reconcile stale version references (v0.1.0-v0.4.0 -> current)
31. Implement docs CI checks (see automation section)

---

## Best-Aligned Documents (Use as Reference Models)

These documents most closely follow the correct architecture and can serve as patterns for rewriting others:

1. **`node-archetypes.md`** — Thin nodes, contract-driven YAML, correct pattern
2. **`HANDLER_CONTRACT_GUIDE.md`** — Best handler architecture documentation
3. **`HANDLER_CONVERSION_GUIDE.md`** — Correctly describes handlers owning logic
4. **`OPERATION_BINDINGS_DSL.md`** — Declarative handler wiring via YAML
5. **`EFFECT_BOUNDARY_GUIDE.md`** — Most recently updated, follows all principles
6. **`05_REDUCER_NODE_TUTORIAL.md`** — Best tutorial, FSM/Intent patterns correct
7. **`PYDANTIC_BEST_PRACTICES.md`** — Consistent with project standards

---

*Report generated 2026-02-14 by parallel documentation audit (8 agents, ~120K lines reviewed)*
*Addendum applied 2026-02-14 with 14 structural improvements per reviewer feedback*
