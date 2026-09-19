# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for scripts/insert_hook_block.py.

OMN-18033: the propagator used to append the rendered hook block at end of
file. Every declared target indents its repos: entries by two spaces, and ten
of the twelve keep top-level keys (ci:, fail_fast:, default_stages:) below
repos:, so the appended block landed outside the list and the resulting
.pre-commit-config.yaml did not parse. Nothing tested the mutation, which is
why that shipped — these tests cover it.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "insert_hook_block.py"

_spec = importlib.util.spec_from_file_location("insert_hook_block", HELPER)
assert _spec and _spec.loader
insert_hook_block = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(insert_hook_block)

HOOK = {
    "id": "validate-gitignore-baseline",
    "name": "Gitignore Baseline Validator",
    "entry": "python -m omnibase_core.validators.gitignore_baseline",
    "language": "python",
    "pass_filenames": False,
}

# The shape every real target has: two-space list indentation, and top-level
# keys after repos:.
TARGET = textwrap.dedent(
    """
    ---
    repos:
      - repo: local
        hooks:
          - id: existing
            name: existing
            entry: "true"
            language: system

    # OMN-14669: every stage a hook uses must be installed.
    default_install_hook_types: [pre-commit, pre-push, commit-msg]
    fail_fast: false
    """
).lstrip()


def _hook_ids(text: str) -> list[str]:
    parsed = yaml.safe_load(text)
    return [h["id"] for repo in parsed["repos"] for h in repo["hooks"]]


@pytest.mark.unit
def test_end_of_file_append_is_what_this_replaces() -> None:
    """Control: the old behaviour really does produce an unparseable config."""
    block = insert_hook_block.render_block(HOOK, None)
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(TARGET + "\n" + block + "\n")


@pytest.mark.unit
def test_insertion_keeps_the_config_parseable() -> None:
    updated = insert_hook_block.insert(
        TARGET, insert_hook_block.render_block(HOOK, None)
    )
    assert _hook_ids(updated) == ["existing", "validate-gitignore-baseline"]


@pytest.mark.unit
def test_insertion_preserves_trailing_top_level_keys() -> None:
    updated = yaml.safe_load(
        insert_hook_block.insert(TARGET, insert_hook_block.render_block(HOOK, None))
    )
    assert updated["fail_fast"] is False
    assert updated["default_install_hook_types"] == [
        "pre-commit",
        "pre-push",
        "commit-msg",
    ]


@pytest.mark.unit
def test_insertion_matches_the_targets_own_indentation() -> None:
    updated = insert_hook_block.insert(
        TARGET, insert_hook_block.render_block(HOOK, None)
    )
    starts = [
        line for line in updated.split("\n") if line.lstrip().startswith("- repo:")
    ]
    assert starts and all(line.startswith("  - repo:") for line in starts), starts


@pytest.mark.unit
def test_insertion_goes_above_the_comment_introducing_the_next_key() -> None:
    updated = insert_hook_block.insert(
        TARGET, insert_hook_block.render_block(HOOK, None)
    ).split("\n")
    comment = next(
        i for i, line in enumerate(updated) if line.startswith("# OMN-14669")
    )
    hook = next(
        i for i, line in enumerate(updated) if "validate-gitignore-baseline" in line
    )
    assert hook < comment


@pytest.mark.unit
def test_pin_lands_in_additional_dependencies() -> None:
    pin = (
        "omnibase-core @ git+https://github.com/OmniNode-ai/omnibase_core.git@"
        + "a" * 40
    )
    block = yaml.safe_load(insert_hook_block.render_block(HOOK, pin))
    assert block[0]["hooks"][0]["additional_dependencies"] == [pin]


@pytest.mark.unit
def test_pin_is_not_duplicated() -> None:
    pin = "omnibase-core @ git+https://example.invalid/r.git@" + "b" * 40
    hook = {**HOOK, "additional_dependencies": [pin]}
    block = yaml.safe_load(insert_hook_block.render_block(hook, pin))
    assert block[0]["hooks"][0]["additional_dependencies"] == [pin]


@pytest.mark.unit
def test_no_pin_leaves_the_hook_exactly_as_declared() -> None:
    block = yaml.safe_load(insert_hook_block.render_block(HOOK, None))
    assert block[0]["hooks"][0] == HOOK


