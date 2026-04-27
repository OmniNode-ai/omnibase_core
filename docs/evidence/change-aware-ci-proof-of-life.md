# Change-Aware CI — Proof of Life

**Status: DEFERRED — pending stack merge**

The epic stack (PRs #925, #927, #928, #929, #930, #931, #932, #936, #937, #938, #939, #940)
was OPEN at the time this document was created (2026-04-26). The live proof cannot be
captured until the workflow-modifying PRs (#936–#939) land on `main`.

A follow-up worker must execute the runbook below once the stack is merged.

Linear ticket: OMN-9861
Plan: `docs/plans/change-aware-ci-omnibase-core.md`

---

## Stack Merge State (at document creation)

| PR | Title snippet | State at creation |
|----|---------------|-------------------|
| #925 | epic stack base | OPEN |
| #927 | | OPEN |
| #928 | | OPEN |
| #929 | | OPEN |
| #930 | | OPEN |
| #931 | | OPEN |
| #932 | | OPEN |
| #936 | workflow-modifying | OPEN |
| #937 | workflow-modifying | OPEN |
| #938 | workflow-modifying | OPEN |
| #939 | workflow-modifying | OPEN |
| #940 | verification checkpoint head | OPEN |

---

## Runbook (execute once stack is on main)

Run every command from the `omnibase_core` worktree root.
Repo: `OmniNode-ai/omnibase_core`.

### Prerequisites

Verify all stacked PRs are merged before proceeding:

```bash
for pr in 925 927 928 929 930 931 932 936 937 938 939 940; do
  state=$(gh pr view $pr --repo OmniNode-ai/omnibase_core --json state --jq .state)
  echo "PR $pr: $state"
done
```

All must show `MERGED`. If any show `OPEN`, abort and wait.

---

### Open the small-scope PR (cli module — non-shared)

Create a one-line whitespace-only edit to `src/omnibase_core/cli/__init__.py`:

```bash
# From a fresh worktree off main:
git fetch origin main
git checkout -b jonah/omn-9861-proof-cli origin/main
# Add a trailing blank line to cli/__init__.py (or a trivial docstring edit)
echo "" >> src/omnibase_core/cli/__init__.py
git add src/omnibase_core/cli/__init__.py
git commit -m "chore(OMN-9861): proof-of-life — cli whitespace edit"
git push -u origin jonah/omn-9861-proof-cli

gh pr create \
  --repo OmniNode-ai/omnibase_core \
  --title "OMN-9861: proof-of-life small-scope (cli only)" \
  --body "Proof-of-life PR for OMN-9861. Touches only cli/__init__.py — expect smart-mode, split_count=1."
```

Record the PR number: **SMALL_PR=<N>**

---

### Wait for CI and download the test-selection artifact

```bash
# Wait for CI to complete on the small PR
gh pr checks $SMALL_PR --repo OmniNode-ai/omnibase_core --watch

# Get the run ID for the workflow run triggered by this PR
RUN_ID=$(gh run list --repo OmniNode-ai/omnibase_core \
  --branch jonah/omn-9861-proof-cli \
  --json databaseId,headBranch,status,conclusion \
  --jq '[.[] | select(.status=="completed" and .conclusion=="success")] | first | .databaseId')
test -n "$RUN_ID" && test "$RUN_ID" != "null" || { echo "No successful run found"; exit 1; }
echo "Run ID: $RUN_ID"

# Download the test-selection artifact
gh run download $RUN_ID \
  --repo OmniNode-ai/omnibase_core \
  --name test-selection \
  -D /tmp/sel-small

cat /tmp/sel-small/selection.json | jq .
```

#### Required assertions (small PR):

| Field | Expected value |
|-------|----------------|
| `is_full_suite` | `false` |
| `full_suite_reason` | `null` |
| `selected_paths` | `["tests/unit/cli/"]` |
| `split_count` | `1` |
| `matrix` | `[1]` |

---

### Confirm matrix shard counts (small PR)

```bash
# Unit shards — expect 1
gh run view $RUN_ID --repo OmniNode-ai/omnibase_core --json jobs \
  --jq '[.jobs[] | select(.name | startswith("Tests (Split "))] | length'

# Integration shards — expect 4
gh run view $RUN_ID --repo OmniNode-ai/omnibase_core --json jobs \
  --jq '[.jobs[] | select(.name | startswith("Integration Tests (Split "))] | length'
```

Expected: `1` and `4` respectively.

---

### Open the shared-module PR

```bash
git fetch origin main
git checkout -b jonah/omn-9861-proof-shared origin/main
echo "" >> src/omnibase_core/models/__init__.py
git add src/omnibase_core/models/__init__.py
git commit -m "chore(OMN-9861): proof-of-life — shared models whitespace edit"
git push -u origin jonah/omn-9861-proof-shared

gh pr create \
  --repo OmniNode-ai/omnibase_core \
  --title "OMN-9861: proof-of-life shared-module (models/__init__.py)" \
  --body "Proof-of-life PR for OMN-9861. Touches models/__init__.py — expect full suite, split_count=40."
```

Record the PR number: **SHARED_PR=<N>**

```bash
gh pr checks $SHARED_PR --repo OmniNode-ai/omnibase_core --watch

SHARED_RUN_ID=$(gh run list --repo OmniNode-ai/omnibase_core \
  --branch jonah/omn-9861-proof-shared \
  --json databaseId,status,conclusion \
  --jq '[.[] | select(.status=="completed" and .conclusion=="success")] | first | .databaseId')
test -n "$SHARED_RUN_ID" && test "$SHARED_RUN_ID" != "null" || { echo "No successful shared run found"; exit 1; }

gh run download $SHARED_RUN_ID \
  --repo OmniNode-ai/omnibase_core \
  --name test-selection \
  -D /tmp/sel-shared

cat /tmp/sel-shared/selection.json | jq .
```

#### Required assertions (shared-module PR):

| Field | Expected value |
|-------|----------------|
| `is_full_suite` | `true` |
| `full_suite_reason` | `"shared_module"` |
| `split_count` | `40` |
| `matrix` | `[1, 2, ..., 40]` |

```bash
# Unit shards — expect 40
gh run view $SHARED_RUN_ID --repo OmniNode-ai/omnibase_core --json jobs \
  --jq '[.jobs[] | select(.name | startswith("Tests (Split "))] | length'

# Integration shards — expect 4
gh run view $SHARED_RUN_ID --repo OmniNode-ai/omnibase_core --json jobs \
  --jq '[.jobs[] | select(.name | startswith("Integration Tests (Split "))] | length'
```

---

### Verify branch-protection gates

```bash
gh api "repos/OmniNode-ai/omnibase_core/branches/main/protection/required_status_checks/contexts" \
  --jq '.[]' | sort
```

Expected output (exactly these three, no extras):

```text
CI Summary
Quality Gate
Tests Gate
```

---

### Verify durations cache

After the shared-module PR (full suite) runs:

```bash
gh api "repos/OmniNode-ai/omnibase_core/actions/caches?key=test-durations" \
  --jq '.actions_caches[] | {key, last_accessed_at, size_in_bytes}'
```

Expected: at least one entry with `key` starting `test-durations-` and `size_in_bytes > 0`.

After the cli-only (smart-suite) run, capture before/after cache state and diff
to prove no conditional cache write occurred:

```bash
# Before the smart-suite PR is opened — record the existing test-durations cache keys.
gh api "repos/OmniNode-ai/omnibase_core/actions/caches?key=test-durations" \
  --jq '.actions_caches[].key' | sort > /tmp/cache-keys-before.txt

# Open the small (cli-only) PR and let it run to completion.

# After the smart-suite run completes — record the cache keys again.
gh api "repos/OmniNode-ai/omnibase_core/actions/caches?key=test-durations" \
  --jq '.actions_caches[].key' | sort > /tmp/cache-keys-after.txt

# Verify no new entries were created (diff must be empty).
diff /tmp/cache-keys-before.txt /tmp/cache-keys-after.txt
```

Expected: `diff` produces no output. Any added line beginning with `> test-durations-`
indicates a conditional cache write fired in smart-suite mode and is a regression.

Attach both `/tmp/cache-keys-before.txt` and `/tmp/cache-keys-after.txt` to the
"Durations Cache State" subsection of the evidence below.

---

### Amend this document with live evidence

Replace the "Pending Evidence" section below with:
- Small PR number and run ID
- Parsed `selection.json` output for both PRs
- `gh run view --json jobs` shard counts for both PRs
- Branch-protection contexts list (verbatim output)
- Durations cache state (before/after smart-suite run)

Then commit:

```bash
git add docs/evidence/change-aware-ci-proof-of-life.md
git commit -m "docs(OMN-9861): proof of life — change-aware CI test selection (live evidence captured)"
git push
```

---

## Pending Evidence

> This section will be populated by a follow-up worker once the epic stack lands on `main`.

### Small PR (cli-only, smart-mode)

- PR number: **PENDING**
- Run ID: **PENDING**
- `selection.json` content:

  ```text
  PENDING
  ```

- Unit shard count: **PENDING** (expected: 1)
- Integration shard count: **PENDING** (expected: 4)

### Shared-Module PR (models/__init__.py, full-suite escalation)

- PR number: **PENDING**
- Run ID: **PENDING**
- `selection.json` content:

  ```text
  PENDING
  ```

- Unit shard count: **PENDING** (expected: 40)
- Integration shard count: **PENDING** (expected: 4)

### Branch-Protection Contexts

```text
PENDING
```

(Expected: `CI Summary`, `Quality Gate`, `Tests Gate`)

### Durations Cache State

```text
PENDING
```

---

## Acceptance Criteria (from OMN-9861)

Per the ticket's exact acceptance criteria:

- [ ] Two PRs landed; both run IDs cited in this document
- [ ] Small-PR `selection.json`: `selected_paths=["tests/unit/cli/"]`, `split_count=1`, `is_full_suite=false`, `full_suite_reason=null`, `matrix=[1]`
- [ ] Shared-module PR `selection.json`: `is_full_suite=true`, `full_suite_reason="shared_module"`, `split_count=40`, `matrix=[1..40]`
- [ ] `gh run view` matrix-shard counts: 1 unit shard (small PR), 40 unit shards (shared-module PR), 4 integration shards for both
- [ ] Branch-protection contexts: exactly `CI Summary`, `Quality Gate`, `Tests Gate` (no extras)
- [ ] Durations cache `size_in_bytes > 0` after full-suite run; no new entry for smart-suite SHA

> **Scope note:** This proof-of-life is representative, not exhaustive. It exercises the
> smart-mode contraction path, shared-module full-suite escalation, stable gate names,
> separate integration shards, and durations-cache write conditioning. It does NOT exercise
> threshold-modules escalation (≥8 non-shared modules), test-infrastructure escalation,
> `feature_flag_off` short-circuit, or doc-only/workflow-only fallback paths. Those are
> validated via Python unit tests in `tests/unit/scripts/ci/` and ongoing shadow-mode
> artifacts from Task 14.
