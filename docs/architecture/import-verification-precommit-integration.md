# Import Verification Script Integration with Pre-commit Hooks

## Executive Summary

This document provides architectural guidance for integrating the import verification script with the existing pre-commit hook pipeline to catch import issues like the ModelSchemaValue import failure before code is committed.

## Problem Analysis

### Current Issue: ModelSchemaValue Import

**Root Cause**: The file `src/omnibase_core/models/core/model_error_context.py` imports from:
```python
from omnibase_core.models.core.model_schema_value import ModelSchemaValue
```

However, `ModelSchemaValue` only exists in `archived/src/omnibase_core/models/core/model_schema_value.py`, not in the active codebase. This import will fail at runtime but wasn't caught by existing validation.

### Why Existing Hooks Missed This

**Current Pre-commit Configuration Analysis**:

1. **MyPy Type Checking (lines 44-52)**:
   - Uses `--ignore-missing-imports` flag
   - Uses `--follow-imports=skip` flag
   - **Issue**: These flags suppress import resolution errors

2. **File Patterns**:
   - MyPy only runs on: `^src/omnibase_core/(core|model|enums|exceptions|decorators).*\.py$`
   - **Issue**: `models/core/` path matches but import resolution is skipped

3. **Validation Scripts**:
   - No existing script validates import paths
   - Focus on patterns, naming, structure - not import resolution

## Proposed Integration Architecture

### 1. Import Verification Hook Design

```yaml
# Addition to .pre-commit-config.yaml
- id: validate-import-resolution
  name: ONEX Import Resolution Validation
  entry: poetry run python scripts/validation/validate-import-paths.py
  language: system
  pass_filenames: true
  files: ^src/.*\.py$
  exclude: ^(tests/fixtures/validation/|archived/|work_tickets/)
  stages: [pre-commit]
  # Performance optimization
  args: [--fast-fail, --cache-imports]
```

### 2. Script Implementation Strategy

**Core Validation Logic**:
```python
# scripts/validation/validate-import-paths.py

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Set, Dict, List, Optional
import time

class ImportValidator:
    def __init__(self, project_root: Path, fast_fail: bool = False):
        self.project_root = project_root
        self.fast_fail = fast_fail
        self.import_cache: Dict[str, bool] = {}
        self.failed_imports: List[Dict[str, str]] = []

    def validate_file_imports(self, file_path: Path) -> bool:
        """Validate all imports in a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            imports = self._extract_imports(tree)

            for import_info in imports:
                if not self._validate_import(import_info, file_path):
                    if self.fast_fail:
                        return False

            return len(self.failed_imports) == 0

        except Exception as e:
            self.failed_imports.append({
                'file': str(file_path),
                'import': 'PARSE_ERROR',
                'error': str(e)
            })
            return False

    def _validate_import(self, import_info: Dict, source_file: Path) -> bool:
        """Validate a single import statement."""
        module_name = import_info['module']

        # Use cache for performance
        if module_name in self.import_cache:
            return self.import_cache[module_name]

        try:
            # Try to resolve the import
            if module_name.startswith('omnibase_core'):
                # Internal import - check file exists
                result = self._validate_internal_import(module_name, source_file)
            else:
                # External import - check if importable
                result = self._validate_external_import(module_name)

            self.import_cache[module_name] = result

            if not result:
                self.failed_imports.append({
                    'file': str(source_file),
                    'import': module_name,
                    'line': import_info.get('line', 0),
                    'error': 'Import resolution failed'
                })

            return result

        except Exception as e:
            self.import_cache[module_name] = False
            self.failed_imports.append({
                'file': str(source_file),
                'import': module_name,
                'line': import_info.get('line', 0),
                'error': str(e)
            })
            return False
```

### 3. Performance Optimization

**Caching Strategy**:
- Cache import resolution results across files
- Skip validation for known-good external packages
- Use file modification time to invalidate cache

**Selective Validation**:
```python
# Only validate modified files in pre-commit context
def get_modified_python_files() -> List[Path]:
    """Get list of Python files modified in current commit."""
    import subprocess

    try:
        # Get staged files
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True, text=True, check=True
        )

        files = []
        for line in result.stdout.strip().split('\n'):
            if line.endswith('.py') and line.startswith('src/'):
                files.append(Path(line))
        return files

    except subprocess.CalledProcessError:
        # Fallback: validate all Python files
        return list(Path('src').rglob('*.py'))
```

### 4. Integration with Existing Pipeline

**Hook Ordering in .pre-commit-config.yaml**:

