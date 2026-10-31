# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure dev-tag lineage parsing and decisions over supplied remote facts."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_dev_tag_lineage_candidate import (
    ModelDevTagLineageCandidate,
)
from omnibase_core.models.validation.model_dev_tag_lineage_facts import (
    ModelDevTagLineageFacts,
)
from omnibase_core.models.validation.model_dev_tag_lineage_invariant_policy import (
    ModelDevTagLineageInvariantPolicy,
)
from omnibase_core.models.validation.model_dev_tag_lineage_lock_entry import (
    ModelDevTagLineageLockEntry,
)
from omnibase_core.models.validation.model_dev_tag_lineage_policy import (
    ModelDevTagLineagePolicy,
)
from omnibase_core.models.validation.model_dev_tag_lineage_rule_parameters import (
    ModelDevTagLineageRuleParameters,
)
from omnibase_core.models.validation.model_dev_tag_lineage_verifier_pin_policy import (
    ModelDevTagLineageVerifierPinPolicy,
)


def invalid(message: str) -> ModelOnexError:
    """A structured failure to establish valid input or policy."""
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def load_policy(contract: ModelValidatorSubcontract) -> ModelDevTagLineagePolicy:
    """Validate the complete blocking rule set and its typed parameters."""
    required = {
        "tag_absent",
        "tag_suffix_mismatch",
        "tag_off_branch",
        "declared_version_mismatch",
        "lock_mismatch",
        "lineage_unresolved",
        "first_party_not_dev_tag",
        "first_party_version_override",
        "first_party_release_only",
        "verifier_version_pin",
    }
    ids = [rule.rule_id for rule in contract.rules]
    if set(ids) != required or len(ids) != len(required):
        raise invalid("dev_tag_lineage requires exactly its ten rule rows")
    if (
        not contract.fail_on_error
        or contract.max_violations != 0
        or contract.suppression_comments
    ):
        raise invalid("dev_tag_lineage requires blocking rules and no suppressions")
    policy: ModelDevTagLineagePolicy | None = None
    for rule in contract.rules:
        if not rule.enabled or rule.severity != EnumSeverity.ERROR:
            raise invalid(
                f"dev_tag_lineage rule must be enabled and error severity: {rule.rule_id}"
            )
        parameters = dict(rule.parameters or {})
        ModelDevTagLineageRuleParameters.model_validate(
            {key: parameters.pop(key) for key in ("phase", "message", "remediation")}
        )
        if rule.rule_id == "lineage_unresolved":
            policy = ModelDevTagLineagePolicy.model_validate(parameters)
        elif rule.rule_id == "first_party_not_dev_tag":
            ModelDevTagLineageInvariantPolicy.model_validate(parameters)
        elif rule.rule_id == "verifier_version_pin":
            ModelDevTagLineageVerifierPinPolicy.model_validate(parameters)
        elif parameters:
            raise invalid(f"unexpected rule parameters: {rule.rule_id}")
    if policy is None:
        raise invalid("dev_tag_lineage git policy is missing")
    for pattern in (
        policy.tag_pattern,
        policy.suffix_pattern,
        policy.commit_pattern,
        policy.normalize_pattern,
        policy.declaration_pattern,
    ):
        re.compile(pattern)
    return policy


def load_verifier_pin_policy(
    contract: ModelValidatorSubcontract,
) -> ModelDevTagLineageVerifierPinPolicy:
    """The typed parameters of the verifier_version_pin rule row."""
    row = next(
        (rule for rule in contract.rules if rule.rule_id == "verifier_version_pin"),
        None,
    )
    if row is None:
        raise invalid("dev_tag_lineage verifier_version_pin rule is missing")
    parameters = dict(row.parameters or {})
    for key in ("phase", "message", "remediation"):
        parameters.pop(key, None)
    return ModelDevTagLineageVerifierPinPolicy.model_validate(parameters)


def normalize(package: str, policy: ModelDevTagLineagePolicy) -> str:
    """Normalize source, declaration, filter and lock names with the contract pattern."""
    return re.sub(policy.normalize_pattern, "-", package).lower()


def _table(document: Mapping[str, object], dotted: str) -> object:
    value: object = document
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _declarations(
    document: Mapping[str, object], policy: ModelDevTagLineagePolicy
) -> dict[str, list[str]]:
    """Collect declarations from each configured list or grouped declaration table."""
    declarations: dict[str, list[str]] = {}
    for table in policy.declaration_tables:
        entries = _table(document, table)
        if entries is None:
            continue
        channels = entries.values() if isinstance(entries, dict) else (entries,)
        for channel in channels:
            if not isinstance(channel, list):
                raise invalid(f"invalid dependency table: {table}")
            for entry in channel:
                if (
                    isinstance(entry, dict)
                    and set(entry) == {"include-group"}
                    and isinstance(entry["include-group"], str)
                ):
                    continue
                if not isinstance(entry, str):
                    raise invalid(f"invalid dependency declaration: {table}")
                match = re.fullmatch(policy.declaration_pattern, entry)
                if match:
                    name = normalize(match["name"], policy)
                    declarations.setdefault(name, []).append(match["spec"].strip())
    return declarations


