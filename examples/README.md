# Example Contracts - Deprecation Notice

> **Compliance Notice**: Example workflow contracts should not be treated as
> current Core product documentation. Current example-contract guidance must
> live in this repository when it affects this repository.

## Current Status: DEPRECATED

This `examples/contracts/` directory will be moved in a future release:

**Target Location**: `docs/orchestrator_examples/` OR `omnibase_infra/examples/`

## Rationale (v1.0.5 Spec)

> "Example workflow contracts MUST NOT reside in omnibase_core. Examples belong in:
> `docs/orchestrator_examples/` OR `omnibase_infra/examples/`. Core repo contains
> only runtime logic. Test fixtures in Core SHOULD be minimal and focused on
> validation, not demonstration."

## Migration Plan

1. **Phase 1** (Current): Mark directory as deprecated with this notice
2. **Phase 2**: Create `docs/orchestrator_examples/` directory structure
3. **Phase 3**: Move example contracts to new location
4. **Phase 4**: Update all documentation references
5. **Phase 5**: Remove this directory

## Affected Files

The following example contracts will be migrated:

- `contracts/compute/user_profile_normalizer.yaml`
- `contracts/effect/*.yaml` (6 files)
- `contracts/orchestrator_data_pipeline.yaml`
- `contracts/reducer_metrics_aggregator.yaml`

## Temporary Usage

These examples remain functional during the deprecation period. Tests referencing
these files will be updated to use the new location after migration.

## Related

- **Ticket**: OMN-664 ([BETA-07] NodeOrchestrator v1.0.5 Compliance)
- **Spec context**: example-contract location guidance summarized in this file
- **Fix Reference**: v1.0.5 Fix 56 - Example Contract Location
