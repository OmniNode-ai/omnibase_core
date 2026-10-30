# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the cosmetic-lint hook (OMN-20074, OMN-21518).

``main`` gathers the snapshot of the working directory through the source-file
gather EFFECT, reads the rule rows of ``cosmetic_lint.validation.yaml``, hands both
to the pure ``HandlerCosmeticLint`` and prints one line per violation to stderr,
in the source's ``path:line: [check] message [fixable]`` form. Only ``check`` is
ported: the exported hook never ran ``fix``, and the best-effort Kafka score event
of the source (a no-op unless the optional ``kafka`` extra was installed) is not.

Usage::

    python -m omnibase_core.nodes.node_cosmetic_lint_check_compute.runtime_cosmetic_lint_check [check]

Exit code 0 = clean. Exit code 1 = violations found, or a file unreadable.
Exit code 2 = unsupported arguments.
"""

from __future__ import annotations

import importlib.resources
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_github_snapshot import (
    ModelCosmeticGithubSnapshot,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_lint_input import (
    ModelCosmeticLintInput,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_lint_rules import (
    ModelCosmeticLintRules,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_cosmetic_lint_check_compute.handler_cosmetic_lint import (
    HandlerCosmeticLint,
    select_python_paths,
    spdx_file_patterns,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
)

__all__ = [
    "CLI_USAGE_RULE",
    "SPEC_RESOURCE",
    "build_rules",
    "load_rule_rows",
    "load_rules",
    "load_spec_yaml",
    "main",
]

SPEC_RESOURCE: Final[str] = "cosmetic_lint_spec.yaml"
RULES_RESOURCE: Final[str] = "cosmetic_lint.validation.yaml"
CLI_USAGE_RULE: Final[str] = "cli_usage"
USAGE_ERROR: Final[int] = 2


_HANDLER_COSMETIC_LINT_TOKEN = cast("type[HandlerCosmeticLint]", HandlerCosmeticLint)
_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN = cast(
    "type[NodeSourceFileGatherEffect]", NodeSourceFileGatherEffect
)


def load_spec_yaml() -> str:
    """Return the packaged cosmetic spec, byte for byte, as text."""
    ref = importlib.resources.files("omnibase_core.contracts") / SPEC_RESOURCE
    return ref.read_text(encoding="utf-8")


def load_rule_rows(contract_text: str | None = None) -> dict[str, ModelValidatorRule]:
    """The rule rows of ``cosmetic_lint.validation.yaml`` by rule id, in file order.

    ``contract_text`` replaces the packaged file; tests mutate a parameter that way.
    """
    if contract_text is None:
        ref = (
            importlib.resources.files("omnibase_core.validation.contracts")
            / RULES_RESOURCE
        )
        contract_text = ref.read_text(encoding="utf-8")
    document = load_yaml_mapping_no_duplicates(contract_text, source=RULES_RESOURCE)
    body = document.get("validation") if isinstance(document, Mapping) else None
    if not isinstance(body, Mapping):
        raise ModelOnexError(
            message=f"{RULES_RESOURCE} has no 'validation' mapping",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    contract = ModelValidatorSubcontract.model_validate(body)
    return {rule.rule_id: rule for rule in contract.rules}


def build_rules(rows: Mapping[str, ModelValidatorRule]) -> ModelCosmeticLintRules:
    """The typed rule data the pure handler reads, from the rule rows."""

    def row(rule_id: str) -> ModelValidatorRule:
        if rule_id not in rows:
            raise ModelOnexError(
                message=f"{RULES_RESOURCE} has no rule {rule_id!r}",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
        return rows[rule_id]

    return ModelCosmeticLintRules(
        checks=tuple(
            rule_id
            for rule_id, rule in rows.items()
            if rule.enabled and rule_id != CLI_USAGE_RULE
        ),
        spdx_skip_marker=rule_string(row("spdx"), "skip_marker"),
        pyproject_path=rule_string(row("pyproject"), "path"),
        precommit_path=rule_string(row("precommit"), "path"),
        readme_path=rule_string(row("readme"), "path"),
        readme_header_lines=rule_int(row("readme"), "header_lines"),
        github_directory=rule_string(row("github"), "directory"),
    )


def load_rules() -> ModelCosmeticLintRules:
    """The packaged rule data."""
    return build_rules(load_rule_rows())


def _github_snapshot(root: Path, directory: str) -> ModelCosmeticGithubSnapshot | None:
    github_dir = root / directory
    if not github_dir.is_dir():
        return None
    return ModelCosmeticGithubSnapshot(
        entries=sorted(
            p.relative_to(github_dir).as_posix()
            for p in github_dir.rglob("*")
            if p.exists()
        )
    )


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_HANDLER_COSMETIC_LINT_TOKEN, HandlerCosmeticLint),
        (_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN, NodeSourceFileGatherEffect),
    ):
        run_coro_sync(
            registry.register_service(
                token,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(
    argv: Sequence[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: Sequence[str] | None, container: ModelONEXContainer) -> int:
    """Run the exported hook on the working directory."""
    args = list(sys.argv[1:] if argv is None else argv)
    rows = load_rule_rows()
    if args not in ([], ["check"]):
        sys.stderr.write(rule_string(rows[CLI_USAGE_RULE], "usage_message"))
        return USAGE_ERROR
    rules = build_rules(rows)
    root = Path()
    spec_yaml = load_spec_yaml()
    candidates = [
        path.as_posix()
        for pattern in spdx_file_patterns(spec_yaml)
        for path in root.rglob(pattern)
        if path.is_file()
    ]
    named = [
        name
        for name in (rules.pyproject_path, rules.precommit_path, rules.readme_path)
        if (root / name).exists()
    ]
    wanted = [*select_python_paths(spec_yaml, candidates), *named]
    # An empty explicit list would make the gather effect walk the whole tree.
    gathered = (
        container.get_service(_NODE_SOURCE_FILE_GATHER_EFFECT_TOKEN).handle(
            ModelSourceFileGatherInput(
                root=".", explicit_paths=wanted, include_patterns=["**/*"]
            )
        )
        if wanted
        else None
    )
    if gathered is not None and gathered.skipped:
        for skipped in gathered.skipped:
            sys.stderr.write(f"ERROR: {skipped.path}: {skipped.reason}\n")
        return 1
    texts = {f.path: f.source for f in gathered.files} if gathered else {}
    report = container.get_service(_HANDLER_COSMETIC_LINT_TOKEN).handle(
        ModelCosmeticLintInput(
            spec_yaml=spec_yaml,
            rules=rules,
            python_files=[
                ModelSourceFile(path=path, source=source)
                for path, source in texts.items()
                if path not in named
            ],
            pyproject_toml=texts.get(rules.pyproject_path),
            precommit_config=texts.get(rules.precommit_path),
            readme=texts.get(rules.readme_path),
            github=_github_snapshot(root, rules.github_directory),
        )
    )
    for finding in report.findings:
        sys.stderr.write(f"{finding.message}\n")
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
