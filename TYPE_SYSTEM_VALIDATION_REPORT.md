# ONEX Type System Validation Report
## Zero Tolerance Any Type Detection Results

**Scan Summary**
- Files Scanned: 139
- Files with Violations: 9
- Total Violations: 32
- **Status**: ❌ VIOLATIONS DETECTED

## Critical Violations (Must Fix)

Found 32 critical Any type violations that must be eliminated:

### File: /src/omnibase_core/models/contracts/model_contract_compute.py
**Violations**: 1

- **Line 62**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `def __init__(self, **data: Any) -> None:`

### File: /src/omnibase_core/models/contracts/model_contract_effect.py
**Violations**: 5

- **Line 25**: Generic Any Usage
  - Context: Generic type containing Any
  - Code: `ValidationRulesInput = Union[`

- **Line 26**: Generic Any Usage
  - Context: Generic type containing Any
  - Code: `None, dict[str, Any], list[Any], "ModelValidationRules", str, int, float, bool`

- **Line 26**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `None, dict[str, Any], list[Any], "ModelValidationRules", str, int, float, bool`

- **Line 26**: Generic Any Usage
  - Context: Generic type containing Any
  - Code: `None, dict[str, Any], list[Any], "ModelValidationRules", str, int, float, bool`

- **Line 26**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `None, dict[str, Any], list[Any], "ModelValidationRules", str, int, float, bool`

### File: /src/omnibase_core/models/contracts/model_workflow_condition.py
**Violations**: 3

- **Line 15**: Generic Any Usage
  - Context: Generic type containing Any
  - Code: `ContextValue = Union[`

- **Line 21**: Generic Any Usage
  - Context: Generic type containing Any
  - Code: `dict[str, Any],  # Using Any for recursive dict values to avoid type complexity`

- **Line 21**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `dict[str, Any],  # Using Any for recursive dict values to avoid type complexity`

### File: /src/omnibase_core/models/nodes/model_node_configuration_value.py
**Violations**: 6

- **Line 71**: Function Parameter Any
  - Context: Parameter 'value' annotated with Any
  - Code: `def from_value(cls, value: Any) -> ModelNodeConfigurationValue:`

- **Line 71**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `def from_value(cls, value: Any) -> ModelNodeConfigurationValue:`

- **Line 89**: Function Return Any
  - Context: Function 'to_python_value' returns Any
  - Code: `def to_python_value(self) -> Any:`

- **Line 89**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `def to_python_value(self) -> Any:`

- **Line 113**: Function Return Any
  - Context: Function 'as_numeric' returns Any
  - Code: `def as_numeric(self) -> Any:`

- **Line 113**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `def as_numeric(self) -> Any:`

### File: /src/omnibase_core/types/typed_dict_collection_kwargs.py
**Violations**: 3

- **Line 23**: Variable Annotation Any
  - Context: Variable 'items' annotated with Any
  - Code: `items: list[Any]  # Don't import BaseModel from types - use Any`

- **Line 23**: Generic Any Usage
  - Context: Generic type containing Any
  - Code: `items: list[Any]  # Don't import BaseModel from types - use Any`

- **Line 23**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `items: list[Any]  # Don't import BaseModel from types - use Any`

### File: /src/omnibase_core/types/typed_dict_factory_kwargs.py
**Violations**: 2

- **Line 22**: Variable Annotation Any
  - Context: Variable 'data' annotated with Any
  - Code: `data: Any  # Don't import models from types - use Any for generic data`

- **Line 22**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `data: Any  # Don't import models from types - use Any for generic data`

### File: /src/omnibase_core/types/typed_dict_node_configuration_summary.py
**Violations**: 8

- **Line 15**: Variable Annotation Any
  - Context: Variable 'execution' annotated with Any
  - Code: `execution: Any  # Don't import model types from types directory`

- **Line 15**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `execution: Any  # Don't import model types from types directory`

- **Line 16**: Variable Annotation Any
  - Context: Variable 'resources' annotated with Any
  - Code: `resources: Any`

- **Line 16**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `resources: Any`

- **Line 17**: Variable Annotation Any
  - Context: Variable 'features' annotated with Any
  - Code: `features: Any`

- **Line 17**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `features: Any`

- **Line 18**: Variable Annotation Any
  - Context: Variable 'connection' annotated with Any
  - Code: `connection: Any`

- **Line 18**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `connection: Any`

### File: /src/omnibase_core/types/typed_dict_result_factory_kwargs.py
**Violations**: 2

- **Line 18**: Variable Annotation Any
  - Context: Variable 'data' annotated with Any
  - Code: `data: Any  # Don't import models from types - use Any for generic data`

- **Line 18**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `data: Any  # Don't import models from types - use Any for generic data`

### File: /src/omnibase_core/types/typed_dict_structured_definitions.py
**Violations**: 2

- **Line 15**: Function Parameter Any
  - Context: Parameter 'value' annotated with Any
  - Code: `def _parse_datetime(value: Any) -> datetime:`

- **Line 15**: Direct Any Usage
  - Context: Identifier 'Any' used
  - Code: `def _parse_datetime(value: Any) -> datetime:`

## Remediation Guidance

### Any Type Replacement Strategies

1. **Direct Any Usage**: Replace with specific types
   ```python
   # ❌ Prohibited
   param: Any

   # ✅ ONEX Compliant
   param: ModelSchemaValue | str | int
   ```

2. **Generic Any Usage**: Use specific generic types
   ```python
   # ❌ Prohibited
   data: Dict[str, Any]

   # ✅ ONEX Compliant
   data: Dict[str, ModelSchemaValue]
   ```

3. **Function Signatures**: Specify exact parameter and return types
   ```python
   # ❌ Prohibited
   def process(data: Any) -> Any:

   # ✅ ONEX Compliant
   def process(data: ModelContractData) -> ModelProcessingResult:
   ```
