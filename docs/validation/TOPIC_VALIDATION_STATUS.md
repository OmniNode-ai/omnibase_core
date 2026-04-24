# Topic Validation Status

**Owner:** `omnibase_core`
**Last verified:** 2026-04-24
**Verification:** `uv run onex-validate-topics . --verbose`, OMN-9599 docs pass

This page records the current Core-owned topic validation boundary.

## Current Validator

Core owns the topic validator entrypoint:

```bash
uv run onex-validate-topics . --verbose
```

The validator scans Python and TypeScript files that look topic-related and
checks `TOPIC_*` and `SUFFIX_*` constants against the canonical ONEX topic
format:

```text
onex.<kind>.<producer>.<event-name>.v<version>
```

See [Validation Ownership](../reference/VALIDATION_OWNERSHIP.md) for downstream
consumption rules.

## Current Result

As of 2026-04-24, the validator is present and runnable, but the repo still has
known cleanup failures:

```text
Scanned 28 files, found 17 topic constants
FAIL: 14 violation(s) found
```

Failure categories:

- Flat legacy topic taxonomy constants in
  `src/omnibase_core/constants/constants_topic_taxonomy.py`.
- Flat topic-kind values in
  `src/omnibase_core/models/validation/model_topic_suffix_parts.py`.
- Test fixture strings that intentionally exercise invalid or partial topic
  shapes.

## Cleanup Boundary

The umbrella plan
`docs/plans/2026-04-24-omnibase-core-hardcoded-topics-cleanup.md` tracks cleanup
sequencing. That plan is execution context, not the current topic architecture
source of truth.

Current truth lives in:

- `onex-validate-topics`
- [Validation Ownership](../reference/VALIDATION_OWNERSHIP.md)
- [ONEX Topic Taxonomy](../standards/onex_topic_taxonomy.md)

## Documentation Rule

Docs may describe the current failure state, but they must not present invalid
legacy topic strings as current examples unless the example is clearly marked as
invalid, historical, or test-fixture context.
