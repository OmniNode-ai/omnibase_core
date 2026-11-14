# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generic file validator: a tracker payload is admitted only when bound to a commitment (OMN-22850)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.ticket_creation.model_ticket_creation_document import (
    ModelTicketCreationDocument,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_ticket_creation import (
    LedgerLineLookup,
    check_ticket_creation,
    rows_of,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorTicketCreation", "ledger_line_lookup"]


def ledger_line_lookup(ledger: Path | None) -> LedgerLineLookup:
    """Bind a ledger citation to the rolling ledger and its rolled archive.

    A cited path resolves by file name: the ledger itself, else the same name under its
    ``archive`` directory. Symlinks are never followed and an unreadable file resolves
    nothing, so an unreadable ledger admits nothing.
    """

    def lookup(path: str, line: int) -> bool:
        if ledger is None or line < 1:
            return False
        name = Path(path).name
        candidates = [ledger] if name == ledger.name else []
        archive = ledger.parent / "archive"
        if archive.is_dir() and not archive.is_symlink():
            candidates.append(archive / name)
        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            return line <= len(lines) and bool(lines[line - 1].strip())
        return False

    return lookup


class ValidatorTicketCreation(ValidatorBase):
    """Read one recorded payload, judge it with the pure checker and the contract's rule data."""

    validator_id: ClassVar[str] = "ticket_creation"

    def _get_contract_path(self) -> Path:
        """Find the committed contract alongside the base validator's contracts."""
        return (
            Path(validator_base.__file__).parent
            / "contracts"
            / "ticket_creation.validation.yaml"
        )

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            document = ModelTicketCreationDocument.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read the ticket payload: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        ledger = Path(document.ledger_path) if document.ledger_path else None
        result = check_ticket_creation(
            document.tool_input,
            contract,
            lane=document.lane,
            ledger_line_exists=ledger_line_lookup(ledger),
            route=document.route,
            route_switch=document.route_switch,
            current_description=document.current_description,
        )
        rows = rows_of(contract)
        return tuple(
            ModelValidationIssue(
                severity=rows[finding.code].severity,
                message=f"[{finding.code}] {finding.field}: {finding.reason}",
                code=finding.code,
                file_path=path,
                rule_name=finding.code,
                suggestion=finding.fix,
            )
            for finding in result.findings
        )


if __name__ == "__main__":
    sys.exit(ValidatorTicketCreation.main())
