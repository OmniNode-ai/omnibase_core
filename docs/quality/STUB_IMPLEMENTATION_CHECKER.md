# Stub Implementation Checker

AST-based pre-commit hook for detecting incomplete stub implementations in Python code.

## Overview

The stub implementation checker uses Python's Abstract Syntax Tree (AST) parsing to reliably detect incomplete or stubbed function/method implementations that shouldn't be committed to production code.

**Script Location**: `scripts/validation/check_stub_implementations.py`

## Detection Patterns

### 1. Functions with Only `pass`
```python
# ❌ DETECTED AS STUB
def process_data(data):
    """Process the data."""
    pass
```

### 2. Functions with Only `...` (Ellipsis)
```python
# ❌ DETECTED AS STUB
def calculate(x, y):
    """Calculate something."""
    ...
```

### 3. NotImplementedError Raises
```python
# ❌ DETECTED AS STUB
def validate(value):
    """Validate the value."""
    raise NotImplementedError("TODO: implement validation")
```

### 4. Empty Function Bodies
```python
# ❌ DETECTED AS STUB (after docstring extraction)
def empty_function():
    """This function has no implementation."""
    pass
```

### 5. Pass + Return Pattern
```python
# ❌ DETECTED AS STUB
def get_data():
    """Get data."""
    pass
    return None
```

### 6. TODO/FIXME in Docstrings
```python
# ❌ DETECTED AS STUB
def future_feature():
    """TODO: implement this feature."""
    return None
```

## Legitimate Exclusions

### 1. Abstract Base Class Methods
```python
# ✅ NOT DETECTED (Legitimate)
from abc import ABC, abstractmethod

class BaseClass(ABC):
    @abstractmethod
    def abstract_method(self):
        """Abstract methods can be stubs."""
        pass
```

### 1.5. Overload Decorated Methods (Type Hints)
```python
# ✅ NOT DETECTED (Legitimate)
from typing import overload

class MyClass:
    @overload
    def method(self, value: str) -> str: ...

    @overload
    def method(self, value: int) -> int: ...

    def method(self, value):
        """Actual implementation."""
        return value
```

### 2. Protocol Classes
```python
# ✅ NOT DETECTED (Legitimate)
from typing import Protocol

class DataProcessor(Protocol):
    def process(self, data):
        """Protocol methods can be stubs."""
        ...
```

### 3. Type Stub Files (.pyi)
```python
# ✅ NOT DETECTED (Legitimate)
# File: mymodule.pyi
def function() -> int: ...
```

### 4. Inline Exclusion Comments
```python
# ✅ NOT DETECTED (Explicit exclusion)
def intentional_stub():  # stub-ok
    """This stub is intentionally incomplete for now."""
    pass
```

### 5. Dunder Methods (except __init__)
```python
# ✅ NOT DETECTED (Dunder methods often need stubs)
class MyClass:
    def __str__(self):
        pass

    def __repr__(self):
        pass
```

### 6. Test Files and Fixtures
```python
# ✅ NOT DETECTED (Test fixtures can use pass)
# File: tests/test_module.py or conftest.py
@pytest.fixture
def my_fixture():
    pass
```

## Usage

### Command Line

#### Check Specific Files
```bash
python scripts/validation/check_stub_implementations.py file1.py file2.py
```

#### Check Directory Recursively
```bash
python scripts/validation/check_stub_implementations.py src/
```

#### Strict CI Mode
```bash
python scripts/validation/check_stub_implementations.py --check-mode src/
```

#### Show Fix Suggestions
```bash
python scripts/validation/check_stub_implementations.py --fix-suggestions file.py
```

#### Use Custom Configuration
```bash
python scripts/validation/check_stub_implementations.py --config .stub-check-config.yaml src/
```

### Pre-commit Hook

The hook is automatically configured in `.pre-commit-config.yaml`:

```yaml
- id: check-stub-implementations
  name: ONEX Stub Implementation Detector
  entry: poetry run python scripts/validation/check_stub_implementations.py
  language: system
  pass_filenames: true
  files: ^src/.*\.py$
  exclude: ^(tests/|archived/|archive/|examples/prototypes/).*\.py$
  stages: [pre-commit]
```

#### Run Manually
```bash
pre-commit run check-stub-implementations --all-files
```

## Configuration

### Configuration File

Create `.stub-check-config.yaml` in your project root (see `.stub-check-config.example.yaml`):

```yaml
# Files to exclude (exact filenames)
excluded_files:
  - __init__.py
  - conftest.py

# Path patterns to exclude
excluded_patterns:
  - /tests/fixtures/
  - /examples/experimental/
  - /prototypes/

# Function names to exclude
excluded_functions:
  - setup
  - teardown
  - mock_factory
```

### Default Exclusions

The checker automatically excludes:
- `test_*.py` - Test files
- `*/tests/*` - Test directories
- `*/examples/*` - Example code
- `*/prototypes/*` - Prototype code
- `*/archived/*` - Archived code
- `conftest.py` - Pytest configuration
- `.pyi` files - Type stub files

## Example Output

### Success (No Stubs Found)

```
✅ Stub Implementation Check PASSED
   Checked 45 file(s) - no stub implementations found
```

### Failure (Stubs Detected)

