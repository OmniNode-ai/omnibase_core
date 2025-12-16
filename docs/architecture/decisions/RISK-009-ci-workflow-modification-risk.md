# RISK-009: CI Workflow Modification Risk

**Status**: 🟢 **MITIGATED**
**Date**: 2025-12-10
**Owner**: Platform Team
**Related**: PR #149, ADR-001-protocol-based-di-architecture.md

---

## Summary

Future changes to `.github/workflows/test.yml` could accidentally disable the full transport import scan on protected branches (main/master), potentially allowing dependency inversion violations to be merged.

---

## Risk Details

### Description

The CI workflow implements a "B+ hybrid mode" for transport import validation:

- **Changed-files mode** on feature branches (fast feedback, ~15 seconds)
- **Full scan mode** on protected branches main/master (comprehensive validation)

This protection relies on conditional logic in the workflow file:

```yaml
if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
```

A future modification to the workflow could:
1. Accidentally remove or alter this conditional
2. Disable the full scan step entirely
3. Change the branch detection logic incorrectly
4. Remove the transport import check step altogether

### Impact

**Severity**: High

If full scan is disabled on protected branches:
- Transport import violations could be merged to main
- Dependency inversion architecture would be compromised
- `omnibase_core` could gain unwanted dependencies on higher-level packages
- Breaking changes could propagate to downstream consumers

### Likelihood

**Probability**: Medium

Workflow files are modified during:
- CI optimization efforts
- GitHub Actions version updates
- New check additions
- Performance tuning

Without explicit protection, these modifications may not receive sufficient review focus on the transport import logic.

---

## Mitigation Strategy

### 1. CODEOWNERS Protection (Primary)

Add CODEOWNERS entry requiring platform team review for workflow changes:

```text
# CI/CD workflow changes require platform team review
/.github/workflows/ @OmniNode-ai/platform-team
```

This ensures workflow modifications receive dedicated review from team members who understand the transport import protection requirements.

### 2. Inline Documentation (Secondary)

The workflow file includes comments explaining the protection logic:

```yaml
# CRITICAL: This step runs on PROTECTED branches (main/master) only
# to ensure full transport import validation before merge.
# See RISK-009 for details on why this protection exists.
```

### 3. Architecture Documentation (Tertiary)

- `docs/architecture/DEPENDENCY_INVERSION.md` documents the import rules
- `docs/ci/` contains CI-specific documentation
- This risk register provides traceability

### 4. Test Coverage (Supporting)

The transport import checker itself has unit tests ensuring:
- Changed-files mode works correctly
- Full scan mode detects all violations
- Branch detection logic is correct

---

## Monitoring

### Indicators of Risk Materialization

1. **CI workflow changes without platform team approval** - CODEOWNERS violation
2. **Transport import violations on main branch** - Detection failure
3. **Missing full-scan job in main branch CI runs** - Protection disabled

### Detection Mechanisms

- GitHub branch protection requires CODEOWNERS approval
- Post-merge transport import scan (if implemented) would catch missed violations
- Periodic architecture review includes CI workflow audit

---

## Acceptance Criteria

The risk is considered mitigated when:

- [x] CODEOWNERS file includes workflow protection
- [x] Workflow file includes inline documentation referencing this risk
- [x] Risk documented in architecture decisions
- [ ] Platform team trained on transport import requirements (ongoing)

---

## Related Documentation

- [DEPENDENCY_INVERSION.md](../DEPENDENCY_INVERSION.md) - Import rules and architecture
- [CI_MONITORING_GUIDE.md](../../ci/CI_MONITORING_GUIDE.md) - CI health monitoring
- [ADR-001](./ADR-001-protocol-based-di-architecture.md) - Protocol-based DI architecture

---

## Changelog

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-10 | Initial risk documentation | Platform Team |

---

**Review Schedule**: Quarterly or upon CI workflow modifications
