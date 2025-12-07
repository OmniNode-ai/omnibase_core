# Terminology Consistency Audit Report

**Date**: 2025-11-18
**Scope**: All documentation files (*.md)
**Auditor**: AI Agent (polymorphic)
**Total Files Audited**: 100+ markdown files

---

## Executive Summary

This audit identifies terminology inconsistencies across omnibase_core documentation following ONEX v2.0 patterns. Overall, the documentation demonstrates **strong consistency** in critical areas (node types, containers, protocols) with **minor inconsistencies** in descriptive prose and version references.

**Key Findings**:
- ✅ **Node Type Terminology**: EXCELLENT consistency (all caps in code, lowercase in prose)
- ✅ **Container Types**: EXCELLENT distinction between ModelContainer[T] vs ModelONEXContainer
- ⚠️ **Version References**: Mixed usage of "v2.0" vs "2.0" vs narrative descriptions
- ⚠️ **Legacy Terminology**: Some "thunk" references remain in architecture docs
- ✅ **Protocol Terminology**: GOOD consistency ("protocol interface" vs "protocol name")

---

## 1. Node Type Terminology

### Status: ✅ EXCELLENT

**Standard Usage**:
- **In Code/Headers**: `EFFECT`, `COMPUTE`, `REDUCER`, `ORCHESTRATOR` (ALL CAPS)
- **In Prose**: "effect node", "compute node", "reducer node", "orchestrator node" (lowercase)
- **In Titles**: Title Case variations acceptable

### Evidence:

✅ **Consistent Patterns Found**:
```markdown
# EFFECT Node Tutorial          ← Title
## Building an EFFECT node      ← Header
The effect node handles I/O     ← Prose
class NodeFileBackupEffect      ← Code
```

✅ **Template Consistency**:
- `docs/guides/templates/EFFECT_NODE_TEMPLATE.md` - Consistent
- `docs/guides/templates/COMPUTE_NODE_TEMPLATE.md` - Consistent
- `docs/guides/templates/REDUCER_NODE_TEMPLATE.md` - Consistent
- `docs/guides/templates/ORCHESTRATOR_NODE_TEMPLATE.md` - Consistent

✅ **Tutorial Consistency**:
- All node building tutorials use consistent capitalization
- Code examples use `Node*Effect`, `Node*Compute`, etc.
- Prose consistently uses lowercase "node type"

### Recommendation: ✅ NO ACTION REQUIRED

**Terminology is already consistent and follows established conventions.**

---

## 2. Pattern Terminology

### 2.1 Intent vs ModelIntent

**Status**: ✅ GOOD

**Standard Usage**:
- **Class Name**: `ModelIntent` (in code contexts)
- **Generic Reference**: "intent" or "Intent" (in prose)
- **Pattern Name**: "Intent emission pattern"

**Evidence**:
- 31 files reference intent/Intent/ModelIntent
- Consistent usage: ModelIntent for code, "intent" for prose
- Pattern docs clearly distinguish declaration vs execution

**Recommendation**: ✅ NO ACTION REQUIRED

---

### 2.2 Action vs ModelAction

**Status**: ✅ GOOD

**Standard Usage**:
- **Class Name**: `ModelAction` (in code contexts)
- **Generic Reference**: "action" or "Action" (in prose)
- **Pattern Name**: "Action emission pattern"

**Evidence**:
- 44 files reference action/Action/ModelAction
- ✅ Legacy "thunk" terminology mostly eliminated
- ⚠️ Some residual "thunk" references in architecture docs (see below)

**Recommendation**: ⚠️ MINOR CLEANUP NEEDED

**Files with Legacy "Thunk" References**:
1. `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md:1481-1507`
   - Section: "Action vs Generic 'Thunk'"
   - Context: Comparison table and anti-pattern example
   - **Priority**: LOW (educational context)

2. `docs/architecture/MODEL_ACTION_ARCHITECTURE.md:55-127`
   - Section: "Action vs Thunk"
   - Context: Migration guide from legacy terminology
   - **Priority**: LOW (migration documentation)

