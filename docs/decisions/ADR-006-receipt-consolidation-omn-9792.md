# ADR-006: Receipt Type Consolidation onto ModelDodReceipt (OMN-9792)

**Date:** 2026-04-27
**Ticket:** OMN-9792
**Status:** Accepted

## Context

A scan on 2026-04-26 identified two near-duplicate receipt-shaped types that diverged
from the canonical `ModelDodReceipt`:

- `omniclaude.EvidenceReceipt` — a `@dataclass` in the DoD evidence runner with
  7 fields: `ticket_id`, `timestamp`, `git_sha`, `branch`, `working_dir`,
  `contract_path`, `result`.
- `onex_change_control.ModelVerifierCheckResult` — a Pydantic model used as items
  in `ModelVerifierOutput.checks` with fields: `name`, `passed`, `message`,
  `failure_class`.

Leaving both in place creates ongoing schema drift and forces callers to maintain
knowledge of three distinct receipt types with overlapping semantics.

## Decision

### EvidenceReceipt → ModelDodReceipt

Extend `ModelDodReceipt` with two optional fields (`branch`, `working_dir`) to
absorb the extra provenance information carried by `EvidenceReceipt`. The `result`
field is intentionally **not** migrated — it is an aggregate run summary, not a
per-check receipt. The runner constructs one `ModelDodReceipt` per evidence check
using the field mappings below:

| EvidenceReceipt field | ModelDodReceipt field |
|-----------------------|-----------------------|
| `ticket_id` | `ticket_id` |
| `timestamp` | `run_timestamp` |
| `git_sha` | `commit_sha` |
| `branch` | `branch` (new optional field) |
| `working_dir` | `working_dir` (new optional field) |
| `contract_path` | `check_value` |
| `result.details[i].checks[j].status` | `status` (mapped to `EnumReceiptStatus`) |

### ModelVerifierCheckResult → ModelDodReceipt

`ModelVerifierOutput.checks` is re-typed from `tuple[ModelVerifierCheckResult, ...]`
to `tuple[ModelDodReceipt, ...]`. The `failure_class` field on `ModelVerifierCheckResult`
is encoded in `probe_stdout` (the captured stderr/stdout of the verification command).
The `passed` field is derived from `status == PASS`.

The `ModelVerifierCheckResult` class and the `model_verifier_output.py` file are
**deleted**; no backwards-compat re-exports are added per CLAUDE.md policy.

### Forward-compatibility with OMN-9132

OMN-9132 will extend `ModelDodReceipt` with a required `post_merge_probe` field
(`ModelPostMergeProbe`). That field is intentionally **not** added here to preserve
the non-breaking nature of this PR. OMN-9132 owns that addition.

## Consequences

- Single receipt type across omnibase_core, omniclaude, and onex_change_control.
- `EvidenceReceipt` dataclass deleted from omniclaude.
- `ModelVerifierCheckResult` deleted from onex_change_control.
- `ModelDodReceipt` gains two optional fields; all existing receipts remain valid
  (no migration required — both fields default to `None`).
- `ModelVerifierOutput.checks` type changes from `tuple[ModelVerifierCheckResult, ...]`
  to `tuple[ModelDodReceipt, ...]`; callers must be updated.
