# OMN-1431 Migration Checklist: `version` → `contract_version`

**Ticket**: [OMN-1431](https://linear.app/omninode/issue/OMN-1431)
**Status**: In Progress
**Branch**: `jonah/omn-1431-add-contract_version-and-node_version-fields-to`

## Canonical Truth

- **YAML field**: `contract_version`
- **Python attribute**: `contract_version`
- **New field**: `node_version: ModelSemVer | None`

---

## Step 1: Model Change (DONE)

- [x] `src/omnibase_core/models/contracts/model_contract_base.py`
  - Renamed `version` → `contract_version`
  - Added `node_version: ModelSemVer | None = Field(default=None)`

---

## Step 2: YAML Handler Contracts (5 files)

Replace `version:` → `contract_version:` and optionally add `node_version:`:

```bash
# Files to update:
examples/contracts/handlers/compute_handler.yaml
examples/contracts/handlers/effect_handler.yaml
examples/contracts/handlers/reducer_handler.yaml
examples/demo/handlers/support_assistant/support_assistant.yaml
examples/demo/model-validate/contract.yaml
```

**Pattern**:
```yaml
# Before
version: "1.0.0"

# After
contract_version: "1.0.0"
node_version: "1.0.0"  # Optional, add if these are golden spec examples
```

---

## Step 3: Source Files (11 files, 22 references)

Replace `.version` → `.contract_version` on contract objects:

### Validation Layer
| File | Lines | Pattern |
|------|-------|---------|
| `src/omnibase_core/validation/phases/validator_expanded_contract.py` | 242 | `contract.version` → `contract.contract_version` |
| `src/omnibase_core/validation/validator_base.py` | 794 | `self.contract.version` → `self.contract.contract_version` |
| `src/omnibase_core/validation/phases/validator_merge.py` | 299 | `merged.version` → `merged.contract_version` |
| `src/omnibase_core/validation/validator_contract_pipeline.py` | 616 | `patch.extends.version` → `patch.extends.contract_version` |
| `src/omnibase_core/validation/validator_contract_patch.py` | 593 | `patch.extends.version` → `patch.extends.contract_version` |

### Services Layer
| File | Lines | Pattern |
|------|-------|---------|
| `src/omnibase_core/services/service_contract_validator.py` | 415, 418 | `contract.version` → `contract.contract_version` |

### Contract Infrastructure
| File | Lines | Pattern |
|------|-------|---------|
| `src/omnibase_core/merge/contract_merge_engine.py` | 254, 275, 280 | `patch.extends.version`, `base.version` → `*.contract_version` |
| `src/omnibase_core/contracts/contract_hash_registry.py` | 477, 507, 508 | `registered.version`, `computed.version` → `*.contract_version` |

### CLI
| File | Lines | Pattern |
|------|-------|---------|
| `src/omnibase_core/cli/cli_contract.py` | 773, 1054, 1139 | `patch.extends.version` → `patch.extends.contract_version` |

### Validators (string literal checks)
| File | Lines | Pattern |
|------|-------|---------|
| `src/omnibase_core/validation/validator_contract_linter.py` | 238-252, 411 | `"version" in data` → `"contract_version" in data` |

---

## Step 4: Remove Dual-Compat Code

**File**: `src/omnibase_core/contracts/contract_hash_registry.py`
**Lines**: 256-259

```python
# REMOVE THIS:
version_data = getattr(contract, "contract_version", None) or getattr(
    contract, "version", None
)

# REPLACE WITH:
version_data = contract.contract_version
```

---

## Step 5: Test Files (25 files, ~65 references)

### Contract Model Tests
```
tests/unit/contracts/test_model_contract_base.py
tests/unit/runtime/test_node_instance.py
tests/unit/models/contracts/test_model_handler_contract.py
tests/unit/models/contracts/test_handler_contract_examples.py
tests/unit/models/contracts/test_model_omnimemory_contract.py
tests/unit/models/contracts/subcontracts/test_model_event_handling_subcontract.py
tests/unit/models/contracts/subcontracts/test_model_compute_subcontract.py
tests/unit/models/projectors/test_model_projector_contract.py
tests/unit/orchestrator/test_contract_versioning.py
tests/unit/factories/test_contract_profile_factory.py
tests/unit/examples/demo/handlers/support_assistant/test_handler_contract.py
```

### Contract Merge/Validation Tests
```
tests/unit/merge/test_contract_merge_engine.py
tests/unit/merge/test_contract_merge_engine_events.py
tests/unit/validation/test_contract_validation_pipeline_events.py
```

**Pattern**: Update fixture data and assertions from `version=` to `contract_version=`

---

## Step 6: Add Guardrail Validator

Create or update validator to reject YAML contracts using `version:` instead of `contract_version:`:

**Location**: `src/omnibase_core/validation/validator_contract_linter.py`

**Logic**:
```python
if "version" in data and "contract_version" not in data:
    raise ModelOnexError(
        message="YAML contracts must use 'contract_version:', not 'version:'",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        migration_guide="Rename 'version:' to 'contract_version:' per ONEX spec",
    )
```

---

## Verification

After migration, run:

```bash
# Type checking
poetry run mypy src/omnibase_core/

# Full test suite
poetry run pytest tests/ -x

# Specific contract tests
poetry run pytest tests/unit/contracts/ tests/unit/models/contracts/ -v
```

---

## Files NOT to Change

These use `version` for different purposes (not `ModelContractBase.version`):

- `ModelContractFingerprint.version` - Uses `ModelContractVersion`, different model
- `ModelProfileReference.version` - String version constraint
- `ModelCapabilityProvided.version` - Capability version
- `ModelReference.version` - Reference version
- `ModelDependency.version` - Dependency version constraint
- Subcontract `version` fields - Internal model versions
