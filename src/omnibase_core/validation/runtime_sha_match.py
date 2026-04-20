# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""runtime_sha_match DoD gate — OMN-9356.

Addresses: "code on main, runtime not redeployed" (root cause of OMN-9321 class).

A ticket whose dod_evidence contains check_type=runtime_sha_match CANNOT
transition to Done without a PASS receipt proving the deployed runtime SHA
matches the merge SHA. No advisory mode — this is a hard block.

Receipt actual_output must be a JSON blob matching ModelRuntimeShaMatchOutput.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_runtime_sha_classify_result import (
    ModelRuntimeShaClassifyResult,
)
from omnibase_core.models.contracts.ticket.model_runtime_sha_match_output import (
    ModelRuntimeShaMatchOutput,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

CHECK_TYPE_RUNTIME_SHA_MATCH = "runtime_sha_match"


def classify_runtime_sha_match_receipt(
    receipt: ModelDodReceipt,
) -> ModelRuntimeShaClassifyResult:
    """Classify a runtime_sha_match receipt as blocking or not.

    Args:
        receipt: A ModelDodReceipt with check_type == CHECK_TYPE_RUNTIME_SHA_MATCH.

    Returns:
        ModelRuntimeShaClassifyResult with blocking=True when the receipt proves
        the runtime is stale or the output is unparseable.

    Raises:
        ModelOnexError: If receipt.check_type is not runtime_sha_match.
    """
    if receipt.check_type != CHECK_TYPE_RUNTIME_SHA_MATCH:
        raise ModelOnexError(
            message=(
                f"classify_runtime_sha_match_receipt called with check_type="
                f"{receipt.check_type!r}; expected {CHECK_TYPE_RUNTIME_SHA_MATCH!r}"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    if receipt.status is not EnumReceiptStatus.PASS:
        return ModelRuntimeShaClassifyResult(
            valid=True,
            blocking=True,
            reason=f"receipt status is {receipt.status.value} (not PASS)",
        )

    if not receipt.actual_output:
        return ModelRuntimeShaClassifyResult(
            valid=True,
            blocking=True,
            reason="actual_output is missing — cannot verify SHA match without probe output",
        )

    try:
        raw = json.loads(receipt.actual_output)
        output = ModelRuntimeShaMatchOutput.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        return ModelRuntimeShaClassifyResult(
            valid=True,
            blocking=True,
            reason=f"actual_output is not valid ModelRuntimeShaMatchOutput JSON: {exc}",
        )

    if not output.match or output.deployed_sha != output.merge_sha:
        return ModelRuntimeShaClassifyResult(
            valid=True,
            blocking=True,
            reason=(
                f"SHA mismatch: deployed_sha={output.deployed_sha!r} "
                f"!= merge_sha={output.merge_sha!r}"
            ),
        )

    return ModelRuntimeShaClassifyResult(
        valid=True,
        blocking=False,
        reason="PASS: deployed_sha matches merge_sha",
    )


def assert_runtime_sha_receipts_present(
    *,
    ticket_id: str,
    evidence_items: list[ModelDodEvidenceItem],
    receipts: list[ModelDodReceipt],
) -> None:
    """Block Done transition if any runtime_sha_match evidence lacks a PASS receipt.

    Args:
        ticket_id: Linear ticket ID (e.g., OMN-9356).
        evidence_items: Parsed dod_evidence items from the ticket contract.
        receipts: All receipts available for this ticket.

    Raises:
        ModelOnexError: If any runtime_sha_match check has no PASS receipt or the
            receipt classifies as blocking.
    """
    sha_checks: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    for item in evidence_items:
        for check in item.checks:
            if check.check_type == CHECK_TYPE_RUNTIME_SHA_MATCH:
                if item.id in seen_keys:
                    raise ModelOnexError(
                        message=(
                            f"evidence item {item.id!r} has multiple runtime_sha_match checks; "
                            "only one check per (evidence_item_id, check_type) is supported"
                        ),
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
                seen_keys.add(item.id)
                sha_checks.append((item.id, check.check_value))

    if not sha_checks:
        return

    receipt_index: dict[tuple[str, str], ModelDodReceipt] = {
        (r.evidence_item_id, r.check_type): r
        for r in receipts
        if r.check_type == CHECK_TYPE_RUNTIME_SHA_MATCH
    }

    failures: list[str] = []
    for item_id, _check_value in sha_checks:
        key = (item_id, CHECK_TYPE_RUNTIME_SHA_MATCH)
        if key not in receipt_index:
            failures.append(
                f"{ticket_id}/{item_id}/runtime_sha_match: no receipt found — "
                "run the runtime SHA probe and produce a PASS receipt before marking Done"
            )
            continue

        receipt = receipt_index[key]
        result = classify_runtime_sha_match_receipt(receipt)
        if result.blocking:
            failures.append(
                f"{ticket_id}/{item_id}/runtime_sha_match: blocking — {result.reason}"
            )

    if failures:
        raise ModelOnexError(
            message=(
                "runtime_sha_match DoD gate FAILED — ticket cannot be marked Done:\n"
                + "\n".join(f"  - {f}" for f in failures)
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )


__all__ = [
    "CHECK_TYPE_RUNTIME_SHA_MATCH",
    "classify_runtime_sha_match_receipt",
    "assert_runtime_sha_receipts_present",
]
