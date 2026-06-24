# DoD Evidence — Phase Budget and Parallel Dispatch Fields

**Feature:** Add phase budget and parallel dispatch fields to ModelSessionPhaseSpec
**Verification grade:** medium — unit tests on model fields
**Date:** 2026-05-19

## Fields Added

### ModelSessionPhaseSpec (model_session_phase_spec.py)
- `max_duration_minutes: int | None = Field(default=None, gt=0)` — hard phase time cap
- `budget_warning_pct: int = Field(default=80, gt=0, le=100)` — warning threshold as % of budget
- `parallel_with: tuple[str, ...] = ()` — co-dispatch relationships by phase name

### ModelSessionContract (model_session_contract.py)
- `max_parallel_workers: int = Field(default=7, gt=0)` — contract-level worker concurrency limit
- `max_daily_cost_usd: float | None = Field(default=None, gt=0)` — daily cost ceiling

## Test Results

```
tests/unit/models/overseer/test_phase_budget.py — 9 passed
  test_phase_has_budget_fields PASSED
  test_phase_budget_defaults PASSED
  test_phase_max_duration_must_be_positive PASSED
  test_phase_budget_warning_pct_range PASSED
  test_phase_parallel_with_multiple PASSED
  test_contract_has_max_parallel_workers PASSED
  test_contract_max_parallel_workers_default PASSED
  test_contract_has_max_daily_cost PASSED
  test_contract_max_daily_cost_default_none PASSED
```

## Acceptance Criteria

- [x] All new fields have defaults (backwards-compatible)
- [x] Phases declare time budgets independently of contract-level timeout
- [x] `parallel_with` declares co-dispatch relationships by phase name
- [x] Contract declares worker concurrency limit (`max_parallel_workers`)
- [x] `max_duration_minutes` validated `gt=0` (rejects 0 and negative)
- [x] `budget_warning_pct` validated `gt=0, le=100` (rejects 0 and 101+)
