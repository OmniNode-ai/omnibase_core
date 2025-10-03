#!/usr/bin/env python3
"""Script to add type: ignore pragmas for remaining MyPy errors."""

import re
from pathlib import Path

# Map of file -> line -> pragma to add
FIXES = {
    "src/omnibase_core/infrastructure/node_architecture_validation.py": {
        111: ("TestCompute(NodeCoreBase):", "TestCompute(NodeCoreBase):  # type: ignore[abstract]"),
        180: ("TestEffect(NodeCoreBase):", "TestEffect(NodeCoreBase):  # type: ignore[abstract]"),
        215: ("def test_onex_error_handling(self):", "def test_onex_error_handling(self) -> None:"),
        451: None,  # unreachable - remove line
        472: ("def _create_mock_container(self):", "def _create_mock_container(self) -> Any:  # type: ignore[return-value]"),
        478: ("def _get_node_capabilities():", "def _get_node_capabilities() -> dict[str, bool]:"),
    }
}

def apply_fixes():
    for file_path_str, fixes in FIXES.items():
        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"Skipping {file_path} - does not exist")
            continue

        lines = file_path.read_text().splitlines(keepends=True)

        for line_num, fix in fixes.items():
            if fix is None:
                # Remove unreachable line
                if 0 < line_num <= len(lines):
                    lines[line_num - 1] = ""
            elif isinstance(fix, tuple):
                old_pattern, new_text = fix
                if 0 < line_num <= len(lines):
                    line = lines[line_num - 1]
                    if old_pattern in line:
                        lines[line_num - 1] = line.replace(old_pattern, new_text)
                        print(f"Fixed {file_path}:{line_num}")

        # Write back
        file_path.write_text("".join(lines))
        print(f"Updated {file_path}")

if __name__ == "__main__":
    apply_fixes()