```yaml
repos:
  # ... existing hooks ...

  - repo: local
    hooks:
      # PHASE 1: Fast syntax and import validation
      - id: validate-import-resolution
        name: ONEX Import Resolution Validation
        entry: poetry run python scripts/validation/validate-import-paths.py
        language: system
        pass_filenames: true
        files: ^src/.*\.py$
        exclude: ^(tests/fixtures/validation/|archived/)
        stages: [pre-commit]
        args: [--fast-fail, --cache-imports]

      # PHASE 2: Code formatting (existing)
      - id: black
        # ... existing black config ...

      # PHASE 3: Type checking (existing, but enhanced)
      - id: mypy-poetry
        name: MyPy Type Checking (via Poetry)
        entry: poetry run mypy
        language: system
        types: [python]
        # REMOVE --ignore-missing-imports for better validation
        args: [--show-error-codes, --no-strict-optional, --no-error-summary, --follow-imports=normal, --config-file=mypy.ini]
        files: ^src/omnibase_core/(core|model|enums|exceptions|decorators).*\.py$
        exclude: ^(tests/|archived/).*\.py$

      # PHASE 4: Pattern validation (existing)
      - id: validate-pydantic-patterns
        # ... existing config ...
```

### 5. Enhanced MyPy Configuration

**Update mypy.ini**:
```ini
[mypy]
python_version = 3.12
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# ENHANCED: Better import resolution
follow_imports = normal
ignore_missing_imports = false
warn_unreachable = true

# ENHANCED: Stricter checking
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_calls = true

# Project-specific overrides
[mypy-omnibase_spi.*]
ignore_missing_imports = true

[mypy-llama_index.*]
ignore_missing_imports = true

# Only ignore missing imports for specific external packages
[mypy-fastapi.*,uvicorn.*,redis.*,psycopg2.*]
ignore_missing_imports = true
```

## Implementation Phases

### Phase 1: Basic Import Validation (Week 1)

**Deliverables**:
1. Basic import validation script
2. Pre-commit hook integration
3. Fix existing broken imports (ModelSchemaValue issue)

**Script Features**:
- AST-based import extraction
- Internal import path validation
- Basic error reporting

### Phase 2: Performance Optimization (Week 2)

**Deliverables**:
1. Import result caching
2. Incremental validation (git diff integration)
3. Parallel processing for large codebases

**Performance Targets**:
- Validate 100 files in <5 seconds
- Cache hit rate >80% for repeated runs
- Memory usage <100MB

### Phase 3: Advanced Validation (Week 3)

**Deliverables**:
1. Circular import detection
2. Deprecated import warnings
3. Import organization recommendations

**Advanced Features**:
- Dependency graph analysis
- Import path optimization suggestions
- Integration with existing naming validation

## Script Implementation Details

### Core Import Extraction

```python
class ImportExtractor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'module': alias.name,
                'line': node.lineno,
                'alias': alias.asname
            })

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.imports.append({
                    'type': 'from_import',
                    'module': node.module,
                    'name': alias.name,
                    'line': node.lineno,
                    'alias': alias.asname,
                    'level': node.level  # Relative import level
                })
```

### Internal Import Validation

```python
def _validate_internal_import(self, module_name: str, source_file: Path) -> bool:
    """Validate internal omnibase_core imports."""

    # Convert module path to file path
    # omnibase_core.models.core.model_schema_value ->
    # src/omnibase_core/models/core/model_schema_value.py

    module_parts = module_name.split('.')
    if module_parts[0] != 'omnibase_core':
        return True  # Not our module

    # Build expected file path
    expected_path = self.project_root / 'src'
    for part in module_parts:
        expected_path = expected_path / part
    expected_path = expected_path.with_suffix('.py')

    # Check if file exists
    if expected_path.exists():
        return True

    # Check if it's a package (directory with __init__.py)
    if (expected_path.parent / '__init__.py').exists():
        return True

    # Check archived folder (should warn but not fail)
    archived_path = self.project_root / 'archived' / 'src'
    for part in module_parts:
        archived_path = archived_path / part
    archived_path = archived_path.with_suffix('.py')

    if archived_path.exists():
        # Warn about archived import
        print(f"WARNING: Importing from archived: {module_name}")
        return False

    return False
```

### Error Reporting

