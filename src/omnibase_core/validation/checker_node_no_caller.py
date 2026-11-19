# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure checker for ``node_no_caller`` (OMN-24538, fail-open ratchets, class iv: built and never called).

A node nothing calls is finished work nobody can reach: no file outside its own directory names it, no
other node publishes a topic it subscribes to, and nothing outside the node graph feeds it. The rule
mirrors the ``node_no_caller`` defect class of omnimarket's seam graph defects node, so the two read the
same fact. Facts in (one contract's path and source, plus a callable that returns the repository index:
the topics each node directory publishes and the files that name each node), ``ModelValidationIssue``
out. The name keys, the topic keys, the pattern of externally fed topics, the catalog threshold, the
annotation marker and the reason and remediation texts are ``parameters`` of the ``node_no_caller`` rule
row of ``contracts/node_no_caller.validation.yaml``; an enabled row with a missing or mistyped parameter
raises, so a broken contract fails to load instead of passing every file. A contract that does not parse
is a finding, never clean. No file read, no clock, no environment.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path

import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_detector_common import (
    detector_issue,
    is_annotated,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

RULE_NODE_NO_CALLER = "node_no_caller"


# A node's seams as read from its contract: (name, subscribed topics, published topics).
# The repository index is (publishers: topic -> node directories, named_in: node name -> files naming it).


def read_node_facts(
    path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
) -> tuple[str, tuple[str, ...], tuple[str, ...]] | None:
    """The node's name and topics from one contract; ``None`` when the text is not a YAML mapping.

    The name is the first of the ``name_keys`` present, else the contract's directory name; callers may use
    either, so the checker looks for both.
    """
    row = rules.get(RULE_NODE_NO_CALLER)
    if row is None or not row.enabled:
        return None
    name_keys = rule_strings(row, "name_keys")
    events_key = rule_string(row, "events_key")
    subscribe_key = rule_string(row, "subscribe_key")
    publish_key = rule_string(row, "publish_key")
    try:
        loaded = load_yaml_mapping_no_duplicates(source, source=RULE_NODE_NO_CALLER)
    except (yaml.YAMLError, ValueError):
        return None
    name = next(
        (v for k in name_keys if isinstance(v := loaded.get(k), str) and v),
        path.parent.name,
    )
    events = loaded.get(events_key)
    topics = events if isinstance(events, Mapping) else {}
    return (
        name,
        _strings(topics.get(subscribe_key)),
        _strings(topics.get(publish_key)),
    )


def _strings(value: object) -> tuple[str, ...]:
    return (
        tuple(v for v in value if isinstance(v, str)) if isinstance(value, list) else ()
    )


def _first_line(lines: list[str], name_keys: tuple[str, ...]) -> int:
    pattern = re.compile("^(?:" + "|".join(re.escape(k) for k in name_keys) + "):")
    return next((n for n, line in enumerate(lines, 1) if pattern.match(line)), 1)


def check_node_no_caller(
    path: Path,
    source: str,
    index: Callable[
        [], tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str]]]
    ],
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Issues for one contract under the ``node_no_caller`` row (at most one, on the name line).

    ``index`` builds the repository index and is called only when the contract parses, so a probe over
    empty source never scans the tree.
    """
    row = rules.get(RULE_NODE_NO_CALLER)
    if row is None or not row.enabled:
        return ()
    name_keys = rule_strings(row, "name_keys")
    external = re.compile(rule_string(row, "external_feed_pattern"))
    marker = rule_string(row, "comment_prefix") + rule_string(row, "annotation_marker")
    reason = rule_string(row, "reason")
    remediation = rule_string(row, "remediation")
    # the validator reads these four to scan the tree; a missing one fails here, at load, not later
    rule_string(row, "contract_file")
    rule_strings(row, "scanned_extensions")
    rule_strings(row, "excluded_dir_names")
    rule_int(row, "catalog_file_node_threshold")
    rule_strings(row, "name_token_patterns")
    rule_string(row, "name_token_strip")
    lines = source.splitlines()
    lineno = _first_line(lines, name_keys)
    if is_annotated(lines, lineno, marker):
        return ()
    facts = read_node_facts(path, source, rules)
    if facts is None:
        return (
            detector_issue(
                row,
                path,
                lines,
                lineno,
                f"{reason} (the contract does not parse as a YAML mapping)",
                remediation,
            ),
        )
    name, subscribes, _published = facts
    publishers, named_in = index()
    own = path.parent.as_posix()
    outside = [
        f
        for candidate in {name, path.parent.name}
        for f in named_in.get(candidate, frozenset())
        if f != own and not f.startswith(own + "/")
    ]
    published_by_another = any(
        d != own for topic in subscribes for d in publishers.get(topic, ())
    )
    fed_from_outside = any(external.search(topic) for topic in subscribes)
    if outside or published_by_another or fed_from_outside:
        return ()
    return (
        detector_issue(
            row,
            path,
            lines,
            lineno,
            f"{reason} ({name}: no file outside its directory names it (by contract name or directory name) and no other node publishes a "
            f"topic it subscribes to)",
            remediation,
        ),
    )


__all__ = ["RULE_NODE_NO_CALLER", "check_node_no_caller", "read_node_facts"]
