# Pydantic Error Fixing Scripts

Automated tools for analyzing and fixing Pydantic-related mypy call-arg errors in the omnibase_core project.

## Overview

This suite of scripts helps diagnose and fix common Pydantic v2 compatibility issues that manifest as mypy `call-arg` errors. The scripts are designed to work together as a complete workflow.

### Results Summary

**Initial State**: 821 call-arg errors across 86 files

**After Field Syntax Fixes**: 164 errors remaining (80% reduction, 657 errors fixed)

**Fixes Applied**: 2,113 Field() syntax updates across 1,320 files

## Available Scripts

### 1. `analyze_pydantic_errors.py` - Error Analysis & Categorization

Parses mypy output to identify and categorize all Pydantic-related errors.

#### Usage

```bash
# Run fresh mypy analysis
poetry run python scripts/analyze_pydantic_errors.py

# Use cached errors (faster)
poetry run python scripts/analyze_pydantic_errors.py --no-run-mypy

# Custom output location
poetry run python scripts/analyze_pydantic_errors.py --output my_report.json
```

#### Output

- **Console Report**: Statistics, top error patterns, recommendations
- **JSON Report**: Detailed error list with file, line, type, model, field info

#### Example Output

```text
================================================================================
PYDANTIC CALL-ARG ERROR ANALYSIS REPORT
================================================================================

Total Errors: 821
Unique Files: 86

--- Error Types ---
  missing_argument: 775
  unexpected_argument: 45
  too_many_arguments: 1

--- Top 15 Models with Most Errors ---
  ModelHealthCheckConfig: 35
  ModelPolicySeverity: 29
  ModelAuditEntry: 22
  ...
```

### 2. `fix_pydantic_field_syntax.py` - Field Definition Fixer

Fixes Pydantic 2.x Field() syntax issues automatically.

#### What It Fixes

Converts Pydantic v1 Field syntax to v2:

```python
# Before (Pydantic v1 syntax)
field: str | None = Field(None, description="...")

# After (Pydantic v2 syntax)
field: str | None = Field(default=None, description="...")
```

Also handles:
- `Field([], ...)` → `Field(default=[], ...)`
- `Field({}, ...)` → `Field(default={}, ...)`
- `Field("", ...)` → `Field(default="", ...)`
- Multi-line Field() definitions

#### Usage

```bash
# Dry run - preview changes
poetry run python scripts/fix_pydantic_field_syntax.py --all --dry-run

# Fix specific file
poetry run python scripts/fix_pydantic_field_syntax.py --file src/path/to/file.py

# Fix all model files with backups
poetry run python scripts/fix_pydantic_field_syntax.py --all --backup

# Fix all model files (no backups)
poetry run python scripts/fix_pydantic_field_syntax.py --all
```

#### Options

- `--file PATH`: Fix a specific file
- `--all`: Fix all Python files in models directory
- `--dry-run`: Preview changes without modifying files
- `--backup`: Create .bak backups before modifying files
- `--models-dir PATH`: Custom models directory (default: src/omnibase_core/models)

#### Example Output

```text
model_health_check_config.py:
  Line 72: expected_response_body
    Before: expected_response_body: str | None = Field(
        None,
    After:  expected_response_body: str | None = Field(
        default=None,

================================================================================
SUMMARY:
  Files processed: 1320
  Total fixes: 2113
  Files have been updated

  Fix breakdown:
    multiline_none_to_default: 1959
    value_to_default: 154
================================================================================
```

### 3. `fix_pydantic_missing_fields.py` - Constructor Call Fixer

**Status**: Experimental - Use with caution

Adds missing optional fields to Pydantic model instantiation calls using AST analysis.

#### What It Does

Analyzes model definitions to extract field information, then adds missing optional fields to constructor calls with appropriate defaults.

```python
# Before
result = ModelHealthMetric(
    metric_name="cpu",
    current_value=75.0,
    unit="%",
)

# After
result = ModelHealthMetric(
    metric_name="cpu",
    current_value=75.0,
    unit="%",
    min_value=None,
    max_value=None,
    average_value=None,
)
```

#### Usage

```bash
# IMPORTANT: Run analyzer first to generate error report
poetry run python scripts/analyze_pydantic_errors.py

# Dry run - preview changes
poetry run python scripts/fix_pydantic_missing_fields.py --all --dry-run

# Fix specific file
poetry run python scripts/fix_pydantic_missing_fields.py --file src/path/to/file.py

# Fix all files with errors (with backups)
poetry run python scripts/fix_pydantic_missing_fields.py --all --backup
```

#### Options

- `--file PATH`: Fix a specific file
- `--all`: Fix all files with missing argument errors
- `--dry-run`: Preview changes without modifying files
- `--backup`: Create .bak backups before modifying files
- `--report PATH`: Error report JSON file (default: pydantic_errors_report.json)

