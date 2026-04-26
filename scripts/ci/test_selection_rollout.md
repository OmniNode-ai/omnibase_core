# Change-aware test selection — rollout activation criteria

## Shadow phase (ENABLE_SMART_TESTS=false)

- **Duration:** at least 14 calendar days AND at least 30 PR runs, whichever lands later.
- **Captured per PR:** `selection.json` artifact (always emitted by detect-changes).
- **Comparison:** for each PR run during the shadow phase, run a daily diff job that lists
  every test file the full-suite run executed that the smart selection would have skipped.
  Persist the per-PR diff to a private GitHub Actions artifact (retained 90 days) or the
  `omnidash_analytics` DB if available. Do NOT use a public Gist — diff data contains
  internal file paths and test metadata.

## Activation gate (flip ENABLE_SMART_TESTS=true)

All MUST be true:
1. `shadow_runs >= 30` AND `shadow_calendar_days >= 14`
2. `would_have_missed_failing_tests / total_failing_tests <= 0.01` (≤ 1% miss rate).
   If `total_failing_tests == 0` across the entire shadow window, gate does NOT
   auto-pass — require manual sign-off from the on-call engineer before activating.
3. Zero `would_have_missed` events where the missed test produced a FAIL result
   (i.e., the selection would have hidden a real failure) in the trailing 14 days.
4. `actionlint .github/workflows/ci.yml` is green on `main`

## Rollback trigger (flip ENABLE_SMART_TESTS=false)

ANY single one of these forces immediate rollback (no debate):
- A PR merges to main, smart-mode CI was green, and a regression is caught by nightly
  OR by the next PR's shadow comparison.
- A single nightly full-suite run catches a failure that the prior PR's smart selection
  would have missed (one strike, not two).
- `selection.json` ever fails Pydantic validation.

Rollback procedure:
1. Set `ENABLE_SMART_TESTS=false` in repo variables.
2. Open a Linear ticket tagged `change-aware-ci-rollback`.
3. Do NOT delete the `detect-changes` job — it remains in shadow mode, which is the same as the pre-activation state.
