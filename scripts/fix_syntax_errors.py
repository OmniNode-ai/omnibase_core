#!/usr/bin/env python3
"""Fix syntax errors introduced by automated script."""

import re
from pathlib import Path

src_dir = Path(__file__).parent.parent / "src"
fixed = []

for py_file in src_dir.rglob("*.py"):
    content = py_file.read_text(encoding="utf-8")
    original = content

    # Fix double commas after message parameter
    content = re.sub(r"message=(\w+),,", r"message=\1,", content)

    # Fix indentation issues with raise statements
    content = re.sub(
        r"raise ModelOnexError\(\n\s+error_code=",
        r"raise ModelOnexError(\n                error_code=",
        content,
    )

    if content != original:
        py_file.write_text(content, encoding="utf-8")
        fixed.append(str(py_file.relative_to(src_dir.parent.parent)))

print(f"Fixed {len(fixed)} files with syntax errors:")
for f in fixed:
    print(f"  {f}")
