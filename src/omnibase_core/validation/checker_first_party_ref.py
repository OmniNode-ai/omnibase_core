# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure first-party reference checker: source snapshots and inventories in, issues out.

No filesystem, environment, process, or wall-clock access. Parsing source snapshots
here also makes multi-file invariants independent of traversal and runtime state.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatchcase
from pathlib import Path
from typing import cast

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_brief_ref_parameters import (
    ModelBriefRefParameters,
)
from omnibase_core.models.validation.model_first_party_cross_parameters import (
    ModelFirstPartyCrossParameters,
)
from omnibase_core.models.validation.model_first_party_homes_parameters import (
    ModelFirstPartyHomesParameters,
)
from omnibase_core.models.validation.model_first_party_policy import (
    ModelFirstPartyPolicy,
)
from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.models.validation.model_first_party_ref_parameters import (
    ModelFirstPartyRefParameters,
)
from omnibase_core.models.validation.model_first_party_reference import (
    ModelFirstPartyReference,
)
from omnibase_core.models.validation.model_sibling_parameters import (
    ModelSiblingParameters,
)
from omnibase_core.models.validation.model_sibling_release_parameters import (
    ModelSiblingReleaseParameters,
)
from omnibase_core.models.validation.model_sibling_repo_parameters import (
    ModelSiblingRepoParameters,
)
from omnibase_core.models.validation.model_sibling_stale_parameters import (
    ModelSiblingStaleParameters,
)
from omnibase_core.models.validation.model_third_party_ref_parameters import (
    ModelThirdPartyRefParameters,
)

PARAMETER_MODELS: dict[str, type[ModelFirstPartyPolicy]] = {
    "first_party_not_dev_tag": ModelFirstPartyRefParameters,
    "third_party_not_sha": ModelThirdPartyRefParameters,
    "cross_repo_ref_not_dev_tag": ModelFirstPartyCrossParameters,
    "first_party_source_not_dev_tag": ModelFirstPartyRefParameters,
    "first_party_ref_two_homes": ModelFirstPartyHomesParameters,
    "brief_names_release_version": ModelBriefRefParameters,
    "missing_source": ModelSiblingParameters,
    "wrong_repo": ModelSiblingRepoParameters,
    "release_pin": ModelSiblingReleaseParameters,
    "stale_pin": ModelSiblingStaleParameters,
}


def invalid(message: str) -> ModelOnexError:
    """The structured error every rejected contract, snapshot or target raises."""
    return ModelOnexError(message=message, error_code=EnumCoreErrorCode.INVALID_INPUT)


def load_rule_parameters(
    contract: ModelValidatorSubcontract,
) -> dict[str, ModelFirstPartyPolicy]:
    """Reject incomplete, unknown, disabled, or malformed policy rather than pass."""
    if (
        not contract.fail_on_error
        or contract.max_violations != 0
        or contract.suppression_comments
    ):
        raise invalid(
            "first_party_ref is blocking with a zero target and no suppressions"
        )
    ids = [rule.rule_id for rule in contract.rules]
    if set(ids) != set(PARAMETER_MODELS) or len(ids) != len(set(ids)):
        raise invalid("first_party_ref requires exactly its declared rule set")
    result: dict[str, ModelFirstPartyPolicy] = {}
    for rule in contract.rules:
        if not rule.enabled or rule.severity != EnumSeverity.ERROR:
            raise invalid(f"{rule.rule_id} must be enabled with severity error")
        policy = PARAMETER_MODELS[rule.rule_id].model_validate(rule.parameters)
        for key, value in policy.model_dump(mode="json").items():
            if key.endswith("pattern") and isinstance(value, str):
                re.compile(value)
            if key.endswith("patterns") and isinstance(value, list):
                for pattern in value:
                    re.compile(pattern.replace("{org}", "org"))
        result[rule.rule_id] = policy
    return result


def matches(path: str, globs: list[str]) -> bool:
    """Match repository-relative labels, including root-level recursive globs."""
    return any(
        fnmatchcase(path, pattern)
        or (pattern.startswith("**/") and fnmatchcase(path, pattern[3:]))
        for pattern in globs
    )


def _issue(
    rule: str, policy: ModelFirstPartyPolicy, path: str, line: int, detail: str
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=EnumSeverity.ERROR,
        code=rule,
        rule_name=rule,
        file_path=Path(path),
        line_number=line,
        message=f"{rule}: {detail}",
        suggestion=policy.remediation,
    )


