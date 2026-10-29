# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorEventDeclarationDrift -- ``check-event-registry-drift`` in the generic format (OMN-21416, OMN-21503).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_event_registry_drift`.
The emit registry (``topics.yaml``) is the validated target; the producer's
sources and the baseline are arguments. A source that is missing, unreadable,
oversized or malformed, a contract directory with no file or with no
``event_registration``, or a side that declares nothing, is an error, never a pass.

    python -m omnibase_core.validation.validator_event_registry_drift \\
        --source-contracts DIR [--source-document FILE] --registry-topics-yaml FILE [--baseline FILE]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.handlers.handler_event_registry_drift_sources import (
    parse_baseline,
    parse_emit_registry,
    parse_registration_contract,
    parse_registration_document,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_baseline import (
    ModelEventRegistryDriftBaseline,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input import (
    ModelEventRegistryDriftCheckInput,
)
from omnibase_core.validation.checker_event_registry_drift import (
    RULE_SOURCE_UNREADABLE,
    check_event_registry_drift,
    issue,
)
from omnibase_core.validation.checker_rule_parameters import rule_int, rule_strings
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorEventDeclarationDrift(ValidatorBase):
    """Compare a producer's declared event registrations with an emit registry."""

    validator_id: ClassVar[str] = "event_registry_drift"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        source_contracts: tuple[Path, ...] = (),
        source_documents: tuple[Path, ...] = (),
        baseline: Path | None = None,
    ) -> None:
        super().__init__(contract)
        self._source_contracts = source_contracts
        self._source_documents = source_documents
        self._baseline = baseline

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        unreadable = rules[RULE_SOURCE_UNREADABLE]
        limit = rule_int(unreadable, "max_file_bytes")
        globs = rule_strings(unreadable, "contract_globs")
        errors: list[str] = []

        def read(file: Path) -> str | None:
            try:
                if file.stat().st_size > limit:
                    errors.append(f"{file}: exceeds max file size {limit}")
                    return None
                return file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{file}: read error: {exc}")
                return None

        source: list[ModelEventRegistration] = []
        if not self._source_contracts and not self._source_documents:
            errors.append(
                "no source given: pass --source-contracts or --source-document"
            )
        for directory in self._source_contracts:
            files = sorted(
                {f for g in globs for f in directory.rglob(g) if f.is_file()}
                if directory.is_dir()
                else ()
            )
            if not files:
                errors.append(
                    f"{directory}: no contract file found (missing or empty directory); "
                    "a scan that reads nothing is ERROR, never PASS"
                )
            declared = 0
            read_failed = False
            for file in files:
                text = read(file)
                if text is None:
                    read_failed = True
                    continue
                registration, parse_errors = parse_registration_contract(
                    str(file), text
                )
                errors.extend(parse_errors)
                if registration is not None:
                    source.append(registration)
                    declared += 1
            if files and not read_failed and declared == 0:
                errors.append(
                    f"{directory}: no contract declares an event_registration; "
                    "empty discovery is ERROR, never PASS"
                )
        for document in self._source_documents:
            text = read(document)
            if text is None:
                continue
            parsed, parse_errors = parse_registration_document(str(document), text)
            source.extend(parsed)
            errors.extend(parse_errors)

        registry: tuple[ModelEventRegistration, ...] = ()
        text = read(path)
        if text is not None:
            registry, registry_errors = parse_emit_registry(str(path), text)
            errors.extend(registry_errors)

        baseline = ModelEventRegistryDriftBaseline()
        if self._baseline is not None:
            text = read(self._baseline)
            if text is not None:
                parsed_baseline, baseline_errors = parse_baseline(
                    str(self._baseline), text
                )
                errors.extend(baseline_errors)
                if parsed_baseline is not None:
                    baseline = parsed_baseline

        if errors:
            return tuple(
                issue(rules, RULE_SOURCE_UNREADABLE, str(path), error)
                for error in errors
            )
        return check_event_registry_drift(
            ModelEventRegistryDriftCheckInput(
                source_registrations=tuple(source),
                registry_registrations=registry,
                baseline=baseline,
            ),
            rules,
        )

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        """CLI entry: the emit registry is the target; sources and baseline are flags."""
        parser = argparse.ArgumentParser(
            prog="check-event-registry-drift",
            description=f"Run {cls.validator_id} validator",
        )
        parser.add_argument(
            "--source-contracts", action="append", default=[], type=Path
        )
        parser.add_argument("--source-document", action="append", default=[], type=Path)
        parser.add_argument("--registry-topics-yaml", required=True, type=Path)
        parser.add_argument("--baseline", default=None, type=Path)
        args = parser.parse_args(argv)
        validator = cls(
            source_contracts=tuple(args.source_contracts),
            source_documents=tuple(args.source_document),
            baseline=args.baseline,
        )
        registry: Path = args.registry_topics_yaml
        if not registry.is_file():
            sys.stdout.write(
                f"ERROR: [{RULE_SOURCE_UNREADABLE}] {registry}: not a readable file\n"
            )
            return 1
        result = validator.validate([registry])
        for found in result.issues:
            sys.stdout.write(
                f"{found.severity.value.upper()}: [{found.code}] {found.message}\n"
            )
        return validator.get_exit_code(result)


if __name__ == "__main__":
    sys.exit(ValidatorEventDeclarationDrift.main())
