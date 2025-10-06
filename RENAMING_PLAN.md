# Repository Structure Renaming Plan

## Files to rename (15 total):

### Container models:
- `src/omnibase_core/models/container/base_model_onex_container.py` → `src/omnibase_core/models/container/model_base_model_onex_container.py`

### Metadata models:
- `src/omnibase_core/models/metadata/typed_dict_analytics_summary_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_analytics_summary_data.py`
- `src/omnibase_core/models/metadata/typed_dict_categorization_update_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_categorization_update_data.py`
- `src/omnibase_core/models/metadata/typed_dict_core_analytics.py` → `src/omnibase_core/models/metadata/model_typed_dict_core_analytics.py`
- `src/omnibase_core/models/metadata/typed_dict_core_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_core_data.py`
- `src/omnibase_core/models/metadata/typed_dict_error_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_error_data.py`
- `src/omnibase_core/models/metadata/typed_dict_node_core_update_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_node_core_update_data.py`
- `src/omnibase_core/models/metadata/typed_dict_node_core.py` → `src/omnibase_core/models/metadata/model_typed_dict_node_core.py`
- `src/omnibase_core/models/metadata/typed_dict_node_info_summary_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_node_info_summary_data.py`
- `src/omnibase_core/models/metadata/typed_dict_performance_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_performance_data.py`
- `src/omnibase_core/models/metadata/typed_dict_performance_update_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_performance_update_data.py`
- `src/omnibase_core/models/metadata/typed_dict_quality_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_quality_data.py`
- `src/omnibase_core/models/metadata/typed_dict_quality_update_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_quality_update_data.py`
- `src/omnibase_core/models/metadata/typed_dict_timestamp_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_timestamp_data.py`
- `src/omnibase_core/models/metadata/typed_dict_timestamp_update_data.py` → `src/omnibase_core/models/metadata/model_typed_dict_timestamp_update_data.py`

## Strategy:
1. Use git mv to rename files (preserves git history)
2. Search for all import statements referencing old filenames
3. Update import statements across the entire codebase
4. Test that everything still works
