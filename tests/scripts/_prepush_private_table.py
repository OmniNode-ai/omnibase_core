# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A synthetic deployment host table for the pre-push tests (OMN-20939).

The shipped ``scripts/hooks/prepush_hosts.tsv`` carries only a neutral disabled
row; a deployment's real hosts live in its own private table. These tests need
rows to exercise the picker and the identity guard, so they build a table of the
same thirteen-column shape from invented hosts (RFC 5737 documentation
addresses, ``.invalid`` names) and point the workspace-config resolver at it.
The labels keep the names the picker's override maps use; no value here belongs
to any real machine.
"""

from __future__ import annotations

from pathlib import Path

PRIVATE_TABLE_REL = "config/lab/prepush_hosts.omnibase_core.tsv"

_HEADER = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
)

#: label -> hostname, the names the tests refer to.
HOST_A = "gate-host-a"
HOST_B = "gate-host-b"
HOST_B_CONTAINER = "gate-runner-b"
HOST_C = "gate-host-c"
HOST_D = "gate-host-d"
HOST_E = "gate-host-e"

SYNTHETIC_ROWS = (
    f"h200\tcapacity\t{HOST_A}\t{HOST_A}.example.invalid\t24\t/opt/onex/bin/uv\t0.11.0"
    "\t/srv/onex-prepush\tlockdir\t1\t-\tauthorizing\tlocal/default identity host\n"
    f"h201\tcapacity\t{HOST_B}\t192.0.2.21\t32\t/opt/onex/bin/uv\t0.11.0"
    "\t/srv/onex-prepush\tqueue\t1\t-\tauthorizing\tqueue-serialized host\n"
    f"h201c\tidentity\t{HOST_B_CONTAINER}\t-\t32\t-\t-\t-\tnone\t1\t-\tauthorizing"
    "\tcontainer identity of the queue-serialized host\n"
    f"h101\tcapacity\t{HOST_C}\t192.0.2.31\t12\t/opt/onex/bin/uv\t0.12.7"
    "\t/srv/onex-prepush\tlockdir\t2\t-\tauthorizing\ttwo-slot host\n"
    f"h105\tcapacity\t{HOST_D}\t192.0.2.41\t10\t/opt/onex/bin/uv\t0.11.0"
    "\t/srv/onex-prepush\tlockdir\t2\t-\tauthorizing\ttwo-slot host\n"
    f"hcloud\tcapacity\t{HOST_E}\t198.51.100.50\t16\t/opt/onex/bin/uv\t0.11.0"
    "\t/srv/onex-prepush\tlockdir\t1\t-\tauthorizing\toverflow host\n"
)

SYNTHETIC_TABLE = _HEADER + SYNTHETIC_ROWS


def write_private_root(base: Path, table_text: str = SYNTHETIC_TABLE) -> Path:
    """Create a plain-directory workspace-config root holding ``table_text``."""
    root = base / "workspace_config"
    target = root / PRIVATE_TABLE_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(table_text, encoding="utf-8")
    return root
