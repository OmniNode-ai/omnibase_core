# Your First Node - omnibase_core

**Status**: ✅ Complete
**Estimated Time**: 20 minutes

## Overview

This tutorial guides you through creating your first complete ONEX node from scratch, with proper models, testing, and deployment. You'll build a temperature converter that demonstrates real-world patterns.

## What You'll Build

A temperature converter COMPUTE node that:
- Converts between Celsius, Fahrenheit, and Kelvin
- Validates input ranges and units
- Handles errors gracefully with proper error types
- Includes comprehensive tests with edge cases
- Uses Pydantic models for type safety

## Prerequisites

- ✅ Completed [Installation](INSTALLATION.md)
- ✅ Completed [Quick Start](QUICK_START.md)
- ✅ Basic Python knowledge
- ✅ Understanding of Pydantic models

## Step-by-Step Guide

### Step 1: Project Setup

```bash
# Create project directory
mkdir temperature-converter
cd temperature-converter

# Initialize Poetry project
poetry init --no-interaction
poetry add omnibase_core
poetry add --group dev pytest pytest-asyncio mypy

# Create project structure
mkdir -p src/temperature_converter/{nodes,models,enums}
mkdir -p tests/{nodes,models,enums}
touch src/temperature_converter/__init__.py
touch src/temperature_converter/nodes/__init__.py
touch src/temperature_converter/models/__init__.py
touch src/temperature_converter/enums/__init__.py
```

### Step 2: Define Enums

**File**: `src/temperature_converter/enums/temperature_unit.py`

```python
"""Temperature unit enumeration."""

from enum import Enum


class TemperatureUnit(str, Enum):
    """Supported temperature units."""

    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"

    @classmethod
    def get_all_units(cls) -> list[str]:
        """Get all supported temperature units."""
        return [unit.value for unit in cls]

    def get_symbol(self) -> str:
        """Get the symbol for this temperature unit."""
        symbols = {
            self.CELSIUS: "°C",
            self.FAHRENHEIT: "°F",
            self.KELVIN: "K"
        }
        return symbols[self]
```

### Step 3: Define Input Model

**File**: `src/temperature_converter/models/temperature_input.py`

```python
"""Input model for temperature conversion."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..enums.temperature_unit import TemperatureUnit


class TemperatureInput(BaseModel):
    """Input for temperature conversion."""

    # Pydantic v2: model_config replaces Config class
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        json_schema_extra={
            "examples": [{
                "value": 25.0,
                "from_unit": "celsius",
                "to_unit": "fahrenheit",
                "precision": 2
            }]
        }
    )

    value: float = Field(
        description="Temperature value to convert",
        gt=-273.15,  # Absolute zero in Celsius
        le=10000.0   # Reasonable upper limit
    )

    from_unit: TemperatureUnit = Field(
        description="Source temperature unit"
    )

    to_unit: TemperatureUnit = Field(
        description="Target temperature unit"
    )

    precision: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Number of decimal places in result"
    )

    # Pydantic v2: field_validator replaces validator, requires @classmethod
    @field_validator('from_unit', 'to_unit')
    @classmethod
    def validate_units(cls, v):
        """Ensure units are valid."""
        if v not in TemperatureUnit:
            raise ValueError(f"Invalid temperature unit: {v}")
        return v

    # Pydantic v2: field_validator for dependent validation
    @field_validator('value')
    @classmethod
    def validate_temperature_range(cls, v, info):
        """Validate temperature is within reasonable range for the unit."""
        # Pydantic v2: info.data replaces values
        from_unit = info.data.get('from_unit')

        if from_unit == TemperatureUnit.CELSIUS:
            if v < -273.15:  # Absolute zero
                raise ValueError("Temperature cannot be below absolute zero (-273.15°C)")
        elif from_unit == TemperatureUnit.FAHRENHEIT:
            if v < -459.67:  # Absolute zero in Fahrenheit
                raise ValueError("Temperature cannot be below absolute zero (-459.67°F)")
        elif from_unit == TemperatureUnit.KELVIN:
            if v < 0:  # Absolute zero in Kelvin
                raise ValueError("Temperature cannot be below absolute zero (0K)")

        return v
```

