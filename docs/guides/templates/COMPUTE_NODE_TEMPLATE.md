> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > Templates > COMPUTE Node

# COMPUTE Node Template

## Overview

Template for building ONEX COMPUTE nodes. COMPUTE nodes perform **pure transformations** -- deterministic computations with no side effects. Same input always produces same output.

**Architectural invariants**:

- Nodes are thin shells -- only `__init__` calling `super().__init__(container)`
- Handlers own ALL business logic
- YAML contracts define behavior
- COMPUTE nodes MUST return `result` via `ModelHandlerOutput.for_compute(result=...)`
- COMPUTE nodes CANNOT emit `events[]`, `intents[]`, or `projections[]`

## When to Use

- Data validation and rule enforcement
- Format conversion and mapping
- Business rule evaluation
- Parsing and serialization
- Algorithm execution
- Price calculations and aggregations

## Directory Structure

```
nodes/node_data_validator/
    contract.yaml          # ONEX contract (required)
    node.py                # Thin node shell (required)
    handlers/
        handler_validation.py  # Business logic lives here
    models/
        __init__.py
        model_validation_input.py
        model_validation_output.py
```

## Template Files

### 1. YAML Contract (`contract.yaml`)

The contract is the **single source of truth** for node behavior.

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_data_validator"
node_type: "COMPUTE_GENERIC"
description: "Validates data structures against schema rules."

input_model:
  name: "ModelValidationRequest"
  module: "myapp.nodes.node_data_validator.models.model_validation_input"

output_model:
  name: "ModelValidationResult"
  module: "myapp.nodes.node_data_validator.models.model_validation_output"

capabilities:
  - name: "data_validation"
    description: "Validate data structures against schema rules"
  - name: "schema_enforcement"
  - name: "error_reporting"

# Validation rules (contract-driven, not hardcoded in Python)
validation_rules:
  - rule_id: "VAL-001"
    name: "Required Fields Check"
    severity: "ERROR"
    description: "Verify all required fields are present"
    detection_strategy:
      type: "field_presence"
      required_fields:
        - "user_id"
        - "email"
        - "created_at"

  - rule_id: "VAL-002"
    name: "Email Format Validation"
    severity: "ERROR"
    description: "Verify email follows valid format"
    detection_strategy:
      type: "regex_pattern"
      field: "email"
      pattern: "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"

# Handler routing
handler_routing:
  routing_strategy: "payload_type_match"
  handlers:
    - handler:
        name: "HandlerValidation"
        module: "myapp.nodes.node_data_validator.handlers.handler_validation"
```

### 2. Node Implementation (`node.py`)

The node is a **thin coordination shell**. No business logic here.

```python
"""Data validator compute node for schema validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeDataValidator(NodeCompute):
    """Data validator -- COMPUTE_GENERIC node.

    Validates data structures against schema rules defined in contract.yaml.
    All business logic is in handlers/handler_validation.py.

    Pure computation -- no side effects.
    Same input always produces same output.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the validator node."""
        super().__init__(container)


__all__ = ["NodeDataValidator"]
```

### 3. Handler Implementation (`handlers/handler_validation.py`)

All business logic lives in the handler, not the node.

```python
"""Validation handler for the data validator compute node."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


class HandlerValidation:
    """Handler that owns the validation business logic.

    This handler implements the actual computation. The node
    delegates to this handler -- it never contains business logic itself.
    """

    async def handle(
        self,
        input_data: dict[str, Any],
        contract_rules: list[dict[str, Any]],
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput:
        """Execute validation against contract-defined rules.

        Args:
            input_data: The data to validate.
            contract_rules: Validation rules from contract.yaml.
            input_envelope_id: ID of the input envelope that triggered this handler.
            correlation_id: Correlation ID copied from the input envelope.

        Returns:
            ModelHandlerOutput with result containing validation findings.
        """
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        for rule in contract_rules:
            rule_id = rule["rule_id"]
            strategy = rule["detection_strategy"]

            if strategy["type"] == "field_presence":
                for field in strategy["required_fields"]:
                    if field not in input_data:
                        errors.append({
                            "rule_id": rule_id,
                            "field": field,
                            "message": f"Required field '{field}' is missing",
                        })

            elif strategy["type"] == "regex_pattern":
                field = strategy["field"]
                pattern = strategy["pattern"]
                value = input_data.get(field, "")
                if value and not re.match(pattern, str(value)):
                    errors.append({
                        "rule_id": rule_id,
                        "field": field,
                        "message": f"Field '{field}' does not match pattern",
                    })

        # COMPUTE nodes MUST return result
        return ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="handler-validation",
            result={
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "rules_checked": len(contract_rules),
            },
        )
