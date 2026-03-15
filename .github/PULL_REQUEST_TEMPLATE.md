## Summary

<!-- Brief description of changes -->

## Changes

<!-- List of changes made -->

## Test plan

<!-- How were these changes tested? -->

## Type safety checklist
- [ ] No new `metadata["key"]` or `metadata.get("key")` string literal access on Pydantic model fields
- [ ] No new `metadata: dict[str, Any]` fields without TypedDict or `# ONEX_EXCLUDE:` comment
- [ ] No new bare `except Exception` — must use narrowed type, or minimal-scope boundary with `logger.exception(...)` + degrade comment, or typed wrap/re-raise
- [ ] If adding a key to a metadata dict, the key is defined in the relevant TypedDict

## Related issues

<!-- OMN-XXXX -->
