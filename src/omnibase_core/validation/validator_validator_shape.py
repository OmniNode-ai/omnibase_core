# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorValidatorShape -- the ``validator_shape`` entry (OMN-21494).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_validator_shape`:
reads one node contract and the modules beside it, judges the modules with the
no-I/O-outside-effects checker as a compute node, builds typed facts and hands them to
the pure checker. This module is the input effect around the validator; the checker
holds the rules, and the rules are data in ``contracts/validator_shape.validation.yaml``.

    python -m omnibase_core.validation.validator_validator_shape [paths...]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_no_io_outside_effects_facts import (
    ModelNoIoOutsideEffectsFacts,
)
from omnibase_core.models.validation.model_validator_shape_node_fact import (
    ModelValidatorShapeNodeFact,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_no_io_outside_effects import (
    check_no_io_outside_effects,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings
from omnibase_core.validation.checker_validator_shape import (
    RULE_ARCHETYPE,
    RULE_SCOPE,
    check_node,
)
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_no_io_outside_effects import (
    ValidatorNoIoOutsideEffects,
)


class ValidatorValidatorShape(ValidatorBase):
    """Refuse a validator node that is not a pure compute node with a bound handler."""

    validator_id: ClassVar[str] = "validator_shape"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        if RULE_SCOPE not in rules or path.name != rule_string(
            rules[RULE_SCOPE], "contract_filename"
        ):
            return ()
        return check_node(path, _read_node(path, rules), rules)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _dig(data: object, key: str) -> object:
    return data.get(key) if isinstance(data, dict) else None


def _read_node(
    path: Path, rules: dict[str, ModelValidatorRule]
) -> ModelValidatorShapeNodeFact:
    scope = rules[RULE_SCOPE]
    data = load_yaml_mapping_no_duplicates(_text(path), source=str(path))
    tags = _dig(data, rule_string(scope, "tags_key"))
    routing = _dig(data, rule_string(scope, "handler_routing_key"))
    default = _dig(routing, rule_string(scope, "default_handler_key"))
    listed = _dig(routing, rule_string(scope, "handlers_key"))
    bindings = [default] if isinstance(default, str) and default else []
    if isinstance(listed, list):
        bindings.extend(item for item in listed if item)
    purity = _dig(
        _dig(data, rule_string(scope, "descriptor_key")),
        rule_string(scope, "purity_key"),
    )
    node_type = _dig(data, rule_string(scope, "node_type_key"))
    return ModelValidatorShapeNodeFact(
        directory_name=path.parent.name,
        tags=tuple(str(t) for t in tags) if isinstance(tags, list) else (),
        node_type=str(node_type or ""),
        purity=str(purity or ""),
        handler_bindings=tuple(str(b) for b in bindings),
        compute_step_io=_compute_step_io(path, rules),
    )


def _compute_step_io(
    path: Path, rules: dict[str, ModelValidatorRule]
) -> tuple[str, ...]:
    """Every no-I/O finding of the node's modules, judged as the archetype a validator must be."""
    scope = rules[RULE_SCOPE]
    judged_as = rule_string(rules[RULE_ARCHETYPE], "required_node_type")
    contract = ModelSourceFile(
        path=path.as_posix(),
        source=f"{rule_string(scope, 'node_type_key')}: {judged_as}\n",
    )
    no_io_rules = {r.rule_id: r for r in ValidatorNoIoOutsideEffects().contract.rules}
    return tuple(
        f"{issue.file_path}: {issue.message}"
        for pattern in rule_strings(scope, "compute_step_module_globs")
        for module in sorted(path.parent.rglob(pattern))
        for issue in check_no_io_outside_effects(
            ModelNoIoOutsideEffectsFacts(
                contract=contract,
                module=ModelSourceFile(path=module.as_posix(), source=_text(module)),
            ),
            no_io_rules,
        )
    )


__all__ = ["ValidatorValidatorShape"]

if __name__ == "__main__":
    sys.exit(ValidatorValidatorShape.main())