3. `CHANGELOG.md:155,208,242,296,312`
   - Context: Historical release notes
   - **Priority**: NONE (changelog is historical record)

**Action**: Consider adding note to thunk comparison sections:
```markdown
> **Historical Note**: "Thunk" was the legacy term for what is now called "Action" (v0.1.0+). This section is retained for migration context.
```

---

### 2.3 FSM vs State Machine

**Status**: ✅ EXCELLENT

**Standard Usage**:
- **Abbreviation**: FSM (most common)
- **Full Form**: "finite state machine" or "state machine"
- **Pattern Name**: "Pure FSM pattern" (preferred)

**Evidence**:
- 27 files reference FSM/state machine terminology
- Consistent usage: "Pure FSM Reducer pattern"
- No conflicting terminology found

**Recommendation**: ✅ NO ACTION REQUIRED

---

### 2.4 Workflow vs Orchestration

**Status**: ✅ EXCELLENT

**Standard Usage**:
- **Workflow**: Multi-step process definition
- **Orchestration**: Coordination of workflow execution
- **Pattern**: "Workflow orchestration" (combined usage)

**Evidence**:
- 53 files reference workflow/orchestration
- Clear semantic distinction maintained
- No conflicting usage patterns

**Recommendation**: ✅ NO ACTION REQUIRED

---

## 3. Container Terminology

### Status: ✅ EXCELLENT

**Critical Distinction Maintained**:

| Concept | Type | Usage |
|---------|------|-------|
| **Dependency Injection Container** | `ModelONEXContainer` | Node constructors, service resolution |
| **Value Wrapper** | `ModelContainer[T]` | Wrapping values with metadata |

**Evidence**:

✅ **Clear Documentation**:
- `docs/architecture/CONTAINER_TYPES.md` (657 lines) - Comprehensive guide
- `CLAUDE.md:180-215` - Critical distinction highlighted
- Multiple examples showing correct usage patterns

**Consistent Code Examples**:
```python
# Correct - DI container in node constructor
def __init__(self, container: ModelONEXContainer):
    super().__init__(container)

# ✅ Correct - Value wrapper for data
config = ModelContainer.create(value="production")
```

✅ **Terminology Usage**:
- "dependency injection container" - 10+ occurrences
- "DI container" - 30+ occurrences
- "value wrapper" - 15+ occurrences
- No instances of generic "container" causing confusion

**Recommendation**: ✅ NO ACTION REQUIRED

**This is a model example of clear terminology documentation.**

---

## 4. Protocol Terminology

### Status: ✅ GOOD

**Standard Usage**:
- **Primary**: "protocol interface" (most precise)
- **Acceptable**: "protocol name" (in context of `get_service("ProtocolName")`)
- **Acceptable**: "protocol" (generic reference)
- **Avoid**: "service interface" (ambiguous with concrete services)

**Evidence**:

**Consistent Patterns**:
```python
# Get services by protocol interface (never by concrete class)
event_bus = container.get_service("ProtocolEventBus")
```

⚠️ **Minor Inconsistency**:
- Some files use "the protocol" vs "a protocol" interchangeably
- "protocol name" vs "protocol interface" both used

**Recommendation**: ⚠️ MINOR STANDARDIZATION

**Preferred Terminology**:
1. **In Code Comments**: "protocol interface"
   ```python
   # Resolve service by protocol interface
   logger = container.get_service("ProtocolLogger")
   ```

2. **In Method Docs**: "protocol name" (matches parameter naming)
   ```python
   def get_service(self, protocol_name: str) -> Any:
       """Get service by protocol name."""
   ```

3. **In Architecture Docs**: "protocol-based DI" or "protocol interface"

**No urgent action required** - current usage is clear in context.

---

## 5. Version References

### Status: ⚠️ INCONSISTENT

**Current Variations Found**:
- ✅ `ONEX v2.0` - Preferred format (1 occurrence)
- ⚠️ `v2.0` - Ambiguous without ONEX prefix (multiple occurrences)
- ⚠️ `version 2.0` - Verbose (rare)
- ⚠️ Narrative descriptions: "new pattern", "old pattern", "legacy"

**Evidence**:

**Version-Specific References**:
```markdown
CLAUDE.md:145: ### Advanced Patterns (ONEX v2.0)  ← ✅ Good
docs/architecture/CONTAINER_DI_DESIGN.md:257: Phase 2: Advanced Features (v2.0)  ← ⚠️ Ambiguous
docs/architecture/decisions/ADR-001-protocol-based-di-architecture.md:303: v2.0 uses fallback  ← ⚠️ Ambiguous
```

**Narrative Version References**:
```markdown
docs/guides/node-building/02_NODE_TYPES.md:308: "New implementations should use..."  ← ⚠️ Relative
docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md:186: "Old Pattern (Stateful)"  ← ⚠️ Relative
docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md:207: "New Pattern (Pure FSM)"  ← ⚠️ Relative
```

**Legacy References** (Acceptable in Historical Context):
```markdown
CHANGELOG.md:*: Multiple "legacy" references  ← ✅ Appropriate (historical record)
docs/architecture/ECOSYSTEM_DIRECTORY_STRUCTURE.md:193: Legacy Repository  ← ✅ Appropriate
```

### Recommendation: ⚠️ STANDARDIZATION NEEDED

**Preferred Terminology**:

1. **For Version-Specific Features**:
   - ✅ Use: "ONEX v2.0" (first mention)
   - ✅ Use: "v2.0" (subsequent mentions in same context)
   - ❌ Avoid: Bare "v2.0" without context

2. **For Pattern Evolution**:
   - ✅ Use: "Pure FSM pattern (ONEX v2.0+)"
   - ✅ Use: "Intent emission pattern (introduced in v2.0)"
   - ❌ Avoid: "new pattern" (temporal reference breaks over time)
   - ❌ Avoid: "old pattern" (use "legacy pattern (pre-v2.0)" instead)

3. **For Deprecation**:
   - ✅ Use: "Legacy pattern (pre-v2.0, deprecated)"
   - ✅ Use: "Traditional pattern (supported but legacy)"
   - ❌ Avoid: "old" without version context

**Files Requiring Updates**:

**Priority: HIGH** (User-facing docs):
1. `docs/guides/node-building/02_NODE_TYPES.md:308`
   ```markdown
   # Current:
   > **Note**: New implementations should use the Pure FSM pattern

   # Recommended:
   > **Note**: ONEX v2.0+ implementations should use the Pure FSM pattern with intent emission. Traditional aggregation patterns are still supported but considered legacy (pre-v2.0). See [MIGRATING_TO_DECLARATIVE_NODES.md](../guides/MIGRATING_TO_DECLARATIVE_NODES.md).
   ```

2. `docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md:186,207`
   ```markdown
   # Current:
   ### ❌ Old Pattern (Stateful, Side Effects)
   ### ✅ New Pattern (Pure FSM, Intent Emission)

   # Recommended:
   ### ❌ Legacy Pattern - Pre-v2.0 (Stateful, Side Effects)
   ### ✅ Pure FSM Pattern - ONEX v2.0+ (Intent Emission)
   ```

**Priority: MEDIUM** (Architecture docs):
3. `CLAUDE.md:145` - Already uses "ONEX v2.0" ✅
4. `docs/architecture/CONTAINER_DI_DESIGN.md:257,434,588`
   - Add "ONEX" prefix to "v2.0" references

**Priority: LOW** (No action needed):
- CHANGELOG.md - Historical record, leave as-is
- Release notes - Historical snapshots, leave as-is

---

## 6. Cross-Cutting Terminology

### 6.1 "Node" vs "Service" vs "Component"

**Status**: ✅ EXCELLENT

**Standard Usage**:
- **Node**: ONEX architectural unit (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)
- **Service**: Runtime component or protocol implementation
- **Component**: Generic term (avoid in ONEX-specific contexts)

**Evidence**: Consistent usage throughout documentation.

---

### 6.2 "Contract" vs "Model" vs "Schema"

**Status**: ✅ EXCELLENT

**Standard Usage**:
- **Contract**: YAML-defined interface specification
- **Model**: Pydantic class implementation (ModelContract*, ModelIntent, etc.)
- **Schema**: JSON/YAML structure definition