def _captures(
    source: str, patterns: list[str], *, comments_are_prose: bool = False
) -> Iterator[tuple[int, str]]:
    for number, line in enumerate(source.splitlines(), 1):
        if not comments_are_prose and line.lstrip().startswith("#"):
            continue
        seen: list[tuple[int, int]] = []
        for pattern in patterns:
            for match in re.finditer(pattern, line):
                groups = match.groupdict()
                value = next(
                    (v for v in groups.values() if v is not None), match.group()
                )
                span = match.span()
                if not any(start < span[1] and span[0] < end for start, end in seen):
                    seen.append(span)
                    yield number, value


def _yaml_document(source: str) -> yaml.Node | None:
    """Compose snapshots with standard YAML merges, retaining source marks."""
    loader = yaml.SafeLoader(source)
    seen: set[int] = set()

    def flatten(node: yaml.Node) -> None:
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, MappingNode):
            loader.flatten_mapping(node)
            for _key, value in node.value:
                flatten(value)
        elif isinstance(node, SequenceNode):
            for value in node.value:
                flatten(value)

    try:
        document = loader.get_single_node()
        if document is not None:
            flatten(document)
        return document
    finally:
        loader.dispose()


def _yaml_precommit(source: str, path: str) -> Iterator[ModelFirstPartyReference]:
    document = _yaml_document(source)
    if not isinstance(document, MappingNode):
        raise invalid(f"{path}: expected a YAML mapping")
    for key, value in document.value:
        if (
            not isinstance(key, ScalarNode)
            or key.value != "repos"
            or not isinstance(value, SequenceNode)
        ):
            continue
        for entry in value.value:
            if not isinstance(entry, MappingNode):
                raise invalid(f"{path}: malformed pre-commit repository")
            fields = {k.value: v for k, v in entry.value if isinstance(k, ScalarNode)}
            repo, rev = fields.get("repo"), fields.get("rev")
            if isinstance(repo, ScalarNode):
                yield ModelFirstPartyReference(
                    path=path,
                    line=(rev or repo).start_mark.line + 1,
                    value=repo.value
                    + ("@" + rev.value if isinstance(rev, ScalarNode) else ""),
                    kind="precommit",
                )


def _yaml_lab(
    source: str, path: str, policy: ModelFirstPartyCrossParameters
) -> Iterator[ModelFirstPartyReference]:
    document = _yaml_document(source)
    seen: set[int] = set()

    def walk(
        node: yaml.Node, inherited_repo: str = ""
    ) -> Iterator[ModelFirstPartyReference]:
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, MappingNode):
            fields = {k.value: v for k, v in node.value if isinstance(k, ScalarNode)}
            repo = next(
                (
                    v.value
                    for k, v in fields.items()
                    if k in policy.repository_keys and isinstance(v, ScalarNode)
                ),
                inherited_repo,
            )
            for key, value in fields.items():
                if key in policy.literal_ref_keys and isinstance(value, ScalarNode):
                    yield ModelFirstPartyReference(
                        path=path,
                        line=value.start_mark.line + 1,
                        value=value.value,
                        kind="cross",
                    )
                if repo and key in policy.ref_keys and isinstance(value, ScalarNode):
                    yield ModelFirstPartyReference(
                        path=path,
                        line=value.start_mark.line + 1,
                        value=repo + "@" + value.value,
                        kind="cross",
                    )
            for _key, value in node.value:
                yield from walk(value, repo)
        elif isinstance(node, SequenceNode):
            for value in node.value:
                yield from walk(value, inherited_repo)

    if document is not None:
        yield from walk(document)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def _uv(document: Mapping[str, object]) -> Mapping[str, object]:
    return _mapping(_mapping(document.get("tool")).get("uv"))


def _requirements(document: Mapping[str, object]) -> Iterator[str]:
    project = _mapping(document.get("project"))
    channels = [project.get("dependencies")]
    channels.extend(_mapping(project.get("optional-dependencies")).values())
    channels.extend(_mapping(document.get("dependency-groups")).values())
    uv = _uv(document)
    channels.extend(
        uv.get(key)
        for key in (
            "override-dependencies",
            "constraint-dependencies",
            "dev-dependencies",
        )
    )
    for channel in channels:
        if isinstance(channel, list):
            yield from (entry for entry in channel if isinstance(entry, str))


