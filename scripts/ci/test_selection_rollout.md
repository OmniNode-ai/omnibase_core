# Change-aware test selection — rollout activation criteria

## Shadow phase (ENABLE_SMART_TESTS=false)

- **Duration:** at least 7 calendar days AND at least 30 PR runs whichever lands later.
- **Captured per PR:** `selection.json` artifact (always emitted by detect-changes).
- **Comparison:** for each PR run during the shadow phase, run a daily diff job that lists
  every test file the full-suite run executed that the smart selection would have skipped.
  Persist the per-PR diff to a long-lived artifact bucket (or the `omnidash_analytics` DB
  if available; otherwise a Gist).

## Activation gate (flip ENABLE_SMART_TESTS=true)

All MUST be true:
1. `shadow_runs >= 30` AND `shadow_calendar_days >= 7`
2. `would_have_missed_failing_tests / total_failing_tests <= 0.01` (≤ 1% miss rate)
3. Zero CRITICAL/MAJOR `would_have_missed` events in the trailing 14 days
4. `actionlint .github/workflows/ci.yml` is green on `main`

## Rollback trigger (flip ENABLE_SMART_TESTS=false)

ANY single one of these forces immediate rollback (no debate):
- A PR merges to main, smart-mode CI was green, and a regression is caught by nightly OR by the next PR's shadow comparison.
- Two consecutive nightly full-suite runs catch a failure that the prior PR's smart selection would have missed.
- `selection.json` ever fails Pydantic validation (operator manually corrupts the model).

Rollback procedure:
1. Set `ENABLE_SMART_TESTS=false` in repo variables.
2. Open a Linear ticket tagged `change-aware-ci-rollback`.
3. Do NOT delete the `detect-changes` job — it remains in shadow mode, which is the same as the pre-activation state.