def parse_candidates(
    text: str, policy: ModelDevTagLineagePolicy, package: str | None = None
) -> tuple[ModelDevTagLineageCandidate, ...]:
    """Parse each in-scope source with every declaration in contract table order."""
    document = tomllib.loads(text)
    declarations = _declarations(document, policy)
    sources = _table(document, "tool.uv.sources")
    if sources is None:
        return ()
    if not isinstance(sources, dict):
        raise invalid("tool.uv.sources must be a table")
    selected = normalize(package, policy) if package is not None else None
    candidates: list[ModelDevTagLineageCandidate] = []
    for raw_name, values in sorted(sources.items()):
        name = normalize(raw_name, policy)
        if selected is not None and name != selected:
            continue
        for value in values if isinstance(values, list) else [values]:
            if not isinstance(value, dict):
                continue
            url, tag = value.get("git"), value.get("tag")
            if (
                isinstance(url, str)
                and isinstance(tag, str)
                and "rev" not in value
                and "branch" not in value
                and re.fullmatch(policy.tag_pattern, tag)
            ):
                candidates.append(
                    ModelDevTagLineageCandidate(
                        package=name,
                        url=url,
                        tag=tag,
                        declared_specs=tuple(declarations.get(name, ())),
                    )
                )
    return tuple(candidates)


def parse_lock(
    text: str, policy: ModelDevTagLineagePolicy
) -> tuple[ModelDevTagLineageLockEntry, ...]:
    """Retain duplicates so that exactly-one can be decided by the checker."""
    document = tomllib.loads(text)
    entries = document.get("package", [])
    if not isinstance(entries, list):
        raise invalid("lock package entries must be an array")
    result: list[ModelDevTagLineageLockEntry] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise invalid("invalid lock package entry")
        source = entry.get("source", {})
        git = source.get("git", "") if isinstance(source, dict) else ""
        version = entry.get("version", "")
        result.append(
            ModelDevTagLineageLockEntry(
                package=normalize(entry["name"], policy),
                version=version if isinstance(version, str) else "",
                git=git if isinstance(git, str) else "",
            )
        )
    return tuple(result)


def check_dev_tag_lineage(
    path: Path,
    candidate: ModelDevTagLineageCandidate,
    facts: ModelDevTagLineageFacts,
    lock_entries: tuple[ModelDevTagLineageLockEntry, ...] | None,
    contract: ModelValidatorSubcontract,
) -> tuple[ModelValidationIssue, ...]:
    """Judge established facts, and refuse every unresolved required fact."""
    policy = load_policy(contract)
    failures: set[str] = set()
    if facts.tag_exists is False:
        failures.add("tag_absent")
    else:
        if (
            facts.tag_exists is None
            or facts.commit is None
            or facts.version is None
            or facts.on_branch is None
        ):
            failures.add("lineage_unresolved")
        if facts.commit is not None:
            suffix = re.search(policy.suffix_pattern, candidate.tag)
            if not re.fullmatch(policy.commit_pattern, facts.commit):
                failures.add("lineage_unresolved")
            elif suffix is None or not facts.commit.startswith(suffix[1]):
                failures.add("tag_suffix_mismatch")
        if facts.on_branch is False:
            failures.add("tag_off_branch")
    if not candidate.declared_specs:
        failures.add("declared_version_mismatch")
    for spec in candidate.declared_specs:
        try:
            declared = SpecifierSet(spec)
            if facts.version is not None and not declared.contains(facts.version):
                failures.add("declared_version_mismatch")
        except (InvalidSpecifier, InvalidVersion):
            failures.add("declared_version_mismatch")
    if lock_entries is not None:
        entries = [
            entry for entry in lock_entries if entry.package == candidate.package
        ]
        if len(entries) != 1:
            failures.add("lock_mismatch")
        else:
            entry = entries[0]
            try:
                source = urlsplit(entry.git)
                tag_values = parse_qs(source.query).get("tag")
                fragment = source.fragment
            except ValueError:
                tag_values, fragment = None, ""
            if (
                tag_values != [candidate.tag]
                or (facts.version is not None and entry.version != facts.version)
                or (facts.commit is not None and fragment != facts.commit)
            ):
                failures.add("lock_mismatch")
    context = {
        **candidate.model_dump(mode="json"),
        **facts.model_dump(mode="json"),
        "branch": policy.branch,
    }
    issues: list[ModelValidationIssue] = []
    for rule in contract.rules:
        if rule.rule_id in failures:
            parameters = rule.parameters or {}
            issues.append(
                ModelValidationIssue(
                    severity=rule.severity,
                    code=rule.rule_id,
                    rule_name=rule.rule_id,
                    file_path=path,
                    message=str(parameters["message"]).format(**context),
                    suggestion=str(parameters["remediation"]),
                )
            )
    return tuple(issues)


