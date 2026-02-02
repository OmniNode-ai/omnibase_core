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
| `omnibase_infra` | Concrete implementations (Kafka, Postgres adapters) |
| `omnibase_spi` | Service Provider Interface definitions |
| `omniclaude` | Claude Code integration, hooks, skills |
| `omnidash` | Dashboard and visualization |
| `omniintelligence` | Learning, pattern extraction, ML |
| `omnimemory` | Persistence, recall, embeddings |
| `omninode_infra` | Deployment infrastructure (AWS, k8s, Terraform) |

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

## CI Integration

Downstream repos should add CI checks to ensure their handshake stays current with omnibase_core. This prevents architecture drift when omnibase_core releases new constraints.

### GitHub Actions

Add this job to your `.github/workflows/ci.yml`:

```yaml
jobs:
  check-handshake:
    name: Check architecture handshake
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Checkout omnibase_core
        uses: actions/checkout@v4
        with:
          repository: OmniNode/omnibase_core
          path: omnibase_core

      - name: Check architecture handshake
        run: |
          # Verify handshake is current with omnibase_core
          ./omnibase_core/architecture-handshakes/check-handshake.sh
```

### Pre-commit Hook (Optional)

For local development, add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: check-handshake
        name: Check architecture handshake
        entry: ../omnibase_core/architecture-handshakes/check-handshake.sh
        language: script
        pass_filenames: false
```

**Note**: The pre-commit hook requires `omnibase_core` to be cloned as a sibling directory.

### What the Check Does

The `check-handshake.sh` script:

1. **Verifies handshake exists** - Fails if `.claude/architecture-handshake.md` is missing
2. **Compares checksums** - Ensures installed handshake matches the source in omnibase_core
3. **Validates metadata** - Checks the `source_sha256` in the metadata block matches the current source file

This ensures agents always operate with the latest architectural constraints, preventing drift when omnibase_core releases updates.

## Metadata Block Format

Installed handshakes include a metadata block at the **beginning** of the file:

```markdown
<!-- HANDSHAKE_METADATA
source: omnibase_core/architecture-handshakes/repos/omniclaude.md
source_version: 0.12.0
source_sha256: a1b2c3d4e5f6...
installed_at: 2025-01-15T10:30:00Z
installed_by: jonah
-->
```

| Field | Description |
|-------|-------------|
| `source` | Full path to source file within omnibase_core |
| `source_version` | Version of omnibase_core (from pyproject.toml) |
| `source_sha256` | SHA256 hash of source file for integrity verification |
| `installed_at` | UTC timestamp when the handshake was installed |
| `installed_by` | Username of the person who ran the installer |

**Important**: Do not edit this block manually. The CI check uses `source_sha256` to detect tampering or drift.

## Troubleshooting

### "Handshake file not found"

```
Error: .claude/architecture-handshake.md not found
```

**Solution**: Run the installer from your repo:

```bash
../omnibase_core/architecture-handshakes/install.sh $(basename $(pwd))
```

### "Handshake checksum mismatch"

```
Error: Handshake is outdated (checksum mismatch)
```

**Cause**: The installed handshake differs from the current version in omnibase_core.

**Solution**: Re-run the installer to update:

```bash
../omnibase_core/architecture-handshakes/install.sh $(basename $(pwd))
git add .claude/architecture-handshake.md
git commit -m "chore: update architecture handshake"
```

### "Unknown repository"

```
Error: No handshake found for repo 'my-repo'
```

**Cause**: The repo name is not in the supported repos list.

**Solution**: Either:
1. Check spelling against the [Supported Repos](#supported-repos) table
2. Add a new handshake file (see [Adding a New Repo](#adding-a-new-repo))

### "Pre-commit hook fails but CI passes"

**Cause**: Local omnibase_core checkout is outdated.

**Solution**: Update your local omnibase_core:

```bash
cd ../omnibase_core
git pull origin main
```

### "Metadata block corrupted"

**Cause**: Manual editing of the metadata block or merge conflict.

**Solution**: Delete and reinstall:

```bash
rm .claude/architecture-handshake.md
../omnibase_core/architecture-handshakes/install.sh $(basename $(pwd))
```

## Design Rationale

**Why separate from CLAUDE.md?**
- CLAUDE.md is comprehensive (500+ lines) - constraints may not stick
- Handshakes are focused (~50 lines) - quick to parse, hard to ignore
- Negative constraints ("don't do X") are clearer than positive guidance

**Why centralized in omnibase_core?**
- Single source of truth for architectural constraints
- Version-tracked and auditable
- Changes propagate via releases, not manual copying

**Why CI checks?**
- Prevents architecture drift when omnibase_core releases updates
- Ensures all repos operate with current constraints
- Catches stale handshakes before they cause agent misbehavior
