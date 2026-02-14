> **Navigation**: [Home](../INDEX.md) > [Standards](onex_terminology.md) > CI/CD Standards

# CI/CD Standards

> **Version**: 1.0.0
> **Last Updated**: 2026-02-14
> **Status**: Canonical Reference
> **Purpose**: Organization-wide CI/CD standards for all OmniNode repositories
> **Ticket**: OMN-2224

---

## Table of Contents

1. [Overview](#overview)
2. [Repository Classifications](#repository-classifications)
3. [Check Tier System](#check-tier-system)
4. [Gate Check Name Contract](#gate-check-name-contract)
5. [required-checks.yaml v2 Schema](#required-checksyaml-v2-schema)
6. [Invariants](#invariants)
7. [Branch Protection Migration Safety](#branch-protection-migration-safety)
8. [CI Summary Semantics](#ci-summary-semantics)
9. [Examples](#examples)
10. [Related Documentation](#related-documentation)

---

## Overview

This document defines the CI/CD standards that apply to all OmniNode repositories. It establishes:

- A **tier system** for classifying CI checks by scope and enforcement policy
- **Repository classifications** that determine which tiers apply
- A **gate check name contract** that treats certain check names as API-stable identifiers
- A **v2 schema** for `required-checks.yaml` that separates operational gates from documentation
- **Invariants** that must hold across all CI configurations

These standards exist because GitHub branch protection rules reference check names as opaque strings. Renaming a check without coordinating the branch protection update breaks merging. This document codifies the rules that prevent that class of failure.

---

## Repository Classifications

Every OmniNode repository falls into one of four classifications. The classification determines which check tiers apply.

| Classification | Description | Examples |
|---------------|-------------|----------|
| **library-core** | Shared libraries consumed by other repos. Breaking changes affect the entire org. Strictest CI requirements. | `omnibase_core`, `omnibase_spi` |
| **toolchain** | Developer tools, CLI utilities, and build infrastructure. Must not break developer workflows. | `omniclaude`, `omniarchon` |
| **deployable-service** | Services that run in production. Require deployment-specific checks (container builds, health probes). | `omninode_bridge`, `omniintelligence` |
| **infrastructure-as-code** | Terraform, Docker Compose, and infrastructure definitions. Require plan validation and drift detection. | `omninode_infra` |

### Classification Rules

1. A repository has exactly one classification.
2. The classification is declared in `required-checks.yaml` under the `classification` key.
3. If not declared, the repository defaults to `deployable-service` (most common, most conservative).

---

## Check Tier System

CI checks are organized into four tiers based on scope, applicability, and enforcement policy.

### Tier A-Org: Universal Checks

**Scope**: Every OmniNode repository, regardless of classification.

**Enforcement**: Always required. No path filtering. Cannot be skipped.

**Rationale**: These checks enforce invariants that apply to the entire organization. Skipping them on any repository creates a gap in the org-wide quality floor.

| Check | What It Validates | Typical Job Name |
|-------|-------------------|------------------|
| Linting / Formatting | Code style consistency | `Code Quality` |
| License headers | OSS compliance | (embedded in lint) |
| Secret scanning | No credentials in code | (GitHub native or third-party) |
| Branch protection compliance | `required-checks.yaml` matches actual branch protection | (manual or automated) |

### Tier A-Runtime: Per-Technology Checks

**Scope**: Every repository using a given technology stack.

**Enforcement**: Always required for repos using that stack. No path filtering. Cannot be skipped.

**Rationale**: These checks are universal within a technology, but not across technologies. A Python repo needs mypy; a TypeScript repo needs tsc. The check is mandatory for any repo that uses the technology.

| Technology | Check | What It Validates | Typical Job Name |
|-----------|-------|-------------------|------------------|
| Python | Type checking (mypy strict) | Type safety | `Code Quality` |
| Python | Type checking (pyright) | Complementary type analysis | `Pyright Type Checking` |
| Python | Test suite | Functional correctness | `Tests Gate` |
| Python | Exports validation | `__all__` correctness | `Exports Validation` |
| TypeScript | `tsc --noEmit` | Type safety | `Type Check` |
| Docker | Container build | Image builds successfully | `Docker Build` |

### Tier B: Conditional Checks

**Scope**: Specific repositories, or specific paths within a repository.

**Enforcement**: Required when applicable, but may use path filtering. MUST NOT be listed as branch protection required checks if path-filtered (see [Invariant 3](#invariant-3-path-filtered-checks-and-branch-protection)).

**Rationale**: These checks validate domain-specific invariants that only matter when certain files change. Running them on every PR wastes CI minutes without catching additional issues.

| Check | Condition | What It Validates | Typical Job Name |
|-------|-----------|-------------------|------------------|
| Architecture handshake | `architecture-handshakes/**` changed | Cross-repo contract consistency | `Check architecture handshake` |
| DB ownership CI twin | `**/db/**` changed | Database ownership metadata | `DB ownership CI twin (B1)` |
| Transport import boundary | `src/**` changed | ADR-005 core-infra boundary | `Core-Infra Boundary` |
| Schema migration | `migrations/**` changed | Migration file validity | (repo-specific) |

### Tier C: Profile Checks

**Scope**: Optional quality profiles that repositories opt into.

**Enforcement**: Not required for merging. Informational. Failures produce warnings, not blocking errors.

**Rationale**: These checks provide additional quality signals but are not mature enough, not reliable enough, or not universally applicable enough to be required. They run but do not block.

| Check | What It Validates | Why Not Required |
|-------|-------------------|------------------|
| Documentation validation | Broken links, stale references | External link rot causes false positives |
| Node purity check | Declarative node purity guarantees | Existing tech debt (`continue-on-error: true`) |
| Coverage threshold | Code coverage percentage | Enforced on main only, not all PRs |
| Performance benchmarks | Regression detection | Noisy on shared runners |

### Tier Applicability Matrix

| Tier | library-core | toolchain | deployable-service | infrastructure-as-code |
|------|-------------|-----------|-------------------|----------------------|
| **A-Org** | Required | Required | Required | Required |
| **A-Runtime** | Required (per stack) | Required (per stack) | Required (per stack) | Required (per stack) |
| **B** | As applicable | As applicable | As applicable | As applicable |
| **C** | Optional | Optional | Optional | Optional |

---

## Gate Check Name Contract

### The Four Canonical Gates

Branch protection in OmniNode repositories uses exactly four gate names. These names are **API-stable** -- they are the contract surface between CI workflows and GitHub's branch protection system.

| Gate Name | Purpose | Scope |
|-----------|---------|-------|
| `Quality Gate` | Aggregates all Tier A code quality checks (lint, type checking, exports). Reports pass only when every constituent check passes. | All repos |
| `Tests Gate` | Aggregates all test execution. For matrix strategies, this is the single aggregator that branch protection references instead of individual shards. | All repos with tests |
| `Security Gate` | Aggregates security scanning (secret detection, dependency audit, SAST). | All repos |
| `CI Summary` | Final aggregator. Enumerates the status of all gates. Required when path filtering can cause any Tier A gate job to be skipped. See [CI Summary Semantics](#ci-summary-semantics). | Conditional |

### Gate Design Principles

1. **Gates are aggregators, not executors.** A gate job itself does no work. It depends on the actual check jobs and reports pass/fail based on their outcomes.
2. **Branch protection references gates, never individual jobs.** Individual jobs may be renamed, split, merged, or reorganized without affecting branch protection.
3. **Gate names are API-stable.** See [Invariant 1](#invariant-1-check-name-stability).
4. **Each gate covers exactly one concern.** Quality, testing, and security are separate gates. This allows independent evolution and clear failure attribution.

### Gate vs. Individual Check

```
Branch Protection          Gate (aggregator)           Individual Checks
─────────────────          ─────────────────           ─────────────────
requires: "Tests Gate" --> tests-gate job      ------> Tests (Split 1/20)
                           (if: always())              Tests (Split 2/20)
                           checks needs result         ...
                                                       Tests (Split 20/20)
```

Individual check names (like `Tests (Split 1/20)`) are internal implementation details. They can be renamed freely because branch protection never references them directly.

---

## required-checks.yaml v2 Schema

The `required-checks.yaml` file in `.github/` is the source of truth for what branch protection should require. The v2 schema separates operational gates from documentary check listings.

### Schema Definition

```yaml
# required-checks.yaml v2 schema
# Location: .github/required-checks.yaml

# REQUIRED: Schema version
schema_version: 2

# REQUIRED: Repository classification (see Repository Classifications)
classification: library-core | toolchain | deployable-service | infrastructure-as-code

# REQUIRED: The operational contract.
# These are the ONLY check names that branch protection should require.
# This list is the single source of truth for branch protection configuration.
gates:
  - name: "Quality Gate"          # Aggregates lint, type checking, exports
    workflow: test.yml
    rationale: "Aggregator for all Tier A code quality checks"

  - name: "Tests Gate"            # Aggregates test matrix
    workflow: test.yml
    rationale: "Aggregator for test matrix. Never require individual shards."

  - name: "Security Gate"         # Aggregates security checks
    workflow: security.yml
    rationale: "Aggregator for secret scanning and dependency audit"

  # CONDITIONAL: Required iff path filtering can skip any Tier A gate job.
  # See: CI Summary Semantics in CI_CD_STANDARDS.md
  - name: "CI Summary"
    workflow: test.yml
    rationale: "Final aggregator. Enumerates skips. Fails on missing gates."
    condition: "required_iff_path_filtering"

# OPTIONAL: Documentary listing of individual checks.
# This section is for human reference ONLY. It has NO operational effect.
# Branch protection MUST NOT reference check names from this section.
checks:
  # Tier A-Org
  - name: "Code Quality"
    tier: A-Org
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "ruff format + ruff check + mypy strict"

  - name: "Pyright Type Checking"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "Complementary type checking to mypy"

  - name: "Exports Validation"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "__all__ exports correctness"

  - name: "Mypy Validation Scripts"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "Type check CI scripts + transport import validation"

  - name: "Core-Infra Boundary"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "ADR-005 -- no transport/I/O imports in omnibase_core"

  - name: "Enum Governance Check"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "Enum architectural standards (OMN-1313)"

  # Tier A-Runtime (Tests)
  - name: "Tests (Split N/20)"
    tier: A-Runtime
    workflow: test.yml
    gate: "Tests Gate"
    rationale: "Matrix shards -- use Tests Gate aggregator instead"

  # Tier B (Conditional)
  - name: "Check architecture handshake"
    tier: B
    workflow: check-handshake.yml
    gate: null
    rationale: "Path-filtered -- skips on most PRs"
    paths: ["architecture-handshakes/**", ".claude/architecture-handshake.md"]

  - name: "DB ownership CI twin (B1)"
    tier: B
    workflow: check-db-ownership.yml
    gate: null
    rationale: "Path-filtered -- skips on most PRs"
    paths: ["**/db/**", "scripts/check_db_ownership.py"]

  # Tier C (Profile)
  - name: "Documentation Validation"
    tier: C
    workflow: test.yml
    gate: null
    rationale: "External link rot causes false positives. Non-blocking."

  - name: "Node Purity Check"
    tier: C
    workflow: test.yml
    gate: null
    rationale: "continue-on-error: true -- tech debt. Non-blocking."

  - name: "Test Summary"
    tier: C
    workflow: test.yml
    gate: null
    rationale: "Reporting/aggregation job, not a gate."
```

### Schema Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `schema_version` | Yes | `int` | Must be `2`. |
| `classification` | Yes | `string` | One of: `library-core`, `toolchain`, `deployable-service`, `infrastructure-as-code`. |
| `gates` | Yes | `list[Gate]` | Operational contract. Only these names go into branch protection. |
| `gates[].name` | Yes | `string` | API-stable check name. |
| `gates[].workflow` | Yes | `string` | Workflow file that produces this check. |
| `gates[].rationale` | Yes | `string` | Why this gate exists. |
| `gates[].condition` | No | `string` | When this gate is conditionally required. |
| `checks` | No | `list[Check]` | Documentary listing. No operational effect. |
| `checks[].name` | Yes | `string` | Human-readable check name. |
| `checks[].tier` | Yes | `string` | One of: `A-Org`, `A-Runtime`, `B`, `C`. |
| `checks[].workflow` | Yes | `string` | Workflow file that runs this check. |
| `checks[].gate` | Yes | `string | null` | Which gate aggregates this check, or `null` if not gated. |
| `checks[].rationale` | Yes | `string` | Why this check exists or why it is excluded. |
| `checks[].paths` | No | `list[string]` | Path filters (Tier B only). |

### v1 to v2 Migration

The v1 schema used `required_checks` and `excluded_checks` as flat lists. The v2 schema introduces:

1. **`gates`** as the only operational contract (replaces `required_checks` for branch protection).
2. **`checks`** as documentary-only (replaces both `required_checks` and `excluded_checks` with tier annotations).
3. **`classification`** to declare what type of repository this is.
4. **`schema_version`** to enable forward compatibility.

Repos can migrate incrementally. During migration, the v1 `required_checks` list remains authoritative until the repo explicitly sets `schema_version: 2`.

---

## Invariants

These invariants must hold across all OmniNode CI configurations. Violations indicate a misconfiguration that must be fixed before merging.

### Invariant 1: Check Name Stability

> **Gate `check_name` values are API-stable. Renaming a gate requires a coordinated branch protection update.**

Gate names (`Quality Gate`, `Tests Gate`, `Security Gate`, `CI Summary`) are referenced by GitHub branch protection as opaque strings. Renaming a gate without updating branch protection causes all PRs to become unmergeable because the old required check name will never appear.

**What this means in practice**:

- Do NOT rename a gate job's `name:` field in a workflow file without following the [Branch Protection Migration Safety](#branch-protection-migration-safety) procedure.
- Individual check names (non-gates) can be renamed freely because branch protection does not reference them.
- The `checks` section in `required-checks.yaml` is documentary and has no stability guarantee.

### Invariant 2: Single Source of Truth

> **The `gates` list is the only operational contract for branch protection. The `checks` section is documentation only.**

When configuring or auditing branch protection:

- Read the `gates` list to determine what branch protection should require.
- Ignore the `checks` list -- it exists for human understanding, not for tooling.

This separation exists because the `checks` list will grow and change as CI evolves, while the `gates` list should be small and stable.

### Invariant 3: Path-Filtered Checks and Branch Protection

> **A check that uses path filtering MUST NOT be listed as a branch protection required check.**

GitHub branch protection requires that a required check **reports a status** on every PR. Path-filtered checks do not run (and therefore do not report a status) when their paths are not modified. This causes PRs that do not touch those paths to be permanently blocked.

**Consequences**:

- Tier B checks must not appear in the `gates` list.
- If a Tier B check must become required, remove its path filter first (promoting it to Tier A-Runtime).
- The `CI Summary` gate exists specifically to detect when path filtering causes important checks to be skipped.

### Invariant 4: CI Summary Requirement Condition

> **`CI Summary` is REQUIRED if and only if path filtering can skip any Tier A gate job.**

If all Tier A checks run unconditionally on every PR, the `CI Summary` gate is optional (the individual gates already ensure completeness).

If any Tier A check uses path filtering (which would normally violate Invariant 3, but may occur during migration), `CI Summary` becomes required. It must:

1. Enumerate which gates were skipped and why.
2. Fail if any expected gate is missing (not skipped-by-policy, but genuinely absent).
3. Distinguish between **skipped-by-policy** (path filter matched no files, expected) and **misconfiguration** (gate job failed to register, unexpected).

---

## Branch Protection Migration Safety

When a gate check name must be renamed (e.g., consolidating `Code Quality` into `Quality Gate`), follow this procedure to avoid blocking all PRs.

### Standard Procedure

**Phase 1: Dual-Require (1 PR)**

1. Add the new gate name to the workflow (new aggregator job).
2. Keep the old gate name running (do not remove it yet).
3. Update `required-checks.yaml` to list both old and new gate names.
4. Update branch protection to require both old and new names.
5. Merge this PR.

**Phase 2: Verify (1-2 PRs)**

1. Open a test PR to verify both old and new gate names report status.
2. Confirm the test PR is mergeable.

**Phase 3: Remove Old (1 PR)**

1. Remove the old gate job from the workflow.
2. Remove the old gate name from `required-checks.yaml`.
3. Update branch protection to require only the new gate name.
4. Merge this PR.

### Why Three Phases?

Single-step renames create a window where either:

- The old name is required but no longer reported (PRs blocked), or
- The new name is required but not yet reported (PRs blocked).

The dual-require window ensures at least one valid check always exists.

### Applying Branch Protection

```bash
# Read gates from required-checks.yaml and apply to branch protection
gh api -X PUT repos/OmniNode-ai/<REPO>/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Quality Gate",
      "Tests Gate",
      "Security Gate",
      "CI Summary"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {"required_approving_review_count": 1},
  "restrictions": null
}
EOF
```

---

## CI Summary Semantics

The `CI Summary` job serves a specific purpose: it is the safety net for path-filtered CI configurations. It runs after all other jobs and produces a definitive pass/fail based on gate completeness.

### When CI Summary Is Required

`CI Summary` is required when **any** of the following conditions hold:

1. A workflow uses path filtering (`paths:` or `paths-ignore:`) on jobs that feed into a gate.
2. A gate aggregator uses `if: always()` and must distinguish between "upstream skipped" and "upstream failed".
3. The repository has Tier B checks whose absence could mask a gap in Tier A coverage.

### What CI Summary Must Do

```
For each gate in required-checks.yaml.gates:
  status = lookup_gate_status(gate.name)

  if status == "success":
    record(gate.name, PASSED)
  elif status == "failure":
    record(gate.name, FAILED)
    set_exit_code(1)
  elif status == "skipped" and gate.condition == "required_iff_path_filtering":
    record(gate.name, SKIPPED_BY_POLICY)
  elif status == "skipped" and gate.condition is None:
    record(gate.name, MISSING_GATE)
    set_exit_code(1)  # Unconditionally required gate was not reported
  elif status not found:
    record(gate.name, MISSING_GATE)
    set_exit_code(1)  # Gate job did not run at all

Output: table of gate statuses
Exit: 0 if all required gates passed, 1 otherwise
```

### Skipped-by-Policy vs. Misconfiguration

| Scenario | Status | CI Summary Action |
|----------|--------|-------------------|
| Gate job ran and passed | `success` | Record as PASSED |
| Gate job ran and failed | `failure` | Record as FAILED, exit 1 |
| Gate job skipped because path filter matched no files | `skipped` | Record as SKIPPED_BY_POLICY (if gate has `condition`) |
| Gate job did not run and has no `condition` | not found | Record as MISSING_GATE, exit 1 |
| Gate job not found in workflow at all | not found | Record as MISSING_GATE, exit 1 |

The distinction between SKIPPED_BY_POLICY and MISSING_GATE is critical. A skipped-by-policy check was intentionally not run because the relevant files were not modified. A missing gate indicates that the workflow is misconfigured and a required check is not being produced.

---

## Examples

### Example 1: omnibase_core (library-core, v2)

```yaml
schema_version: 2
classification: library-core

gates:
  - name: "Quality Gate"
    workflow: test.yml
    rationale: "Aggregates lint, mypy, pyright, exports, enum governance, core-infra boundary"

  - name: "Tests Gate"
    workflow: test.yml
    rationale: "Aggregates 20-split test matrix. Never require individual shards."

checks:
  - name: "Code Quality"
    tier: A-Org
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "ruff format + ruff check + mypy strict"

  - name: "Pyright Type Checking"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "Complementary type checking"

  - name: "Exports Validation"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "__all__ exports correctness"

  - name: "Mypy Validation Scripts"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "Type check CI scripts + transport import validation"

  - name: "Core-Infra Boundary"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "ADR-005 boundary enforcement"

  - name: "Enum Governance Check"
    tier: A-Runtime
    workflow: test.yml
    gate: "Quality Gate"
    rationale: "Enum architectural standards (OMN-1313)"

  - name: "Tests (Split N/20)"
    tier: A-Runtime
    workflow: test.yml
    gate: "Tests Gate"
    rationale: "Matrix shards"

  - name: "Check architecture handshake"
    tier: B
    workflow: check-handshake.yml
    gate: null
    rationale: "Path-filtered"
    paths: ["architecture-handshakes/**"]

  - name: "DB ownership CI twin (B1)"
    tier: B
    workflow: check-db-ownership.yml
    gate: null
    rationale: "Path-filtered"
    paths: ["**/db/**"]

  - name: "Documentation Validation"
    tier: C
    workflow: test.yml
    gate: null
    rationale: "Non-blocking (link rot)"

  - name: "Node Purity Check"
    tier: C
    workflow: test.yml
    gate: null
    rationale: "Non-blocking (tech debt)"
```

### Example 2: Deployable Service (deployable-service, v2)

```yaml
schema_version: 2
classification: deployable-service

gates:
  - name: "Quality Gate"
    workflow: ci.yml
    rationale: "Lint, type checking"

  - name: "Tests Gate"
    workflow: ci.yml
    rationale: "Unit and integration tests"

  - name: "Security Gate"
    workflow: security.yml
    rationale: "Dependency audit, secret scanning"

checks:
  - name: "Lint"
    tier: A-Org
    workflow: ci.yml
    gate: "Quality Gate"
    rationale: "Code style"

  - name: "Type Check"
    tier: A-Runtime
    workflow: ci.yml
    gate: "Quality Gate"
    rationale: "mypy strict"

  - name: "Unit Tests"
    tier: A-Runtime
    workflow: ci.yml
    gate: "Tests Gate"
    rationale: "Unit test suite"

  - name: "Integration Tests"
    tier: A-Runtime
    workflow: ci.yml
    gate: "Tests Gate"
    rationale: "Integration test suite"

  - name: "Docker Build"
    tier: A-Runtime
    workflow: ci.yml
    gate: "Quality Gate"
    rationale: "Container builds successfully"

  - name: "Dependency Audit"
    tier: A-Org
    workflow: security.yml
    gate: "Security Gate"
    rationale: "Known vulnerability scanning"
```

### Example 3: Gate Aggregator Job (Workflow Implementation)

```yaml
# In a GitHub Actions workflow file
jobs:
  # ... individual check jobs ...

  quality-gate:
    name: Quality Gate
    runs-on: ubuntu-latest
    needs: [lint, pyright, exports-validation, mypy-validation-scripts, core-infra-boundary, enum-governance]
    if: always()
    steps:
      - name: Check quality results
        run: |
          FAILED=false
          for result in \
            "${{ needs.lint.result }}" \
            "${{ needs.pyright.result }}" \
            "${{ needs.exports-validation.result }}" \
            "${{ needs.mypy-validation-scripts.result }}" \
            "${{ needs.core-infra-boundary.result }}" \
            "${{ needs.enum-governance.result }}"; do
            if [ "$result" != "success" ]; then
              FAILED=true
              echo "::error::Check failed with result: $result"
            fi
          done
          if [ "$FAILED" = "true" ]; then
            exit 1
          fi
          echo "All quality checks passed."

  tests-gate:
    name: Tests Gate
    runs-on: ubuntu-latest
    needs: [test-parallel]
    if: always()
    steps:
      - name: Check test results
        run: |
          if [ "${{ needs.test-parallel.result }}" != "success" ]; then
            echo "::error::Test matrix failed"
            exit 1
          fi
          echo "All test splits passed."
```

---

## Related Documentation

| Topic | Document |
|-------|----------|
| Current required checks (v1) | `.github/required-checks.yaml` |
| CI test strategy | `docs/testing/CI_TEST_STRATEGY.md` |
| CI monitoring guide | `docs/ci/CI_MONITORING_GUIDE.md` |
| Core-infra boundary (ADR-005) | `docs/decisions/ADR-005-core-infra-dependency-boundary.md` |
| Standard doc layout | `docs/standards/STANDARD_DOC_LAYOUT.md` |
| GitHub branch protection API | [GitHub Docs](https://docs.github.com/en/rest/branches/branch-protection) |

---

**Document Version**: 1.0.0
**Created**: 2026-02-14
**Author**: ONEX Framework Team
**Linear Ticket**: OMN-2224 (Phase 1)
