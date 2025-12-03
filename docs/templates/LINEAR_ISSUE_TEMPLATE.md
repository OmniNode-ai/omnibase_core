# Linear Issue Template - ONEX MVP Development

Generic issue template for all Omninode MVP projects.

---

## Template Content (copy everything below into Linear)

## Description

*Concise description of what needs to be done and why*

## Acceptance Criteria

- [ ] *Specific, testable criterion 1*
- [ ] *Specific, testable criterion 2*
- [ ] Type checking passes (mypy --strict / pyright)
- [ ] Tests pass with appropriate coverage

## Location

*path/to/file or directory*

## Dependencies

- *OMN-XXX (if any)*

## Cross-Repo

*single repo / core+spi / core+spi+infra*

## TDD

*Required / Optional / None*

---

## Setup Instructions

1. Go to **Settings > Workspace > Templates** (or **Team > Templates**)
2. Click **Create template**
3. Name it "ONEX MVP Issue"
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
