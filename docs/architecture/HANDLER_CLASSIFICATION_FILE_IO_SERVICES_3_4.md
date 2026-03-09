> **Navigation**: [Home](../INDEX.md) > [Architecture](overview.md) > Handler Classification — File I/O Services (3.4)

# Handler Classification: omnibase_core File I/O Services (Epic 3 — Ticket 3.4)

**Ticket**: OMN-4010
**Epic**: OMN-4014 — Epic 3: Mixin/Service -> Handler Refactoring
**Status**: Final — KEEP AS SERVICE (abort conditions apply)
**Last Updated**: 2026-03-08
**Classification Rules**: OMN-4004 (`HANDLER_CLASSIFICATION_RULES.md` in omnibase_infra `docs/architecture/`)
**Decision Matrix**: Section 3 of OMN-4004 classification rules
**3.1 POC Finding**: OMN-4005 — postgres mixins KEEP AS MIXIN (utility-function pattern); evaluated independently per PR #706 guidance

---

## Scope

Four file I/O services evaluated for handler conversion:

| Service | Location | Role |
|---------|----------|------|
| `ServiceDiffFileStore` | `services/diff/service_diff_file_store.py` | JSONL-based storage for `ModelContractDiff` objects |
| `ServiceFileSink` | `services/sinks/service_sink_file.py` | JSONL event sink for contract validation events |
| `OncpBuilder` | `package/service_oncp_builder.py` | Assembles `.oncp` content-addressed zip bundles |
| `OncpReader` | `package/service_oncp_reader.py` | Reads and validates `.oncp` zip bundles |

---

## Classification Rubric Results

### ServiceDiffFileStore

| Criterion | Score | Evidence |
|-----------|-------|---------|
| C1: I/O Ownership | YES | Owns filesystem path (`base_path`); direct `open()` / `unlink()` calls |
| C2: Lifecycle Manageability | YES | Explicit `close()` method; `_ready` flag; buffer flush on close |
| C3: Dispatch Entry Point | YES | `put/get/query/delete/flush/close` are clear, named entry points |
| C4: Testability without subclassing | YES | Standalone class; tests inject directly without subclassing |
| C5: Cross-layer leakage | NO | Not a mixin; no inheritance grants I/O capability to subclasses |

**Criteria Met**: 4/5 → Matrix says CONVERT

**Abort Condition Analysis** (Section 7 of classification rules):

Abort condition #2 applies: **fewer than 2 ambiguity signals (Section 5) are demonstrably satisfied.**

- S1 (Hidden I/O eliminated): NOT applicable. `ServiceDiffFileStore` is already a standalone class, not a mixin. No subclass inherits hidden I/O capability via inheritance. Converting to a handler does not eliminate any hidden I/O — there is none.
- S2 (Dispatch ownership clarified): NOT applicable. The entry points (`put`, `get`, `query`) are already clearly named and owned. No scattered inherited methods to consolidate.
- S3 (Lifecycle enforced): MARGINAL. The class already has explicit `close()` and `_ready`. Wrapping in `initialize()`/`shutdown()` adds boilerplate with no new enforcement — callers already call `close()` explicitly.
- S4 (Testability improved): NOT applicable. Tests already inject `ServiceDiffFileStore` directly without subclassing. The handler pattern would not improve testability.
- S5 (Layer boundary respected): NOT applicable. No compute or orchestrator node inherits this via mixin. No layer boundary violation exists to remediate.

**Conclusion**: Zero signals are demonstrably satisfied. Section 8 criterion 2 requires at least two. Abort condition applies.

**Decision: KEEP AS SERVICE**

---

### ServiceFileSink

| Criterion | Score | Evidence |
|-----------|-------|---------|
| C1: I/O Ownership | YES | Owns `_file_path`; direct `open("a")` file writes |
| C2: Lifecycle Manageability | YES | `close()` / `_ready` flag pattern; buffer flush on close |
| C3: Dispatch Entry Point | YES | `write/flush/close` are the entry points |
| C4: Testability without subclassing | YES | Standalone class; `ServiceContractValidationEventEmitter` constructs it directly |
| C5: Cross-layer leakage | NO | Not a mixin; no inheritance chain |

**Criteria Met**: 4/5 → Matrix says CONVERT

**Abort Condition Analysis** (Section 7 of classification rules):

Same abort condition as `ServiceDiffFileStore`: **fewer than 2 ambiguity signals are demonstrably satisfied.**

- S1: NOT applicable — standalone class, no mixin inheritance to break.
- S2: NOT applicable — entry points (`write`, `flush`, `close`) are already owned and clear.
- S3: MARGINAL — `close()` is already explicit. Handler lifecycle would not add enforcement.
- S4: NOT applicable — `ServiceContractValidationEventEmitter` already injects `ServiceFileSink` by construction; no subclassing required.
- S5: NOT applicable — no cross-layer inheritance to remediate.

**Conclusion**: Zero signals satisfied. Abort condition applies.

**Decision: KEEP AS SERVICE**

---

### OncpBuilder

| Criterion | Score | Evidence |
|-----------|-------|---------|
| C1: I/O Ownership | YES | Writes `.oncp` zip to filesystem via `build(output_path)` |
| C2: Lifecycle Manageability | NO | One-shot builder; no `initialize()`/`shutdown()` — `build()` is synchronous and finalizing |
| C3: Dispatch Entry Point | YES | `build()` / `build_bytes()` are the single entry points |
| C4: Testability without subclassing | YES | Standalone class; injectable |
| C5: Cross-layer leakage | NO | Not a mixin; no inheritance chain |

