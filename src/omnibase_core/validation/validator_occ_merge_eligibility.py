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
from omnibase_core.validation.validator_receipt_gate import (
    _CONTRACT_SHA256_REQUIRED_AFTER,
    _extract_ticket_ids,
    _honestly_superseded_dod_ids,
    _iter_dod_evidence,
    check_receipt_contract_binding,
)
from omnibase_core.validation.validator_receipt_supersession import (
    resolve_supersession,
)

EVIDENCE_TICKET_PATTERN = re.compile(
    r"^\s*Evidence-Ticket\s*:\s*(OMN-\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
TICKET_TOKEN_PATTERN = re.compile(r"(?<![A-Z0-9])OMN-(\d+)(?![A-Z0-9])", re.IGNORECASE)

# OMN-16353: the OCC evidence repo, where a PR under evaluation is itself the
# companion carrying contracts/receipts and must self-bind via an
# `occ-self-bind-pr-<N>` entry. Callers pass either the short repo name (the
# CI workflows pass `REPO_SHORT`) or the org-qualified form.
_OCC_REPO_NAME = "onex_change_control"
_OCC_REPO_ORG = "OmniNode-ai"
_OCC_REPO_QUALIFIED = f"{_OCC_REPO_ORG}/{_OCC_REPO_NAME}"


def _is_occ_repo(repo: str) -> bool:
    """True only for the canonical OCC repo — bare name or exact org/name.

    Matches the short name (``onex_change_control``, what CI passes as
    ``REPO_SHORT``) or the exact canonical org-qualified name
    (``OmniNode-ai/onex_change_control``). Deliberately NOT a bare suffix
    match: a differently-owned repo that merely shares the short name (e.g.
    a fork under another org) must not be classified as the OCC evidence
    repo (CodeRabbit finding on OMN-16353's initial diff).
    """
    normalized = repo.strip().rstrip("/")
    return normalized in (_OCC_REPO_NAME, _OCC_REPO_QUALIFIED)


def _self_bind_remediation(ticket_id: str, pr_number: int) -> str:
    """Exact remedy for an OCC companion missing its self-bind (OMN-16353).

    Emitted only when everything else verifies: contracts resolve, receipts
    are PASS and hash-bound — the sole defect is that no receipt carries
    ``pr_number == <this OCC PR>``. Names the precise YAML entry and receipt
    path so the convention is taught at the moment of failure instead of
    costing a full CI round-trip of re-diagnosis.
    """
    entry_id = f"occ-self-bind-pr-{pr_number}"
    return (
        f"OCC evidence for {ticket_id} verifies (receipts PASS, hashes bound), "
        f"but no receipt binds to this OCC PR (#{pr_number}). "
        f"Add a self-bind entry to contracts/{ticket_id}.yaml:\n"
        "\n"
        f'  - id: "{entry_id}"\n'
        "    description: >-\n"
        f"      OCC self-binding receipt for PR #{pr_number}, the in-repo evidence PR\n"
        f"      carrying this contract. Binds {ticket_id} to the OCC PR by pr_number\n"
        "      so eligibility can resolve a PASS receipt for the evidence PR itself.\n"
        '    source: "manual"\n'
        '    status: "verified"\n'
        "    checks:\n"
        '      - check_type: "command"\n'
        "        check_value: >-\n"
        f"          gh pr view {pr_number} --repo {_OCC_REPO_QUALIFIED} "
        "--json number,state,headRefName\n"
        "\n"
        "then write a PASS receipt at "
        f"drift/dod_receipts/{ticket_id}/{entry_id}/command.yaml with "
        f"pr_number: {pr_number}. Recompute contract_sha256 on the EXISTING "
        f"receipts for {ticket_id} — the whole-file hash moves when the contract "
        "gains an entry; per-entry contract_entry_sha256 values do not "
        "(OMN-13888)."
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
    searchable_texts = (
        snapshot.pr_title,
        snapshot.pr_branch,
        *snapshot.pr_commit_texts,
    )
    bound_tickets = {
        f"OMN-{match.group(1)}".upper()
        for text in searchable_texts
        for match in TICKET_TOKEN_PATTERN.finditer(text)
    }
    evidence_tickets = {
        match.group(1).upper()
        for match in EVIDENCE_TICKET_PATTERN.finditer(snapshot.pr_body)
    }
    return ticket_id in bound_tickets or ticket_id in evidence_tickets


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
    # OMN-14404: stale contract bindings accumulate like every other failure
    # class in this function. Returning on the first one discards the other N-1
    # already-resolved receipts and costs the operator a full CI round per stale
    # receipt, which is what manufactured the #3965 -> #3966 -> #3968 -> #3969
    # serial OCC repair chain. Keys mirror `missing_or_nonpass_receipts`;
    # `stale_binding_details` holds the human-readable per-receipt message.
    stale_bindings: list[str] = []
    stale_binding_details: list[str] = []
    tickets_with_pr_bound_receipt: set[str] = set()

    def _stale_binding_result() -> ModelOccEligibilityResult:
        detail = "; ".join(stale_binding_details)
        if len(stale_bindings) > 1:
            detail = (
                f"{len(stale_bindings)} receipts have stale contract bindings "
                f"(repair all of them in one pass): {detail}"
            )
        return ModelOccEligibilityResult(
            eligible=False,
            reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
            ticket_ids=ticket_ids,
            occ_commit_sha=snapshot.occ_commit_sha,
            contract_hashes=contract_hashes,
            receipt_ids=tuple(sorted(receipt_ids)),
            stale_receipt_bindings=tuple(sorted(stale_bindings)),
            detail=detail,
        )

    for ticket_id in ticket_ids:
        contract_path = snapshot.contracts_dir / f"{ticket_id}.yaml"
        if not contract_path.is_file():
            missing_contracts.append(ticket_id)
            continue
        try:
            contract_data = _load_yaml(contract_path)
            contract_hash = _sha256_file(contract_path)
        except (OSError, yaml.YAMLError) as exc:
            missing_contracts.append(ticket_id)
            # OMN-14404: a stale binding found in an earlier iteration still
            # dominates, exactly as it did when the binding check returned
            # inline. Same guard at every hard-fail return below; it can only
            # fire on bindings from PRIOR iterations, because the binding check
            # is the last check in an iteration and `continue`s on failure.
            if stale_bindings:
                return _stale_binding_result()
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.MISSING_CONTRACT,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                contract_hashes=contract_hashes,
                missing_contracts=tuple(sorted(missing_contracts)),
                detail=f"contract {contract_path} is unreadable: {exc}",
            )
        contract_hashes[ticket_id] = contract_hash
        triples = _iter_dod_evidence(contract_data)
        if not triples:
            missing_receipts.append(f"{ticket_id}:*:*")
            continue
        dod_evidence_raw = (
            contract_data.get("dod_evidence", [])
            if isinstance(contract_data, dict)
            else []
        )
        honestly_superseded = _honestly_superseded_dod_ids(dod_evidence_raw)
        for evidence_item_id, check_type, _check_value in triples:
            if evidence_item_id in honestly_superseded:
                # OMN-15664 AC5: a later dod_evidence item's evidence_artifact
                # honestly supersedes this one (see
                # _honestly_superseded_dod_ids docstring for the exact
                # honesty conditions). This item's own receipt requirement is
                # excused; it is not silently dropped from the contract, and
                # contract_compliance_check independently reports it WARN
                # "superseded" rather than executing its (possibly dead)
                # checks.
                continue
            receipt_path = (
                snapshot.receipts_dir
                / ticket_id
                / evidence_item_id
                / f"{check_type}.yaml"
            )
            receipt_key = f"{ticket_id}:{evidence_item_id}:{check_type}"

            # OMN-13888 (scope 3): resolve the supersession chain first. A
            # tombstone invalidates the key (no active receipt); a replacement
            # re-binds it to a net-new receipt without editing the base file.
            # OMN-16432: current_pr_number scopes resolution to the record
            # that explicitly targets this consumer when a shared key is
            # bound to several downstream PRs.
            supersession = resolve_supersession(
                snapshot.receipts_dir,
                ticket_id,
                evidence_item_id,
                check_type,
                current_pr_number=snapshot.pr_number,
            )
            if supersession is not None:
                if supersession.error is not None:
                    nonpass_receipts.append(receipt_key)
                    if stale_bindings:
                        return _stale_binding_result()
                    return ModelOccEligibilityResult(
                        eligible=False,
                        reason=EnumOccEligibilityReason.NONPASS_RECEIPT,
                        ticket_ids=ticket_ids,
                        occ_commit_sha=snapshot.occ_commit_sha,
                        contract_hashes=contract_hashes,
                        receipt_ids=tuple(sorted(receipt_ids)),
                        missing_or_nonpass_receipts=tuple(sorted(nonpass_receipts)),
                        detail=supersession.error,
                    )
                if supersession.tombstoned or supersession.receipt is None:
                    missing_receipts.append(receipt_key)
                    continue
                receipt = supersession.receipt
                receipt_source = supersession.source_path
            else:
                if not receipt_path.exists():
                    missing_receipts.append(receipt_key)
                    continue
                try:
                    receipt_raw = _load_yaml(receipt_path)
                    receipt = ModelDodReceipt.model_validate(receipt_raw)
                except (OSError, yaml.YAMLError, ValidationError) as exc:
                    nonpass_receipts.append(receipt_key)
                    if stale_bindings:
                        return _stale_binding_result()
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
                receipt_source = receipt_path
            if receipt.ticket_id != ticket_id:
                if stale_bindings:
                    return _stale_binding_result()
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.PR_TICKET_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"receipt {receipt_source} declares ticket_id={receipt.ticket_id}, "
                        f"expected {ticket_id}"
                    ),
                )
            is_bound = _receipt_bound_to_pr(receipt, snapshot)
            # OMN-13888 (scope 1/5): dual-accept contract binding. A receipt
            # with a per-entry hash is checked strictly; a legacy receipt is
            # whole-file-checked only when bound to THIS PR (prior merged
            # receipts grandfather so appending an entry does not invalidate
            # them). The None hard-fail (OMN-10421 / OMN-13061) fires only when
            # BOTH bindings are absent.
            #
            # Round-1 soft-spot (verifier PROBE6): `is_bound` keys on the
            # receipt-controlled `pr_number`, so a NEW legacy-only receipt could
            # in principle set a FOREIGN pr_number to reach the grandfather path
            # and skip the whole-file check with a wrong hash. That path is NOT
            # independently exploitable end-to-end: a receipt can only be
            # introduced through an onex_change_control PR, and OCC's Receipt
            # Honesty Gate (scripts/validation/check_receipt_hardening.py, a
            # REQUIRED status check) validates every post-cutoff receipt's
            # contract_sha256 == sha256(contracts/<ticket>.yaml) UNCONDITIONAL on
            # pr_number — so a forged wrong-hash net-new receipt is rejected
            # upstream before this grandfather is ever reached. The grandfather
            # here is defense-in-depth behind that stricter gate; the terminal
            # fix is the per-entry hash (scope 1), which makes every new receipt
            # immune to appends without needing the whole-file grandfather at
            # all. Full closure of the pure-function residual (an unforgeable
            # "receipt file is net-new in this PR" git signal threaded from CI)
            # is tracked as follow-up and is disproportionate to wire here.
            if (
                receipt.contract_sha256 is None
                and receipt.contract_entry_sha256 is None
            ):
                if stale_bindings:
                    return _stale_binding_result()
                return ModelOccEligibilityResult(
                    eligible=False,
                    reason=EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH,
                    ticket_ids=ticket_ids,
                    occ_commit_sha=snapshot.occ_commit_sha,
                    contract_hashes=contract_hashes,
                    receipt_ids=tuple(sorted(receipt_ids)),
                    detail=(
                        f"receipt {receipt_source} missing both contract_sha256 and "
                        f"contract_entry_sha256 (OMN-10421 / OMN-13061 / OMN-13888): "
                        f"receipts produced after "
                        f"{_CONTRACT_SHA256_REQUIRED_AFTER.date()} must bind the "
                        "contract. Rerun probes to produce a new receipt."
                    ),
                )
            binding_error = check_receipt_contract_binding(
                receipt=receipt,
                contract_data=contract_data,
                evidence_item_id=evidence_item_id,
                whole_file_hash=contract_hash,
                is_bound_to_this_pr=is_bound,
            )
            if binding_error is not None:
                stale_bindings.append(receipt_key)
                stale_binding_details.append(
                    f"receipt {receipt_source}: {binding_error}"
                )
                continue
            if is_bound:
                tickets_with_pr_bound_receipt.add(ticket_id)
            if receipt.status is not EnumReceiptStatus.PASS:
                nonpass_receipts.append(receipt_key)
                continue
            receipt_ids.append(receipt_key)

    # OMN-14404: stale bindings are reported FIRST, ahead of MISSING_CONTRACT,
    # MISSING_RECEIPT/NONPASS_RECEIPT and the terminal unbound-ticket check. This
    # reproduces the pre-batching precedence exactly: the old in-loop early return
    # preempted every one of those post-loop checks, in every iteration order.
    if stale_bindings:
        return _stale_binding_result()
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
        if _is_occ_repo(snapshot.repo):
            # OMN-16353: reaching this branch means every contract resolved and
            # every required receipt is PASS and hash-bound — the ONLY defect is
            # that no receipt binds to THIS PR. On the OCC repo itself that is
            # the hand-authored-companion omission of the self-bind entry
            # (three occurrences in one 2026-08-21 session: OCC#6819, #6820,
            # #6675). The verdict is unchanged (ineligible either way);
            # only the reason and remediation differ — advisory-to-actionable.
            return ModelOccEligibilityResult(
                eligible=False,
                reason=EnumOccEligibilityReason.MISSING_OCC_SELF_BIND,
                ticket_ids=ticket_ids,
                occ_commit_sha=snapshot.occ_commit_sha,
                contract_hashes=contract_hashes,
                receipt_ids=tuple(sorted(receipt_ids)),
                detail="\n\n".join(
                    _self_bind_remediation(ticket_id, snapshot.pr_number)
                    for ticket_id in unbound_tickets
                ),
            )
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
