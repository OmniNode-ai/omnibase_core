# Architecture Handshakes

Centralized constraint maps for OmniNode repositories. These files prevent AI agents from hallucinating architecture by defining hard constraints that cannot be violated.

## What is a Handshake?

An architecture handshake is a **focused constraint map** - the minimum set of rules an agent MUST obey before writing any code.

```
CLAUDE.md = Full Operations Manual (comprehensive documentation)
architecture-handshake.md = Pre-flight Checklist (constraints checked every time)
```

## Structure

Each handshake follows a standard template:

```markdown
# OmniNode Architecture – Constraint Map (<repo-name>)

> **Role**: [Brief description of this repo's role]
> **Handshake Version**: 0.1.0

## Core Principles
- [Fundamental principles this repo embodies]

### This Repo Contains
- [What belongs here]

### Rules the Agent Must Obey
- [Hard constraints that cannot be violated]

### Non-Goals (DO NOT)
- [Things the agent should NOT do in this repo]

### Patterns to Avoid
- [Anti-patterns with brief explanations]
```

## Installation

### From omnibase_core

```bash
# Install to a specific repo
./architecture-handshakes/install.sh omniclaude

# Install with explicit path
./architecture-handshakes/install.sh omniclaude /path/to/omniclaude
```

### From target repo

```bash
# Run from the repo that depends on omnibase_core
../omnibase_core/architecture-handshakes/install.sh $(basename $(pwd))
```

### Verify installation

```bash
cat .claude/architecture-handshake.md
```

## Supported Repos

| Repo | Description |
|------|-------------|
| `omnibase_core` | Contracts, models, invariants, enums |
| `omnibase_infra` | Concrete implementations, Kafka, Postgres |
| `omnibase_spi` | Service Provider Interface definitions |
| `omniclaude` | Claude Code integration, hooks, skills |
| `omnidash` | Dashboard and visualization |
| `omniintelligence` | Learning, pattern extraction, ML |
| `omnimemory` | Persistence, recall, embeddings |
| `omninode_infra` | Node infrastructure services |

## When Handshakes Are Loaded

Handshakes are injected into agent context at:

1. **`/ticket-work` start** - Before research phase begins
2. **SessionStart hook** - When an active ticket is detected
3. **Resume** - When resuming interrupted ticket work

## Versioning

Handshakes are versioned with omnibase_core releases. After upgrading omnibase_core, re-run the installer to get updated constraints:

```bash
# After poetry update omnibase_core
../omnibase_core/architecture-handshakes/install.sh $(basename $(pwd))
```

## Adding a New Repo

1. Create `repos/<repo-name>.md` following the template
2. Add repo name to `SUPPORTED_REPOS` array in `install.sh`
3. Release omnibase_core with the new handshake

## Design Rationale

**Why separate from CLAUDE.md?**
- CLAUDE.md is comprehensive (500+ lines) - constraints may not stick
- Handshakes are focused (~50 lines) - quick to parse, hard to ignore
- Negative constraints ("don't do X") are clearer than positive guidance

**Why centralized in omnibase_core?**
- Single source of truth for architectural constraints
- Version-tracked and auditable
- Changes propagate via releases, not manual copying