def _sources(
    document: Mapping[str, object],
) -> Iterator[tuple[str, Mapping[str, object]]]:
    for name, source in _mapping(_uv(document).get("sources")).items():
        for item in source if isinstance(source, list) else [source]:
            yield name, _mapping(item)


def _normal(name: str, policy: ModelSiblingParameters) -> str:
    return re.sub(policy.normalize_pattern, "-", name).lower()


def _siblings(policy: ModelSiblingParameters) -> dict[str, str]:
    return {
        _normal(name, policy): repo
        for name, repo in (item.split("=", 1) for item in policy.siblings)
    }


def _declared(
    document: Mapping[str, object], policy: ModelSiblingParameters
) -> dict[str, list[str]]:
    siblings = _siblings(policy)
    own = _normal(str(_mapping(document.get("project")).get("name", "")), policy)
    declared: dict[str, list[str]] = {}
    for requirement in _requirements(document):
        match = re.match(policy.name_pattern, requirement)
        if match:
            name = _normal(match.group(1), policy)
            if name in siblings and name != own:
                declared.setdefault(name, []).append(requirement)
    for name, _ in _sources(document):
        normalized = _normal(name, policy)
        if normalized in siblings and normalized != own:
            declared.setdefault(normalized, [])
    return declared


def inventory_repositories(
    facts: ModelFirstPartyRefInput, contract: ModelValidatorSubcontract
) -> tuple[str, ...]:
    """Pure discovery for the effect boundary; self dependencies are excluded."""
    policy = cast(
        ModelSiblingStaleParameters, load_rule_parameters(contract)["stale_pin"]
    )
    return tuple(
        sorted(
            {
                _siblings(policy)[name]
                for file in facts.files
                if matches(file.path, policy.file_globs)
                for name in _declared(tomllib.loads(file.source), policy)
            }
        )
    )


def _split(
    value: str, homes: ModelFirstPartyHomesParameters
) -> tuple[str, str, str | None]:
    value = value.removeprefix("git+")
    if "@" in value and not (value.startswith("git@") and value.count("@") == 1):
        action, _, ref = value.rpartition("@")
    else:
        action, ref = value, None
    match = re.search(homes.repository_pattern, action)
    if match:
        return match.group("org"), match.group("repo").lower(), ref
    return action.split("/", 1)[0], action, ref


def _refs(
    facts: ModelFirstPartyRefInput, policies: dict[str, ModelFirstPartyPolicy]
) -> tuple[ModelFirstPartyReference, ...]:
    refs: list[ModelFirstPartyReference] = []
    for file in sorted(facts.files, key=lambda file: file.path):
        for rule, kind in (
            ("first_party_not_dev_tag", "uses"),
            ("cross_repo_ref_not_dev_tag", "cross"),
            ("first_party_source_not_dev_tag", "source"),
        ):
            policy = cast(ModelFirstPartyRefParameters, policies[rule])
            if not matches(file.path, policy.file_globs):
                continue
            if kind == "uses" and matches(file.path, policy.structured_globs):
                refs.extend(_yaml_precommit(file.source, file.path))
            else:
                patterns = list(policy.patterns)
                if isinstance(policy, ModelFirstPartyCrossParameters) and matches(
                    file.path, policy.brief_globs
                ):
                    patterns.extend(policy.brief_patterns)
                for line, value in _captures(
                    file.source,
                    [
                        pattern.replace("{org}", re.escape(policy.github_org))
                        for pattern in patterns
                    ],
                    comments_are_prose=isinstance(
                        policy, ModelFirstPartyCrossParameters
                    )
                    and matches(file.path, policy.brief_globs),
                ):
                    if kind == "uses" and value.startswith(("./", ".\\")):
                        continue
                    if value.startswith("git+"):
                        value = value.partition("#")[0]
                    refs.append(
                        ModelFirstPartyReference(
                            path=file.path, line=line, value=value, kind=kind
                        )
                    )
            if isinstance(policy, ModelFirstPartyCrossParameters) and matches(
                file.path, policy.structured_globs
            ):
                refs.extend(_yaml_lab(file.source, file.path, policy))
            if kind == "source" and matches(file.path, policy.structured_globs):
                document = tomllib.loads(file.source)
                sibling = cast(ModelSiblingRepoParameters, policies["wrong_repo"])
                for name, item in _sources(document):
                    key = next(
                        (key for key in ("branch", "rev", "tag") if key in item), ""
                    )
                    url = str(item.get("git", ""))
                    non_git = not url
                    if not url:
                        repo = _siblings(sibling).get(_normal(name, sibling))
                        if repo is None:
                            continue
                        url = sibling.url_template.format(
                            org=sibling.github_org, repo=repo
                        )
                    value = url + ("@" + str(item[key]) if key else "")
                    line = next(
                        (
                            n
                            for n, text in enumerate(file.source.splitlines(), 1)
                            if name in text and "=" in text
                        ),
                        1,
                    )
                    refs.append(
                        ModelFirstPartyReference(
                            path=file.path,
                            line=line,
                            value=value,
                            kind="source",
                            source_key="non_git" if non_git else (key or "non_git"),
                        )
                    )
                for name, requirements in _declared(document, sibling).items():
                    for requirement in requirements:
                        if " @ " in requirement and not requirement.split(" @ ", 1)[
                            1
                        ].startswith("git+"):
                            repo = _siblings(sibling)[name]
                            refs.append(
                                ModelFirstPartyReference(
                                    path=file.path,
                                    line=1,
                                    value=sibling.url_template.format(
                                        org=sibling.github_org, repo=repo
                                    ),
                                    kind="source",
                                    source_key="non_git",
                                )
                            )
    return tuple(
        {
            (ref.path, ref.line, ref.value, ref.kind, ref.source_key): ref
            for ref in refs
        }.values()
    )


