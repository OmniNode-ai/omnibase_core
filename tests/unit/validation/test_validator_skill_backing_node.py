# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for validator_skill_backing_node (OMN-10171, SEAM-2).

Tests cover the three assertion surfaces:
- extract_backing_node: all SKILL.md patterns accepted
- check_node_liveness: directory/contract/handler checks
- scan: full scan with allowlist and omnimarket-absent skip
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.validator_skill_backing_node import (
    SkillBackingNodeViolation,
    check_node_liveness,
    extract_backing_node,
    load_allowlist,
    scan,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_live_node(base: Path, node_name: str) -> Path:
    """Create a minimal live node directory under *base*."""
    node_dir = base / node_name
    (node_dir / "handlers").mkdir(parents=True, exist_ok=True)
    _write(node_dir / "contract.yaml", "node_id: " + node_name + "\n")
    handler = node_dir / "handlers" / "handler_main.py"
    lines = "\n".join(f"line_{i} = {i}" for i in range(15))
    _write(handler, lines + "\n")
    return node_dir


def _make_skill(omniclaude_root: Path, skill_name: str, content: str) -> None:
    skill_dir = omniclaude_root / "plugins" / "onex" / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    _write(skill_dir / "SKILL.md", content)


# ---------------------------------------------------------------------------
# extract_backing_node
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractBackingNode:
    def test_canonical_body_form(self, tmp_path: Path) -> None:
        p = tmp_path / "SKILL.md"
        _write(
            p,
            "**Backing node**: `omnimarket/src/omnimarket/nodes/node_foo/`\n",
        )
        assert extract_backing_node(p) == "node_foo"

    def test_short_body_form(self, tmp_path: Path) -> None:
        p = tmp_path / "SKILL.md"
        _write(p, "- **Backing node**: `node_bar`\n")
        assert extract_backing_node(p) == "node_bar"

    def test_yaml_frontmatter_form(self, tmp_path: Path) -> None:
        p = tmp_path / "SKILL.md"
        _write(p, "---\nbacking_node: node_baz\n---\n")
        assert extract_backing_node(p) == "node_baz"

    def test_inline_heading_form(self, tmp_path: Path) -> None:
        p = tmp_path / "SKILL.md"
        _write(
            p,
            "**Skill ID**: foo · Backing node**: `omnimarket/src/omnimarket/nodes/node_qux/` · rest\n",
        )
        assert extract_backing_node(p) == "node_qux"

    def test_no_declaration_returns_none(self, tmp_path: Path) -> None:
        p = tmp_path / "SKILL.md"
        _write(p, "# Pure instruction skill\nNo node here.\n")
        assert extract_backing_node(p) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert extract_backing_node(tmp_path / "nonexistent.md") is None


# ---------------------------------------------------------------------------
# load_allowlist
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadAllowlist:
    def test_valid_allowlist(self, tmp_path: Path) -> None:
        allowlist_path = (
            tmp_path
            / "plugins"
            / "onex"
            / "skills"
            / "_lib"
            / "skill_backing_node_allowlist.yaml"
        )
        allowlist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"allowlist": [{"skill": "skill_foo", "reason": "pending node rewrite"}]}
        _write(allowlist_path, yaml.dump(data))
        result = load_allowlist(tmp_path)
        assert result == {"skill_foo": "pending node rewrite"}

    def test_missing_allowlist_returns_empty(self, tmp_path: Path) -> None:
        assert load_allowlist(tmp_path) == {}

    def test_blank_reason_raises(self, tmp_path: Path) -> None:
        allowlist_path = (
            tmp_path
            / "plugins"
            / "onex"
            / "skills"
            / "_lib"
            / "skill_backing_node_allowlist.yaml"
        )
        allowlist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"allowlist": [{"skill": "skill_foo", "reason": ""}]}
        _write(allowlist_path, yaml.dump(data))
        with pytest.raises(ValueError, match="non-empty 'reason'"):
            load_allowlist(tmp_path)

    def test_missing_skill_field_raises(self, tmp_path: Path) -> None:
        allowlist_path = (
            tmp_path
            / "plugins"
            / "onex"
            / "skills"
            / "_lib"
            / "skill_backing_node_allowlist.yaml"
        )
        allowlist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"allowlist": [{"reason": "something"}]}
        _write(allowlist_path, yaml.dump(data))
        with pytest.raises(ValueError, match="non-empty 'skill'"):
            load_allowlist(tmp_path)