#### Important Notes

⚠️ **This script is experimental and may require manual review of changes.**

- Only fixes `missing_argument` type errors
- Analyzes all models in `src/omnibase_core/models` to extract field definitions
- Uses AST parsing to understand model structure
- Generates conservative defaults (None for optional fields)
- May not handle complex default values correctly

**Recommendation**: Always use `--dry-run` first and review changes carefully.

## Complete Workflow

### Step 1: Analyze Current State

```bash
# Run analysis
poetry run python scripts/analyze_pydantic_errors.py

# Review the report
cat pydantic_errors_report.json
```

### Step 2: Fix Field Syntax (Safe, High-Impact)

```bash
# Dry run first to see what will change
poetry run python scripts/fix_pydantic_field_syntax.py --all --dry-run

# Apply fixes with backups
poetry run python scripts/fix_pydantic_field_syntax.py --all --backup

# Verify reduction in errors
poetry run mypy src/omnibase_core/ 2>&1 | grep "call-arg" | wc -l
```

### Step 3: Fix Missing Fields (Optional, Experimental)

```bash
# Generate fresh report after field syntax fixes
poetry run python scripts/analyze_pydantic_errors.py

# Preview fixes
poetry run python scripts/fix_pydantic_missing_fields.py --all --dry-run

# Apply carefully on specific files
poetry run python scripts/fix_pydantic_missing_fields.py --file src/path/to/file.py --backup
```

### Step 4: Verify Results

```bash
# Run mypy to see remaining errors
poetry run mypy src/omnibase_core/ 2>&1 | grep "call-arg"

# Run tests to ensure no regressions
poetry run pytest tests/
```

## Results from Initial Run

### Before Fixes

- **Total Errors**: 821
- **Unique Files**: 86
- **Error Types**:
  - missing_argument: 775 (94%)
  - unexpected_argument: 45 (5%)
  - too_many_arguments: 1 (<1%)

### After Field Syntax Fixes

- **Total Errors**: 164 (80% reduction)
- **Fixes Applied**: 2,113 Field() syntax updates
- **Files Modified**: 1,320

### Remaining Errors

The remaining 164 errors are primarily:

1. **Unexpected keyword arguments** (45 errors)
   - Incorrect parameter names in function/constructor calls
   - Renamed or deprecated parameters
   - Requires manual code review and fixing

2. **Missing required arguments** (119 errors)
   - Models with truly required fields not being provided
   - More complex fixes requiring domain knowledge
   - May indicate actual bugs or incomplete implementations

## Safety Features

All scripts include:

- **Dry-run mode**: Preview changes before applying
- **Backup creation**: Optional .bak file creation
- **Error handling**: Graceful failure with detailed error messages
- **Validation**: Pre-flight checks to ensure files exist
- **Reporting**: Detailed statistics and fix summaries

## Best Practices

1. **Always run analyzer first** to understand the scope
2. **Use dry-run mode** before applying any fixes
3. **Create backups** when running fixes on important files
4. **Test incrementally** - fix one file, test, then continue
5. **Review changes** using git diff before committing
6. **Run tests** after applying fixes to catch regressions

## Common Issues

### "Error report not found"

**Problem**: Running fix scripts before generating the error report

**Solution**:
```bash
poetry run python scripts/analyze_pydantic_errors.py
```

### "Model not found in analyzer"

**Problem**: The missing fields fixer can't find the model definition

**Solution**: Ensure the model file is in `src/omnibase_core/models/` and is a proper Pydantic BaseModel

### "No errors found for file"

**Problem**: The specified file has no errors in the report

**Solution**: Run the analyzer again to regenerate the report with current errors

## Performance

- **Analyzer**: ~5-10 seconds for full codebase mypy run
- **Field Syntax Fixer**: ~30-60 seconds for all files (1320+ files)
- **Missing Fields Fixer**: ~10-20 seconds per file (depending on complexity)

## Future Enhancements

Potential improvements:

1. **Parallel processing** for faster file processing
2. **Smart default generation** based on field type and usage patterns
3. **Integration with pre-commit hooks** for continuous validation
4. **Automatic test generation** for fixed code
5. **Git integration** for automatic commit creation

## Support

For issues or questions:

1. Check the error output - scripts provide detailed error messages
2. Use `--dry-run` to preview changes
3. Review this documentation for usage patterns
4. Check git diff to see what changed

## Contributing

When modifying these scripts:

1. Test on small files first
2. Add new fix patterns to the appropriate script
3. Update this README with new features
4. Run the full workflow to ensure no regressions

---

**Last Updated**: 2025-10-06
**Scripts Version**: 1.0.0
**Python Version**: 3.12
**Poetry**: Required for all commands
