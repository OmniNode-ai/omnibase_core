# v0.4.0 Release Gate Checklist (Hardened)

> **Version**: 0.4.0
> **Status**: Pre-release
> **Last Updated**: 2025-12-14
> **Linear Ticket**: [OMN-218](https://linear.app/omninode/issue/OMN-218)

This checklist defines **hard release gates** for v0.4.0.
All items are mandatory unless explicitly marked as informational.
All checks require **verifiable evidence**. No exceptions, no vibes.

---

## 1. Code Quality

- [ ] **All nodes pure-checked (AST)**
  - Run AST purity checker on all node implementations
  - Command: `poetry run python -m omnibase_core.tools.ast_checker`
  - Expected: 0 violations
  - Evidence: Attached output

- [ ] **Strict type safety enforced**
  - Command: `poetry run mypy src/omnibase_core/ --strict`
  - Expected: 0 errors
  - Evidence: CI run or local output

- [ ] **Pre-commit hooks pass**
  - Command: `pre-commit run --all-files`
  - Hooks: black, isort, ruff, mypy
  - Evidence: CI log or screenshot

---

## 2. Testing

- [ ] **CI passes all parallel test splits**
  - All splits succeed
  - No retries, no flaky allowances
  - Expected runtime: 2m30s-3m30s per split
  - Evidence: CI link

- [ ] **Adapter fuzz testing completed**
  - All adapters fuzzed with randomized inputs
  - No crashes or undefined behavior
  - Evidence: Fuzz test report

- [ ] **Coverage threshold met**
  - Minimum: 60% line coverage
  - Command: `poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing`
  - Evidence: Coverage report

- [ ] **Negative-path tests present**
  - At least one failure-mode test per contract class
  - Explicit assertions on error shape
  - Evidence: Test file references

---

## 3. Determinism & Replayability

- [ ] **Deterministic execution verified**
  - Identical inputs produce identical outputs
  - Hash comparison of emitted ModelActions or events
  - Evidence: Test output with hashes

- [ ] **Replay validation completed**
  - At least one representative workflow replayed end-to-end
  - Replay output matches original execution exactly
  - Evidence: Replay log comparison

---

## 4. Contracts & Architecture

- [ ] **All contracts have valid fingerprints**
  - Every RuntimeHostContract YAML includes a fingerprint
  - Fingerprints verified against contract content
  - Evidence: Contract fingerprint report

- [ ] **Fingerprint enforcement validated**
  - Modified contract fails verification
  - No fallback or silent acceptance
  - Evidence: Failing test output

- [ ] **All nodes are contract-driven**
  - No legacy node implementations remain
  - Command: `grep -r "NodeComputeLegacy\|NodeReducerLegacy\|NodeOrchestratorLegacy" src/`
  - Expected: Empty output
  - Evidence: Command output

---

## 5. Registry & Discovery Integrity

- [ ] **Registry loads all contracts**
  - No orphaned or unreachable contracts
  - Evidence: Registry load log

- [ ] **Contract-to-node resolution verified**
  - Every fingerprint resolves to a runnable node
  - Evidence: Resolution test results

---

## 6. Versioning & Upgrade Safety

- [ ] **Semantic versioning enforced**
  - Version bump aligns with documented breaking changes
  - Evidence: CHANGELOG and tag comparison

- [ ] **Upgrade behavior verified**
  - v0.3.x -> v0.4.0 upgrade path documented and tested
  - Evidence: Migration test or documented failure mode

- [ ] **Downgrade behavior declared**
  - Either:
    - Downgrade tested and supported
    - Downgrade explicitly unsupported and fails fast
  - Evidence: Documentation or test

---

## 7. Dependency & Build Reproducibility

- [ ] **Dependency lock verified**
  - poetry.lock committed and intentional
  - No untracked dependency drift
  - Evidence: Git diff

- [ ] **Reproducible install verified**
  - Fresh environment install using lockfile only
  - Tests pass in clean environment
  - Evidence: CI or local install log

---

## 8. Observability & Diagnostics

- [ ] **Structured error payloads enforced**
  - Errors include:
    - contract_id
    - fingerprint
    - node_id
  - Evidence: Error object snapshot

- [ ] **Failure events emitted**
  - Node failures emit observable events
  - No silent failures
  - Evidence: Event log excerpt

---

## 9. Cross-Repository Compatibility

- [ ] **Dependent repositories validated**
  - API compatibility confirmed
  - No breaking integration regressions
  - Evidence: Downstream test results

---

## 10. Documentation

- [ ] **Documentation updated**
  - CLAUDE.md reflects v0.4.0 architecture
  - Node building guides updated
  - Migration guide complete (if applicable)
  - CHANGELOG.md updated
  - Evidence: Documentation PR or commit

- [ ] **Breaking changes documented**
  - Each breaking change listed
  - Explicit migration instructions provided
  - Evidence: CHANGELOG section

---

## Verification Commands

```bash
# Type checking
poetry run mypy src/omnibase_core/ --strict

# Run tests
poetry run pytest tests/

# Coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# Pre-commit
pre-commit run --all-files

# Legacy pattern check
grep -r "NodeComputeLegacy\|NodeReducerLegacy\|NodeOrchestratorLegacy" src/

# Contract fingerprint verification
poetry run python -m omnibase_core.tools.verify_fingerprints
```

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| Release Manager | | | |

---

## Release Notes Template

```markdown
## v0.4.0 Release Notes

### Highlights
- [Major changes]

### Breaking Changes
- [Breaking changes with migrations]

### New Features
- [New features]

### Bug Fixes
- [Bug fixes]

### Documentation
- [Docs updated]

### Dependencies
- [Dependency updates]
```

---

## Post-Release Verification

- [ ] PyPI package published successfully
- [ ] Git tag created
- [ ] GitHub release published
- [ ] Documentation site updated
- [ ] Dependent repositories updated
