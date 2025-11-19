# Terminology Fixes Checklist

**Based on**: TERMINOLOGY_AUDIT_REPORT.md
**Date**: 2025-11-18

---

## HIGH Priority Fixes (User-Facing Documentation)

### Fix 1: Node Types Tutorial - Version Context
**File**: `docs/guides/node-building/02_NODE_TYPES.md:308`

**Current** (Line 308):
```markdown
> **Note**: New implementations should use the Pure FSM pattern with intent emission (see below). Traditional aggregation patterns are still supported but considered legacy. See [MIGRATING_TO_DECLARATIVE_NODES.md](../guides/MIGRATING_TO_DECLARATIVE_NODES.md) for migration guidance.
```

**Recommended**:
```markdown
> **Note**: ONEX v2.0+ implementations should use the Pure FSM pattern with intent emission (see below). Traditional aggregation patterns are still supported but considered legacy (pre-v2.0). See [MIGRATING_TO_DECLARATIVE_NODES.md](../guides/MIGRATING_TO_DECLARATIVE_NODES.md) for migration guidance.
```

**Changes**:
- "New implementations" → "ONEX v2.0+ implementations"
- "considered legacy" → "considered legacy (pre-v2.0)"

**Impact**: Adds version context for future-proofing

---

### Fix 2: Reducer Tutorial - Pattern Headers
**File**: `docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md`

**Current** (Line 186):
```markdown
### ❌ Old Pattern (Stateful, Side Effects)
```

**Recommended**:
```markdown
### ❌ Legacy Pattern - Pre-v2.0 (Stateful, Side Effects)
```

**Current** (Line 207):
```markdown
### ✅ New Pattern (Pure FSM, Intent Emission)
```

**Recommended**:
```markdown
### ✅ Pure FSM Pattern - ONEX v2.0+ (Intent Emission)
```

**Changes**:
- "Old Pattern" → "Legacy Pattern - Pre-v2.0"
- "New Pattern" → "Pure FSM Pattern - ONEX v2.0+"

**Impact**:
- Removes temporal language that becomes outdated
- Adds explicit version markers
- Uses pattern names instead of relative terms

---

## MEDIUM Priority Fixes (Architecture Documentation)

### Fix 3: Container DI Design - Version Prefix
**File**: `docs/architecture/CONTAINER_DI_DESIGN.md`

**Current** (Line 257):
```markdown
### Phase 2: Advanced Features (v2.0)
```

**Recommended**:
```markdown
### Phase 2: Advanced Features (ONEX v2.0)
```

**Current** (Line 434):
```markdown
**Phase 2 (v2.0):**
```

**Recommended**:
```markdown
**Phase 2 (ONEX v2.0):**
```

**Current** (Line 588):
```markdown
### Phase 2: Advanced Features (v2.0)
```

**Recommended**:
```markdown
### Phase 2: Advanced Features (ONEX v2.0)
```

**Changes**: Add "ONEX" prefix to all "v2.0" references for context

**Impact**: Prevents ambiguity about which version system is referenced

---

### Fix 4: ADR-001 - Version Context
**File**: `docs/architecture/decisions/ADR-001-protocol-based-di-architecture.md`

**Current** (Line 303):
```markdown
**Migration Path**: v1.0 uses fallback, v2.0 will be ServiceRegistry-only.
```

**Recommended**:
```markdown
**Migration Path**: ONEX v1.0 uses fallback, ONEX v2.0 will be ServiceRegistry-only.
```

**Current** (Line 399):
```markdown
**Planned for v2.0**:
```

**Recommended**:
```markdown
**Planned for ONEX v2.0**:
```

**Current** (Line 420):
```markdown
**Phase 3 (v2.0.x)**: ServiceRegistry only
```

**Recommended**:
```markdown
**Phase 3 (ONEX v2.0.x)**: ServiceRegistry only
```

**Changes**: Add "ONEX" prefix for clarity

---

## LOW Priority Fixes (Optional Context Notes)

### Fix 5: Action vs Thunk - Historical Note
**File**: `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md:1481`

**Current**:
```markdown
### Action vs Generic "Thunk"
```