### Step 4: Define Output Model

**File**: `src/temperature_converter/models/temperature_output.py`

```python
"""Output model for temperature conversion."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from ..enums.temperature_unit import TemperatureUnit


class TemperatureOutput(BaseModel):
    """Output from temperature conversion."""

    # Pydantic v2: model_config replaces Config class
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        json_schema_extra={
            "examples": [{
                "original_value": 25.0,
                "converted_value": 77.0,
                "from_unit": "celsius",
                "to_unit": "fahrenheit",
                "from_symbol": "°C",
                "to_symbol": "°F",
                "precision": 2,
                "success": True
            }]
        }
    )

    original_value: float = Field(description="Original input value")
    converted_value: float = Field(description="Converted temperature value")

    from_unit: TemperatureUnit = Field(description="Source temperature unit")
    to_unit: TemperatureUnit = Field(description="Target temperature unit")

    from_symbol: str = Field(description="Source unit symbol")
    to_symbol: str = Field(description="Target unit symbol")

    precision: int = Field(description="Number of decimal places used")

    success: bool = Field(default=True, description="Whether conversion was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if conversion failed")
```

### Step 5: Implement the Node

**File**: `src/temperature_converter/nodes/temperature_converter_compute.py`

```python
"""Temperature converter COMPUTE node."""

import time
from typing import Dict, Any
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

from ..models.temperature_input import TemperatureInput
from ..models.temperature_output import TemperatureOutput
from ..enums.temperature_unit import TemperatureUnit


class TemperatureConverterCompute(NodeCompute):
    """COMPUTE node for temperature conversions."""

    def __init__(self, container: ModelONEXContainer):
        """Initialize the temperature converter."""
        super().__init__(container)

        # Conversion statistics
        self.conversion_count = 0
        self.error_count = 0

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert temperature between units.

        Args:
            input_data: Dictionary containing temperature conversion parameters

        Returns:
            Dictionary with conversion result

        Raises:
            ModelOnexError: If conversion fails
        """
        start_time = time.time()

        try:
            # Validate and parse input
            temp_input = TemperatureInput(**input_data)

            # Perform conversion
            result = self._convert_temperature(temp_input)

            # Update statistics
            self.conversion_count += 1

            # Add processing time
            processing_time = (time.time() - start_time) * 1000

            return {
                **result.dict(),
                "processing_time_ms": round(processing_time, 3)
            }

        except Exception as e:
            self.error_count += 1

            # Convert to ONEX error
            if isinstance(e, ValueError):
                error_code = EnumCoreErrorCode.VALIDATION_ERROR
            else:
                error_code = EnumCoreErrorCode.PROCESSING_ERROR

            raise ModelOnexError(
                error_code=error_code,
                message=f"Temperature conversion failed: {str(e)}",
                context={"input_data": input_data}
            ) from e

    def _convert_temperature(self, input_data: TemperatureInput) -> TemperatureOutput:
        """
        Perform the actual temperature conversion.

        Args:
            input_data: Validated input data

        Returns:
            Conversion result
        """
        # Convert to Celsius first (our base unit)
        celsius_value = self._to_celsius(input_data.value, input_data.from_unit)

        # Convert from Celsius to target unit
        converted_value = self._from_celsius(celsius_value, input_data.to_unit)

        # Round to specified precision
        converted_value = round(converted_value, input_data.precision)

        return TemperatureOutput(
            original_value=input_data.value,
            converted_value=converted_value,
            from_unit=input_data.from_unit,
            to_unit=input_data.to_unit,
            from_symbol=input_data.from_unit.get_symbol(),
            to_symbol=input_data.to_unit.get_symbol(),
            precision=input_data.precision
        )

    def _to_celsius(self, value: float, unit: TemperatureUnit) -> float:
        """Convert any temperature unit to Celsius."""
        if unit == TemperatureUnit.CELSIUS:
            return value
        elif unit == TemperatureUnit.FAHRENHEIT:
            return (value - 32) * 5/9
        elif unit == TemperatureUnit.KELVIN:
            return value - 273.15
        else:
            raise ValueError(f"Unsupported source unit: {unit}")

    def _from_celsius(self, celsius_value: float, unit: TemperatureUnit) -> float:
        """Convert Celsius to any temperature unit."""
        if unit == TemperatureUnit.CELSIUS:
            return celsius_value
        elif unit == TemperatureUnit.FAHRENHEIT:
            return (celsius_value * 9/5) + 32
        elif unit == TemperatureUnit.KELVIN:
            return celsius_value + 273.15
        else:
            raise ValueError(f"Unsupported target unit: {unit}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        total_operations = self.conversion_count + self.error_count
        success_rate = (self.conversion_count / total_operations * 100) if total_operations > 0 else 0

        return {
            "total_conversions": self.conversion_count,
            "total_errors": self.error_count,
            "total_operations": total_operations,
            "success_rate_percent": round(success_rate, 2)
        }
```

