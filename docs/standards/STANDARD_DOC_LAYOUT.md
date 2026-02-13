> **Navigation**: [Home](../INDEX.md) > [Standards](../standards/onex_terminology.md) > Standard Doc Layout

# Standard Documentation Layout

Prescriptive structure for the `docs/` directory in omnibase_core.

---

## Required Directories

```text
docs/
├── architecture/          # How ONEX works (system design, data flow, protocols)
├── conventions/           # Coding standards and naming conventions
├── decisions/             # ADRs — why things work the way they do
├── getting-started/       # Installation, quick start, first node
├── guides/                # Step-by-step tutorials and how-to guides
│   ├── node-building/     # Node building tutorial series (10 parts)
│   └── templates/         # Production-ready node templates (canonical location)
├── reference/             # API docs, contract specs, service wrappers
│   └── api/               # Per-module API reference (enums, models, nodes, utils)
└── standards/             # Normative specs (terminology, topic taxonomy, this file)
```

## Optional Directories

```text
docs/
├── ci/                    # CI monitoring, purity failures, deprecation warnings
├── contracts/             # Contract guides (handler, introspection, operation bindings)
├── patterns/              # Implementation patterns (circuit breaker, FSM, anti-patterns)
├── performance/           # Benchmark results and threshold definitions
├── services/              # Service documentation
├── testing/               # Test strategy, parallel testing, performance testing
└── troubleshooting/       # Debugging guides (async hangs, etc.)
```

---

## File Naming

| Pattern | Use |
|---------|-----|
| `UPPER_SNAKE_CASE.md` | All documentation files |
| `README.md` | Directory index files only |
| `ADR-NNN-<slug>.md` | Architecture Decision Records in `decisions/` |
| `NN_<TITLE>.md` | Numbered tutorial series (e.g., `01_WHAT_IS_A_NODE.md`) |

---

## Doc Authority Model

| Location | Contains | Does NOT Contain |
|----------|----------|------------------|
| **CLAUDE.md** | Hard constraints, invariants, rules, navigation pointers | Tutorials, API reference, architecture explanations, code examples |
| **docs/** | Explanations, tutorials, deep dives, architecture, reference | Rules that override CLAUDE.md |

**No duplication**: CLAUDE.md links to docs/ sections. CLAUDE.md does not re-explain what docs/ already covers.

---

## INDEX.md Requirements

The root `docs/INDEX.md` must include:

1. **Documentation Authority Model** table (CLAUDE.md vs docs/ roles)
2. **Quick Navigation** table (intent-based: "I want to...")
3. **Documentation Structure** with per-section tables linking to every doc
4. **Document Status** summary table

All links in INDEX.md must use relative paths and resolve to existing files.

---

## Deleted Content Policy

- Completed plans, stale analyses, and point-in-time reports are deleted outright
- No `archive/` directories — if unused, delete it
- Inbound links to deleted files must be removed or updated in the same commit
