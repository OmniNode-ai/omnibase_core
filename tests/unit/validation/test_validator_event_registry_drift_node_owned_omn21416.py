# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21416: two rules omnimarket's own drift gate has that the core check must share.

Route 1 (owner ruling 2026-11-04) moves omnimarket's event-registry drift gate onto this check
over omniclaude's exported event_registrations document. Measured that day, the check leaves 17
drift lines that omnimarket's current gate does not report; all of them come from these two rules.

Failure modes, one case or more each:
  (1) an emit-registry event marked node_owned: true (emitted by an omnimarket node, never a
      hook, OMN-21112) is reported as registry-only drift
  (2) node_owned that is not the literal boolean true (false, or the string "true") stops the
      event being compared
  (3) a node_owned registry event that a source does declare is silently accepted
  (4) a side-channel document entry declaring topics: [] is refused, though the registry event it
      matches has fan_out: [] too
  (5) an empty-topics entry is accepted against a registry event that does fan out
  (6) an entry with no topics key at all is accepted as if it declared none
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_event_registry_drift import (
    ValidatorEventDeclarationDrift,
)

pytestmark = pytest.mark.unit

_TOPIC = "onex.evt.omniclaude.prompt-submitted.v1"
_NODE_TOPIC = "onex.evt.omnimarket.context-compaction-installed.v1"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _document(*entries: str) -> str:
    return "event_registrations:\n" + "".join(entries)


def _entry(event_type: str, topics: str, *, key: str = "session_id") -> str:
    return (
        f"  - event_type: {event_type}\n"
        f"{topics}"
        f"    partition_key_field: {key}\n"
        "    required_fields: [session_id]\n"
    )


_PROMPT = _entry("prompt.submitted", f"    topics: [{_TOPIC}]\n")


def _registry(*events: str) -> str:
    return "events:\n" + "".join(events)


_PROMPT_EVENT = (
    "  prompt.submitted:\n"
    "    partition_key_field: session_id\n"
    "    required_fields: [session_id]\n"
    "    fan_out:\n"
    f"      - topic: {_TOPIC}\n"
)


def _node_event(node_owned: str) -> str:
    return (
        "  compaction.installed:\n"
        f"    node_owned: {node_owned}\n"
        "    partition_key_field: session_id\n"
        "    required_fields: [session_id]\n"
        "    fan_out:\n"
        f"      - topic: {_NODE_TOPIC}\n"
    )


_SIDE_CHANNEL_EVENT = (
    "  skill.friction_recorded:\n"
    "    fan_out: []\n"
    "    partition_key_field: session_id\n"
    "    required_fields: [session_id]\n"
)


def _run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], document: str, registry: str
) -> tuple[int, list[str]]:
    doc = _write(tmp_path / "event_registrations.yaml", document)
    reg = _write(tmp_path / "topics.yaml", registry)
    capsys.readouterr()
    exit_code = ValidatorEventDeclarationDrift.main(
        ["--source-document", str(doc), "--registry-topics-yaml", str(reg)]
    )
    rules = sorted(
        ln.split("[", 1)[1].split("]", 1)[0]
        for ln in capsys.readouterr().out.splitlines()
        if ln.startswith("ERROR")
    )
    return exit_code, rules


def test_node_owned_registry_event_is_not_registry_only_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, rules = _run(
        tmp_path,
        capsys,
        _document(_PROMPT),
        _registry(_PROMPT_EVENT, _node_event("true")),
    )
    assert (code, rules) == (0, [])


@pytest.mark.parametrize("value", ["false", '"true"'])
def test_node_owned_other_than_literal_true_still_compares(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str
) -> None:
    code, rules = _run(
        tmp_path,
        capsys,
        _document(_PROMPT),
        _registry(_PROMPT_EVENT, _node_event(value)),
    )
    assert code == 1
    assert "event_registry_only" in rules


def test_node_owned_registry_event_a_source_declares_is_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    declared = _entry("compaction.installed", f"    topics: [{_NODE_TOPIC}]\n")
    code, rules = _run(
        tmp_path,
        capsys,
        _document(_PROMPT, declared),
        _registry(_PROMPT_EVENT, _node_event("true")),
    )
    assert code == 1
    assert "event_source_only" in rules


def test_side_channel_entry_with_empty_topics_matches_empty_fan_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    side = _entry("skill.friction_recorded", "    topics: []\n")
    code, rules = _run(
        tmp_path,
        capsys,
        _document(_PROMPT, side),
        _registry(_PROMPT_EVENT, _SIDE_CHANNEL_EVENT),
    )
    assert (code, rules) == (0, [])


def test_side_channel_entry_against_a_fanning_out_event_is_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    side = _entry("prompt.submitted", "    topics: []\n")
    code, rules = _run(tmp_path, capsys, _document(side), _registry(_PROMPT_EVENT))
    assert code == 1
    assert set(rules) & {"topic_registry_only", "topics_mismatch"}


def test_side_channel_entry_without_a_topics_key_is_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = _entry("skill.friction_recorded", "")
    code, rules = _run(
        tmp_path,
        capsys,
        _document(_PROMPT, missing),
        _registry(_PROMPT_EVENT, _SIDE_CHANNEL_EVENT),
    )
    assert code == 1
    assert rules == ["source_unreadable"]
