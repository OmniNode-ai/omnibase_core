#!/bin/bash

# Copy updated framework to all 6 repositories
repos=(
    "../omnibase_spi"
    "../omniagent"
    "../omnibase_infra"
    "../omniplan"
    "../omnimcp"
    "../omnimemory"
)

files_to_copy=(
    "OMNI_ECOSYSTEM_STANDARDIZATION_FRAMEWORK.md"
    "VALIDATION_SCRIPTS.md"
    "ARCHITECTURE_DECISION_RECORDS.md"
)

echo "Copying framework files to all repositories..."

for repo in "${repos[@]}"; do
    if [ -d "$repo" ]; then
        echo "Copying to $repo..."
        for file in "${files_to_copy[@]}"; do
            if [ -f "$file" ]; then
                cp "$file" "$repo/"
                echo "  ✓ Copied $file"
            else
                echo "  ❌ File $file not found"
            fi
        done
    else
        echo "❌ Repository $repo not found"
    fi
done

echo "Framework copy completed!"
