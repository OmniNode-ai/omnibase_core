> **Navigation**: [Home](../INDEX.md) > Templates > Linear Issue Template

# Linear Issue Template - Omninode MVP Development

> **Scope**: This template applies to **all Omninode MVP projects** (omnibase_core, omnibase_spi, omnibase_infra), not just ONEX-specific work. Use this for any Linear issue in the MVP development phase.

---

## Template Content (copy everything below into Linear)

## Description

*Concise description of what needs to be done and why*

## Acceptance Criteria

- [ ] *Specific, testable criterion 1*
- [ ] *Specific, testable criterion 2*
- [ ] Type checking passes (`poetry run mypy --strict` or `poetry run pyright`)
- [ ] Tests pass with appropriate coverage

## Location

*path/to/file or directory*

## Dependencies

- *XXX (if any)*

## Cross-Repo Impact

Impact scope for coordinated changes across repositories:

- **core-only** - No cross-repo dependencies, changes isolated to one repository
- **core+spi** - Requires SPI protocol alignment, updates to both omnibase_core and omnibase_spi
- **core+spi+infra** - Requires all three repos, spans omnibase_core, omnibase_spi, and omnibase_infra

*core-only / core+spi / core+spi+infra*

> **Note**: For `core+spi` or `core+spi+infra` issues, check cross-repo synchronization points to understand blocking dependencies and release sequencing.

## TDD

*Required / Optional / None*

---

## Setup Instructions

1. Go to **Settings > Workspace > Templates** (or **Team > Templates**)
2. Click **Create template**
3. Name it "Omninode MVP Issue"
4. Copy the content above (from "## Description" to "## TDD")
5. Select the placeholder text (italicized parts) and click **Aa** in the formatting bar to mark as placeholder
6. Save the template

---

## Label Reference

**Repository (pick one):** `omnibase_core` | `omnibase_spi` | `omnibase_infra`

**Milestone (pick one):** `mvp` | `beta` | `production`

**Priority:** Urgent | High | Medium | Low

---

## TDD Guide

| Level | When | Examples |
|-------|------|----------|
| Required | New logic, validation, state machines | Validators, adapters, FSM |
| Optional | Migrations, refactoring, infra | File moves, deprecations |
| None | Config, CI, metadata | pyproject.toml, yaml |
