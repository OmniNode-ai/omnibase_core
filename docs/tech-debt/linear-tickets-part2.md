# Linear Tickets - MVP Tech Debt Part 2 (Cleanup and Refactoring)

**Project**: MVP - OmniNode Platform Foundation
**Created**: 2025-12-27
**Total Tickets**: 6

---

## Ticket 7: Convert Optional[X] to PEP 604 syntax

| Field | Value |
|-------|-------|
| **Title** | [Typing] Convert Optional[X] to X \| None (PEP 604) |
| **Priority** | Medium |
| **Labels** | tech-debt, typing, pep-604 |
| **Estimate** | 2 points |

### Description

#### Problem
44 occurrences of `Optional[X]` should use PEP 604 syntax `X | None`.

#### Top Affected Files
| File | Occurrences |
|------|-------------|
| models/health/model_tool_health.py | 13 |
| models/core/model_node_announce_metadata.py | 3 |
| models/projection/model_projection_base.py | 1 |
| models/security/model_security_context.py | 1 |
| models/services/model_service_health.py | 2 |
| models/services/model_execution_priority.py | 1 |
| models/core/model_extracted_block.py | 1 |
| Other files | 22 |

#### Solution
Convert all `Optional[X]` to `X | None`:
```python
# Before
field: Optional["ModelType"] = None

# After
field: "ModelType" | None = None
```

#### Test Requirements
- [ ] Run `poetry run ruff check src/ --select UP007` - no violations
- [ ] Run `poetry run mypy src/omnibase_core/` - no errors
- [ ] Run `poetry run pytest tests/` - all tests pass

#### Acceptance Criteria
- Zero `Optional[` usage in source code
- All typing uses PEP 604 union syntax
- mypy passes

---

## Ticket 8: Remove or Implement Empty Placeholder Models

| Field | Value |
|-------|-------|
| **Title** | [Cleanup] Remove or implement empty placeholder models |
| **Priority** | Medium |
| **Labels** | tech-debt, cleanup |
| **Estimate** | 1 point |

### Description

#### Problem
5 empty placeholder models exist that should be removed or implemented.

#### Affected Files
| File | Class | Issue |
|------|-------|-------|
| models/services/model_plan.py | ModelPlan | Empty with only `pass` |
| models/graph/model_graph.py | ModelGraph | Empty with only `pass` |
| models/core/model_output_data.py | ModelOutputData | Empty with placeholder comment |
| models/core/model_reducer.py | ModelState | Empty with placeholder comment |
| models/workflow/execution/model_config.py | - | Empty module |

#### Solution
For each placeholder:
1. If not used anywhere -> Remove the file
2. If referenced -> Implement minimum viable version
3. Document decision in commit message

#### Test Requirements
- [ ] Search for usages: `grep -r "ModelPlan\|ModelGraph\|ModelOutputData\|ModelState" src/`
- [ ] Run `poetry run pytest tests/` after changes
- [ ] Run `poetry run mypy src/omnibase_core/` - no errors

#### Acceptance Criteria
- No empty placeholder classes remain
- All removed/implemented with justification
- Tests pass

---

## Ticket 9: Refactor Hardcoded Timeout Values

| Field | Value |
|-------|-------|
| **Title** | [Refactor] Replace hardcoded timeout values with constants |
| **Priority** | Medium |
| **Labels** | tech-debt, refactoring, constants |
| **Estimate** | 2 points |
| **Blocked By** | Ticket for constants_timeouts.py creation |

### Description

#### Problem
30+ hardcoded timeout values (30000, 300000, 5.0) should use constants.

#### Affected Files (partial list)
| File | Line | Value |
|------|------|-------|
| models/orchestrator/model_action.py | 125 | 30000 |
| models/workflow/execution/model_workflow_step_execution.py | 85 | 30000 |
| models/contracts/model_workflow_step.py | 68 | 30000 |
| models/context/model_action_execution_context.py | 101 | 30000 |
| validation/workflow_linter.py | 367 | 30000 |
| utils/workflow_executor.py | 398 | 30000 |
| mixins/mixin_event_bus.py | 582 | 5.0 |
| mixins/mixin_event_listener.py | 320 | 5 |

#### Dependencies
- Requires: constants_timeouts.py ticket completed first

#### Solution
Replace hardcoded values with imports from constants:
```python
from omnibase_core.constants import DEFAULT_ACTION_TIMEOUT_MS

# Before
timeout_ms: int = Field(default=30000)

# After
timeout_ms: int = Field(default=DEFAULT_ACTION_TIMEOUT_MS)
```

#### Test Requirements
- [ ] Run `grep -r "= 30000\|= 300000" src/` - should return 0 results
- [ ] Run `poetry run pytest tests/` - all tests pass
- [ ] Verify Field defaults work correctly

#### Acceptance Criteria
- All timeout values use constants
- No hardcoded 30000/300000/5.0 in source
- Tests pass

---

## Ticket 10: Audit and Fix type: ignore Comments

| Field | Value |
|-------|-------|
| **Title** | [Typing] Audit and reduce # type: ignore comments |
| **Priority** | Medium |
| **Labels** | tech-debt, typing, audit |
| **Estimate** | 3 points |

### Description

#### Problem
277 `# type: ignore` comments may be hiding real issues or be outdated.

