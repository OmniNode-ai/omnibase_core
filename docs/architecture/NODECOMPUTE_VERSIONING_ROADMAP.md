# NodeCompute Versioning Roadmap

> **Version**: 1.0.0
> **Date**: 2025-12-07
> **Status**: Active
> **Ticket**: [OMN-465](https://linear.app/omninode/issue/OMN-465)
> **Author**: ONEX Framework Team

---

## Executive Summary

This document defines the versioning strategy for NodeCompute's contract-driven architecture. NodeCompute is a **platform primitive**, not a utility library. Its versioning philosophy prioritizes stability, predictability, and incremental complexity.

**Core Principle**: Ship boring first, earn complexity later.

---

## Table of Contents

1. [Versioning Philosophy](#versioning-philosophy)
2. [Version Summary](#version-summary)
3. [v1.0 - Core Sequential Pipelines](#v10---core-sequential-pipelines)
4. [v1.1 Roadmap - Control Flow](#v11-roadmap---control-flow)
5. [v1.2 Roadmap - Observability and Caching](#v12-roadmap---observability-and-caching)
6. [v1.3 Roadmap - Evolution and Governance](#v13-roadmap---evolution-and-governance)
7. [NOT in 1.x](#not-in-1x)
8. [Migration Path](#migration-path)
9. [References](#references)

---

## Versioning Philosophy

### NodeCompute is a Platform Primitive

NodeCompute is not a utility library that can be versioned casually. It is a **platform primitive** - a foundational building block upon which other ONEX components depend. This distinction demands a fundamentally different approach to versioning.

**What makes NodeCompute a platform primitive:**

1. **Ledger Integration**: NodeCompute transformations are recorded in the ONEX ledger for replay and audit. Breaking changes to transformation semantics break historical replay.

2. **Contract-Driven Execution**: Agents and orchestrators generate NodeCompute contracts programmatically. Schema instability causes agent failures at scale.

3. **Cross-Service Dependencies**: Multiple services depend on NodeCompute's transformation guarantees. Breaking changes cascade across the entire platform.

4. **Long-Lived State**: Cached results and ledger entries may reference transformation versions from months or years ago. Version stability is not optional.

### The "Boring First" Principle

v1.0 must be **small, boring, and stable**. This means:

**Small**: Include only what is necessary to prove the architecture works in production. Every additional feature is a liability until proven valuable.

**Boring**: No clever optimizations, no exotic features, no speculative additions. Boring code is debuggable code. Boring APIs are learnable APIs.

**Stable**: Once v1.0 ships, its behavior is frozen. No "minor breaking changes." No "technically backward compatible but different." Frozen.

### Earned Complexity

Each version after v1.0 must **earn its complexity** through demonstrated need:

1. **v1.0 proves**: "Can we wire production transforms through contracts?"
2. **v1.1 proves**: "Do we actually need control flow in NodeCompute?"
3. **v1.2 proves**: "Is observability worth the model complexity?"
4. **v1.3 proves**: "Can we evolve contracts without breaking replay?"

A feature graduates from "roadmap" to "implementation" only when:

- Real production workloads require it
- Simpler alternatives have been tried and rejected
- The implementation maintains all prior guarantees

### Version Guarantees

**Within 1.x (v1.0 through v1.3):**

| Guarantee | Description |
|-----------|-------------|
| **Schema Stability** | All v1.0 contracts remain valid in v1.3 |
| **Transformation Semantics** | Same input + same contract = same output |
| **Ledger Compatibility** | v1.0 ledger entries replayable by v1.3 executor |
| **Error Codes** | Error types are additive only, never removed |
| **Config Models** | Fields are additive only, never removed or retyped |

**What can change within 1.x:**

- New transformation types (additive)
- New step types (additive)
- New optional config fields with sensible defaults
- Performance improvements that preserve semantics
- New error types for new failure modes

**What cannot change within 1.x:**

- Existing transformation behavior
- Existing config field types or semantics
- Existing error type meanings
- Required field additions to existing models
- Removal of any public API

### Version Numbering

NodeCompute follows semantic versioning with platform-primitive semantics:

```
1.x.y
| | |
| | +-- Patch: Bug fixes, performance improvements (no API changes)
| +---- Minor: New features, new transformations (backward compatible)
+------ Major: Breaking changes (new replay epoch)
```

**Major version increments (2.0, 3.0) signal:**
- Ledger replay compatibility boundary
- Potential schema migration required
- Explicit opt-in from consumers

---

## Version Summary

| Version | Focus | Status | Documentation |
|---------|-------|--------|---------------|
| **v1.0** | Core sequential pipelines | Implementation Ready | [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md) |
| **v1.1** | Control flow (conditional, parallel) | Planned | [Section below](#v11-roadmap---control-flow) |
| **v1.2** | Caching, observability, replay | Planned | [Section below](#v12-roadmap---observability-and-caching) |
| **v1.3** | Cancellation, versioning, schema policy | Planned | [Section below](#v13-roadmap---evolution-and-governance) |

### Version Timeline (Tentative)

```
Q1 2025: v1.0 Implementation and Production Validation
Q2 2025: v1.1 Design and Implementation (if warranted)
Q3 2025: v1.2 Design and Implementation (if warranted)
Q4 2025: v1.3 Design and Implementation (if warranted)
```

**Note**: Each version's implementation depends on production feedback validating the need for additional complexity.

---

## v1.0 - Core Sequential Pipelines

### Goal

> "Can I wire real production transforms through contracts without embarrassment?"

v1.0 answers this question and nothing more. It proves that:

1. Contracts can define transformation pipelines
2. Pipelines execute deterministically
3. Results are suitable for ledger recording
4. The architecture scales to real workloads

### What v1.0 Includes

**Step Types (3):**
- `VALIDATION` - Schema validation against input/output refs (uses `ModelValidationStepConfig`)
- `TRANSFORMATION` - Apply a built-in transformation
- `MAPPING` - Shape results using simple path expressions (JSONPath-like)

**Note**: Validation is a **step type**, not a transformation. This keeps semantic boundaries clean:
- VALIDATION → schema checks
- TRANSFORMATION → pure data transforms
- MAPPING → shape results

**Transformation Types (6):**

| Type | Purpose | Config Model |
|------|---------|--------------|
| `regex` | Pattern matching and replacement | `ModelTransformRegexConfig` |
| `case_conversion` | Uppercase/lowercase/titlecase | `ModelTransformCaseConfig` |
| `normalize_unicode` | Unicode normalization (NFC, NFD, etc.) | `ModelTransformUnicodeConfig` |
| `trim` | Whitespace trimming | `ModelTransformTrimConfig` |
| `json_path` | JSONPath extraction | `ModelTransformJsonPathConfig` |
| `identity` | Pass-through (no-op) | (no config) |

**Core Models:**
- `ModelComputeSubcontract` - Contract definition
- `ModelComputePipelineStep` - Step definition
- `ModelComputeStepResult` - Step execution result
- Per-transformation config models (all with `extra="forbid"`, `frozen=True`)

**Execution Guarantees:**
- Sequential step execution in declaration order
- Deterministic output for same input
- Immediate abort on any step failure
- Schema references resolved at load time

### What v1.0 Excludes

**Explicitly deferred to v1.1:**
- `CONDITIONAL` step type
- `PARALLEL` step type
- `SPLIT`, `JOIN`, `TEMPLATE`, `TYPE_CONVERSION`, `SCHEMA_VALIDATE` transformation types
- Boolean expression language
- Arithmetic expressions

**Explicitly deferred to v1.2:**
- Caching configuration
- Debug metadata
- Performance metrics and timing
- Parallel execution statistics

**Explicitly deferred to v1.3:**
- Cooperative cancellation
- Transformation versioning
- Ledger replay version matching
- Schema version strictness

### v1.0 Contract Example

```yaml
node_type: COMPUTE
node_name: text_normalizer
node_version: "1.0.0"

compute_operations:
  version: "1.0.0"
  operation_name: normalize_text
  operation_version: "1.0.0"
  description: "Normalize text for consistent processing"

  input_schema_ref: text_input_v1
  output_schema_ref: text_output_v1
  pipeline_timeout_ms: 5000

  pipeline:
    - step_name: validate_input
      step_type: validation
      validation_config:
        config_type: validation
        schema_ref: input_schema
        fail_on_error: true

    - step_name: normalize_unicode
      step_type: transformation
      transformation_type: normalize_unicode
      transformation_config:
        config_type: normalize_unicode
        form: NFC

    - step_name: trim_whitespace
      step_type: transformation
      transformation_type: trim
      transformation_config:
        config_type: trim
        mode: both

    - step_name: collapse_spaces
      step_type: transformation
      transformation_type: regex
      transformation_config:
        config_type: regex
        pattern: "\\s+"
        replacement: " "

    - step_name: build_output
      step_type: mapping
      mapping_config:
        config_type: mapping
        field_mappings:
          normalized_text: "$.steps.collapse_spaces.output"
```

### v1.0 Success Criteria

- [ ] All 6 transformation types implemented with typed configs
- [ ] VALIDATION step type uses `ModelValidationStepConfig` (not a transformation)
- [ ] Sequential pipeline execution works end-to-end
- [ ] Schema validation at load time catches malformed contracts
- [ ] Deterministic execution verified via property-based tests
- [ ] At least 3 production workloads running on v1.0
- [ ] No `dict[str, Any]` at semantic boundaries
- [ ] mypy strict mode passes with zero errors

### Reference

See [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md) for the complete v1.0 specification.

---

## v1.1 Roadmap - Control Flow

### Goal

> "Can I express non-trivial control flow without writing Python?"

v1.1 introduces conditional branching and parallel execution. These features are **only implemented if v1.0 production usage demonstrates clear need**.

### Prerequisites

Before implementing v1.1:

1. v1.0 has been in production for at least 4 weeks
2. At least 2 production use cases explicitly require control flow
3. Workarounds using multiple nodes have proven unacceptable
4. Design review completed by ONEX architecture team

### What v1.1 Adds

**New Step Types:**

| Step Type | Purpose |
|-----------|---------|
| `CONDITIONAL` | Branch execution based on expression |
| `PARALLEL` | Execute substeps concurrently, merge results |

**New Transformation Types:**

| Type | Purpose | Config Model |
|------|---------|--------------|
| `split` | String to array splitting | `ModelTransformSplitConfig` |
| `join` | Array to string joining | `ModelTransformJoinConfig` |
| `template` | String templating | `ModelTransformTemplateConfig` |
| `type_conversion` | Type coercion | `ModelTransformTypeConversionConfig` |
| `schema_validate` | Schema validation as transform | `ModelTransformValidationConfig` |

**Note**: `MAPPING` step type with simple path expressions is already in v1.0.

**New Configuration Models:**

```python
class ModelConditionalConfig(BaseModel):
    """Conditional execution configuration."""
    config_type: Literal["conditional"] = "conditional"
    condition: str  # ONEX Expression Language
    then_steps: list[ModelComputePipelineStep]
    else_steps: list[ModelComputePipelineStep] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)


class EnumParallelMergeStrategy(str, Enum):
    """Deterministic merge strategies for parallel steps."""
    OBJECT = "object"   # Merge dicts
    ARRAY = "array"     # Concatenate arrays
    FIRST = "first"     # Take first result
    LAST = "last"       # Take last result


class ModelParallelConfig(BaseModel):
    """Parallel execution configuration."""
    config_type: Literal["parallel"] = "parallel"
    steps: list[ModelComputePipelineStep]
    merge_strategy: EnumParallelMergeStrategy = EnumParallelMergeStrategy.OBJECT
    max_parallelism: int | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelMappingConfig(BaseModel):
    """Field mapping configuration."""
    config_type: Literal["mapping"] = "mapping"
    field_mappings: dict[str, str]  # output_field -> path expression

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Basic Expression Language:**

v1.1 introduces a minimal expression language for conditions and mappings:

```ebnf
path        = "$" segment* ;
segment     = "." identifier | "[" index "]" ;
identifier  = letter (letter | digit | "_")* ;
index       = digit+ ;

expr        = path | path "==" literal | path "!=" literal | "!" expr ;
literal     = string | number | "true" | "false" | "null" ;
```

**Supported operators (v1.1 only):**
- `==`, `!=` - Equality comparison
- `!` - Logical NOT
- `&&`, `||` - Logical AND/OR

**Deferred operators (v1.3):**
- `<`, `<=`, `>`, `>=` - Numeric comparison
- `+`, `-`, `*`, `/`, `%` - Arithmetic
- `in` - Membership testing
- Function calls (`len()`, `exists()`, etc.)

**Optional New Transformations:**

If production use cases demand, v1.1 may include:

| Type | Purpose | Config Model |
|------|---------|--------------|
| `filter` | Filter collection elements | `ModelTransformFilterConfig` |
| `map` | Transform collection elements | `ModelTransformMapConfig` |
| `reduce` | Aggregate collection to scalar | `ModelTransformReduceConfig` |

These are **optional** - they are only added if v1.0 production feedback demonstrates need.

### What v1.1 Still Defers

**Deferred to v1.2:**
- Caching configuration
- Debug metadata and observability
- Performance timing and metrics

**Deferred to v1.3:**
- Cancellation
- Transformation versioning
- Schema evolution policies

### v1.1 Contract Example

```yaml
compute_operations:
  version: "1.1.0"
  operation_name: format_aware_processor
  operation_version: "1.0.0"
  description: "Process data based on detected format"

  pipeline:
    - step_name: detect_format
      step_type: transformation
      transformation_type: json_path
      config:
        path: "$.format"

    - step_name: process_by_format
      step_type: conditional
      conditional_config:
        condition: "$.steps.detect_format.output == 'json'"
        then_steps:
          - step_name: normalize_json
            step_type: transformation
            transformation_type: identity  # Placeholder for future json_normalize
        else_steps:
          - step_name: normalize_text
            step_type: transformation
            transformation_type: trim
            config:
              mode: both

    - step_name: aggregate_results
      step_type: parallel
      parallel_config:
        steps:
          - step_name: compute_length
            step_type: transformation
            transformation_type: json_path
            config:
              path: "$.length"
          - step_name: compute_hash
            step_type: transformation
            transformation_type: identity  # Placeholder
        merge_strategy: object

    - step_name: output_mapping
      step_type: mapping
      mapping_config:
        field_mappings:
          result: "$.steps.process_by_format.output"
          metadata.length: "$.steps.compute_length.output"
          metadata.hash: "$.steps.compute_hash.output"
```

### v1.1 Success Criteria

- [ ] Conditional branching executes correctly
- [ ] Parallel steps execute concurrently with deterministic merge
- [ ] Mapping expressions resolve paths correctly
- [ ] Expression evaluation is type-safe (no implicit coercion)
- [ ] All v1.0 contracts remain valid and produce identical output
- [ ] Forward references in expressions fail at contract load time

---

## v1.2 Roadmap - Observability and Caching

### Goal

> "Can I observe, cache, and reliably replay what happened?"

v1.2 adds production-grade observability and caching. These features require v1.0/v1.1 to be stable and well-understood.

### Prerequisites

Before implementing v1.2:

1. v1.1 has been in production for at least 4 weeks (or v1.0 if v1.1 was skipped)
2. Production monitoring reveals specific observability gaps
3. Cache hit rates justify caching complexity
4. Replay requirements are documented and tested

### What v1.2 Adds

**Caching Configuration:**

```python
class EnumEvictionPolicy(str, Enum):
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL_ONLY = "ttl_only"


class ModelComputeCaching(BaseModel):
    """Caching configuration for compute operations."""
    enabled: bool = False
    key_fields: list[str] = Field(default_factory=list)
    ttl_seconds: int = 3600
    eviction_policy: EnumEvictionPolicy = EnumEvictionPolicy.LRU
    max_size: int | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Cache Key Semantics:**

```python
# Cache key derivation (v1.2)
cache_key = hash(
    operation_name,
    operation_version,
    transformation_version,  # Bound to omnibase_core version
    tuple(resolve_key_field(data, field) for field in key_fields),
)
```

**Key fields must:**
- Be dot-notation paths into input data
- Be validated against `input_schema_ref` at load time
- Fail gracefully at runtime if unresolvable (cache miss, warning in debug metadata)

**Debug Metadata:**

v1.2 introduces the **only** approved use of `dict[str, Any]` - opaque debug metadata:

```python
class ModelComputeDebugMetadata(BaseModel):
    """
    Opaque debug metadata for pipeline execution.

    CRITICAL: This is the ONLY place where dict[str, Any] is allowed.
    This data MUST NOT affect deterministic behavior.
    This data MUST NOT be used for cache key derivation.
    This data MAY be omitted entirely in production mode.
    """
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")  # Intentionally permissive
```

**Performance Metrics:**

```python
class ModelComputePerformance(BaseModel):
    """Performance configuration and metrics."""
    timeout_ms: int | None = None
    pipeline_timeout_ms: int | None = None
    batch_size: int | None = None
    max_retries: int = 0
    retry_delay_ms: int = 100

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelComputeStepMetadata(BaseModel):
    """Execution metadata for a single step."""
    duration_ms: float
    cache_hit: bool = False
    warnings: list[str] = Field(default_factory=list)
    transformation_type: str | None = None
    input_type: str | None = None
    output_type: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Error Type Taxonomy:**

```python
class EnumComputeErrorType(str, Enum):
    """Structured error types for compute failures."""
    CONTRACT_VALIDATION = "contract_validation"
    SCHEMA_VALIDATION = "schema_validation"
    TRANSFORMATION = "transformation"
    EXPRESSION = "expression"
    TIMEOUT = "timeout"
    PARALLEL_FAILURE = "parallel_failure"
    FORWARD_REFERENCE = "forward_reference"
    CACHE_KEY_RESOLUTION = "cache_key_resolution"


class ModelComputeError(BaseModel):
    """Structured error for pipeline failures."""
    error_type: EnumComputeErrorType
    message: str
    step_name: str | None = None
    expression: str | None = None
    path: str | None = None
    stack_trace: str | None = None  # Debug mode only

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelParallelStepError(BaseModel):
    """Aggregated error for parallel step failures."""
    substep_errors: list[ModelComputeError]
    total_substeps: int
    failed_substeps: int
    completed_substeps: int

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Immutability Enforcement:**

v1.2 enforces `frozen=True` on all context and result models:

```python
class ModelComputeExecutionContext(BaseModel):
    """Typed execution context for compute pipelines."""
    operation_id: UUID
    computation_type: EnumComputationType
    correlation_id: UUID | None = None
    tenant_id: str | None = None
    node_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)  # Opaque only

    model_config = ConfigDict(frozen=True)  # FROZEN


class ModelComputeStepResult(BaseModel):
    """Result of a single pipeline step."""
    step_name: str
    output: Any
    success: bool = True
    metadata: ModelComputeStepMetadata
    error: ModelComputeError | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)  # FROZEN
```

### What v1.2 Still Defers

**Deferred to v1.3:**
- Cooperative cancellation
- Transformation version binding
- Ledger replay version matching
- Schema version strictness policies

### v1.2 Success Criteria

- [ ] Caching reduces redundant computation in production
- [ ] Cache keys are derived deterministically
- [ ] Debug metadata is non-semantic (removing it doesn't change output)
- [ ] Performance metrics accurately reflect execution time
- [ ] Error types cover all observed failure modes
- [ ] All models are immutable (frozen=True verified)
- [ ] All v1.0 and v1.1 contracts remain valid

---

## v1.3 Roadmap - Evolution and Governance

### Goal

> "Can I evolve this thing without hating myself?"

v1.3 adds the governance and evolution mechanisms needed for long-term maintenance. These features are complex and should only be implemented after v1.0-v1.2 are stable.

### Prerequisites

Before implementing v1.3:

1. v1.2 has been in production for at least 8 weeks
2. At least one schema evolution has been manually managed
3. Cancellation requirements are documented from orchestrator usage
4. Ledger replay has been validated against production entries

### What v1.3 Adds

**Cooperative Cancellation:**

```python
class ModelComputeCancellation(BaseModel):
    """Cancellation state for pipeline execution."""
    cancelled: bool = False
    reason: str | None = None
    requested_at: datetime | None = None

    model_config = ConfigDict(frozen=True)
```

**Cancellation semantics:**

| Phase | Behavior |
|-------|----------|
| Between steps | Check cancellation, abort if requested |
| During step | Step completes, then abort |
| During parallel | All substeps complete, then abort |

Cancellation is **cooperative**, not preemptive. Steps are never interrupted mid-execution.

**Transformation Versioning:**

```python
# Bound to omnibase_core version
TRANSFORMATION_VERSION = "1.3.0"

class ModelComputeSubcontract(BaseModel):
    # ... existing fields ...

    # Recorded at contract load time
    transformation_version: str = Field(default=TRANSFORMATION_VERSION)
```

**Ledger replay semantics:**

1. Ledger entries record `transformation_version`
2. Replay executor validates version compatibility
3. Mismatched versions fail with clear error
4. No automatic version migration (explicit operator action required)

**Schema Version Strictness:**

Schemas are frozen at contract load time:

```python
# At load time:
# 1. Resolve input_schema_ref from registry
# 2. Freeze resolved schema into contract
# 3. Schema updates in registry have no effect on loaded contract
# 4. New contracts get new schema version
```

**Expanded Expression Language:**

v1.3 completes the expression language:

```ebnf
# Arithmetic (v1.3)
add_expr    = mul_expr ( ("+" | "-") mul_expr )* ;
mul_expr    = unary_expr ( ("*" | "/" | "%") unary_expr )* ;

# Comparison (v1.3)
comp_op     = "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" ;

# Functions (v1.3)
func_call   = identifier "(" (expr ("," expr)*)? ")" ;
```

**Supported functions (v1.3):**

| Function | Description | Example |
|----------|-------------|---------|
| `len(x)` | Length of string/array | `len($.items) > 0` |
| `exists(path)` | Path exists and not null | `exists($.optional)` |
| `type(x)` | Type of value | `type($.value) == "string"` |
| `lower(s)` | Lowercase string | `lower($.text)` |
| `upper(s)` | Uppercase string | `upper($.text)` |

**Registry Lockdown:**

The transformation registry is **internal only**:

```python
def register_transformation(
    name: EnumTransformationType,
    handler: Callable[[Any, BaseModel], Any],
) -> None:
    """
    Register a transformation handler.

    NOTE: This is an INTERNAL runtime extension hook.
    - Application code CANNOT introduce new transformation types
    - All allowed transformations MUST be in EnumTransformationType
    - This function is ONLY called during ONEX Core initialization
    """
```

User-defined transformations are **not supported** in NodeCompute. Custom logic requires a different node family (NodeScript, NodeLambda, or custom nodes).

### v1.3 Success Criteria

- [ ] Cancellation works correctly from orchestrator
- [ ] Ledger replay validates transformation version
- [ ] Schema freezing prevents accidental version drift
- [ ] Expression language passes comprehensive fuzzing
- [ ] Registry lockdown prevents user-defined transformations
- [ ] All v1.0, v1.1, and v1.2 contracts remain valid

---

## NOT in 1.x

The following features are **explicitly out of scope** for the 1.x version family. They require major version increments (2.0+) or belong in separate products.

### Hot-Swappable Contracts (2.x)

Changing contracts on running NodeCompute instances is not supported in 1.x:

- Once attached, contracts cannot be changed
- New contracts require new NodeCompute instances
- In-flight executions use the original contract
- Hot-swapping introduces state management complexity that 1.x avoids

**Rationale**: Contract hot-swapping requires sophisticated state transfer, in-flight execution tracking, and rollback mechanisms. This complexity is not justified until v1.x has proven stable in production.

### Schema Migration Engine (Separate Product)

Automatic schema migration and backward compatibility checking is **not** part of NodeCompute:

- Schemas are frozen at load time
- Version mismatches fail explicitly
- No automatic type coercion or field mapping
- Migration is an operator responsibility

**Rationale**: Schema migration is a complex problem that deserves its own product. Embedding migration logic in NodeCompute would violate the "boring first" principle and introduce failure modes that are difficult to debug.

### User-Defined Transformations

NodeCompute does not support user-defined transformations:

- All transformation types are in `EnumTransformationType`
- No CUSTOM transformation type
- No runtime transformation registration
- Registry is internal to ONEX Core

**Rationale**: User-defined transformations break:

1. **Determinism**: Custom code can have side effects
2. **Replay**: Custom code may not be available at replay time
3. **Security**: Custom code can access arbitrary resources
4. **Versioning**: Custom code has independent versioning

**Alternative**: Users requiring custom transformations should use:

- **NodeScript**: For lightweight scripting (future)
- **NodeLambda**: For serverless functions (future)
- **Custom nodes**: For complex business logic (existing)

### Non-Deterministic Merge Strategies

Parallel step merge strategies in NodeCompute are strictly deterministic:

- No random selection
- No timing-based ordering
- No "fastest wins" semantics
- Declaration order is canonical

**Rationale**: Non-deterministic merge breaks ledger replay and makes debugging nearly impossible.

### Dynamic Step Generation

Pipeline steps are static and defined at contract load time:

- No runtime step injection
- No dynamic pipeline modification
- No conditional step generation based on data
- Pipeline structure is frozen

**Rationale**: Dynamic step generation would make contracts unpredictable and break static analysis tools.

---

## Migration Path

### v1.0 to v1.1

**What changes:**
- New step types: `CONDITIONAL`, `PARALLEL`, `MAPPING`
- New config models for new step types
- Basic expression language

**Migration effort:** None required

All v1.0 contracts work unchanged in v1.1. New features are additive only.

**Validation:**
```bash
# Verify v1.0 contract still works
poetry run pytest tests/contract_compatibility/test_v1_0_on_v1_1.py
```

### v1.1 to v1.2

**What changes:**
- Caching configuration added to subcontract
- Debug metadata added to results
- Performance metrics added to step results
- Error type taxonomy expanded
- Immutability enforcement

**Migration effort:** None required

All v1.0 and v1.1 contracts work unchanged in v1.2. New fields have sensible defaults.

**Validation:**
```bash
# Verify v1.0 and v1.1 contracts still work
poetry run pytest tests/contract_compatibility/test_v1_x_on_v1_2.py
```

### v1.2 to v1.3

**What changes:**
- Cancellation support added
- Transformation version recorded in subcontract
- Schema version strictness enforced
- Expression language expanded
- Registry lockdown enforced

**Migration effort:** None required

All v1.0, v1.1, and v1.2 contracts work unchanged in v1.3. Transformation version defaults to current version for existing contracts.

**Validation:**
```bash
# Verify all prior contracts still work
poetry run pytest tests/contract_compatibility/test_v1_x_on_v1_3.py
```

### Backward Compatibility Promise

**Within 1.x:**

```
Any contract valid in v1.0 MUST be valid in v1.3
Any contract valid in v1.0 MUST produce identical output in v1.3
Any ledger entry from v1.0 MUST be replayable in v1.3
```

This promise is **enforced by tests**, not just documented. The test suite includes:

1. **Contract Compatibility Tests**: Run all historic contracts on current version
2. **Output Determinism Tests**: Verify identical output across versions
3. **Ledger Replay Tests**: Replay production ledger entries

### When to Expect Breaking Changes (2.0)

A major version (2.0) will only be released when:

1. Accumulated technical debt makes 1.x maintenance unsustainable
2. Fundamental architecture changes are required for scaling
3. The ONEX ledger format requires incompatible changes
4. Security vulnerabilities require breaking changes

Major version releases will include:

- 6-month deprecation notice
- Automated migration tooling where possible
- Parallel support for 1.x and 2.x during transition
- Clear documentation of all breaking changes

---

## References

### Related Documents

| Document | Description |
|----------|-------------|
| [NODECOMPUTE_FULL_DESIGN_V1X_TARGET.md](NODECOMPUTE_FULL_DESIGN_V1X_TARGET.md) | Full vision for 1.x (v1.3.1 target) |
| [CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md](CONTRACT_DRIVEN_NODECOMPUTE_V1_0.md) | v1.0 implementation specification |
| [EXPRESSION_LANGUAGE_SPEC.md](EXPRESSION_LANGUAGE_SPEC.md) | ONEX Expression Language specification |
| [SUBCONTRACT_ARCHITECTURE.md](SUBCONTRACT_ARCHITECTURE.md) | Subcontract pattern documentation |
| [DECLARATIVE_IMPLEMENTATION_PLAN.md](DECLARATIVE_IMPLEMENTATION_PLAN.md) | Overall declarative node implementation |

### Linear Tickets

| Ticket | Description |
|--------|-------------|
| [OMN-465](https://linear.app/omninode/issue/OMN-465) | Contract-Driven NodeCompute |

### External Resources

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-07 | Initial roadmap document |

---

**Last Updated**: 2025-12-07
**Document Version**: 1.0.0
**Status**: Active
**Maintainer**: ONEX Framework Team