**Recommended** (Add note after header):
```markdown
### Action vs Generic "Thunk"

> **Historical Note**: "Thunk" was the legacy term for what is now called "Action" (changed in ONEX v0.1.0). This comparison is retained for migration context and to illustrate anti-patterns.
```

**Impact**: Clarifies that section is historical/educational

---

### Fix 6: Model Action Architecture - Migration Note
**File**: `docs/architecture/MODEL_ACTION_ARCHITECTURE.md:55`

**Current**:
```markdown
## Action vs Thunk
```

**Recommended** (Add note after header):
```markdown
## Action vs Thunk

> **Migration Guide**: This section documents the ONEX v0.1.0 terminology change from "Thunk" to "Action". If you're maintaining pre-v0.1.0 code, see the migration checklist below.
```

**Impact**: Contextualizes migration documentation

---

## NO ACTION NEEDED (Already Excellent)

### ✅ Node Type Terminology
- All caps in code: `EFFECT`, `COMPUTE`, `REDUCER`, `ORCHESTRATOR`
- Lowercase in prose: "effect node", "compute node", etc.
- Consistent across 100+ files

### ✅ Container Types
- Clear distinction: `ModelONEXContainer` (DI) vs `ModelContainer[T]` (value wrapper)
- Comprehensive documentation in `docs/architecture/CONTAINER_TYPES.md`
- No instances of confusion in examples

### ✅ Protocol Terminology
- Consistent usage: "protocol interface" in architecture, "protocol name" in API docs
- Clear examples throughout
- No breaking inconsistencies

### ✅ Intent/Action Patterns
- `ModelIntent` vs "intent" usage consistent
- `ModelAction` vs "action" usage consistent
- Pattern names well-established

### ✅ FSM Terminology
- "Pure FSM pattern" established
- "FSM" / "finite state machine" / "state machine" used appropriately
- No conflicts

---

## Implementation Checklist

- [ ] **HIGH Priority**: Fix 1 - `docs/guides/node-building/02_NODE_TYPES.md:308`
- [ ] **HIGH Priority**: Fix 2 - `docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md:186,207`
- [ ] **MEDIUM Priority**: Fix 3 - `docs/architecture/CONTAINER_DI_DESIGN.md:257,434,588`
- [ ] **MEDIUM Priority**: Fix 4 - `docs/architecture/decisions/ADR-001-protocol-based-di-architecture.md:303,399,420`
- [ ] **LOW Priority**: Fix 5 - `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md:1481`
- [ ] **LOW Priority**: Fix 6 - `docs/architecture/MODEL_ACTION_ARCHITECTURE.md:55`

---

## Estimated Effort

| Priority | Fixes | Time Estimate |
|----------|-------|---------------|
| HIGH | 2 fixes, 4 changes | 15 minutes |
| MEDIUM | 2 fixes, 6 changes | 20 minutes |
| LOW | 2 fixes, 2 changes | 10 minutes |
| **TOTAL** | **6 fixes, 12 changes** | **45 minutes** |

---

## Validation Checklist

After implementing fixes:

- [ ] Run `grep -rn "New implementations" docs/` (should return 0 results)
- [ ] Run `grep -rn "Old Pattern" docs/` (should return 0 results in tutorials)
- [ ] Run `grep -rn "\\bv2\\.0\\b" docs/architecture/` (verify all have "ONEX" prefix)
- [ ] Review updated files for readability
- [ ] Commit with message: `docs: standardize version terminology across documentation`

---

## Future Prevention

### Add to Style Guide
Create `docs/conventions/TERMINOLOGY_GUIDE.md` with:

1. **Node Type Capitalization Rules**
2. **Container Type Distinctions**
3. **Version Reference Standards**
4. **Pattern Name Conventions**
5. **Temporal Language Avoidance**

### Pre-Commit Hook Suggestion
```
# Detect temporal language in documentation
if git diff --cached --name-only | grep -q '\.md$'; then
    if git diff --cached | grep -E "(New pattern|Old pattern|new feature|old feature)"; then
        echo "⚠️  Warning: Temporal language detected in docs. Consider using version-specific terms."
    fi
fi
```

---

**Document Status**: Ready for implementation
**Approval Required**: Technical writer or project maintainer
**Target Completion**: Next documentation sprint
