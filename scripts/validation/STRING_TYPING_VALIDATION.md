# String Typing Anti-Pattern Validation Hook

## Overview

The String Typing Validation Hook is a comprehensive pre-commit tool designed to detect and prevent string-heavy typing anti-patterns in Pydantic models. It helps enforce strong typing conventions by identifying fields that should use more specific types like UUID, enums, or structured models instead of generic strings.

## Features

- **AST-based Analysis**: Uses Python AST parsing for reliable and accurate pattern detection
- **Configurable Rules**: Flexible configuration system for exclusions, patterns, and severity levels
- **Multiple Pattern Detection**: Identifies ID fields, enum candidates, entity references, and excessive string usage
- **Clear Error Messages**: Provides specific suggestions and explanations for each violation
- **Performance Optimized**: Includes timeout protection and file size limits
- **Integration Ready**: Seamlessly integrates with existing pre-commit pipeline

## Installation

The validation hook is automatically configured in the project's `.pre-commit-config.yaml`. No additional installation is required.

To run manually:

```bash
poetry run python scripts/validation/validate-string-typing.py --dir src/omnibase_core/models/
```

## Detected Anti-Patterns

### 1. String ID Fields (Error)

**Problem**: Using `str` for identifier fields that should be UUIDs.

```python
# ❌ Anti-pattern
class UserModel(BaseModel):
    user_id: str
    session_id: str
    request_id: str

# ✅ Correct
class UserModel(BaseModel):
    user_id: UUID
    session_id: UUID
    request_id: UUID
```

**Why it matters**: UUIDs provide better type safety, validation, and prevent common errors like empty strings or invalid formats.

### 2. String Enum Fields (Warning/Error)

**Problem**: Using `str` for categorical values that should be enums.

```python
# ❌ Anti-pattern
class TaskModel(BaseModel):
    status: str  # "pending", "running", "completed"
    priority: str  # "low", "medium", "high"
    type: str  # "user", "system", "admin"

# ✅ Correct
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskModel(BaseModel):
    status: TaskStatus
    priority: TaskPriority
    type: TaskType
```

**Why it matters**: Enums provide compile-time validation, IDE autocompletion, and prevent typos in categorical values.

### 3. String Entity References (Warning)

**Problem**: Using `str` for fields that appear to reference entities.

```python
# ❌ Anti-pattern
class OrderModel(BaseModel):
    customer_name: str  # Should be customer_id + display_name
    product_name: str   # Should be product_id + display_name

# ✅ Correct
class OrderModel(BaseModel):
    customer_id: UUID
    customer_display_name: str
    product_id: UUID
    product_display_name: str
```

**Why it matters**: Separating entity references (UUID) from display names (str) enables proper relational integrity and efficient lookups.

### 4. Excessive String Fields (Warning)

**Problem**: Models with too many string fields often indicate missing structure.

```python
# ❌ Anti-pattern
class UserProfile(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    country: str
    bio: str

# ✅ Correct
class Name(BaseModel):
    first: str
    last: str

class ContactInfo(BaseModel):
    email: str
    phone: str

class Address(BaseModel):
    street: str
    city: str
    state: str
    country: str

class UserProfile(BaseModel):
    name: Name
    contact: ContactInfo
    address: Address
    bio: str  # Legitimate string content
```

**Why it matters**: Breaking large models into smaller, focused models improves maintainability and type safety.

## Configuration

### Configuration File

The hook uses `scripts/validation/string-typing-config.json` for configuration:

```json
{
  "allowed_string_fields": [
    "description", "content", "text", "message", "notes",
    "path", "url", "template", "pattern", "display_name"
  ],
  "excluded_models": [
    "BaseModel", "TestModel", "LegacyModel"
  ],
  "excluded_files": [
    "test_*.py", "*_legacy.py", "base_*.py"
  ],
  "uuid_patterns": [
    "^.*_id$", "^id$", "^session_id$", "^user_id$"
  ],
  "enum_patterns": {
    "status": ["active", "inactive", "pending"],
    "type": ["user", "admin", "system"],
    "priority": ["low", "medium", "high"]
  },
  "max_string_fields_per_model": 5,
  "strict_mode": false
}
```

### Configuration Options

#### `allowed_string_fields`
Fields that can legitimately be strings:
- **Content fields**: `description`, `content`, `text`, `message`, `notes`
- **Paths and URLs**: `path`, `url`, `uri`, `file_path`, `endpoint`
- **Patterns**: `template`, `pattern`, `regex`, `expression`
- **Human-readable names**: `display_name`, `friendly_name`, `alias`
- **External identifiers**: `external_id`, `third_party_id`, `legacy_id`

#### `excluded_models`
Model classes to skip validation:
- Base classes and mixins
- Test and mock models
- Legacy models (temporary exclusions)

#### `excluded_files`
File patterns to skip:
- Test files: `test_*.py`, `*_test.py`
- Example files: `example*.py`, `*_example.py`
- Legacy files: `legacy_*.py`, `*_legacy.py`
- Base classes: `base_*.py`, `*_base.py`

#### `uuid_patterns`
Regex patterns for fields that should be UUIDs:
- `^.*_id$` - Any field ending in `_id`
- `^id$` - Field named exactly `id`
- `^session_id$`, `^user_id$` - Specific ID fields

#### `enum_patterns`
Field names and their expected enum values:
- `status`: `["active", "inactive", "pending", "completed"]`
- `type`: `["user", "admin", "system", "guest"]`
- `priority`: `["low", "medium", "high", "critical"]`

#### `max_string_fields_per_model`
Maximum allowed string fields per model (default: 5)

#### `strict_mode`
Whether to treat warnings as errors (default: false)

## Command Line Usage

### Basic Usage