### Step 6: Write Comprehensive Tests

**File**: `tests/nodes/test_temperature_converter.py`

```python
"""Tests for temperature converter node."""

import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from temperature_converter.nodes.temperature_converter_compute import TemperatureConverterCompute
from temperature_converter.enums.temperature_unit import TemperatureUnit


@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def converter(container):
    """Create temperature converter node."""
    return TemperatureConverterCompute(container)


@pytest.mark.asyncio
async def test_celsius_to_fahrenheit(converter):
    """Test Celsius to Fahrenheit conversion."""
    result = await converter.process({
        "value": 25.0,
        "from_unit": "celsius",
        "to_unit": "fahrenheit",
        "precision": 2
    })

    assert result["converted_value"] == 77.0
    assert result["original_value"] == 25.0
    assert result["from_unit"] == "celsius"
    assert result["to_unit"] == "fahrenheit"
    assert result["success"] is True


@pytest.mark.asyncio
async def test_fahrenheit_to_celsius(converter):
    """Test Fahrenheit to Celsius conversion."""
    result = await converter.process({
        "value": 68.0,
        "from_unit": "fahrenheit",
        "to_unit": "celsius",
        "precision": 1
    })

    assert result["converted_value"] == 20.0
    assert result["from_unit"] == "fahrenheit"
    assert result["to_unit"] == "celsius"


@pytest.mark.asyncio
async def test_celsius_to_kelvin(converter):
    """Test Celsius to Kelvin conversion."""
    result = await converter.process({
        "value": 0.0,
        "from_unit": "celsius",
        "to_unit": "kelvin",
        "precision": 1
    })

    assert result["converted_value"] == 273.1
    assert result["from_unit"] == "celsius"
    assert result["to_unit"] == "kelvin"


@pytest.mark.asyncio
async def test_kelvin_to_fahrenheit(converter):
    """Test Kelvin to Fahrenheit conversion."""
    result = await converter.process({
        "value": 273.15,
        "from_unit": "kelvin",
        "to_unit": "fahrenheit",
        "precision": 2
    })

    assert result["converted_value"] == 32.0
    assert result["from_unit"] == "kelvin"
    assert result["to_unit"] == "fahrenheit"


@pytest.mark.asyncio
async def test_same_unit_conversion(converter):
    """Test conversion to the same unit."""
    result = await converter.process({
        "value": 25.5,
        "from_unit": "celsius",
        "to_unit": "celsius",
        "precision": 1
    })

    assert result["converted_value"] == 25.5
    assert result["original_value"] == 25.5


@pytest.mark.asyncio
async def test_precision_handling(converter):
    """Test precision handling."""
    result = await converter.process({
        "value": 25.123456,
        "from_unit": "celsius",
        "to_unit": "fahrenheit",
        "precision": 3
    })

    # Should round to 3 decimal places
    assert result["converted_value"] == 77.222
    assert result["precision"] == 3


@pytest.mark.asyncio
async def test_negative_temperatures(converter):
    """Test negative temperature conversions."""
    result = await converter.process({
        "value": -40.0,
        "from_unit": "celsius",
        "to_unit": "fahrenheit",
        "precision": 1
    })

    # -40°C = -40°F (the point where they intersect)
    assert result["converted_value"] == -40.0


@pytest.mark.asyncio
async def test_absolute_zero_validation(converter):
    """Test absolute zero validation."""
    with pytest.raises(ModelOnexError):
        await converter.process({
            "value": -300.0,  # Below absolute zero in Celsius
            "from_unit": "celsius",
            "to_unit": "fahrenheit"
        })


@pytest.mark.asyncio
async def test_invalid_input_missing_value(converter):
    """Test error handling for missing value."""
    with pytest.raises(ModelOnexError):
        await converter.process({
            "from_unit": "celsius",
            "to_unit": "fahrenheit"
        })


@pytest.mark.asyncio
async def test_invalid_input_missing_units(converter):
    """Test error handling for missing units."""
    with pytest.raises(ModelOnexError):
        await converter.process({
            "value": 25.0
        })


@pytest.mark.asyncio
async def test_statistics_tracking(converter):
    """Test statistics tracking."""
    # Perform some conversions
    await converter.process({
        "value": 25.0,
        "from_unit": "celsius",
        "to_unit": "fahrenheit"
    })

    await converter.process({
        "value": 68.0,
        "from_unit": "fahrenheit",
        "to_unit": "celsius"
    })

    # Try an invalid conversion
    try:
        await converter.process({
            "value": -300.0,
            "from_unit": "celsius",
            "to_unit": "fahrenheit"
        })
    except ModelOnexError:
        pass  # Expected error

    stats = converter.get_statistics()

    assert stats["total_conversions"] == 2
    assert stats["total_errors"] == 1
    assert stats["total_operations"] == 3
    assert stats["success_rate_percent"] == 66.67


@pytest.mark.asyncio
async def test_processing_time_tracking(converter):
    """Test that processing time is tracked."""
    result = await converter.process({
        "value": 25.0,
        "from_unit": "celsius",
        "to_unit": "fahrenheit"
    })

    assert "processing_time_ms" in result
    assert isinstance(result["processing_time_ms"], float)
    assert result["processing_time_ms"] >= 0
```