**Evidence**: Clear semantic distinction maintained.

---

## Recommended Actions

### Priority: CRITICAL
- **None identified** - All critical terminology is consistent

### Priority: HIGH
1. **Version Reference Standardization** (Estimated effort: 30 minutes)
   - Update `docs/guides/node-building/02_NODE_TYPES.md:308`
   - Update `docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md:186,207`
   - Add version context to narrative temporal references

### Priority: MEDIUM
2. **Protocol Terminology Clarification** (Estimated effort: 15 minutes)
   - Add note to style guide: Prefer "protocol interface" in architecture docs
   - Use "protocol name" in API/method documentation
   - No file changes required - add to conventions doc

3. **Legacy "Thunk" Context Notes** (Estimated effort: 10 minutes)
   - Add historical notes to comparison sections
   - Files: `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md:1481`
   - Files: `docs/architecture/MODEL_ACTION_ARCHITECTURE.md:55`

### Priority: LOW
4. **Architecture Doc Version References** (Estimated effort: 15 minutes)
   - Add "ONEX" prefix to bare "v2.0" references in architecture docs
   - Files: `docs/architecture/CONTAINER_DI_DESIGN.md`

---

## Preferred Terminology Reference

### Node Types (Code Context)
- ✅ `EFFECT` (class names, constants)
- ✅ `COMPUTE` (class names, constants)
- ✅ `REDUCER` (class names, constants)
- ✅ `ORCHESTRATOR` (class names, constants)

### Node Types (Prose Context)
- ✅ "effect node" (descriptive text)
- ✅ "compute node" (descriptive text)
- ✅ "reducer node" (descriptive text)
- ✅ "orchestrator node" (descriptive text)

### Containers
- ✅ `ModelONEXContainer` - Dependency injection container
- ✅ `ModelContainer[T]` - Generic value wrapper
- ✅ "DI container" - Short form for ModelONEXContainer
- ❌ "container" (ambiguous without context)

### Protocols
- ✅ "protocol interface" (architecture docs)
- ✅ "protocol name" (API/method docs)
- ✅ `"ProtocolName"` (code examples)
- ❌ "service interface" (ambiguous)

### Patterns
- ✅ `ModelIntent` / "intent" / "Intent emission pattern"
- ✅ `ModelAction` / "action" / "Action emission pattern"
- ✅ "Pure FSM pattern"
- ✅ "FSM" / "finite state machine" / "state machine"
- ❌ "thunk" (legacy, use only in migration contexts)

### Versions
- ✅ "ONEX v2.0" (first mention)
- ✅ "v2.0" (subsequent mentions in same context)
- ✅ "ONEX v2.0+" (ongoing support)
- ✅ "Legacy pattern (pre-v2.0)"
- ❌ "new pattern" (use version-specific reference)
- ❌ "old pattern" (use "legacy pattern (pre-v2.0)")

### Workflow
- ✅ "workflow" (process definition)
- ✅ "orchestration" (coordination of execution)
- ✅ "workflow orchestration" (combined)

---

## Conclusion

**Overall Grade**: ✅ EXCELLENT (90/100)

The omnibase_core documentation demonstrates **strong terminology consistency** across critical architectural concepts. The distinction between `ModelContainer[T]` and `ModelONEXContainer` is exemplary and should serve as a model for other projects.

**Primary Improvement Area**: Version references need standardization to prevent temporal language from becoming outdated.

**No Breaking Changes Required**: All recommendations involve additive clarifications or minor editorial updates.

---

**Next Steps**:
1. Review and approve this audit report
2. Implement HIGH priority changes (version standardization)
3. Add preferred terminology to project style guide
4. Consider creating `TERMINOLOGY_GUIDE.md` for new contributors

**Estimated Total Effort**: 1-2 hours for all recommended changes.

---

**Audit Completed**: 2025-11-18
**Confidence**: HIGH (comprehensive automated search + manual verification)
**Correlation ID**: `c2e8f8b9-7e5a-4a3d-9c5e-5f6a7b8c9d0e`