```
❌ Stub Implementation Detection FAILED
================================================================================
Found 4 stub implementation(s) in 2 file(s):

📄 src/mymodule/processor.py
   Line 23: process_data()
   ├─ Issue: Function contains only 'pass' statement
   └─ Fix: Implement processing logic based on function's documented purpose

   Line 45: validate_input()
   ├─ Issue: Function raises NotImplementedError (stubbed)
   └─ Fix: Implement the documented behavior: Validate input according to schema...

📄 src/mymodule/calculator.py
   Line 12: calculate()
   ├─ Issue: Function contains only '...' (Ellipsis)
   └─ Fix: Implement getter logic to retrieve and return the requested data

   Line 34: get_result()
   ├─ Issue: Function docstring contains TODO/FIXME marker
   └─ Fix: Complete the implementation and remove TODO/FIXME markers

================================================================================
🔧 How to Fix Stub Implementations:

❌ BAD Examples:
   def process_data(data):
       '''Process the data.'''
       pass  # Stub - needs implementation

   def calculate(x, y):
       ...  # Stub

   def validate(value):
       raise NotImplementedError('TODO: implement validation')

✅ GOOD Examples:
   def process_data(data):
       '''Process the data by validating and transforming it.'''
       if not data:
           raise ValueError('Data cannot be empty')
       return [item.strip() for item in data]

   def calculate(x, y):
       '''Calculate sum with validation.'''
       if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
           raise TypeError('Arguments must be numeric')
       return x + y

💡 Tips:
   • Replace pass/... with actual implementation logic
   • Replace NotImplementedError with working code
   • Remove TODO/FIXME comments after implementation
   • Use '# stub-ok' comment to exclude legitimate stubs
   • Protocol/ABC classes are automatically excluded
```

### With Fix Suggestions

```bash
python scripts/validation/check_stub_implementations.py --fix-suggestions src/processor.py
```

```
❌ Stub Implementation Detection FAILED
================================================================================
Found 1 stub implementation(s) in 1 file(s):

📄 src/processor.py
   Line 15: process_data()
   ├─ Issue: Function contains only 'pass' statement
   └─ Fix: Implement processing logic based on function's documented purpose

   Suggestion based on function name 'process_data':
   def process_data(data):
       '''Process the data by validating and transforming it.'''
       if not data:
           raise ValueError('Data cannot be empty')

       # Add your processing logic here
       processed = []
       for item in data:
           if item is not None:
               processed.append(transform(item))

       return processed
```

## Exit Codes

- **0**: No stub implementations found (success)
- **1**: Stub implementations detected (failure)

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Check for stub implementations
  run: |
    poetry run python scripts/validation/check_stub_implementations.py --check-mode src/
```

### GitLab CI

```yaml
check-stubs:
  script:
    - poetry run python scripts/validation/check_stub_implementations.py --check-mode src/
  only:
    - merge_requests
```

## Best Practices

### 1. Complete Before Committing
Always implement functionality completely before committing:

```python
# ❌ Don't commit this
def important_feature():
    pass  # TODO: implement later

# ✅ Commit this
def important_feature():
    """Implement the important feature with proper logic."""
    if not condition:
        raise ValueError("Invalid condition")
    return process_result()
```

### 2. Use Type Hints
Proper type hints help clarify expected implementation:

```python
# ✅ Clear expectations
def process_data(data: List[str]) -> List[str]:
    """Process list of strings."""
    return [s.strip().lower() for s in data if s]
```

### 3. Document Incomplete Work
If you must commit incomplete work (rare cases):

```python
# ✅ Explicitly mark as intentional
def future_feature():  # stub-ok
    """
    This feature is intentionally incomplete.
    Tracked in issue #123.
    """
    pass
```

### 4. Use Abstract Base Classes
For framework code that's meant to be overridden:

```python
# ✅ Proper use of abstraction
from abc import ABC, abstractmethod

class DataProcessor(ABC):
    @abstractmethod
    def process(self, data):
        """Subclasses must implement this."""
        pass
```

## Troubleshooting

### False Positives

If the checker incorrectly flags legitimate code:

1. **Add inline comment**: `# stub-ok`
2. **Update configuration**: Add to `.stub-check-config.yaml`
3. **Check if it's truly needed**: Consider if the code should actually be implemented

### Excluded Files Not Working

Ensure patterns in configuration use forward slashes:

```yaml
excluded_patterns:
  - /tests/fixtures/  # ✅ Correct
  - tests\fixtures\   # ❌ Won't work on all platforms
```

### Script Not Found

If running from command line fails:

```bash
# Use full path
python scripts/validation/check_stub_implementations.py src/

# Or use poetry
poetry run python scripts/validation/check_stub_implementations.py src/
```

## Advanced Usage

### Custom Detection Logic

The script can be extended by modifying `StubImplementationDetector` class:

```python
# Add custom stub pattern detection
def _check_custom_pattern(self, node, statements):
    # Your custom logic here
    pass
```

### Integration with Custom Tools

```python
from scripts.validation.check_stub_implementations import (
    StubImplementationChecker,
    StubDetectorConfig
)

# Use programmatically
config = StubDetectorConfig()
checker = StubImplementationChecker(check_mode=True, config=config)
success = checker.check_files([Path("myfile.py")])
```

## Performance

- **AST Parsing**: Fast and accurate (~100-200 files/second)
- **Memory Usage**: Minimal (processes files one at a time)
- **Parallel Execution**: Compatible with pre-commit's parallel mode

## Related Tools

- `validate-stubbed-functionality.py` - Original validator (less comprehensive)
- `mypy` - Type checking (complementary)
- `pylint` - General code quality (complementary)

## Contributing

When extending the checker:

1. Add new patterns to `_check_stub_patterns()` method
2. Update documentation with examples
3. Add test cases in `tests/validation/test_check_stub_implementations.py`
4. Ensure backward compatibility with existing exclusions
