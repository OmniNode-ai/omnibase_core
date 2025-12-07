# Contract-Driven NodeCompute Architecture Design

> **Version**: 1.3.1
> **Date**: 2025-12-07
> **Status**: DRAFT - Pending Implementation
> **Ticket**: [OMN-465](https://linear.app/omninode/issue/OMN-465)
> **Author**: ONEX Framework Team

---

## Executive Summary

This document describes the architecture for implementing contract-driven `NodeCompute`, following the established patterns from `NodeReducer` (FSM-driven) and `NodeOrchestrator` (workflow-driven). The goal is **zero custom Python code** - all computation logic defined declaratively in YAML contracts.

**Key Principles**:
1. NodeCompute nodes should be created by simply inheriting from the base class and defining a YAML contract
2. The contract specifies the transformation pipeline, and the mixin executes it
3. **All semantic boundaries use Pydantic models** - `dict[str, Any]` is only permitted for opaque metadata that does not affect deterministic behavior

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Pattern Comparison](#pattern-comparison)
3. [Component Design](#component-design)
4. [ModelComputeSubcontract Schema](#modelcomputesubcontract-schema)
5. [MixinComputeExecution Interface](#mixincomputeexecution-interface)
6. [Compute Executor Utilities](#compute-executor-utilities)
7. [Transformation Registry](#transformation-registry)
8. [Example Contracts](#example-contracts)
9. [Migration Path](#migration-path)
10. [Implementation Plan](#implementation-plan)

---

## Architecture Overview

### Component Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                   YAML Contract (New)                        │
│                 ModelComputeSubcontract                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Execution Mixin (New)                           │
│              MixinComputeExecution                           │
│   - execute_compute_pipeline()                               │
│   - validate_compute_contract()                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Utility Module (New)                              │
│            utils/compute_executor.py                         │
│   - Pure functions for pipeline execution                    │
│   - Transformation registry                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│        Refactored NodeCompute                                │
│   class NodeCompute(NodeCoreBase, MixinComputeExecution):   │
│       pass  # All logic from contract via mixin              │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Zero Custom Code**: Developers inherit from `NodeCompute` without writing transformation logic
2. **Pipeline-Driven**: Computations are sequences of named steps, each with a specific type
3. **Transformation Registry**: Built-in transformations (regex, case, mapping) + extensibility
4. **Pure Functions**: All execution logic in utility module for testability
5. **Consistent Patterns**: Follows `NodeReducer`/`NodeOrchestrator` mixin patterns exactly
6. **Typed Boundaries**: All public surfaces use Pydantic models - `dict[str, Any]` only for opaque metadata

### Type Safety Invariants

**Critical Design Rule**: All semantic boundaries are represented by Pydantic models. Raw dicts (`dict[str, Any]`) are only used for:
- Opaque debug metadata that does not affect determinism
- Best-effort `extra` fields that are never required for correctness

This ensures:
- **Stable serialization** for ledger entries and cache keys
- **Static guarantees** - contracts validated into models at load time
- **Safer evolution** - breaking changes caught by mypy, not discovered at runtime

---

## Pattern Comparison

| Aspect | NodeReducer | NodeOrchestrator | NodeCompute (New) |
|--------|-------------|------------------|-------------------|
| **Subcontract** | `ModelFSMSubcontract` | `ModelWorkflowDefinition` | `ModelComputeSubcontract` |
| **Mixin** | `MixinFSMExecution` | `MixinWorkflowExecution` | `MixinComputeExecution` |
| **Executor** | `utils/fsm_executor.py` | `utils/workflow_executor.py` | `utils/compute_executor.py` |
| **Core Unit** | State + Transitions | Steps + Dependencies | Pipeline Steps + Transformations |
| **Side Effects** | Emits `ModelIntent` | Emits `ModelAction` | Returns transformed data (pure) |
| **Driving Paradigm** | FSM (state machine) | Workflow (DAG) | Pipeline (sequential/parallel) |

### Key Insight: Compute is "Pure"

Unlike Reducer (FSM with intents) and Orchestrator (workflow with actions), Compute is fundamentally **pure transformation**:
- Input data → Pipeline steps → Output data
- No side effects emitted (that's Effect node's job)
- Caching and performance are contract-configurable
- Results are deterministic for same inputs

---

## Typed Model Boundaries

### Execution Context Model

Replace `dict[str, Any]` context with explicit typed model:

```python
class ModelComputeExecutionContext(BaseModel):
    """
    Typed execution context for compute pipelines.

    All fields are required for determinism except `extra`.
    """

    operation_id: UUID
    computation_type: EnumComputationType
    correlation_id: UUID | None = None
    tenant_id: str | None = None
    node_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)  # Opaque, not for correctness

    model_config = ConfigDict(frozen=True)  # Immutable for hash stability
```

### Step Result Models

Replace `dict[str, Any]` step results with typed models:

```python
class ModelComputeStepMetadata(BaseModel):
    """Metadata for a single pipeline step execution."""

    duration_ms: float
    cache_hit: bool = False
    warnings: list[str] = Field(default_factory=list)
    transformation_type: str | None = None
    input_type: str | None = None
    output_type: str | None = None


class ModelComputeStepResult(BaseModel):
    """Result of a single pipeline step."""

    step_name: str
    output: Any  # Actual output - type varies by step
    success: bool = True
    metadata: ModelComputeStepMetadata
    error: str | None = None

    # NOTE: See "Pipeline Context Immutability" section for final
    # model_config with frozen=True and extra="forbid"
```

### Transformation Config Models

Replace generic `config: dict[str, Any]` with typed per-transformation configs:

```python
class EnumCaseMode(str, Enum):
    """Case transformation modes."""
    UPPER = "uppercase"
    LOWER = "lowercase"
    TITLE = "titlecase"


class EnumRegexFlag(str, Enum):
    """Supported regex flags."""
    IGNORECASE = "IGNORECASE"
    MULTILINE = "MULTILINE"
    DOTALL = "DOTALL"


class EnumUnicodeForm(str, Enum):
    """Unicode normalization forms."""
    NFC = "NFC"
    NFD = "NFD"
    NFKC = "NFKC"
    NFKD = "NFKD"


class EnumTrimMode(str, Enum):
    """Whitespace trim modes."""
    BOTH = "both"
    LEFT = "left"
    RIGHT = "right"


# Per-transformation config models
# NOTE: Each model MUST define a `config_type` literal field for discriminated union support

class ModelTransformRegexConfig(BaseModel):
    """Configuration for regex transformation."""
    config_type: Literal["regex"] = "regex"
    pattern: str
    replacement: str = ""
    flags: list[EnumRegexFlag] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformCaseConfig(BaseModel):
    """Configuration for case transformation."""
    config_type: Literal["case_conversion"] = "case_conversion"
    mode: EnumCaseMode

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformUnicodeConfig(BaseModel):
    """Configuration for unicode normalization."""
    config_type: Literal["normalize_unicode"] = "normalize_unicode"
    form: EnumUnicodeForm = EnumUnicodeForm.NFC

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformTrimConfig(BaseModel):
    """Configuration for whitespace trimming."""
    config_type: Literal["trim"] = "trim"
    mode: EnumTrimMode = EnumTrimMode.BOTH

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformSplitConfig(BaseModel):
    """Configuration for string splitting."""
    config_type: Literal["split"] = "split"
    delimiter: str
    max_splits: int | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformJoinConfig(BaseModel):
    """Configuration for array joining."""
    config_type: Literal["join"] = "join"
    delimiter: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformJsonPathConfig(BaseModel):
    """Configuration for JSONPath extraction."""
    config_type: Literal["json_path"] = "json_path"
    path: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformTemplateConfig(BaseModel):
    """Configuration for string templating."""
    config_type: Literal["template"] = "template"
    template: str
    variables: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformFilterConfig(BaseModel):
    """Configuration for collection filtering."""
    config_type: Literal["filter"] = "filter"
    condition: str  # Expression string

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformReduceConfig(BaseModel):
    """Configuration for collection reduction."""
    config_type: Literal["reduce"] = "reduce"
    operation: str  # sum, count, average, min, max

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelTransformValidationConfig(BaseModel):
    """Configuration for schema validation."""
    config_type: Literal["schema_validate"] = "schema_validate"
    schema_ref: str
    fail_on_error: bool = True

    model_config = ConfigDict(extra="forbid", frozen=True)


# Tagged union for all transformation configs
# NOTE: This union MUST include ALL transformation config models
ModelTransformationConfig = Annotated[
    ModelTransformRegexConfig
    | ModelTransformCaseConfig
    | ModelTransformUnicodeConfig
    | ModelTransformTrimConfig
    | ModelTransformSplitConfig
    | ModelTransformJoinConfig
    | ModelTransformJsonPathConfig
    | ModelTransformTemplateConfig
    | ModelTransformFilterConfig
    | ModelTransformReduceConfig
    | ModelTransformValidationConfig
    | ModelTransformTypeConversionConfig  # Defined in Additional Config Models section
    | ModelTransformMapConfig             # Defined in Additional Config Models section
    | ModelTransformSortConfig,           # Defined in Additional Config Models section
    Field(discriminator="config_type"),   # Discriminated union
]
```

### Pipeline Step Model (Typed)

```python
class EnumComputeStepType(str, Enum):
    """Pipeline step types."""
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    MAPPING = "mapping"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


class EnumTransformationType(str, Enum):
    """
    Transformation types for registry lookup.

    NOTE: NodeCompute is restricted to built-in transformation types only.
    There is no CUSTOM type - custom transformations require a different
    node family or runtime extension mechanism.
    """
    REGEX = "regex"
    CASE_CONVERSION = "case_conversion"
    NORMALIZE_UNICODE = "normalize_unicode"
    TRIM = "trim"
    SPLIT = "split"
    JOIN = "join"
    JSON_PATH = "json_path"
    TEMPLATE = "template"
    FILTER = "filter"
    MAP = "map"
    REDUCE = "reduce"
    SORT = "sort"
    TYPE_CONVERSION = "type_conversion"
    SCHEMA_VALIDATE = "schema_validate"
    IDENTITY = "identity"
    # NOTE: No CUSTOM type - NodeCompute is fully contract-driven and replayable


class ModelComputePipelineStep(BaseModel):
    """
    A single step in the compute pipeline.

    Uses typed config models instead of dict[str, Any].
    """

    step_name: str
    step_type: EnumComputeStepType

    # For transformation steps
    transformation_type: EnumTransformationType | None = None
    transformation_config: ModelTransformationConfig | None = None

    # For mapping steps
    mapping_config: ModelMappingConfig | None = None

    # For conditional steps
    conditional_config: ModelConditionalConfig | None = None

    # For parallel steps
    parallel_config: ModelParallelConfig | None = None

    # Common options
    enabled: bool = True
    timeout_ms: int | None = None

    @model_validator(mode="after")
    def validate_step_config(self) -> "ModelComputePipelineStep":
        """Ensure correct config is provided for step type."""
        if self.step_type == EnumComputeStepType.TRANSFORMATION:
            if self.transformation_type is None:
                raise ValueError("transformation_type required for transformation steps")
        return self
```

---

## Execution Guarantees

This section consolidates all guarantees that make NodeCompute deterministic, replayable, and safe for ONEX ledger integration.

### 1. Determinism

NodeCompute pipelines must be fully deterministic:

**No External I/O**:
- No network calls
- No file system access
- No environment-dependent behavior
- All I/O belongs in Effect nodes

**No Randomness or Time-Based Behavior**:
- No RNG usage
- No direct wall-clock calls
- Any time-related value must enter via `ModelComputeInput`

**Violation Handling**: Any transformation that violates these rules leads to contract validation failure at load time.

### 2. Config Resolution

YAML contracts use a generic `config` field parsed into typed Pydantic models at load time:

```text
YAML Contract (generic config)
         │
         ▼
┌─────────────────────────────────┐
│ Contract Loader                  │
│ 1. Read transformation_type      │
│ 2. Select config model class     │
│ 3. Validate config into model    │
└─────────────────────────────────┘
         │
         ▼
Typed ModelTransformationConfig
```

**Rules**:
- `transformation_type` selects the config model (e.g., `regex` → `ModelTransformRegexConfig`)
- YAML `config` maps to `ModelTransformationConfig` via the discriminator
- **Hard failure on mismatch**: If `transformation_type` does not map to a known config model, or `config` cannot be parsed, contract validation fails and NodeCompute must not start
- Extra or missing fields result in hard failure - no partial pipeline load
- Runtime never receives `dict[str, Any]` for configuration

### 3. Caching

**Cache Key Derivation**:
```python
cache_key = hash(
    operation_name,
    operation_version,
    tuple(resolve_key_field(data, field) for field in key_fields),
)
```

**Key Fields**:
- Dot-notation paths resolved against `ModelComputeInput.data`
- Validated against `input_schema_ref` where possible

**Validation Rules**:
- At contract load time: Unresolvable `key_fields` cause validation failure if schema exists
- If no `input_schema_ref` is provided: Allow but emit warning in debug metadata
- At runtime: If any `key_field` cannot be resolved, disable caching for that call and emit non-fatal warning in `ModelComputePipelineResult.debug_metadata`

**Never Part of Cache Key**:
- `ModelComputeExecutionContext.extra`
- `ModelComputeExecutionContext.correlation_id`
- `ModelComputeDebugMetadata`
- Any field not listed in `key_fields`

### 4. Parallel Semantics

**Execution Model**:
- Parallel execution is only expressed via `EnumComputeStepType.PARALLEL`
- Merge strategies must be deterministic

**Ordering Rules**:
- Substep list order in the contract is canonical
- Logical ordering for merge is the declaration order
- Physical execution may be concurrent, but merge always respects original order

**Example**:
```yaml
steps:
  - compute_sum
  - compute_count
  - compute_avg
```

Merge result is always equivalent to applying in declaration order, regardless of runtime scheduling.

**Forbidden**: Non-deterministic merge strategies are not allowed in NodeCompute.

### 5. No Custom Transformations

- `EnumTransformationType` does not include `CUSTOM`
- NodeCompute is restricted to built-in transformation types only
- Custom transformations require a different node family or runtime extension mechanism
- This ensures all NodeCompute behavior is fully contract-driven and replayable

### 6. Unknown Fields in Contracts

Any unknown fields in:
- `compute_operations`
- `pipeline` steps
- transformation `config` blocks

Must be treated as validation errors, not ignored.

**Rationale**: Prevents silent typos in contracts and keeps the contract surface stable.

**Implementation**: Use Pydantic `extra = "forbid"` on all contract-side models.

### 7. Immutability

- All context and step-level models are immutable by default
- `ModelComputeExecutionContext`: `model_config = ConfigDict(frozen=True)`
- `ModelComputeStepResult`: Frozen after construction
- Mutation of pipeline state only through controlled internal structures

This prevents accidental mutation between steps or after execution.

---

## Schema Resolution

### Identifier Format

Schema identifiers follow the pattern:
- Base name: `[a-zA-Z0-9_]+`
- Version suffix: `_v[0-9]+`
- Example: `text_processor_input_v1`

### Resolution Algorithm

Given `schema_ref` in a validation step:

1. If `schema_ref == "input_schema"`: Resolve to `compute_contract.input_schema_ref`
2. If `schema_ref == "output_schema"`: Resolve to `compute_contract.output_schema_ref`
3. Otherwise: Resolve against the global schema registry by name

### Collision Rules

- Contract-local aliases win: If `input_schema_ref` or `output_schema_ref` collide with a global name, the contract-local value is used
- Global registry requires unique `(name, version)` pairs

### Failure Behavior

If a schema reference cannot be resolved:
- Contract validation fails
- NodeCompute instance must not start

---

## Missing Config Models

### ModelMappingConfig

```python
class ModelMappingConfig(BaseModel):
    """
    Mapping configuration.

    `field_mappings` uses ONEX Path Expressions
    evaluated against step results and input.
    """

    field_mappings: dict[str, str]

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelConditionalConfig

```python
class ModelConditionalConfig(BaseModel):
    """
    Conditional execution configuration.

    The `condition` expression is evaluated against the
    pipeline context (input data and step results).
    """

    condition: str  # ONEX Expression Language
    then_steps: list["ModelComputePipelineStep"]
    else_steps: list["ModelComputePipelineStep"] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelParallelConfig

```python
class EnumParallelMergeStrategy(str, Enum):
    """Deterministic merge strategies for parallel steps."""
    OBJECT = "object"   # Merge dicts
    ARRAY = "array"     # Concatenate arrays
    FIRST = "first"     # Take first result
    LAST = "last"       # Take last result


class ModelParallelConfig(BaseModel):
    """
    Parallel execution configuration.

    `steps` are executed in parallel, merged according
    to a deterministic strategy in declaration order.
    """

    steps: list["ModelComputePipelineStep"]
    merge_strategy: EnumParallelMergeStrategy = EnumParallelMergeStrategy.OBJECT
    max_parallelism: int | None = None  # Optional concurrency limit

    model_config = ConfigDict(extra="forbid", frozen=True)
```

---

## ONEX Expression Language

All expression and path fields use the **ONEX Expression Language**. This section defines the grammar, semantics, and evaluation rules.

> **Canonical Source**: The authoritative definition of the ONEX Expression Language lives in `EXPRESSION_LANGUAGE_SPEC.md`. This section is a curated subset tailored specifically for NodeCompute contracts and must remain consistent with the canonical spec. **If there is any conflict, the canonical spec wins.**

### Expression Contexts

| Field | Context | Example |
|-------|---------|---------|
| `condition` in conditional steps | Pipeline context | `$.steps.validate.success == true` |
| `field_mappings` in mapping steps | Pipeline context | `$.steps.transform.output` |
| `path` in JSONPath transformations | Input data | `$.metrics[*].value` |
| `condition` in filter transformations | Current element | `$.value > 0` |

### Root Object Definition

Expressions operate on a root object that varies by context:

```python
# Pipeline context (conditional, mapping)
root = {
    "input": <ModelComputeInput.data>,
    "steps": {
        "<step_name>": {
            "output": <step_output>,
            "success": <bool>,
            "metadata": <ModelComputeStepMetadata>
        }
    },
    "context": {
        "operation_id": <str>,
        "computation_type": <str>
    }
}

# Input data context (JSONPath, filter)
root = <input_data>  # Direct access to the data being transformed
```

### Path Expression Grammar (EBNF)

```ebnf
path        = "$" segment* ;
segment     = "." identifier | "[" index "]" | "[" "*" "]" ;
identifier  = letter (letter | digit | "_")* ;
index       = digit+ ;
letter      = "a".."z" | "A".."Z" ;
digit       = "0".."9" ;
```

**Examples**:
- `$.text` - Access `text` field
- `$.options.mode` - Nested field access
- `$.items[0]` - Array index access
- `$.items[*].value` - Array wildcard (all elements)

### Boolean Expression Grammar (EBNF)

```ebnf
expr        = or_expr ;
or_expr     = and_expr ( "||" and_expr )* ;
and_expr    = comp_expr ( "&&" comp_expr )* ;
comp_expr   = add_expr ( comp_op add_expr )? ;
add_expr    = mul_expr ( ("+" | "-") mul_expr )* ;
mul_expr    = unary_expr ( ("*" | "/" | "%") unary_expr )* ;
unary_expr  = ("!" | "-")? primary ;
primary     = path | literal | "(" expr ")" | func_call ;
literal     = string | number | "true" | "false" | "null" ;
func_call   = identifier "(" (expr ("," expr)*)? ")" ;
comp_op     = "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" ;
```

### Supported Functions

| Function | Description | Example |
|----------|-------------|---------|
| `len(x)` | Length of string/array | `len($.items) > 0` |
| `exists(path)` | Path exists and not null | `exists($.optional)` |
| `type(x)` | Type of value | `type($.value) == "string"` |
| `lower(s)` | Lowercase string | `lower($.text)` |
| `upper(s)` | Uppercase string | `upper($.text)` |

### Operator Precedence (Highest to Lowest)

1. `()` - Parentheses
2. `!`, `-` (unary) - Logical NOT, negation
3. `*`, `/`, `%` - Multiplication, division, modulo
4. `+`, `-` - Addition, subtraction
5. `<`, `<=`, `>`, `>=` - Comparison
6. `==`, `!=`, `in` - Equality, membership
7. `&&` - Logical AND
8. `||` - Logical OR

### Type Coercion Rules

| Operation | Rule |
|-----------|------|
| `string == number` | Error (no implicit coercion) |
| `null == anything` | Only `null == null` is true |
| `bool && non-bool` | Error |
| `number + string` | Error |

**Strict typing**: No implicit type coercion. Type mismatches cause expression evaluation failure.

### Error Handling

| Error Type | Behavior |
|------------|----------|
| Path not found | Returns `null` unless in `exists()` |
| Type mismatch | Expression fails, step fails |
| Division by zero | Expression fails, step fails |
| Function unknown | Contract validation failure |

### Determinism Guarantees

- No side effects
- No external state access
- No randomness
- No time-based behavior
- Same input always produces same output

---

## Mapping Expression Resolution

### Namespace Access

Mapping expressions access the pipeline context with specific rules:

```yaml
field_mappings:
  result: "$.steps.transform_case.output"
  original: "$.input.text"
  computed: "$.steps.compute_sum.output + $.steps.compute_count.output"
```

### Resolution Rules

1. **`$.input`**: Resolves to `ModelComputeInput.data`
2. **`$.steps.<name>`**: Resolves to the result of step `<name>`
3. **`$.context`**: Resolves to execution context fields

### Forward Reference Prohibition

```yaml
# INVALID - step_b hasn't executed yet
- step_name: step_a
  step_type: mapping
  field_mappings:
    value: "$.steps.step_b.output"  # ERROR: forward reference

- step_name: step_b
  step_type: transformation
```

**Rule**: Mapping expressions can only reference:
- `$.input` (always available)
- `$.steps.<name>` where `<name>` is a step that executed before the current step
- `$.context` (always available)

### Missing Path Behavior

| Scenario | Behavior |
|----------|----------|
| Path doesn't exist | **Fatal error** - step fails |
| Path exists but value is `null` | Returns `null` (valid) |
| Step referenced didn't execute (conditional) | **Fatal error** - step fails |

**Rationale**: Silent nulls cause downstream bugs. Fail fast.

### Evaluation Order

Mappings in `field_mappings` are evaluated in **declaration order**:

```yaml
field_mappings:
  a: "$.input.x"           # Evaluated first
  b: "$.steps.foo.output"  # Evaluated second
  c: "$.input.y"           # Evaluated third
```

---

## Error Propagation Model

### Error Classification

| Error Type | Severity | Behavior |
|------------|----------|----------|
| Contract validation error | Fatal | Node fails to start |
| Schema validation error | Fatal | Pipeline aborts immediately |
| Transformation error | Fatal | Pipeline aborts, step recorded as failed |
| Expression evaluation error | Fatal | Pipeline aborts, step recorded as failed |
| Timeout error | Fatal | Pipeline aborts, partial results discarded |
| Cache resolution error | Non-fatal | Warning in debug metadata, execution continues |

### Abort Semantics

When a fatal error occurs:
1. Current step is marked as failed with error details
2. Remaining steps are **not executed**
3. Pipeline result is marked as failed
4. All executed step results are preserved in `step_results`
5. Error is recorded in `ModelComputePipelineResult.errors`

### Error Structure

```python
class ModelComputeError(BaseModel):
    """Structured error for pipeline failures."""

    error_type: EnumComputeErrorType
    message: str
    step_name: str | None = None
    expression: str | None = None  # For expression errors
    path: str | None = None        # For path resolution errors
    stack_trace: str | None = None # Debug mode only

    model_config = ConfigDict(extra="forbid", frozen=True)


class EnumComputeErrorType(str, Enum):
    CONTRACT_VALIDATION = "contract_validation"
    SCHEMA_VALIDATION = "schema_validation"
    TRANSFORMATION = "transformation"
    EXPRESSION = "expression"
    TIMEOUT = "timeout"
    PARALLEL_FAILURE = "parallel_failure"
    FORWARD_REFERENCE = "forward_reference"
```

### Short-Circuit Behavior

```
Step 1: OK
Step 2: OK
Step 3: FAIL (transformation error)
Step 4: SKIPPED (not executed)
Step 5: SKIPPED (not executed)

Result: FAIL
Executed: [Step 1, Step 2, Step 3]
Errors: [Step 3 error]
```

---

## Parallel Step Error Semantics

### Failure Rules

When **any** substep in a parallel block fails:

1. **Entire parallel step fails** - No partial success
2. **Merge strategy is never applied** - No partial merge
3. **All substep errors are collected** - Combined in error list
4. **Remaining substeps may complete** - But results are discarded

### Error Aggregation

```python
class ModelParallelStepError(BaseModel):
    """Aggregated error for parallel step failures."""

    substep_errors: list[ModelComputeError]
    total_substeps: int
    failed_substeps: int
    completed_substeps: int

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### Example

```yaml
- step_name: parallel_compute
  step_type: parallel
  parallel_config:
    steps:
      - step_name: compute_a  # Succeeds
      - step_name: compute_b  # Fails
      - step_name: compute_c  # Succeeds
    merge_strategy: object
```

**Result**:
- `parallel_compute` step: FAILED
- `step_result.error`: Contains `compute_b` error details
- `step_result.output`: `null` (no merge applied)
- Pipeline: ABORTED (unless error handling specified)

### No Partial Results

**Rule**: Parallel steps are atomic. Either all substeps succeed and merge, or the entire parallel step fails with no output.

---

## Timeout Semantics

### Step-Level Timeout

```yaml
- step_name: transform
  step_type: transformation
  timeout_ms: 5000
```

**Behavior**:
- Timer starts when step execution begins
- If step exceeds `timeout_ms`, execution is **interrupted immediately**
- Step is marked as failed with `TIMEOUT` error
- No partial results are recorded

### Pipeline-Level Timeout

```yaml
performance:
  pipeline_timeout_ms: 30000
  timeout_ms: 5000  # Default per-step timeout
```

**Rules**:
- `pipeline_timeout_ms`: Maximum total execution time for all steps
- `timeout_ms`: Default timeout for steps without explicit timeout
- Step-level `timeout_ms` overrides the default

### Timeout Interaction

| Scenario | Behavior |
|----------|----------|
| Step timeout expires | Step fails, pipeline aborts |
| Pipeline timeout expires | Current step interrupted, pipeline aborts |
| Both specified | Whichever expires first triggers abort |

### Timeout Abort Behavior

1. Current step is immediately interrupted
2. Step is marked with `TIMEOUT` error
3. No partial step results are recorded
4. Pipeline result is marked as failed
5. All prior step results are preserved

---

## Step Execution Ordering

### Universal Ordering Rule

**All step types execute in declaration order**, with specific semantics per type:

| Step Type | Execution Semantics |
|-----------|---------------------|
| `validation` | Sequential, abort on failure |
| `transformation` | Sequential, abort on failure |
| `mapping` | Sequential, abort on failure |
| `conditional` | Sequential, evaluates condition then executes branch |
| `parallel` | Substeps concurrent, merge in declaration order |

### Conditional Step Ordering

```yaml
- step_name: check
  step_type: conditional
  conditional_config:
    condition: "$.input.mode == 'fast'"
    then_steps:
      - step_name: fast_a
      - step_name: fast_b
    else_steps:
      - step_name: slow_a
      - step_name: slow_b
```

**Execution**:
1. Evaluate `condition`
2. If true: Execute `then_steps` in declaration order (fast_a, then fast_b)
3. If false: Execute `else_steps` in declaration order (slow_a, then slow_b)
4. Branch steps are **not visible** to subsequent steps if condition was false

### Nested Pipeline Ordering

Nested steps (inside conditional or parallel) maintain their declaration order:

```yaml
- step_name: outer
  step_type: parallel
  parallel_config:
    steps:
      - step_name: inner_conditional
        step_type: conditional
        conditional_config:
          condition: "..."
          then_steps:
            - step_name: nested_a  # Executes first in then branch
            - step_name: nested_b  # Executes second in then branch
```

---

## Pipeline Context Immutability

### Immutability Guarantees

```python
# All step results are frozen after execution
class ModelComputeStepResult(BaseModel):
    step_name: str
    output: Any
    success: bool
    metadata: ModelComputeStepMetadata
    error: ModelComputeError | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)  # FROZEN


# Pipeline context stores results immutably
class ModelComputePipelineContext(BaseModel):
    input_data: Any  # Frozen reference
    step_results: MappingProxyType[str, ModelComputeStepResult]  # Immutable mapping
    current_step: str | None = None
    started_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

### Mutation Rules

| Rule | Enforcement |
|------|-------------|
| Step results are frozen after creation | `frozen=True` on model |
| Previous step outputs cannot be mutated | Immutable mapping type |
| Input data cannot be mutated | Frozen reference |
| Steps receive copies, not references | Deep copy on access |

### Implementation Requirement

```python
# After step execution:
result = ModelComputeStepResult(...)  # Frozen
context.step_results = MappingProxyType({
    **context.step_results,
    step.step_name: result
})
```

---

## Schema Version Compatibility

### Version Format

Schema identifiers: `{name}_v{major}` (e.g., `text_processor_input_v1`)

### Compatibility Model

**Strict version matching only**:
- `input_schema_ref: text_processor_input_v1` resolves to exactly `v1`
- No wildcards (`_v*`)
- No backward compatibility checks
- No automatic upgrades

### Version Mismatch Behavior

| Scenario | Behavior |
|----------|----------|
| Schema not found | Contract validation failure |
| Version mismatch | Contract validation failure |
| Schema updated after contract load | No effect (frozen at load time) |

### Schema Caching

- Schemas are resolved **once** at contract load time
- Resolved schemas are frozen into the contract
- Runtime does not re-fetch schemas
- Schema updates require contract reload

### Future Compatibility (Deferred)

The following are explicitly **out of scope** for v1.0:
- Version ranges (`_v1-v3`)
- Backward compatibility validation
- Automatic schema migration
- Schema inheritance

---

## Transformation Versioning

### Version Binding

Built-in transformations are versioned implicitly by **ONEX Core version**:

```python
# Transformation version is bound to core version
TRANSFORMATION_VERSION = "1.0.0"  # Matches omnibase_core version
```

### Replay Semantics

For deterministic replay:
1. Ledger entries record `transformation_version`
2. Replay uses the transformation implementation from that version
3. If version mismatch, replay fails with clear error

### Transformation Package Freezing

```python
class ModelComputeSubcontract(BaseModel):
    # ... other fields ...

    # Recorded at contract load time
    transformation_version: str = Field(default=TRANSFORMATION_VERSION)
```

### Upgrade Path

When transformation behavior changes:
1. Increment `TRANSFORMATION_VERSION`
2. Old contracts continue to work (version recorded)
3. New contracts get new version
4. Replay uses version from ledger entry

---

## Additional Config Models

### ModelTransformTypeConversionConfig

```python
class EnumTargetType(str, Enum):
    """Allowed target types for conversion."""
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "list"
    DICT = "dict"


class ModelTransformTypeConversionConfig(BaseModel):
    """
    Configuration for type conversion transformation.

    Converts input data to the specified target type.
    """

    config_type: Literal["type_conversion"] = "type_conversion"
    target_type: EnumTargetType
    strict: bool = True  # If False, allow lossy conversions

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Conversion Rules (strict=True)**:
- `str → int`: Must be valid integer string
- `str → float`: Must be valid float string
- `str → bool`: Only "true"/"false" (case-insensitive)
- `int → str`: Always succeeds
- `list → dict`: Error
- Invalid conversion: Error, step fails

### ModelTransformMapConfig

```python
class ModelTransformMapConfig(BaseModel):
    """
    Configuration for map transformation.

    Applies an expression to each element of a collection.
    """

    config_type: Literal["map"] = "map"
    expression: str  # ONEX Expression, `$` refers to current element
    preserve_nulls: bool = False  # If True, null results are kept

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Example**:
```yaml
- step_name: extract_values
  step_type: transformation
  transformation_type: map
  config:
    expression: "$.value * 2"
    preserve_nulls: false
```

### ModelTransformSortConfig

```python
class EnumSortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ModelTransformSortConfig(BaseModel):
    """
    Configuration for sort transformation.

    Sorts a collection by a key expression.
    """

    config_type: Literal["sort"] = "sort"
    key_expression: str | None = None  # If None, sort by value
    order: EnumSortOrder = EnumSortOrder.ASC
    stable: bool = True  # Guaranteed stable sort

    model_config = ConfigDict(extra="forbid", frozen=True)
```

**Stability Guarantee**: Sort is always stable (equal elements preserve original order) when `stable=True`.

---

## Cancellation Semantics

### Cancellation Model

NodeCompute supports cooperative cancellation for orchestrator integration:

```python
class ModelComputeCancellation(BaseModel):
    """Cancellation state for pipeline execution."""

    cancelled: bool = False
    reason: str | None = None
    requested_at: datetime | None = None
```

### Cancellation Behavior

| Phase | Behavior |
|-------|----------|
| Between steps | Check cancellation, abort if requested |
| During step | Step completes, then abort |
| During parallel | All substeps complete, then abort |

### Cancellation Rules

1. **Cooperative, not preemptive**: Steps are not interrupted mid-execution
2. **Check points**: Cancellation checked between steps only
3. **Clean abort**: Current step completes, no partial state
4. **Result surfacing**: `ModelComputePipelineResult.cancelled = True`

### Cancellation Result

```python
class ModelComputePipelineResult(BaseModel):
    success: bool
    cancelled: bool = False  # True if cancelled
    cancellation_reason: str | None = None
    # ... other fields
```

---

## Contract Lifecycle

### Seven Phases

```text
┌─────────────────────────────────────────────────────────────┐
│                    CONTRACT LIFECYCLE                        │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: LOAD                                               │
│  ├── Read YAML/JSON contract file                           │
│  └── Parse into raw Python dict                             │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: VALIDATE STRUCTURE                                 │
│  ├── Validate against ModelComputeSubcontract schema        │
│  ├── Check for unknown fields (extra="forbid")              │
│  └── Validate required fields present                       │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: RESOLVE SCHEMAS                                    │
│  ├── Resolve input_schema_ref from registry                 │
│  ├── Resolve output_schema_ref from registry                │
│  └── Fail if any schema not found                           │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: VALIDATE CONFIGS                                   │
│  ├── Parse each step config into typed model                │
│  ├── Validate transformation_type → config model match      │
│  └── Fail if any config invalid                             │
├─────────────────────────────────────────────────────────────┤
│  Phase 5: RESOLVE TRANSFORMATIONS                            │
│  ├── Verify all transformation_types exist in registry      │
│  ├── Bind transformation handlers                           │
│  └── Record transformation_version                          │
├─────────────────────────────────────────────────────────────┤
│  Phase 6: FREEZE CONTRACT                                    │
│  ├── Make contract immutable                                │
│  ├── Compute contract hash for ledger                       │
│  └── No further modifications allowed                       │
├─────────────────────────────────────────────────────────────┤
│  Phase 7: ATTACH TO NODE                                     │
│  ├── Assign frozen contract to NodeCompute instance         │
│  └── Node ready for execution                               │
└─────────────────────────────────────────────────────────────┘
```

### Phase Details

**Phase 1: Load**
- Input: File path or raw contract string
- Output: Raw Python dict
- Errors: File not found, YAML parse error

**Phase 2: Validate Structure**
- Input: Raw dict
- Output: Partially validated `ModelComputeSubcontract`
- Errors: Unknown fields, missing required fields, type errors

**Phase 3: Resolve Schemas**
- Input: Schema references
- Output: Resolved schema definitions frozen into contract
- Errors: Schema not found, version mismatch

**Phase 4: Validate Configs**
- Input: Step configs as dicts
- Output: Typed config models
- Errors: Config/transformation type mismatch, invalid config values

**Phase 5: Resolve Transformations**
- Input: Transformation types
- Output: Bound handlers + version
- Errors: Unknown transformation type

**Phase 6: Freeze Contract**
- Input: Validated contract
- Output: Immutable contract with hash
- Errors: None (validation complete)

**Phase 7: Attach to Node**
- Input: Frozen contract
- Output: Ready NodeCompute instance
- Errors: None (just assignment)

### Hot-Swap Rules

**Contract hot-swapping is NOT supported**:
- Once attached, contract cannot be changed
- New contract requires new NodeCompute instance
- In-flight executions use original contract

---

## Formal Contract Schema

The formal JSON Schema for `compute_operations` is defined in:

```
schemas/contracts/compute_contract_schema.yaml
```

This schema serves as:
1. **Agent generation target**: Agents can generate valid contracts
2. **Validation source**: Contract loader validates against this schema
3. **Documentation source**: Schema is authoritative for field definitions
4. **Backward compatibility baseline**: Changes must be backward compatible

### Schema Location

```yaml
# schemas/contracts/compute_contract_schema.yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "https://omninode.ai/schemas/compute_contract/v1"
title: "ONEX Compute Contract Schema"
type: object
required: [version, operation_name, pipeline]
# ... full schema definition
```

### Version History

| Schema Version | Core Version | Changes |
|----------------|--------------|---------|
| v1 | 0.4.0 | Initial release |

---

## Transformation Registry

### Runtime Extension Hook

`register_transformation` is a runtime extension hook used only by ONEX core at startup:

```python
def register_transformation(
    name: EnumTransformationType,
    handler: Callable[[Any, BaseModel], Any],
) -> None:
    """
    Register a transformation handler.

    NOTE: This is an internal runtime extension hook.
    - Application code and contracts cannot introduce new transformation types
    - All transformations allowed in NodeCompute must be in EnumTransformationType
    - Any runtime-specific registration must be part of the deployment descriptor
    """
```

**Rules**:
- Application code and contracts cannot introduce new transformation types
- All transformations allowed in NodeCompute must be represented in `EnumTransformationType`
- Any runtime-specific registration must be part of the deployment descriptor, not ad-hoc user code

---

## Component Design

### 1. ModelComputeSubcontract (~150 lines)

**Location**: `src/omnibase_core/models/contracts/subcontracts/model_compute_subcontract.py`

```python
class ModelComputeSubcontract(BaseModel):
    """
    Compute subcontract for pipeline-driven transformations.

    Defines transformation pipelines, caching, and performance settings.
    All computation logic is declarative - no custom Python required.
    """

    # Identity
    version: ModelSemVer
    operation_name: str
    operation_version: ModelSemVer
    description: str

    # Type safety - references only, not inline schemas
    input_schema_ref: str | None = None   # Reference to schema registry
    output_schema_ref: str | None = None  # Reference to schema registry

    # Pipeline definition
    pipeline: list[ModelComputePipelineStep]

    # Caching configuration
    caching: ModelComputeCaching | None = None

    # Performance configuration (no parallel_enabled - use pipeline steps)
    performance: ModelComputePerformance | None = None

    # Validation
    validation: ModelComputeValidation | None = None
```

### 2. MixinComputeExecution (~200 lines)

**Location**: `src/omnibase_core/mixins/mixin_compute_execution.py`

```python
class MixinComputeExecution:
    """
    Mixin providing compute pipeline execution from YAML contracts.

    Enables compute nodes to execute transformation pipelines declaratively.
    All public surfaces use typed models, not dict[str, Any].
    """

    async def execute_compute_pipeline(
        self,
        compute_contract: ModelComputeSubcontract,
        input_data: Any,
        context: ModelComputeExecutionContext,  # Typed, not dict
    ) -> ModelComputePipelineResult:
        """Execute transformation pipeline from YAML contract."""
        ...

    async def validate_compute_contract(
        self,
        compute_contract: ModelComputeSubcontract,
    ) -> list[str]:
        """Validate compute contract for correctness."""
        ...

    def get_pipeline_step_result(
        self,
        step_name: str,
    ) -> ModelComputeStepResult | None:
        """Get typed intermediate result from a pipeline step."""
        ...
```

### 3. Compute Executor Utilities (~300 lines)

**Location**: `src/omnibase_core/utils/compute_executor.py`

```python
# Pure functions for pipeline execution - all typed
async def execute_pipeline(
    compute_contract: ModelComputeSubcontract,
    input_data: Any,
    context: ModelComputeExecutionContext,  # Typed, not dict
) -> ModelComputePipelineResult:
    """Execute compute pipeline declaratively."""
    ...

async def validate_compute_contract(
    compute_contract: ModelComputeSubcontract,
) -> list[str]:
    """Validate compute contract structure."""
    ...

def get_transformation(
    transformation_type: EnumTransformationType,  # Enum, not str
) -> Callable[[Any, BaseModel], Any]:  # Typed config
    """Get transformation function from registry."""
    ...
```

### 4. Refactored NodeCompute (~50 lines)

**Location**: `src/omnibase_core/nodes/node_compute.py`

```python
class NodeCompute[T_Input, T_Output](NodeCoreBase, MixinComputeExecution):
    """
    Pipeline-driven compute node for transformations.

    Zero custom Python code required - all transformation logic
    defined declaratively in YAML contracts.
    All boundaries use typed models, not dict[str, Any].

    Pattern:
        class NodeMyCompute(NodeCompute):
            pass  # All logic from contract via mixin
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.compute_contract: ModelComputeSubcontract | None = None
        # Load from self.contract.compute_operations if available

    async def process(
        self,
        input_data: ModelComputeInput[T_Input],
    ) -> ModelComputeOutput[T_Output]:
        """Execute computation using pipeline from contract."""
        # Create typed context - not dict[str, Any]
        context = ModelComputeExecutionContext(
            operation_id=input_data.operation_id,
            computation_type=input_data.computation_type,
            correlation_id=input_data.correlation_id,
            tenant_id=input_data.tenant_id,
            node_id=self.node_id,
        )

        result = await self.execute_compute_pipeline(
            self.compute_contract,
            input_data.data,
            context=context,  # Typed context
        )

        return ModelComputeOutput(
            result=cast("T_Output", result.output),
            operation_id=input_data.operation_id,
            computation_type=input_data.computation_type,
            processing_time_ms=result.processing_time_ms,
            cache_hit=result.cache_hit,
            step_results=result.step_results,  # Typed step results
        )
```

---

## ModelComputeSubcontract Schema

### Full Schema Definition

```yaml
# Example: ModelComputeSubcontract schema
compute_operations:
  # Identity
  version: "1.0.0"
  operation_name: text_processor
  operation_version: "1.0.0"
  description: "Process and transform text data"

  # Type safety - references to schema registry (not inline)
  input_schema_ref: text_processor_input_v1
  output_schema_ref: text_processor_output_v1

  # Pipeline definition
  pipeline:
    - step_name: validate_input
      step_type: validation
      config:
        schema_ref: input_schema  # Resolves to input_schema_ref
        fail_on_error: true

    - step_name: normalize
      step_type: transformation
      transformation_type: normalize_unicode
      config:
        form: NFC

    - step_name: transform_case
      step_type: transformation
      transformation_type: case_conversion
      config:
        mode: uppercase

    - step_name: regex_replace
      step_type: transformation
      transformation_type: regex
      config:
        pattern: "\\s+"
        replacement: " "
        flags: []

    - step_name: output_mapping
      step_type: mapping
      field_mappings:
        result: "$.transform_case.output"
        original_length: "$.validate_input.length"

  # Caching configuration
  caching:
    enabled: true
    key_fields: [text, options.mode]
    ttl_seconds: 3600
    eviction_policy: LRU
    max_size: 1000

  # Performance configuration (parallelism is via pipeline step_type: parallel)
  performance:
    timeout_ms: 5000
    batch_size: 100
    max_retries: 2
    retry_delay_ms: 100

  # Validation configuration
  validation:
    strict_mode: true
    validate_input: true
    validate_output: true
    max_input_size_bytes: 1048576  # 1MB
```

### Pipeline Step Types

| Step Type | Purpose | Config Options |
|-----------|---------|----------------|
| `validation` | Validate data against schema | `schema_ref`, `fail_on_error` |
| `transformation` | Apply transformation | `transformation_type`, type-specific config |
| `mapping` | Map fields from step results | `field_mappings` (JSONPath expressions) |
| `conditional` | Conditional execution | `condition`, `then_steps`, `else_steps` |
| `parallel` | Parallel step execution | `steps`, `merge_strategy` |

### Transformation Types (Registry)

| Type | Description | Config Model |
|------|-------------|--------------|
| `regex` | Regex find/replace | `ModelTransformRegexConfig` |
| `case_conversion` | Case transformation | `ModelTransformCaseConfig` |
| `normalize_unicode` | Unicode normalization | `ModelTransformUnicodeConfig` |
| `trim` | Whitespace trimming | `ModelTransformTrimConfig` |
| `split` | Split string | `ModelTransformSplitConfig` |
| `join` | Join array | `ModelTransformJoinConfig` |
| `json_path` | Extract via JSONPath | `ModelTransformJsonPathConfig` |
| `template` | String template | `ModelTransformTemplateConfig` |
| `filter` | Collection filtering | `ModelTransformFilterConfig` |
| `map` | Collection mapping | `ModelTransformMapConfig` |
| `reduce` | Collection reduction | `ModelTransformReduceConfig` |
| `sort` | Collection sorting | `ModelTransformSortConfig` |
| `type_conversion` | Type conversion | `ModelTransformTypeConversionConfig` |
| `schema_validate` | Schema validation | `ModelTransformValidationConfig` |
| `identity` | Pass-through (no-op) | (no config required) |

**NOTE**: There is no `custom` type. NodeCompute is restricted to built-in transformations for determinism and replayability.

**Invariant**: Each `EnumTransformationType` value (except `IDENTITY`) MUST have exactly one corresponding config model included in `ModelTransformationConfig`. New transformations are added by:
1. Adding to `EnumTransformationType`
2. Creating a `ModelTransform*Config` with `config_type` literal
3. Adding that config model to `ModelTransformationConfig` union
4. Registering the handler in `TRANSFORMATION_REGISTRY`

---

## MixinComputeExecution Interface

### Public Interface (Typed)

```python
class MixinComputeExecution:
    """
    Mixin providing compute pipeline execution from YAML contracts.

    Usage:
        class NodeMyCompute(NodeCompute, MixinComputeExecution):
            pass  # All logic from contract

    Pattern:
        This mixin maintains minimal state (pipeline context).
        All transformation logic is delegated to pure functions
        in utils/compute_executor.py.

    Type Safety:
        All public methods use typed models, not dict[str, Any].
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pipeline_context: ModelComputePipelineContext | None = None

    async def execute_compute_pipeline(
        self,
        compute_contract: ModelComputeSubcontract,
        input_data: Any,
        context: ModelComputeExecutionContext,  # Typed, not dict
    ) -> ModelComputePipelineResult:
        """
        Execute transformation pipeline from YAML contract.

        Args:
            compute_contract: Compute subcontract from node contract
            input_data: Input data to transform
            context: Typed execution context (not dict[str, Any])

        Returns:
            ModelComputePipelineResult with output and typed step results
        """

    async def validate_compute_contract(
        self,
        compute_contract: ModelComputeSubcontract,
    ) -> list[str]:
        """
        Validate compute contract for correctness.

        Returns:
            List of validation errors (empty if valid)
        """

    def get_pipeline_step_result(
        self,
        step_name: str,
    ) -> ModelComputeStepResult | None:
        """
        Get typed result from a pipeline step.

        Returns:
            ModelComputeStepResult or None if step not found
        """

    # NOTE: No register_custom_transformation - NodeCompute uses built-in types only
```

### Result Types (Pydantic Models)

```python
class ModelComputePipelineResult(BaseModel):
    """Result of compute pipeline execution."""

    success: bool
    output: Any
    processing_time_ms: float
    cache_hit: bool
    steps_executed: list[str]
    step_results: dict[str, ModelComputeStepResult]  # Typed results
    errors: list[str] | None = None
    debug_metadata: dict[str, Any] = Field(default_factory=dict)  # Opaque only

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ModelComputePipelineContext(BaseModel):
    """Context maintained during pipeline execution."""

    input_data: Any
    step_results: dict[str, ModelComputeStepResult]  # Typed, not dict[str, Any]
    current_step: str | None = None
    started_at: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

---

## Compute Executor Utilities

### Pure Functions (Typed)

```python
# src/omnibase_core/utils/compute_executor.py

async def execute_pipeline(
    compute_contract: ModelComputeSubcontract,
    input_data: Any,
    context: ModelComputeExecutionContext,  # Typed, not dict
    cache: ModelComputeCache | None = None,
) -> ModelComputePipelineResult:
    """
    Execute compute pipeline declaratively from YAML contract.

    Pure function: (contract, data, typed_context) → typed_result

    Args:
        compute_contract: Compute subcontract definition
        input_data: Input data to transform
        context: Typed execution context (ModelComputeExecutionContext)
        cache: Optional typed cache instance

    Returns:
        ModelComputePipelineResult with transformed output and typed step results
    """

async def execute_step(
    step: ModelComputePipelineStep,
    input_data: Any,
    step_results: dict[str, ModelComputeStepResult],  # Typed results
    context: ModelComputeExecutionContext,
) -> ModelComputeStepResult:  # Typed return, not tuple
    """
    Execute a single pipeline step.

    Pure function: (step, data, typed_results, typed_context) → typed_result

    Returns:
        ModelComputeStepResult with output, metadata, and timing
    """

async def validate_compute_contract(
    compute_contract: ModelComputeSubcontract,
) -> list[str]:
    """
    Validate compute contract structure.

    Returns:
        List of validation errors (empty if valid)
    """

def get_transformation(
    transformation_type: EnumTransformationType,  # Enum, not str
) -> Callable[[Any, BaseModel], Any]:  # Typed config
    """
    Get transformation function from registry.

    Args:
        transformation_type: Enum value (not string)

    Returns:
        Pure transformation function: (data, typed_config) -> result

    Raises:
        ModelOnexError: If transformation type not found
    """

def register_transformation(
    name: EnumTransformationType,
    handler: Callable[[Any, BaseModel], Any],  # Typed config
) -> None:
    """
    Register a custom transformation handler.

    Args:
        name: Transformation type enum
        handler: Pure function (data, typed_config) → transformed_data
    """
```

---

## Transformation Registry

### Built-in Transformations (Typed)

```python
# Registry of built-in transformations with typed configs
# File: src/omnibase_core/utils/compute_transformations.py

TRANSFORMATION_REGISTRY: dict[EnumTransformationType, Callable[[Any, BaseModel], Any]] = {
    # String transformations - each takes typed config
    EnumTransformationType.REGEX: transform_regex,
    EnumTransformationType.CASE_CONVERSION: transform_case,
    EnumTransformationType.NORMALIZE_UNICODE: transform_unicode,
    EnumTransformationType.TRIM: transform_trim,
    EnumTransformationType.SPLIT: transform_split,
    EnumTransformationType.JOIN: transform_join,
    EnumTransformationType.TEMPLATE: transform_template,

    # Data transformations
    EnumTransformationType.JSON_PATH: transform_json_path,
    EnumTransformationType.TYPE_CONVERSION: transform_type,

    # Validation transformations
    EnumTransformationType.SCHEMA_VALIDATE: transform_schema_validate,

    # Collection transformations
    EnumTransformationType.FILTER: transform_filter,
    EnumTransformationType.MAP: transform_map,
    EnumTransformationType.REDUCE: transform_reduce,
    EnumTransformationType.SORT: transform_sort,

    # Identity
    EnumTransformationType.IDENTITY: lambda data, config: data,
}
```

### Transformation Function Signature (Typed Config)

```python
def transform_regex(data: str, config: ModelTransformRegexConfig) -> str:
    """
    Regex transformation with typed config.

    Args:
        data: Input string to transform
        config: Typed regex config (not dict[str, Any])

    Returns:
        Transformed string
    """
    import re

    # Type-safe access - no dict.get() needed
    pattern = config.pattern
    replacement = config.replacement
    flags_list = config.flags

    flags = 0
    if EnumRegexFlag.IGNORECASE in flags_list:
        flags |= re.IGNORECASE
    if EnumRegexFlag.MULTILINE in flags_list:
        flags |= re.MULTILINE
    if EnumRegexFlag.DOTALL in flags_list:
        flags |= re.DOTALL

    return re.sub(pattern, replacement, data, flags=flags)


def transform_case(data: str, config: ModelTransformCaseConfig) -> str:
    """Case transformation with typed config."""
    if config.mode == EnumCaseMode.UPPER:
        return data.upper()
    elif config.mode == EnumCaseMode.LOWER:
        return data.lower()
    elif config.mode == EnumCaseMode.TITLE:
        return data.title()
    raise ValueError(f"Unknown case mode: {config.mode}")
```

---

## Example Contracts

### Example 1: Text Processing Pipeline

```yaml
# examples/contracts/compute/text_processor.yaml
node_type: COMPUTE
node_name: text_processor
node_version: "1.0.0"

compute_operations:
  version: "1.0.0"
  operation_name: text_normalization
  operation_version: "1.0.0"
  description: "Normalize and clean text data"

  pipeline:
    - step_name: validate
      step_type: validation
      config:
        schema_ref: input_schema
        fail_on_error: true

    - step_name: normalize_unicode
      step_type: transformation
      transformation_type: normalize_unicode
      config:
        form: NFC

    - step_name: trim_whitespace
      step_type: transformation
      transformation_type: trim
      config:
        mode: both

    - step_name: collapse_spaces
      step_type: transformation
      transformation_type: regex
      config:
        pattern: "\\s+"
        replacement: " "

    - step_name: to_lowercase
      step_type: transformation
      transformation_type: case_conversion
      config:
        mode: lowercase

  caching:
    enabled: true
    key_fields: [text]
    ttl_seconds: 3600

  performance:
    timeout_ms: 1000
    max_input_size_bytes: 1048576
```

### Example 2: Data Transformation Pipeline

```yaml
# examples/contracts/compute/data_transformer.yaml
node_type: COMPUTE
node_name: data_transformer
node_version: "1.0.0"

compute_operations:
  version: "1.0.0"
  operation_name: metrics_transformation
  operation_version: "1.0.0"
  description: "Transform raw metrics into aggregated format"

  pipeline:
    - step_name: validate_input
      step_type: validation
      config:
        schema_ref: metrics_input_schema
        fail_on_error: true

    - step_name: extract_values
      step_type: transformation
      transformation_type: json_path
      config:
        path: "$.metrics[*].value"

    - step_name: filter_valid
      step_type: transformation
      transformation_type: filter
      config:
        condition: "value > 0"

    - step_name: compute_stats
      step_type: parallel
      steps:
        - step_name: compute_sum
          step_type: transformation
          transformation_type: reduce
          config:
            operation: sum

        - step_name: compute_count
          step_type: transformation
          transformation_type: reduce
          config:
            operation: count

        - step_name: compute_avg
          step_type: transformation
          transformation_type: reduce
          config:
            operation: average
      merge_strategy: object

    - step_name: output_mapping
      step_type: mapping
      field_mappings:
        total: "$.compute_sum.output"
        count: "$.compute_count.output"
        average: "$.compute_avg.output"
        timestamp: "$.validate_input.timestamp"

  caching:
    enabled: true
    key_fields: [metrics_source, time_range]
    ttl_seconds: 300

  performance:
    timeout_ms: 5000
    # NOTE: Parallelism is expressed via step_type: parallel in the pipeline above
```

### Example 3: Conditional Pipeline

> **NOTE**: This example uses `json_parse` and `csv_parse` transformation types which are **illustrative future types** not included in the initial `EnumTransformationType` set for v1.3.0. These demonstrate the conditional step pattern but would require adding these types to the enum and implementing their handlers before this contract would be valid.

```yaml
# examples/contracts/compute/conditional_processor.yaml
# NOTE: This is a HYPOTHETICAL example showing conditional branching.
# The json_parse and csv_parse types are not yet implemented.
node_type: COMPUTE
node_name: conditional_processor
node_version: "1.0.0"

compute_operations:
  version: "1.0.0"
  operation_name: format_converter
  operation_version: "1.0.0"
  description: "Convert data format based on input type"

  pipeline:
    - step_name: detect_format
      step_type: transformation
      transformation_type: json_path
      config:
        config_type: json_path
        path: "$.format"

    - step_name: process_by_format
      step_type: conditional
      condition: "$.detect_format.output == 'json'"
      then_steps:
        # HYPOTHETICAL: json_parse is not in v1.3.0 EnumTransformationType
        - step_name: parse_json
          step_type: transformation
          transformation_type: json_parse  # Future type
          config:
            config_type: json_parse

        - step_name: validate_json
          step_type: validation
          config:
            schema_ref: json_schema
      else_steps:
        # HYPOTHETICAL: csv_parse is not in v1.3.0 EnumTransformationType
        - step_name: parse_csv
          step_type: transformation
          transformation_type: csv_parse  # Future type
          config:
            config_type: csv_parse
            delimiter: ","
            has_header: true

    - step_name: normalize_output
      step_type: mapping
      field_mappings:
        data: "$.process_by_format.output"
        format: "$.detect_format.output"
```

---

## Migration Path

### Current NodeCompute (Code-Driven)

```python
# Current implementation has ~450 lines of code
class NodeCompute(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.computation_cache = ModelComputeCache(...)
        self.computation_registry: dict[str, Callable[..., Any]] = {}
        self._register_builtin_computations()

    async def process(self, input_data):
        # Custom computation logic
        cache_key = self._generate_cache_key(input_data)
        if cache_hit := self.computation_cache.get(cache_key):
            return cache_hit

        result = await self._execute_computation(input_data)
        self.computation_cache.put(cache_key, result)
        return result

    def register_computation(self, name, func):
        self.computation_registry[name] = func

    def _register_builtin_computations(self):
        # Hard-coded built-in computations
        self.register_computation("default", default_transform)
        self.register_computation("string_uppercase", string_uppercase)
        self.register_computation("sum_numbers", sum_numbers)
```

### New NodeCompute (Contract-Driven, Typed)

```python
# New implementation: ~50 lines
# File: src/omnibase_core/nodes/node_compute.py

class NodeCompute[T_Input, T_Output](NodeCoreBase, MixinComputeExecution):
    """
    Pipeline-driven compute node.
    Zero custom Python code - driven by compute subcontract.
    All boundaries use typed models, not dict[str, Any].
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.compute_contract: ModelComputeSubcontract | None = None

        # Load from contract if available
        if hasattr(self, "contract") and hasattr(self.contract, "compute_operations"):
            self.compute_contract = self.contract.compute_operations

    async def process(
        self,
        input_data: ModelComputeInput[T_Input],
    ) -> ModelComputeOutput[T_Output]:
        if not self.compute_contract:
            raise ModelOnexError(
                message="Compute contract not loaded",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Create typed context - not dict[str, Any]
        context = ModelComputeExecutionContext(
            operation_id=input_data.operation_id,
            computation_type=input_data.computation_type,
            correlation_id=input_data.correlation_id,
        )

        result = await self.execute_compute_pipeline(
            self.compute_contract,
            input_data.data,
            context=context,  # Typed context
        )

        return ModelComputeOutput(
            result=cast("T_Output", result.output),
            operation_id=input_data.operation_id,
            computation_type=input_data.computation_type,
            processing_time_ms=result.processing_time_ms,
            cache_hit=result.cache_hit,
            parallel_execution_used=False,
            step_results=result.step_results,  # Typed step results
        )
```

### Migration Steps

1. **Move current NodeCompute to legacy** ✅ (Done in OMN-159)
2. **Create ModelComputeSubcontract** - Define Pydantic model
3. **Create MixinComputeExecution** - Implement mixin
4. **Create compute_executor.py** - Pure execution functions
5. **Refactor NodeCompute** - Use mixin pattern
6. **Add transformation registry** - Built-in + extensible
7. **Create example contracts** - Demonstrate patterns
8. **Update tests** - Contract-based test cases

---

## Implementation Plan

### File Structure (One Model Per File)

```text
src/omnibase_core/
├── enums/
│   ├── enum_compute_step_type.py           # EnumComputeStepType
│   ├── enum_transformation_type.py         # EnumTransformationType
│   ├── enum_parallel_merge_strategy.py     # EnumParallelMergeStrategy
│   ├── enum_case_mode.py                   # EnumCaseMode
│   ├── enum_regex_flag.py                  # EnumRegexFlag
│   ├── enum_unicode_form.py                # EnumUnicodeForm
│   ├── enum_trim_mode.py                   # EnumTrimMode
│   ├── enum_target_type.py                 # EnumTargetType (for type conversion)
│   ├── enum_sort_order.py                  # EnumSortOrder
│   └── enum_compute_error_type.py          # EnumComputeErrorType
│
├── models/
│   ├── compute/
│   │   ├── model_compute_execution_context.py    # ModelComputeExecutionContext (frozen)
│   │   ├── model_compute_step_metadata.py        # ModelComputeStepMetadata (frozen)
│   │   ├── model_compute_step_result.py          # ModelComputeStepResult (frozen)
│   │   ├── model_compute_pipeline_result.py      # ModelComputePipelineResult
│   │   ├── model_compute_pipeline_context.py     # ModelComputePipelineContext
│   │   ├── model_compute_error.py                # ModelComputeError (frozen)
│   │   ├── model_parallel_step_error.py          # ModelParallelStepError (frozen)
│   │   ├── model_compute_cancellation.py         # ModelComputeCancellation
│   │   └── model_compute_debug_metadata.py       # ModelComputeDebugMetadata (opaque)
│   │
│   ├── contracts/
│   │   └── subcontracts/
│   │       ├── model_compute_subcontract.py      # ModelComputeSubcontract (extra=forbid)
│   │       ├── model_compute_pipeline_step.py    # ModelComputePipelineStep (extra=forbid)
│   │       ├── model_compute_caching.py          # ModelComputeCaching (extra=forbid)
│   │       ├── model_compute_performance.py      # ModelComputePerformance (extra=forbid)
│   │       └── model_compute_validation.py       # ModelComputeValidation (extra=forbid)
│   │
│   └── transformations/
│       ├── model_transform_regex_config.py       # ModelTransformRegexConfig (extra=forbid, frozen)
│       ├── model_transform_case_config.py        # ModelTransformCaseConfig (extra=forbid, frozen)
│       ├── model_transform_unicode_config.py     # ModelTransformUnicodeConfig (extra=forbid, frozen)
│       ├── model_transform_trim_config.py        # ModelTransformTrimConfig (extra=forbid, frozen)
│       ├── model_transform_split_config.py       # ModelTransformSplitConfig (extra=forbid, frozen)
│       ├── model_transform_join_config.py        # ModelTransformJoinConfig (extra=forbid, frozen)
│       ├── model_transform_json_path_config.py   # ModelTransformJsonPathConfig (extra=forbid, frozen)
│       ├── model_transform_template_config.py    # ModelTransformTemplateConfig (extra=forbid, frozen)
│       ├── model_transform_filter_config.py      # ModelTransformFilterConfig (extra=forbid, frozen)
│       ├── model_transform_reduce_config.py      # ModelTransformReduceConfig (extra=forbid, frozen)
│       ├── model_transform_validation_config.py  # ModelTransformValidationConfig (extra=forbid, frozen)
│       ├── model_mapping_config.py               # ModelMappingConfig (extra=forbid, frozen)
│       ├── model_conditional_config.py           # ModelConditionalConfig (extra=forbid, frozen)
│       ├── model_parallel_config.py              # ModelParallelConfig (extra=forbid, frozen)
│       └── types.py                              # ModelTransformationConfig (Union)
│
├── mixins/
│   └── mixin_compute_execution.py                # MixinComputeExecution
│
├── utils/
│   ├── compute_executor.py                       # Pure execution functions
│   └── compute_transformations.py                # Transformation registry + handlers
│
└── nodes/
    └── node_compute.py                           # NodeCompute (refactored)
```

### Phase 1: Enums & Core Models (~3 days)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| EnumComputeStepType | `enums/enum_compute_step_type.py` | ~20 | P0 |
| EnumTransformationType | `enums/enum_transformation_type.py` | ~30 | P0 |
| EnumParallelMergeStrategy | `enums/enum_parallel_merge_strategy.py` | ~15 | P0 |
| EnumCaseMode | `enums/enum_case_mode.py` | ~15 | P0 |
| EnumRegexFlag | `enums/enum_regex_flag.py` | ~15 | P0 |
| EnumUnicodeForm | `enums/enum_unicode_form.py` | ~15 | P0 |
| EnumTrimMode | `enums/enum_trim_mode.py` | ~15 | P0 |
| ModelComputeExecutionContext | `models/compute/model_compute_execution_context.py` | ~40 | P0 |
| ModelComputeStepMetadata | `models/compute/model_compute_step_metadata.py` | ~30 | P0 |
| ModelComputeStepResult | `models/compute/model_compute_step_result.py` | ~30 | P0 |
| ModelComputeDebugMetadata | `models/compute/model_compute_debug_metadata.py` | ~25 | P1 |

### Phase 2: Transformation Config Models (~2 days)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| ModelTransformRegexConfig | `models/transformations/model_transform_regex_config.py` | ~25 | P0 |
| ModelTransformCaseConfig | `models/transformations/model_transform_case_config.py` | ~20 | P0 |
| ModelTransformUnicodeConfig | `models/transformations/model_transform_unicode_config.py` | ~20 | P0 |
| ModelTransformTrimConfig | `models/transformations/model_transform_trim_config.py` | ~20 | P0 |
| ModelTransformSplitConfig | `models/transformations/model_transform_split_config.py` | ~20 | P0 |
| ModelTransformJoinConfig | `models/transformations/model_transform_join_config.py` | ~20 | P0 |
| ModelTransformJsonPathConfig | `models/transformations/model_transform_json_path_config.py` | ~20 | P0 |
| ModelTransformTemplateConfig | `models/transformations/model_transform_template_config.py` | ~25 | P1 |
| ModelTransformFilterConfig | `models/transformations/model_transform_filter_config.py` | ~20 | P1 |
| ModelTransformReduceConfig | `models/transformations/model_transform_reduce_config.py` | ~20 | P1 |
| ModelTransformationConfig (Union) | `models/transformations/types.py` | ~30 | P0 |

### Phase 3: Step Config Models (~2 days)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| ModelMappingConfig | `models/transformations/model_mapping_config.py` | ~25 | P0 |
| ModelConditionalConfig | `models/transformations/model_conditional_config.py` | ~35 | P0 |
| ModelParallelConfig | `models/transformations/model_parallel_config.py` | ~35 | P0 |

### Phase 4: Contract Subcontracts (~2 days)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| ModelComputeSubcontract | `models/contracts/subcontracts/model_compute_subcontract.py` | ~80 | P0 |
| ModelComputePipelineStep | `models/contracts/subcontracts/model_compute_pipeline_step.py` | ~60 | P0 |
| ModelComputeCaching | `models/contracts/subcontracts/model_compute_caching.py` | ~40 | P0 |
| ModelComputePerformance | `models/contracts/subcontracts/model_compute_performance.py` | ~40 | P0 |
| ModelComputeValidation | `models/contracts/subcontracts/model_compute_validation.py` | ~30 | P1 |

### Phase 5: Execution Infrastructure (~3 days)

| Task | File | Lines | Priority |
|------|------|-------|----------|
| compute_executor.py | `utils/compute_executor.py` | ~350 | P0 |
| compute_transformations.py | `utils/compute_transformations.py` | ~300 | P0 |
| MixinComputeExecution | `mixins/mixin_compute_execution.py` | ~250 | P0 |
| Refactor NodeCompute | `nodes/node_compute.py` | ~60 | P0 |

### Phase 6: Testing & Documentation (~3 days)

| Task | File | Priority |
|------|------|----------|
| Unit tests for compute_executor | `tests/unit/utils/test_compute_executor.py` | P0 |
| Unit tests for models | `tests/unit/models/compute/test_*.py` | P0 |
| Unit tests for transformations | `tests/unit/models/transformations/test_*.py` | P0 |
| Unit tests for step configs | `tests/unit/models/transformations/test_*_config.py` | P0 |
| Integration tests | `tests/integration/test_compute_pipeline.py` | P1 |
| Example contracts | `examples/contracts/compute/*.yaml` | P1 |

### Total Estimated Effort

- **New Files**: ~38 files (one model per file)
- **New Code**: ~1,600 lines
- **Refactored Code**: ~400 lines removed
- **Tests**: ~1,000 lines
- **Documentation**: ~200 lines
- **Timeline**: 15 working days (realistic estimate accounting for type plumbing, validation, and iteration)

---

## Acceptance Criteria

### Type Safety Requirements

- [ ] **Zero `dict[str, Any]` at semantic boundaries** - All public APIs use typed models
- [ ] `ModelComputeExecutionContext` replaces context dict in all signatures
- [ ] `ModelComputeStepResult` replaces tuple/dict returns from step execution
- [ ] Per-transformation typed config models (not `config: dict[str, Any]`)
- [ ] `ModelTransformationConfig` discriminated union for all config types
- [ ] `ModelComputeDebugMetadata` is the ONLY place for opaque dict (documented as non-semantic)
- [ ] Type checking passes (mypy --strict) with zero errors

### Model Structure Requirements

- [ ] **One model per file** - No multi-model files
- [ ] All Pydantic models use `Model` prefix (e.g., `ModelComputeStepResult`)
- [ ] All dataclasses use `DataClass` prefix if applicable
- [ ] All enums use `Enum` prefix (e.g., `EnumComputeStepType`)
- [ ] Union types in dedicated `types.py` file per module

### Functional Requirements

- [ ] `ModelComputeSubcontract` Pydantic model defined with full validation
- [ ] `MixinComputeExecution` mixin implemented with typed pipeline execution
- [ ] `NodeCompute` refactored to use mixin (zero custom logic in node class)
- [ ] Pipeline steps execute from contract definition
- [ ] Transformation registry: typed signature `Callable[[Any, BaseModel], Any]`
- [ ] Transformation registry supports: regex, case, mapping, validation, json_path
- [ ] Caching honors contract configuration
- [ ] Performance settings (timeout, parallel) respected

### Testing & Documentation

- [ ] Unit tests with 90%+ coverage
- [ ] Integration tests with contract-only node definitions
- [ ] Example contracts in `examples/contracts/compute/`
- [ ] All existing tests pass

---

## Dependencies

- **Blocked by**: None (OMN-159 already completed)
- **Blocks**: OMN-467 (Runtime Orchestrator Contract)

## References

- [OMN-465 Linear Issue](https://linear.app/omninode/issue/OMN-465)
- [NodeReducer Implementation](../src/omnibase_core/nodes/node_reducer.py)
- [NodeOrchestrator Implementation](../src/omnibase_core/nodes/node_orchestrator.py)
- [FSM Executor](../src/omnibase_core/utils/fsm_executor.py)
- [Workflow Executor](../src/omnibase_core/utils/workflow_executor.py)
- [DECLARATIVE_IMPLEMENTATION_PLAN.md](./DECLARATIVE_IMPLEMENTATION_PLAN.md)
- [SUBCONTRACT_ARCHITECTURE.md](./SUBCONTRACT_ARCHITECTURE.md)

---

**Last Updated**: 2025-12-07
**Version**: 1.3.1 (alignment of config union, table, and examples)
**Status**: DRAFT - Ready for Implementation
**Next Steps**: Begin Phase 1 implementation

### Changelog

- **v1.3.1** (2025-12-07): No behavioral changes; alignment of config union, transformation table, and examples with previously stated invariants
  - **Fixed `ModelTransformationConfig` union**: Added missing `ModelTransformTypeConversionConfig`, `ModelTransformMapConfig`, `ModelTransformSortConfig`
  - **Added `config_type` discriminator fields**: All config models now have `config_type: Literal["..."]` for proper discriminated union support
  - **Updated transformation types table**: All types now reference their correct config models (map, sort, type_conversion no longer show "(inline)")
  - **Marked hypothetical types**: Example 3 now explicitly notes that `json_parse` and `csv_parse` are future types not in v1.3.x
  - **Added error models to file structure**: `EnumComputeErrorType`, `ModelComputeError`, `ModelParallelStepError`, `ModelComputeCancellation` now in implementation plan
  - **Added immutability cross-reference**: Early `ModelComputeStepResult` definition references canonical "Pipeline Context Immutability" section
  - **Added expression language canonical source note**: Explicit subordination to `EXPRESSION_LANGUAGE_SPEC.md`
  - **Added missing enums to file structure**: `EnumTargetType`, `EnumSortOrder`
- **v1.3.0** (2025-12-07): Implementation-ready with all invariants explicit
  - **Consolidated execution guarantees**: Merged determinism, config resolution, caching, parallel semantics into single "Execution Guarantees" section
  - **Added schema resolution algorithm**: Explicit rules for resolving `input_schema`, `output_schema`, and global references
  - **Added unknown field handling**: `extra = "forbid"` on all contract-side models
  - **Defined missing config models**: `ModelMappingConfig`, `ModelConditionalConfig`, `ModelParallelConfig` with full definitions
  - **Added `EnumParallelMergeStrategy`**: Deterministic merge strategies for parallel steps
  - **Added immutability rules**: Context and step-level models are frozen by default
  - **Specified parallel step ordering**: Declaration order is canonical for deterministic merge
  - **Added expression language reference**: All expressions use ONEX Expression Language (EXPRESSION_LANGUAGE_SPEC.md)
  - **Clarified `register_transformation`**: Internal runtime extension hook, not for user-land code
  - **Added Phase 3**: Step config models as separate phase
  - **Adjusted timeline**: 15 working days (realistic estimate)
  - **Hard fail on config mismatch**: Explicit rule that contract validation fails if `transformation_type` doesn't map to known config
- **v1.2.0** (2025-12-07): Consolidated and clarified invariants
  - Removed duplicate sections: Component Design now shows typed signatures consistently
  - Added Determinism and Replay Guarantees section
  - Added YAML Config to Typed Model Resolution section
  - Added Caching Key Resolution section
  - Removed CUSTOM transformation type
  - Removed `parallel_enabled` from performance
  - Changed to schema references
  - Removed `register_custom_transformation`
- **v1.1.0** (2025-12-07): Added typed model boundaries
  - Replaced all `dict[str, Any]` at semantic boundaries with typed Pydantic models
  - Added per-transformation typed config models
  - Updated file structure to show one model per file
- **v1.0.0** (2025-12-06): Initial design document
