# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure cross-repository dependency-pin checker (OMN-22360).

Facts in (the manifest, lock and pre-commit texts, the release inventories and the
hook histories), ``ModelValidationIssue`` out: no file read, no git call, no clock.
The layer order is the caller's ``ModelRepoLayerMap`` (``contracts/repo_layers.yaml``)
and every bound is the caller's ``ModelDependencyPinPolicy``
(``contracts/dependency_pin_policy.yaml``); every message and file format key is a
``parameters`` entry of the matching rule row in
``contracts/dependency_pins.validation.yaml``.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.dependency_direction.model_repo_layer import ModelRepoLayer
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.dependency_pins.model_dependency_hook_history import (
    ModelDependencyHookHistory,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_edge import (
    ModelDependencyPinEdge,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    DependencyTable,
    ModelDependencyPinPolicy,
)
from omnibase_core.models.dependency_pins.model_dependency_pins_input import (
    ModelDependencyPinsInput,
)
from omnibase_core.models.dependency_pins.model_dependency_release_inventory import (
    ModelDependencyReleaseInventory,
)
from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.validation.checker_precommit_pin_parity import (
    extract_pins,
    normalize_repo_url,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = [
    "RULE_CYCLE",
    "RULE_FACTS",
    "RULE_HOOK_BEHIND",
    "RULE_HOOK_EXEMPTED",
    "RULE_HOOK_EXEMPTION_EXPIRED",
    "RULE_HOOK_NEAR_BOUND",
    "RULE_HOOK_UNRESOLVED",
    "RULE_INVENTORY",
    "RULE_LAYER",
    "RULE_PIN_STYLE",
    "RULE_RELEASE",
    "RULE_RETIRED",
    "RULE_SPECIFIER",
    "RULE_UNDECLARED",
    "RULE_UNREADABLE",
    "bounded_hook_pins",
    "check_dependency_pins",
    "declared_edges",
    "dependency_repos",
    "first_party_index",
    "release_versions",
    "validate_rules",
]

RULE_UNREADABLE = "manifest_unreadable"
RULE_UNDECLARED = "repo_not_in_layer_map"
RULE_LAYER = "layer_order"
RULE_RETIRED = "retired_repository"
RULE_CYCLE = "dependency_cycle"
RULE_RELEASE = "release_behind"
RULE_SPECIFIER = "specifier_excludes_newest_release"
RULE_PIN_STYLE = "pin_style"
RULE_INVENTORY = "release_inventory_unreadable"
RULE_HOOK_BEHIND = "hook_rev_behind"
RULE_HOOK_NEAR_BOUND = "hook_rev_near_bound"
RULE_HOOK_EXEMPTED = "hook_rev_exempted"
RULE_HOOK_EXEMPTION_EXPIRED = "hook_rev_exemption_expired"
RULE_HOOK_UNRESOLVED = "hook_rev_unresolved"
RULE_FACTS = "facts_lookup"


def _invalid(reason: str) -> ModelOnexError:
    return ModelOnexError(
        message=reason, error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR
    )


def validate_rules(rules: Mapping[str, ModelValidatorRule]) -> None:
    """Every row the checker reads exists and the format row holds only strings.

    A parameter missing from a row raises at its first read, which the runtime
    reports as an error, never a pass.
    """
    for rule_id in (
        RULE_UNREADABLE,
        RULE_UNDECLARED,
        RULE_LAYER,
        RULE_RETIRED,
        RULE_CYCLE,
        RULE_RELEASE,
        RULE_SPECIFIER,
        RULE_PIN_STYLE,
        RULE_INVENTORY,
        RULE_HOOK_BEHIND,
        RULE_HOOK_NEAR_BOUND,
        RULE_HOOK_EXEMPTED,
        RULE_HOOK_EXEMPTION_EXPIRED,
        RULE_HOOK_UNRESOLVED,
        RULE_FACTS,
    ):
        if rule_id not in rules:
            raise _invalid(f"the contract has no {rule_id} rule row")
    for key in rules[RULE_UNREADABLE].parameters or {}:
        rule_string(rules[RULE_UNREADABLE], key)
    re.compile(rule_string(rules[RULE_UNREADABLE], "name_separator_pattern"))
    rule_strings(rules[RULE_PIN_STYLE], "exact_operators")
    rule_int(rules[RULE_HOOK_NEAR_BOUND], "margin")
    re.compile(rule_string(rules[RULE_HOOK_EXEMPTED], "full_rev_pattern"))


def _fmt(rules: Mapping[str, ModelValidatorRule], key: str) -> str:
    return rule_string(rules[RULE_UNREADABLE], key)


def _normalize(name: str, rules: Mapping[str, ModelValidatorRule]) -> str:
    return re.sub(_fmt(rules, "name_separator_pattern"), "-", name).lower()


def _issue(
    rules: Mapping[str, ModelValidatorRule],
    rule_id: str,
    path: str,
    message: str,
    line: int | None = None,
) -> tuple[ModelValidationIssue, ...]:
    row = rules[rule_id]
    if not row.enabled:
        return ()
    return (
        ModelValidationIssue(
            severity=row.severity,
            message=" ".join(message.split()),
            code=rule_id,
            file_path=Path(path),
            line_number=line,
            rule_name=rule_id,
        ),
    )


def _report(
    rules: Mapping[str, ModelValidatorRule],
    rule_id: str,
    path: str,
    *,
    key: str = "message",
    line: int | None = None,
    **values: object,
) -> tuple[ModelValidationIssue, ...]:
    template = rule_string(rules[rule_id], key)
    return _issue(
        rules, rule_id, path, template.format(path=path, line=line, **values), line
    )


def first_party_index(
    layer_map: ModelRepoLayerMap, rules: Mapping[str, ModelValidatorRule]
) -> dict[str, ModelRepoLayer]:
    """Every declared distribution, normalised, to the repository that publishes it."""
    return {
        _normalize(dist, rules): entry
        for entry in layer_map.repos
        for dist in entry.distributions
    }


def _parse_toml(text: str, path: str) -> dict[str, object]:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise _invalid(f"{path}: {exc}") from exc


def _table(document: Mapping[str, object], *keys: str) -> object:
    node: object = document
    for key in keys:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(v for v in value if isinstance(v, str))
    return ()


def _line_of(text: str, requirement: str) -> int:
    for quote in ('"', "'"):
        index = text.find(f"{quote}{requirement}{quote}")
        if index >= 0:
            return text.count("\n", 0, index) + 1
    return 1


def manifest_distribution(
    manifest: Mapping[str, object], rules: Mapping[str, ModelValidatorRule]
) -> str | None:
    """The normalised ``[project] name``, or None when the manifest declares none."""
    name = _table(manifest, _fmt(rules, "project_key"), _fmt(rules, "name_key"))
    return _normalize(name, rules) if isinstance(name, str) else None


def _declarations(
    manifest: Mapping[str, object], rules: Mapping[str, ModelValidatorRule]
) -> Iterable[tuple[DependencyTable, str, str]]:
    project = _fmt(rules, "project_key")
    tool, uv = _fmt(rules, "tool_key"), _fmt(rules, "uv_key")
    for requirement in _strings(
        _table(manifest, project, _fmt(rules, "dependencies_key"))
    ):
        yield "project", _fmt(rules, "label_project"), requirement
    extras = _table(manifest, project, _fmt(rules, "optional_key"))
    if isinstance(extras, Mapping):
        for name, value in extras.items():
            label = _fmt(rules, "label_optional").format(name=name)
            for requirement in _strings(value):
                yield "optional", label, requirement
    groups = _table(manifest, _fmt(rules, "groups_key"))
    if isinstance(groups, Mapping):
        for name, value in groups.items():
            label = _fmt(rules, "label_group").format(name=name)
            for requirement in _strings(value):
                yield "group", label, requirement
    for requirement in _strings(_table(manifest, tool, uv, _fmt(rules, "uv_dev_key"))):
        yield "uv_dev", _fmt(rules, "label_uv_dev"), requirement
    for requirement in _strings(
        _table(manifest, tool, uv, _fmt(rules, "override_key"))
    ):
        yield "override", _fmt(rules, "label_override"), requirement


def _retired_declarations(
    manifest: Mapping[str, object], rules: Mapping[str, ModelValidatorRule]
) -> Iterable[tuple[str, str]]:
    """(table label, requirement or source name) of every table that can name a distribution."""
    tool, uv = _fmt(rules, "tool_key"), _fmt(rules, "uv_key")
    for _table_key, label, raw in _declarations(manifest, rules):
        yield label, raw
    for requirement in _strings(
        _table(manifest, tool, uv, _fmt(rules, "constraint_key"))
    ):
        yield _fmt(rules, "label_constraint"), requirement
    sources = _table(manifest, tool, uv, _fmt(rules, "sources_key"))
    if isinstance(sources, Mapping):
        for name in sources:
            yield _fmt(rules, "label_source"), str(name)
    for requirement in _strings(
        _table(manifest, _fmt(rules, "build_system_key"), _fmt(rules, "requires_key"))
    ):
        yield _fmt(rules, "label_build_system"), requirement


def _retired_issues(
    request: ModelDependencyPinsInput,
    rules: Mapping[str, ModelValidatorRule],
    manifest: Mapping[str, object],
    repo: str,
) -> list[ModelValidationIssue]:
    """One issue per manifest declaration of a retired distribution, in every table."""
    retired = {
        _normalize(dist, rules): entry
        for entry in request.layer_map.retired
        for dist in entry.distributions
    }
    if not retired:
        return []
    separator = _fmt(rules, "name_separator_pattern")
    issues: list[ModelValidationIssue] = []
    for label, raw in _retired_declarations(manifest, rules):
        try:
            name = Requirement(raw).name
        except InvalidRequirement:
            name = raw.strip()
        entry = retired.get(re.sub(separator, "-", name).lower())
        if entry is None:
            continue
        issues.extend(
            _report(
                rules,
                RULE_RETIRED,
                request.manifest_path,
                line=_line_of(request.manifest_text, raw),
                repo=repo,
                target=entry.distributions[0] if entry.distributions else entry.repo,
                target_repo=entry.repo,
                retired_by=entry.retired_by,
                table=label,
            )
        )
    return issues


def declared_edges(
    request: ModelDependencyPinsInput, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelDependencyPinEdge, ...]:
    """Every first-party requirement of the manifest in a policy edge table, self excluded."""
    manifest = _parse_toml(request.manifest_text, request.manifest_path)
    index = first_party_index(request.layer_map, rules)
    own = manifest_distribution(manifest, rules)
    edges: list[ModelDependencyPinEdge] = []
    for table, label, raw in _declarations(manifest, rules):
        if table not in request.policy.edge_tables:
            continue
        try:
            requirement = Requirement(raw)
        except InvalidRequirement as exc:
            raise _invalid(f"{request.manifest_path}: {raw!r}: {exc}") from exc
        target = _normalize(requirement.name, rules)
        if target not in index or target == own:
            continue
        edges.append(
            ModelDependencyPinEdge(
                table=table,
                label=label,
                target=target,
                requirement=raw,
                specifier=str(requirement.specifier),
                line=_line_of(request.manifest_text, raw),
            )
        )
    return tuple(edges)


def dependency_repos(
    request: ModelDependencyPinsInput, rules: Mapping[str, ModelValidatorRule]
) -> tuple[str, ...]:
    """The repositories whose release inventory the release rules need."""
    index = first_party_index(request.layer_map, rules)
    return tuple(
        sorted({index[edge.target].repo for edge in declared_edges(request, rules)})
    )


def bounded_hook_pins(
    precommit_text: str | None, policy: ModelDependencyPinPolicy
) -> tuple[ModelPrecommitPin, ...]:
    """The pre-commit pins of a hook repository the policy bounds."""
    if precommit_text is None or not policy.hook_repos:
        return ()
    bounded = {normalize_repo_url(hook.url) for hook in policy.hook_repos}
    return tuple(
        pin
        for pin in extract_pins(precommit_text)
        if normalize_repo_url(pin.repo) in bounded
    )


def release_versions(
    inventory: ModelDependencyReleaseInventory,
) -> tuple[Version, ...]:
    """The parseable final-release versions of an inventory, ascending."""
    versions: set[Version] = set()
    for raw in inventory.versions:
        try:
            version = Version(raw)
        except InvalidVersion:
            continue
        if not version.is_prerelease:
            versions.add(version)
    return tuple(sorted(versions))


def _lock(
    request: ModelDependencyPinsInput,
    rules: Mapping[str, ModelValidatorRule],
    index: Mapping[str, ModelRepoLayer],
) -> tuple[dict[str, set[Version]], set[tuple[str, str]]]:
    """Locked versions per distribution, and locked edges among first-party ones."""
    versions: dict[str, set[Version]] = {}
    edges: set[tuple[str, str]] = set()
    if request.lock_text is None:
        return versions, edges
    document = _parse_toml(request.lock_text, request.lock_path)
    packages = document.get(_fmt(rules, "lock_package_key"))
    if not isinstance(packages, list):
        return versions, edges
    for package in packages:
        if not isinstance(package, Mapping):
            continue
        name = package.get(_fmt(rules, "name_key"))
        if not isinstance(name, str):
            continue
        source = _normalize(name, rules)
        raw_version = package.get(_fmt(rules, "lock_version_key"))
        if isinstance(raw_version, str):
            try:
                versions.setdefault(source, set()).add(Version(raw_version))
            except InvalidVersion as exc:
                raise _invalid(f"{request.lock_path}: {name} {raw_version}") from exc
        if source not in index:
            continue
        for target in _lock_targets(package, rules):
            if target in index and target != source:
                edges.add((source, target))
    return versions, edges


def _lock_targets(
    package: Mapping[str, object], rules: Mapping[str, ModelValidatorRule]
) -> Iterable[str]:
    lists: list[object] = [package.get(_fmt(rules, "lock_dependencies_key"))]
    for key in (_fmt(rules, "lock_optional_key"), _fmt(rules, "lock_dev_key")):
        grouped = package.get(key)
        if isinstance(grouped, Mapping):
            lists.extend(grouped.values())
    for entries in lists:
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, Mapping):
                name = entry.get(_fmt(rules, "name_key"))
                if isinstance(name, str):
                    yield _normalize(name, rules)


def _cycles(edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    """One cycle per strongly connected component of more than one node."""
    graph: dict[str, set[str]] = {}
    for source, target in edges:
        graph.setdefault(source, set()).add(target)
        graph.setdefault(target, set())
    order: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        order[node] = low[node] = len(order)
        stack.append(node)
        on_stack.add(node)
        for nxt in sorted(graph[node]):
            if nxt not in order:
                visit(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], order[nxt])
        if low[node] == order[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in sorted(graph):
        if node not in order:
            visit(node)
    return [_cycle_path(component, graph) for component in sorted(components)]


def _cycle_path(component: list[str], graph: Mapping[str, set[str]]) -> list[str]:
    """A simple cycle through the first member of a strongly connected component."""
    members = set(component)
    start = component[0]
    path = [start]
    seen = {start}
    node = start
    while True:
        nxt = sorted(graph[node] & members)
        if start in nxt and len(path) > 1:
            return [*path, start]
        step = next((n for n in nxt if n not in seen), None)
        if step is None:
            return [*path, start]
        path.append(step)
        seen.add(step)
        node = step


def _lowest_admitted(specifier: str) -> Version | None:
    floors: list[Version] = []
    for spec in SpecifierSet(specifier):
        if spec.operator in (">=", ">", "==", "===", "~="):
            try:
                floors.append(Version(spec.version))
            except InvalidVersion:
                continue
    return max(floors) if floors else None


def _is_exact(specifier: str, operators: tuple[str, ...]) -> bool:
    specs = list(SpecifierSet(specifier))
    return len(specs) == 1 and specs[0].operator in operators


def _has_exact(specifier: str, operators: tuple[str, ...]) -> bool:
    return any(spec.operator in operators for spec in SpecifierSet(specifier))


def check_dependency_pins(
    request: ModelDependencyPinsInput, rules: Mapping[str, ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """Judge one repository's facts; every value comes from the two overlays and the rows."""
    path = request.manifest_path
    try:
        manifest = _parse_toml(request.manifest_text, path)
        edges = declared_edges(request, rules)
    except ModelOnexError as exc:
        return _report(rules, RULE_UNREADABLE, path, reason=exc.message)
    index = first_party_index(request.layer_map, rules)
    distribution = manifest_distribution(manifest, rules)
    own = index.get(distribution) if distribution is not None else None
    if own is None and request.repo is not None:
        own = request.layer_map.get(request.repo)
    issues: list[ModelValidationIssue] = []
    issues.extend(
        _retired_issues(
            request, rules, manifest, own.repo if own else (distribution or "")
        )
    )
    if own is None:
        issues.extend(
            _report(rules, RULE_UNDECLARED, path, distribution=distribution or "")
        )
    else:
        for edge in edges:
            target = index[edge.target]
            if target.layer >= own.layer:
                issues.extend(
                    _report(
                        rules,
                        RULE_LAYER,
                        path,
                        line=edge.line,
                        repo=own.repo,
                        own_layer=own.layer,
                        target=edge.target,
                        target_repo=target.repo,
                        target_layer=target.layer,
                        table=edge.label,
                    )
                )
    try:
        locked, lock_edges = _lock(request, rules, index)
    except ModelOnexError as exc:
        locked, lock_edges = {}, set()
        issues.extend(
            _report(rules, RULE_UNREADABLE, request.lock_path, reason=exc.message)
        )
    graph = set(lock_edges)
    root = distribution or (own.distributions[0] if own and own.distributions else "")
    if root:
        graph.update((root, edge.target) for edge in edges)
    lock_name = request.lock_path if request.lock_text is not None else "none"
    separator = rule_string(rules[RULE_CYCLE], "separator")
    for cycle in _cycles(graph):
        issues.extend(
            _report(
                rules, RULE_CYCLE, path, cycle=separator.join(cycle), lock=lock_name
            )
        )
    issues.extend(_style_issues(request, rules, edges))
    issues.extend(_release_issues(request, rules, edges, index, locked))
    issues.extend(_hook_issues(request, rules))
    return tuple(issues)


def _style_issues(
    request: ModelDependencyPinsInput,
    rules: Mapping[str, ModelValidatorRule],
    edges: tuple[ModelDependencyPinEdge, ...],
) -> list[ModelValidationIssue]:
    operators = rule_strings(rules[RULE_PIN_STYLE], "exact_operators")
    issues: list[ModelValidationIssue] = []
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        if (edge.target, edge.specifier) in seen:
            continue
        seen.add((edge.target, edge.specifier))
        style = request.policy.style_for(edge.target)
        if style == "range" and _has_exact(edge.specifier, operators):
            key = "range_wanted_message"
        elif style == "exact" and not _is_exact(edge.specifier, operators):
            key = "exact_wanted_message"
        else:
            continue
        issues.extend(
            _report(
                rules,
                RULE_PIN_STYLE,
                request.manifest_path,
                key=key,
                line=edge.line,
                target=edge.target,
                specifier=edge.specifier,
                table=edge.label,
            )
        )
    return issues


def _release_issues(
    request: ModelDependencyPinsInput,
    rules: Mapping[str, ModelValidatorRule],
    edges: tuple[ModelDependencyPinEdge, ...],
    index: Mapping[str, ModelRepoLayer],
    locked: Mapping[str, set[Version]],
) -> list[ModelValidationIssue]:
    path = request.manifest_path
    policy = request.policy
    inventories = {inv.repo: inv for inv in request.inventories}
    issues: list[ModelValidationIssue] = []
    reported: set[str] = set()
    judged: set[tuple[str, str]] = set()
    for edge in edges:
        if (edge.target, edge.specifier) in judged:
            continue
        judged.add((edge.target, edge.specifier))
        repo = index[edge.target].repo
        inventory = inventories.get(repo)
        if inventory is None or inventory.error is not None:
            if repo not in reported:
                reported.add(repo)
                reason = (
                    inventory.error
                    if inventory is not None and inventory.error is not None
                    else rule_string(rules[RULE_INVENTORY], "not_read_reason")
                )
                issues.extend(
                    _report(rules, RULE_INVENTORY, path, repo=repo, reason=reason)
                )
            continue
        releases = release_versions(inventory)
        if not releases:
            continue
        newest = releases[-1]
        if policy.specifier_must_admit_newest_release and not SpecifierSet(
            edge.specifier
        ).contains(newest, prereleases=True):
            issues.extend(
                _report(
                    rules,
                    RULE_SPECIFIER,
                    path,
                    line=edge.line,
                    target=edge.target,
                    specifier=edge.specifier,
                    table=edge.label,
                    newest=newest,
                )
            )
        if edge.target in locked:
            pinned = min(locked[edge.target])
            source = request.lock_path
        else:
            floor = _lowest_admitted(edge.specifier)
            if floor is None:
                continue
            pinned, source = floor, edge.requirement
        behind = sum(1 for release in releases if release > pinned)
        if behind > policy.max_releases_behind:
            issues.extend(
                _report(
                    rules,
                    RULE_RELEASE,
                    path,
                    line=edge.line,
                    target=edge.target,
                    pinned=pinned,
                    source=source,
                    table=edge.label,
                    behind=behind,
                    newest=newest,
                    bound=policy.max_releases_behind,
                )
            )
    return issues


def _unresolved_reason(
    history: ModelDependencyHookHistory | None,
    rev: str,
    rules: Mapping[str, ModelValidatorRule],
) -> str | None:
    """Why ``rev`` has no commit time, or None when it has one."""
    row = rules[RULE_HOOK_UNRESOLVED]
    if history is None:
        return rule_string(row, "no_history_reason")
    if history.error is not None:
        return history.error
    if not any(t.rev == rev for t in history.rev_times):
        return rule_string(row, "not_in_history_reason")
    return None


def _hook_issues(
    request: ModelDependencyPinsInput, rules: Mapping[str, ModelValidatorRule]
) -> list[ModelValidationIssue]:
    path = request.precommit_path
    policy = request.policy
    try:
        pins = bounded_hook_pins(request.precommit_text, policy)
    except ModelOnexError as exc:
        return list(_report(rules, RULE_UNREADABLE, path, reason=exc.message))
    histories: dict[str, ModelDependencyHookHistory] = {
        normalize_repo_url(h.url): h for h in request.hook_histories
    }
    repos = {normalize_repo_url(h.url): h.repo for h in policy.hook_repos}
    near_margin = rule_int(rules[RULE_HOOK_NEAR_BOUND], "margin")
    full_rev_pattern = rule_string(rules[RULE_HOOK_EXEMPTED], "full_rev_pattern")
    issues: list[ModelValidationIssue] = []
    for pin in pins:
        url = normalize_repo_url(pin.repo)
        history = histories.get(url)
        hooks = ", ".join(pin.hook_ids)
        reason = _unresolved_reason(history, pin.rev, rules)
        if reason is not None or history is None:
            issues.extend(
                _report(
                    rules,
                    RULE_HOOK_UNRESOLVED,
                    path,
                    line=pin.line,
                    reason=reason,
                    url=pin.repo,
                    rev=pin.rev,
                    hooks=hooks,
                    repo=repos[url],
                )
            )
            continue
        committed = next(t.committed_at for t in history.rev_times if t.rev == pin.rev)
        behind = sum(1 for t in history.release_times if t > committed)
        bound = policy.hook_rev_max_releases_behind
        exemption = next(
            (
                e
                for e in policy.hook_rev_exemptions
                if normalize_repo_url(e.url) == url
                and re.fullmatch(full_rev_pattern, pin.rev)
                and pin.rev.startswith(e.rev)
            ),
            None,
        )
        if exemption is not None:
            expired = (
                request.checked_on is None or request.checked_on > exemption.expires
            )
            fields = {
                "path": path,
                "line": pin.line,
                "url": pin.repo,
                "rev": pin.rev,
                "hooks": hooks,
                "repo": repos[url],
                "behind": behind,
                "bound": bound,
                "expires": exemption.expires.isoformat(),
                "ruling": exemption.ruling,
                "ticket": exemption.ticket,
            }
            if expired:
                issues.extend(_report(rules, RULE_HOOK_EXEMPTION_EXPIRED, **fields))
            else:
                issues.extend(_report(rules, RULE_HOOK_EXEMPTED, **fields))
                continue
        if bound - near_margin <= behind <= bound and behind > 0:
            issues.extend(
                _report(
                    rules,
                    RULE_HOOK_NEAR_BOUND,
                    path,
                    line=pin.line,
                    behind=behind,
                    bound=bound,
                    margin=near_margin,
                    url=pin.repo,
                    rev=pin.rev,
                    hooks=hooks,
                    repo=repos[url],
                )
            )
        if behind > bound:
            issues.extend(
                _report(
                    rules,
                    RULE_HOOK_BEHIND,
                    path,
                    line=pin.line,
                    behind=behind,
                    bound=policy.hook_rev_max_releases_behind,
                    url=pin.repo,
                    rev=pin.rev,
                    hooks=hooks,
                    repo=repos[url],
                )
            )
    return issues