### Step 7: Run Tests and Validation

```bash
# Run tests
poetry run pytest tests/ -v

# Run type checking
poetry run mypy src/

# Run linting
poetry run ruff check src/ tests/
```

### Step 8: Create Usage Example

**File**: `example_usage.py`

```python
"""Example usage of the temperature converter."""

import asyncio
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from temperature_converter.nodes.temperature_converter_compute import TemperatureConverterCompute


async def main():
    """Demonstrate the temperature converter."""
    # Create container and node
    container = ModelONEXContainer()
    converter = TemperatureConverterCompute(container)

    # Test cases
    test_cases = [
        {"value": 0, "from_unit": "celsius", "to_unit": "fahrenheit", "precision": 1},
        {"value": 32, "from_unit": "fahrenheit", "to_unit": "celsius", "precision": 1},
        {"value": 0, "from_unit": "celsius", "to_unit": "kelvin", "precision": 1},
        {"value": 100, "from_unit": "celsius", "to_unit": "fahrenheit", "precision": 2},
        {"value": -40, "from_unit": "celsius", "to_unit": "fahrenheit", "precision": 1},
    ]

    print("Temperature Converter Demo")
    print("=" * 40)

    for test_case in test_cases:
        try:
            result = await converter.process(test_case)
            print(f"{result['original_value']}{result['from_symbol']} = {result['converted_value']}{result['to_symbol']}")
        except Exception as e:
            print(f"Error converting {test_case}: {e}")

    # Show statistics
    stats = converter.get_statistics()
    print(f"\nStatistics: {stats['total_conversions']} conversions, {stats['success_rate_percent']}% success rate")


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
poetry run python example_usage.py

# Expected output:
# Temperature Converter Demo
# ========================================
# 0°C = 32.0°F
# 32°F = 0.0°C
# 0°C = 273.1K
# 100°C = 212.0°F
# -40°C = -40.0°F
#
# Statistics: 5 conversions, 100.0% success rate
```

