# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Replay adapter for ``canonical_file_shape``: one path of a revision into ``check``.

The checker reads a whole revision, not a file. The facts are gathered the way the node runtime
gathers them (``gather_tree`` and ``gather_facts`` of ``runtime_canonical_file_shape_check``), from the
audited revision instead of a working tree, and narrowed to what the verdict on the audited path
reads: the whole file list, every ``contract.yaml``, the audited file's own handler, command line and
shebang facts, the baseline pair and lifecycle text at the head, and, when the assertion names a base
revision, the same texts and the audited file's change at that revision. The issues returned are those
reported at the audited path.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_canonical_file_shape_change import (
    ModelCanonicalFileShapeChange,
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
from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)
from omnibase_core.models.validation.model_canonical_file_shape_tree import (
    ModelCanonicalFileShapeTree,
)
from omnibase_core.validation.checker_canonical_file_shape import check, load_rule_set
from tests.fixtures.andon_replay import driver
from tests.fixtures.andon_replay.driver import ReplayContract, ReplayRun, in_scope

# The fact roles an assertion's input bundle uses for this checker.
ROLE_NODE_CONTRACTS = "node_contracts"
ROLE_BASE_REVISION = "base_revision"

type TextOf = Callable[[str], str | None]


def _revision_reader(revision: str) -> TextOf:
    """Read a path at ``revision`` from whichever corpus clone holds that commit.

    ``ReplaySource.fact_text`` reads a fact's own path, and a revision fact names none, so the
    base revision's blobs are read here, through the driver's clone resolution.
    """
    corpus = driver.load_corpus(driver.DEFAULT_CORPUS_PATH)
    clone_root = driver.environment(corpus).get(corpus.resolution.clone_root_env, "")
    timeout = corpus.resolution.git_timeout_seconds
    if clone_root:
        for name in dict.fromkeys(corpus.resolution.clone_dirs.values()):
            clone = Path(clone_root) / name
            if clone.is_dir() and driver._commit_exists(clone, revision, timeout):
                return lambda path: driver._git_text(clone, timeout, revision, path)
    return lambda _path: None


def _tree(
    p: ModelCanonicalFileShapeRules,
    path: str,
    files: Sequence[str],
    contract_paths: Sequence[str],
    text_of: TextOf,
) -> ModelCanonicalFileShapeTree:
    """``gather_tree`` for the audited path: its own facts, every contract, the whole file list."""
    text = text_of(path)
    shebangs: list[ModelCanonicalFileShapeText] = []
    handlers: list[str] = []
    entries: list[str] = []
    if text is not None:
        if not PurePosixPath(path).suffix and text.startswith(p.shebang_prefix):
            shebangs.append(
                ModelCanonicalFileShapeText(path=path, text=text.split("\n", 1)[0])
            )
        if path.endswith(".py") and path.split("/", 1)[0] == p.src_root:
            if re.search(p.handler_class_pattern, text, re.MULTILINE):
                handlers.append(path)
            if re.search(p.argparse_pattern, text) and re.search(
                p.main_pattern, text, re.MULTILINE
            ):
                entries.append(path)
    return ModelCanonicalFileShapeTree(
        files=tuple(files),
        shebang_lines=tuple(shebangs),
        handler_class_paths=tuple(handlers),
        argparse_main_paths=tuple(entries),
        contract_texts=tuple(
            ModelCanonicalFileShapeText(path=name, text=body)
            for name in contract_paths
            if (body := text_of(name)) is not None
        ),
        pyproject_text=text_of("pyproject.toml"),
    )


