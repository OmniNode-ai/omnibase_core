# Contract-Driven NodeCompute v1.0 Specification

> **Version**: 1.0.0
> **Date**: 2025-12-07
> **Status**: DRAFT - Ready for Implementation
> **Ticket**: [OMN-465](https://linear.app/omninode/issue/OMN-465)
> **Full Roadmap**: [NODECOMPUTE_VERSIONING_ROADMAP.md](./NODECOMPUTE_VERSIONING_ROADMAP.md)

---

## Executive Summary

This document defines the **minimal v1.0 implementation** of contract-driven `NodeCompute`. The goal is a boring, stable foundation that can be shipped safely and extended incrementally.

**v1.0 Scope**: Sequential-only pipelines with 6 built-in transformation types, simple mapping, and abort-on-first-failure semantics. No caching, no parallelism, no conditionals.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [v1.0 Scope](#v10-scope)
3. [Core Models](#core-models)
4. [Enums](#enums)
5. [Transformation Config Models](#transformation-config-models)
6. [Execution Model](#execution-model)
7. [Immutability Guarantees](#immutability-guarantees-v10)
8. [Error Model](#error-model-v10)
9. [NodeCompute Behavior](#v10-nodecompute-behavior)
10. [Schema Resolution](#schema-resolution)
11. [Example Contract](#example-contract)
12. [Implementation Plan](#implementation-plan)
13. [Acceptance Criteria](#acceptance-criteria)

---

## Design Principles

These principles apply to v1.0 and all future versions:

1. **Zero Custom Code**: Developers inherit from `NodeCompute` without writing transformation logic
2. **Pipeline-Driven**: Computations are sequences of named steps
3. **Transformation Registry**: Built-in transformations only (no custom registration)
4. **Pure Functions**: All execution logic in utility module for testability
5. **Typed Boundaries**: All public surfaces use Pydantic models
6. **Deterministic**: Same input always produces same output

---

## v1.0 Scope

### What's IN v1.0

| Feature | Description |
|---------|-------------|
| **Sequential Pipelines** | Steps execute in declaration order |
| **3 Step Types** | `VALIDATION`, `TRANSFORMATION`, `MAPPING` |
| **6 Transformation Types** | `IDENTITY`, `REGEX`, `CASE_CONVERSION`, `TRIM`, `NORMALIZE_UNICODE`, `JSON_PATH` |
| **Simple Mapping** | JSONPath-like selectors: `$.input`, `$.steps.<name>.output` |
| **Abort on First Failure** | Pipeline stops at first error |
| **Schema References** | `input_schema_ref` / `output_schema_ref` resolved at load time |
| **Pipeline Timeout** | Single `pipeline_timeout_ms` setting |

### What's NOT in v1.0

| Feature | Deferred To | Rationale |
|---------|-------------|-----------|
| **Caching** | v1.1 | Adds cache invalidation complexity |
| **Cancellation** | v1.1 | Requires cooperative cancellation infrastructure |
| **Parallel Steps** | v1.2 | Merge semantics need careful design |
| **Conditional Steps** | v1.2 | Expression language needs full spec |
| **Full Expression Language** | v1.2 | Only simple path expressions in v1.0 |
| **Transformation Versioning** | v1.2 | Not needed until transformations evolve |
| **SPLIT/JOIN/FILTER/MAP/REDUCE/SORT/TEMPLATE/TYPE_CONVERSION/SCHEMA_VALIDATE** | v1.1+ | Start with minimal set; `SCHEMA_VALIDATE` transform duplicates `VALIDATION` step type |
| **Detailed Error Enums** | v1.1 | Simple string `error_type` sufficient for v1.0 |

See [NODECOMPUTE_VERSIONING_ROADMAP.md](./NODECOMPUTE_VERSIONING_ROADMAP.md) for full roadmap.

---

## Core Models

### ModelComputeSubcontract

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class ModelComputeSubcontract(BaseModel):
    """
    v1.0 Compute subcontract for sequential pipeline transformations.

    Defines transformation pipelines with abort-on-first-failure semantics.
    """

    # Identity
    version: str = "1.0.0"
    operation_name: str
    operation_version: str
    description: str = ""

    # Schema references (resolved at load time)
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None

    # Pipeline definition
    pipeline: list["ModelComputePipelineStep"]

    # v1.0 Performance (minimal)
    pipeline_timeout_ms: int | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelComputePipelineStep

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal, Annotated

class ModelComputePipelineStep(BaseModel):
    """
    A single step in the compute pipeline.

    v1.0 supports: VALIDATION, TRANSFORMATION, MAPPING

    NOTE: No per-step timeout in v1.0. Use pipeline_timeout_ms on contract.
    """

    step_name: str
    step_type: "EnumComputeStepType"

    # For transformation steps
    transformation_type: "EnumTransformationType | None" = None
    transformation_config: "ModelTransformationConfig | None" = None

    # For mapping steps
    mapping_config: "ModelMappingConfig | None" = None

    # For validation steps
    validation_config: "ModelValidationStepConfig | None" = None

    # Common options
    enabled: bool = True
    # v1.0: No per-step timeout - only pipeline-level timeout_ms on contract

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_step_config(self) -> "ModelComputePipelineStep":
        """Ensure correct config is provided for step type."""
        if self.step_type == EnumComputeStepType.TRANSFORMATION:
            if self.transformation_type is None:
                raise ValueError("transformation_type required for transformation steps")
            if self.transformation_config is None and self.transformation_type != EnumTransformationType.IDENTITY:
                raise ValueError("transformation_config required for non-identity transformations")
        if self.step_type == EnumComputeStepType.MAPPING:
            if self.mapping_config is None:
                raise ValueError("mapping_config required for mapping steps")
        if self.step_type == EnumComputeStepType.VALIDATION:
            if self.validation_config is None:
                raise ValueError("validation_config required for validation steps")
        return self
```

### ModelComputeExecutionContext

```python
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID

class ModelComputeExecutionContext(BaseModel):
    """
    Typed execution context for compute pipelines.

    v1.0: Minimal context for deterministic execution.
    """

    operation_id: UUID
    correlation_id: UUID | None = None
    node_id: str | None = None

    model_config = ConfigDict(frozen=True)
```

### ModelComputeStepMetadata

```python
from pydantic import BaseModel, ConfigDict, Field

class ModelComputeStepMetadata(BaseModel):
    """Metadata for a single pipeline step execution."""

    duration_ms: float
    transformation_type: str | None = None

    model_config = ConfigDict(frozen=True)
```

### ModelComputeStepResult

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Any

class ModelComputeStepResult(BaseModel):
    """Result of a single pipeline step."""

    step_name: str
    output: Any
    success: bool = True
    metadata: "ModelComputeStepMetadata"
    error_type: str | None = None  # v1.0: Simple string, not enum
    error_message: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelComputePipelineResult

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Any

class ModelComputePipelineResult(BaseModel):
    """Result of compute pipeline execution."""

    success: bool
    output: Any
    processing_time_ms: float
    steps_executed: list[str]
    step_results: dict[str, "ModelComputeStepResult"]
    error_type: str | None = None  # v1.0: Simple string
    error_message: str | None = None
    error_step: str | None = None

    model_config = ConfigDict(frozen=True)
```

### ModelMappingConfig

```python
from pydantic import BaseModel, ConfigDict, Field

class ModelMappingConfig(BaseModel):
    """
    v1.0 Mapping configuration.

    field_mappings uses simple path expressions:
    - $.input - Access input data
    - $.steps.<name>.output - Access step output
    """

    config_type: Literal["mapping"] = "mapping"
    field_mappings: dict[str, str]

    model_config = ConfigDict(extra="forbid", frozen=True)
```

---

## Enums

### EnumComputeStepType

```python
from enum import Enum

class EnumComputeStepType(str, Enum):
    """
    v1.0 Pipeline step types.

    Only 3 types for v1.0 - CONDITIONAL and PARALLEL deferred.
    """

    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    MAPPING = "mapping"
    # v1.2+: CONDITIONAL = "conditional"
    # v1.2+: PARALLEL = "parallel"
```

### EnumTransformationType

```python
from enum import Enum

class EnumTransformationType(str, Enum):
    """
    v1.0 Transformation types.

    Only 6 types for v1.0 - collection operations and SCHEMA_VALIDATE deferred.

    NOTE: Schema validation is handled by VALIDATION step type, not as a transformation.
    This keeps step types semantically clean:
    - VALIDATION → schema checks
    - TRANSFORMATION → pure data transforms
    - MAPPING → shape results
    """

    # v1.0 Types (6 transformations)
    IDENTITY = "identity"
    REGEX = "regex"
    CASE_CONVERSION = "case_conversion"
    TRIM = "trim"
    NORMALIZE_UNICODE = "normalize_unicode"
    JSON_PATH = "json_path"

    # v1.1+: SPLIT, JOIN, TEMPLATE, TYPE_CONVERSION, SCHEMA_VALIDATE
    # v1.2+: FILTER, MAP, REDUCE, SORT
```

### Supporting Enums

```python
from enum import Enum

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
```

---

## Transformation Config Models

All config models have:
- `config_type` literal field for discriminated union
- `model_config = ConfigDict(extra="forbid", frozen=True)`

### ModelTransformRegexConfig

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class ModelTransformRegexConfig(BaseModel):
    """Configuration for regex transformation."""

    config_type: Literal["regex"] = "regex"
    pattern: str
    replacement: str = ""
    flags: list[EnumRegexFlag] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelTransformCaseConfig

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ModelTransformCaseConfig(BaseModel):
    """Configuration for case transformation."""

    config_type: Literal["case_conversion"] = "case_conversion"
    mode: EnumCaseMode

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelTransformTrimConfig

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ModelTransformTrimConfig(BaseModel):
    """Configuration for whitespace trimming."""

    config_type: Literal["trim"] = "trim"
    mode: EnumTrimMode = EnumTrimMode.BOTH

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelTransformUnicodeConfig

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ModelTransformUnicodeConfig(BaseModel):
    """Configuration for unicode normalization."""

    config_type: Literal["normalize_unicode"] = "normalize_unicode"
    form: EnumUnicodeForm = EnumUnicodeForm.NFC

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelTransformJsonPathConfig

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ModelTransformJsonPathConfig(BaseModel):
    """Configuration for JSONPath extraction."""

    config_type: Literal["json_path"] = "json_path"
    path: str

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelValidationStepConfig

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class ModelValidationStepConfig(BaseModel):
    """
    Configuration for VALIDATION step type.

    NOTE: This is NOT a transformation config. It configures the VALIDATION step type.
    Schema validation is semantically distinct from data transformation.
    """

    config_type: Literal["validation"] = "validation"
    schema_ref: str
    fail_on_error: bool = True

    model_config = ConfigDict(extra="forbid", frozen=True)
```

### ModelTransformationConfig (Union)

```python
from typing import Annotated, Union
from pydantic import Field

# v1.0 Discriminated union - only 5 types (IDENTITY has no config)
ModelTransformationConfig = Annotated[
    Union[
        ModelTransformRegexConfig,
        ModelTransformCaseConfig,
        ModelTransformTrimConfig,
        ModelTransformUnicodeConfig,
        ModelTransformJsonPathConfig,
        # IDENTITY has no config - handled separately
        # VALIDATION uses ModelValidationStepConfig on step, not here
    ],
    Field(discriminator="config_type"),
]
```

---

## Execution Model

### Sequential Execution

v1.0 uses **strictly sequential execution**:

```text
Step 1 → Step 2 → Step 3 → ... → Step N → Output
    ↓        ↓        ↓
  Result   Result   Result
```

**Rules**:
1. Steps execute in declaration order
2. Each step receives output from previous step (or input for first step)
3. Step results accumulate in `step_results` dict
4. Mapping steps can reference any prior step result

### Abort on First Failure

When any step fails:
1. Current step is marked as failed
2. **No subsequent steps execute**
3. Pipeline result is marked as failed
4. All executed step results are preserved
5. Error details recorded in `error_type`, `error_message`, `error_step`

```text
Step 1: OK      → Result preserved
Step 2: FAIL    → Error recorded, pipeline aborts
Step 3: SKIPPED → Not executed
Step 4: SKIPPED → Not executed

Result: FAIL
```

### Transformation Execution

```python
async def execute_transformation(
    data: Any,
    transformation_type: EnumTransformationType,
    config: ModelTransformationConfig | None,
) -> Any:
    """
    Execute a single transformation.

    Pure function: (data, type, config) → result

    Raises:
        ModelOnexError on transformation failure
    """
    if transformation_type == EnumTransformationType.IDENTITY:
        return data

    handler = TRANSFORMATION_REGISTRY.get(transformation_type)
    if handler is None:
        raise ModelOnexError(f"Unknown transformation type: {transformation_type}")

    return handler(data, config)
```

### Mapping Execution

v1.0 mapping uses simple path expressions:

```yaml
field_mappings:
  result: "$.steps.transform_case.output"
  original: "$.input.text"
```

### v1.0 Mapping Path Grammar (Intentionally Minimal)

v1.0 does **NOT** implement full JSONPath. This is intentional.

**Supported Forms**:

| Pattern | Description | Example |
|---------|-------------|---------|
| `$.input` | Full input object | `$.input` |
| `$.input.<field>` | Direct child field | `$.input.text` |
| `$.input.<field>.<subfield>` | Nested fields | `$.input.options.mode` |
| `$.steps.<step_name>.output` | Full output from previous step | `$.steps.trim.output` |

**NOT Supported in v1.0**:

| Pattern | Why Not |
|---------|---------|
| `$.input.items[0]` | Array indexing requires expression language |
| `$.input.items[*].value` | Wildcards require expression language |
| `$.input[?(@.active)]` | Filters require expression language |
| `$.input.a + $.input.b` | Arithmetic requires expression language |
| `len($.input.items)` | Functions require expression language |

**Validation**: Any unsupported path pattern is a **contract validation error** at load time.

**Resolution**:
```python
def resolve_path(path: str, input_data: Any, step_results: dict) -> Any:
    if path.startswith("$.input"):
        return resolve_json_path(path[7:], input_data)
    if path.startswith("$.steps."):
        parts = path[8:].split(".", 1)
        step_name = parts[0]
        if step_name not in step_results:
            raise ModelOnexError(f"Step not found: {step_name}")
        result = step_results[step_name]
        if len(parts) > 1 and parts[1] == "output":
            return result.output
        raise ModelOnexError(f"Invalid path: {path}")
    raise ModelOnexError(f"Invalid path prefix: {path}")
```

### IDENTITY Transformation Rules

The `IDENTITY` transformation is special - it has **no config**:

- `transformation_config` **must** be omitted or `null`
- The transformation simply returns the input data unchanged
- Useful as a no-op placeholder or for explicit passthrough steps

**Example**:
```yaml
- step_name: passthrough
  step_type: transformation
  transformation_type: identity
  # NO transformation_config - must be omitted
```

**Validation**: If `transformation_type` is `IDENTITY` and `transformation_config` is provided, contract validation fails.

---

## Immutability Guarantees (v1.0)

All pipeline artifacts are immutable after creation:

| Model | Immutable? | Enforcement |
|-------|------------|-------------|
| `ModelComputeExecutionContext` | ✅ Yes | `frozen=True` |
| `ModelComputeStepMetadata` | ✅ Yes | `frozen=True` |
| `ModelComputeStepResult` | ✅ Yes | `frozen=True` |
| `ModelComputePipelineResult` | ✅ Yes | `frozen=True` |

The executor may maintain internal mutable structures while running, but anything exposed outside the executor is frozen. This prevents:
- Accidental mutation between steps
- Mutation after pipeline completion
- Race conditions in future parallel execution (v1.2+)

This sets up v1.2's replay/observability guarantees cleanly.

---

## Error Model (v1.0)

v1.0 uses **string-only error types**:

```python
error_type: str | None = None   # e.g., "validation_failed", "transformation_error"
error_message: str | None = None
error_step: str | None = None
```

**Why not enums in v1.0?**
- Enums require defining a complete taxonomy upfront
- v1.0 focuses on getting the pipeline mechanics right
- String errors are sufficient for debugging

**v1.1+ Upgrade Path**:
- `EnumComputeErrorType` will be introduced in v1.1
- `ModelComputeError` structured error model in v1.2
- `ModelParallelStepError` for parallel step aggregation in v1.2

Existing v1.0 contracts will continue to work - error type becomes an enum value instead of free-form string.

---

## v1.0 NodeCompute Behavior

### Startup Behavior

When a `NodeCompute` instance starts:

1. **Load Contract**: Read `compute_operations` from node contract
2. **Validate Structure**: Validate `ModelComputeSubcontract` with `extra="forbid"`
3. **Resolve Schemas**: Resolve `input_schema_ref` / `output_schema_ref` from registry
4. **Fail Fast**: If contract or schemas are invalid, node **must not start**

### Runtime Behavior

When `process(ModelComputeInput)` is called:

1. **Build Context**: Create `ModelComputeExecutionContext` with operation_id, correlation_id
2. **Execute Pipeline**: Call `MixinComputeExecution.execute_compute_pipeline()`
3. **Check Timeout**: Abort if `pipeline_timeout_ms` exceeded
4. **Build Output**: Convert `ModelComputePipelineResult` to `ModelComputeOutput`
5. **Return**: Return typed output to caller

### Lifecycle

```text
┌─────────────────┐
│  Contract Load  │──▶ Validates structure, resolves schemas
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Node Ready    │──▶ Contract frozen, schemas cached
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   process()     │──▶ Builds context, executes pipeline, returns result
└─────────────────┘
```

---

## Schema Resolution

### Resolution Rules

1. `input_schema_ref` and `output_schema_ref` are resolved at **contract load time**
2. If schema reference cannot be resolved → **contract validation failure**
3. NodeCompute instance **must not start** if schema resolution fails
4. No version ranges - exact match required

### Schema Reference Format

```yaml
input_schema_ref: text_processor_input_v1
output_schema_ref: text_processor_output_v1
```

Format: `{name}_v{major}` (e.g., `text_processor_input_v1`)

### Validation Step Schema Resolution

Within validation steps, `schema_ref` can use aliases:
- `input_schema` → Resolves to `input_schema_ref`
- `output_schema` → Resolves to `output_schema_ref`
- Otherwise → Resolve from global schema registry

---

## Example Contract

### Simple Text Processor

```yaml
# examples/contracts/compute/text_processor_v1.yaml
node_type: COMPUTE
node_name: text_processor
node_version: "1.0.0"

compute_operations:
  version: "1.0.0"
  operation_name: text_normalization
  operation_version: "1.0.0"
  description: "Normalize and clean text data"

  input_schema_ref: text_input_v1
  output_schema_ref: text_output_v1

  pipeline_timeout_ms: 5000

  pipeline:
    # Step 1: Validate input (uses ModelValidationStepConfig, NOT a transformation)
    - step_name: validate_input
      step_type: validation
      validation_config:
        config_type: validation
        schema_ref: input_schema
        fail_on_error: true

    # Step 2: Normalize unicode
    - step_name: normalize_unicode
      step_type: transformation
      transformation_type: normalize_unicode
      transformation_config:
        config_type: normalize_unicode
        form: NFC

    # Step 3: Trim whitespace
    - step_name: trim_whitespace
      step_type: transformation
      transformation_type: trim
      transformation_config:
        config_type: trim
        mode: both

    # Step 4: Collapse multiple spaces
    - step_name: collapse_spaces
      step_type: transformation
      transformation_type: regex
      transformation_config:
        config_type: regex
        pattern: "\\s+"
        replacement: " "

    # Step 5: Convert to lowercase
    - step_name: to_lowercase
      step_type: transformation
      transformation_type: case_conversion
      transformation_config:
        config_type: case_conversion
        mode: lowercase

    # Step 6: Identity passthrough (demonstrates no-config transformation)
    - step_name: passthrough
      step_type: transformation
      transformation_type: identity
      # NO transformation_config for identity

    # Step 7: Map output
    - step_name: build_output
      step_type: mapping
      mapping_config:
        config_type: mapping
        field_mappings:
          normalized_text: "$.steps.passthrough.output"
          original_length: "$.input.length"
```

### Usage

```python
from omnibase_core.nodes import NodeCompute

class NodeTextProcessor(NodeCompute):
    """Text processor - all logic from contract."""
    pass
```

---

## Implementation Plan

### Phase 1: Core Models & Enums (~3 days)

| Task | File | Priority |
|------|------|----------|
| EnumComputeStepType | `enums/enum_compute_step_type.py` | P0 |
| EnumTransformationType | `enums/enum_transformation_type.py` | P0 |
| EnumCaseMode | `enums/enum_case_mode.py` | P0 |
| EnumRegexFlag | `enums/enum_regex_flag.py` | P0 |
| EnumUnicodeForm | `enums/enum_unicode_form.py` | P0 |
| EnumTrimMode | `enums/enum_trim_mode.py` | P0 |
| ModelComputeExecutionContext | `models/compute/model_compute_execution_context.py` | P0 |
| ModelComputeStepMetadata | `models/compute/model_compute_step_metadata.py` | P0 |
| ModelComputeStepResult | `models/compute/model_compute_step_result.py` | P0 |
| ModelComputePipelineResult | `models/compute/model_compute_pipeline_result.py` | P0 |

### Phase 2: Config Models (~2 days)

| Task | File | Priority |
|------|------|----------|
| ModelTransformRegexConfig | `models/transformations/model_transform_regex_config.py` | P0 |
| ModelTransformCaseConfig | `models/transformations/model_transform_case_config.py` | P0 |
| ModelTransformTrimConfig | `models/transformations/model_transform_trim_config.py` | P0 |
| ModelTransformUnicodeConfig | `models/transformations/model_transform_unicode_config.py` | P0 |
| ModelTransformJsonPathConfig | `models/transformations/model_transform_json_path_config.py` | P0 |
| ModelValidationStepConfig | `models/transformations/model_validation_step_config.py` | P0 |
| ModelMappingConfig | `models/transformations/model_mapping_config.py` | P0 |
| ModelTransformationConfig | `models/transformations/types.py` | P0 |

### Phase 3: Contract & Execution (~3 days)

| Task | File | Priority |
|------|------|----------|
| ModelComputePipelineStep | `models/contracts/subcontracts/model_compute_pipeline_step.py` | P0 |
| ModelComputeSubcontract | `models/contracts/subcontracts/model_compute_subcontract.py` | P0 |
| compute_executor.py | `utils/compute_executor.py` | P0 |
| compute_transformations.py | `utils/compute_transformations.py` | P0 |
| MixinComputeExecution | `mixins/mixin_compute_execution.py` | P0 |
| Refactor NodeCompute | `nodes/node_compute.py` | P0 |

### Phase 4: Testing (~2 days)

| Task | File | Priority |
|------|------|----------|
| Unit tests for enums | `tests/unit/enums/test_compute_*.py` | P0 |
| Unit tests for models | `tests/unit/models/compute/test_*.py` | P0 |
| Unit tests for executor | `tests/unit/utils/test_compute_executor.py` | P0 |
| Unit tests for transformations | `tests/unit/utils/test_compute_transformations.py` | P0 |
| Integration tests | `tests/integration/test_compute_pipeline.py` | P0 |

### Total Estimate

- **Files**: ~25 files
- **Code**: ~800 lines
- **Tests**: ~600 lines
- **Timeline**: 10 working days

---

## Acceptance Criteria

### Functional Requirements

- [ ] `ModelComputeSubcontract` validates contracts with `extra="forbid"`
- [ ] All 6 transformation types implemented and tested (IDENTITY, REGEX, CASE_CONVERSION, TRIM, NORMALIZE_UNICODE, JSON_PATH)
- [ ] VALIDATION step type uses separate `ModelValidationStepConfig` (not a transformation)
- [ ] Pipeline executes steps sequentially
- [ ] Pipeline aborts on first failure
- [ ] Mapping resolves `$.input` and `$.steps.<name>.output` paths
- [ ] Schema references validated at contract load time
- [ ] Pipeline timeout enforced

### Type Safety Requirements

- [ ] All config models have `config_type` discriminator field
- [ ] All models use `ConfigDict(extra="forbid", frozen=True)` where appropriate
- [ ] `ModelTransformationConfig` is proper discriminated union
- [ ] mypy --strict passes with zero errors

### Testing Requirements

- [ ] Unit tests for each enum
- [ ] Unit tests for each model
- [ ] Unit tests for each transformation type
- [ ] Integration test with example contract
- [ ] 90%+ code coverage

### Documentation Requirements

- [ ] Example contract in `examples/contracts/compute/`
- [ ] API documentation for public functions
- [ ] Migration guide from code-driven NodeCompute

---

## References

- **Full Vision**: [NODECOMPUTE_FULL_DESIGN_V1X_TARGET.md](./NODECOMPUTE_FULL_DESIGN_V1X_TARGET.md)
- **Versioning Roadmap**: [NODECOMPUTE_VERSIONING_ROADMAP.md](./NODECOMPUTE_VERSIONING_ROADMAP.md)
- **Linear Issue**: [OMN-465](https://linear.app/omninode/issue/OMN-465)
- **NodeReducer Pattern**: [node_reducer.py](../../src/omnibase_core/nodes/node_reducer.py)
- **NodeOrchestrator Pattern**: [node_orchestrator.py](../../src/omnibase_core/nodes/node_orchestrator.py)

---

**Last Updated**: 2025-12-07
**Version**: 1.0.0
**Status**: DRAFT - Ready for Implementation