**Criteria Met**: 3/5 → AMBIGUOUS (proof-of-concept required before committing)

**Additional Abort Condition** (beyond AMBIGUOUS score): `OncpBuilder` is instantiated **inline within handler logic** (`node_contract_verify_replay_compute/handler.py`). The reader and builder are used as in-process utilities scoped to a single handler invocation — converting them to injected handlers would require either:

1. Making them per-call dependencies (requiring factory injection), or
2. Restructuring the handler's internal private methods to pass an injected instance through every check method (`_check_schema_validation`, `_check_capability_linting`, etc.)

This is abort condition #1 (**dispatch integration is more complex than expected**) and abort condition #3 (**extracting the handler causes callers to expose their internal operation logic**).

**Conclusion**: AMBIGUOUS score + two abort conditions. Do not convert.

**Decision: KEEP AS SERVICE**

---

### OncpReader

| Criterion | Score | Evidence |
|-----------|-------|---------|
| C1: I/O Ownership | YES | Reads `.oncp` zip from filesystem via `open(path)` |
| C2: Lifecycle Manageability | NO | Stateful but no cleanup — `_zip_bytes` is in-memory; no `close()` needed |
| C3: Dispatch Entry Point | YES | `open()/open_bytes()` then `validate_digests()/get_overlay_patches()` |
| C4: Testability without subclassing | YES | Standalone class; injectable |
| C5: Cross-layer leakage | NO | Not a mixin |

**Criteria Met**: 3/5 → AMBIGUOUS

**Same abort conditions as OncpBuilder**: `OncpReader` is instantiated inline in `handler.py` (`OncpReader().open_bytes(raw_bytes)`) and passed through multiple private check methods. Injecting it as a handler dependency would expose the handler's internal check methods to external wiring, violating encapsulation (abort condition #3). No lifecycle management benefit (C2 = NO) means S3 signal cannot be satisfied.

**Conclusion**: AMBIGUOUS score + abort conditions. Do not convert.

**Decision: KEEP AS SERVICE**

---

## Summary Decision Table

| Service | Rubric Score | Abort Conditions | Decision |
|---------|-------------|-----------------|---------|
| `ServiceDiffFileStore` | 4/5 (CONVERT) | <2 ambiguity signals | **KEEP AS SERVICE** |
| `ServiceFileSink` | 4/5 (CONVERT) | <2 ambiguity signals | **KEEP AS SERVICE** |
| `OncpBuilder` | 3/5 (AMBIGUOUS) | Integration complexity + encapsulation | **KEEP AS SERVICE** |
| `OncpReader` | 3/5 (AMBIGUOUS) | Integration complexity + encapsulation | **KEEP AS SERVICE** |

---

## Why the Rubric Score Alone Is Insufficient

The classification rubric correctly scores `ServiceDiffFileStore` and `ServiceFileSink` as 4/5
(CONVERT), but the rubric is designed for **mixin-to-handler** conversions. These are already
standalone service classes. The handler pattern adds value specifically when:

1. I/O capability leaks into subclasses via inheritance (mixins) — not present here
2. Multiple callers must coordinate lifecycle management — not present here (each caller owns its own instance)
3. Testing requires subclassing to wire up the I/O — not present here

Section 8 of the classification rules makes this explicit: handlerization must satisfy **at
least two observable signals from Section 5**. When all five signals score NOT APPLICABLE or
MARGINAL for a standalone service class, the conversion would add handler scaffolding
(contract YAML, `initialize()`, `shutdown()`, injection wiring) with zero observable
architectural benefit.

**This is not a case where the rubric was wrong** — the rubric is working correctly. It
catches that the score is high because these classes genuinely own I/O. The abort conditions
exist precisely to prevent refactoring that increases complexity without yielding clarity.

---

## Relation to 3.1 POC (OMN-4005)

The 3.1 POC (OMN-4005, PR #706) concluded KEEP AS MIXIN for the postgres utility-function
mixins. That finding does not gate OMN-4010 (the PR explicitly states: "OMN-4010 should be
evaluated independently — this finding is specific to utility-function mixins").

OMN-4010 was evaluated independently. The outcome is KEEP AS SERVICE for all four targets,
reached via the abort conditions in Section 7 and Section 8, not the 3.1 POC finding.

---

## No Changes to Production Code

This ticket is **classification only**. No production files are modified. No tests are
changed. No handler contracts are created. All four services remain in their current
locations unchanged.

---

## References

- OMN-4004 — Handler classification rules (`HANDLER_CLASSIFICATION_RULES.md` in omnibase_infra)
- OMN-4005 — POC 3.1 classification assessment (`HANDLER_CLASSIFICATION_POC_3_1.md` in omnibase_infra, PR #706)
- `src/omnibase_core/services/diff/service_diff_file_store.py`
- `src/omnibase_core/services/sinks/service_sink_file.py`
- `src/omnibase_core/package/service_oncp_builder.py`
- `src/omnibase_core/package/service_oncp_reader.py`
- `src/omnibase_core/nodes/node_contract_verify_replay_compute/handler.py` (OncpReader usage)
- OMN-4014 — parent epic
