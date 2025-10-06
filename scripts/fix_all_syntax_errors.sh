#!/bin/bash

# Fix all syntax errors from bad import placement
cd /Volumes/PRO-G40/Code/omnibase_core

while true; do
    # Get first file with syntax error
    file=$(poetry run mypy src/omnibase_core/ 2>&1 | grep "Invalid syntax" | head -1 | cut -d':' -f1)

    if [ -z "$file" ]; then
        echo "No more syntax errors found!"
        break
    fi

    echo "Fixing: $file"

    # Read file and fix the import issue
    python3 << EOF
from pathlib import Path
import re

file_path = Path('$file')
if not file_path.exists():
    exit(1)

content = file_path.read_text()
original = content

# Pattern to match and fix
# from X import (
# from omnibase_core.errors.error_codes import ModelCoreErrorCode
#     Y,
# )

lines = content.split('\n')
new_lines = []
error_import_line = None

# Find and remove the error import line
for line in lines:
    if 'from omnibase_core.errors.error_codes import ModelCoreErrorCode' in line:
        error_import_line = line
        continue
    new_lines.append(line)

if not error_import_line:
    print("Could not find error import line")
    exit(1)

# Find where to insert it (after the closing paren of previous multi-line import)
final_lines = []
inserted = False

for i, line in enumerate(new_lines):
    final_lines.append(line)

    # Check if this is a closing paren and there's a multi-line import above
    if not inserted and line.strip().endswith(')') and i > 0:
        # Check if there's a multi-line import above
        for j in range(max(0, i-10), i):
            if 'import (' in new_lines[j]:
                # Insert the error import after this closing paren
                final_lines.append(error_import_line)
                inserted = True
                break

# Write back
file_path.write_text('\n'.join(final_lines))
print(f"Fixed {file_path}")
EOF

    if [ $? -ne 0 ]; then
        echo "  Failed to fix $file"
        break
    fi

    echo "  ✓ Fixed"
done

echo "Done!"