def check_dev_tag_invariants(
    path: Path,
    text: str,
    contract: ModelValidatorSubcontract,
    package: str | None = None,
) -> tuple[ModelValidationIssue, ...]:
    """Require tag iteration from source text alone, without resolving any git fact."""
    policy = load_policy(contract)
    row = next(
        rule for rule in contract.rules if rule.rule_id == "first_party_not_dev_tag"
    )
    parameters = dict(row.parameters or {})
    for key in ("phase", "message", "remediation"):
        parameters.pop(key)
    invariant = ModelDevTagLineageInvariantPolicy.model_validate(parameters)

    def normalized(name: str) -> str:
        return re.sub(invariant.normalize_pattern, "-", name).lower()

    siblings = {normalized(entry.split("=", 1)[0]) for entry in invariant.siblings}
    document = tomllib.loads(text)
    own = _table(document, "project.name")
    own_name = normalized(own) if isinstance(own, str) else None
    declarations = _declarations(document, policy)
    raw_sources = _table(document, "tool.uv.sources")
    if raw_sources is not None and not isinstance(raw_sources, dict):
        raise invalid("tool.uv.sources must be a table")
    sources: dict[str, list[object]] = {}
    for name, values in (raw_sources or {}).items():
        sources.setdefault(normalized(name), []).extend(
            values if isinstance(values, list) else [values]
        )
    selected = normalized(package) if package is not None else None
    issues: list[ModelValidationIssue] = []
    for name in sorted((declarations.keys() | sources.keys()) & siblings):
        if name == own_name or (selected is not None and name != selected):
            continue
        failures: set[str] = set()
        for source in sources.get(name, ()):
            if (
                not isinstance(source, dict)
                or not isinstance(source.get("git"), str)
                or not isinstance(source.get("tag"), str)
                or not re.fullmatch(invariant.tag_pattern, source["tag"])
                or any(key in source for key in invariant.incompatible_source_keys)
            ):
                failures.add("first_party_not_dev_tag")
        if name in sources and not sources[name]:
            failures.add("first_party_not_dev_tag")
        direct_git = False
        for spec in declarations.get(name, ()):
            if re.search(invariant.exact_pattern, spec):
                failures.add("first_party_version_override")
            direct = re.fullmatch(invariant.direct_git_pattern, spec)
            # A malformed/unversioned git URL is still a git requirement, and fails its tag rule.
            if direct is not None:
                direct_git = True
                if not re.fullmatch(invariant.tag_pattern, direct["ref"]):
                    failures.add("first_party_not_dev_tag")
            elif re.match(invariant.direct_git_prefix_pattern, spec):
                direct_git = True
                failures.add("first_party_not_dev_tag")
        if name in declarations and name not in sources and not direct_git:
            failures.add("first_party_release_only")
        for rule in contract.rules:
            if rule.rule_id in failures:
                values = rule.parameters or {}
                issues.append(
                    ModelValidationIssue(
                        severity=rule.severity,
                        code=rule.rule_id,
                        rule_name=rule.rule_id,
                        file_path=path,
                        message=str(values["message"]).format(package=name),
                        suggestion=str(values["remediation"]),
                    )
                )
    return tuple(issues)


def check_verifier_version_pins(
    path: Path, text: str, contract: ModelValidatorSubcontract
) -> tuple[ModelValidationIssue, ...]:
    """Flag each workflow line that gives the pinned verifier input a value.

    The ruling of 2026-10-31 (OMN-21676) is that the gate iterates with tags, not with
    releases, so a released-package verifier version in a caller is the form this cannot
    return in. A reusable workflow that only declares the input (a key with a nested
    mapping), a comment and a read of the input are not a pin. The pattern is rule data.
    """
    load_policy(contract)
    policy = load_verifier_pin_policy(contract)
    row = next(
        rule for rule in contract.rules if rule.rule_id == "verifier_version_pin"
    )
    parameters = row.parameters or {}
    pin = re.compile(policy.pin_pattern)
    issues: list[ModelValidationIssue] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if pin.match(line):
            issues.append(
                ModelValidationIssue(
                    severity=row.severity,
                    code=row.rule_id,
                    rule_name=row.rule_id,
                    file_path=path,
                    line_number=number,
                    message=str(parameters["message"]).format(line=number),
                    suggestion=str(parameters["remediation"]),
                )
            )
    return tuple(issues)