def _sibling_issues(
    facts: ModelFirstPartyRefInput, policies: dict[str, ModelFirstPartyPolicy]
) -> Iterator[ModelValidationIssue]:
    homes = cast(ModelFirstPartyHomesParameters, policies["first_party_ref_two_homes"])
    for rule in ("missing_source", "wrong_repo", "release_pin", "stale_pin"):
        policy = cast(ModelSiblingParameters, policies[rule])
        for file in facts.files:
            if not matches(file.path, policy.file_globs):
                continue
            document = tomllib.loads(file.source)
            sources = list(_sources(document))
            for name, requirements in _declared(document, policy).items():
                entries = [
                    item for raw, item in sources if _normal(raw, policy) == name
                ]
                direct = [
                    req.split(" @ ", 1)[1] for req in requirements if " @ " in req
                ]
                repo = _siblings(policy)[name]
                if rule == "missing_source" and not entries and not direct:
                    yield _issue(
                        rule, policy, file.path, 1, f"{name} has no git source"
                    )
                if isinstance(policy, ModelSiblingReleaseParameters):
                    for req in requirements:
                        match = re.match(policy.name_pattern, req)
                        if (
                            match
                            and " @ " not in req
                            and re.search(
                                policy.exact_pattern,
                                req[match.end() :].split(";", 1)[0],
                            )
                        ):
                            yield _issue(
                                rule,
                                policy,
                                file.path,
                                1,
                                f"{name} pins an exact release: {req}",
                            )
                if isinstance(policy, ModelSiblingRepoParameters):
                    expected = (
                        policy.url_template.format(org=policy.github_org, repo=repo)
                        .rstrip("/")
                        .removesuffix(".git")
                        .lower()
                    )
                    urls = [
                        str(item.get("git", "")) for item in entries if "git" in item
                    ]
                    urls.extend(
                        url.removeprefix("git+").rpartition("@")[0]
                        if "@" in url
                        else url.removeprefix("git+")
                        for url in direct
                        if url.startswith("git+")
                    )
                    for url in urls:
                        if url.rstrip("/").removesuffix(".git").lower() != expected:
                            yield _issue(
                                rule,
                                policy,
                                file.path,
                                1,
                                f"{name} source {url!r} is not {expected}",
                            )
                if isinstance(policy, ModelSiblingStaleParameters):
                    pins = [
                        str(item["tag"])
                        for item in entries
                        if "tag" in item
                        and "rev" not in item
                        and "branch" not in item
                        and "git" in item
                    ]
                    pins.extend(
                        _split(url.partition("#")[0], homes)[2] or ""
                        for url in direct
                        if url.startswith("git+")
                    )
                    tags = {
                        tag
                        for inventory in facts.dev_tags
                        if inventory.repo == repo
                        for tag in inventory.tags
                        if re.fullmatch(policy.tag_pattern, tag)
                    }
                    for pin in pins:
                        if re.fullmatch(policy.tag_pattern, pin) is None:
                            continue
                        detail = ""
                        if pin not in tags:
                            detail = f"unverifiable_pin: {name}@{pin} absent from supplied tag inventory"
                        else:
                            newest = max(tags)
                            try:
                                pin_match = re.search(policy.timestamp_pattern, pin)
                                newest_match = re.search(
                                    policy.timestamp_pattern, newest
                                )
                                if pin_match is None or newest_match is None:
                                    raise invalid("timestamp pattern did not match")
                                delta = datetime.strptime(
                                    newest_match.group(1), policy.timestamp_format
                                ).replace(tzinfo=UTC) - datetime.strptime(
                                    pin_match.group(1), policy.timestamp_format
                                ).replace(tzinfo=UTC)
                                merges = sum(tag > pin for tag in tags)
                                if (
                                    merges > policy.max_trailing_merges
                                    or delta
                                    > timedelta(hours=policy.max_trailing_hours)
                                ):
                                    detail = f"{name}@{pin} trails newest dev tag {newest} by {merges} merges and {delta / timedelta(hours=1):g} hours"
                            except (ValueError, ModelOnexError):
                                detail = f"unverifiable_pin: cannot parse timestamps for {name}@{pin} and {newest}"
                        if detail:
                            yield _issue(rule, policy, file.path, 1, detail)