#### Top Files
| File | Count |
|------|-------|
| container/container_service_resolver.py | 31 |
| logging/emit.py | 5 |
| decorators/pattern_exclusions.py | 5 |
| decorators/allow_dict_any.py | 2 |

#### Solution
For each `# type: ignore`:
1. Check if still necessary with current mypy version
2. If necessary, add specific error code: `# type: ignore[error-code]`
3. If not necessary, remove and fix underlying issue
4. Document remaining ignores

#### Test Requirements
- [ ] Run `poetry run mypy src/omnibase_core/ --warn-unused-ignores`
- [ ] Count remaining ignores: `grep -r "type: ignore" src/ | wc -l`
- [ ] Target: Reduce by at least 50%

#### Acceptance Criteria
- All remaining ignores have specific error codes
- Unused ignores removed
- Count reduced by 50%+
- Document remaining ignores with justification

---

## Ticket 11: Standardize Exception Handling

| Field | Value |
|-------|-------|
| **Title** | [Refactor] Replace generic Exception catches with specific types |
| **Priority** | Medium |
| **Labels** | tech-debt, error-handling, refactoring |
| **Estimate** | 3 points |

### Description

#### Problem
50+ instances of `except Exception as e:` could be more specific.

#### Top Files
| File | Count |
|------|-------|
| mixins/mixin_event_bus.py | 11 |
| mixins/mixin_effect_execution.py | 8 |
| infrastructure/node_core_base.py | 7 |
| infrastructure/node_base.py | 5 |

#### Solution
For each generic exception:
1. Identify specific exceptions that can occur
2. Replace with specific types (ValueError, TypeError, ModelOnexError, etc.)
3. Keep `except Exception` only for true catch-all logging scenarios
4. Use `@standard_error_handling` decorator where appropriate

#### Test Requirements
- [ ] Run `grep -r "except Exception" src/ | wc -l` - track reduction
- [ ] Run `poetry run pytest tests/` - all tests pass
- [ ] Verify error handling still works for edge cases

#### Acceptance Criteria
- Generic exceptions reduced by 70%+
- Specific exception types used where possible
- No change in error handling behavior
- Tests pass

---

## Ticket 12: Implement encrypt/decrypt Stub Methods

| Field | Value |
|-------|-------|
| **Title** | [Feature] Implement encrypt_payload and decrypt_payload methods |
| **Priority** | Medium |
| **Labels** | tech-debt, security, feature |
| **Estimate** | 3 points |

### Description

#### Problem
Security methods raise NotImplementedError instead of providing real implementation.

#### Location
- File: `src/omnibase_core/models/security/model_secure_event_envelope_class.py`
- Methods:
  - `encrypt_payload()` at line 537
  - `decrypt_payload()` at line 562
- Documented: AES-256-GCM encryption

#### Solution
**Option A: Implement real encryption**
```python
from cryptography.fernet import Fernet
# or
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
```

**Option B: Remove methods if not needed**
- Remove methods entirely
- Update documentation
- Remove security claims

#### Test Requirements
- [ ] If implementing: Add encryption/decryption unit tests
- [ ] Test round-trip: encrypt then decrypt returns original
- [ ] Test with various payload sizes
- [ ] Run `poetry run pytest tests/unit/models/security/`

#### Acceptance Criteria
- No NotImplementedError in production code paths
- Either real implementation or methods removed
- Tests pass
- Documentation updated

---

## JSON Format for API Import

```json
{
  "tickets": [
    {
      "title": "[Typing] Convert Optional[X] to X | None (PEP 604)",
      "priority": 2,
      "labels": ["tech-debt", "typing", "pep-604"],
      "estimate": 2
    },
    {
      "title": "[Cleanup] Remove or implement empty placeholder models",
      "priority": 2,
      "labels": ["tech-debt", "cleanup"],
      "estimate": 1
    },
    {
      "title": "[Refactor] Replace hardcoded timeout values with constants",
      "priority": 2,
      "labels": ["tech-debt", "refactoring", "constants"],
      "estimate": 2
    },
    {
      "title": "[Typing] Audit and reduce # type: ignore comments",
      "priority": 2,
      "labels": ["tech-debt", "typing", "audit"],
      "estimate": 3
    },
    {
      "title": "[Refactor] Replace generic Exception catches with specific types",
      "priority": 2,
      "labels": ["tech-debt", "error-handling", "refactoring"],
      "estimate": 3
    },
    {
      "title": "[Feature] Implement encrypt_payload and decrypt_payload methods",
      "priority": 2,
      "labels": ["tech-debt", "security", "feature"],
      "estimate": 3
    }
  ]
}
```

---

## Summary

| Ticket # | Title | Priority | Estimate |
|----------|-------|----------|----------|
| 7 | [Typing] Convert Optional[X] to X \| None (PEP 604) | Medium | 2 pts |
| 8 | [Cleanup] Remove or implement empty placeholder models | Medium | 1 pt |
| 9 | [Refactor] Replace hardcoded timeout values with constants | Medium | 2 pts |
| 10 | [Typing] Audit and reduce # type: ignore comments | Medium | 3 pts |
| 11 | [Refactor] Replace generic Exception catches with specific types | Medium | 3 pts |
| 12 | [Feature] Implement encrypt_payload and decrypt_payload methods | Medium | 3 pts |

**Total Estimated Points**: 14 points
