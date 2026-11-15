# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorNodeNoCaller -- ``node_no_caller`` entry (OMN-24538, fail-open ratchets, class iv).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_node_no_caller`: it reads every node
contract under its root once (the topics each directory publishes) and every text file of the scanned
extensions once (the node names each file mentions; a file that names more distinct nodes than the catalog
threshold is a catalog and never a caller), then holds each contract it is handed to its entry in
``.onex_ratchets/node_no_caller_ratchet.yaml``. A file or contract that exists but cannot be read raises
instead of leaving the index short, which would flag nodes that are called. The scope and every rule value
live in ``contracts/node_no_caller.validation.yaml``.

Usage (pre-commit hook ``node-no-caller``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_node_no_caller:ValidatorNodeNoCaller --baseline .onex_ratchets/node_no_caller_ratchet.yaml <files...>
"""

from __future__ import annotations

import fnmatch
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.validation.checker_node_no_caller import (
    RULE_NODE_NO_CALLER,
    check_node_no_caller,
    read_node_facts,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)
from omnibase_core.validation.validator_baselined_detector import (
    ValidatorBaselinedDetector,
)

__all__ = ["ValidatorNodeNoCaller"]


class ValidatorNodeNoCaller(ValidatorBaselinedDetector):
    """Read one node contract and judge it against the repository index and its baseline entry."""

    validator_id: ClassVar[str] = "node_no_caller"
    _repo_index: (
        tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str]]] | None
    ) = None

    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        return check_node_no_caller(path, source, lambda: self._index(rules), rules)

    def _index(
        self, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str]]]:
        if self._repo_index is None:
            self._repo_index = self._build_index(rules)
        return self._repo_index

    def _build_index(
        self, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str]]]:
        row = rules[RULE_NODE_NO_CALLER]
        contract_file = rule_string(row, "contract_file")
        extensions = frozenset(rule_strings(row, "scanned_extensions"))
        excluded = rule_strings(row, "excluded_dir_names")
        threshold = rule_int(row, "catalog_file_node_threshold")
        token_patterns = [
            re.compile(p) for p in rule_strings(row, "name_token_patterns")
        ]
        strip = rule_string(row, "name_token_strip")
        texts: dict[str, str] = {}
        for directory, subdirs, files in os.walk(self._root):
            subdirs[:] = sorted(
                d for d in subdirs if not any(fnmatch.fnmatch(d, p) for p in excluded)
            )
            for name in sorted(files):
                if Path(name).suffix in extensions:
                    full = Path(directory) / name
                    texts[self._key(full)] = _read(full)
        publishers: dict[str, set[str]] = {}
        names: set[str] = set()
        for key, text in texts.items():
            if Path(key).name != contract_file:
                continue
            facts = read_node_facts(Path(key), text, rules)
            if facts is None:
                raise ModelOnexError(
                    message=f"{key}: the node contract does not parse as a YAML mapping",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            names.update((facts[0], Path(key).parent.name))
            for topic in facts[2]:
                publishers.setdefault(topic, set()).add(Path(key).parent.as_posix())
        named_in: dict[str, set[str]] = {}
        for key, text in texts.items():
            tokens = {
                found.rstrip(strip)
                for pattern in token_patterns
                for found in pattern.findall(text)
            }
            mentioned = names.intersection(tokens)
            if len(mentioned) > threshold:
                continue
            for name in mentioned:
                named_in.setdefault(name, set()).add(key)
        return (
            {t: frozenset(d) for t, d in publishers.items()},
            {n: frozenset(f) for n, f in named_in.items()},
        )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""
    except OSError as exc:
        raise ModelOnexError(
            message=f"{path}: cannot read a file the node index scans: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