@pytest.mark.unit
def test_config_without_repos_key_is_refused(tmp_path: Path) -> None:
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text("fail_fast: false\n")
    before = cfg.read_text()
    result = subprocess.run(
        [sys.executable, str(HELPER), str(cfg), "--hook-json", json.dumps(HOOK)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3, result.stderr
    assert cfg.read_text() == before, "refused run must not modify the target"


@pytest.mark.unit
def test_cli_writes_a_parseable_config(tmp_path: Path) -> None:
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text(TARGET)
    result = subprocess.run(
        [sys.executable, str(HELPER), str(cfg), "--hook-json", json.dumps(HOOK)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert _hook_ids(cfg.read_text()) == ["existing", "validate-gitignore-baseline"]


@pytest.mark.unit
def test_print_block_does_not_touch_the_target(tmp_path: Path) -> None:
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text(TARGET)
    result = subprocess.run(
        [
            sys.executable,
            str(HELPER),
            str(cfg),
            "--print-block",
            "--hook-json",
            json.dumps(HOOK),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert cfg.read_text() == TARGET
    assert _hook_ids("repos:\n" + result.stdout) == ["validate-gitignore-baseline"]


@pytest.mark.unit
def test_rendered_sequences_are_indented_under_their_key() -> None:
    """yaml.safe_dump's indentless sequence fails omninode_infra's yamllint.

    Every .pre-commit-config.yaml in the fleet indents the sequence under
    `hooks:`; the indentless form is valid yaml but a lint failure there
    ("wrong indentation: expected 8 but found 6"), which turns the bot's own
    PR red in the repo it is trying to help.
    """
    block = insert_hook_block.render_block(HOOK, None).split("\n")
    hooks_at = next(i for i, line in enumerate(block) if line.strip() == "hooks:")
    hooks_indent = len(block[hooks_at]) - len(block[hooks_at].lstrip())
    item = block[hooks_at + 1]
    item_indent = len(item) - len(item.lstrip())
    assert item.lstrip().startswith("- id:"), item
    assert item_indent > hooks_indent, f"sequence not indented: {item!r}"


@pytest.mark.unit
def test_indented_block_still_parses_to_the_declared_hook() -> None:
    parsed = yaml.safe_load(insert_hook_block.render_block(HOOK, None))
    assert parsed[0]["hooks"][0] == HOOK


@pytest.mark.unit
def test_multiline_values_render_as_literal_block_scalars() -> None:
    """yamlfmt re-folds a quoted multi-line scalar and injects its own marker.

    onex_change_control's contamination gate (OMN-15479) refuses a committed
    value containing `#magic___^_^___line`, which is exactly what the target's
    formatter produced from the hook's folded description. A literal block
    scalar is not re-folded.
    """
    # The shape the real hook has: a folded description ending in a blank line.
    hook = {**HOOK, "description": "line one\nline two\n\n"}
    rendered = insert_hook_block.render_block(hook, None)
    description_line = next(
        line for line in rendered.split("\n") if line.strip().startswith("description:")
    )
    assert description_line.rstrip().endswith(("|", "|-", "|+")), description_line
    assert yaml.safe_load(rendered)[0]["hooks"][0]["description"] == hook["description"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "description",
    ["one\ntwo\n", "one\ntwo", "two\n\n", "single line", "trailing space \nx"],
)
def test_render_round_trips_every_description_shape(description: str) -> None:
    """PyYAML does not round-trip every string through a literal block scalar.

    A value ending in exactly one newline emits `|` and parses back without it,
    so render_block verifies its own output and falls back rather than
    propagating a block whose content differs from the declared hook.
    """
    hook = {**HOOK, "description": description}
    parsed = yaml.safe_load(insert_hook_block.render_block(hook, None))
    assert parsed[0]["hooks"][0] == hook


@pytest.mark.unit
def test_single_line_values_stay_plain() -> None:
    rendered = insert_hook_block.render_block(HOOK, None)
    name_line = next(
        line for line in rendered.split("\n") if line.strip().startswith("name:")
    )
    assert "|" not in name_line, name_line