```python
def generate_report(self) -> str:
    """Generate human-readable validation report."""
    if not self.failed_imports:
        return "✅ All imports validated successfully"

    report = []
    report.append(f"❌ Found {len(self.failed_imports)} import issues:")
    report.append("")

    # Group by file
    by_file = {}
    for failure in self.failed_imports:
        file_path = failure['file']
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(failure)

    for file_path, failures in by_file.items():
        report.append(f"📁 {file_path}:")
        for failure in failures:
            line = failure.get('line', '?')
            import_name = failure['import']
            error = failure['error']
            report.append(f"  ❌ Line {line}: {import_name} - {error}")
        report.append("")

    return "\n".join(report)
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/validation/test_import_validation.py

def test_valid_internal_import():
    """Test validation of valid internal import."""
    validator = ImportValidator(project_root)

    # Create test file with valid import
    test_content = """
from omnibase_core.core.core_uuid_service import UUIDService
"""

    # Test validation
    result = validator.validate_content(test_content, Path("test.py"))
    assert result is True

def test_invalid_internal_import():
    """Test detection of invalid internal import."""
    validator = ImportValidator(project_root)

    # Create test file with invalid import
    test_content = """
from omnibase_core.models.core.model_schema_value import ModelSchemaValue
"""

    # Test validation
    result = validator.validate_content(test_content, Path("test.py"))
    assert result is False
    assert len(validator.failed_imports) == 1
```

### Integration Tests

```python
# tests/integration/validation/test_precommit_integration.py

def test_precommit_hook_execution():
    """Test that pre-commit hook executes successfully."""

    # Run the actual pre-commit hook
    result = subprocess.run([
        'poetry', 'run', 'python',
        'scripts/validation/validate-import-paths.py',
        'src/omnibase_core/models/core/model_error_context.py'
    ], capture_output=True, text=True)

    # Should detect the ModelSchemaValue import issue
    assert result.returncode != 0
    assert 'ModelSchemaValue' in result.stdout
```

## Performance Considerations

### Execution Time Analysis

**Current Pre-commit Hook Timing**:
- MyPy: ~15-30 seconds (with import resolution)
- Black: ~2-3 seconds
- Other validation scripts: ~5-10 seconds
- **Total**: ~25-45 seconds

**Import Validation Timing Goals**:
- Initial run: <10 seconds for full codebase
- Incremental run: <3 seconds for typical commits
- Cache warm-up: <5 seconds

### Memory Usage

**Optimization Strategies**:
1. **Lazy Loading**: Only load modules when needed
2. **Result Caching**: Cache import resolution results
3. **Process Pooling**: Validate files in parallel
4. **Memory Mapping**: Use file memory mapping for large files

### Cache Strategy

```python
class ImportCache:
    def __init__(self, cache_file: Path = Path('.import_cache.json')):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cached import results."""
        if self.cache_file.exists():
            try:
                import json
                with open(self.cache_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_import_result(self, module: str, file_mtime: float) -> Optional[bool]:
        """Get cached import result if still valid."""
        cache_entry = self.cache.get(module)
        if cache_entry and cache_entry['mtime'] >= file_mtime:
            return cache_entry['valid']
        return None

    def cache_import_result(self, module: str, valid: bool, file_mtime: float):
        """Cache import validation result."""
        self.cache[module] = {
            'valid': valid,
            'mtime': file_mtime,
            'timestamp': time.time()
        }
```

## Migration Strategy

### Phase 1: Fix Immediate Issues

**Step 1**: Fix the ModelSchemaValue import issue
```bash
# Option A: Move file from archived to active
mv archived/src/omnibase_core/models/core/model_schema_value.py \
   src/omnibase_core/models/core/

# Option B: Remove the import and refactor code
# Update model_error_context.py to not use ModelSchemaValue
```

**Step 2**: Deploy basic import validation
```bash
# Add the hook to .pre-commit-config.yaml
# Create basic validation script
# Test on current codebase
```

### Phase 2: Enhanced Validation

**Step 3**: Improve MyPy configuration
```ini
# Remove --ignore-missing-imports
# Add stricter import checking
# Configure per-package overrides
```

**Step 4**: Add performance optimizations
```python
# Implement caching
# Add parallel processing
# Optimize for incremental validation
```

### Phase 3: Advanced Features

**Step 5**: Add circular dependency detection
**Step 6**: Integration with existing validation pipeline
**Step 7**: Documentation and training

## Conclusion

The import verification script will provide essential protection against import failures that bypass current validation. The integration with pre-commit hooks ensures immediate feedback to developers while maintaining acceptable performance through caching and optimization strategies.

**Key Benefits**:
1. **Early Detection**: Catch import issues before commit
2. **Fast Feedback**: <10 second validation for typical commits
3. **Comprehensive Coverage**: Validates all internal imports
4. **Performance Optimized**: Caching and incremental validation
5. **Seamless Integration**: Works with existing pre-commit pipeline

**Success Metrics**:
- Zero import failures in production
- <10 second pre-commit hook execution
- >95% cache hit rate for repeated runs
- Zero false positives in validation