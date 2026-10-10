#!/usr/bin/env python3
"""Generate ONEX node scaffolding.

Creates a complete node package with contract, handler, metadata, tests,
and __init__.py files following the omnimarket node conventions.

Usage:
    python scripts/generate_node.py --name my_feature --type compute
    python scripts/generate_node.py --name data_sync --type effect
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

VALID_NODE_TYPES = ("compute", "effect", "reducer", "orchestrator")

NODES_DIR = Path(__file__).resolve().parent.parent / "src" / "omnimarket" / "nodes"
TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"


def _snake_to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def _snake_to_kebab(name: str) -> str:
    """Convert snake_case to kebab-case."""
    return name.replace("_", "-")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def _contract_yaml(name: str, node_type: str) -> str:
    kebab = _snake_to_kebab(name)
    pascal = _snake_to_pascal(name)
    purity = "pure" if node_type in ("compute", "reducer") else "impure"
    return f"""\
---
name: {name}
contract_version: {{major: 1, minor: 0, patch: 0}}
node_type: {node_type}
node_version: {{major: 1, minor: 0, patch: 0}}

description: >
  {pascal} node. TODO: add description.

handler_routing:
  default_handler: handler:Node{pascal}

descriptor:
  node_archetype: {node_type}
  purity: {purity}
  idempotent: true
  timeout_ms: 60000

event_bus:
  subscribe_topics:
    - onex.cmd.market.{kebab}-requested.v1
  publish_topics:
    - onex.evt.market.{kebab}-completed.v1
"""


def _metadata_yaml(name: str, node_type: str) -> str:
    pascal = _snake_to_pascal(name)
    side_effect = "read_only" if node_type in ("compute", "reducer") else "write"
    return f"""\
name: node_{name}
version: "1.0.0"
description: "{pascal} node — TODO: add description"
omnibase_core_compat: ">=0.39.0,<1.0.0"
entry_points:
  onex.nodes:
    node_{name}: "omnimarket.nodes.node_{name}"
capabilities:
  standalone: true
  full_runtime: true
  requires_network: false
  requires_repo: false
  requires_secrets: false
  requires_docker: false
  side_effect_class: {side_effect}
dependencies:
  - "omnibase_core>=0.39.0"
authors: ["OmniNode Platform Team"]
license: "MIT"
tags: ["{name}", "{node_type}"]
"""


def _handler_py(name: str, node_type: str) -> str:
    pascal = _snake_to_pascal(name)
    return f'''\
"""Node{pascal} — {pascal} handler.

ONEX node type: {node_type.upper()}
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class {pascal}Request:
    """Input for the {name} handler."""

    pass


@dataclass
class {pascal}Result:
    """Output of the {name} handler."""

    success: bool = False
    message: str = ""


class Node{pascal}:
    """Handler for {name} node."""

    def handle(self, request: {pascal}Request) -> {pascal}Result:
        """Process the request and return a result."""
        return {pascal}Result(success=True, message="ok")
'''


def _handler_init_py() -> str:
    return ""


def _node_init_py(name: str) -> str:
    pascal = _snake_to_pascal(name)
    return f'''\
"""node_{name} — {pascal} node."""

from omnimarket.nodes.node_{name}.handlers.handler_{name} import (
    Node{pascal},
)

__all__ = ["Node{pascal}"]
'''


def _tests_init_py() -> str:
    return ""


def _golden_chain_test(name: str) -> str:
    pascal = _snake_to_pascal(name)
    kebab = _snake_to_kebab(name)
    return f'''\
"""Golden chain test for node_{name}.

Verifies the {name} node end-to-end via event bus wiring.
"""

from __future__ import annotations

import json

import pytest
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory

from omnimarket.nodes.node_{name} import Node{pascal}

CMD_TOPIC = "onex.cmd.market.{kebab}-requested.v1"
EVT_TOPIC = "onex.evt.market.{kebab}-completed.v1"


@pytest.mark.unit
class Test{pascal}GoldenChain:
    """Golden chain: command -> handle -> completion event."""

    async def test_handle_returns_success(
        self, event_bus: EventBusInmemory
    ) -> None:
        """Basic handler invocation should succeed."""
        handler = Node{pascal}()
        result = handler.handle(None)

        assert result is not None

    async def test_event_bus_wiring(self, event_bus: EventBusInmemory) -> None:
        """Node can be wired to event bus for command/completion flow."""
        completions: list[bytes] = []

        async def on_command(message: object) -> None:
            payload = json.dumps({{"run": True}}).encode()
            completions.append(payload)
            await event_bus.publish(EVT_TOPIC, key=None, value=payload)

        await event_bus.start()
        await event_bus.subscribe(
            CMD_TOPIC, on_message=on_command, group_id="test-{kebab}"
        )

        await event_bus.publish(CMD_TOPIC, key=None, value=b'{{"run": true}}')

        assert len(completions) == 1

        history = await event_bus.get_event_history(topic=EVT_TOPIC)
        assert len(history) == 1

        await event_bus.close()
'''


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------


def generate_node(name: str, node_type: str) -> list[Path]:
    """Generate all files for a new node. Returns list of created paths."""
    node_dir = NODES_DIR / f"node_{name}"
    handlers_dir = node_dir / "handlers"
    tests_dir = node_dir / "tests"

    if node_dir.exists():
        print(f"Error: {node_dir} already exists", file=sys.stderr)
        sys.exit(1)

    files: list[tuple[Path, str]] = [
        (node_dir / "contract.yaml", _contract_yaml(name, node_type)),
        (node_dir / "metadata.yaml", _metadata_yaml(name, node_type)),
        (node_dir / "__init__.py", _node_init_py(name)),
        (handlers_dir / "__init__.py", _handler_init_py()),
        (handlers_dir / f"handler_{name}.py", _handler_py(name, node_type)),
        (tests_dir / "__init__.py", _tests_init_py()),
        (TESTS_DIR / f"test_golden_chain_{name}.py", _golden_chain_test(name)),
    ]

    created: list[Path] = []
    for path, content in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        created.append(path)
        print(f"  created: {path}")

    return created


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ONEX node scaffolding",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Node name in snake_case (e.g. my_feature)",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=VALID_NODE_TYPES,
        dest="node_type",
        help="Node type",
    )
    args = parser.parse_args()

    name = args.name.strip().lower()
    if not name.isidentifier():
        print(f"Error: '{name}' is not a valid Python identifier", file=sys.stderr)
        sys.exit(1)

    print(f"Generating node_{name} ({args.node_type})...")
    created = generate_node(name, args.node_type)
    print(f"\nGenerated {len(created)} files. Next steps:")
    print(
        f"  1. Edit handler: src/omnimarket/nodes/node_{name}/handlers/handler_{name}.py"
    )
    print("  2. Add entry point to pyproject.toml:")
    print(f'     node_{name} = "omnimarket.nodes.node_{name}"')
    print(f"  3. Run tests: uv run pytest tests/test_golden_chain_{name}.py -v")


if __name__ == "__main__":
    main()
