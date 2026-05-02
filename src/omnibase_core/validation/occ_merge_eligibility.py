# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic OCC-first merge eligibility checks.

This module is intentionally pure after the caller supplies a PR metadata
snapshot and a pinned OCC commit SHA. It does not fetch GitHub or mutate state.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.validation.model_occ_eligibility_input import (
    ModelOccEligibilityInput,
)
from omnibase_core.models.validation.model_occ_eligibility_result import (
    ModelOccEligibilityResult,
)
from omnibase_core.validation.receipt_gate import (
    _extract_ticket_ids,
    _iter_dod_evidence,
)

EVIDENCE_TICKET_PATTERN = re.compile(
    r"^\s*Evidence-Ticket\s*:\s*(OMN-\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=yaml.SafeLoader)


def _normalize_sha_set(values: tuple[str, ...]) -> set[str]:
    return {v.strip().lower() for v in values if v.strip()}


def _ticket_bound_to_pr(ticket_id: str, snapshot: ModelOccEligibilityInput) -> bool:
    needle = ticket_id.casefold()
    if needle in snapshot.pr_title.casefold():
        return True
    if needle in snapshot.pr_branch.casefold():
        return True
    if any(needle in text.casefold() for text in snapshot.pr_commit_texts):
        return True
    evidence_tickets = {
        match.group(1).upper()
        for match in EVIDENCE_TICKET_PATTERN.finditer(snapshot.pr_body)
    }
    return ticket_id in evidence_tickets


def _receipt_bound_to_pr(
    receipt: ModelDodReceipt,
    snapshot: ModelOccEligibilityInput,
) -> bool:
    if receipt.pr_number == snapshot.pr_number:
        return True
    shas = _normalize_sha_set(snapshot.pr_commit_shas)
    return receipt.commit_sha.lower() in shas


def validate_occ_merge_eligibility(
    snapshot: ModelOccEligibilityInput,
) -> ModelOccEligibilityResult:
    """Validate PR merge eligibility against a pinned OCC evidence snapshot."""

    ticket_ids = tuple(_extract_ticket_ids(snapshot.pr_body, snapshot.pr_title))
    if not ticket_ids:
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.MISSING_TICKET,
            occ_commit_sha=snapshot.occ_commit_sha,
            detail="PR title/body does not cite an OMN ticket",
        )

    for ticket_id in ticket_ids:
        if not _ticket_bound_to_pr(ticket_id, snapshot):
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                detail=(
                    f"{ticket_id} is cited but not bound through PR title, branch, "
                    "commit text, or Evidence-Ticket metadata"
                ),
            )

    contract_hashes: dict[str, str] = {}
    receipt_ids: list[str] = []
    missing_contracts: list[str] = []
    missing_receipts: list[str] = []
    nonpass_receipts: list[str] = []
    tickets_with_pr_bound_receipt: set[str] = set()

    for ticket_id in ticket_ids:
        contract_path = snapshot.contracts_dir / f"{ticket_id}.yaml"
        if not contract_path.exists():
            missing_contracts.append(ticket_id)
            continue
        contract_hash = _sha256_file(contract_path)
        contract_hashes[ticket_id] = contract_hash
        try:
            contract_data = _load_yaml(contract_path)
        except (OSError, yaml.YAMLError) as exc:
            missing_contracts.append(ticket_id)
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.MISSING_CONTRACT,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                contract_hashes=contract_hashes,
                missing_contracts=tuple(sorted(missing_contracts)),
                detail=f"contract {contract_path} is unreadable: {exc}",
            )
        triples = _iter_dod_evidence(contract_data)
        if not triples:
            missing_receipts.append(f"{ticket_id}:*:*")
            continue
        for evidence_item_id, check_type, _check_value in triples:
            receipt_path = (
                snapshot.receipts_dir
                / ticket_id
                / evidence_item_id
                / f"{check_type}.yaml"
            )
            receipt_key = f"{ticket_id}:{evidence_item_id}:{check_type}"
            if not receipt_path.exists():
                missing_receipts.append(receipt_key)
                continue
            try:
                receipt_raw = _load_yaml(receipt_path)
                receipt = ModelDodReceipt.model_validate(receipt_raw)
            except (OSError, yaml.YAMLError, ValidationError) as exc:
                nonpass_receipts.append(receipt_key)
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.NONPASS_RECEIPT,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    missing_or_nonpass_receipts=tuple(sorted(nonpass_receipts)),
                    detail=f"receipt {receipt_path} is invalid: {exc}",
                )
            if receipt.ticket_id != ticket_id:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"receipt {receipt_path} declares ticket_id={receipt.ticket_id}, "
                        f"expected {ticket_id}"
                    ),
                )
            if receipt.contract_sha256 is None:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=f"receipt {receipt_path} missing contract_sha256",
                )
            if receipt.contract_sha256 != contract_hash:
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"receipt {receipt_path} contract_sha256={receipt.contract_sha256} "
                        f"does not match pinned contract hash {contract_hash}"
                    ),
                )
            if _receipt_bound_to_pr(receipt, snapshot):
                tickets_with_pr_bound_receipt.add(ticket_id)
            if receipt.status is not EnumReceiptStatus.PASS:
                nonpass_receipts.append(receipt_key)
                continue
            receipt_ids.append(receipt_key)

    if missing_contracts:
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.MISSING_CONTRACT,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            missing_contracts=tuple(sorted(missing_contracts)),
            detail="one or more ticket contracts are missing from pinned OCC evidence",
        )
    if missing_receipts or nonpass_receipts:
        reason = (
            EnumOccEligibilityReason.MISSING_RECEIPT
            if missing_receipts
            else EnumOccEligibilityReason.NONPASS_RECEIPT
        )
        return ModelOccEligibilityResult(
            eligible=False,
            reason=reason,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            missing_or_nonpass_receipts=tuple(
                sorted([*missing_receipts, *nonpass_receipts])
            ),
            detail="one or more receipts are missing or non-PASS",
        )
    unbound_tickets = tuple(
        ticket_id
        for ticket_id in ticket_ids
        if ticket_id not in tickets_with_pr_bound_receipt
    )
    if unbound_tickets:
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            detail=(
                "no PASS receipt for one or more tickets binds to PR "
                f"#{snapshot.pr_number} or one of its commit SHAs: "
                f"{', '.join(unbound_tickets)}"
            ),
        )

    return ModelOccEligibilityResult(
        eligible=True,
        reason=EnumOccEligibilityReason.ELIGIBLE,
        ticket_ids=ticket_ids,
        occ_commit_sha=snapshot.occ_commit_sha,
        contract_hashes=contract_hashes,
        receipt_ids=tuple(sorted(receipt_ids)),
        detail="OCC evidence is present, PASS, hash-bound, and PR-bound",
    )


