# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure lab-receipt checker: supplied facts and contract in, issues out (OMN-21823).

A change that runs needs a receipt that its exact head was installed on the lab and
observed running. Which files run, what a receipt must name and which observations
count as proof are rule-row parameters of ``contracts/lab_receipt.validation.yaml``;
this module holds none. It performs no I/O.
"""

from __future__ import annotations

from omnibase_core.enums.enum_lab_receipt_phase import EnumLabReceiptPhase
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.lab_receipt.model_lab_receipt_check_input import (
    ModelLabReceiptCheckInput,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_check_result import (
    ModelLabReceiptCheckResult,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_facts import (
    ModelLabReceiptFacts,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_record import (
    ModelLabReceiptRecord,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_rules import (
    ModelLabReceiptRules,
)

__all__ = ["check_lab_receipt"]


def _counted_classes(
    rules: ModelLabReceiptRules, facts: ModelLabReceiptFacts
) -> tuple[list[str], int]:
    """Class names of the counted files, in first-seen order, and how many files count."""
    row = rules.row("receipt_required")
    statuses = row.lists["counted_statuses"]
    names: dict[str, None] = {}
    count = 0
    for changed in facts.changed_files:
        if changed.status[:1] not in statuses:
            continue
        where = (facts.repository, changed.path)
        if any(c.selects(*where) for c in rules.classes["prod_classes"]):
            continue
        operative = [c for c in rules.classes["operative_classes"] if c.selects(*where)]
        if operative:
            names[operative[0].name] = None
            count += 1
            continue
        if any(c.selects(*where) for c in rules.classes["exempt_classes"]):
            continue
        runtime = [c for c in rules.classes["runtime_classes"] if c.selects(*where)]
        names[runtime[0].name if runtime else row.texts["unclassified_class"]] = None
        count += 1
    return list(names), count


def _corroborated(receipt: ModelLabReceiptRecord, facts: ModelLabReceiptFacts) -> bool:
    revision = receipt.installed_revision.lower()
    return any(
        read.host == receipt.host
        and read.running
        and (
            read.installed_revision.lower().startswith(revision)
            or revision.startswith(read.installed_revision.lower())
        )
        for read in facts.lab_reads or ()
    )


class _Issues:
    """Collects the issues of one run for the rows that apply to its phase and source."""

    def __init__(
        self, rules: ModelLabReceiptRules, request: ModelLabReceiptCheckInput
    ) -> None:
        self.rules = rules
        self.request = request
        self.found: list[ModelValidationIssue] = []

    def add(self, code: str, **fields: str) -> None:
        """Record an issue of rule ``code`` when its row is enabled here."""
        row = self.rules.row(code)
        if not self.rules.runs_in(code, self.request.document.phase):
            return
        if not row.judges(self.request.source_name):
            return
        context = {
            "head": self.request.document.facts.head_sha,
            "host": "",
            "installer": "",
            "revision": "",
            "field": "",
            "count": "",
            "classes": "",
            "ticket": "",
            "detail": "",
            **fields,
        }
        self.found.append(
            ModelValidationIssue(
                severity=row.severity,
                message=row.message.format(**context),
                code=code,
                rule_name=code,
                context=context,
            )
        )


def _judge_receipt(
    rules: ModelLabReceiptRules,
    facts: ModelLabReceiptFacts,
    receipt: ModelLabReceiptRecord,
    sink: _Issues,
) -> None:
    """Judge one receipt that names the PR head; an omitted field is judged once."""
    revision = receipt.installed_revision
    text = receipt.observation
    revision_row = rules.row("receipt_revision_not_head")
    observation_row = rules.row("receipt_observation_unproven")
    for field in rules.row("receipt_field_missing").lists["required_fields"]:
        if not getattr(receipt, field):
            sink.add("receipt_field_missing", host=receipt.host, field=field)
    installers = rules.row("receipt_installer_undeclared").lists["installers"]
    if receipt.installer and not any(
        receipt.installer.startswith(n) for n in installers
    ):
        sink.add("receipt_installer_undeclared", installer=receipt.installer)
    if revision and not (
        revision_row.pattern("revision_pattern").search(revision)
        and facts.head_sha.lower().startswith(revision.lower())
    ):
        sink.add("receipt_revision_not_head", host=receipt.host, revision=revision)
    if text and (
        not observation_row.pattern("length_pattern").search(text)
        or not any(p.search(text) for p in rules.observed)
        or any(p.search(text) for p in rules.refused)
    ):
        sink.add("receipt_observation_unproven", host=receipt.host, detail=text)
    if (
        facts.lab_reads is not None
        and receipt.host
        and revision
        and not _corroborated(receipt, facts)
    ):
        sink.add("receipt_not_on_lab", host=receipt.host, revision=revision)


def check_lab_receipt(request: ModelLabReceiptCheckInput) -> ModelLabReceiptCheckResult:
    """Judge whether a change needs a lab receipt and whether the receipt is sound."""
    rules = ModelLabReceiptRules.from_contract(request.contract)
    facts = request.document.facts
    sink = _Issues(rules, request)
    classes, count = _counted_classes(rules, facts)
    required = count > 0
    if required:
        counted = {"count": str(count), "classes": ",".join(classes)}
        criterion = rules.row("receipt_criterion_missing").pattern("criterion_pattern")
        if not any(criterion.search(c.statement) for c in facts.criteria):
            sink.add("receipt_criterion_missing", **counted)
        if not facts.receipts:
            sink.add("receipt_required", **counted)
        head_receipts = [r for r in facts.receipts if r.head_sha == facts.head_sha]
        if facts.receipts and not head_receipts:
            sink.add(
                "receipt_head_mismatch",
                detail=",".join(r.head_sha for r in facts.receipts),
            )
        for receipt in head_receipts:
            _judge_receipt(rules, facts, receipt, sink)
        if (
            request.document.phase is EnumLabReceiptPhase.VERIFY
            and facts.lab_reads is None
        ):
            sink.add("lab_read_unavailable")
    return ModelLabReceiptCheckResult(
        issues=tuple(sink.found),
        exit_code=1
        if any(issue.severity.is_error_or_above() for issue in sink.found)
        else 0,
        required=required,
        classes=tuple(classes),
    )
