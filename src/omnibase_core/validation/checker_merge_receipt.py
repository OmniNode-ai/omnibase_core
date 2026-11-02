# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure merge-side receipt checker: supplied facts and contract in, issues out (OMN-21926).

A runtime-affecting pull request needs a machine-written receipt from a branch deployment
at its exact head. Which paths run, which receipt sources are machine-written, and what
each refusal cause says are rule-row parameters of
``contracts/merge_receipt.validation.yaml``; this module holds none. It performs no I/O and
is report-only: the result's exit code is zero whatever it finds.
"""

from __future__ import annotations

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.merge_receipt.model_merge_receipt_check_input import (
    ModelMergeReceiptCheckInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_check_result import (
    ModelMergeReceiptCheckResult,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_pr import (
    ModelMergeReceiptPr,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_record import (
    ModelMergeReceiptRecord,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_rules import (
    ModelMergeReceiptRules,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_verdict import (
    ModelMergeReceiptVerdict,
)

__all__ = ["check_merge_receipt"]


def _same_repo(receipt: ModelMergeReceiptRecord, pr: ModelMergeReceiptPr) -> bool:
    """A receipt names its repository bare or owner-qualified; an unnamed one matches."""
    if not receipt.repo:
        return True
    return receipt.repo.rsplit("/", 1)[-1].lower() == pr.repo.lower()


def _about_this_pr(receipt: ModelMergeReceiptRecord, pr: ModelMergeReceiptPr) -> bool:
    """Whether a receipt of another sha is an earlier head of this same pull request."""
    return (receipt.pr_number != 0 and receipt.pr_number == pr.number) or (
        receipt.branch != "" and receipt.branch == pr.head_ref
    )


def _issue(
    rules: ModelMergeReceiptRules,
    request: ModelMergeReceiptCheckInput,
    pr: ModelMergeReceiptPr,
    code: str,
    detail: str,
) -> ModelValidationIssue | None:
    row = rules.row(code)
    if not row.enabled or not row.judges(request.source_name):
        return None
    context = {
        "repo": pr.repo,
        "number": str(pr.number),
        "head": pr.head_sha,
        "detail": detail,
    }
    return ModelValidationIssue(
        severity=row.severity,
        message=row.message.format(**context),
        code=code,
        rule_name=code,
        context=context,
    )


def check_merge_receipt(
    request: ModelMergeReceiptCheckInput,
) -> ModelMergeReceiptCheckResult:
    """Judge which runtime-affecting pull requests lack a receipt at their exact head."""
    rules = ModelMergeReceiptRules.from_contract(request.contract)
    sources = rules.row("receipt_sources").lists["machine_sources"]
    lab_line = rules.row("lab_line_not_receipt").pattern("lab_line_pattern")
    found: list[ModelValidationIssue] = []
    verdicts: list[ModelMergeReceiptVerdict] = []
    skipped = 0
    for pr in request.pull_requests:
        if not any(rules.is_runtime_path(path) for path in pr.changed_paths):
            skipped += 1
            continue
        counted = [r for r in pr.receipts if r.source in sources and _same_repo(r, pr)]
        if any(r.sha == pr.head_sha for r in counted):
            verdicts.append(
                ModelMergeReceiptVerdict(
                    repo=pr.repo,
                    number=pr.number,
                    head_sha=pr.head_sha,
                    would_refuse=False,
                    causes=(),
                )
            )
            continue
        stale = sorted(
            {r.sha for r in counted if r.sha != pr.head_sha and _about_this_pr(r, pr)}
        )
        candidates = (
            _issue(rules, request, pr, "receipt_missing", ""),
            _issue(rules, request, pr, "receipt_stale_head", ",".join(stale))
            if stale
            else None,
            _issue(rules, request, pr, "lab_line_not_receipt", "")
            if lab_line.search(pr.body)
            else None,
        )
        issues = [c for c in candidates if c is not None]
        found.extend(issues)
        verdicts.append(
            ModelMergeReceiptVerdict(
                repo=pr.repo,
                number=pr.number,
                head_sha=pr.head_sha,
                would_refuse=True,
                causes=tuple(i.code for i in issues if i.code),
            )
        )
    return ModelMergeReceiptCheckResult(
        issues=tuple(found),
        verdicts=tuple(verdicts),
        examined=len(verdicts),
        would_refuse=sum(1 for v in verdicts if v.would_refuse),
        skipped=skipped,
        exit_code=0,
    )
