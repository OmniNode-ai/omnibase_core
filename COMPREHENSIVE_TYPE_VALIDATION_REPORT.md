# ONEX Type System Comprehensive Validation Report
## Zero Tolerance Type Safety Enforcement Results

### Validation Summary
- **Files Scanned**: 166
- **Files with Violations**: 48
- **Total Violations**: 348

### Violation Breakdown by Severity
- **CRITICAL**: 334 (Any type violations, must fix immediately)
- **HIGH**: 14 (Convention violations, should fix)
- **MEDIUM**: 0 (Code quality issues, recommended to fix)
- **LOW**: 0 (Minor issues, optional fixes)

### **Status**: ❌ VIOLATIONS DETECTED

## 🚨 CRITICAL Violations (Zero Tolerance - Must Fix)

Found 334 critical violations that MUST be eliminated:

### File: /src/omnibase_core/models/contracts/model_fast_imports.py
**Violations**: 3

- **Line 201**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def create_compute_contract(**kwargs: Any) -> "ModelContractCompute":`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 210**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def create_effect_contract(**kwargs: Any) -> "ModelContractEffect":`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 219**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def create_base_contract(**kwargs: Any) -> "ModelContractBase":`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_configuration_base.py
**Violations**: 10

- **Line 125**: Function Return Any (CRITICAL)
  - **Issue**: Function 'create_empty' returns Any
  - **Code**: `def create_empty(cls, name: str) -> ModelConfigurationBase[Any]:`
  - **Fix**: Specify exact return type for 'create_empty': use specific return type instead of Any

- **Line 125**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def create_empty(cls, name: str) -> ModelConfigurationBase[Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 125**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def create_empty(cls, name: str) -> ModelConfigurationBase[Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 135**: Function Return Any (CRITICAL)
  - **Issue**: Function 'create_disabled' returns Any
  - **Code**: `def create_disabled(cls, name: str) -> ModelConfigurationBase[Any]:`
  - **Fix**: Specify exact return type for 'create_disabled': use specific return type instead of Any

- **Line 135**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def create_disabled(cls, name: str) -> ModelConfigurationBase[Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 135**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def create_disabled(cls, name: str) -> ModelConfigurationBase[Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 145**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 145**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 145**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 149**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_container.py
**Violations**: 4

- **Line 304**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 314**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 314**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 314**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_custom_fields_accessor.py
**Violations**: 28

- **Line 36**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `list_fields: Dict[str, List[Any]] = Field(default_factory=dict)`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 36**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `list_fields: Dict[str, List[Any]] = Field(default_factory=dict)`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 36**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `list_fields: Dict[str, List[Any]] = Field(default_factory=dict)`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 50**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'values' uses Any type
  - **Code**: `def validate_and_distribute_fields(cls, values: Any) -> Dict[str, Any]:`
  - **Fix**: Specify exact type for parameter 'values': use str | int | ModelSchemaValue

- **Line 50**: Function Return Any (CRITICAL)
  - **Issue**: Function 'validate_and_distribute_fields' returns Any
  - **Code**: `def validate_and_distribute_fields(cls, values: Any) -> Dict[str, Any]:`
  - **Fix**: Specify exact return type for 'validate_and_distribute_fields': use specific return type instead of Any

- **Line 50**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def validate_and_distribute_fields(cls, values: Any) -> Dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 50**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def validate_and_distribute_fields(cls, values: Any) -> Dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 50**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def validate_and_distribute_fields(cls, values: Any) -> Dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 140**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'default' uses Any type
  - **Code**: `def get_field(self, key: str, default: Any = None) -> Any:`
  - **Fix**: Specify exact type for parameter 'default': use str | int | ModelSchemaValue

- **Line 140**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_field' returns Any
  - **Code**: `def get_field(self, key: str, default: Any = None) -> Any:`
  - **Fix**: Specify exact return type for 'get_field': use specific return type instead of Any

- **Line 140**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_field(self, key: str, default: Any = None) -> Any:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 140**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_field(self, key: str, default: Any = None) -> Any:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 213**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_list' returns Any
  - **Code**: `def get_list(self, key: str, default: List[Any] | None = None) -> List[Any]:`
  - **Fix**: Specify exact return type for 'get_list': use specific return type instead of Any

- **Line 213**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_list(self, key: str, default: List[Any] | None = None) -> List[Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 213**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_list(self, key: str, default: List[Any] | None = None) -> List[Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 213**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_list(self, key: str, default: List[Any] | None = None) -> List[Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 213**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_list(self, key: str, default: List[Any] | None = None) -> List[Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 379**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_fields_by_type' returns Any
  - **Code**: `def get_fields_by_type(self, field_type: str) -> Dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_fields_by_type': use specific return type instead of Any