def _facts(
    p: ModelCanonicalFileShapeRules,
    path: str,
    files: Sequence[str],
    contract_paths: Sequence[str],
    head: TextOf,
    base: TextOf | None,
) -> ModelCanonicalFileShapeFacts:
    """``gather_facts`` for the audited path: head tree and texts, and the change against ``base``."""
    workflows = [
        name
        for name in files
        if PurePosixPath(name).parent.as_posix() == p.workflows_dir
        and PurePosixPath(name).suffix in {".yml", ".yaml"}
    ]
    declared = tuple(
        ModelCanonicalFileShapeText(path=name, text=body)
        for name in (p.pre_commit_config_path, p.hooks_manifest_path, *workflows)
        if (body := head(name)) is not None
    )
    at_head = ModelCanonicalFileShapeFacts(
        head_tree=_tree(p, path, files, contract_paths, head),
        head_baseline_text=head(p.baseline_path),
        head_burndown_text=head(p.burndown_baseline_path),
        declared_texts=declared,
        head_lifecycle_text=head(p.lifecycle_path),
    )
    if base is None:
        return at_head
    new_text = head(path)
    old_text = base(path)
    changes = (
        (
            ModelCanonicalFileShapeChange(
                status="M" if old_text is not None else "A",
                path=path,
                new_text=new_text,
                old_text=old_text,
            ),
        )
        if new_text is not None and new_text != old_text
        else ()
    )
    return at_head.model_copy(
        update={
            "has_base": True,
            "base_baseline_text": base(p.baseline_path),
            "base_burndown_text": base(p.burndown_baseline_path),
            "base_lifecycle_text": base(p.lifecycle_path),
            "changes": changes,
        }
    )


def _named_modules(
    text: str | None, line: int | None, p: ModelCanonicalFileShapeRules
) -> frozenset[str]:
    """Source files of the modules the audited line names, as dotted module paths.

    A command line entry is declared in ``pyproject.toml`` and refused at the module it names, so an
    audit anchored at that line is answered by the issue at the module.
    """
    if text is None or line is None or not 1 <= line <= len(text.splitlines()):
        return frozenset()
    spelled = text.splitlines()[line - 1]
    return frozenset(
        f"{p.src_root}/{dotted.replace('.', '/')}.py"
        for dotted in re.findall(r"[A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)+", spelled)
    )


def replay(run: ReplayRun) -> Sequence[ModelValidationIssue]:
    source = run.source
    if run.contract is None or not in_scope(run.contract, source.path):
        return ()
    rules = load_rule_set(run.contract.subcontract)
    p = rules.parameters
    files = source.names()
    contract_paths = [
        name
        for name in (source.fact_names(ROLE_NODE_CONTRACTS) or files)
        if PurePosixPath(name).name == p.contract_file_name
    ]
    base_revision = source.fact_revision(ROLE_BASE_REVISION)
    facts = _facts(
        p,
        source.path,
        files,
        contract_paths,
        source.text,
        None if base_revision is None else _revision_reader(base_revision),
    )
    named = _named_modules(source.text(source.path), source.line, p)
    return [
        issue
        for issue in _issues_of_rule(facts, rules, run.rule_id)
        if issue.file_path == Path(source.path) or str(issue.file_path) in named
    ]


def _issues_of_rule(
    facts: ModelCanonicalFileShapeFacts,
    rules: ModelCanonicalFileShapeRuleSet,
    asserted: str,
) -> list[ModelValidationIssue]:
    """The issues of the asserted rule judged alone.

    The checker refuses a path under the first file rule that matches it, so a handler file that is
    also a command line entry reports only the handler rule. An assertion names one rule, and the
    question is whether that rule reports the input, so that rule is run on its own; a rule id the
    contract does not enable (or an assertion naming the checker) runs the checker as it is.
    """
    name = asserted.rsplit(":", 1)[-1]
    if name not in rules.enabled:
        return check(facts, rules)
    return check(facts, rules.model_copy(update={"enabled": frozenset({name})}))


def replay_fixture(
    contract: ReplayContract, fixture: Path
) -> Sequence[ModelValidationIssue]:
    """One violation fixture: the checker's typed facts as JSON."""
    facts = ModelCanonicalFileShapeFacts.model_validate_json(
        fixture.read_text(encoding="utf-8")
    )
    return check(facts, load_rule_set(contract.subcontract))