# ---------------------------------------------------------------------------
# check_node_liveness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckNodeLiveness:
    def _make_omnimarket_root(self, tmp_path: Path) -> Path:
        """Create an omnimarket nodes root sibling to a fake omniclaude root."""
        omniclaude_root = tmp_path / "omniclaude"
        omniclaude_root.mkdir()
        omnimarket_nodes = tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes"
        omnimarket_nodes.mkdir(parents=True)
        return omniclaude_root

    def test_live_node_passes(self, tmp_path: Path) -> None:
        omniclaude_root = self._make_omnimarket_root(tmp_path)
        nodes_root = tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes"
        _make_live_node(nodes_root, "node_live")
        result = check_node_liveness("skill_x", "node_live", omniclaude_root)
        assert result is None

    def test_missing_node_directory(self, tmp_path: Path) -> None:
        omniclaude_root = self._make_omnimarket_root(tmp_path)
        result = check_node_liveness("skill_x", "node_missing", omniclaude_root)
        assert isinstance(result, SkillBackingNodeViolation)
        assert "not found" in result.detail

    def test_missing_contract_yaml(self, tmp_path: Path) -> None:
        omniclaude_root = self._make_omnimarket_root(tmp_path)
        nodes_root = tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes"
        node_dir = nodes_root / "node_nocontract"
        (node_dir / "handlers").mkdir(parents=True)
        result = check_node_liveness("skill_x", "node_nocontract", omniclaude_root)
        assert isinstance(result, SkillBackingNodeViolation)
        assert "contract.yaml missing" in result.detail

    def test_missing_handlers_dir(self, tmp_path: Path) -> None:
        omniclaude_root = self._make_omnimarket_root(tmp_path)
        nodes_root = tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes"
        node_dir = nodes_root / "node_nohandlers"
        node_dir.mkdir(parents=True)
        _write(node_dir / "contract.yaml", "node_id: node_nohandlers\n")
        result = check_node_liveness("skill_x", "node_nohandlers", omniclaude_root)
        assert isinstance(result, SkillBackingNodeViolation)
        assert "handlers/ directory missing" in result.detail

    def test_stub_handler_fails(self, tmp_path: Path) -> None:
        omniclaude_root = self._make_omnimarket_root(tmp_path)
        nodes_root = tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes"
        node_dir = nodes_root / "node_stub"
        (node_dir / "handlers").mkdir(parents=True)
        _write(node_dir / "contract.yaml", "node_id: node_stub\n")
        _write(node_dir / "handlers" / "handler_stub.py", "pass\n")
        result = check_node_liveness("skill_x", "node_stub", omniclaude_root)
        assert isinstance(result, SkillBackingNodeViolation)
        assert "stubs" in result.detail


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScan:
    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        """Return (omniclaude_root, omnimarket_nodes_root)."""
        omniclaude_root = tmp_path / "omniclaude"
        omniclaude_root.mkdir()
        nodes_root = tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes"
        nodes_root.mkdir(parents=True)
        return omniclaude_root, nodes_root

    def test_clean_scan(self, tmp_path: Path) -> None:
        omniclaude_root, nodes_root = self._setup(tmp_path)
        _make_live_node(nodes_root, "node_good")
        _make_skill(omniclaude_root, "skill_good", "**Backing node**: `node_good`\n")
        errors = scan(omniclaude_root)
        assert errors == []

    def test_violation_reported(self, tmp_path: Path) -> None:
        omniclaude_root, _ = self._setup(tmp_path)
        _make_skill(omniclaude_root, "skill_bad", "**Backing node**: `node_phantom`\n")
        errors = scan(omniclaude_root)
        assert len(errors) == 1
        assert "node_phantom" in errors[0]

    def test_allowlisted_skill_skipped(self, tmp_path: Path) -> None:
        omniclaude_root, _ = self._setup(tmp_path)
        _make_skill(
            omniclaude_root, "skill_exempt", "**Backing node**: `node_phantom`\n"
        )
        allowlist_path = (
            omniclaude_root
            / "plugins"
            / "onex"
            / "skills"
            / "_lib"
            / "skill_backing_node_allowlist.yaml"
        )
        allowlist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "allowlist": [
                {"skill": "skill_exempt", "reason": "node being rebuilt in OMN-XXXX"}
            ]
        }
        _write(allowlist_path, yaml.dump(data))
        errors = scan(omniclaude_root)
        assert errors == []

    def test_skill_without_backing_node_skipped(self, tmp_path: Path) -> None:
        omniclaude_root, _ = self._setup(tmp_path)
        _make_skill(omniclaude_root, "skill_pure", "# Pure instruction skill\n")
        errors = scan(omniclaude_root)
        assert errors == []

    def test_missing_skills_dir_returns_error(self, tmp_path: Path) -> None:
        omniclaude_root = tmp_path / "omniclaude"
        omniclaude_root.mkdir()
        (tmp_path / "omnimarket" / "src" / "omnimarket" / "nodes").mkdir(parents=True)
        errors = scan(omniclaude_root)
        assert any("skills directory not found" in e for e in errors)