- **Line 379**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_fields_by_type(self, field_type: str) -> Dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 379**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_fields_by_type(self, field_type: str) -> Dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 439**: Function Return Any (CRITICAL)
  - **Issue**: Function 'model_dump' returns Any
  - **Code**: `def model_dump(self, exclude_none: bool = False, **kwargs: Any) -> Dict[str, Any]:`
  - **Fix**: Specify exact return type for 'model_dump': use specific return type instead of Any

- **Line 439**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def model_dump(self, exclude_none: bool = False, **kwargs: Any) -> Dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 439**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def model_dump(self, exclude_none: bool = False, **kwargs: Any) -> Dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 439**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def model_dump(self, exclude_none: bool = False, **kwargs: Any) -> Dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 522**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 532**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 532**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 532**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_custom_properties.py
**Violations**: 4

- **Line 267**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 277**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 277**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 277**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_field_accessor.py
**Violations**: 4

- **Line 180**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 190**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 190**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 190**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_generic_collection_summary.py
**Violations**: 4

- **Line 59**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 69**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 69**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 69**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_generic_factory.py
**Violations**: 4

- **Line 214**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 224**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 224**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 224**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_item_summary.py
**Violations**: 4

- **Line 106**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 116**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 116**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 116**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_result_accessor.py
**Violations**: 6

- **Line 67**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 77**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 80**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `result: dict[str, Any] = {`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 80**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `result: dict[str, Any] = {`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 77**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 77**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_typed_accessor.py
**Violations**: 6

- **Line 46**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 56**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 59**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `result: dict[str, Any] = {`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 59**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `result: dict[str, Any] = {`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 56**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 56**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_typed_configuration.py
**Violations**: 4

- **Line 77**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 87**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 87**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 87**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/core/model_validation_error_factory.py
**Violations**: 12

- **Line 50**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 50**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 65**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 65**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 80**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 80**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 95**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 95**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `filtered_kwargs: dict[str, Any] = {`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 109**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def configure(self, **kwargs: Any) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 119**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 119**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 119**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_deprecation_info.py
**Violations**: 9

- **Line 135**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 135**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 135**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 148**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 148**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 148**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 158**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 158**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 158**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_documentation.py
**Violations**: 9

- **Line 134**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 134**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 134**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 147**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 147**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 147**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 157**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 157**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 157**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_node.py
**Violations**: 9

- **Line 302**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 302**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 302**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 315**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 315**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 315**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 325**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 325**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 325**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_node_core.py
**Violations**: 9

- **Line 209**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 209**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 209**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 222**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 222**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 222**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 232**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 232**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 232**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_node_metadata.py
**Violations**: 9

- **Line 383**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 383**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 383**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 396**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 396**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 396**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 406**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 406**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 406**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_node_performance.py
**Violations**: 9

- **Line 243**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 243**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 243**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 256**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 256**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 256**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 266**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 266**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 266**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_node_summary.py
**Violations**: 9

- **Line 237**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 237**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 237**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 250**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 250**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 250**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 260**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 260**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 260**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_function_relationships.py
**Violations**: 9

- **Line 167**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 167**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 167**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 180**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 180**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 180**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 190**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 190**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 190**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_capabilities_info.py
**Violations**: 9

- **Line 167**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 167**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 167**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 180**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 180**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 180**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 190**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 190**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 190**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_capabilities_summary.py
**Violations**: 9

- **Line 70**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 70**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 70**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 83**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 83**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 83**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 93**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 93**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 93**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_capability.py
**Violations**: 9

- **Line 326**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 326**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 326**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 339**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 339**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 339**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 349**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 349**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 349**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_configuration.py
**Violations**: 9

- **Line 314**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 314**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 314**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 327**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 327**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 327**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 337**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 337**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 337**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_configuration_summary.py
**Violations**: 9

- **Line 90**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 90**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 90**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 103**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 103**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 103**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 113**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 113**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 113**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_configuration_value.py
**Violations**: 2

