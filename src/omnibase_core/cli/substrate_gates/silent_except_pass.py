# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate 4 — banned silent except: pass / except Exception: pass patterns."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from omnibase_core.cli.substrate_gates._base import (
    BaseGateCheck,
    has_allow_annotation,
    main_for_gate,
)
from omnibase_core.cli.substrate_gates.gate_violation import GateViolation


class SilentExceptPassGate(BaseGateCheck):
    """Detect ExceptHandler nodes whose body is solely [Pass].

    Banned forms (any type annotation, including bare except):
      except:           pass
      except Exception: pass
      except (A, B):    pass

    Allowed:
      - body has any statement other than a lone Pass
      - the ``except`` line carries ``# substrate-allow: <reason>``
    """

    def check_tree(
        self,
        tree: ast.Module,
        source_lines: list[str],
        path: Path,
    ) -> list[GateViolation]:
        violations: list[GateViolation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if len(node.body) != 1 or not isinstance(node.body[0], ast.Pass):
                continue
            if has_allow_annotation(source_lines, node.lineno):
                continue
            violations.append(
                GateViolation(
                    path=path,
                    line=node.lineno,
                    message=(
                        "silent except-pass: bare 'except: pass' swallows all errors; "
                        "handle the exception or add '# substrate-allow: <reason>'"
                    ),
                )
            )
        return violations


def main(argv: list[str] | None = None) -> int:
    return main_for_gate(SilentExceptPassGate(), argv)


if __name__ == "__main__":
    sys.exit(main())