def check_first_party_refs(
    facts: ModelFirstPartyRefInput, contract: ModelValidatorSubcontract
) -> tuple[ModelValidationIssue, ...]:
    """Evaluate all references together; every additional home is one finding."""
    policies = load_rule_parameters(contract)
    homes = cast(ModelFirstPartyHomesParameters, policies["first_party_ref_two_homes"])
    issues: list[ModelValidationIssue] = []
    occurrences: dict[tuple[str, str], set[str]] = {}
    for ref in _refs(facts, policies):
        org, repo, pin = _split(ref.value, homes)
        rule = {
            "uses": "first_party_not_dev_tag",
            "precommit": "first_party_not_dev_tag",
            "cross": "cross_repo_ref_not_dev_tag",
            "source": "first_party_source_not_dev_tag",
        }[ref.kind]
        policy = cast(ModelFirstPartyRefParameters, policies[rule])
        if org.lower() == policy.github_org.lower():
            if (
                pin is None
                or re.fullmatch(policy.sha_pattern, pin)
                or pin in policy.forbidden_refs
                or not re.fullmatch(policy.tag_pattern, pin)
                or (ref.kind == "source" and ref.source_key and ref.source_key != "tag")
            ):
                issues.append(
                    _issue(
                        rule,
                        policy,
                        ref.path,
                        ref.line,
                        f"{ref.value} must name a dev-merge tag",
                    )
                )
        if (
            org.lower() == homes.github_org.lower()
            and pin is not None
            and matches(ref.path, homes.file_globs)
        ):
            files = occurrences.setdefault((repo, pin), set())
            if ref.path not in files:
                files.add(ref.path)
                if len(files) > homes.max_files:
                    issues.append(
                        _issue(
                            "first_party_ref_two_homes",
                            homes,
                            ref.path,
                            ref.line,
                            f"{repo}@{pin} also appears in {', '.join(sorted(files - {ref.path}))}",
                        )
                    )
    third = cast(ModelThirdPartyRefParameters, policies["third_party_not_sha"])
    for file in facts.files:
        if matches(file.path, third.file_globs):
            for line, value in _captures(file.source, third.patterns):
                if value.startswith(("./", ".\\")):
                    continue
                org, _repo, pin = _split(value, homes)
                if org.lower() != third.github_org.lower() and (
                    pin is None or re.fullmatch(third.sha_pattern, pin) is None
                ):
                    issues.append(
                        _issue(
                            "third_party_not_sha",
                            third,
                            file.path,
                            line,
                            f"{value} must name a full commit SHA",
                        )
                    )
    brief = cast(ModelBriefRefParameters, policies["brief_names_release_version"])
    for file in facts.files:
        if matches(file.path, brief.file_globs):
            for line, value in _captures(
                file.source, brief.patterns, comments_are_prose=True
            ):
                if re.fullmatch(brief.release_pattern, value) and not re.fullmatch(
                    brief.tag_pattern, value
                ):
                    issues.append(
                        _issue(
                            "brief_names_release_version",
                            brief,
                            file.path,
                            line,
                            f"brief names release version {value}",
                        )
                    )
    issues.extend(_sibling_issues(facts, policies))
    return tuple(
        sorted(
            issues,
            key=lambda issue: (
                str(issue.file_path),
                issue.line_number or 0,
                issue.code or "",
                issue.message,
            ),
        )
    )
