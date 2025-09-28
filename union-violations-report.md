# Union Type Legitimacy Validation Report

Generated: 2025-09-28T08:52:46.149671
Validation Approach: AST-based Legitimacy Analysis

## Executive Summary

- **Files Scanned**: 510
- **Total Unions**: 829
- **Legitimate Unions**: 821
- **Invalid Unions**: 8
- **Legitimacy Ratio**: 99.0%
- **Issues Found**: 16

## Pattern Statistics

### ✅ Legitimate Patterns

- **optional**: 796
- **error_handling**: 8
- **type_narrowing**: 2
- **simple_union**: 15

### ❌ Invalid Patterns

- **unclassified_complex**: 8

## Issues Found

- scripts/validation/validate-no-backward-compatibility.py: Line 194: Complex union pattern needs review - Union[re.DOTALL, re.IGNORECASE, re.MULTILINE]
- scripts/validation/validate-no-backward-compatibility.py: Line 194: Suggestion - Consider using discriminated union or proper model
- scripts/validation/validate-no-backward-compatibility.py: Line 229: Complex union pattern needs review - Union[re.DOTALL, re.IGNORECASE, re.MULTILINE]
- scripts/validation/validate-no-backward-compatibility.py: Line 229: Suggestion - Consider using discriminated union or proper model
- tests/unit/enums/test_enum_filter_type.py: Line 167: Complex union pattern needs review - Union[collection_filters, data_type_filters, operational_filters]
- tests/unit/enums/test_enum_filter_type.py: Line 167: Suggestion - Consider using discriminated union or proper model
- tests/unit/enums/test_enum_registry_status.py: Line 185: Complex union pattern needs review - Union[critical_statuses, good_statuses, warning_statuses]
- tests/unit/enums/test_enum_registry_status.py: Line 185: Suggestion - Consider using discriminated union or proper model
- tests/unit/enums/test_enum_scenario_status.py: Line 171: Complex union pattern needs review - Union[active_states, final_states, initial_states, pending_states]
- tests/unit/enums/test_enum_scenario_status.py: Line 171: Suggestion - Consider using discriminated union or proper model
- tests/unit/enums/test_enum_scenario_status.py: Line 171: Complex union pattern needs review - Union[active_states, initial_states, pending_states]
- tests/unit/enums/test_enum_scenario_status.py: Line 171: Suggestion - Consider using discriminated union or proper model
- tests/unit/enums/test_enum_scenario_status.py: Line 197: Complex union pattern needs review - Union[failure_outcomes, neutral_outcomes, non_final_states, success_outcomes]
- tests/unit/enums/test_enum_scenario_status.py: Line 197: Suggestion - Consider using discriminated union or proper model
- tests/unit/enums/test_enum_scenario_status.py: Line 197: Complex union pattern needs review - Union[failure_outcomes, neutral_outcomes, success_outcomes]
- tests/unit/enums/test_enum_scenario_status.py: Line 197: Suggestion - Consider using discriminated union or proper model

## Legitimacy Criteria

### ✅ Legitimate Pattern Types

- optional: T | None patterns
- result_monadic: Result[T, E] error handling
- discriminated: Unions with Literal discriminators
- model_schema_value: Proper ModelSchemaValue usage
- error_handling: Exception handling patterns
- type_narrowing: Related type narrowing (str | Path)
- simple_union: Small coherent unions

### ❌ Invalid Pattern Types

- primitive_soup: 3+ primitive types without semantic meaning
- any_contaminated: Unions containing Any types
- overly_broad: 5+ types or mixed primitive/complex without semantics
- semantic_mismatch: Unrelated type combinations
- unclassified_complex: Complex patterns needing review