## What You Learned

By completing this tutorial, you've learned:

- ✅ **Project Structure**: How to organize a complete ONEX node project
- ✅ **Pydantic Models**: Input/output validation with proper error handling
- ✅ **Enums**: Type-safe constants and validation
- ✅ **Node Implementation**: Complete COMPUTE node with business logic
- ✅ **Error Handling**: ONEX error patterns and proper exception management
- ✅ **Testing**: Comprehensive test coverage with edge cases
- ✅ **Type Safety**: Full type checking with MyPy
- ✅ **Statistics**: Performance tracking and monitoring
- ✅ **Documentation**: Clear docstrings and examples

## Key ONEX Patterns You Used

1. **Model-Driven Development**: Pydantic models for validation
2. **Error Handling**: Proper ONEX error types and context
3. **Async Processing**: Non-blocking computation
4. **Container Pattern**: Dependency injection
5. **Statistics Tracking**: Performance monitoring
6. **Type Safety**: Full typing throughout

## Next Steps

### 🚀 **Continue Building**
- [Node Building Guide](../guides/node-building/README.md) - Comprehensive guide
- [EFFECT Node Tutorial](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md) - External interactions
- [REDUCER Node Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md) - State management

### 🏗️ **Enhance Your Node**
- Add more temperature units (Rankine, Réaumur)
- Add batch conversion support
- Add caching for common conversions
- Add logging and metrics
- Add API endpoints

### 📚 **Learn More**
- [Testing Guide](../guides/TESTING_GUIDE.md) - Advanced testing strategies
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Best practices
- [Performance Tuning](../guides/PRODUCTION_CACHE_TUNING.md) - Optimization

## Challenge: Extend Your Node

Try these enhancements:

1. **Add More Units**: Support Rankine and Réaumur temperature scales
2. **Batch Processing**: Convert multiple temperatures at once
3. **Caching**: Cache common conversions for performance
4. **API Endpoints**: Add REST API endpoints
5. **Configuration**: Make conversion formulas configurable

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure you're in the virtual environment
poetry shell

# Check imports
poetry run python -c "from temperature_converter.nodes.temperature_converter_compute import TemperatureConverterCompute"
```

#### Test Failures
```bash
# Run with verbose output
poetry run pytest tests/ -vvs

# Run specific test
poetry run pytest tests/nodes/test_temperature_converter.py::test_celsius_to_fahrenheit -v
```

#### Type Checking Issues
```bash
# Run MyPy with more details
poetry run mypy src/ --show-error-codes
```

## Summary

🎉 **Congratulations!** You've built a complete, production-ready ONEX node!

You now understand:
- ✅ Complete project structure and organization
- ✅ Pydantic models for validation and type safety
- ✅ Comprehensive error handling with ONEX patterns
- ✅ Full test coverage with edge cases
- ✅ Performance tracking and statistics
- ✅ Real-world node implementation patterns

**Ready for more?** Continue with the [Node Building Guide](../guides/node-building/README.md) to learn about other node types and advanced patterns.

---

**Related Documentation**:
- [Quick Start Guide](QUICK_START.md)
- [Node Building Guide](../guides/node-building/README.md)
- [Testing Guide](../guides/TESTING_GUIDE.md)
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
