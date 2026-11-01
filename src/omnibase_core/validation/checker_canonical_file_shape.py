# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for the canonical-file-shape rules (OMN-20304, OMN-21515).

Typed facts in, ``ModelValidationIssue`` out: no file, git, clock or environment
access. Every pattern, name list, path, threshold and remediation text comes from
the ``parameters`` of the rule rows in
``contracts/canonical_file_shape.validation.yaml`` (``load_rule_set``).

Rules: noncanonical-file, handler_outside_node, cli_entry_outside_node (file
rules, refused paths that the shrink-only baseline may carry), baseline-stale,
baseline-growth, baselined-file-growth, burndown-ticket-missing,
burndown-baseline-removed, burndown-extra-entry, burndown-ticket-uncited,
skill-imperative, suppression-growth,
new-exception-file, exception-entry-growth, and the repository-lifecycle rules
(lifecycle-no-code, lifecycle-fix-only-new-file, lifecycle-fix-only-growth,
lifecycle-retired). The only state is the baseline file and the ticketed
burn-down baseline file.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path, PurePosixPath

import yaml
from pydantic import ValidationError

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_canonical_location_rules import (
    TYPESCRIPT_EXTENSIONS,
    HandlerCanonicalLocationRules,
)
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.models.validation.model_canonical_file_shape_rule_set import (
    ModelCanonicalFileShapeRuleSet,
)
from omnibase_core.models.validation.model_canonical_file_shape_rules import (
    ModelCanonicalFileShapeRules,
)
from omnibase_core.models.validation.model_canonical_file_shape_tree import (
    ModelCanonicalFileShapeTree,
)
from omnibase_core.models.validation.model_canonical_location_request import (
    ModelCanonicalLocationRequest,
)
from omnibase_core.models.validation.model_canonical_location_verdict import (
    ModelCanonicalLocationVerdict,
)

VALIDATOR_ID = "canonical_file_shape"
RULE_NONCANONICAL = "noncanonical-file"
RULE_BASELINE_STALE = "baseline-stale"
RULE_BASELINE_GROWTH = "baseline-growth"
RULE_BASELINED_GROWTH = "baselined-file-growth"
RULE_BURNDOWN_TICKET = "burndown-ticket-missing"
RULE_BURNDOWN_REMOVED = "burndown-baseline-removed"
RULE_BURNDOWN_EXTRA = "burndown-extra-entry"
RULE_BURNDOWN_UNCITED = "burndown-ticket-uncited"
RULE_SKILL_IMPERATIVE = "skill-imperative"
RULE_SUPPRESSION_GROWTH = "suppression-growth"
RULE_NEW_EXCEPTION = "new-exception-file"
RULE_EXCEPTION_GROWTH = "exception-entry-growth"
RULE_LIFECYCLE = "repository-lifecycle"
RULE_NO_CODE = "lifecycle-no-code"
RULE_FIX_ONLY_NEW = "lifecycle-fix-only-new-file"
RULE_FIX_ONLY_GROWTH = "lifecycle-fix-only-growth"
RULE_RETIRED = "lifecycle-retired"
RULE_HANDLER = "handler_outside_node"
RULE_CLI_ENTRY = "cli_entry_outside_node"


