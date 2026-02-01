# Example Contracts

This directory contains example contract files demonstrating the ONEX contract formats.

## DB Repository Contracts

`db_repository_example.yaml` demonstrates the v1 DB repository contract format:

- **Named parameters** (`:param`) - the only supported style in v1
- **Read operations** - SELECT queries with ORDER BY for determinism
- **Write operations** - INSERT, UPDATE, DELETE with WHERE clauses
- **Model aliasing** - short names mapping to fully qualified imports
- **Pagination** - LIMIT/OFFSET with required ORDER BY

### Validation Rules

DB repository contracts are validated by 5 validators:

1. **Structural** - Valid identifiers, single statements
2. **SQL Safety** - Mode/verb matching, no DDL, WHERE requirements
3. **Table Access** - Only declared tables allowed
4. **Deterministic** - ORDER BY for many=true and LIMIT/OFFSET
5. **Parameters** - Named params match declarations

### Usage

```python
from omnibase_core.runtime.runtime_file_registry import FileRegistry
from pathlib import Path

registry = FileRegistry()
contract = registry.load(Path("examples/contracts/db_repository_example.yaml"))
```

## Other Contract Examples

| File | Description |
|------|-------------|
| `orchestrator_data_pipeline.yaml` | Orchestrator node contract for data pipelines |
| `reducer_metrics_aggregator.yaml` | Reducer node contract for metrics aggregation |
| `compute/` | Compute node contract examples |
| `effect/` | Effect node contract examples |
| `handlers/` | Handler contract examples |

## Contract Format Reference

### DB Repository Contract Structure

```yaml
db_repository:
  name: <repository_name>           # Unique identifier
  engine: postgres | mysql | sqlite # Database engine
  database_ref: <database_name>     # Database connection reference
  description: |                    # Human-readable description
    Multi-line description here.

  tables:                           # Allowed tables (enforced)
    - table_name

  # Note: Table matching is case-insensitive. For example, `tables: ["Users"]`
  # will match `FROM users`, `FROM USERS`, or `FROM Users` in SQL. This follows
  # PostgreSQL's default identifier case-folding behavior. Quoted identifiers
  # like `FROM "Users"` are compared case-sensitively and must match the
  # declared table name exactly.

  models:                           # Model aliases
    AliasName: module.path:ClassName

  ops:                              # Named operations
    operation_name:
      mode: read | write            # Operation type
      description: |                # Operation description
        What this operation does.
      sql: |                        # SQL with named params
        SELECT ... WHERE col = :param
      params:                       # Parameter definitions
        param_name:
          name: param_name
          param_type: string | integer | number | boolean
          required: true | false
          default: <value>          # Optional default
          ge: <min>                 # Optional: >= constraint
          le: <max>                 # Optional: <= constraint
          min_length: <n>           # Optional: string min length
          max_length: <n>           # Optional: string max length
          description: |            # Optional description
      returns:
        model_ref: AliasName        # Return type (from models)
        many: true | false          # Single vs multiple rows
```

### Parameter Types

| Type | Description | Constraints |
|------|-------------|-------------|
| `string` | Text value | `min_length`, `max_length` |
| `integer` | Whole number | `ge`, `le` |
| `number` | Decimal number | `ge`, `le` |
| `boolean` | True/false | None |

### Validation Errors

Common validation errors and fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing ORDER BY` | `many: true` without ORDER BY | Add ORDER BY clause |
| `Table not allowed` | Query uses undeclared table | Add table to `tables` list |
| `Mode mismatch` | SELECT in write mode | Change mode to `read` |
| `Parameter undefined` | `:param` not in params | Add parameter definition |
| `DDL not allowed` | CREATE/DROP/ALTER in SQL | Remove DDL statements |

> **Note**: Table matching is case-insensitive, so `Table not allowed` errors are not caused by case differences. `tables: ["Users"]` will match `users`, `USERS`, or `Users` in SQL queries. However, quoted identifiers like `FROM "Users"` are compared case-sensitively and must match the declared table name exactly.
