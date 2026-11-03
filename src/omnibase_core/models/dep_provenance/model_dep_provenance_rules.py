# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict, typed interpretation of the dependency provenance validation subcontract (OMN-22011)."""

from __future__ import annotations

import string
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.dep_provenance.model_dep_provenance_finding import (
    ModelDepProvenanceFinding,
)
from omnibase_core.models.dep_provenance.model_dep_provenance_vocabulary import (
    ModelDepProvenanceVocabulary,
)

__all__ = ["ModelDepProvenanceRules"]

VOCABULARY_RULE = "source_vocabulary"
SHAPE_RULE = "source_shape_not_admitted"
REPOSITORY_RULE = "dev_tag_foreign_repository"
FOREIGN_RULE = "foreign_git_source"
INVALID_RULE = "invalid_pyproject"

# The fields a message template may name; the checker fills exactly these.
_FIELDS: dict[str, frozenset[str]] = {
    "message@" + SHAPE_RULE: frozenset({"package", "keys", "admitted", "line"}),
    "message@" + REPOSITORY_RULE: frozenset(
        {"package", "tag", "git", "expected", "line"}
    ),
    "message@" + FOREIGN_RULE: frozenset({"package", "keys", "line"}),
    "message@" + INVALID_RULE: frozenset({"detail"}),
}


def _invalid(rule_id: str, detail: str) -> ModelOnexError:
    return ModelOnexError(
        message=f"dep_provenance rule {rule_id!r}: {detail}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def _template(rule_id: str, key: str, text: str) -> None:
    allowed = _FIELDS.get(f"{key}@{rule_id}", _FIELDS.get(key))
    if allowed is None:
        return
    try:
        names = {
            field.split(".")[0].split("[")[0]
            for _, field, _, _ in string.Formatter().parse(text)
            if field
        }
        text.format(**dict.fromkeys(allowed, "x"))
    except (ValueError, IndexError, KeyError) as exc:
        raise _invalid(rule_id, f"{key} is not a usable template: {exc!r}") from exc
    if not names <= allowed:
        raise _invalid(
            rule_id, f"{key} names {sorted(names - allowed)} not in {sorted(allowed)}"
        )


class ModelDepProvenanceRules(BaseModel):
    """All rule parameters must validate before a file can pass."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    RULE_IDS: ClassVar[frozenset[str]] = frozenset(
        {
            VOCABULARY_RULE,
            SHAPE_RULE,
            REPOSITORY_RULE,
            FOREIGN_RULE,
            INVALID_RULE,
        }
    )
    rows: dict[str, ModelValidatorRule]
    vocabulary: ModelDepProvenanceVocabulary
    shape: ModelDepProvenanceFinding
    repository: ModelDepProvenanceFinding
    foreign: ModelDepProvenanceFinding
    invalid: ModelDepProvenanceFinding

    @classmethod
    def from_contract(
        cls, contract: ModelValidatorSubcontract
    ) -> ModelDepProvenanceRules:
        """Reject missing/unknown rules and malformed parameters, even if disabled."""
        rows = {row.rule_id: row for row in contract.rules}
        if set(rows) != cls.RULE_IDS or len(rows) != len(contract.rules):
            raise _invalid(
                "*", f"requires exactly the declared rules {sorted(cls.RULE_IDS)}"
            )
        if not rows[VOCABULARY_RULE].enabled:
            raise _invalid(VOCABULARY_RULE, "must be enabled")
        for rule_id, row in rows.items():
            for key, value in (row.parameters or {}).items():
                if isinstance(value, str):
                    _template(rule_id, key, value)

        def parse[T: BaseModel](rule_id: str, model: type[T]) -> T:
            try:
                parsed = model.model_validate(rows[rule_id].parameters)
            except ValidationError as exc:
                raise _invalid(rule_id, str(exc)) from exc
            for key, value in parsed.model_dump(mode="json").items():
                if key in {"remediation", "message"} and not str(value).strip():
                    raise _invalid(rule_id, f"parameter {key!r} must be non-empty")
            return parsed

        return cls(
            rows=rows,
            vocabulary=parse(VOCABULARY_RULE, ModelDepProvenanceVocabulary),
            shape=parse(SHAPE_RULE, ModelDepProvenanceFinding),
            repository=parse(REPOSITORY_RULE, ModelDepProvenanceFinding),
            foreign=parse(FOREIGN_RULE, ModelDepProvenanceFinding),
            invalid=parse(INVALID_RULE, ModelDepProvenanceFinding),
        )