def load_rule_set(
    contract: ModelValidatorSubcontract,
) -> ModelCanonicalFileShapeRuleSet:
    """Merge the rows' ``parameters`` into the typed rule set.

    A key that two rows both carry, an unknown key or a missing key raises, so an
    invalid contract fails to load instead of passing.
    """
    merged: dict[str, object] = {}
    for rule in contract.rules:
        for key, value in (rule.parameters or {}).items():
            if key in merged:
                raise ModelOnexError(
                    message=f"{VALIDATOR_ID} contract: parameter '{key}' is declared by two rule rows",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            merged[key] = value
    try:
        parameters = ModelCanonicalFileShapeRules.model_validate(merged)
    except ValidationError as exc:
        raise ModelOnexError(
            message=f"{VALIDATOR_ID} contract parameters are invalid: {exc}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from exc
    return ModelCanonicalFileShapeRuleSet(
        parameters=parameters,
        enabled=frozenset(rule.rule_id for rule in contract.rules if rule.enabled),
        severities={rule.rule_id: rule.severity.value for rule in contract.rules},
    )


@lru_cache(maxsize=256)
def _regex(pattern: str, multiline: bool = False) -> re.Pattern[str]:
    return re.compile(pattern, re.MULTILINE if multiline else 0)


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _heads(tree: ModelCanonicalFileShapeTree) -> dict[str, bytes]:
    return {line.path: line.text.encode() for line in tree.shebang_lines}


def _is_code(path: str, text: str | None, p: ModelCanonicalFileShapeRules) -> bool:
    suffix = _suffix(path)
    if suffix in p.code_extensions:
        return True
    return suffix == "" and text is not None and text.startswith(p.shebang_prefix)


_LOCATION_RULES = HandlerCanonicalLocationRules()


def _canonical_location(
    path: str,
    location: ModelCanonicalLocationVerdict,
    p: ModelCanonicalFileShapeRules,
) -> bool:
    if _suffix(path) in TYPESCRIPT_EXTENSIONS:
        return location.is_typescript_canonical_location
    parts = PurePosixPath(path).parts
    if not parts:
        return False
    if parts[0] == p.docs_root or parts[-1] in p.always_canonical_names:
        return True
    if any(part in p.test_dirs for part in parts[:-1]):
        return True
    if len(parts) < p.canonical_src_min_parts or parts[0] != p.src_root:
        return False
    if parts[2] in p.canonical_src_dirs:
        return True
    return len(parts) == p.canonical_src_min_parts and any(
        parts[2] == directory and parts[-1].startswith(prefix)
        for directory, _, prefix in (
            entry.partition(":") for entry in p.canonical_prefixed_dirs
        )
    )


def _module_of(path: str, p: ModelCanonicalFileShapeRules) -> str:
    pure = PurePosixPath(path)
    parts = pure.with_suffix("").parts
    if parts and parts[0] == p.src_root:
        parts = parts[1:]
    return ".".join(parts)


def _walk(node: object) -> Iterable[tuple[str, object]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key), value
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _bound_modules(
    tree: ModelCanonicalFileShapeTree, p: ModelCanonicalFileShapeRules
) -> frozenset[str]:
    """Dotted modules that a ``contract.yaml`` binds as a handler."""
    bound: set[str] = set()
    for contract in tree.contract_texts:
        if PurePosixPath(contract.path).name != p.contract_file_name:
            continue
        try:
            document = yaml.safe_load(contract.text)
        except yaml.YAMLError:
            continue
        directory = PurePosixPath(contract.path).parent
        for key, value in _walk(document):
            if (
                key == p.binding_handler_key
                and isinstance(value, dict)
                and isinstance(value.get(p.binding_module_key), str)
            ):
                bound.add(value[p.binding_module_key])
            elif key == p.binding_default_key and isinstance(value, str):
                module = value.split(":", 1)[0].strip()
                if module and "." not in module:
                    bound.add(_module_of((directory / f"{module}.py").as_posix(), p))
                elif module:
                    bound.add(module)
    return frozenset(bound)


def _is_node_runtime(
    path: str, files: frozenset[str], p: ModelCanonicalFileShapeRules
) -> bool:
    pure = PurePosixPath(path)
    return pure.name.startswith(p.node_runtime_prefix) and (
        (pure.parent / p.contract_file_name).as_posix() in files
    )


def _script_modules(
    tree: ModelCanonicalFileShapeTree, p: ModelCanonicalFileShapeRules
) -> frozenset[str]:
    if tree.pyproject_text is None:
        return frozenset()
    try:
        table: object = tomllib.loads(tree.pyproject_text)
    except tomllib.TOMLDecodeError:
        return frozenset()
    for key in p.scripts_key_path.split("."):
        if not isinstance(table, dict) or key not in table:
            return frozenset()
        table = table[key]
    if not isinstance(table, dict):
        return frozenset()
    return frozenset(
        str(target).split(":", 1)[0].strip()
        for target in table.values()
        if isinstance(target, str)
    )


def file_rule_refusals(
    tree: ModelCanonicalFileShapeTree,
    rules: ModelCanonicalFileShapeRuleSet,
) -> dict[str, tuple[str, str]]:
    """``path -> (rule id, reason)`` for every path a file rule refuses at ``tree``."""
    p = rules.parameters
    refusals: dict[str, tuple[str, str]] = {}
    files = frozenset(tree.files)
    heads = _heads(tree)
    roots = _LOCATION_RULES.handle(
        ModelCanonicalLocationRequest(tracked_files=tree.files)
    ).workspace_roots
    if RULE_NONCANONICAL in rules.enabled:
        for path in sorted(files):
            head = heads.get(path)
            text = None if head is None else head.decode(errors="replace")
            if not _is_code(path, text, p):
                continue
            location = _LOCATION_RULES.handle(
                ModelCanonicalLocationRequest(
                    path=path, head_bytes=head, workspace_roots=roots
                )
            )
            if location.is_shell_script:
                refusals[path] = (RULE_NONCANONICAL, p.shell_text)
            elif not _canonical_location(path, location, p):
                refusals[path] = (RULE_NONCANONICAL, p.noncanonical_text)
    if RULE_HANDLER in rules.enabled:
        bound = _bound_modules(tree, p)
        candidates = {
            path
            for path in files
            if path.endswith(".py")
            and path.split("/", 1)[0] == p.src_root
            and (
                PurePosixPath(path).name.startswith(p.handler_file_prefix)
                or path in tree.handler_class_paths
            )
        }
        for path in sorted(candidates):
            if path not in refusals and _module_of(path, p) not in bound:
                refusals[path] = (RULE_HANDLER, p.handler_outside_node_text)
    if RULE_CLI_ENTRY in rules.enabled:
        by_module = {
            _module_of(path, p): path for path in files if path.endswith(".py")
        }
        entries = set(tree.argparse_main_paths)
        entries.update(
            by_module[module]
            for module in _script_modules(tree, p)
            if module in by_module
        )
        for path in sorted(entries):
            if (
                path in files
                and path not in refusals
                and not _is_node_runtime(path, files, p)
            ):
                refusals[path] = (RULE_CLI_ENTRY, p.cli_entry_outside_node_text)
    return refusals


def parse_baseline(text: str | None) -> list[str]:
    if text is None:
        return []
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _count_entries(text: str, prefixes: tuple[str, ...]) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(prefixes):
            count += 1
    return count


def _count_matching_lines(text: str, patterns: tuple[str, ...]) -> int:
    compiled = [_regex(pattern) for pattern in patterns]
    return sum(
        1 for line in text.splitlines() if any(rx.search(line) for rx in compiled)
    )


def _count_matches(text: str, patterns: tuple[str, ...]) -> int:
    return sum(len(_regex(pattern).findall(text)) for pattern in patterns)


def _entry_module(entry: object) -> str | None:
    tokens = str(entry or "").split()
    for i, token in enumerate(tokens[:-1]):
        if token == "-m":
            return tokens[i + 1]
    return None


def _safe_load(text: str | None) -> object:
    if text is None:
        return None
    try:
        # the C loader reads the same documents as safe_load, several times faster, and a
        # tree holds hundreds of contract.yaml files
        if hasattr(yaml, "CSafeLoader"):
            return yaml.load(text, Loader=yaml.CSafeLoader)
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def contract_tags(text: str | None, field: str) -> frozenset[str]:
    """The strings listed under ``field`` at the top level of a ``contract.yaml``.

    Empty when the text is absent, is not a mapping, does not parse, or holds a
    value that is not a list.
    """
    document = _safe_load(text)
    if not isinstance(document, dict):
        return frozenset()
    declared = document.get(field)
    if not isinstance(declared, list):
        return frozenset()
    return frozenset(str(item) for item in declared)


def _provided_gate_modules(
    text: str | None, p: ModelCanonicalFileShapeRules
) -> dict[str, str]:
    manifest = _safe_load(text)
    if not isinstance(manifest, list):
        return {}
    provided: dict[str, str] = {}
    for hook in manifest:
        if not isinstance(hook, dict) or hook.get("id") not in p.gate_hook_ids:
            continue
        module = _entry_module(hook.get("entry"))
        if module is not None:
            provided[str(hook["id"])] = module
    return provided


def _declared_gate_baselines(
    text: str | None, provided: Mapping[str, str], p: ModelCanonicalFileShapeRules
) -> set[str]:
    config = _safe_load(text)
    if not isinstance(config, dict):
        return set()
    core_url = _regex(p.gate_repo_url_pattern)
    declared: set[str] = set()
    for entry in config.get("repos") or []:
        if not isinstance(entry, dict):
            continue
        repo_url = str(entry.get("repo", ""))
        is_core = core_url.search(repo_url) is not None
        if not is_core and repo_url != "local":
            continue
        for hook in entry.get("hooks") or []:
            if not isinstance(hook, dict) or hook.get("id") not in p.gate_hook_ids:
                continue
            hook_id = str(hook["id"])
            args = [str(a) for a in hook.get("args") or []]
            if not is_core:
                module = _entry_module(hook.get("entry"))
                if module is None or provided.get(hook_id) != module:
                    continue
                args = str(hook.get("entry")).split() + args
            has_baseline_arg = False
            for i, arg in enumerate(args):
                if arg == "--baseline":
                    has_baseline_arg = True
                    if i + 1 < len(args):
                        declared.add(args[i + 1])
                elif arg.startswith("--baseline="):
                    has_baseline_arg = True
                    declared.add(arg.split("=", 1)[1])
            if not is_core or has_baseline_arg:
                continue
            if hook_id == p.node_boundary_hook_name:
                declared.add(p.node_boundary_baseline)
            elif hook_id == p.model_config_hook_name and "args" not in hook:
                declared.add(p.model_config_baseline)
    return declared


def _declared_guard_allowlists(
    text: str | None, p: ModelCanonicalFileShapeRules
) -> set[str]:
    workflow = _safe_load(text)
    if not isinstance(workflow, dict) or not isinstance(workflow.get("jobs"), dict):
        return set()
    uses = _regex(p.guard_workflow_uses_pattern)
    declared: set[str] = set()
    for job in workflow["jobs"].values():
        if not isinstance(job, dict) or not uses.fullmatch(
            str(job.get("uses", "")).strip()
        ):
            continue
        inputs = job.get("with")
        if not isinstance(inputs, dict):
            continue
        allowlist = inputs.get(p.guard_allowlist_input)
        if isinstance(allowlist, str) and allowlist.strip():
            declared.add(PurePosixPath(allowlist.strip()).as_posix())
    return declared


def declared_paths(
    facts: ModelCanonicalFileShapeFacts, p: ModelCanonicalFileShapeRules
) -> frozenset[str]:
    """Shrink-only gate lists that the head revision declares; they are not exceptions."""
    texts = {item.path: item.text for item in facts.declared_texts}
    declared = _declared_gate_baselines(
        texts.get(p.pre_commit_config_path),
        _provided_gate_modules(texts.get(p.hooks_manifest_path), p),
        p,
    )
    workflows = PurePosixPath(p.workflows_dir)
    for path, text in texts.items():
        pure = PurePosixPath(path)
        if pure.parent == workflows and pure.suffix in {".yml", ".yaml"}:
            declared |= _declared_guard_allowlists(text, p)
    return frozenset(PurePosixPath(item).as_posix() for item in declared)


def _issue(
    rules: ModelCanonicalFileShapeRuleSet, path: str, rule: str, reason: str
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=EnumSeverity(rules.severities.get(rule, EnumSeverity.ERROR.value)),
        message=reason,
        code=rule,
        file_path=Path(path),
        rule_name=rule,
    )


def _is_exception_file(
    path: str, declared: frozenset[str], p: ModelCanonicalFileShapeRules
) -> bool:
    if (
        path in {p.baseline_path, p.burndown_baseline_path, p.node_home_baseline_path}
        or path in declared
    ):
        return False
    if any(part in p.test_dirs for part in PurePosixPath(path).parts[:-1]):
        return False
    suffix = _suffix(path)
    if suffix in p.code_extensions or suffix in p.prose_extensions:
        return False
    return (
        _regex(p.exception_name_pattern, False).search(PurePosixPath(path).name)
        is not None
    )


def _diff_issues(
    rules: ModelCanonicalFileShapeRuleSet,
    path: str,
    new_text: str,
    old_text: str | None,
    declared: frozenset[str],
) -> list[ModelValidationIssue]:
    p = rules.parameters
    issues: list[ModelValidationIssue] = []
    if (
        RULE_SKILL_IMPERATIVE in rules.enabled
        and PurePosixPath(path).name == p.skill_file_name
    ):
        new_n = _count_matching_lines(new_text, p.imperative_patterns)
        old_n = (
            0
            if old_text is None
            else _count_matching_lines(old_text, p.imperative_patterns)
        )
        if new_n > old_n:
            issues.append(
                _issue(
                    rules,
                    path,
                    RULE_SKILL_IMPERATIVE,
                    p.skill_imperative_text.format(old=old_n, new=new_n),
                )
            )
    if _is_exception_file(path, declared, p):
        if old_text is None:
            if RULE_NEW_EXCEPTION in rules.enabled:
                issues.append(
                    _issue(rules, path, RULE_NEW_EXCEPTION, p.new_exception_text)
                )
        elif RULE_EXCEPTION_GROWTH in rules.enabled:
            new_n = _count_entries(new_text, p.comment_prefixes)
            old_n = _count_entries(old_text, p.comment_prefixes)
            if new_n > old_n:
                issues.append(
                    _issue(
                        rules,
                        path,
                        RULE_EXCEPTION_GROWTH,
                        p.exception_growth_text.format(old=old_n, new=new_n),
                    )
                )
    suffix = _suffix(path)
    if RULE_SUPPRESSION_GROWTH in rules.enabled and (
        suffix in p.code_extensions
        or suffix in p.config_extensions
        or (suffix == "" and new_text.startswith(p.shebang_prefix))
    ):
        new_n = _count_matches(new_text, p.suppression_patterns)
        old_n = (
            0 if old_text is None else _count_matches(old_text, p.suppression_patterns)
        )
        if new_n > old_n:
            issues.append(
                _issue(
                    rules,
                    path,
                    RULE_SUPPRESSION_GROWTH,
                    p.suppression_growth_text.format(old=old_n, new=new_n),
                )
            )
    return issues


_STATE_UNKNOWN = -1


def _lifecycle_state(
    text: str | None, p: ModelCanonicalFileShapeRules
) -> tuple[int, str | None]:
    """``(rank, error)``; rank is the state's position in ``lifecycle_states``."""
    if text is None:
        return _STATE_UNKNOWN, None
    document = _safe_load(text)
    state = document.get(p.lifecycle_state_key) if isinstance(document, dict) else None
    if isinstance(state, str) and state in p.lifecycle_states:
        return p.lifecycle_states.index(state), None
    return _STATE_UNKNOWN, (
        f"{p.lifecycle_path}: '{p.lifecycle_state_key}' must be one of "
        f"{', '.join(p.lifecycle_states)}"
    )


def _lifecycle_issues(
    facts: ModelCanonicalFileShapeFacts, rules: ModelCanonicalFileShapeRuleSet
) -> list[ModelValidationIssue]:
    p = rules.parameters
    if RULE_LIFECYCLE not in rules.enabled:
        return []
    head_rank, head_error = _lifecycle_state(facts.head_lifecycle_text, p)
    base_rank, _base_error = _lifecycle_state(facts.base_lifecycle_text, p)
    issues: list[ModelValidationIssue] = []
    if head_error is not None:
        issues.append(_issue(rules, p.lifecycle_path, RULE_LIFECYCLE, head_error))
    rank = max(head_rank, base_rank)
    if rank == _STATE_UNKNOWN:
        return issues
    state = p.lifecycle_states[rank]
    trailer = _regex(rf"^{re.escape(p.release_trailer_key)}=\S+", True)
    stamped = facts.commit_messages is not None and any(
        trailer.search(message) for message in facts.commit_messages
    )
    heads = _heads(facts.head_tree)
    for change in facts.changes:
        if state == p.retired_state:
            if RULE_RETIRED in rules.enabled:
                issues.append(_issue(rules, change.path, RULE_RETIRED, p.retired_text))
            continue
        head_text = (
            change.new_text
            if change.new_text is not None
            else heads.get(change.path, b"").decode(errors="replace")
        )
        if not _is_code(change.path, head_text, p):
            continue
        new_n = _count_entries(change.new_text or "", p.comment_prefixes)
        old_n = (
            0
            if change.old_text is None
            else _count_entries(change.old_text, p.comment_prefixes)
        )
        added = change.old_text is None
        grown = new_n > old_n
        if state == p.no_code_state and (added or grown):
            if RULE_NO_CODE in rules.enabled:
                issues.append(_issue(rules, change.path, RULE_NO_CODE, p.no_code_text))
        elif state == p.fix_only_state:
            if added:
                if RULE_FIX_ONLY_NEW in rules.enabled:
                    issues.append(
                        _issue(
                            rules,
                            change.path,
                            RULE_FIX_ONLY_NEW,
                            p.fix_only_new_file_text,
                        )
                    )
            elif (
                grown
                and facts.commit_messages is not None
                and not stamped
                and RULE_FIX_ONLY_GROWTH in rules.enabled
            ):
                issues.append(
                    _issue(
                        rules,
                        change.path,
                        RULE_FIX_ONLY_GROWTH,
                        p.fix_only_growth_text.format(
                            old=old_n, new=new_n, key=p.release_trailer_key
                        ),
                    )
                )
    return issues


def _burndown_ticket_line(text: str, p: ModelCanonicalFileShapeRules) -> str | None:
    """The first comment line of the burn-down file that reads as its ticket header."""
    first = next(
        (
            line
            for line in text.splitlines()
            if line.strip().startswith(p.comment_prefixes)
        ),
        None,
    )
    if first is None or _regex(p.burndown_ticket_pattern).search(first) is None:
        return None
    return first


def _burndown_ticket_named(text: str, p: ModelCanonicalFileShapeRules) -> bool:
    """Whether the first comment line of the burn-down file names a ticket."""
    return _burndown_ticket_line(text, p) is not None


def _burndown_install_issues(
    facts: ModelCanonicalFileShapeFacts,
    rules: ModelCanonicalFileShapeRuleSet,
    head_burndown: str,
) -> list[ModelValidationIssue]:
    """First install only: the entries must be base findings, under the change's own ticket."""
    p = rules.parameters
    issues: list[ModelValidationIssue] = []
    if RULE_BURNDOWN_EXTRA in rules.enabled:
        status_of = {change.path: change.status for change in facts.changes}
        listed = set(parse_baseline(facts.head_baseline_text))
        for path in sorted(set(parse_baseline(head_burndown))):
            status = status_of.get(path)
            if status is not None and status not in p.burndown_base_statuses:
                reason = p.burndown_extra_added_text.format(path=path, status=status)
            elif path in listed:
                reason = p.burndown_extra_duplicate_text.format(
                    path=path, baseline=p.baseline_path
                )
            else:
                continue
            issues.append(
                _issue(rules, p.burndown_baseline_path, RULE_BURNDOWN_EXTRA, reason)
            )
    line = _burndown_ticket_line(head_burndown, p)
    found = None if line is None else _regex(p.burndown_ticket_id_pattern).search(line)
    if (
        RULE_BURNDOWN_UNCITED in rules.enabled
        and facts.commit_messages is not None
        and found is not None
    ):
        ticket = found.group(0)
        cited = _regex(
            p.burndown_ticket_citation_pattern.replace("{ticket}", re.escape(ticket)),
            True,
        )
        if not any(cited.search(message) for message in facts.commit_messages):
            issues.append(
                _issue(
                    rules,
                    p.burndown_baseline_path,
                    RULE_BURNDOWN_UNCITED,
                    p.burndown_ticket_uncited_text.format(ticket=ticket),
                )
            )
    return issues


def check(
    facts: ModelCanonicalFileShapeFacts, rules: ModelCanonicalFileShapeRuleSet
) -> tuple[ModelValidationIssue, ...]:
    """Every issue for the head revision against the baselines and the base revision."""
    p = rules.parameters
    issues: list[ModelValidationIssue] = []
    refused = file_rule_refusals(facts.head_tree, rules)
    # (path, head entries, base entries, stale text, growth text, base file present)
    lists = (
        (
            p.baseline_path,
            set(parse_baseline(facts.head_baseline_text)),
            set(parse_baseline(facts.base_baseline_text)),
            p.baseline_stale_text,
            p.baseline_growth_text,
            facts.base_baseline_text is not None,
        ),
        (
            p.burndown_baseline_path,
            set(parse_baseline(facts.head_burndown_text)),
            set(parse_baseline(facts.base_burndown_text)),
            p.burndown_stale_text,
            p.burndown_growth_text,
            facts.base_burndown_text is not None,
        ),
    )
    baselined = set().union(*(entry[1] for entry in lists))
    renames_by_list = [
        {
            change.path: change.old_path
            for change in facts.changes
            if change.status == "R"
            and change.old_path is not None
            and change.old_path in base_entries
            and change.path in refused
        }
        for _, _, base_entries, _, _, _ in lists
    ]
    renames = {path: old for found in renames_by_list for path, old in found.items()}
    renamed_from = set(renames.values())
    declared = declared_paths(facts, p)

    for path, (rule, reason) in sorted(refused.items()):
        if path not in baselined and path not in renames:
            issues.append(_issue(rules, path, rule, reason))
    if RULE_BASELINE_STALE in rules.enabled:
        for location, head_entries, _, stale_text, _, _ in lists:
            for path in sorted(head_entries - set(refused) - renamed_from):
                issues.append(
                    _issue(
                        rules,
                        location,
                        RULE_BASELINE_STALE,
                        stale_text.format(path=path),
                    )
                )
    if (
        RULE_BURNDOWN_TICKET in rules.enabled
        and facts.head_burndown_text is not None
        and not _burndown_ticket_named(facts.head_burndown_text, p)
    ):
        issues.append(
            _issue(
                rules,
                p.burndown_baseline_path,
                RULE_BURNDOWN_TICKET,
                p.burndown_ticket_missing_text,
            )
        )

    if not facts.has_base:
        return tuple(issues)

    if RULE_BASELINE_GROWTH in rules.enabled:
        for (
            location,
            head_entries,
            base_entries,
            _,
            growth_text,
            installed,
        ), found in zip(lists, renames_by_list, strict=True):
            if not installed:
                continue
            for path in sorted(head_entries - base_entries):
                if path in found and found[path] not in head_entries:
                    continue
                issues.append(
                    _issue(
                        rules,
                        location,
                        RULE_BASELINE_GROWTH,
                        growth_text.format(path=path),
                    )
                )
    if (
        RULE_BURNDOWN_REMOVED in rules.enabled
        and facts.base_burndown_text is not None
        and facts.head_burndown_text is None
    ):
        issues.append(
            _issue(
                rules,
                p.burndown_baseline_path,
                RULE_BURNDOWN_REMOVED,
                p.burndown_removed_text,
            )
        )

    if facts.base_burndown_text is None and facts.head_burndown_text is not None:
        issues.extend(_burndown_install_issues(facts, rules, facts.head_burndown_text))

    grown_set = baselined | set(renames)
    for change in facts.changes:
        if change.new_text is None:
            continue
        issues.extend(
            _diff_issues(rules, change.path, change.new_text, change.old_text, declared)
        )
        if (
            RULE_BASELINED_GROWTH in rules.enabled
            and change.old_text is not None
            and change.path in grown_set
        ):
            new_n = _count_entries(change.new_text, p.comment_prefixes)
            old_n = _count_entries(change.old_text, p.comment_prefixes)
            if new_n > old_n:
                issues.append(
                    _issue(
                        rules,
                        change.path,
                        RULE_BASELINED_GROWTH,
                        p.baselined_growth_text.format(old=old_n, new=new_n),
                    )
                )
    issues.extend(_lifecycle_issues(facts, rules))
    return tuple(issues)
