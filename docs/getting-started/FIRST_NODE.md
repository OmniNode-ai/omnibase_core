> **Navigation**: [Home](../INDEX.md) > Getting Started > First Node

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Build Your First Node

**Estimated Time**: 20 minutes

## Overview

This tutorial walks you through building a complete ONEX COMPUTE node using the correct handler architecture. You will define a YAML contract, write Pydantic input/output models, implement a handler with business logic, and wire it all together with a thin node shell.

By the end, you will understand the foundational pattern used by every node in the system.

## What You Will Build

A temperature converter COMPUTE node that:
- Converts between Celsius, Fahrenheit, and Kelvin
- Uses a YAML contract as the source of truth for behavior
- Keeps business logic in a handler, not in the node
- Returns results via `ModelHandlerOutput` with enforced output constraints
- Follows ONEX file naming conventions

## Prerequisites

- Completed [Installation](INSTALLATION.md)
- Basic Python 3.12+ knowledge
- Familiarity with Pydantic models

## Key Architecture Rules

Before writing code, understand these non-negotiable rules:

1. **Nodes are thin shells** -- only `__init__` calling `super().__init__(container)`, no business logic
2. **Handlers own ALL business logic** -- conversion formulas, validation, error handling
3. **YAML contracts define behavior** -- the contract declares the node type, I/O models, and handler binding
4. **Output constraints are enforced per node kind**:

| Kind | Allowed | Forbidden |
|------|---------|-----------|
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |

These constraints are enforced at runtime by `ModelHandlerOutput` validators. Violating them raises `ModelOnexError`.

---

## Step 1: Create the Project Structure

```bash
mkdir -p temperature_converter/nodes/node_temperature_converter/{models,handlers}
mkdir -p temperature_converter/enums
mkdir -p tests/nodes

# Create required __init__.py files
touch temperature_converter/__init__.py
touch temperature_converter/nodes/__init__.py
touch temperature_converter/nodes/node_temperature_converter/__init__.py
touch temperature_converter/nodes/node_temperature_converter/models/__init__.py
touch temperature_converter/nodes/node_temperature_converter/handlers/__init__.py
touch temperature_converter/enums/__init__.py
```

The directory layout follows ONEX conventions:

```
temperature_converter/
├── enums/
│   └── enum_temperature_unit.py      # Enum prefix required
├── nodes/
│   └── node_temperature_converter/
│       ├── contract.yaml             # YAML contract (source of truth)
│       ├── node.py                   # Thin node shell
│       ├── models/
│       │   ├── model_temperature_input.py    # Model prefix required
│       │   └── model_temperature_output.py
│       └── handlers/
│           └── handler_temperature.py        # Handler prefix required
└── tests/
    └── nodes/
        └── test_temperature_converter.py
```

Note the file naming conventions: `enum_*`, `model_*`, `handler_*`. These are enforced by the project structure rules.

---

## Step 2: Define the YAML Contract

The contract is the single source of truth for what this node does. It declares the node type, I/O models, capabilities, and handler binding.

**File**: `temperature_converter/nodes/node_temperature_converter/contract.yaml`

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_temperature_converter"
node_type: "COMPUTE_GENERIC"
description: "Converts temperature values between Celsius, Fahrenheit, and Kelvin."

input_model:
  name: "ModelTemperatureInput"
  module: "temperature_converter.nodes.node_temperature_converter.models.model_temperature_input"

output_model:
  name: "ModelTemperatureOutput"
  module: "temperature_converter.nodes.node_temperature_converter.models.model_temperature_output"

capabilities:
  - name: "temperature.conversion"
    description: "Convert temperature between unit systems"

handler:
  path: "temperature_converter.nodes.node_temperature_converter.handlers.handler_temperature:handle_temperature_conversion"
```

Key points:
- `node_type: "COMPUTE_GENERIC"` -- this is a pure computation, no side effects
- `input_model` and `output_model` use fully qualified module paths
- `handler.path` uses colon-separated format: `module.path:callable_name`

---

## Step 3: Define the Enum

**File**: `temperature_converter/enums/enum_temperature_unit.py`

```python
"""Temperature unit enumeration."""

from __future__ import annotations

from enum import Enum


class EnumTemperatureUnit(str, Enum):
    """Supported temperature units."""

    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"

    def get_symbol(self) -> str:
        """Get the display symbol for this temperature unit."""
        symbols = {
            EnumTemperatureUnit.CELSIUS: "C",
            EnumTemperatureUnit.FAHRENHEIT: "F",
            EnumTemperatureUnit.KELVIN: "K",
        }
        return symbols[self]