def _read_file(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OCC-first merge eligibility gate")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--pr-title", required=True)
    parser.add_argument("--pr-body", default=None)
    parser.add_argument("--pr-body-file", default=None)
    parser.add_argument("--pr-branch", required=True)
    parser.add_argument("--pr-commit-sha", action="append", default=[])
    parser.add_argument("--pr-commit-text", action="append", default=[])
    parser.add_argument("--occ-commit-sha", required=True)
    parser.add_argument("--contracts-dir", required=True)
    parser.add_argument("--receipts-dir", required=True)
    args = parser.parse_args(argv)

    body = args.pr_body if args.pr_body is not None else _read_file(args.pr_body_file)
    snapshot = ModelOccEligibilityInput(
        repo=args.repo,
        pr_number=args.pr_number,
        pr_title=args.pr_title,
        pr_body=body,
        pr_branch=args.pr_branch,
        pr_commit_shas=tuple(args.pr_commit_sha),
        pr_commit_texts=tuple(args.pr_commit_text),
        occ_commit_sha=args.occ_commit_sha,
        contracts_dir=Path(args.contracts_dir),
        receipts_dir=Path(args.receipts_dir),
    )
    result = validate_occ_merge_eligibility(snapshot)
    sys.stdout.write(f"{result.to_json()}\n")
    return 0 if result.eligible else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "EnumOccEligibilityReason",
    "ModelOccEligibilityInput",
    "ModelOccEligibilityResult",
    "validate_occ_merge_eligibility",
]