```

### 4. Input Model (`models/model_validation_input.py`)

```python
"""Input model for data validation compute operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationRequest(BaseModel):
    """Input model for data validation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    data: dict[str, Any] = Field(
        description="The data structure to validate",
    )
    schema_id: str = Field(
        description="Identifier of the validation schema to apply",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for request tracing",
    )
```

### 5. Output Model (`models/model_validation_output.py`)

```python
"""Output model for data validation compute operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationResult(BaseModel):
    """Output model for data validation.

    Contains the validation result with error and warning details.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    valid: bool = Field(
        description="Whether the data passed all validation rules",
    )
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="Validation errors found",
    )
    warnings: list[dict[str, str]] = Field(
        default_factory=list,
        description="Validation warnings found",
    )
    rules_checked: int = Field(
        default=0,
        description="Number of validation rules that were checked",
    )
```

## Output Constraints

COMPUTE is the **only** node kind that returns a typed `result`.

| Field | COMPUTE |
|-------|---------|
| `result` | **Required** |
| `events[]` | Forbidden |
| `intents[]` | Forbidden |
| `projections[]` | Forbidden |

```python
# CORRECT -- COMPUTE returns result
output = ModelHandlerOutput.for_compute(
    input_envelope_id=input_envelope_id,
    correlation_id=correlation_id,
    handler_id="handler-validation",
    result={"valid": True, "errors": []},
)

# WRONG -- COMPUTE cannot emit events (raises ModelOnexError)
output = ModelHandlerOutput.for_compute(
    input_envelope_id=input_envelope_id,
    correlation_id=correlation_id,
    handler_id="handler-validation",
    result={"valid": True},
    events=[some_event],  # ModelOnexError!
)
```

## Key Principles

1. **Node is a thin shell**: Only `__init__` calling `super().__init__(container)`. No methods, no state, no logic.
2. **Handler owns logic**: All computation happens in the handler class.
3. **Contract drives behavior**: Validation rules, capabilities, and routing are defined in YAML.
4. **Pure computation**: No I/O, no database calls, no side effects. Deterministic and cacheable.
5. **PEP 604 types**: Use `X | None` not `Optional[X]`, `list[str]` not `List[str]`.
6. **Pydantic v2**: Use `model_config = ConfigDict(...)` not `class Config:`. Use `pattern=` not `regex=`.
7. **`ModelONEXContainer`**: Always use `ModelONEXContainer` for DI, never `ModelContainer`.
8. **No backwards compatibility**: This repo has no external consumers. No shims, no deprecation periods.

## Testing

```python
"""Tests for the data validator compute node."""

from uuid import uuid4

import pytest
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

from myapp.nodes.node_data_validator.handlers.handler_validation import (
    HandlerValidation,
)


@pytest.mark.unit
class TestHandlerValidation:
    """Test the validation handler directly -- not the node."""

    async def test_valid_data_passes(self) -> None:
        handler = HandlerValidation()
        rules = [
            {
                "rule_id": "VAL-001",
                "detection_strategy": {
                    "type": "field_presence",
                    "required_fields": ["user_id", "email"],
                },
            }
        ]
        result = await handler.handle(
            {"user_id": "u1", "email": "a@b.com"},
            rules,
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
        )
        assert result.result["valid"] is True
        assert result.result["errors"] == []

    async def test_missing_field_fails(self) -> None:
        handler = HandlerValidation()
        rules = [
            {
                "rule_id": "VAL-001",
                "detection_strategy": {
                    "type": "field_presence",
                    "required_fields": ["user_id"],
                },
            }
        ]
        result = await handler.handle(
            {},
            rules,
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
        )
        assert result.result["valid"] is False
        assert len(result.result["errors"]) == 1
```

## Related Documentation

| Topic | Document |
|-------|----------|
| Node archetypes reference | [Node Archetypes](../../reference/node-archetypes.md) |
| Handler contract guide | [Handler Contract Guide](../../contracts/HANDLER_CONTRACT_GUIDE.md) |
| Four-node architecture | [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| Execution shapes | [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md) |
| Container types | [Container Types](../../architecture/CONTAINER_TYPES.md) |
| Coding standards | [CLAUDE.md](../../../CLAUDE.md) |
