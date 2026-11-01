# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for ``hardcoded_model_literals``: the hardcoded-model-config scan of one file.

``replay`` builds the scan the way ``runtime_hardcoded_model_config`` does: the policy is the
assertion's ``policy`` fact (the policy file at the audited revision) plus the private lab
vocabulary, the path class comes from that policy, and the rule rows of families O, G, F, P,
S, H and B are the rows of the contract handed in (``run.contract``), so an ``enabled: false``
row silences its family. Families T and N are judged by ``checker_hardcoded_model_tier`` and E
by the endpoint scan, both inside ``handler.scan`` under the policy; they have no contract row.

A finding counts for an assertion only on the asserted line (``source.line``).

Spelling of an issue, one scheme for ``replay`` and ``replay_fixture``: ``code`` is the id of
the contract row of the finding's family (the checker's own issue code), or the qualified
family spelling when the family has no row; ``rule_name`` is always the qualified family
spelling ``<scanner package name>:<family>``, so ``driver.reported_ids`` yields both the row
id and the corpus spelling.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    build_container,
    capture_environment,
    resolve_private_vocabulary,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.private_vocabulary import ModelPrivateVocabularyResolution
from omnibase_core.models.validation.model_hardcoded_literal_rule_set import (
    ModelHardcodedLiteralRuleSet,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation import hardcoded_model_config as scanner_package
from omnibase_core.validation.checker_hardcoded_model_literals import (
    check_text,
    load_rule_set,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.hardcoded_model_config.handler import scan
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigFinding,
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    load_policy,
)
from omnibase_core.validation.validator_hardcoded_model_scan import is_scanned
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope

_FAMILY_KEY = "family"
_REGISTRY_KEY = "registry_contract"
_REGISTRY_FAMILY = "P"
_VOCABULARY_NAME = "hardcoded_model_config_lab_denylist"
_PREFIX = scanner_package.__name__.rsplit(".", 1)[-1]


def _qualified(family: str) -> str:
    return f"{_PREFIX}:{family}"


@functools.cache
def _vocabulary() -> ModelPrivateVocabularyResolution:
    """The private vocabulary as the runtime resolves it (neutral when it is absent)."""
    container = build_container()
    return resolve_private_vocabulary(
        container,
        _VOCABULARY_NAME,
        environment=capture_environment(container),
        now=datetime.now(UTC),
    )


@functools.cache
def _layer_map(registry_path: str) -> ModelRepoLayerMap:
    package = resources.files("omnibase_core")
    node = package
    for part in registry_path.split("/"):
        node = node.joinpath(part)
    return load_yaml_content_as_model(node.read_text("utf-8"), ModelRepoLayerMap)


def _rule_set(
    contract: ReplayContract, policy: ModelHardcodedModelConfigPolicy
) -> ModelHardcodedLiteralRuleSet:
    """The rule rows of ``contract`` and the repository facts, as ``load_literal_rule_set``."""
    rules = contract.subcontract.rules
    by_family = {rule_string(rule, _FAMILY_KEY): rule for rule in rules}
    layer_map = _layer_map(rule_string(by_family[_REGISTRY_FAMILY], _REGISTRY_KEY))
    return load_rule_set(
        rules,
        github_org=layer_map.github_org,
        repository_names=[entry.repo for entry in layer_map.repos],
        host_names=policy.lab_host_names,
        python_suffixes=policy.python_suffixes,
        slash_comment_suffixes=policy.slash_comment_suffixes,
        no_comment_suffixes=policy.no_comment_suffixes,
        exclude_patterns=contract.subcontract.exclude_patterns,
    )


def _row_ids(contract: ReplayContract) -> dict[str, str]:
    """The id of the contract row of each family it carries."""
    return {
        rule_string(rule, _FAMILY_KEY): rule.rule_id
        for rule in contract.subcontract.rules
    }


def _issue(
    contract: ReplayContract, finding: ModelHardcodedModelConfigFinding
) -> ModelValidationIssue:
    row_id = _row_ids(contract).get(finding.family)
    qualified = _qualified(finding.family)
    return ModelValidationIssue(
        severity=EnumSeverity(contract.subcontract.severity_default),
        message=f"{qualified}: {finding.matched_text}",
        code=row_id or qualified,
        file_path=Path(finding.path),
        line_number=finding.line,
        rule_name=qualified,
        context={"family": finding.family, "matched": finding.matched_text},
    )


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    contract = run.contract
    text = source.text(source.path)
    if text is None or contract is None:
        return ()
    policy = load_policy(_vocabulary())
    if not is_scanned(source.path, policy):
        return ()
    findings = scan(source.path, text, policy, _rule_set(contract, policy))
    return [
        _issue(contract, finding)
        for finding in findings
        if source.line is None or finding.line == source.line
    ]


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture of the rule rows: a file judged by ``check_text`` under the rows."""
    policy = load_policy(_vocabulary())
    rules = _rule_set(contract, policy)
    files = [fixture] if fixture.is_file() else sorted(fixture.rglob("*"))
    issues: list[ModelValidationIssue] = []
    for target in files:
        if not target.is_file():
            continue
        relative = (
            target.name if fixture.is_file() else target.relative_to(fixture).as_posix()
        )
        if not in_scope(contract, relative):
            continue
        for issue in check_text(relative, target.read_text(encoding="utf-8"), rules):
            family = (issue.context or {}).get(_FAMILY_KEY, "")
            issues.append(issue.model_copy(update={"rule_name": _qualified(family)}))
    return issues