```bash
# Validate all models in the models directory
poetry run python scripts/validation/validate-string-typing.py --dir src/omnibase_core/models/

# Validate specific files
poetry run python scripts/validation/validate-string-typing.py file1.py file2.py

# Use custom configuration
poetry run python scripts/validation/validate-string-typing.py --config custom-config.json --dir src/

# Enable strict mode (warnings become errors)
poetry run python scripts/validation/validate-string-typing.py --strict --dir src/
```

### Command Line Options

- `--config CONFIG`: Path to configuration JSON file
- `--strict`: Treat warnings as errors
- `--dir`: Recursively scan directories for Python files
- Without `--dir`: Treat arguments as individual Python files

## Integration with Pre-commit

The hook is automatically configured in `.pre-commit-config.yaml`:

```yaml
- id: validate-string-typing
  name: ONEX String Typing Anti-Pattern Detection
  entry: poetry run python scripts/validation/validate-string-typing.py
  args: ['--config', 'scripts/validation/string-typing-config.json', '--dir', 'src/omnibase_core/models/']
  language: system
  always_run: true
  pass_filenames: false
  files: ^src/omnibase_core/models/.*\.py$
  exclude: ^(tests/|archive/|archived/|scripts/).*\.py$
  stages: [pre-commit]
```

## Output Examples

### Successful Validation

```text
✅ String Typing Validation PASSED (15 files checked)
```

### Validation with Issues

```text
🔍 String Typing Validation Results
==================================================

📊 Found 4 typing issues:
   • 2 errors
   • 2 warnings

📁 src/omnibase_core/models/user.py
  ❌ Line 12:4 - user_id
      Type: string_id
      Current: str
      Suggested: UUID
      💡 Field 'user_id' appears to be an identifier and should use UUID type for proper type safety and validation

  ⚠️  Line 15:4 - status
      Type: string_enum
      Current: str
      Suggested: EnumStatus
      💡 Field 'status' appears to represent a categorical value and should use an enum. Common values: active, inactive, pending

📁 src/omnibase_core/models/task.py
  ⚠️  Line 8:4 - customer_name
      Type: string_entity_reference
      Current: str
      Suggested: UUID + display_name: str (separate fields)
      💡 Field 'customer_name' appears to reference an entity. Consider using a UUID for the reference and a separate display_name field for human-readable text

  ⚠️  Line 1:0 - TaskModel
      Type: excessive_string_fields
      Current:
      Suggested: Use more specific types (UUID, enums, separate models)
      💡 Model 'TaskModel' has 6 string fields (limit: 5). Consider using more specific types or breaking into multiple models

🔧 Quick Fix Guide:
   1. ID fields: user_id: str → user_id: UUID
   2. Status fields: status: str → status: StatusEnum
   3. Entity names: user_name: str → user_id: UUID + display_name: str
   4. Too many strings: Break model into smaller, more specific models

❌ VALIDATION FAILED (errors found)
```

## Best Practices

### 1. Use UUIDs for Identifiers

```python
from uuid import UUID
from pydantic import BaseModel

class UserModel(BaseModel):
    id: UUID
    organization_id: UUID
    session_id: UUID
```

### 2. Create Enums for Categorical Values

```python
from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class UserModel(BaseModel):
    role: UserRole
    status: UserStatus
```

### 3. Separate Entity References from Display Names

```python
# Instead of this:
class OrderModel(BaseModel):
    customer_name: str  # Ambiguous - is this an ID or display name?

# Do this:
class OrderModel(BaseModel):
    customer_id: UUID  # Clear entity reference
    customer_display_name: str  # Clear human-readable name
```

### 4. Break Large Models into Smaller Ones

```python
# Instead of this:
class UserModel(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    street: str
    city: str
    state: str
    country: str

# Do this:
class UserName(BaseModel):
    first: str
    last: str

class ContactInfo(BaseModel):
    email: str
    phone: str

class Address(BaseModel):
    street: str
    city: str
    state: str
    country: str

class UserModel(BaseModel):
    name: UserName
    contact: ContactInfo
    address: Address
```

### 5. Use Legitimate String Fields

These fields are appropriate as strings:
- Content: `description`, `content`, `text`, `message`
- Paths: `file_path`, `url`, `endpoint`
- Templates: `template`, `pattern`, `format`
- Human names: `display_name`, `friendly_name`

## Troubleshooting

### Common Issues

1. **False Positives**: Add field names to `allowed_string_fields` in config
2. **Excluded Models**: Add model names to `excluded_models` in config
3. **Legacy Code**: Add file patterns to `excluded_files` in config
4. **Custom Patterns**: Modify `uuid_patterns` or `enum_patterns` in config

### Performance

- Files larger than 10MB are skipped with a warning
- Validation times out after 10 minutes
- Directory scanning times out after 30 seconds per directory

### Error Recovery

- Syntax errors in Python files are silently skipped (other tools will catch them)
- Permission errors and file access issues are logged but don't stop validation
- Configuration file errors fall back to default configuration

## Contributing

When adding new patterns or rules:

1. Update the configuration file with new patterns
2. Add tests for the new patterns
3. Update this documentation
4. Consider backward compatibility for existing code

## Related Tools

This hook works alongside other ONEX validation tools:
- `validate-string-versions.py` - Validates version and ID field types
- `validate-pydantic-patterns.py` - General Pydantic pattern validation
- `validate-union-usage.py` - Union type usage validation
- `validate-dict-any-usage.py` - Dict[str, Any] anti-pattern detection

## Version History

- **v1.0.0**: Initial implementation with ID, enum, and entity reference detection
- **v1.1.0**: Added excessive string field detection and model-level analysis
- **v1.2.0**: Enhanced configuration system and performance improvements
