> **Navigation**: [Home](../INDEX.md) > [Decisions](README.md) > ADR Best Practices

# ADR Best Practices

## Document Purpose

This guide establishes best practices for writing and maintaining Architecture Decision Records (ADRs) in the omnibase_core project.

---

## Core Principles

### 1. Code References - Use Commit SHAs, Not Line Numbers

**Problem**: Line numbers become stale as code evolves, requiring frequent documentation updates.

**Solution**: Reference code using commit SHAs and method/function names.

#### ❌ Fragile (Line Numbers)

```markdown
### Implementation

The validation logic is implemented in:
- Lines 155-199: `validate_processing_time_ms` method
- Lines 201-233: `validate_items_processed` method
- Lines 47-119: Comprehensive documentation
```

**Issues**:
- Requires manual updates after every code change
- Difficult to verify accuracy
- Creates maintenance burden
- Breaks silently when code moves

#### ✅ Maintainable (Commit SHAs)

```markdown
### Implementation

The validation logic is implemented in `src/omnibase_core/models/reducer/model_reducer_output.py`:
- `validate_processing_time_ms` method (commit 4e97e09f)
- `validate_items_processed` method (commit 4e97e09f)
- Comprehensive documentation in class docstring (commit 6f218db4)
```

**Benefits**:
- Git commit SHA provides permanent reference
- Method names enable easy code navigation
- No updates needed when code moves
- Verifiable via `git show <SHA>`

#### How to Find Commit SHAs

```bash
# Find commits that modified a specific file
git log --oneline --all -- path/to/file.py | head -10

# Show what changed in a commit
git show 4e97e09f

# Find when a specific method was introduced
git log -p --all -S "def validate_processing_time_ms" -- path/to/file.py
```

---

### 2. Reference Format Standards

#### File References

**Format**: `path/to/file.py` - Brief description (commit SHA)

**Example**:
```markdown
- `src/omnibase_core/models/reducer/model_reducer_output.py` - ModelReducerOutput implementation (commit 4e97e09f)
```

#### Method/Class References

**Format**: `MethodName` or `ClassName` in `file.py` (commit SHA)

**Example**:
```markdown
- `validate_processing_time_ms` method in `model_reducer_output.py` (commit 4e97e09f)
- `TestModelReducerOutputValidation` class in `test_model_reducer_output.py` (commit bce11d16)
```

#### Section References (Documentation)

**Format**: Section description (commit SHA)

**Example**:
```markdown
- Sentinel semantics documentation in class docstring (commit 6f218db4)
```

---

### 3. ADR Structure

Every ADR should follow this structure:

```markdown
# ADR-NNN: Title

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Status** | 🟢 IMPLEMENTED / 🟡 IN PROGRESS / 🔴 REJECTED |
| **Created** | YYYY-MM-DD |
| **Last Updated** | YYYY-MM-DD |
| **Author** | Name |
| **Related PR** | [#NNN](link) |
| **Related Issue** | [ISSUE-NNN](link) |
| **Correlation ID** | UUID |
| **Implementation** | path/to/file.py |

## Executive Summary

Brief 2-3 sentence summary of the decision and its impact.

## Problem Statement

What problem are we solving?

## Options Considered

### Option A: [Chosen/Not Chosen]
Description, pros, cons

### Option B: [Chosen/Not Chosen]
Description, pros, cons

## Decision

What we decided and why.

## Implementation

Code references using commit SHAs (see section 1 above).

## Trade-offs

What trade-offs did we accept?

## References

### Related Documentation
- Links to related docs

### Related Code
- File references with commit SHAs

### Related Issues
- Links to issues/PRs

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| YYYY-MM-DD | 1.0 | Author | Initial version |
```

---

### 4. Status Indicators

Use emoji indicators for quick status scanning:

- 🟢 **IMPLEMENTED** - Decision is fully implemented
- 🟡 **IN PROGRESS** - Implementation underway
- 🔴 **REJECTED** - Decision was considered but not adopted
- ⚪ **SUPERSEDED** - Decision replaced by newer ADR (link to replacement)

---

### 5. Maintenance Model

#### When to Update an ADR

**Update if**:
- Implementation changes significantly
- New insights affect the trade-off analysis
- Related patterns evolve elsewhere in the codebase
- Code references become invalid (rare with commit SHAs)

**Don't update for**:
- Minor code refactoring (commit SHAs remain valid)
- Cosmetic changes
- Unrelated features

#### Superseding an ADR

When a decision is reversed or replaced:

1. Update status to ⚪ **SUPERSEDED**
2. Add supersession note at top:
   ```markdown
   > **SUPERSEDED**: This ADR is superseded by [ADR-NNN](link). See that document for current decision.
   ```
3. Link to the new ADR
4. Retain the original document for historical context
5. **Never delete ADRs** - they provide valuable historical context

---

### 6. Audience and Purpose

Every ADR should include an "Audience" section:

```markdown
## Target Audience

| Audience | Use Case |
|----------|----------|
| **Backend Developers** | Understanding when to apply pattern X |
| **Code Reviewers** | Evaluating PRs that use approach Y |
| **New Contributors** | Learning project conventions |
| **Architects** | Assessing system-wide strategy |
```

---

### 7. Commit Message Format

When committing ADR updates:

```bash
docs(adr): replace line references with commit SHAs [ADR-NNN]

- Replace fragile line number references with commit SHA references
- Update ADR-001 code references section
- Add ADR best practices guide
```

---

### 8. Examples

See these ADRs for reference implementations:

- **ADR-001**: Protocol-Based DI Architecture
  - Good example of code references with commit SHAs
  - Clear structure with metadata and trade-offs

- **ADR-002**: Centralized Field Limit Constants
  - Good example of standards-based rationale
  - Clear categorization and documentation

- **ADR-007**: Context Mutability Design Decision
  - Good example of trade-off analysis
  - Clear alternatives record

- **ADR-003**: Reducer Output Exception Consistency
  - Good example of test coverage references
  - Clear implementation status tracking
  - Comprehensive documentation of validation patterns

---

## Quick Reference

### ✅ Do

- Use commit SHAs for code references
- Include clear method/class names for navigation
- Maintain revision history
- Use status indicators
- Include target audience
- Document trade-offs
- Link to related issues/PRs

### ❌ Don't

- Use line numbers (fragile, high maintenance)
- Delete ADRs (mark as SUPERSEDED instead)
- Skip revision history
- Write without clear problem statement
- Omit implementation details
- Forget to update status indicators

---

**Last Updated**: 2025-12-16
**Related Documents**:
- ADR-001: Protocol-Based DI Architecture
- ADR-002: Centralized Field Limit Constants
- ADR-003: Reducer Output Exception Consistency
- ADR-007: Context Mutability Design Decision

**Correlation ID**: `95cac850-05a3-43e2-9e57-ccbbef683f43`
