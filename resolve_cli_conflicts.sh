#!/bin/bash
# Script to resolve CLI model conflicts following the established pattern

CLI_FILES=$(git status --porcelain | grep "^UU" | grep "model_cli" | awk '{print $2}')

for file in $CLI_FILES; do
    echo "Resolving conflicts in $file..."

    # Check if file has import conflicts
    if grep -q "from typing import Any$" "$file" && grep -q "from typing import Any, Union" "$file"; then
        echo "  - Resolving import conflict (taking main's improved imports)"
        # Replace the import conflict with main's version
        perl -i -pe '
            BEGIN { $in_conflict = 0; }
            if (/^<<<<<<< HEAD$/) { $in_conflict = 1; next; }
            if (/^=======/ && $in_conflict) { $in_conflict = 2; next; }
            if (/^>>>>>>> origin\/main$/ && $in_conflict) { $in_conflict = 0; next; }
            if ($in_conflict == 1) { next; }  # Skip our version
            if ($in_conflict == 2) { print; next; }  # Keep main version
            print;
        ' "$file"
    fi

    # Check if file has protocol vs model_config conflict
    if grep -q "# Protocol method implementations" "$file" && grep -q "model_config = {" "$file"; then
        echo "  - Resolving protocol vs model_config conflict (keeping both)"
        # This is more complex - replace the conflict section with combined version
        perl -i -pe '
            BEGIN { $in_conflict = 0; $protocol_section = ""; $config_section = ""; }
            if (/^<<<<<<< HEAD$/) { $in_conflict = 1; next; }
            if (/^=======/ && $in_conflict) { $in_conflict = 2; next; }
            if (/^>>>>>>> origin\/main$/ && $in_conflict) {
                # Output config section first, then protocol section
                print $config_section;
                print "\n";
                print $protocol_section;
                $in_conflict = 0;
                $protocol_section = "";
                $config_section = "";
                next;
            }
            if ($in_conflict == 1) { $protocol_section .= $_ . "\n"; next; }
            if ($in_conflict == 2) { $config_section .= $_ . "\n"; next; }
            print;
        ' "$file"
    fi

    # Stage the resolved file
    git add "$file"
    echo "  - Staged resolved file"

done

echo "All CLI model conflicts resolved!"
