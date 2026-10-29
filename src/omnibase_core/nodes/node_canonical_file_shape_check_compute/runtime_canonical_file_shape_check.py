# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Git facts and CLI of the canonical-file-shape COMPUTE check (OMN-20304, OMN-21515).

The hook ``canonical-file-shape`` runs this module. It reads a revision of the
repository through git, hands the facts and the validator contract to the pure
node handler, resolves the report writer from the container and prints one line
per finding. Usage::

    python -m omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check --base origin/dev --head HEAD
    python -m ...runtime_canonical_file_shape_check --write-baseline
    python -m ...runtime_canonical_file_shape_check --prune-baseline
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

from omnibase_core.enums.enum_canonical_file_shape_rule_group import (
    EnumCanonicalFileShapeRuleGroup,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_canonical_file_shape_change import (
    ModelCanonicalFileShapeChange,
)
from omnibase_core.models.validation.model_canonical_file_shape_check_input import (
    ModelCanonicalFileShapeCheckInput,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.models.validation.model_canonical_file_shape_rules import (
    ModelCanonicalFileShapeRules,
)
from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)
from omnibase_core.models.validation.model_canonical_file_shape_tree import (
    ModelCanonicalFileShapeTree,
)
from omnibase_core.models.validation.model_node_home_ratchet_request import (
    ModelNodeHomeRatchetRequest,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.handler import (
    NodeCanonicalFileShapeCheckCompute,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.matcher_node_home import (
    eligible,
    node_directories,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.checker_canonical_file_shape import (
    file_rule_refusals,
    load_rule_set,
    parse_baseline,
)
from omnibase_core.validation.validator_canonical_file_shape import (
    ValidatorCanonicalFileShape,
    write_text_file,
)
from omnibase_core.validation.validator_git_repo import INDEX, GitCommandError, GitRepo


def _decode(blob: bytes | None) -> str | None:
    return None if blob is None else blob.decode("utf-8", errors="replace")


def gather_tree(
    repo: GitRepo, rev: str, p: ModelCanonicalFileShapeRules
) -> ModelCanonicalFileShapeTree:
    """The facts the file rules read from ``rev``."""
    files = repo.list_files(rev)
    extensionless = [f for f in files if not PurePosixPath(f).suffix]
    contracts = [f for f in files if PurePosixPath(f).name == p.contract_file_name]
    sources = [
        f for f in files if f.endswith(".py") and f.split("/", 1)[0] == p.src_root
    ]
    blobs = repo.read_blobs(
        rev, [*extensionless, *contracts, *sources, "pyproject.toml"]
    )
    handler_class = re.compile(p.handler_class_pattern, re.MULTILINE)
    argparse_use = re.compile(p.argparse_pattern)
    main_def = re.compile(p.main_pattern, re.MULTILINE)
    shebangs: list[ModelCanonicalFileShapeText] = []
    for path in extensionless:
        blob = blobs.get(path)
        if blob is not None and blob.startswith(p.shebang_prefix.encode()):
            first = blob.split(b"\n", 1)[0].decode(errors="replace")
            shebangs.append(ModelCanonicalFileShapeText(path=path, text=first))
    handler_paths: list[str] = []
    cli_paths: list[str] = []
    for path in sources:
        text = _decode(blobs.get(path))
        if text is None:
            continue
        if handler_class.search(text):
            handler_paths.append(path)
        if argparse_use.search(text) and main_def.search(text):
            cli_paths.append(path)
    return ModelCanonicalFileShapeTree(
        files=tuple(files),
        shebang_lines=tuple(shebangs),
        handler_class_paths=tuple(handler_paths),
        argparse_main_paths=tuple(cli_paths),
        contract_texts=tuple(
            ModelCanonicalFileShapeText(path=path, text=text)
            for path in contracts
            if (text := _decode(blobs.get(path))) is not None
        ),
        pyproject_text=_decode(blobs.get("pyproject.toml")),
    )


MERGE_HEAD = "MERGE_HEAD"


def resolve_revisions(
    repo: GitRepo, base: str | None, head: str | None
) -> tuple[str, str | None]:
    """``(head, base)``: the flags as given, else the index against ``HEAD``.

    A merge commit in progress (``MERGE_HEAD`` exists) is checked against the branch being
    merged in, the way the CI run checks a head against its merge base: against the first
    parent every file the merged-in branch brings would read as a new file of the change.
    """
    resolved_head = head or INDEX
    if base is not None:
        return resolved_head, base
    if resolved_head == INDEX and repo.has_revision(MERGE_HEAD):
        return resolved_head, MERGE_HEAD
    if resolved_head == INDEX and repo.has_revision("HEAD"):
        return resolved_head, "HEAD"
    return resolved_head, None


def gather_facts(
    repo: GitRepo,
    p: ModelCanonicalFileShapeRules,
    head: str,
    base: str | None,
    commit_message: str | None,
) -> ModelCanonicalFileShapeFacts:
    """Read the head tree, the baseline pair, the changes and the lifecycle texts."""
    head_tree = gather_tree(repo, head, p)
    workflows = [
        f
        for f in head_tree.files
        if PurePosixPath(f).parent.as_posix() == p.workflows_dir
        and PurePosixPath(f).suffix in {".yml", ".yaml"}
    ]
    head_blobs = repo.read_blobs(
        head,
        [
            p.baseline_path,
            p.lifecycle_path,
            p.pre_commit_config_path,
            p.hooks_manifest_path,
            *workflows,
        ],
    )
    declared = tuple(
        ModelCanonicalFileShapeText(path=path, text=text)
        for path in (p.pre_commit_config_path, p.hooks_manifest_path, *workflows)
        if (text := _decode(head_blobs.get(path))) is not None
    )
    head_baseline = _decode(head_blobs.get(p.baseline_path))
    if base is None:
        return ModelCanonicalFileShapeFacts(
            head_tree=head_tree,
            head_baseline_text=head_baseline,
            declared_texts=declared,
            head_lifecycle_text=_decode(head_blobs.get(p.lifecycle_path)),
            commit_messages=None if commit_message is None else (commit_message,),
        )
    base_blobs = repo.read_blobs(base, [p.baseline_path, p.lifecycle_path])
    base_baseline = _decode(base_blobs.get(p.baseline_path))
    raw_changes = [c for c in repo.changed_paths(base, head) if c[0] != "D"]
    head_text = repo.read_blobs(head, [path for _, path, _ in raw_changes])
    base_text = repo.read_blobs(base, [old or path for _, path, old in raw_changes])
    changes = tuple(
        ModelCanonicalFileShapeChange(
            status=status,
            path=path,
            old_path=old,
            new_text=_decode(head_text.get(path)),
            old_text=_decode(base_text.get(old or path)),
        )
        for status, path, old in raw_changes
    )
    new_entries = set(parse_baseline(head_baseline)) - set(
        parse_baseline(base_baseline)
    )
    base_tree = (
        gather_tree(repo, base, p)
        if base_baseline is not None and new_entries
        else None
    )
    if commit_message is not None:
        messages: tuple[str, ...] | None = (commit_message,)
    elif head != INDEX:
        messages = repo.commit_messages(base, head)
    else:
        messages = None
    return ModelCanonicalFileShapeFacts(
        head_tree=head_tree,
        base_tree=base_tree,
        has_base=True,
        head_baseline_text=head_baseline,
        base_baseline_text=base_baseline,
        declared_texts=declared,
        changes=changes,
        head_lifecycle_text=_decode(head_blobs.get(p.lifecycle_path)),
        base_lifecycle_text=_decode(base_blobs.get(p.lifecycle_path)),
        commit_messages=messages,
    )


def _has_node_class(blob: bytes, p: ModelCanonicalFileShapeRules) -> bool:
    node_class = re.compile(p.node_home_node_class_pattern)
    tree = ast.parse(blob)
    return any(
        isinstance(statement, ast.ClassDef)
        and node_class.fullmatch(statement.name) is not None
        for statement in tree.body
    )


def _python_paths(paths: frozenset[str], p: ModelCanonicalFileShapeRules) -> list[str]:
    return sorted(
        path
        for path in paths
        if path.endswith(p.node_home_source_suffix)
        and eligible(posix_path := PurePosixPath(path), p)
        and (
            posix_path.parent.name.startswith(p.node_home_node_dir_prefix)
            or (posix_path.parent / p.contract_file_name).as_posix() in paths
        )
    )


def _node_class_paths(
    blobs: Mapping[str, bytes | None], p: ModelCanonicalFileShapeRules
) -> frozenset[str]:
    return frozenset(
        path
        for path, blob in blobs.items()
        if path.endswith(p.node_home_source_suffix)
        and blob is not None
        and _has_node_class(blob, p)
    )


def _entry_points(
    blob: bytes | None, p: ModelCanonicalFileShapeRules
) -> frozenset[str]:
    if blob is None:
        return frozenset()
    table = tomllib.loads(blob.decode("utf-8"))
    for key in p.node_home_entry_point_path:
        value = table.get(key, {})
        if not isinstance(value, dict):
            raise ModelOnexError(
                message=f"pyproject.toml {key} must be a table",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        table = value
    return frozenset(table)


def gather_node_home_request(
    repo: GitRepo, head: str, base: str | None, p: ModelCanonicalFileShapeRules
) -> ModelNodeHomeRatchetRequest:
    """Gather head and base-revision node inventories, registrations and renames."""
    repo.run("rev-parse", "--show-toplevel")
    if head == INDEX and repo.run("ls-files", "-u"):
        raise ModelOnexError(
            message="resolve unmerged index entries before checking node homes",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    paths = frozenset(repo.list_files(head))
    blobs = repo.read_blobs(
        head,
        [*_python_paths(paths, p), p.node_home_baseline_path, "pyproject.toml"],
    )
    node_class_paths = _node_class_paths(blobs, p)
    contract_paths = [
        f"{directory}/{p.contract_file_name}"
        for directory in node_directories(paths, node_class_paths, p)
        if f"{directory}/{p.contract_file_name}" in paths
    ]
    contract_blobs = repo.read_blobs(head, contract_paths)
    base_blob: bytes | None = None
    base_nodes: frozenset[str] = frozenset()
    base_entry_points: frozenset[str] = frozenset()
    renamed: tuple[tuple[str, str], ...] = ()
    if base is not None:
        if not repo.has_revision(base):
            raise ModelOnexError(
                message=f"base revision does not exist: {base}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        base_blobs = repo.read_blobs(
            base, [p.node_home_baseline_path, "pyproject.toml"]
        )
        base_blob = base_blobs[p.node_home_baseline_path]
        base_entry_points = _entry_points(base_blobs["pyproject.toml"], p)
        renamed = tuple(
            (old, path)
            for status, path, old in repo.changed_paths(base, head)
            if status == "R" and old is not None
        )
        if base_blob is None:
            base_paths = frozenset(repo.list_files(base))
            base_python = repo.read_blobs(base, _python_paths(base_paths, p))
            base_nodes = frozenset(
                node_directories(base_paths, _node_class_paths(base_python, p), p)
            )
    head_blob = blobs[p.node_home_baseline_path]
    return ModelNodeHomeRatchetRequest(
        tracked_paths=paths,
        node_class_paths=node_class_paths,
        node_contract_texts=tuple(
            ModelCanonicalFileShapeText(path=path, text=text)
            for path in contract_paths
            if (text := _decode(contract_blobs.get(path))) is not None
        ),
        head_baseline_text=_decode(head_blob),
        base_baseline_text=_decode(base_blob),
        base_node_directories=base_nodes,
        head_entry_points=_entry_points(blobs["pyproject.toml"], p),
        base_entry_points=base_entry_points,
        renamed_paths=renamed,
    )


def build_container() -> ModelONEXContainer:
    """The composition root: a container with the report writer registered."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry()
    run_coro_sync(
        registry.register_instance(
            NodeValidationReportWriteEffect, NodeValidationReportWriteEffect()
        )
    )
    return container


def run_check(
    container: ModelONEXContainer,
    repo: GitRepo,
    base: str | None,
    head: str | None,
    commit_message: str | None,
    report_json: str | None,
    rule_groups: Sequence[str] = tuple(EnumCanonicalFileShapeRuleGroup),
) -> ModelValidationReport:
    """Gather facts, run the pure node, write the report through the container's writer."""
    validator = ValidatorCanonicalFileShape()
    contract = validator.contract
    p = load_rule_set(contract).parameters
    resolved_head, resolved_base = resolve_revisions(repo, base, head)
    facts = (
        gather_facts(repo, p, resolved_head, resolved_base, commit_message)
        if EnumCanonicalFileShapeRuleGroup.FILE_SHAPE in rule_groups
        else None
    )
    node_home = (
        gather_node_home_request(repo, resolved_head, resolved_base, p)
        if EnumCanonicalFileShapeRuleGroup.NODE_HOME in rule_groups
        else None
    )
    report = NodeCanonicalFileShapeCheckCompute().handle(
        ModelCanonicalFileShapeCheckInput(
            facts=facts, node_home=node_home, contract=contract
        )
    )
    if report_json is not None:
        writer = container.get_service(NodeValidationReportWriteEffect)
        writer.handle(
            ModelValidationReportWriteInput(report_path=report_json, report=report)
        )
    return report


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refuse new code files outside canonical locations, handlers and command "
            "line entries outside a node, new imperative code in skills, growth of a "
            "baselined file, new exception entries and changes a repository lifecycle "
            "declaration does not admit."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base", default=None, help="base revision")
    parser.add_argument("--head", default=None, help="head revision (default: index)")
    parser.add_argument(
        "--commit-message-file",
        type=Path,
        default=None,
        help="the commit message whose release= trailer admits fix-only growth",
    )
    parser.add_argument("--report-json", default=None)
    parser.add_argument(
        "--rules",
        action="append",
        choices=[group.value for group in EnumCanonicalFileShapeRuleGroup],
        default=None,
        help="rule group to run (repeatable); default: all",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="create the baseline from the head; refused when one exists",
    )
    parser.add_argument(
        "--prune-baseline",
        action="store_true",
        help="delete baseline entries that no file rule refuses any more",
    )
    parser.add_argument(
        "filenames", nargs="*", help="ignored; the whole tree is checked"
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    container: ModelONEXContainer | None = None,
) -> int:
    """Check the head revision, or write or prune the baseline; return 0, 1 or 2."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    p = load_rule_set(ValidatorCanonicalFileShape().contract).parameters
    repo = GitRepo(
        root=args.repo_root, env=env, cat_file_timeout_s=p.cat_file_timeout_s
    )
    baseline_file = args.repo_root / p.baseline_path

    if args.write_baseline or args.prune_baseline:
        refused = sorted(
            file_rule_refusals(
                gather_tree(repo, args.head or INDEX, p),
                load_rule_set(ValidatorCanonicalFileShape().contract),
            )
        )
        if args.write_baseline:
            if baseline_file.exists():
                sys.stderr.write(
                    f"{p.baseline_path} exists; a baseline is written once, then only shrinks\n"
                )
                return 1
            write_text_file(
                baseline_file,
                p.baseline_header + "".join(f"{path}\n" for path in refused),
            )
            sys.stdout.write(f"wrote {len(refused)} entries to {p.baseline_path}\n")
            return 0
        current = parse_baseline(
            baseline_file.read_text(encoding="utf-8")
            if baseline_file.exists()
            else None
        )
        kept = [path for path in current if path in set(refused)]
        write_text_file(
            baseline_file,
            p.baseline_header + "".join(f"{path}\n" for path in sorted(set(kept))),
        )
        sys.stdout.write(
            f"pruned {len(current) - len(kept)} entries from {p.baseline_path}\n"
        )
        return 0

    message = (
        None
        if args.commit_message_file is None
        else args.commit_message_file.read_text(encoding="utf-8", errors="replace")
    )
    try:
        report = run_check(
            container or build_container(),
            repo,
            args.base,
            args.head,
            message,
            args.report_json,
            args.rules or tuple(EnumCanonicalFileShapeRuleGroup),
        )
    except (OSError, ValueError, SyntaxError, ModelOnexError, GitCommandError) as exc:
        sys.stderr.write(f"canonical-file-shape: {exc}\n")
        return 2
    if report.overall_status == "PASS":
        return 0
    sys.stderr.write("Canonical-file-shape ratchet (OMN-20304) refused this change:\n")
    for finding in report.findings:
        sys.stderr.write(
            f"  {(finding.location or '').removesuffix(':1')}: [{finding.rule_id}] {finding.message}\n"
        )
    sys.stderr.write(
        "\nOperator ruling 2026-10-01: no new scripts, plugins or exceptions. "
        "Build new capability as contract + node + handler. The baseline only "
        "shrinks; there is no suppression.\n"
    )
    return 2 if report.overall_status == "ERROR" else 1


if __name__ == "__main__":
    sys.exit(main())