- **Line 72**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'v' uses Any type
  - **Code**: `def get_discriminator_value(v: Any) -> str:`
  - **Fix**: Specify exact type for parameter 'v': use str | int | ModelSchemaValue

- **Line 72**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_discriminator_value(v: Any) -> str:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_connection_settings.py
**Violations**: 9

- **Line 155**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 155**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 155**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 168**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 168**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 168**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 178**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 178**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 178**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_core_info.py
**Violations**: 9

- **Line 172**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 172**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 172**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 185**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 185**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 185**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 195**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 195**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 195**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_core_info_summary.py
**Violations**: 9

- **Line 74**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 74**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 74**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 87**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 87**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 87**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 97**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 97**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 97**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_core_metadata.py
**Violations**: 11

- **Line 130**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 130**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 130**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 143**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 143**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 143**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 153**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 153**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 153**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 206**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'v' uses Any type
  - **Code**: `def get_node_status_discriminator(v: Any) -> str:`
  - **Fix**: Specify exact type for parameter 'v': use str | int | ModelSchemaValue

- **Line 206**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_node_status_discriminator(v: Any) -> str:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_execution_settings.py
**Violations**: 9

- **Line 103**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 103**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 103**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 116**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 116**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 116**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 126**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 126**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 126**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_feature_flags.py
**Violations**: 9

- **Line 134**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 134**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 134**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 147**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 147**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 147**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 157**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 157**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 157**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_information.py
**Violations**: 9

- **Line 338**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 338**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 338**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 351**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 351**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 351**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 361**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 361**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 361**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_information_summary.py
**Violations**: 9

- **Line 78**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 78**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 78**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 91**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 91**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 91**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 101**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 101**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 101**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_metadata_info.py
**Violations**: 12

- **Line 355**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'node_info' uses Any type
  - **Code**: `def from_node_info(cls, node_info: dict[str, Any]) -> ModelNodeMetadataInfo:`
  - **Fix**: Specify exact type for parameter 'node_info': use str | int | ModelSchemaValue

- **Line 355**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def from_node_info(cls, node_info: dict[str, Any]) -> ModelNodeMetadataInfo:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 355**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def from_node_info(cls, node_info: dict[str, Any]) -> ModelNodeMetadataInfo:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 409**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 409**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 409**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 422**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 422**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 422**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 432**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 432**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 432**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_organization_metadata.py
**Violations**: 9

- **Line 174**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 174**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 174**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 187**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 187**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 187**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 197**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 197**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 197**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_performance_metrics.py
**Violations**: 9

- **Line 136**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 136**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 136**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 149**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 149**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 149**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 159**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 159**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 159**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_resource_limits.py
**Violations**: 9

- **Line 123**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 123**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 123**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 136**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 136**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 136**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 146**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 146**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 146**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

### File: /src/omnibase_core/models/nodes/model_node_type.py
**Violations**: 9

- **Line 530**: Function Return Any (CRITICAL)
  - **Issue**: Function 'get_metadata' returns Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'get_metadata': use specific return type instead of Any

