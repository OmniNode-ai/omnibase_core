# Files Requiring Manual Fix

These 15 files have parse errors after running the string version fixer. They need manual review and correction.

## Parse Errors

### Mixins (3 files)
1. **src/omnibase_core/mixins/mixin_yaml_serialization.py**
   - Line 53: `serialize_pydantic_model_to_yaml,`
   - Issue: Orphaned import statement or incorrect indentation

2. **src/omnibase_core/mixins/mixin_service_registry.py**
   - Line 168: `ModelEventEnvelope,`
   - Issue: Orphaned import statement or incorrect indentation

3. **src/omnibase_core/mixins/mixin_request_response_introspection.py**
   - Line 422: `ModelEventEnvelope,`
   - Issue: Orphaned import statement or incorrect indentation

### Models (12 files)

#### Common Module (2 files)
4. **src/omnibase_core/models/common/model_schema_value.py**
   - Line 317: Indentation error - unindent does not match any outer indentation level
   - Issue: Indentation mismatch

5. **src/omnibase_core/models/common/model_value_container.py**
   - Line 34: `ProtocolModelValidatable as ModelProtocolValidatable,`
   - Issue: Orphaned import statement or incorrect indentation

#### Container Module (1 file)
6. **src/omnibase_core/models/container/model_workflow_coordinator.py**
   - Line 82: `emit_log_event_sync as emit_log_event,`
   - Issue: Orphaned import statement or incorrect indentation

#### Contracts Module (3 files)
7. **src/omnibase_core/models/contracts/model_compensation_plan.py**
   - Line 200: Indentation error - unindent does not match any outer indentation level
   - Issue: Indentation mismatch

8. **src/omnibase_core/models/contracts/model_contract_compute.py**
   - Line 278: `ModelValidationRulesConverter,`
   - Issue: Orphaned import statement or incorrect indentation

9. **src/omnibase_core/models/contracts/model_dependency.py**
   - Line 115: Indentation error - unindent does not match any outer indentation level
   - Issue: Indentation mismatch

#### Core Module (5 files)
10. **src/omnibase_core/models/core/model_environment.py**
    - Line 277: `ModelResourceLimits,`
    - Issue: Orphaned import statement or incorrect indentation

11. **src/omnibase_core/models/core/model_node_announce_metadata.py**
    - Line 94: Indentation error - unindent does not match any outer indentation level
    - Issue: Indentation mismatch

12. **src/omnibase_core/models/core/model_node_introspection.py**
    - Line 115: `ModelNodeIntrospectionResponse,`
    - Issue: Orphaned import statement or incorrect indentation

13. **src/omnibase_core/models/core/model_onex_reply_class.py**
    - Line 19: `from omnibase_core.errors.model_onex_error import ModelOnexError`
    - Issue: Invalid import or parse error

14. **src/omnibase_core/models/core/model_version_manifest_class.py**
    - Line 15: `from omnibase_core.models.service.model_node_service_config import ModelVersionFile`
    - Issue: Invalid import or parse error

#### Metadata Module (1 file)
15. **src/omnibase_core/models/metadata/model_generic_metadata.py**
    - Line 33: `from pydantic import BaseModel, Field, field_validator`
    - Issue: Invalid import or parse error

## Common Patterns

Most errors fall into these categories:

### 1. Orphaned Import Statements
- Pattern: Import statement with trailing comma but no opening parenthesis
- Example:
  ```python
  # Wrong:
      ModelEventEnvelope,
  )

  # Should be:
  from module import ModelEventEnvelope
  ```

### 2. Indentation Mismatches
- Pattern: Unindent that doesn't match any outer indentation level
- Usually caused by inconsistent spacing/tabs
- Fix: Ensure consistent indentation (4 spaces per level)

### 3. Invalid Import Paths
- Pattern: Import from non-existent module or incorrect path
- Fix: Verify import path and module existence

## Fix Strategy

For each file:
1. Open file and navigate to the error line
2. Check for orphaned import statements
3. Verify indentation consistency
4. Ensure import paths are valid
5. Run `poetry run black <file>` to verify syntax
6. Run `poetry run mypy <file>` to check types

## Batch Check Command

```bash
# Check all files for syntax errors
for file in \
  src/omnibase_core/mixins/mixin_yaml_serialization.py \
  src/omnibase_core/mixins/mixin_service_registry.py \
  src/omnibase_core/mixins/mixin_request_response_introspection.py \
  src/omnibase_core/models/common/model_schema_value.py \
  src/omnibase_core/models/common/model_value_container.py \
  src/omnibase_core/models/container/model_workflow_coordinator.py \
  src/omnibase_core/models/contracts/model_compensation_plan.py \
  src/omnibase_core/models/contracts/model_contract_compute.py \
  src/omnibase_core/models/contracts/model_dependency.py \
  src/omnibase_core/models/core/model_environment.py \
  src/omnibase_core/models/core/model_node_announce_metadata.py \
  src/omnibase_core/models/core/model_node_introspection.py \
  src/omnibase_core/models/core/model_onex_reply_class.py \
  src/omnibase_core/models/core/model_version_manifest_class.py \
  src/omnibase_core/models/metadata/model_generic_metadata.py
do
  echo "Checking: $file"
  python -m py_compile "$file" 2>&1 | head -3
done
```