```

---

## Step 4: Define Input and Output Models

**File**: `temperature_converter/nodes/node_temperature_converter/models/model_temperature_input.py`

```python
"""Input model for temperature conversion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from temperature_converter.enums.enum_temperature_unit import EnumTemperatureUnit


class ModelTemperatureInput(BaseModel):
    """Input for temperature conversion.

    Immutable value object following ONEX Pydantic standards.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    value: float = Field(
        description="Temperature value to convert",
    )
    from_unit: EnumTemperatureUnit = Field(
        description="Source temperature unit",
    )
    to_unit: EnumTemperatureUnit = Field(
        description="Target temperature unit",
    )
    precision: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Number of decimal places in result",
    )
```

**File**: `temperature_converter/nodes/node_temperature_converter/models/model_temperature_output.py`

```python
"""Output model for temperature conversion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from temperature_converter.enums.enum_temperature_unit import EnumTemperatureUnit


class ModelTemperatureOutput(BaseModel):
    """Output from temperature conversion.

    Immutable value object. Used as the result payload in ModelHandlerOutput.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    original_value: float = Field(description="Original input value")
    converted_value: float = Field(description="Converted temperature value")
    from_unit: EnumTemperatureUnit = Field(description="Source temperature unit")
    to_unit: EnumTemperatureUnit = Field(description="Target temperature unit")
    precision: int = Field(description="Number of decimal places used")
```

Note the use of:
- `ConfigDict(frozen=True, extra="forbid", from_attributes=True)` -- required for immutable value objects
- `X | None` instead of `Optional[X]` (PEP 604)
- `list[str]` instead of `List[str]` (lowercase generics)
- No `Optional` or `Dict` imports from `typing`

---

## Step 5: Write the Handler (Business Logic)

This is where all computation logic lives. The handler is a standalone callable, not a method on the node.

**File**: `temperature_converter/nodes/node_temperature_converter/handlers/handler_temperature.py`

```python
"""Handler for temperature conversion computation."""

from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

from temperature_converter.enums.enum_temperature_unit import EnumTemperatureUnit
from temperature_converter.nodes.node_temperature_converter.models.model_temperature_input import (
    ModelTemperatureInput,
)
from temperature_converter.nodes.node_temperature_converter.models.model_temperature_output import (
    ModelTemperatureOutput,
)


def _to_celsius(value: float, unit: EnumTemperatureUnit) -> float:
    """Convert a temperature value to Celsius."""
    if unit == EnumTemperatureUnit.CELSIUS:
        return value
    elif unit == EnumTemperatureUnit.FAHRENHEIT:
        return (value - 32) * 5 / 9
    elif unit == EnumTemperatureUnit.KELVIN:
        return value - 273.15
    raise ValueError(f"Unsupported source unit: {unit}")


def _from_celsius(celsius: float, unit: EnumTemperatureUnit) -> float:
    """Convert a Celsius value to the target unit."""
    if unit == EnumTemperatureUnit.CELSIUS:
        return celsius
    elif unit == EnumTemperatureUnit.FAHRENHEIT:
        return (celsius * 9 / 5) + 32
    elif unit == EnumTemperatureUnit.KELVIN:
        return celsius + 273.15
    raise ValueError(f"Unsupported target unit: {unit}")


def handle_temperature_conversion(
    input_data: ModelTemperatureInput,
    *,
    input_envelope_id: UUID,
    correlation_id: UUID,
) -> ModelHandlerOutput[ModelTemperatureOutput]:
    """Convert a temperature value between units.

    This is a pure function: same input always produces the same output.
    No side effects, no I/O, no state mutation.

    Args:
        input_data: Validated temperature conversion request.
        input_envelope_id: ID of the input envelope (for causality tracking).
        correlation_id: Correlation ID copied from the input envelope.

    Returns:
        ModelHandlerOutput containing the conversion result.
        Uses for_compute() because COMPUTE nodes must return a result.
    """
    # Convert via Celsius as the intermediate representation
    celsius = _to_celsius(input_data.value, input_data.from_unit)
    converted = _from_celsius(celsius, input_data.to_unit)
    converted = round(converted, input_data.precision)

    result = ModelTemperatureOutput(
        original_value=input_data.value,
        converted_value=converted,
        from_unit=input_data.from_unit,
        to_unit=input_data.to_unit,
        precision=input_data.precision,
    )

    # COMPUTE nodes MUST return a result via for_compute()
    return ModelHandlerOutput.for_compute(
        input_envelope_id=input_envelope_id,
        correlation_id=correlation_id,
        handler_id="compute.temperature.converter",
        result=result,
    )