- **Line 530**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 530**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def get_metadata(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 543**: Function Parameter Any (CRITICAL)
  - **Issue**: Parameter 'metadata' uses Any type
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Specify exact type for parameter 'metadata': use str | int | ModelSchemaValue

- **Line 543**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 543**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def set_metadata(self, metadata: dict[str, Any]) -> bool:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

- **Line 553**: Function Return Any (CRITICAL)
  - **Issue**: Function 'serialize' returns Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Specify exact return type for 'serialize': use specific return type instead of Any

- **Line 553**: Generic Any Usage (CRITICAL)
  - **Issue**: Generic type contains Any
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace with specific types: Dict[str, ModelSchemaValue] instead of Dict[str, Any]

- **Line 553**: Any Type Usage (CRITICAL)
  - **Issue**: Direct Any usage: 'Any'
  - **Code**: `def serialize(self) -> dict[str, Any]:`
  - **Fix**: Replace Any with specific types: str | int | ModelSchemaValue

## ⚠️  HIGH Priority Violations (Should Fix)

Found 14 high priority violations:

### File: /src/omnibase_core/models/contracts/model_fast_imports.py
**Violations**: 1

- **Line 30**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'PerformanceMetrics' doesn't follow TypedDict* naming pattern
  - **Code**: `class PerformanceMetrics(TypedDict):`
  - **Fix**: Rename 'PerformanceMetrics' to 'TypedDictPerformanceMetrics' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_function_deprecation_info.py
**Violations**: 1

- **Line 24**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelDeprecationSummary' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelDeprecationSummary(TypedDict):`
  - **Fix**: Rename 'ModelDeprecationSummary' to 'TypedDictModelDeprecationSummary' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_function_node_metadata.py
**Violations**: 2

- **Line 40**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelDocumentationSummaryFiltered' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelDocumentationSummaryFiltered(TypedDict):`
  - **Fix**: Rename 'ModelDocumentationSummaryFiltered' to 'TypedDictModelDocumentationSummaryFiltered' to follow ONEX conventions

- **Line 50**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelFunctionMetadataSummary' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelFunctionMetadataSummary(TypedDict):`
  - **Fix**: Rename 'ModelFunctionMetadataSummary' to 'TypedDictModelFunctionMetadataSummary' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_node_core_info.py
**Violations**: 1

- **Line 29**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelCoreSummary' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelCoreSummary(TypedDict):`
  - **Fix**: Rename 'ModelCoreSummary' to 'TypedDictModelCoreSummary' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_node_performance_metrics.py
**Violations**: 1

- **Line 23**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelPerformanceSummary' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelPerformanceSummary(TypedDict):`
  - **Fix**: Rename 'ModelPerformanceSummary' to 'TypedDictModelPerformanceSummary' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_function_documentation_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelFunctionDocumentationSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelFunctionDocumentationSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelFunctionDocumentationSummaryType' to 'TypedDictModelFunctionDocumentationSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_function_relationships_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelFunctionRelationshipsSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelFunctionRelationshipsSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelFunctionRelationshipsSummaryType' to 'TypedDictModelFunctionRelationshipsSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_node_capabilities_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelNodeCapabilitiesSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelNodeCapabilitiesSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelNodeCapabilitiesSummaryType' to 'TypedDictModelNodeCapabilitiesSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_node_connection_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelNodeConnectionSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelNodeConnectionSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelNodeConnectionSummaryType' to 'TypedDictModelNodeConnectionSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_node_execution_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelNodeExecutionSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelNodeExecutionSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelNodeExecutionSummaryType' to 'TypedDictModelNodeExecutionSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_node_feature_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelNodeFeatureSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelNodeFeatureSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelNodeFeatureSummaryType' to 'TypedDictModelNodeFeatureSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_node_metadata_summary.py
**Violations**: 1

- **Line 15**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelNodeMetadataSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelNodeMetadataSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelNodeMetadataSummaryType' to 'TypedDictModelNodeMetadataSummaryType' to follow ONEX conventions

### File: /src/omnibase_core/models/nodes/model_types_node_resource_summary.py
**Violations**: 1

- **Line 12**: TypedDict Naming Convention (HIGH)
  - **Issue**: TypedDict class 'ModelNodeResourceSummaryType' doesn't follow TypedDict* naming pattern
  - **Code**: `class ModelNodeResourceSummaryType(TypedDict):`
  - **Fix**: Rename 'ModelNodeResourceSummaryType' to 'TypedDictModelNodeResourceSummaryType' to follow ONEX conventions

## 🛠️  Comprehensive Remediation Strategy

### Phase 1: CRITICAL - Any Type Elimination (Zero Tolerance)

**Every Any type must be replaced with specific types:**

```python
# ❌ CRITICAL VIOLATIONS
param: Any
def func() -> Any:
data: Dict[str, Any]
items: List[Any]

# ✅ ONEX COMPLIANT
param: str | int | ModelSchemaValue
def func() -> ModelProcessingResult:
data: Dict[str, ModelSchemaValue]
items: List[ModelSchemaValue]
```

### Phase 2: HIGH - Convention Compliance

**TypedDict Naming**: All TypedDict classes must start with 'TypedDict'
```python
# ❌ Wrong
class ConfigSummary(TypedDict):

# ✅ Correct
class TypedDictConfigSummary(TypedDict):
```

### Phase 3: MEDIUM - Code Quality Improvements

**Union Optimization**: Large unions may indicate lazy typing
```python
# ❌ Potential lazy typing
Union[str, int, float, bool, dict, list]

# ✅ Better approach
Protocol or specific model class
```

### Priority Order
1. Fix 334 CRITICAL violations first (Any types)
2. Address 14 HIGH violations (conventions)
3. Consider 0 MEDIUM violations (quality)