```

Key points about this handler:

1. **All logic lives here** -- conversion formulas, rounding, result construction
2. **Returns `ModelHandlerOutput.for_compute()`** -- the builder method enforces COMPUTE constraints automatically. If you tried to pass `events=` or `intents=`, it would raise `ModelOnexError`.
3. **Pure function** -- no `self`, no state, no I/O. Same input always produces the same output.
4. **Typed models** -- accepts `ModelTemperatureInput`, returns `ModelHandlerOutput[ModelTemperatureOutput]`

---

## Step 6: Write the Thin Node Shell

The node is a coordination shell. It does not contain business logic. Its only job is to call `super().__init__(container)`.

**File**: `temperature_converter/nodes/node_temperature_converter/node.py`

```python
"""Temperature converter compute node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeTemperatureConverter(NodeCompute):
    """Temperature converter - COMPUTE_GENERIC node.

    Converts temperature values between Celsius, Fahrenheit, and Kelvin.
    Pure computation with no side effects.

    All business logic lives in the handler:
        handler_temperature:handle_temperature_conversion

    Behavior is defined by contract.yaml.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the temperature converter node."""
        super().__init__(container)


__all__ = ["NodeTemperatureConverter"]
```

Notice what is **not** here:
- No `process()` method -- the handler owns the logic
- No `_convert_temperature()` -- business logic belongs in the handler
- No `self.conversion_count` -- nodes do not maintain state
- No `Dict[str, Any]` signatures -- typed models are used throughout
- The `__init__` does nothing except call `super().__init__(container)`

---

## Step 7: Write Tests

**File**: `tests/nodes/test_temperature_converter.py`

```python
"""Tests for the temperature converter handler."""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind

from temperature_converter.enums.enum_temperature_unit import EnumTemperatureUnit
from temperature_converter.nodes.node_temperature_converter.handlers.handler_temperature import (
    handle_temperature_conversion,
)
from temperature_converter.nodes.node_temperature_converter.models.model_temperature_input import (
    ModelTemperatureInput,
)


@pytest.mark.unit
class TestTemperatureConversionHandler:
    """Test the temperature conversion handler."""

    def _make_input(
        self,
        value: float,
        from_unit: EnumTemperatureUnit,
        to_unit: EnumTemperatureUnit,
        precision: int = 2,
    ) -> ModelTemperatureInput:
        return ModelTemperatureInput(
            value=value,
            from_unit=from_unit,
            to_unit=to_unit,
            precision=precision,
        )

    def _call_handler(self, input_data: ModelTemperatureInput):
        return handle_temperature_conversion(
            input_data=input_data,
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
        )

    def test_celsius_to_fahrenheit(self) -> None:
        """Test basic Celsius to Fahrenheit conversion."""
        input_data = self._make_input(
            value=100.0,
            from_unit=EnumTemperatureUnit.CELSIUS,
            to_unit=EnumTemperatureUnit.FAHRENHEIT,
        )
        output = self._call_handler(input_data)

        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.result is not None
        assert output.result.converted_value == 212.0
        assert output.result.original_value == 100.0

    def test_fahrenheit_to_celsius(self) -> None:
        """Test Fahrenheit to Celsius conversion."""
        input_data = self._make_input(
            value=32.0,
            from_unit=EnumTemperatureUnit.FAHRENHEIT,
            to_unit=EnumTemperatureUnit.CELSIUS,
        )
        output = self._call_handler(input_data)

        assert output.result is not None
        assert output.result.converted_value == 0.0

    def test_celsius_to_kelvin(self) -> None:
        """Test Celsius to Kelvin conversion."""
        input_data = self._make_input(
            value=0.0,
            from_unit=EnumTemperatureUnit.CELSIUS,
            to_unit=EnumTemperatureUnit.KELVIN,
        )
        output = self._call_handler(input_data)

        assert output.result is not None
        assert output.result.converted_value == 273.15

    def test_same_unit_returns_same_value(self) -> None:
        """Test that converting to the same unit is a no-op."""
        input_data = self._make_input(
            value=42.0,
            from_unit=EnumTemperatureUnit.CELSIUS,
            to_unit=EnumTemperatureUnit.CELSIUS,
        )
        output = self._call_handler(input_data)

        assert output.result is not None
        assert output.result.converted_value == 42.0

    def test_negative_40_intersection(self) -> None:
        """Test the -40 intersection point of Celsius and Fahrenheit."""
        input_data = self._make_input(
            value=-40.0,
            from_unit=EnumTemperatureUnit.CELSIUS,
            to_unit=EnumTemperatureUnit.FAHRENHEIT,
        )
        output = self._call_handler(input_data)

        assert output.result is not None
        assert output.result.converted_value == -40.0

    def test_precision_rounding(self) -> None:
        """Test that precision controls decimal places."""
        input_data = self._make_input(
            value=100.0,
            from_unit=EnumTemperatureUnit.FAHRENHEIT,
            to_unit=EnumTemperatureUnit.CELSIUS,
            precision=4,
        )
        output = self._call_handler(input_data)

        assert output.result is not None
        assert output.result.converted_value == 37.7778
        assert output.result.precision == 4

    def test_output_is_compute_kind(self) -> None:
        """Verify the handler returns COMPUTE-typed output."""
        input_data = self._make_input(
            value=0.0,
            from_unit=EnumTemperatureUnit.CELSIUS,
            to_unit=EnumTemperatureUnit.KELVIN,
        )
        output = self._call_handler(input_data)

        # ModelHandlerOutput enforces: COMPUTE has result, no events/intents/projections
        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.result is not None
        assert output.events == ()
        assert output.intents == ()
        assert output.projections == ()
```

Run the tests:

```bash
poetry run pytest tests/nodes/test_temperature_converter.py -v
```

---

## Step 8: Understand the Output Constraints

The `ModelHandlerOutput` model enforces architectural constraints at runtime. Here is what happens if you violate them:

```python
from uuid import uuid4
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

# CORRECT: COMPUTE returns a result
output = ModelHandlerOutput.for_compute(
    input_envelope_id=uuid4(),
    correlation_id=uuid4(),
    handler_id="compute.temperature.converter",
    result={"converted_value": 212.0},
)

# ERROR: COMPUTE cannot emit events
# This raises ModelOnexError at construction time:
#   "COMPUTE cannot emit events[] - result only.
#    COMPUTE nodes are pure transformations. If you need to emit events, use EFFECT."
```

The builder methods (`for_compute`, `for_effect`, `for_reducer`, `for_orchestrator`) are the preferred way to construct handler output because they set the correct `node_kind` automatically. The full constraint table:

| Builder Method | `node_kind` | Allowed Fields | Raises on |
|---|---|---|---|
| `for_compute()` | `COMPUTE` | `result` (required) | `events`, `intents`, `projections` |
| `for_effect()` | `EFFECT` | `events` | `intents`, `projections`, `result` |
| `for_reducer()` | `REDUCER` | `projections` | `events`, `intents`, `result` |
| `for_orchestrator()` | `ORCHESTRATOR` | `events`, `intents` | `projections`, `result` |

---

## What You Learned

By completing this tutorial, you have learned:

- **Contract-first development** -- the YAML contract defines behavior before any code is written
- **Handler architecture** -- business logic lives in handlers, not nodes
- **Thin node pattern** -- the node class is a coordination shell with no logic
- **ModelHandlerOutput** -- typed, constraint-enforced output that prevents architectural violations
- **Pydantic model standards** -- frozen, extra-forbid, from_attributes for immutable value objects
- **File naming conventions** -- `enum_*`, `model_*`, `handler_*` prefixes enforced by the project

## Common Mistakes to Avoid

| Mistake | Correct Pattern |
|---|---|
| Business logic in `node.py` | Put it in `handlers/handler_*.py` |
| `async def process(self, input_data: Dict[str, Any])` | Use typed Pydantic models as handler arguments |
| `Optional[str]` | `str \| None` (PEP 604) |
| `Dict[str, Any]`, `List[str]` | `dict[str, Any]`, `list[str]` |
| File named `temperature_unit.py` | Name it `enum_temperature_unit.py` |
| `ModelContainer` for DI | Use `ModelONEXContainer` |
| Returning `dict` from a handler | Return `ModelHandlerOutput.for_compute(result=...)` |
| `self._cache = {}` in node `__init__` | Nodes do not maintain state; use protocol injection |

## Next Steps

- [Quick Start](QUICK_START.md) -- See all four node kinds side by side
- [Node Archetypes Reference](../reference/node-archetypes.md) -- Complete reference for each node type
- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) -- Advanced handler contract features
- [Node Building Guide](../guides/node-building/README.md) -- In-depth guide for each node type

---

**Related Documentation**:
- [Quick Start Guide](QUICK_START.md)
- [Node Archetypes Reference](../reference/node-archetypes.md)
- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
